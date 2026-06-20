"""
Room-layout / 3-D domain tools for the SpaceFlow AI agents.

This module powers the room_designer agent. It parses natural-language prompts,
checks live furniture availability, generates event-aware layouts with server-side
collision/fit rules, persists the result, and broadcasts it to the Three.js bridge.

The layout engine intentionally mirrors the client-side furnishing constraints:
- the room floor has a small inset around the edges
- floor items cannot overlap
- stackable items sit on tables instead of the floor
- conference layouts keep presentation zones and aisles clear
- hackathon/workshop layouts use explicit pod footprints
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    THREE_D_ROOM_DIMENSIONS,
    get_reserved_quantity,
    list_assets,
    list_venues,
    save_ai_layout,
)
from app.websocket.manager import ws_manager


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "parse_design_prompt",
            "description": (
                "Analyse a natural-language room-design prompt and extract a structured "
                "layout specification: event_type, attendee_count, equipment flags, "
                "layout style, and room dimensions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The raw user design prompt.",
                    },
                    "venue_name": {
                        "type": "string",
                        "description": "Name of the venue to design the room for.",
                    },
                },
                "required": ["prompt", "venue_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_and_apply_layout",
            "description": (
                "Generate a collision-aware furniture layout from a spec, persist it to the "
                "database, and broadcast it to the Three.js 3-D bridge via WebSocket. "
                "Returns layout_id, item_count, placed seats, and placement limitations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {
                        "type": "string",
                        "description": "Name of the venue.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Original design prompt (stored for audit trail).",
                    },
                    "event_request_id": {
                        "type": "string",
                        "description": "Optional UUID of the related event request.",
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "Optional ISO 8601 datetime — used to check live furniture availability.",
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "Optional ISO 8601 datetime.",
                    },
                },
                "required": ["venue_name", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_room_layouts",
            "description": "Return all saved AI-generated layouts for a venue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {
                        "type": "string",
                        "description": "Name of the venue.",
                    },
                },
                "required": ["venue_name"],
            },
        },
    },
]


ROOM_EDGE_INSET = 0.22
PLACEMENT_GAP = 0.08
SIDE_AISLE = 0.45
CENTER_AISLE = 0.78
BACK_CLEARANCE = 0.35
FRONT_STAGE_DEPTH = 1.25
GRID_STEP = 0.18

# Approximate placed footprints in meters after client scaling.
# The numbers are tuned to the real Three.js furnishing rules rather than to
# perfect physical accuracy; the goal is stable non-overlapping placement.
MODEL_FOOTPRINTS: dict[str, tuple[float, float]] = {
    "simple_chair": (0.42, 0.48),
    "office_chair": (0.50, 0.56),
    "simple_table": (0.92, 0.55),
    "office_table": (1.18, 0.62),
    "whiteboard": (1.20, 0.28),
    "microphone_stand": (0.32, 0.32),
    "speaker": (0.22, 0.22),
    "led_tv": (0.84, 0.20),
    "wall_flat_tv": (1.35, 0.08),
    "office_monitor": (0.28, 0.18),
    "keyboard_mouse": (0.32, 0.16),
}


STYLE_EVENT_TYPE_MAP: dict[str, str] = {
    "conference": "conference",
    "theater": "conference",
    "office": "workshop",
    "hackathon": "hackathon",
    "workshop": "workshop",
    "classroom": "workshop",
    "exhibition": "exhibition",
    "media_studio": "concert",
    "boardroom": "private",
    "banquet": "dinner",
}


@dataclass(slots=True)
class Rect:
    x: float
    z: float
    w: float
    d: float

    def overlaps(self, other: "Rect", gap: float = PLACEMENT_GAP) -> bool:
        return not (
            self.x + self.w / 2 + gap <= other.x - other.w / 2
            or self.x - self.w / 2 >= other.x + other.w / 2 + gap
            or self.z + self.d / 2 + gap <= other.z - other.d / 2
            or self.z - self.d / 2 >= other.z + other.d / 2 + gap
        )

    def within(self, half_w: float, half_d: float) -> bool:
        return (
            self.x - self.w / 2 >= -half_w
            and self.x + self.w / 2 <= half_w
            and self.z - self.d / 2 >= -half_d
            and self.z + self.d / 2 <= half_d
        )


@dataclass
class LayoutPlanner:
    room_dims: dict[str, float]
    items: list[dict[str, Any]] = field(default_factory=list)
    reserved: list[Rect] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    @property
    def room_w(self) -> float:
        return float(self.room_dims["w"])

    @property
    def room_d(self) -> float:
        return float(self.room_dims["d"])

    @property
    def room_h(self) -> float:
        return float(self.room_dims["h"])

    @property
    def half_w(self) -> float:
        return self.room_w / 2 - ROOM_EDGE_INSET

    @property
    def half_d(self) -> float:
        return self.room_d / 2 - ROOM_EDGE_INSET

    def can_place(self, rect: Rect, gap: float = PLACEMENT_GAP) -> bool:
        if not rect.within(self.half_w, self.half_d):
            return False
        return not any(rect.overlaps(other, gap) for other in self.reserved)

    def reserve(self, rect: Rect, gap: float = PLACEMENT_GAP) -> bool:
        if not self.can_place(rect, gap):
            return False
        self.reserved.append(rect)
        return True

    def reserve_zone(self, x: float, z: float, w: float, d: float, gap: float = PLACEMENT_GAP) -> bool:
        return self.reserve(Rect(x=x, z=z, w=w, d=d), gap=gap)

    def candidate_positions(
        self,
        pref_x: float,
        pref_z: float,
        *,
        max_radius: float | None = None,
        step: float = GRID_STEP,
    ) -> Iterable[tuple[float, float]]:
        yield (pref_x, pref_z)
        radius_cap = max_radius or max(self.half_w, self.half_d)
        radius = step
        while radius <= radius_cap + 1e-6:
            segments = max(12, int(radius / step) * 10)
            for idx in range(segments):
                angle = (idx / segments) * math.tau
                yield (
                    pref_x + math.cos(angle) * radius,
                    pref_z + math.sin(angle) * radius,
                )
            radius += step

    def find_free_zone(
        self,
        pref_x: float,
        pref_z: float,
        *,
        w: float,
        d: float,
        gap: float = PLACEMENT_GAP,
        max_radius: float | None = None,
    ) -> tuple[float, float] | None:
        for x, z in self.candidate_positions(pref_x, pref_z, max_radius=max_radius):
            rect = Rect(x=x, z=z, w=w, d=d)
            if self.can_place(rect, gap):
                return (x, z)
        return None

    def place_floor(
        self,
        model_key: str,
        x: float,
        z: float,
        rot_y: float,
        *,
        scale: dict[str, float] | None = None,
        extra: dict[str, Any] | None = None,
        reserve: bool = True,
        allow_search: bool = False,
        gap: float = PLACEMENT_GAP,
        max_radius: float | None = None,
    ) -> int | None:
        w, d = _footprint(model_key, rot_y)
        chosen = (x, z)
        rect = Rect(x=x, z=z, w=w, d=d)

        if reserve:
            if not self.reserve(rect, gap=gap):
                if not allow_search:
                    return None
                candidate = self.find_free_zone(
                    x,
                    z,
                    w=w,
                    d=d,
                    gap=gap,
                    max_radius=max_radius,
                )
                if candidate is None:
                    return None
                chosen = candidate
                self.reserve(Rect(x=chosen[0], z=chosen[1], w=w, d=d), gap=gap)
        else:
            if not rect.within(self.half_w, self.half_d):
                return None

        item: dict[str, Any] = {
            "modelKey": model_key,
            "x": round(chosen[0], 3),
            "z": round(chosen[1], 3),
            "rotY": rot_y,
            "type": "floor",
        }
        if scale:
            item["scale"] = scale
        if extra:
            item.update(extra)
        self.items.append(item)
        return len(self.items) - 1

    def place_wall(
        self,
        model_key: str,
        *,
        wall: str = "back",
        offset_x: float = 0.0,
        mount_ratio: float = 0.66,
    ) -> int:
        half_d = self.room_d / 2 - 0.1
        mount_y = min(1.8, max(1.3, self.room_h * mount_ratio))
        if wall == "back":
            item = {
                "modelKey": model_key,
                "x": round(offset_x, 3),
                "y": round(mount_y, 3),
                "z": round(-half_d, 3),
                "rotY": 0.0,
                "type": "wall",
                "wallAxis": "z",
                "wallCoord": round(-half_d, 3),
                "isPositiveWall": False,
                "mountY": round(mount_y, 3),
            }
        else:
            item = {
                "modelKey": model_key,
                "x": round(offset_x, 3),
                "y": round(mount_y, 3),
                "z": round(half_d, 3),
                "rotY": math.pi,
                "type": "wall",
                "wallAxis": "z",
                "wallCoord": round(half_d, 3),
                "isPositiveWall": True,
                "mountY": round(mount_y, 3),
            }
        self.items.append(item)
        return len(self.items) - 1

    def place_stacked(
        self,
        table_index: int,
        model_key: str,
        *,
        lxf: float = 0.0,
        lzf: float = 0.0,
        rot_y: float = 0.0,
        scale: dict[str, float] | None = None,
    ) -> int:
        base = self.items[table_index]
        item: dict[str, Any] = {
            "modelKey": model_key,
            "x": round(float(base["x"]) + lxf, 3),
            "z": round(float(base["z"]) + lzf, 3),
            "rotY": rot_y,
            "type": "floor",
            "stackOn": table_index,
            "lxf": lxf,
            "lzf": lzf,
        }
        if scale:
            item["scale"] = scale
        self.items.append(item)
        return len(self.items) - 1


def _extract_number_near_keyword(text: str, keywords: list[str]) -> int | None:
    for keyword in keywords:
        match = re.search(rf"(\d+)\s+{re.escape(keyword)}", text)
        if match:
            return int(match.group(1))
    return None


def _flag_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_workstation_count(text: str) -> int | None:
    for pattern in (
        r"(\d+)\s*(?:pc|pcs|computer|computers|workstation|workstations|desk|desks|setup|setups)\b",
        r"\b(?:two|three|four|five|six)\s+(?:pc|pcs|computer|computers|workstation|workstations|desk|desks|setup|setups)\b",
    ):
        match = re.search(pattern, text)
        if match:
            word = match.group(1) if match.lastindex else match.group(0)
            word_map = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
            if word in word_map:
                return word_map[word]
            return int(word)
    return None


def _detect_layout_style(text: str) -> str:
    if _flag_any(
        text,
        [
            "office setup",
            "office layout",
            " like an office",
            "like office",
            "professional setup",
            "professional office",
            "workstation",
            "workstations",
            "pc setup",
            "dual pc",
            "dual monitor",
            "developer desk",
            "coding desk",
        ],
    ) or re.search(r"\b\d+\s*(?:pc|pcs|computer|computers|workstation|workstations)\b", text):
        return "office"
    if _flag_any(text, ["hackathon", "coding", "programming", "pods", "team pod"]):
        return "hackathon"
    if _flag_any(text, ["podcast", "recording", "studio", "media room", "broadcast"]):
        return "media_studio"
    if _flag_any(text, ["classroom", "computer lab", "lab setup", "training room", "student desk"]):
        return "classroom"
    if _flag_any(text, ["workshop", "brainstorm", "cluster", "collaboration", "team tables", "collaborative"]):
        return "workshop"
    if _flag_any(text, ["exhibition", "booth", "showcase", "gallery", "display tables", "networking"]):
        return "exhibition"
    if _flag_any(text, ["boardroom", "meeting room", "roundtable", "board meeting", "u-shaped", "u shaped"]):
        return "boardroom"
    if _flag_any(text, ["dinner", "banquet", "reception", "cocktail"]):
        return "banquet"
    if _flag_any(text, ["theater", "theatre", "auditorium", "presentation rows", "facing stage"]):
        return "theater"
    return "conference"


def _parse_layout_prompt(prompt: str, venue_name: str, room_dims: dict[str, float]) -> dict[str, Any]:
    text = prompt.lower()
    style = _detect_layout_style(text)
    event_type = STYLE_EVENT_TYPE_MAP.get(style, STYLE_EVENT_TYPE_MAP.get("conference", "conference"))
    if style == "theater":
        event_type = "conference"
    workstation_count = _extract_workstation_count(text)
    microphone_count = (
        _extract_number_near_keyword(text, ["microphone", "microphones", "mic", "mics"])
        or (1 if _flag_any(text, ["microphone", "mic", "stage"]) else 0)
    )
    speaker_count = _extract_number_near_keyword(text, ["speaker", "speakers"]) or (
        2 if _flag_any(text, ["speaker", "sound", "audio", "pa system"]) else 0
    )

    include_tv = _flag_any(text, ["tv", "screen", "display", "projector", "monitor wall"]) or style in {
        "conference",
        "classroom",
        "media_studio",
        "theater",
    }
    include_whiteboard = _flag_any(text, ["whiteboard", "flipchart", "ideation board"]) or style in {
        "hackathon",
        "workshop",
        "classroom",
    }
    include_monitors = _flag_any(text, ["monitor", "computer", "workstation", "pc", "desktop", "laptop"]) or style in {
        "hackathon",
        "classroom",
        "media_studio",
        "office",
    }
    include_speakers = speaker_count > 0 or _flag_any(text, ["speaker", "sound", "audio"]) or style == "media_studio"
    include_registration = _flag_any(text, ["registration", "check-in", "welcome desk", "reception desk"])
    include_keyboard = include_monitors or _flag_any(text, ["keyboard", "mouse", "typing"])
    include_stage_tv = _flag_any(text, ["stage", "theater", "theatre", "auditorium", "led tv", "floor screen"])
    use_executive = _flag_any(text, ["executive", "office chair", "office table", "premium", "boardroom", "professional"])

    if style == "office":
        attendee_count = workstation_count or 2
        chair_model = "office_chair"
        table_model = "office_table"
        include_monitors = True
        include_keyboard = True
    else:
        attendee_count = (
            _extract_number_near_keyword(
                text,
                ["person", "people", "attendee", "attendees", "seat", "seats", "guest", "guests"],
            )
            or (workstation_count if workstation_count else None)
            or 24
        )
        chair_model = "office_chair" if use_executive and style == "boardroom" else "simple_chair"
        table_model = "office_table" if use_executive and style in {"boardroom", "workshop"} else "simple_table"

    return {
        "venue_name": venue_name,
        "event_type": event_type,
        "layout_style": style,
        "attendee_count": attendee_count,
        "include_tv": include_tv,
        "include_whiteboard": include_whiteboard,
        "include_monitors": include_monitors,
        "include_speakers": include_speakers,
        "include_registration": include_registration,
        "include_keyboard": include_keyboard,
        "include_stage_tv": include_stage_tv,
        "microphone_count": microphone_count,
        "speaker_count": speaker_count,
        "chair_model": chair_model,
        "table_model": table_model,
        "workstation_count": workstation_count or (attendee_count if style == "office" else None),
        "prompt_text": prompt,
        "room_dims": room_dims,
    }


def _normalize_rot(rot_y: float) -> float:
    value = rot_y % math.tau
    return value if value >= 0 else value + math.tau


def _is_sideways(rot_y: float) -> bool:
    normalized = _normalize_rot(rot_y)
    return abs((normalized % math.pi) - math.pi / 2) < 0.2


def _footprint(model_key: str, rot_y: float) -> tuple[float, float]:
    w, d = MODEL_FOOTPRINTS.get(model_key, (0.40, 0.40))
    if _is_sideways(rot_y):
        return (d, w)
    return (w, d)


def _block_centers(left_edge: float, right_edge: float, item_w: float, gap: float) -> list[float]:
    width = right_edge - left_edge
    if width < item_w:
        return []
    count = max(1, int((width + gap) // (item_w + gap)))
    start = left_edge + item_w / 2
    end = right_edge - item_w / 2
    if count == 1:
        return [round((start + end) / 2, 3)]
    step = (end - start) / (count - 1)
    return [round(start + idx * step, 3) for idx in range(count)]


def _add_conference_support(planner: LayoutPlanner, spec: dict[str, Any], avail: dict[str, int]) -> None:
    if spec["include_tv"] and avail.get("wall_flat_tv", 0) > 0:
        planner.place_wall("wall_flat_tv", wall="back")
    if spec["include_whiteboard"] and avail.get("whiteboard", 0) > 0:
        if planner.room_w >= 5.2:
            planner.place_floor("whiteboard", -planner.half_w + 0.52, -planner.half_d + 0.60, math.pi / 2)
            if avail.get("whiteboard", 0) > 1:
                planner.place_floor("whiteboard", planner.half_w - 0.52, -planner.half_d + 0.60, -math.pi / 2)
        else:
            planner.place_floor("whiteboard", 0.0, -planner.half_d + 0.62, 0.0)

    mic_count = min(int(spec["microphone_count"]), avail.get("microphone_stand", int(spec["microphone_count"])))
    if mic_count:
        offsets = _block_centers(-0.7, 0.7, 0.32, 0.25)
        for idx, x in enumerate(offsets[:mic_count]):
            planner.place_floor("microphone_stand", x, -planner.half_d + 0.90, 0.0)


def _layout_conference(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    _add_conference_support(planner, spec, avail)

    chairs_available = avail.get("simple_chair", 0)
    target = min(spec["attendee_count"], chairs_available)
    if target <= 0:
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": ["No simple chairs available for a conference layout."],
            "layout_style": "conference",
        }

    chair_w, chair_d = _footprint("simple_chair", math.pi)
    row_gap = 0.18
    seat_gap = 0.12
    front_depth = FRONT_STAGE_DEPTH
    left_edge = -planner.half_w + SIDE_AISLE
    right_edge = planner.half_w - SIDE_AISLE
    use_center_aisle = planner.room_w >= 4.8 and target >= 10

    if use_center_aisle:
        left_centers = _block_centers(left_edge, -CENTER_AISLE / 2, chair_w, seat_gap)
        right_centers = _block_centers(CENTER_AISLE / 2, right_edge, chair_w, seat_gap)
        x_centers = left_centers + right_centers
    else:
        x_centers = _block_centers(left_edge, right_edge, chair_w, seat_gap)

    z_centers = _block_centers(
        -planner.half_d + front_depth,
        planner.half_d - BACK_CLEARANCE,
        chair_d,
        row_gap,
    )

    placed = 0
    for row_idx, z in enumerate(z_centers):
        row_positions = list(x_centers)
        if len(row_positions) >= 6 and row_idx % 2 == 1:
            row_positions = [round(x + 0.04, 3) for x in row_positions]
        for x in row_positions:
            if placed >= target:
                break
            if planner.place_floor("simple_chair", x, z, math.pi) is not None:
                placed += 1
        if placed >= target:
            break

    if placed < spec["attendee_count"]:
        planner.limitations.append(
            f"Room and live inventory support {placed} theater-style seats, below the requested {spec['attendee_count']}."
        )

    if spec["include_registration"] and avail.get("simple_table", 0) > 0:
        planner.place_floor("simple_table", planner.half_w - 0.85, planner.half_d - 0.75, math.pi / 2, allow_search=True)

    return {
        "items": planner.items,
        "placed_seats": placed,
        "limitations": planner.limitations,
        "layout_style": "conference",
    }


def _place_four_seat_cluster(
    planner: LayoutPlanner,
    center_x: float,
    center_z: float,
    *,
    seat_goal: int,
    monitor_count: int = 0,
    speaker_count: int = 0,
    include_keyboard: bool = False,
    table_model: str = "simple_table",
    chair_model: str = "simple_chair",
) -> tuple[int, int]:
    # Reserve the whole pod first so the individual chairs/table do not collide
    # with neighboring pods during placement.
    cluster_w = 2.24
    cluster_d = 1.98
    reserved = planner.find_free_zone(center_x, center_z, w=cluster_w, d=cluster_d, max_radius=0.6)
    if reserved is None:
        return (0, 0)
    actual_x, actual_z = reserved
    planner.reserve_zone(actual_x, actual_z, cluster_w, cluster_d)

    table_index = planner.place_floor(
        table_model,
        actual_x,
        actual_z,
        0.0,
        reserve=False,
    )
    if table_index is None:
        return (0, 0)

    seat_offsets = [
        (0.0, 0.72, math.pi),
        (0.0, -0.72, 0.0),
        (0.98, 0.0, -math.pi / 2),
        (-0.98, 0.0, math.pi / 2),
    ]
    placed_seats = 0
    for dx, dz, rot in seat_offsets:
        if placed_seats >= seat_goal:
            break
        if planner.place_floor(chair_model, actual_x + dx, actual_z + dz, rot, reserve=False) is not None:
            placed_seats += 1

    for idx in range(monitor_count):
        if idx == 0:
            planner.place_stacked(table_index, "office_monitor", lxf=0.0, lzf=0.24, rot_y=0.0)
        elif idx == 1:
            planner.place_stacked(table_index, "office_monitor", lxf=0.0, lzf=-0.24, rot_y=math.pi)
        else:
            planner.place_stacked(table_index, "office_monitor", lxf=0.0, lzf=0.0, rot_y=0.0)

    if include_keyboard and monitor_count > 0:
        planner.place_stacked(table_index, "keyboard_mouse", lxf=0.0, lzf=0.0, rot_y=0.0)

    if speaker_count > 0:
        planner.place_stacked(table_index, "speaker", lxf=0.0, lzf=0.0, rot_y=0.0, scale={"h": 0.22})

    return (table_index, placed_seats)


def _template_cluster_positions(room_dims: dict[str, float], cluster_w: float, cluster_d: float) -> list[tuple[float, float]]:
    room_w = float(room_dims["w"])
    room_d = float(room_dims["d"])
    half_w = room_w / 2 - ROOM_EDGE_INSET
    half_d = room_d / 2 - ROOM_EDGE_INSET
    compact = room_w < 6.5 or room_d < 4.0

    side_x = min(max(0.0, half_w - cluster_w / 2), 1.42)
    back_z = -min(max(0.0, half_d - cluster_d / 2), half_d * 0.72)
    front_z = min(max(0.0, half_d - cluster_d / 2), half_d * 0.68)

    if compact:
        return [(-side_x, 0.0), (side_x, 0.0)] if side_x > 0.2 else [(0.0, 0.0)]
    return [(-side_x, back_z), (side_x, back_z), (0.0, front_z)]


def _layout_hackathon(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    requested = spec["attendee_count"]
    chairs_available = avail.get("simple_chair", 0)
    tables_available = avail.get("simple_table", 0)
    if chairs_available <= 0 or tables_available <= 0:
        planner.limitations.append("Hackathon layout requires both tables and chairs in inventory.")
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": planner.limitations,
            "layout_style": "hackathon",
        }

    if spec["include_whiteboard"] and avail.get("whiteboard", 0) > 0:
        planner.place_floor("whiteboard", planner.half_w - 0.55, -planner.half_d + 0.72, -math.pi / 2)

    positions = _template_cluster_positions(room_dims, 2.24, 1.98)
    requested_pods = math.ceil(min(requested, chairs_available) / 4)
    pod_count = min(len(positions), tables_available, requested_pods)
    placed_seats = 0
    monitors_remaining = avail.get("office_monitor", 0) if spec["include_monitors"] else 0
    speakers_remaining = avail.get("speaker", 0) if spec["include_speakers"] else 0

    for cx, cz in positions[:pod_count]:
        seats_needed = min(4, requested - placed_seats, chairs_available - placed_seats)
        monitors_for_pod = min(2, monitors_remaining)
        speakers_for_pod = 1 if speakers_remaining > 0 else 0
        _, seats_here = _place_four_seat_cluster(
            planner,
            cx,
            cz,
            seat_goal=max(0, seats_needed),
            monitor_count=monitors_for_pod,
            speaker_count=speakers_for_pod,
            include_keyboard=spec.get("include_keyboard", False),
            table_model=spec.get("table_model", "simple_table"),
            chair_model=spec.get("chair_model", "simple_chair"),
        )
        placed_seats += seats_here
        monitors_remaining -= monitors_for_pod
        speakers_remaining -= speakers_for_pod

    if spec["include_registration"] and avail.get("simple_table", 0) > pod_count:
        planner.place_floor("simple_table", planner.half_w - 0.85, planner.half_d - 0.78, math.pi / 2, allow_search=True)

    if placed_seats < requested:
        planner.limitations.append(
            f"The current room size and furniture availability support about {placed_seats} hackathon seats, below the requested {requested}."
        )

    return {
        "items": planner.items,
        "placed_seats": placed_seats,
        "limitations": planner.limitations,
        "layout_style": "hackathon",
    }


def _layout_workshop(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    requested = spec["attendee_count"]
    chairs_available = avail.get("simple_chair", 0)
    tables_available = avail.get("simple_table", 0)
    if chairs_available <= 0 or tables_available <= 0:
        planner.limitations.append("Workshop layout requires both simple tables and simple chairs.")
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": planner.limitations,
            "layout_style": "workshop",
        }

    if spec["include_tv"] and avail.get("wall_flat_tv", 0) > 0:
        planner.place_wall("wall_flat_tv", wall="back")
    if spec["include_whiteboard"] and avail.get("whiteboard", 0) > 0:
        planner.place_floor("whiteboard", -planner.half_w + 0.55, -planner.half_d + 0.72, math.pi / 2)

    cluster_w = 2.24
    cluster_d = 1.98
    x_centers = _block_centers(-planner.half_w + SIDE_AISLE, planner.half_w - SIDE_AISLE, cluster_w, 0.38)
    z_centers = _block_centers(-planner.half_d + 1.10, planner.half_d - BACK_CLEARANCE, cluster_d, 0.42)
    x_centers = x_centers[: 1 if planner.room_w < 4.8 else 2 if planner.room_w < 7.2 else 3]
    z_centers = z_centers[: 1 if planner.room_d < 4.8 else 2]

    positions: list[tuple[float, float]] = [(x, z) for z in z_centers for x in x_centers]
    if not positions:
        planner.limitations.append("Room is too compact for the standard workshop pod footprint.")
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": planner.limitations,
            "layout_style": "workshop",
        }

    target = min(requested, chairs_available)
    clusters_needed = min(len(positions), tables_available, math.ceil(target / 4))
    placed_seats = 0
    for cx, cz in positions[:clusters_needed]:
        seats_needed = min(4, target - placed_seats)
        _, seats_here = _place_four_seat_cluster(
            planner,
            cx,
            cz,
            seat_goal=seats_needed,
            monitor_count=2 if spec.get("include_monitors") else 0,
            include_keyboard=spec.get("include_keyboard", False),
            table_model=spec.get("table_model", "simple_table"),
            chair_model=spec.get("chair_model", "simple_chair"),
        )
        placed_seats += seats_here

    if placed_seats < requested:
        planner.limitations.append(
            f"The workshop pod layout supports {placed_seats} seats in this room, below the requested {requested}."
        )

    if spec["include_registration"] and avail.get("simple_table", 0) > clusters_needed:
        planner.place_floor("simple_table", planner.half_w - 0.85, planner.half_d - 0.78, math.pi / 2, allow_search=True)

    return {
        "items": planner.items,
        "placed_seats": placed_seats,
        "limitations": planner.limitations,
        "layout_style": "workshop",
    }


def _layout_classroom(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    if spec["include_tv"] and avail.get("wall_flat_tv", 0) > 0:
        planner.place_wall("wall_flat_tv", wall="back", offset_x=0.55 if planner.room_w >= 5.8 else 0.18, mount_ratio=0.63)
    if spec["include_whiteboard"] and avail.get("whiteboard", 0) > 0:
        planner.place_floor("whiteboard", -planner.half_w + 0.55, -planner.half_d + 0.72, math.pi / 2)

    requested = spec["attendee_count"]
    tables_available = avail.get("simple_table", 0)
    chairs_available = avail.get("simple_chair", 0)
    monitors_available = avail.get("office_monitor", 0) if spec["include_monitors"] else 0
    keyboards_available = avail.get("keyboard_mouse", 0) if spec["include_monitors"] else 0

    if tables_available <= 0 or chairs_available <= 0:
        planner.limitations.append("Classroom layout requires tables and chairs.")
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": planner.limitations,
            "layout_style": "classroom",
        }

    station_w = 1.24
    station_d = 1.20
    x_centers = _block_centers(-planner.half_w + SIDE_AISLE, planner.half_w - SIDE_AISLE, station_w, 0.38)
    z_centers = _block_centers(-planner.half_d + 1.05, planner.half_d - BACK_CLEARANCE, station_d, 0.36)
    x_centers = x_centers[: 2 if planner.room_w < 6 else 3]
    z_centers = z_centers[: 1 if planner.room_d < 4.0 else 2]

    seats_target = min(requested, tables_available, chairs_available)
    placed = 0
    for z in z_centers:
        for x in x_centers:
            if placed >= seats_target:
                break
            zone = planner.find_free_zone(x, z, w=station_w, d=station_d, max_radius=0.45)
            if zone is None:
                continue
            actual_x, actual_z = zone
            planner.reserve_zone(actual_x, actual_z, station_w, station_d)
            table_idx = planner.place_floor("simple_table", actual_x, actual_z, 0.0, reserve=False)
            if table_idx is None:
                continue
            planner.place_floor("simple_chair", actual_x, actual_z + 0.62, math.pi, reserve=False)
            if monitors_available > 0:
                planner.place_stacked(table_idx, "office_monitor", lxf=0.0, lzf=-0.20, rot_y=0.0)
                monitors_available -= 1
            if keyboards_available > 0:
                planner.place_stacked(table_idx, "keyboard_mouse", lxf=0.0, lzf=0.22, rot_y=0.0)
                keyboards_available -= 1
            placed += 1
        if placed >= seats_target:
            break

    if planner.room_d >= 4.2 and avail.get("simple_table", 0) > placed:
        planner.place_floor("simple_table", 0.0, planner.half_d - 0.78, math.pi)

    if placed < requested:
        planner.limitations.append(
            f"The classroom / lab layout supports {placed} student workstations in this room, below the requested {requested}."
        )

    return {
        "items": planner.items,
        "placed_seats": placed,
        "limitations": planner.limitations,
        "layout_style": "classroom",
    }


def _layout_exhibition(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    table_count = min(avail.get("simple_table", 0), 6 if planner.room_w >= 6 else 4)
    if table_count <= 0:
        planner.limitations.append("No display tables available for an exhibition layout.")
    else:
        side_zs = _block_centers(-planner.half_d + 0.75, planner.half_d - 0.75, 0.55, 0.36)
        used = 0
        for z in side_zs:
            if used >= table_count:
                break
            if planner.place_floor("simple_table", -planner.half_w + 0.72, z, math.pi / 2) is not None:
                used += 1
        for z in side_zs:
            if used >= table_count:
                break
            if planner.place_floor("simple_table", planner.half_w - 0.72, z, -math.pi / 2) is not None:
                used += 1
    if spec["include_tv"] and avail.get("wall_flat_tv", 0) > 0:
        planner.place_wall("wall_flat_tv", wall="back")
    return {
        "items": planner.items,
        "placed_seats": 0,
        "limitations": planner.limitations,
        "layout_style": "exhibition",
    }


def _layout_media_studio(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    if avail.get("wall_flat_tv", 0) > 0:
        planner.place_wall("wall_flat_tv", wall="back", mount_ratio=0.68)

    desk_x = -0.42 if planner.room_w < 6 else -planner.half_w * 0.34
    desk_z = -0.05 if planner.room_d < 3.6 else -planner.half_d * 0.06
    table_idx = planner.place_floor("simple_table", desk_x, desk_z, 0.0, allow_search=True)
    if table_idx is not None:
        if avail.get("office_monitor", 0) > 0:
            planner.place_stacked(table_idx, "office_monitor", lxf=0.0, lzf=-0.22, rot_y=0.0)
        if avail.get("keyboard_mouse", 0) > 0:
            planner.place_stacked(table_idx, "keyboard_mouse", lxf=0.0, lzf=0.24, rot_y=0.0)

    chair_x = desk_x + (0.72 if planner.room_w < 6 else 0.92)
    chair_z = desk_z + (0.26 if planner.room_d < 3.6 else planner.half_d * 0.24)
    planner.place_floor("simple_chair", chair_x, chair_z, math.pi / 2, allow_search=True)

    if avail.get("microphone_stand", 0) > 0:
        planner.place_floor("microphone_stand", chair_x + 0.10, chair_z + 0.34, -0.35, allow_search=True)
    if avail.get("led_tv", 0) > 0:
        planner.place_floor("led_tv", -planner.half_w * 0.82, planner.half_d * 0.62, math.pi / 2, allow_search=True)
    if spec["include_speakers"] and avail.get("speaker", 0) > 0:
        planner.place_floor("speaker", planner.half_w * 0.76, planner.half_d * 0.52, -0.55, allow_search=True, scale={"h": 0.82})
    if spec["include_speakers"] and avail.get("speaker", 0) > 1:
        planner.place_floor("speaker", -planner.half_w * 0.52, planner.half_d * 0.58, 0.42, allow_search=True, scale={"h": 0.58})

    return {
        "items": planner.items,
        "placed_seats": 1,
        "limitations": planner.limitations,
        "layout_style": "media_studio",
    }


def _layout_boardroom(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    tables_available = avail.get("simple_table", 0)
    chairs_available = avail.get("simple_chair", 0)
    if tables_available <= 0 or chairs_available <= 0:
        planner.limitations.append("Boardroom layout requires tables and chairs.")
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": planner.limitations,
            "layout_style": "boardroom",
        }

    target = min(spec["attendee_count"], chairs_available)
    table_count = min(tables_available, 3 if planner.room_w >= 6.8 else 2 if planner.room_w >= 5.2 else 1)
    table_spacing = 1.08
    start_x = -(table_spacing * (table_count - 1)) / 2
    table_indices: list[int] = []
    for idx in range(table_count):
        table_idx = planner.place_floor("simple_table", start_x + idx * table_spacing, 0.0, 0.0)
        if table_idx is not None:
            table_indices.append(table_idx)

    if not table_indices:
        planner.limitations.append("Could not fit the boardroom table arrangement in this room.")
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": planner.limitations,
            "layout_style": "boardroom",
        }

    total_table_length = 0.92 * len(table_indices)
    top_bottom_slots = max(2, min(target // 2, len(table_indices) * 2 + 2))
    x_centers = _block_centers(-total_table_length / 2 - 0.25, total_table_length / 2 + 0.25, 0.42, 0.14)
    placed = 0
    for side in (-1, 1):
        z = side * 0.92
        rot = 0.0 if side < 0 else math.pi
        for x in x_centers:
            if placed >= target:
                break
            if planner.place_floor("simple_chair", x, z, rot, allow_search=True, max_radius=0.18) is not None:
                placed += 1
    for side in (-1, 1):
        if placed >= target:
            break
        x = side * (total_table_length / 2 + 0.82)
        rot = -math.pi / 2 if side > 0 else math.pi / 2
        if planner.place_floor("simple_chair", x, 0.0, rot, allow_search=True, max_radius=0.18) is not None:
            placed += 1

    if spec["include_tv"] and avail.get("wall_flat_tv", 0) > 0:
        planner.place_wall("wall_flat_tv", wall="back")

    if placed < spec["attendee_count"]:
        planner.limitations.append(
            f"The boardroom layout supports {placed} seats in this room, below the requested {spec['attendee_count']}."
        )

    return {
        "items": planner.items,
        "placed_seats": placed,
        "limitations": planner.limitations,
        "layout_style": "boardroom",
    }


def _layout_banquet(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    # Banquet / dinner falls back to workshop-style table clusters without front presentation gear.
    workshop_spec = {
        **spec,
        "include_tv": False,
        "include_whiteboard": False,
        "include_monitors": False,
        "include_speakers": False,
    }
    result = _layout_workshop(room_dims, workshop_spec, avail)
    result["layout_style"] = "banquet"
    return result


def _reserve_existing_items(planner: LayoutPlanner, items: list[dict[str, Any]]) -> None:
    stackable = {"office_monitor", "keyboard_mouse", "speaker"}
    for item in items:
        if item.get("type") == "wall" or item.get("modelKey") in stackable:
            continue
        w, d = _footprint(item["modelKey"], float(item.get("rotY", 0.0)))
        planner.reserve(Rect(item["x"], item["z"], w, d), gap=0.05)


def _compose_catalog_extras(
    room_dims: dict[str, float],
    spec: dict[str, Any],
    avail: dict[str, int],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add prompt-requested 3D models that the base layout did not place yet."""
    planner = LayoutPlanner(room_dims)
    _reserve_existing_items(planner, items)
    new_items = list(items)
    placed_counts: dict[str, int] = {}
    for item in items:
        key = item.get("modelKey")
        if key:
            placed_counts[key] = placed_counts.get(key, 0) + 1

    def add_floor(model_key: str, x: float, z: float, rot_y: float = 0.0, **kwargs: Any) -> None:
        if avail.get(model_key, 0) <= placed_counts.get(model_key, 0):
            return
        idx = planner.place_floor(model_key, x, z, rot_y, allow_search=True, **kwargs)
        if idx is not None:
            new_items.append(planner.items[-1])
            placed_counts[model_key] = placed_counts.get(model_key, 0) + 1

    if spec.get("include_stage_tv") and placed_counts.get("led_tv", 0) == 0:
        add_floor("led_tv", 0.0, -planner.half_d + 0.55, 0.0)

    speaker_target = max(spec.get("speaker_count", 0), 2 if spec.get("include_speakers") else 0)
    while placed_counts.get("speaker", 0) < speaker_target and avail.get("speaker", 0) > placed_counts.get("speaker", 0):
        side = 1 if placed_counts.get("speaker", 0) % 2 else -1
        add_floor(
            "speaker",
            side * planner.half_w * 0.72,
            planner.half_d * 0.45,
            -0.4 * side,
            scale={"h": 0.75},
        )

    mic_target = int(spec.get("microphone_count", 0))
    while placed_counts.get("microphone_stand", 0) < mic_target and avail.get("microphone_stand", 0) > placed_counts.get("microphone_stand", 0):
        offset = placed_counts.get("microphone_stand", 0) * 0.35
        add_floor("microphone_stand", -0.35 + offset, -planner.half_d + 0.85, 0.0)

    if spec.get("include_keyboard"):
        for index, item in enumerate(new_items):
            if item.get("modelKey") not in {"simple_table", "office_table"}:
                continue
            has_monitor = any(
                other.get("stackOn") == index and other.get("modelKey") == "office_monitor"
                for other in new_items
            )
            has_keyboard = any(
                other.get("stackOn") == index and other.get("modelKey") == "keyboard_mouse"
                for other in new_items
            )
            if has_monitor and not has_keyboard and avail.get("keyboard_mouse", 0) > placed_counts.get("keyboard_mouse", 0):
                new_items.append(
                    {
                        "modelKey": "keyboard_mouse",
                        "x": round(float(item["x"]), 3),
                        "z": round(float(item["z"]) + 0.22, 3),
                        "rotY": 0.0,
                        "type": "floor",
                        "stackOn": index,
                        "lxf": 0.0,
                        "lzf": 0.22,
                    }
                )
                placed_counts["keyboard_mouse"] = placed_counts.get("keyboard_mouse", 0) + 1

    return new_items


def _pick_catalog_model(avail: dict[str, int], preferred: str, fallback: str) -> str:
    if avail.get(preferred, 0) > 0:
        return preferred
    return fallback if avail.get(fallback, 0) > 0 else preferred


def _layout_office_workstations(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    planner = LayoutPlanner(room_dims)
    target = int(spec.get("workstation_count") or spec.get("attendee_count") or 2)
    target = max(1, min(target, 6))

    table_model = _pick_catalog_model(avail, spec.get("table_model", "office_table"), "simple_table")
    chair_model = _pick_catalog_model(avail, spec.get("chair_model", "office_chair"), "simple_chair")

    if avail.get(table_model, 0) <= 0:
        planner.limitations.append("No office tables available for a workstation layout.")
        return {
            "items": planner.items,
            "placed_seats": 0,
            "limitations": planner.limitations,
            "layout_style": "office",
        }

    if spec.get("include_whiteboard") and avail.get("whiteboard", 0) > 0:
        planner.place_floor("whiteboard", -planner.half_w + 0.55, -planner.half_d + 0.72, math.pi / 2)

    station_w = 1.28
    station_gap = 0.62
    row_width = target * station_w + max(0, target - 1) * station_gap
    start_x = -row_width / 2 + station_w / 2
    desk_z = 0.0

    placed = 0
    for index in range(target):
        if avail.get(table_model, 0) <= placed:
            planner.limitations.append(f"Inventory supports {placed} workstations, below the requested {target}.")
            break
        x = start_x + index * (station_w + station_gap)
        table_idx = planner.place_floor(table_model, x, desk_z, 0.0, allow_search=True)
        if table_idx is None:
            continue

        planner.place_floor(chair_model, x, desk_z + 0.78, math.pi, allow_search=True)

        if spec.get("include_monitors") and avail.get("office_monitor", 0) > 0:
            planner.place_stacked(table_idx, "office_monitor", lxf=0.0, lzf=-0.18, rot_y=0.0)
        if spec.get("include_keyboard") and avail.get("keyboard_mouse", 0) > 0:
            planner.place_stacked(table_idx, "keyboard_mouse", lxf=0.0, lzf=0.18, rot_y=0.0)

        placed += 1

    if placed == 0:
        planner.limitations.append("Could not fit the requested office workstations in this room.")

    return {
        "items": planner.items,
        "placed_seats": placed,
        "limitations": planner.limitations,
        "layout_style": "office",
    }


def _layout_from_style(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    style = spec["layout_style"]
    if style == "office":
        return _layout_office_workstations(room_dims, spec, avail)
    if style == "theater":
        return _layout_conference(room_dims, spec, avail)
    if style == "hackathon":
        return _layout_hackathon(room_dims, spec, avail)
    if style == "workshop":
        return _layout_workshop(room_dims, spec, avail)
    if style == "classroom":
        return _layout_classroom(room_dims, spec, avail)
    if style == "exhibition":
        return _layout_exhibition(room_dims, spec, avail)
    if style == "media_studio":
        return _layout_media_studio(room_dims, spec, avail)
    if style == "boardroom":
        return _layout_boardroom(room_dims, spec, avail)
    if style == "banquet":
        return _layout_banquet(room_dims, spec, avail)
    return _layout_conference(room_dims, spec, avail)


def _is_modification_prompt(text: str) -> bool:
    text = text.lower()
    return _flag_any(
        text,
        [
            "add ",
            "add a ",
            "add an ",
            "also add",
            "can you add",
            "can u add",
            "put ",
            "place ",
            "hang ",
            "mount ",
            "keep the",
            "keep existing",
            "without removing",
            "on the left",
            "on the right",
            "on the wall",
        ],
    )


def _is_full_redesign_prompt(text: str) -> bool:
    text = text.lower()
    return _flag_any(
        text,
        [
            "start over",
            "from scratch",
            "clear the room",
            "clear everything",
            "replace everything",
            "new layout",
            "redesign the whole",
            "completely new",
        ],
    )


def _has_additive_intent(text: str) -> bool:
    text = text.lower()
    return _flag_any(
        text,
        [
            "tv",
            "television",
            "screen",
            "display",
            "whiteboard",
            "speaker",
            "microphone",
            "mic ",
            "monitor",
            "projector",
            "camera",
            "plant",
            "lamp",
        ],
    )


def _should_modify_existing_layout(
    prompt: str,
    existing_items: list[dict[str, Any]],
    previous_style: str | None = None,
) -> bool:
    if not existing_items or _is_full_redesign_prompt(prompt):
        return False
    if _is_modification_prompt(prompt):
        return True
    if _has_additive_intent(prompt):
        return True
    if previous_style and len(prompt.split()) <= 16:
        return True
    return False


def _infer_layout_style_from_items(items: list[dict[str, Any]]) -> str:
    keys = {item.get("modelKey") for item in items}
    if "office_table" in keys or ("office_monitor" in keys and "office_chair" in keys):
        return "office"
    chair_count = sum(1 for item in items if item.get("modelKey") in {"simple_chair", "office_chair"})
    if chair_count >= 10:
        return "conference"
    if "simple_table" in keys and chair_count >= 4:
        return "workshop"
    return "custom"


def _count_seats(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("modelKey") in {"simple_chair", "office_chair"})


def _append_wall_tv(
    items: list[dict[str, Any]],
    room_dims: dict[str, float],
    *,
    wall: str = "back",
    offset_x: float = 0.0,
    offset_z: float = 0.0,
) -> bool:
    if any(item.get("modelKey") == "wall_flat_tv" for item in items):
        return False

    half_w = float(room_dims["w"]) / 2 - 0.1
    half_d = float(room_dims["d"]) / 2 - 0.1
    mount_y = round(min(1.8, max(1.3, float(room_dims["h"]) * 0.66)), 3)

    if wall == "left":
        items.append(
            {
                "modelKey": "wall_flat_tv",
                "x": round(-half_w, 3),
                "y": mount_y,
                "z": round(offset_z, 3),
                "rotY": math.pi / 2,
                "type": "wall",
                "wallAxis": "x",
                "wallCoord": round(-half_w, 3),
                "isPositiveWall": False,
                "mountY": mount_y,
            }
        )
        return True

    if wall == "right":
        items.append(
            {
                "modelKey": "wall_flat_tv",
                "x": round(half_w, 3),
                "y": mount_y,
                "z": round(offset_z, 3),
                "rotY": -math.pi / 2,
                "type": "wall",
                "wallAxis": "x",
                "wallCoord": round(half_w, 3),
                "isPositiveWall": True,
                "mountY": mount_y,
            }
        )
        return True

    items.append(
        {
            "modelKey": "wall_flat_tv",
            "x": round(offset_x, 3),
            "y": mount_y,
            "z": round(-half_d, 3),
            "rotY": 0.0,
            "type": "wall",
            "wallAxis": "z",
            "wallCoord": round(-half_d, 3),
            "isPositiveWall": False,
            "mountY": mount_y,
        }
    )
    return True


def _modify_existing_layout(
    room_dims: dict[str, float],
    prompt: str,
    existing_items: list[dict[str, Any]],
    avail: dict[str, int],
    previous_style: str | None = None,
) -> dict[str, Any]:
    text = prompt.lower()
    items = [dict(item) for item in existing_items]
    limitations: list[str] = []
    added: list[str] = []
    style = previous_style or _infer_layout_style_from_items(items)

    wants_tv = _flag_any(text, ["tv", "screen", "display", "monitor wall", "flat screen"])
    wants_whiteboard = _flag_any(text, ["whiteboard", "white board", "flipchart"])
    wants_speaker = _flag_any(text, ["speaker", "sound", "audio"])
    wants_mic = _flag_any(text, ["mic", "microphone"])
    wants_chair = _flag_any(text, ["chair", "seat"])
    wants_table = _flag_any(text, ["table", "desk"])

    if wants_tv and avail.get("wall_flat_tv", 0) > 0:
        wall = "back"
        offset_x = 0.0
        if _flag_any(text, ["left wall", "on the left", "left side", "left of"]):
            wall = "left"
        elif _flag_any(text, ["right wall", "on the right", "right side", "right of"]):
            wall = "right"
        elif "left" in text:
            wall = "left"
        elif "right" in text:
            wall = "right"
        if _append_wall_tv(items, room_dims, wall=wall, offset_x=offset_x):
            added.append("wall_flat_tv")

    if wants_whiteboard and avail.get("whiteboard", 0) > 0:
        if not any(item.get("modelKey") == "whiteboard" for item in items):
            half_w = float(room_dims["w"]) / 2 - ROOM_EDGE_INSET
            half_d = float(room_dims["d"]) / 2 - ROOM_EDGE_INSET
            side = -half_w + 0.55 if "left" in text else half_w - 0.55
            items.append(
                {
                    "modelKey": "whiteboard",
                    "x": round(side, 3),
                    "z": round(-half_d + 0.72, 3),
                    "rotY": math.pi / 2 if "left" in text else -math.pi / 2,
                    "type": "floor",
                }
            )
            added.append("whiteboard")

    planner = LayoutPlanner(room_dims)
    _reserve_existing_items(planner, items)

    if wants_speaker and avail.get("speaker", 0) > 0:
        current = sum(1 for item in items if item.get("modelKey") == "speaker")
        if current < avail.get("speaker", 0):
            idx = planner.place_floor(
                "speaker",
                planner.half_w * 0.72,
                planner.half_d * 0.45,
                -0.4,
                allow_search=True,
                scale={"h": 0.75},
            )
            if idx is not None:
                items.append(planner.items[-1])
                added.append("speaker")

    if wants_mic and avail.get("microphone_stand", 0) > 0:
        if not any(item.get("modelKey") == "microphone_stand" for item in items):
            idx = planner.place_floor("microphone_stand", 0.0, -planner.half_d + 0.85, 0.0, allow_search=True)
            if idx is not None:
                items.append(planner.items[-1])
                added.append("microphone_stand")

    if not added:
        limitations.append(
            "Could not apply that change on top of the current layout. Try being specific, e.g. "
            "'add a TV on the left wall'."
        )

    return {
        "items": items,
        "placed_seats": _count_seats(items),
        "limitations": limitations,
        "layout_style": style,
        "models_used": sorted({item["modelKey"] for item in items}),
        "added_models": added,
        "modified": bool(added),
    }


def _generate_layout(room_dims: dict[str, float], spec: dict[str, Any], avail: dict[str, int]) -> dict[str, Any]:
    result = _layout_from_style(room_dims, spec, avail)
    result["items"] = _compose_catalog_extras(room_dims, spec, avail, result["items"])
    result["models_used"] = sorted({item["modelKey"] for item in result["items"]})
    if not result["models_used"]:
        result["limitations"].append(
            "Could not place furniture from the 3D catalog for this prompt — check inventory availability."
        )
    return result


async def _resolve_venue_by_name(venue_name: str, db: AsyncSession):  # type: ignore[return]
    lowered = venue_name.lower().strip()
    venues = await list_venues(db, active_only=False)
    for venue in venues:
        if venue.name.lower() == lowered:
            return venue
    for venue in venues:
        if lowered in venue.name.lower():
            return venue
    return None


async def _get_furniture_availability(
    start_dt: datetime | None,
    end_dt: datetime | None,
    db: AsyncSession,
) -> dict[str, int]:
    assets = await list_assets(db, active_only=True)
    counts: dict[str, int] = {}
    for asset in assets:
        if not asset.three_d_item_key:
            continue
        available = asset.total_quantity
        if start_dt and end_dt:
            reserved = await get_reserved_quantity(asset.id, start_dt, end_dt, db)
            available = max(0, asset.total_quantity - reserved)
        key = asset.three_d_item_key
        counts[key] = counts.get(key, 0) + available
    return counts


def _coerce_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(str(value))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def parse_design_prompt(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    venue_name = str(args["venue_name"])
    prompt = str(args["prompt"])
    venue = await _resolve_venue_by_name(venue_name, db)
    if not venue or not venue.three_d_room_id:
        return {"error": f"Venue '{venue_name}' not found or not linked to a 3-D room."}
    room_dims = THREE_D_ROOM_DIMENSIONS.get(venue.three_d_room_id)
    if not room_dims:
        return {"error": f"No 3-D dimensions registered for room '{venue.three_d_room_id}'."}
    spec = _parse_layout_prompt(prompt, venue.name, room_dims)
    return {
        "venue_id": str(venue.id),
        "three_d_room_id": venue.three_d_room_id,
        "spec": spec,
    }


async def generate_and_apply_layout(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    venue_name = str(args["venue_name"])
    prompt = str(args["prompt"])
    event_request_id_raw = args.get("event_request_id")
    event_request_id = UUID(str(event_request_id_raw)) if event_request_id_raw else None
    start_dt = _coerce_dt(args.get("start_datetime"))
    end_dt = _coerce_dt(args.get("end_datetime"))

    venue = await _resolve_venue_by_name(venue_name, db)
    if not venue or not venue.three_d_room_id:
        return {"error": f"Venue '{venue_name}' not found or has no 3-D room."}
    room_dims = THREE_D_ROOM_DIMENSIONS.get(venue.three_d_room_id)
    if not room_dims:
        return {"error": f"No 3-D dimensions for room '{venue.three_d_room_id}'."}

    spec = _parse_layout_prompt(prompt, venue.name, room_dims)
    availability = await _get_furniture_availability(start_dt, end_dt, db)

    existing_items = args.get("existing_items") or []
    previous_style = args.get("previous_layout_style")
    if _should_modify_existing_layout(
        prompt, existing_items, str(previous_style) if previous_style else None
    ):
        result = _modify_existing_layout(
            room_dims,
            prompt,
            existing_items,
            availability,
            previous_style=str(previous_style) if previous_style else None,
        )
    else:
        result = _generate_layout(room_dims, spec, availability)

    items = result["items"]
    limitations = list(result["limitations"])
    if not items:
        limitations.append("No layout items could be placed for the requested design.")

    layout_name = f"AI Layout - {venue.name}"
    await ws_manager.broadcast_to_channel(
        "3d-bridge",
        {
            "type": "APPLY_LAYOUT",
            "payload": {
                "roomId": venue.three_d_room_id,
                "items": items,
                "source": "ai_agent",
                "layout_name": layout_name,
            },
        },
    )

    layout = await save_ai_layout(
        three_d_room_id=venue.three_d_room_id,
        items=items,
        ai_prompt=prompt,
        layout_name=layout_name,
        event_request_id=event_request_id,
        db=db,
    )

    await ws_manager.broadcast_to_channel(
        "admin",
        {
            "type": "LAYOUT_AI_APPLIED",
            "payload": {
                "room_id": venue.three_d_room_id,
                "layout_id": str(layout.id) if layout else None,
                "item_count": len(items),
            },
        },
    )

    return {
        "venue_id": str(venue.id),
        "venue_name": venue.name,
        "three_d_room_id": venue.three_d_room_id,
        "layout_id": str(layout.id) if layout else None,
        "item_count": len(items),
        "placed_seats": result["placed_seats"],
        "limitations": limitations,
        "event_type": spec["event_type"],
        "layout_style": result["layout_style"],
        "models_used": result.get("models_used", []),
        "added_models": result.get("added_models", []),
        "modified": bool(result.get("modified")),
        "model_availability": availability,
    }


async def list_room_layouts(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models import RoomLayout

    venue_name = str(args["venue_name"])
    venue = await _resolve_venue_by_name(venue_name, db)
    if not venue:
        return {"error": f"Venue '{venue_name}' not found."}
    stmt = (
        select(RoomLayout)
        .where(RoomLayout.venue_id == venue.id)
        .order_by(RoomLayout.created_at.desc())
        .limit(10)
    )
    rows = list((await db.scalars(stmt)).all())
    return {
        "venue_id": str(venue.id),
        "venue_name": venue.name,
        "layout_count": len(rows),
        "layouts": [
            {
                "id": str(row.id),
                "name": row.name,
                "source": row.source,
                "item_count": len(row.items_json or []),
                "created_at": str(row.created_at),
            }
            for row in rows
        ],
    }
