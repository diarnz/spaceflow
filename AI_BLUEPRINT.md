# SpaceFlow — Agentic AI Implementation Blueprint
## Phase-by-Phase Guide | JunctionX Tirana 2026

> This document is the authoritative implementation guide for the Agentic AI subsystem.
> It extends the existing `backend/app/ai/__init__.py` monolith into a proper multi-module
> architecture with true ReAct-style tool-calling, 21 structured tools across 5 domain
> modules, per-agent system prompts, streaming support, conversation management, and a
> deterministic fallback when the LLM is unavailable.
>
> **Do not begin implementation until you have reviewed and approved this blueprint.**

---

## Phase Map & Dependency Chain

```
A1: Module Scaffold & Legacy Preservation
 └─► A2: Venue Tool Module (4 tools)
      └─► A3: Inventory Tool Module (4 tools)
           └─► A4: Layout Tool Module (5 tools + geometry engine)
                └─► A5: Quotation Tool Module (3 tools)
                     └─► A6: Task Tool Module (5 tools)
                          └─► A7: Tool Registry (tools/__init__.py)
                               └─► A8: System Prompts (prompts.py)
                                    └─► A9: ReAct Agent Engine (agent.py)
                                         └─► A10: Updated Public API (__init__.py)
                                              ├─► A11: New Pydantic Schemas
                                              └─► A12: Extended Router & Endpoints
                                                   └─► A13: Background Task Integration
```

---

## Final Directory Layout After This Blueprint

```
backend/app/ai/
├── __init__.py              ← public API: re-exports run_agent from agent.py
├── agent.py                 ← ReAct loop engine (new)
├── prompts.py               ← system prompts for all 5 agent types (new)
├── _legacy.py               ← deterministic fallback — current __init__.py renamed (new)
└── tools/
    ├── __init__.py          ← TOOL_SETS registry + execute_tool() dispatcher (new)
    ├── venue_tools.py       ← 4 venue tools (new)
    ├── inventory_tools.py   ← 4 inventory tools (new)
    ├── layout_tools.py      ← 5 layout tools + full geometry engine (new)
    ├── quotation_tools.py   ← 3 quotation tools (new)
    └── task_tools.py        ← 5 task tools (new)
```

New/extended router and schema files:
```
backend/app/routers/ai.py    ← extended with 6 new endpoints
backend/app/schemas/__init__.py ← extended with 5 new schema classes
```

---

## Global Conventions

Throughout all phases:

- All tool executors: `async def execute_X_tool(name, args, context, db) -> dict[str, Any]`
- Tool executors **never raise** — they return `{"error": "reason"}` on failure
- Tool schemas follow OpenAI function-calling format (OpenRouter-compatible)
- The ReAct loop caps at **10 iterations** to prevent runaway chains
- When `OPENROUTER_API_KEY` is absent, the system transparently falls back to `_legacy.py`
- Room coordinate system: centre of floor at origin; X = room width, Z = room depth, Y = height; Y=0 is floor level
- All monetary amounts are `float` in EUR
- All IDs are UUID v4 strings
- Model keys for the Three.js catalog: `simple_chair`, `simple_table`, `wall_flat_tv`, `whiteboard`, `microphone_stand`, `office_monitor`, `speaker`
- Venue-to-3D-room mapping (from `services.THREE_D_ROOM_DIMENSIONS`):
  - `"blue-box"` → Blue Room (w=5.2, d=3.8, h=2.6)
  - `"orange-box"` → Orange Room (w=8.0, d=4.2, h=3.0)
  - `"lime-green-box"` → Green Room (w=5.5, d=3.2, h=2.6)
  - `"dark-green-box"` → Yellow Room (w=4.2, d=4.0, h=2.6)

---

## Phase A1: Module Scaffold & Legacy Preservation

### Goal

Create the `app/ai/tools/` package and move the entire working content of the current
`app/ai/__init__.py` into `app/ai/_legacy.py`, renaming only the top-level dispatcher
function from `run_agent` to `run_agent_legacy`. After this phase the application
behaves identically to before — the new `__init__.py` simply calls through to `_legacy.py`.

### Prerequisites

Backend implementation complete (all phases in BACKEND_BLUEPRINT.md done and running).

### Files Created / Modified

| File | Action |
|------|--------|
| `backend/app/ai/_legacy.py` | **CREATED** — full copy of current `__init__.py`, `run_agent` renamed to `run_agent_legacy` |
| `backend/app/ai/__init__.py` | **MODIFIED** — thin shim that calls `run_agent_legacy` |
| `backend/app/ai/agent.py` | **CREATED** — empty module (filled in A9) |
| `backend/app/ai/prompts.py` | **CREATED** — empty module (filled in A8) |
| `backend/app/ai/tools/__init__.py` | **CREATED** — empty package (filled in A7) |
| `backend/app/ai/tools/venue_tools.py` | **CREATED** — empty (filled in A2) |
| `backend/app/ai/tools/inventory_tools.py` | **CREATED** — empty (filled in A3) |
| `backend/app/ai/tools/layout_tools.py` | **CREATED** — empty (filled in A4) |
| `backend/app/ai/tools/quotation_tools.py` | **CREATED** — empty (filled in A5) |
| `backend/app/ai/tools/task_tools.py` | **CREATED** — empty (filled in A6) |

### `backend/app/ai/__init__.py` (after A1)

```python
"""SpaceFlow Agentic AI — public API."""
from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


async def run_agent(
    agent_type: str,
    user_message: str,
    context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Primary entry point.  Tries the full ReAct engine first; falls back to
    the deterministic legacy implementation when the LLM is unavailable.
    Filled with the real implementation in Phase A10.  During A1–A9 this
    shim calls _legacy.run_agent_legacy directly so the app keeps working.
    """
    from app.ai._legacy import run_agent_legacy
    return await run_agent_legacy(
        agent_type=agent_type,
        user_message=user_message,
        context=context,
        conversation_history=conversation_history,
        db=db,
    )
```

### `backend/app/ai/_legacy.py` (after A1)

Copy the entire current content of `backend/app/ai/__init__.py` verbatim into this file,
then rename the top-level `run_agent(...)` function to `run_agent_legacy(...)`.
Every other function inside the file stays exactly as-is.

### Phase Gate

```bash
cd backend
python -c "from app.ai import run_agent; print('import ok')"
# Expected: import ok
```

---

## Phase A2: Venue Tool Module

### Goal

Implement four venue-domain tools that the Intake, Conflict Detection, and Copilot
agents use to query and reason about the Pyramid's spaces.

### Files Created

`backend/app/ai/tools/venue_tools.py`

### `backend/app/ai/tools/venue_tools.py`

```python
"""
Venue-domain tools for the SpaceFlow agent system.

Tools:
  1. list_available_venues   — venues free for a specific date/time window
  2. get_venue_details       — full info for one venue by name
  3. check_venue_availability — availability slots for a named venue
  4. suggest_best_venue       — scored recommendation based on event requirements
"""
from __future__ import annotations

from datetime import date, time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    THREE_D_ROOM_DIMENSIONS,
    event_duration_hours,
    get_venue_availability,
    list_venues,
)

# ── JSON Schemas (OpenAI function-calling format) ────────────────────────────

VENUE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_available_venues",
            "description": (
                "List all active venues at the Pyramid of Tirana that are free "
                "during a specific date and time window and can fit the required "
                "number of attendees. Returns venues sorted: fully available first, "
                "then closest capacity fit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Event date in YYYY-MM-DD format.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM format (24-hour).",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in HH:MM format (24-hour).",
                    },
                    "min_capacity": {
                        "type": "integer",
                        "description": "Minimum number of attendees the venue must hold.",
                    },
                },
                "required": ["date", "start_time", "end_time", "min_capacity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_venue_details",
            "description": (
                "Get full details for a venue by name: capacity, floor, pricing, "
                "amenities, 3D room ID, and physical dimensions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {
                        "type": "string",
                        "description": "Name of the venue, e.g. 'Blue Room' or 'Orange Room'.",
                    },
                },
                "required": ["venue_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_venue_availability",
            "description": (
                "Check a specific venue's availability on a date for a given duration. "
                "Returns time slots that are free and slots that are occupied, including "
                "setup and teardown buffers of existing events."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {"type": "string"},
                    "date": {"type": "string", "format": "date"},
                    "duration_hours": {
                        "type": "number",
                        "description": "Required duration in hours.",
                    },
                },
                "required": ["venue_name", "date", "duration_hours"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_best_venue",
            "description": (
                "Recommend the best venue(s) for an event based on attendee count, "
                "event type, and any stated preferences. Returns a ranked list of up "
                "to three candidates with a score and reasoning for each."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "conference", "workshop", "concert", "exhibition",
                            "hackathon", "dinner", "classroom", "private", "other",
                        ],
                    },
                    "attendee_count": {"type": "integer"},
                    "preferences": {
                        "type": "string",
                        "description": (
                            "Free-text preferences, e.g. 'needs a projector, "
                            "ground floor preferred, natural lighting'."
                        ),
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Optional event date for a live availability check.",
                    },
                    "start_time": {"type": "string", "description": "Optional start HH:MM."},
                    "end_time": {"type": "string", "description": "Optional end HH:MM."},
                },
                "required": ["event_type", "attendee_count"],
            },
        },
    },
]

# ── Executor ─────────────────────────────────────────────────────────────────

async def execute_venue_tool(
    name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    db: AsyncSession | None,
) -> dict[str, Any]:
    if name == "list_available_venues":
        return await _list_available_venues(args, db)
    if name == "get_venue_details":
        return await _get_venue_details(args, db)
    if name == "check_venue_availability":
        return await _check_venue_availability(args, db)
    if name == "suggest_best_venue":
        return await _suggest_best_venue(args, db)
    return {"error": f"Unknown venue tool: {name}"}


async def _list_available_venues(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    try:
        requested_date = date.fromisoformat(args["date"])
        start_t = time.fromisoformat(args["start_time"])
        end_t = time.fromisoformat(args["end_time"])
        min_cap = int(args.get("min_capacity", 0))
    except (ValueError, KeyError) as exc:
        return {"error": f"Invalid arguments: {exc}"}

    duration_h = float(event_duration_hours(start_t, end_t))
    venues = await list_venues(db, active_only=True)
    results: list[dict[str, Any]] = []

    for venue in venues:
        if venue.capacity_max < min_cap:
            continue
        avail = await get_venue_availability(venue.id, requested_date, duration_h, db)
        results.append(
            {
                "id": str(venue.id),
                "name": venue.name,
                "floor": venue.floor,
                "capacity_max": venue.capacity_max,
                "area_sqm": float(venue.area_sqm) if venue.area_sqm else None,
                "base_price_per_hour": float(venue.base_price_per_hour),
                "three_d_room_id": venue.three_d_room_id,
                "is_fully_available": avail.is_fully_available,
                "available_slots": [s.model_dump() for s in avail.available_slots],
            }
        )

    results.sort(key=lambda v: (not v["is_fully_available"], v["capacity_max"] - min_cap))
    return {"venues": results, "count": len(results)}


async def _get_venue_details(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    venue_name = str(args.get("venue_name", "")).strip()
    venues = await list_venues(db, active_only=False)
    venue = None
    for v in venues:
        if v.name.lower() == venue_name.lower():
            venue = v
            break
    if venue is None:
        for v in venues:
            if venue_name.lower() in v.name.lower():
                venue = v
                break
    if venue is None:
        return {"error": f"Venue '{venue_name}' not found."}

    dims = THREE_D_ROOM_DIMENSIONS.get(venue.three_d_room_id or "") if venue.three_d_room_id else None
    return {
        "id": str(venue.id),
        "name": venue.name,
        "floor": venue.floor,
        "capacity_min": venue.capacity_min,
        "capacity_max": venue.capacity_max,
        "area_sqm": float(venue.area_sqm) if venue.area_sqm else None,
        "description": venue.description,
        "amenities": venue.amenities,
        "status": venue.status,
        "three_d_room_id": venue.three_d_room_id,
        "base_price_per_hour": float(venue.base_price_per_hour),
        "dimensions_meters": dims,
    }


async def _check_venue_availability(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    venue_name = str(args.get("venue_name", "")).strip()
    venues = await list_venues(db, active_only=False)
    venue = next(
        (v for v in venues if venue_name.lower() in v.name.lower()), None
    )
    if venue is None:
        return {"error": f"Venue '{venue_name}' not found."}
    try:
        requested_date = date.fromisoformat(args["date"])
        duration_h = float(args.get("duration_hours", 4))
    except (ValueError, KeyError) as exc:
        return {"error": f"Invalid arguments: {exc}"}

    avail = await get_venue_availability(venue.id, requested_date, duration_h, db)
    return {
        "venue_id": str(venue.id),
        "venue_name": venue.name,
        "date": str(requested_date),
        "duration_hours": duration_h,
        "is_fully_available": avail.is_fully_available,
        "available_slots": [s.model_dump() for s in avail.available_slots],
        "occupied_slots": [s.model_dump() for s in avail.occupied_slots],
    }


async def _suggest_best_venue(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    event_type = str(args.get("event_type", "other"))
    attendee_count = int(args.get("attendee_count", 1))
    preferences = str(args.get("preferences", "")).lower()

    venues = await list_venues(db, active_only=True)
    scored: list[dict[str, Any]] = []

    for venue in venues:
        if venue.capacity_max < attendee_count:
            continue
        score = 0
        reasons: list[str] = []

        # Capacity fit: closer surplus = higher score
        surplus = venue.capacity_max - attendee_count
        if surplus <= int(attendee_count * 0.3):
            score += 30
            reasons.append(f"Near-perfect capacity fit ({venue.capacity_max} seats for {attendee_count} attendees).")
        elif surplus <= attendee_count:
            score += 20
            reasons.append(f"Good capacity fit ({venue.capacity_max} seats).")
        else:
            score += 8

        # Preference matching
        if any(kw in preferences for kw in ["ground", "floor 0", "floor0"]):
            if venue.floor == 0:
                score += 12
                reasons.append("Ground floor matches stated preference.")
        if any(kw in preferences for kw in ["av", "screen", "projector", "tv", "microphone"]):
            amenity_lc = [a.lower() for a in venue.amenities]
            if any(a in amenity_lc for a in ["av system", "projector", "microphone system", "tv"]):
                score += 10
                reasons.append("AV equipment available in this venue.")
        if any(kw in preferences for kw in ["natural light", "window", "daylight"]):
            if venue.floor == 0:
                score += 6
                reasons.append("Ground-floor venue likely has natural light.")

        # Event-type bonus
        if event_type == "concert" and venue.capacity_max >= 150:
            score += 8
            reasons.append("Large capacity suitable for concert.")
        if event_type in {"hackathon", "workshop"} and venue.area_sqm and float(venue.area_sqm) >= 200:
            score += 6
            reasons.append("Large floor area suits collaborative layout.")

        # Live availability check (optional)
        availability_note = "Availability not checked (no date provided)."
        if args.get("date"):
            try:
                req_date = date.fromisoformat(args["date"])
                s_t = time.fromisoformat(args.get("start_time", "09:00"))
                e_t = time.fromisoformat(args.get("end_time", "17:00"))
                dur = float(event_duration_hours(s_t, e_t))
                avail = await get_venue_availability(venue.id, req_date, dur, db)
                if avail.is_fully_available:
                    score += 25
                    availability_note = "Fully available for the requested date/time."
                    reasons.append("Fully available on the requested date.")
                elif avail.available_slots:
                    score += 8
                    availability_note = f"{len(avail.available_slots)} partial slots available."
                else:
                    score -= 40
                    availability_note = "No availability on the requested date."
                    reasons.append("WARNING: not available on requested date.")
            except (ValueError, TypeError):
                pass

        scored.append(
            {
                "id": str(venue.id),
                "name": venue.name,
                "floor": venue.floor,
                "capacity_max": venue.capacity_max,
                "base_price_per_hour": float(venue.base_price_per_hour),
                "three_d_room_id": venue.three_d_room_id,
                "score": score,
                "reasons": reasons,
                "availability_note": availability_note,
            }
        )

    if not scored:
        return {"error": f"No venues found with capacity >= {attendee_count}."}

    scored.sort(key=lambda v: -v["score"])
    top = scored[:3]
    return {
        "best_match": top[0],
        "recommendations": top,
        "total_venues_evaluated": len(scored),
    }
```

### Phase Gate

```bash
python -c "from app.ai.tools.venue_tools import VENUE_TOOLS, execute_venue_tool; print(len(VENUE_TOOLS), 'venue tools loaded')"
# Expected: 4 venue tools loaded
```

---

## Phase A3: Inventory Tool Module

### Goal

Four inventory tools that let agents query the Pyramid's asset catalog and check
real-time stock availability for any time window.

### `backend/app/ai/tools/inventory_tools.py`

```python
"""
Inventory-domain tools for the SpaceFlow agent system.

Tools:
  1. list_assets              — full asset catalog with category filter
  2. check_asset_availability — bulk availability check for a list of items
  3. get_asset_details        — one asset's full record and availability snapshot
  4. get_inventory_summary    — high-level totals by category (dashboard widget)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import get_reserved_quantity, list_assets

# ── JSON Schemas ─────────────────────────────────────────────────────────────

INVENTORY_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_assets",
            "description": (
                "Return the full operational asset catalog. "
                "Optionally filter by category (e.g. 'seating', 'av', 'furniture'). "
                "Each item includes total quantity, unit price, and the Three.js model key."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter. Leave empty for all assets.",
                    },
                    "include_inactive": {
                        "type": "boolean",
                        "description": "Include assets that are currently marked inactive.",
                        "default": False,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_asset_availability",
            "description": (
                "Check whether a list of assets can be provided in the required quantities "
                "for a specific time window. Returns can_fulfill per item and the shortfall "
                "amount for any items that cannot be satisfied."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of assets to check.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Asset name exactly as in the catalog.",
                                },
                                "quantity": {"type": "integer"},
                            },
                            "required": ["name", "quantity"],
                        },
                    },
                    "date_start": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Window start as ISO 8601 datetime.",
                    },
                    "date_end": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Window end as ISO 8601 datetime.",
                    },
                },
                "required": ["items", "date_start", "date_end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_asset_details",
            "description": (
                "Get full details for a single asset by name: total quantity, unit price, "
                "category, Three.js model key, and current availability."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_name": {"type": "string"},
                    "date_start": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Optional: check available quantity for this window.",
                    },
                    "date_end": {
                        "type": "string",
                        "format": "date-time",
                    },
                },
                "required": ["asset_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_summary",
            "description": (
                "Return a high-level inventory summary grouped by category, showing "
                "total quantities. Useful as a starting point before diving into "
                "individual availability checks."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# ── Executor ─────────────────────────────────────────────────────────────────

async def execute_inventory_tool(
    name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    db: AsyncSession | None,
) -> dict[str, Any]:
    if name == "list_assets":
        return await _list_assets(args, db)
    if name == "check_asset_availability":
        return await _check_asset_availability(args, db)
    if name == "get_asset_details":
        return await _get_asset_details(args, db)
    if name == "get_inventory_summary":
        return await _get_inventory_summary(db)
    return {"error": f"Unknown inventory tool: {name}"}


async def _list_assets(args: dict[str, Any], db: AsyncSession | None) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    category = args.get("category") or None
    active_only = not bool(args.get("include_inactive", False))
    assets = await list_assets(db, category=category, active_only=active_only)
    return {
        "assets": [
            {
                "id": str(a.id),
                "name": a.name,
                "category": a.category,
                "total_quantity": a.total_quantity,
                "unit_price": float(a.unit_price),
                "three_d_item_key": a.three_d_item_key,
                "is_active": a.is_active,
            }
            for a in assets
        ],
        "count": len(assets),
    }


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    parsed = datetime.fromisoformat(str(raw))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def _check_asset_availability(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    start = _parse_dt(args.get("date_start"))
    end = _parse_dt(args.get("date_end"))
    if not start or not end:
        return {"error": "date_start and date_end are required."}
    if end <= start:
        return {"error": "date_end must be after date_start."}

    items: list[dict[str, Any]] = args.get("items", [])
    all_assets = await list_assets(db, active_only=True)
    lookup = {a.name.lower(): a for a in all_assets}
    results: list[dict[str, Any]] = []

    for item in items:
        item_name = str(item.get("name", ""))
        quantity = int(item.get("quantity", 1))
        asset = lookup.get(item_name.lower())
        if asset is None:
            # Try partial match
            asset = next(
                (a for n, a in lookup.items() if item_name.lower() in n), None
            )
        if asset is None:
            results.append(
                {
                    "name": item_name,
                    "requested": quantity,
                    "available": 0,
                    "can_fulfill": False,
                    "shortfall": quantity,
                    "note": "Asset not found in catalog.",
                }
            )
            continue
        reserved = await get_reserved_quantity(asset.id, start, end, db)
        available = max(0, asset.total_quantity - reserved)
        results.append(
            {
                "name": asset.name,
                "asset_id": str(asset.id),
                "requested": quantity,
                "total_in_pool": asset.total_quantity,
                "reserved_in_window": reserved,
                "available": available,
                "can_fulfill": available >= quantity,
                "shortfall": max(0, quantity - available),
            }
        )

    can_all = all(r["can_fulfill"] for r in results)
    return {"items": results, "all_fulfilled": can_all, "shortfall_count": sum(1 for r in results if not r["can_fulfill"])}


async def _get_asset_details(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    asset_name = str(args.get("asset_name", "")).strip()
    all_assets = await list_assets(db, active_only=False)
    asset = next(
        (a for a in all_assets if a.name.lower() == asset_name.lower()), None
    )
    if asset is None:
        asset = next(
            (a for a in all_assets if asset_name.lower() in a.name.lower()), None
        )
    if asset is None:
        return {"error": f"Asset '{asset_name}' not found."}

    result: dict[str, Any] = {
        "id": str(asset.id),
        "name": asset.name,
        "category": asset.category,
        "total_quantity": asset.total_quantity,
        "unit_price": float(asset.unit_price),
        "three_d_item_key": asset.three_d_item_key,
        "description": asset.description,
        "is_active": asset.is_active,
    }
    start = _parse_dt(args.get("date_start"))
    end = _parse_dt(args.get("date_end"))
    if start and end and end > start:
        reserved = await get_reserved_quantity(asset.id, start, end, db)
        result["available_in_window"] = max(0, asset.total_quantity - reserved)
        result["reserved_in_window"] = reserved
    return result


async def _get_inventory_summary(db: AsyncSession | None) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    all_assets = await list_assets(db, active_only=True)
    by_category: dict[str, dict[str, Any]] = {}
    for a in all_assets:
        cat = a.category
        if cat not in by_category:
            by_category[cat] = {"category": cat, "item_count": 0, "total_units": 0}
        by_category[cat]["item_count"] += 1
        by_category[cat]["total_units"] += a.total_quantity
    summary = sorted(by_category.values(), key=lambda c: -c["total_units"])
    return {
        "categories": summary,
        "total_asset_types": len(all_assets),
        "total_units": sum(a.total_quantity for a in all_assets),
    }
```

### Phase Gate

```bash
python -c "from app.ai.tools.inventory_tools import INVENTORY_TOOLS; print(len(INVENTORY_TOOLS), 'inventory tools loaded')"
# Expected: 4 inventory tools loaded
```

---

## Phase A4: Layout Tool Module + Geometry Engine

### Goal

Five layout tools including `push_layout_to_3d` (which broadcasts in real time to the
Three.js app via WebSocket) and `generate_room_layout` (which delegates to a pure-Python
geometry engine). The geometry engine is moved wholesale from the current `app/ai/__init__.py`
so it becomes the authoritative, reusable implementation.

### `backend/app/ai/tools/layout_tools.py`

```python
"""
Layout-domain tools for the SpaceFlow agent system.

Tools:
  1. get_venue_dimensions    — room dimensions + 3D room ID for a named venue
  2. get_available_furniture — Three.js model keys and their available counts
  3. generate_room_layout    — geometry-engine layout for event type + attendee count
  4. push_layout_to_3d       — broadcast layout to live Three.js app via WebSocket
  5. clear_room_layout       — send CLEAR_ROOM command to 3D app

Geometry engine functions (pure Python, no LLM calls):
  _layout_conference, _layout_workshop, _layout_hackathon, _layout_exhibition,
  _wall_item, _evenly_spaced_positions, _parse_layout_spec
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any
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

# ── JSON Schemas ─────────────────────────────────────────────────────────────

LAYOUT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_venue_dimensions",
            "description": (
                "Get the physical dimensions (width, depth, height in metres) and "
                "the Three.js room ID for a named venue. Call this first before "
                "generating any layout."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {
                        "type": "string",
                        "description": "Name of the venue, e.g. 'Blue Room'.",
                    },
                },
                "required": ["venue_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_furniture",
            "description": (
                "Return the Three.js model catalog keys with available stock counts "
                "for a time window. Use after get_venue_dimensions to know what "
                "furniture can be placed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_start": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Window start ISO 8601. Omit for total pool (ignores reservations).",
                    },
                    "date_end": {
                        "type": "string",
                        "format": "date-time",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_room_layout",
            "description": (
                "Compute an optimised furniture layout for a room. Returns an array of "
                "item placement objects in the format consumed by the Three.js "
                "furnishing engine. This does NOT push to the 3D app — call "
                "push_layout_to_3d afterwards."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {"type": "string"},
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "conference", "workshop", "hackathon",
                            "exhibition", "classroom", "other",
                        ],
                    },
                    "attendee_count": {"type": "integer"},
                    "preferences": {
                        "type": "string",
                        "description": (
                            "Free-text style notes, e.g. 'include TV screen at front, "
                            "registration table near entrance, U-shape seating'."
                        ),
                    },
                    "date_start": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Optional: use real inventory counts for this window.",
                    },
                    "date_end": {"type": "string", "format": "date-time"},
                },
                "required": ["venue_name", "event_type", "attendee_count"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "push_layout_to_3d",
            "description": (
                "Push a furniture layout to the live Three.js 3D visualization via "
                "WebSocket. This immediately reconfigures the room in real time. "
                "Optionally saves the layout to the database."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "three_d_room_id": {
                        "type": "string",
                        "description": "Three.js room ID, e.g. 'blue-box'. Comes from get_venue_dimensions.",
                    },
                    "layout_items": {
                        "type": "array",
                        "description": "Array of furniture placements from generate_room_layout.",
                        "items": {"type": "object"},
                    },
                    "layout_name": {
                        "type": "string",
                        "description": "Human-readable name saved with the layout.",
                    },
                    "save_to_db": {
                        "type": "boolean",
                        "description": "Persist this layout as the current layout for the venue.",
                        "default": True,
                    },
                    "event_request_id": {
                        "type": "string",
                        "description": "Optional: link this layout to a specific event request UUID.",
                    },
                },
                "required": ["three_d_room_id", "layout_items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_room_layout",
            "description": "Clear all furniture from a room in the live 3D visualization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "three_d_room_id": {
                        "type": "string",
                        "description": "Three.js room ID, e.g. 'blue-box'.",
                    },
                },
                "required": ["three_d_room_id"],
            },
        },
    },
]

# ── Executor ─────────────────────────────────────────────────────────────────

async def execute_layout_tool(
    name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    db: AsyncSession | None,
) -> dict[str, Any]:
    if name == "get_venue_dimensions":
        return await _get_venue_dimensions(args, db)
    if name == "get_available_furniture":
        return await _get_available_furniture(args, db)
    if name == "generate_room_layout":
        return await _generate_room_layout(args, db)
    if name == "push_layout_to_3d":
        return await _push_layout_to_3d(args, context, db)
    if name == "clear_room_layout":
        return await _clear_room_layout(args)
    return {"error": f"Unknown layout tool: {name}"}


async def _get_venue_dimensions(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    venue_name = str(args.get("venue_name", "")).strip()
    if db is not None:
        venues = await list_venues(db, active_only=False)
        venue = next(
            (v for v in venues if venue_name.lower() in v.name.lower()), None
        )
        if venue and venue.three_d_room_id:
            dims = THREE_D_ROOM_DIMENSIONS.get(venue.three_d_room_id, {})
            return {
                "venue_id": str(venue.id),
                "venue_name": venue.name,
                "three_d_room_id": venue.three_d_room_id,
                "width_m": dims.get("w"),
                "depth_m": dims.get("d"),
                "height_m": dims.get("h"),
                "capacity_max": venue.capacity_max,
            }
    # Fallback: scan the static map by name fragment
    for room_id, dims in THREE_D_ROOM_DIMENSIONS.items():
        colour = room_id.replace("-box", "").replace("-", " ").lower()
        if colour in venue_name.lower() or venue_name.lower() in colour:
            return {
                "venue_id": None,
                "venue_name": venue_name,
                "three_d_room_id": room_id,
                "width_m": dims["w"],
                "depth_m": dims["d"],
                "height_m": dims["h"],
            }
    return {"error": f"Venue '{venue_name}' not found or has no 3D room linked."}


def _coerce_dt(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(raw))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


async def _get_available_furniture(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    start = _coerce_dt(args.get("date_start"))
    end = _coerce_dt(args.get("date_end"))
    if db is None:
        return {"error": "Database session not available."}
    assets = await list_assets(db, active_only=True)
    counts: dict[str, int] = {}
    for asset in assets:
        if not asset.three_d_item_key:
            continue
        available = asset.total_quantity
        if start and end and end > start:
            reserved = await get_reserved_quantity(asset.id, start, end, db)
            available = max(0, asset.total_quantity - reserved)
        key = asset.three_d_item_key
        counts[key] = counts.get(key, 0) + available
    return {
        "furniture_available": counts,
        "note": "Keys match Three.js model catalog. Values are available unit counts.",
    }


async def _generate_room_layout(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    venue_name = str(args.get("venue_name", "")).strip()
    event_type = str(args.get("event_type", "conference")).lower()
    attendee_count = int(args.get("attendee_count", 20))
    preferences = str(args.get("preferences", "")).lower()

    # Resolve room dimensions
    room_id: str | None = None
    room_dims: dict[str, float] | None = None
    if db is not None:
        venues = await list_venues(db, active_only=False)
        venue = next(
            (v for v in venues if venue_name.lower() in v.name.lower()), None
        )
        if venue and venue.three_d_room_id:
            room_id = venue.three_d_room_id
            room_dims = THREE_D_ROOM_DIMENSIONS.get(room_id)

    if room_dims is None:
        for rid, dims in THREE_D_ROOM_DIMENSIONS.items():
            colour = rid.replace("-box", "").replace("-", " ").lower()
            if colour in venue_name.lower() or venue_name.lower() in colour:
                room_id = rid
                room_dims = dims
                break

    if room_dims is None:
        return {"error": f"No 3D dimensions found for '{venue_name}'."}

    # Build spec from prompt + args
    spec: dict[str, Any] = {
        "venue_name": venue_name,
        "event_type": event_type,
        "attendee_count": attendee_count,
        "include_tv": any(kw in preferences for kw in ["tv", "screen", "display", "projector"]),
        "include_whiteboard": any(kw in preferences for kw in ["whiteboard"])
            or event_type in {"workshop", "classroom", "hackathon"},
        "include_monitors": any(kw in preferences for kw in ["pc", "computer", "monitor"])
            or event_type == "hackathon",
        "include_microphones": 1 if any(kw in preferences for kw in ["mic", "microphone"]) else 0,
        "side_tables": any(kw in preferences for kw in ["registration", "coffee", "side table"])
            or event_type in {"workshop", "hackathon"},
        "room_dims": room_dims,
    }

    # Get real inventory counts for the window
    availability: dict[str, int] = {}
    start = _coerce_dt(args.get("date_start"))
    end = _coerce_dt(args.get("date_end"))
    if db is not None:
        assets = await list_assets(db, active_only=True)
        for asset in assets:
            if not asset.three_d_item_key:
                continue
            avail = asset.total_quantity
            if start and end and end > start:
                reserved = await get_reserved_quantity(asset.id, start, end, db)
                avail = max(0, asset.total_quantity - reserved)
            key = asset.three_d_item_key
            availability[key] = availability.get(key, 0) + avail
    else:
        # Generous defaults if no DB
        availability = {
            "simple_chair": attendee_count + 50,
            "simple_table": attendee_count // 4 + 10,
            "wall_flat_tv": 2,
            "whiteboard": 3,
            "microphone_stand": 4,
            "office_monitor": 20,
            "speaker": 6,
        }

    result = _generate_layout_from_spec(room_id or "blue-box", room_dims, spec, availability)
    return {
        "three_d_room_id": room_id,
        "venue_name": venue_name,
        "event_type": event_type,
        "attendee_count": attendee_count,
        "items": result["items"],
        "placed_seats": result["placed_seats"],
        "item_count": len(result["items"]),
        "limitations": result["limitations"],
        "note": "Pass items array to push_layout_to_3d to apply to the live 3D visualization.",
    }


async def _push_layout_to_3d(
    args: dict[str, Any], context: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    room_id = str(args.get("three_d_room_id", "")).strip()
    items: list[dict[str, Any]] = args.get("layout_items", [])
    layout_name = str(args.get("layout_name", "AI Generated Layout"))

    if not room_id:
        return {"error": "three_d_room_id is required."}
    if not items:
        return {"error": "layout_items must not be empty."}

    await ws_manager.broadcast_to_channel(
        "3d-bridge",
        {
            "type": "APPLY_LAYOUT",
            "payload": {
                "roomId": room_id,
                "items": items,
                "source": "ai_agent",
                "layout_name": layout_name,
            },
        },
    )

    layout_id: str | None = None
    if args.get("save_to_db", True) and db is not None:
        ai_prompt = str(context.get("user_message", "AI agent layout"))
        event_request_id: UUID | None = None
        raw_req_id = args.get("event_request_id") or context.get("event_request_id")
        if raw_req_id:
            try:
                event_request_id = UUID(str(raw_req_id))
            except (ValueError, TypeError):
                pass
        layout = await save_ai_layout(
            three_d_room_id=room_id,
            items=items,
            ai_prompt=ai_prompt,
            layout_name=layout_name,
            event_request_id=event_request_id,
            db=db,
        )
        if layout:
            layout_id = str(layout.id)

    await ws_manager.broadcast_to_channel(
        "admin",
        {
            "type": "LAYOUT_AI_APPLIED",
            "payload": {
                "room_id": room_id,
                "layout_id": layout_id,
                "item_count": len(items),
                "layout_name": layout_name,
            },
        },
    )

    return {
        "success": True,
        "room_id": room_id,
        "items_placed": len(items),
        "layout_id": layout_id,
        "saved_to_db": layout_id is not None,
    }


async def _clear_room_layout(args: dict[str, Any]) -> dict[str, Any]:
    room_id = str(args.get("three_d_room_id", "")).strip()
    if not room_id:
        return {"error": "three_d_room_id is required."}
    await ws_manager.broadcast_to_channel(
        "3d-bridge",
        {"type": "CLEAR_ROOM", "payload": {"roomId": room_id}},
    )
    return {"success": True, "room_id": room_id}


# ── Geometry Engine ───────────────────────────────────────────────────────────
# Pure-Python spatial calculations — no LLM involved.
# Room origin is at the center of the floor (Y=0). X = width axis, Z = depth axis.

def _generate_layout_from_spec(
    room_id: str,
    room_dims: dict[str, float],
    spec: dict[str, Any],
    availability: dict[str, int],
) -> dict[str, Any]:
    event_type = spec["event_type"]
    if event_type == "hackathon":
        return _layout_hackathon(room_dims, spec, availability)
    if event_type in {"workshop", "classroom"}:
        return _layout_workshop(room_dims, spec, availability)
    if event_type == "exhibition":
        return _layout_exhibition(room_dims, spec, availability)
    return _layout_conference(room_dims, spec, availability)


def _layout_conference(
    room_dims: dict[str, float],
    spec: dict[str, Any],
    availability: dict[str, int],
) -> dict[str, Any]:
    w, d = room_dims["w"], room_dims["d"]
    chairs_avail = availability.get("simple_chair", spec["attendee_count"])
    target = min(spec["attendee_count"], chairs_avail)
    items: list[dict[str, Any]] = []
    limitations: list[str] = []

    if target < spec["attendee_count"]:
        limitations.append(
            f"Only {target} standard chairs were available for this time window."
        )

    if spec["include_tv"] and availability.get("wall_flat_tv", 1) > 0:
        items.append(_wall_item("wall_flat_tv", w, d, room_dims["h"], wall="back", offset_x=0.0))

    if spec["include_whiteboard"] and availability.get("whiteboard", 0) > 0:
        items.append({"modelKey": "whiteboard", "x": -w * 0.22, "z": -(d / 2 - 0.5), "rotY": 0.0, "type": "floor"})
        if availability.get("whiteboard", 0) > 1:
            items.append({"modelKey": "whiteboard", "x": w * 0.22, "z": -(d / 2 - 0.5), "rotY": 0.0, "type": "floor"})

    mic_requested = int(spec["include_microphones"])
    mic_count = min(mic_requested, availability.get("microphone_stand", mic_requested))
    if mic_count < mic_requested:
        limitations.append(f"Only {mic_count} microphone stand(s) were available.")
    for idx in range(mic_count):
        items.append({
            "modelKey": "microphone_stand",
            "x": (idx - (mic_count - 1) / 2) * 0.7,
            "z": -(d / 2 - 1.25),
            "rotY": 0.0,
            "type": "floor",
        })

    usable_w = max(1.6, w - 1.0)
    usable_d = max(1.6, d - 1.5)
    cols = max(2, min(10, int(usable_w / 0.62)))
    rows = max(1, int(usable_d / 0.72))
    placed = min(target, cols * rows)
    if placed < target:
        limitations.append(f"Room footprint fits {placed} seats in a clean conference layout.")

    x_pos = _evenly_spaced_positions(cols, usable_w / 2)
    seat = 0
    for row in range(rows):
        z = 0.1 + row * 0.62
        for x in x_pos:
            if seat >= placed:
                break
            items.append({"modelKey": "simple_chair", "x": x, "z": z, "rotY": math.pi, "type": "floor"})
            seat += 1
        if seat >= placed:
            break

    if spec["side_tables"] and availability.get("simple_table", 0) > 0:
        items.append({"modelKey": "simple_table", "x": -(w / 2 - 0.8), "z": d / 2 - 0.9, "rotY": math.pi / 2, "type": "floor"})
        if availability.get("simple_table", 0) > 1:
            items.append({"modelKey": "simple_table", "x": w / 2 - 0.8, "z": d / 2 - 0.9, "rotY": -math.pi / 2, "type": "floor"})

    return {"items": items, "placed_seats": placed, "limitations": limitations}


def _layout_workshop(
    room_dims: dict[str, float],
    spec: dict[str, Any],
    availability: dict[str, int],
) -> dict[str, Any]:
    w, d = room_dims["w"], room_dims["d"]
    tables_avail = availability.get("simple_table", 0)
    chairs_avail = availability.get("simple_chair", spec["attendee_count"])
    target = min(spec["attendee_count"], chairs_avail)
    cluster_size = 4
    cluster_count = max(1, min(tables_avail or 1, math.ceil(target / cluster_size)))
    items: list[dict[str, Any]] = []
    limitations: list[str] = []

    if tables_avail and cluster_count > tables_avail:
        limitations.append(f"Only {tables_avail} tables available — reduced cluster count.")

    if spec["include_tv"] and availability.get("wall_flat_tv", 0) > 0:
        items.append(_wall_item("wall_flat_tv", w, d, room_dims["h"], wall="back", offset_x=0.0))
    if spec["include_whiteboard"] and availability.get("whiteboard", 0) > 0:
        items.append({"modelKey": "whiteboard", "x": -(w / 2 - 0.45), "z": -(d / 2 - 0.8), "rotY": math.pi / 2, "type": "floor"})

    grid_cols = max(1, min(cluster_count, 2 if w < 6 else 3))
    grid_rows = max(1, math.ceil(cluster_count / grid_cols))
    x_pos = _evenly_spaced_positions(grid_cols, max(1.1, w / 2 - 0.9))
    z_pos = _evenly_spaced_positions(grid_rows, max(0.9, d / 2 - 1.1), start_bias=0.2)

    placed_chairs = 0
    clusters_placed = 0
    for z in z_pos:
        for x in x_pos:
            if clusters_placed >= cluster_count:
                break
            items.append({"modelKey": "simple_table", "x": x, "z": z, "rotY": 0.0, "type": "floor"})
            offsets = [(0, 0.62, math.pi), (0, -0.62, 0.0), (0.72, 0, -math.pi / 2), (-0.72, 0, math.pi / 2)]
            for dx, dz, rot in offsets:
                if placed_chairs >= target:
                    break
                items.append({"modelKey": "simple_chair", "x": x + dx, "z": z + dz, "rotY": rot, "type": "floor"})
                placed_chairs += 1
            clusters_placed += 1
    return {"items": items, "placed_seats": placed_chairs, "limitations": limitations}


def _layout_hackathon(
    room_dims: dict[str, float],
    spec: dict[str, Any],
    availability: dict[str, int],
) -> dict[str, Any]:
    w, d = room_dims["w"], room_dims["d"]
    pod_size = 4
    target = min(spec["attendee_count"], availability.get("simple_chair", spec["attendee_count"]))
    pod_count = min(math.ceil(target / pod_size), availability.get("simple_table", math.ceil(target / pod_size)))
    items: list[dict[str, Any]] = []
    limitations: list[str] = []

    if pod_count * pod_size < spec["attendee_count"]:
        limitations.append(f"Furniture supports ~{pod_count * pod_size} hackathon seats.")

    grid_cols = max(1, min(pod_count, 2 if w < 7 else 3))
    grid_rows = math.ceil(pod_count / grid_cols)
    x_pos = _evenly_spaced_positions(grid_cols, max(1.0, w / 2 - 1.0))
    z_pos = _evenly_spaced_positions(grid_rows, max(0.9, d / 2 - 0.9))
    monitors_left = availability.get("office_monitor", 0)
    speakers_left = availability.get("speaker", 0)
    placed_seats = 0
    pods_left = pod_count

    for z in z_pos:
        for x in x_pos:
            if pods_left <= 0:
                break
            table_idx = len(items)
            items.append({"modelKey": "simple_table", "x": x, "z": z, "rotY": 0.0, "type": "floor"})
            for dx, dz, rot in [(0, 0.62, math.pi), (0, -0.62, 0.0), (0.82, 0, -math.pi / 2), (-0.82, 0, math.pi / 2)]:
                if placed_seats >= target:
                    break
                items.append({"modelKey": "simple_chair", "x": x + dx, "z": z + dz, "rotY": rot, "type": "floor"})
                placed_seats += 1
            if monitors_left > 0:
                items.append({"modelKey": "office_monitor", "x": x, "z": z + 0.18, "rotY": 0.0, "type": "floor", "stackOn": table_idx, "lxf": 0.0, "lzf": 0.28})
                monitors_left -= 1
            if monitors_left > 0:
                items.append({"modelKey": "office_monitor", "x": x, "z": z - 0.18, "rotY": math.pi, "type": "floor", "stackOn": table_idx, "lxf": 0.0, "lzf": -0.28})
                monitors_left -= 1
            if speakers_left > 0:
                items.append({"modelKey": "speaker", "x": x, "z": z, "rotY": 0.0, "type": "floor", "stackOn": table_idx, "scale": {"h": 0.22}})
                speakers_left -= 1
            pods_left -= 1

    if spec["include_whiteboard"] and availability.get("whiteboard", 0) > 0:
        items.append({"modelKey": "whiteboard", "x": w / 2 - 0.55, "z": -(d / 2 - 0.8), "rotY": -math.pi / 2, "type": "floor"})

    return {"items": items, "placed_seats": placed_seats, "limitations": limitations}


def _layout_exhibition(
    room_dims: dict[str, float],
    spec: dict[str, Any],
    availability: dict[str, int],
) -> dict[str, Any]:
    w, d = room_dims["w"], room_dims["d"]
    items: list[dict[str, Any]] = []
    limitations: list[str] = []
    table_count = min(availability.get("simple_table", 0), 6 if w >= 6 else 4)

    if table_count == 0:
        limitations.append("No display tables were available.")

    side_count = max(1, table_count // 2 or 1)
    side_z = _evenly_spaced_positions(side_count, max(0.8, d / 2 - 1.0))
    used = 0
    for z in side_z:
        if used >= table_count:
            break
        items.append({"modelKey": "simple_table", "x": -(w / 2 - 0.8), "z": z, "rotY": math.pi / 2, "type": "floor"})
        used += 1
    for z in side_z:
        if used >= table_count:
            break
        items.append({"modelKey": "simple_table", "x": w / 2 - 0.8, "z": z, "rotY": -math.pi / 2, "type": "floor"})
        used += 1

    if spec["include_tv"] and availability.get("wall_flat_tv", 0) > 0:
        items.append(_wall_item("wall_flat_tv", w, d, room_dims["h"], wall="back", offset_x=0.0))

    return {"items": items, "placed_seats": 0, "limitations": limitations}


def _wall_item(
    model_key: str,
    room_w: float,
    room_d: float,
    room_h: float,
    *,
    wall: str = "back",
    offset_x: float = 0.0,
) -> dict[str, Any]:
    half_d = room_d / 2 - 0.1
    mount_y = min(1.75, max(1.35, room_h * 0.6))
    if wall == "back":
        return {
            "modelKey": model_key,
            "x": offset_x,
            "y": mount_y,
            "z": -half_d,
            "rotY": 0.0,
            "type": "wall",
            "wallAxis": "z",
            "wallCoord": -half_d,
            "isPositiveWall": False,
            "mountY": mount_y,
        }
    return {
        "modelKey": model_key,
        "x": offset_x,
        "y": mount_y,
        "z": half_d,
        "rotY": math.pi,
        "type": "wall",
        "wallAxis": "z",
        "wallCoord": half_d,
        "isPositiveWall": True,
        "mountY": mount_y,
    }


def _evenly_spaced_positions(
    count: int, extent: float, *, start_bias: float = 0.0
) -> list[float]:
    if count <= 1:
        return [start_bias]
    step = (extent * 2) / (count - 1)
    return [-extent + i * step + start_bias for i in range(count)]
```

### Phase Gate

```bash
python -c "from app.ai.tools.layout_tools import LAYOUT_TOOLS, _layout_conference; print(len(LAYOUT_TOOLS), 'layout tools loaded')"
# Expected: 5 layout tools loaded
```

---

## Phase A5: Quotation Tool Module

### Goal

Three quotation tools that let the Intake Agent produce cost estimates and the
Copilot retrieve existing quotations for a request.

### `backend/app/ai/tools/quotation_tools.py`

```python
"""
Quotation-domain tools for the SpaceFlow agent system.

Tools:
  1. estimate_quotation   — compute cost breakdown from venue + assets + event type
  2. get_quotation_details — fetch an existing saved quotation from the DB
  3. list_service_fees     — return the service-fee schedule for an event type
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Quotation
from app.services import SERVICE_FEES, list_assets, list_venues

# ── JSON Schemas ─────────────────────────────────────────────────────────────

QUOTATION_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "estimate_quotation",
            "description": (
                "Calculate a detailed cost estimate including venue rental, asset "
                "costs, and standard service fees. Returns subtotal, 20% VAT, and "
                "total with itemised breakdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {
                        "type": "string",
                        "description": "Name of the venue to quote (e.g. 'Blue Room').",
                    },
                    "duration_hours": {
                        "type": "number",
                        "description": "Total event duration in hours.",
                    },
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "conference", "workshop", "concert", "exhibition",
                            "hackathon", "dinner", "classroom", "private", "other",
                        ],
                    },
                    "attendee_count": {
                        "type": "integer",
                        "description": "Expected number of attendees.",
                    },
                    "requested_assets": {
                        "type": "array",
                        "description": "Optional explicit asset list.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "integer"},
                            },
                        },
                    },
                },
                "required": ["venue_name", "duration_hours", "event_type", "attendee_count"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_quotation_details",
            "description": (
                "Retrieve an existing quotation from the database by request ID. "
                "Returns all line items, totals, status, and creation date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "The event request UUID to look up the quotation for.",
                    },
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_service_fees",
            "description": (
                "Return the standard service-fee schedule for a given event type "
                "(e.g. coordination staff, setup/teardown labour). Useful for "
                "explaining pricing to a client."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "conference", "workshop", "concert", "exhibition",
                            "hackathon", "dinner", "private", "other",
                        ],
                    },
                },
                "required": ["event_type"],
            },
        },
    },
]

# ── Executor ─────────────────────────────────────────────────────────────────

async def execute_quotation_tool(
    name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    db: AsyncSession | None,
) -> dict[str, Any]:
    if name == "estimate_quotation":
        return await _estimate_quotation(args, db)
    if name == "get_quotation_details":
        return await _get_quotation_details(args, db)
    if name == "list_service_fees":
        return _list_service_fees(args)
    return {"error": f"Unknown quotation tool: {name}"}


async def _estimate_quotation(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    venue_name = str(args.get("venue_name", "")).strip()
    duration_h = float(args.get("duration_hours", 4))
    event_type = str(args.get("event_type", "other"))
    attendee_count = int(args.get("attendee_count", 0))
    requested_assets: list[dict[str, Any]] = args.get("requested_assets", [])

    subtotal = Decimal("0")
    breakdown: list[dict[str, Any]] = []

    # Venue line
    if db is not None:
        venues = await list_venues(db, active_only=True)
        venue = next((v for v in venues if venue_name.lower() in v.name.lower()), None)
        if venue:
            venue_total = venue.base_price_per_hour * Decimal(str(duration_h))
            subtotal += venue_total
            breakdown.append({
                "category": "venue",
                "name": f"{venue.name} — {duration_h:.1f}h",
                "qty": 1,
                "unit_price": float(venue.base_price_per_hour),
                "total": float(venue_total),
            })

    # Asset lines
    if db is not None and requested_assets:
        all_assets = await list_assets(db, active_only=True)
        lookup = {a.name.lower(): a for a in all_assets}
        for item in requested_assets:
            asset = lookup.get(item["name"].lower())
            qty = int(item.get("quantity", 1))
            if asset:
                total = asset.unit_price * qty
                subtotal += total
                breakdown.append({
                    "category": "asset",
                    "name": asset.name,
                    "qty": qty,
                    "unit_price": float(asset.unit_price),
                    "total": float(total),
                })
    elif not requested_assets:
        # Auto-estimate chairs + tables from attendee_count
        chair_unit = Decimal("2.00")
        chair_total = chair_unit * attendee_count
        subtotal += chair_total
        breakdown.append({
            "category": "seating",
            "name": "Chair (Standard)",
            "qty": attendee_count,
            "unit_price": float(chair_unit),
            "total": float(chair_total),
        })

    # Service fee lines
    for label, qty, unit in SERVICE_FEES.get(event_type, SERVICE_FEES["other"]):
        total = unit * qty
        subtotal += total
        breakdown.append({
            "category": "service",
            "name": label,
            "qty": qty,
            "unit_price": float(unit),
            "total": float(total),
        })

    tax = (subtotal * Decimal("0.20")).quantize(Decimal("0.01"))
    return {
        "subtotal": float(subtotal),
        "tax_20pct": float(tax),
        "total": float(subtotal + tax),
        "currency": "EUR",
        "breakdown": breakdown,
    }


async def _get_quotation_details(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    try:
        request_id = UUID(str(args.get("request_id", "")))
    except (ValueError, TypeError):
        return {"error": "Invalid request_id UUID."}

    quotation = await db.scalar(
        select(Quotation)
        .where(Quotation.event_request_id == request_id)
        .order_by(desc(Quotation.created_at))
    )
    if not quotation:
        return {"error": f"No quotation found for request {request_id}."}

    return {
        "quotation_id": str(quotation.id),
        "status": quotation.status,
        "subtotal": float(quotation.subtotal),
        "tax": float(quotation.tax),
        "total": float(quotation.total),
        "currency": quotation.currency,
        "line_items": quotation.line_items,
        "notes": quotation.notes,
        "valid_until": quotation.valid_until.isoformat() if quotation.valid_until else None,
        "created_at": quotation.created_at.isoformat(),
    }


def _list_service_fees(args: dict[str, Any]) -> dict[str, Any]:
    event_type = str(args.get("event_type", "other"))
    fees = SERVICE_FEES.get(event_type, SERVICE_FEES["other"])
    return {
        "event_type": event_type,
        "service_fees": [
            {"label": label, "quantity": qty, "unit_price_eur": float(unit)}
            for label, qty, unit in fees
        ],
        "note": "Quantities are default units (e.g. number of staff or labour hours).",
    }
```

### Phase Gate

```bash
python -c "from app.ai.tools.quotation_tools import QUOTATION_TOOLS; print(len(QUOTATION_TOOLS), 'quotation tools loaded')"
# Expected: 3 quotation tools loaded
```

---

## Phase A6: Task Tool Module

### Goal

Five task tools that let the Operational Planning Agent read task templates,
check existing tasks, look up available staff, and batch-create tasks in the DB.

### `backend/app/ai/tools/task_tools.py`

```python
"""
Task-domain tools for the SpaceFlow agent system.

Tools:
  1. get_staff_list              — available staff members for task assignment
  2. get_task_templates          — standard task list template for an event type
  3. create_tasks_batch          — bulk-create tasks in the database
  4. get_existing_tasks          — list current tasks for a request (avoid duplicates)
  5. get_venue_setup_requirements — physical setup requirements for venue + event type
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, User, EventRequest
from app.services import TASK_TEMPLATES, list_tasks

# ── JSON Schemas ─────────────────────────────────────────────────────────────

TASK_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_staff_list",
            "description": (
                "Return all active staff members available for task assignment. "
                "Includes their email (for identification) and full name."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_templates",
            "description": (
                "Return the standard operational task list template for a given "
                "event type. Templates include task title, type (setup/teardown/etc.), "
                "priority, and hour offset relative to event start or end."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "conference", "workshop", "hackathon",
                            "concert", "exhibition", "dinner", "other",
                        ],
                    },
                },
                "required": ["event_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_tasks_batch",
            "description": (
                "Create multiple operational tasks in the database for an approved "
                "event request. Due times are calculated from the event start/end "
                "datetime plus an offset in hours. Negative offsets = before event; "
                "positive = after event. Returns created task IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_request_id": {
                        "type": "string",
                        "description": "UUID of the approved event request.",
                    },
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "task_type": {
                                    "type": "string",
                                    "enum": ["setup", "teardown", "preparation", "logistics", "coordination"],
                                },
                                "priority": {
                                    "type": "integer",
                                    "description": "1=high, 2=medium, 3=low",
                                    "enum": [1, 2, 3],
                                },
                                "due_offset_hours": {
                                    "type": "number",
                                    "description": "Hours relative to event start (negative = before). For teardown tasks use offset_from_end_hours instead and set anchor='end'.",
                                },
                                "anchor": {
                                    "type": "string",
                                    "enum": ["start", "end"],
                                    "description": "Whether offset is from event start or event end.",
                                    "default": "start",
                                },
                                "assignee_email": {
                                    "type": "string",
                                    "description": "Optional staff email for assignment.",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional additional notes for the task.",
                                },
                            },
                            "required": ["title", "task_type", "priority", "due_offset_hours"],
                        },
                    },
                },
                "required": ["event_request_id", "tasks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_existing_tasks",
            "description": (
                "Return the current task list for an event request. "
                "Call this before create_tasks_batch to avoid creating duplicates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_venue_setup_requirements",
            "description": (
                "Return the standard physical setup requirements for a venue and "
                "event type combination: expected furniture counts, AV needs, "
                "staffing estimate, and recommended buffer times."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {"type": "string"},
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "conference", "workshop", "hackathon",
                            "concert", "exhibition", "dinner", "other",
                        ],
                    },
                    "attendee_count": {"type": "integer"},
                },
                "required": ["venue_name", "event_type", "attendee_count"],
            },
        },
    },
]

# ── Executor ─────────────────────────────────────────────────────────────────

async def execute_task_tool(
    name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    db: AsyncSession | None,
) -> dict[str, Any]:
    if name == "get_staff_list":
        return await _get_staff_list(db)
    if name == "get_task_templates":
        return _get_task_templates(args)
    if name == "create_tasks_batch":
        return await _create_tasks_batch(args, db)
    if name == "get_existing_tasks":
        return await _get_existing_tasks(args, db)
    if name == "get_venue_setup_requirements":
        return _get_venue_setup_requirements(args)
    return {"error": f"Unknown task tool: {name}"}


async def _get_staff_list(db: AsyncSession | None) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    staff = list(
        (await db.scalars(
            select(User).where(User.role == "staff", User.is_active.is_(True))
        )).all()
    )
    return {
        "staff": [
            {"id": str(u.id), "full_name": u.full_name, "email": u.email}
            for u in staff
        ],
        "count": len(staff),
    }


def _get_task_templates(args: dict[str, Any]) -> dict[str, Any]:
    event_type = str(args.get("event_type", "other"))
    templates = TASK_TEMPLATES.get(event_type, TASK_TEMPLATES.get("other", []))
    return {
        "event_type": event_type,
        "templates": templates,
        "count": len(templates),
        "note": (
            "offset_from_start_hours: negative = before event start. "
            "offset_from_end_hours: positive = after event end."
        ),
    }


async def _create_tasks_batch(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}

    try:
        request_id = UUID(str(args["event_request_id"]))
    except (ValueError, KeyError, TypeError):
        return {"error": "Invalid or missing event_request_id."}

    req: EventRequest | None = await db.get(EventRequest, request_id)
    if not req:
        return {"error": f"Event request {request_id} not found."}

    # Build start and end datetimes for the event
    from datetime import date, time, timezone
    def _combine(d: date, t: time) -> datetime:
        return datetime.combine(d, t).replace(tzinfo=timezone.utc)

    event_start = _combine(req.requested_date, req.start_time)
    event_end = _combine(req.requested_date, req.end_time)

    # Build staff lookup by email
    staff_lookup: dict[str, UUID] = {}
    all_staff = list(
        (await db.scalars(select(User).where(User.role.in_(["staff", "admin"])))).all()
    )
    for u in all_staff:
        staff_lookup[u.email.lower()] = u.id

    tasks_input: list[dict[str, Any]] = args.get("tasks", [])
    created_ids: list[str] = []
    errors: list[str] = []

    for task_data in tasks_input:
        try:
            title = str(task_data["title"])
            task_type = str(task_data.get("task_type", "coordination"))
            priority = int(task_data.get("priority", 2))
            offset_h = float(task_data.get("due_offset_hours", 0))
            anchor = str(task_data.get("anchor", "start"))
            base_dt = event_end if anchor == "end" else event_start
            due_at = base_dt + timedelta(hours=offset_h)
            assignee_id: UUID | None = None
            email = str(task_data.get("assignee_email", "") or "").lower().strip()
            if email:
                assignee_id = staff_lookup.get(email)
            task = Task(
                event_request_id=request_id,
                title=title,
                description=str(task_data.get("description", "") or ""),
                task_type=task_type,
                priority=priority,
                due_at=due_at,
                assigned_to=assignee_id,
                ai_generated=True,
                status="pending",
            )
            db.add(task)
            await db.flush()
            created_ids.append(str(task.id))
        except Exception as exc:
            errors.append(f"Task '{task_data.get('title', '?')}': {exc}")

    await db.commit()
    return {
        "tasks_created": len(created_ids),
        "task_ids": created_ids,
        "errors": errors,
    }


async def _get_existing_tasks(
    args: dict[str, Any], db: AsyncSession | None
) -> dict[str, Any]:
    if db is None:
        return {"error": "Database session not available."}
    try:
        request_id = UUID(str(args["request_id"]))
    except (ValueError, KeyError, TypeError):
        return {"error": "Invalid or missing request_id."}

    tasks = await list_tasks(db, request_id=request_id)
    return {
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "task_type": t.task_type,
                "status": t.status,
                "priority": t.priority,
                "due_at": t.due_at.isoformat(),
                "ai_generated": t.ai_generated,
            }
            for t in tasks
        ],
        "count": len(tasks),
    }


def _get_venue_setup_requirements(args: dict[str, Any]) -> dict[str, Any]:
    event_type = str(args.get("event_type", "other"))
    attendee_count = int(args.get("attendee_count", 20))
    venue_name = str(args.get("venue_name", "venue"))

    chairs = attendee_count
    tables = 0
    av_items: list[str] = []
    staff_count = 2
    setup_buffer_hours = 2.0
    teardown_buffer_hours = 1.5

    if event_type == "conference":
        tables = max(1, attendee_count // 8)
        av_items = ["Microphone (×1)", "TV Display or Projector (×1)", "PA system"]
        staff_count = max(2, attendee_count // 50)
    elif event_type == "workshop":
        tables = max(1, attendee_count // 4)
        av_items = ["Whiteboard (×1–2)", "TV Display (×1)"]
        staff_count = max(2, attendee_count // 30)
    elif event_type == "hackathon":
        tables = max(1, attendee_count // 4)
        av_items = ["Whiteboard (×2)", "Extension leads / power strips per table", "Network switch"]
        staff_count = max(2, attendee_count // 25)
        setup_buffer_hours = 3.0
    elif event_type == "concert":
        chairs = attendee_count
        tables = 0
        av_items = ["PA system", "Microphones (×4+)", "Stage panels", "Lighting rig"]
        staff_count = max(4, attendee_count // 30)
        setup_buffer_hours = 4.0
        teardown_buffer_hours = 3.0
    elif event_type == "exhibition":
        chairs = 0
        tables = min(8, max(2, attendee_count // 10))
        av_items = ["TV Display (×1–2)"]
        staff_count = 3
    elif event_type == "dinner":
        tables = max(1, attendee_count // 6)
        av_items = ["Microphone (×1)"]
        staff_count = max(2, attendee_count // 20)

    return {
        "venue_name": venue_name,
        "event_type": event_type,
        "attendee_count": attendee_count,
        "chairs_required": chairs,
        "tables_required": tables,
        "av_requirements": av_items,
        "recommended_staff_count": staff_count,
        "setup_buffer_hours": setup_buffer_hours,
        "teardown_buffer_hours": teardown_buffer_hours,
        "notes": f"Estimates for {event_type} event with {attendee_count} attendees in {venue_name}.",
    }
```

### Phase Gate

```bash
python -c "from app.ai.tools.task_tools import TASK_TOOLS; print(len(TASK_TOOLS), 'task tools loaded')"
# Expected: 5 task tools loaded
```

---

## Phase A7: Tool Registry

### Goal

Assemble all five tool modules into the unified registry. Define `TOOL_SETS` (which
tools each agent type receives), `EXECUTOR_MAP` (tool name → executor function), and
the public `get_tools_for_agent()` / `execute_tool()` API used by the ReAct engine.

### `backend/app/ai/tools/__init__.py`

```python
"""
SpaceFlow Agent Tool Registry.

TOOL_SETS maps each agent_type to its permitted tool list.
execute_tool() dispatches a tool call by name to the correct executor.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.inventory_tools import INVENTORY_TOOLS, execute_inventory_tool
from app.ai.tools.layout_tools import LAYOUT_TOOLS, execute_layout_tool
from app.ai.tools.quotation_tools import QUOTATION_TOOLS, execute_quotation_tool
from app.ai.tools.task_tools import TASK_TOOLS, execute_task_tool
from app.ai.tools.venue_tools import VENUE_TOOLS, execute_venue_tool

# Which tools each agent type may call
TOOL_SETS: dict[str, list[dict[str, Any]]] = {
    "intake": VENUE_TOOLS + INVENTORY_TOOLS + QUOTATION_TOOLS,
    "room_designer": INVENTORY_TOOLS + LAYOUT_TOOLS,
    "conflict_detector": VENUE_TOOLS + INVENTORY_TOOLS,
    "planner": INVENTORY_TOOLS + TASK_TOOLS,
    "copilot": VENUE_TOOLS + INVENTORY_TOOLS + LAYOUT_TOOLS + QUOTATION_TOOLS + TASK_TOOLS,
}

# tool_name → executor coroutine
_EXECUTOR_MAP: dict[str, Any] = {
    **{t["function"]["name"]: execute_venue_tool for t in VENUE_TOOLS},
    **{t["function"]["name"]: execute_inventory_tool for t in INVENTORY_TOOLS},
    **{t["function"]["name"]: execute_layout_tool for t in LAYOUT_TOOLS},
    **{t["function"]["name"]: execute_quotation_tool for t in QUOTATION_TOOLS},
    **{t["function"]["name"]: execute_task_tool for t in TASK_TOOLS},
}

ALL_TOOL_NAMES: list[str] = list(_EXECUTOR_MAP.keys())


def get_tools_for_agent(agent_type: str) -> list[dict[str, Any]]:
    """Return the tool schema list for the given agent type."""
    return TOOL_SETS.get(agent_type, [])


async def execute_tool(
    name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    db: AsyncSession | None,
) -> dict[str, Any]:
    """Dispatch a tool call by name to its executor."""
    executor = _EXECUTOR_MAP.get(name)
    if executor is None:
        return {"error": f"Unknown tool: '{name}'. Available: {ALL_TOOL_NAMES}"}
    return await executor(name, args, context, db)
```

### Phase Gate

```bash
python -c "
from app.ai.tools import get_tools_for_agent, execute_tool, ALL_TOOL_NAMES
print('Total tools:', len(ALL_TOOL_NAMES))
print('Copilot tools:', len(get_tools_for_agent('copilot')))
print('Room designer tools:', len(get_tools_for_agent('room_designer')))
"
# Expected:
# Total tools: 21
# Copilot tools: 21
# Room designer tools: 9
```

---

## Phase A8: System Prompts

### Goal

Define specific, grounded system prompts for all five agent types. Prompts encode
the operational context (Pyramid of Tirana, available rooms, event types), the
expected reasoning style, and the precise sequence of tool calls for each agent.

### `backend/app/ai/prompts.py`

```python
"""
System prompts for SpaceFlow's five AI agent types.
Each prompt encodes domain context, reasoning style, and tool-calling strategy.
"""
from __future__ import annotations

from typing import Any


def get_system_prompt(agent_type: str, context: dict[str, Any]) -> str:
    """Return the appropriate system prompt for the given agent type and context."""
    if agent_type == "intake":
        return _intake_prompt(context)
    if agent_type == "room_designer":
        return _room_designer_prompt(context)
    if agent_type == "conflict_detector":
        return _conflict_detector_prompt(context)
    if agent_type == "planner":
        return _planner_prompt(context)
    return _copilot_prompt(context)


def _intake_prompt(context: dict[str, Any]) -> str:
    return """\
You are SpaceFlow's Event Intake Specialist for the Pyramid of Tirana.
When an event request is submitted, your job is to analyse it fully and generate a structured proposal.

The Pyramid of Tirana has four bookable spaces:
- Blue Room   (Floor 0,  capacity up to ~40,  small-medium events)
- Orange Room (Floor 0,  capacity up to ~80,  medium events, best AV setup)
- Green Room  (Floor -1, capacity up to ~60,  workshops and breakout sessions)
- Yellow Room (Floor -1, capacity up to ~30,  small meetings, intimate events)

Your task sequence for every request:
1. Call suggest_best_venue with the event type, attendee count, and any stated preferences.
2. Call check_venue_availability for the top recommended venue on the requested date.
3. Call check_asset_availability with the assets the event type typically requires.
4. Call estimate_quotation using the recommended venue, duration, event type, and asset list.
5. Synthesise everything into a clear, concise proposal with: recommended venue, availability status, asset fulfillment status, cost estimate, and any flags or concerns.

Rules:
- Be decisive. If the best venue is available, say so clearly.
- Flag asset shortfalls immediately with specific numbers (e.g. "We have 80 chairs; you need 120 — shortfall of 40").
- Mention setup and teardown buffers if they create availability constraints.
- Keep your final summary to under 150 words; use bullet points.
- Do not ask clarifying questions — reason from the data you have.
"""


def _room_designer_prompt(context: dict[str, Any]) -> str:
    venue_name = context.get("venue_name", "the specified room")
    return f"""\
You are SpaceFlow's 3D Room Design Agent for the Pyramid of Tirana.
You configure rooms in the live Three.js 3D visualization based on natural language descriptions.

Target venue: {venue_name}

Available Three.js room IDs:
- "blue-box"       → Blue Room   (w=5.2m, d=3.8m, h=2.6m)
- "orange-box"     → Orange Room (w=8.0m, d=4.2m, h=3.0m)
- "lime-green-box" → Green Room  (w=5.5m, d=3.2m, h=2.6m)
- "dark-green-box" → Yellow Room (w=4.2m, d=4.0m, h=2.6m)

Available furniture model keys: simple_chair, simple_table, wall_flat_tv, whiteboard,
microphone_stand, office_monitor, speaker

Your task sequence for every design request:
1. Call get_venue_dimensions to confirm the room's exact dimensions and Three.js room ID.
2. Call get_available_furniture (with event dates if provided) to know real stock counts.
3. Call generate_room_layout with venue_name, event_type, attendee_count, and preferences extracted from the user's prompt.
4. Call push_layout_to_3d with the returned items array, the three_d_room_id, and a descriptive layout_name.
5. Reply with a concise description of what was placed and any limitations encountered.

Rules:
- Always push the layout — never just generate it without pushing.
- Mention exact counts placed (e.g. "32 chairs, 8 tables, 1 TV screen").
- If inventory is insufficient, state the shortfall clearly and describe what was placed instead.
- Do not invent furniture keys — use only the catalog keys listed above.
"""


def _conflict_detector_prompt(context: dict[str, Any]) -> str:
    request_id = context.get("request_id", "the specified request")
    return f"""\
You are SpaceFlow's Conflict Detection Specialist for the Pyramid of Tirana.
Your job is to perform a thorough operational conflict analysis for event request {request_id}.

Conflict categories you must check:
1. Venue double-booking — same venue, overlapping datetime (including setup/teardown buffers)
2. Asset over-reservation — requested quantities exceed available pool for any asset
3. Shared-resource pressure — two large simultaneous events that strain total asset supply
4. Setup/teardown collision — event A's teardown buffer overlaps event B's setup window

Your task sequence:
1. Call list_available_venues for the event's date and time window to see what else is running.
2. Call check_venue_availability for the specific venue assigned to this request.
3. Call check_asset_availability for the assets this event requires.
4. Synthesise into a conflict report with: severity (blocking / warning), description, and concrete resolution suggestion for each issue found.

Rules:
- "blocking" conflicts must be resolved before approval can proceed.
- "warning" conflicts should be flagged but do not block approval.
- Always give a specific resolution suggestion (e.g. "Move to 14:00–18:00", "Use Green Room instead", "Reduce chair allocation to 80").
- If no conflicts are found, state clearly: "No blocking conflicts detected."
"""


def _planner_prompt(context: dict[str, Any]) -> str:
    request_id = context.get("request_id", "the specified request")
    return f"""\
You are SpaceFlow's Operational Planning Agent for the Pyramid of Tirana.
Your job is to generate a complete, time-ordered task list for event request {request_id}.

Your task sequence:
1. Call get_existing_tasks to see what tasks already exist (avoid duplicating them).
2. Call get_staff_list to find available staff for assignment.
3. Call get_task_templates for the event type to use as a base structure.
4. Call get_venue_setup_requirements to understand the physical needs.
5. Call create_tasks_batch with the full task list — customised to the specific event's attendee count, venue, and requirements.
6. Summarise what was created: counts by type, key deadlines, and who was assigned what.

Rules:
- Always distinguish tasks anchored to event start (use anchor: "start") vs event end (anchor: "end").
- Teardown tasks use positive offsets with anchor: "end".
- Preparation tasks use large negative offsets (e.g. -72h, -48h) with anchor: "start".
- Assign staff only to tasks where a staff member exists; leave assignee_email blank otherwise.
- Do not create tasks that already exist in get_existing_tasks output.
- Target: 8–15 tasks for a standard event. More for concerts and large conferences.
"""


def _copilot_prompt(context: dict[str, Any]) -> str:
    return """\
You are SpaceFlow's operations copilot for the Pyramid of Tirana, assisting admin staff.
You have access to all tools: venues, inventory, room layouts, quotations, and tasks.

How to respond:
- For questions about availability: call list_available_venues or check_venue_availability.
- For inventory questions: call list_assets or check_asset_availability.
- For cost estimates: call estimate_quotation.
- For room design requests: use get_venue_dimensions → get_available_furniture → generate_room_layout → push_layout_to_3d.
- For task questions: call get_existing_tasks or get_task_templates.
- For general requests without a specific context: answer concisely from your knowledge and offer to run a specific check.

Tone: professional, concise, practical. No unnecessary filler. When you retrieve data, cite
the numbers directly (e.g. "The Orange Room has 3 available slots on July 15th: 08:00–12:00,
14:00–18:00, and 19:00–22:00."). Always act rather than ask if you have enough information.
"""
```

### Phase Gate

```bash
python -c "
from app.ai.prompts import get_system_prompt
for t in ['intake','room_designer','conflict_detector','planner','copilot']:
    p = get_system_prompt(t, {})
    print(f'{t}: {len(p)} chars')
"
# Expected: each agent type prints a character count > 200
```

---

## Phase A9: ReAct Agent Engine

### Goal

Replace the `_maybe_llm_rewrite()` single-shot approach with a true multi-turn
ReAct loop. The engine sends messages and tools to OpenRouter, receives tool calls,
executes them against the real database, appends results to the context, and
continues until the model produces a final text response or 10 iterations elapse.
Falls back to `_legacy.py` when no API key is present.

### `backend/app/ai/agent.py`

```python
"""
SpaceFlow ReAct Agent Engine.

Implements a multi-turn tool-calling loop compatible with OpenRouter's
OpenAI-format chat completions API.

Flow:
  1. Build messages: [system_prompt, ...history, user_message]
  2. POST to OpenRouter with tools enabled
  3. If response contains tool_calls: execute each, append results, loop
  4. If response is text: return it as the final answer
  5. Cap at MAX_ITERATIONS; fall back to legacy engine on any unrecoverable error
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.ai.prompts import get_system_prompt
from app.ai.tools import execute_tool, get_tools_for_agent
from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ITERATIONS = 10
HISTORY_WINDOW = 20   # keep last N messages to avoid exceeding context window


async def run_agent_react(
    agent_type: str,
    user_message: str,
    context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """
    Full ReAct loop for the given agent_type.
    Returns {"response": str, "tool_calls_made": list, "final_context": dict}.
    """
    system_prompt = get_system_prompt(agent_type, context)
    tools = get_tools_for_agent(agent_type)

    # Build initial message array
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history[-HISTORY_WINDOW:])
    messages.append({"role": "user", "content": user_message})

    # Attach the current user message to context so tool executors can reference it
    context = {**context, "user_message": user_message}

    tool_calls_made: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for iteration in range(MAX_ITERATIONS):
            payload: dict[str, Any] = {
                "model": settings.AI_MODEL,
                "messages": messages,
                "temperature": settings.AI_TEMPERATURE,
                "max_tokens": settings.AI_MAX_TOKENS,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            try:
                resp = await client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "HTTP-Referer": "http://localhost:8080",
                        "X-Title": "SpaceFlow",
                    },
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning("OpenRouter HTTP %s on iteration %d", exc.response.status_code, iteration)
                return {
                    "response": "The AI service is temporarily unavailable. Please try again shortly.",
                    "tool_calls_made": tool_calls_made,
                    "final_context": context,
                    "error": str(exc),
                }
            except httpx.TimeoutException:
                logger.warning("OpenRouter timeout on iteration %d", iteration)
                return {
                    "response": "The AI service timed out. Please try again.",
                    "tool_calls_made": tool_calls_made,
                    "final_context": context,
                    "error": "timeout",
                }

            data = resp.json()
            if not data.get("choices"):
                logger.warning("OpenRouter returned no choices: %s", data)
                break

            choice = data["choices"][0]
            message = choice["message"]
            finish_reason = choice.get("finish_reason", "stop")

            if finish_reason == "tool_calls" and message.get("tool_calls"):
                # Append the assistant message with its tool_calls
                messages.append(message)
                tool_results: list[dict[str, Any]] = []

                for tc in message["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"] or "{}")
                    except json.JSONDecodeError:
                        fn_args = {}

                    result = await execute_tool(fn_name, fn_args, context, db)
                    tool_calls_made.append({"tool": fn_name, "args": fn_args, "result": result})
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result, default=str),
                    })

                messages.extend(tool_results)
                # Continue loop with updated messages

            else:
                # Terminal text response
                content = message.get("content") or ""
                if isinstance(content, list):
                    # Some models return content as list of parts
                    content = "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    ).strip()
                return {
                    "response": content or "(Agent produced no text response.)",
                    "tool_calls_made": tool_calls_made,
                    "final_context": context,
                }

    return {
        "response": "Agent reached the maximum number of reasoning steps without a final answer.",
        "tool_calls_made": tool_calls_made,
        "final_context": context,
    }
```

### Phase Gate

```bash
python -c "from app.ai.agent import run_agent_react; print('ReAct engine importable')"
# Expected: ReAct engine importable
```

---

## Phase A10: Updated Public API

### Goal

Replace the A1 shim in `app/ai/__init__.py` with the full dispatcher: try the ReAct
engine when `OPENROUTER_API_KEY` is set, fall back to `_legacy.py` transparently
when it is not (or when the LLM call fails).

### `backend/app/ai/__init__.py` (final version)

```python
"""SpaceFlow Agentic AI — public API."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


async def run_agent(
    agent_type: str,
    user_message: str,
    context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Primary public entry point for all agent calls.

    Routing logic:
    - If OPENROUTER_API_KEY is set: use the full ReAct engine (agent.py).
    - Otherwise: use the deterministic legacy engine (_legacy.py).
    - If the ReAct engine returns an "error" key, fall back to legacy automatically.
    """
    if settings.OPENROUTER_API_KEY:
        from app.ai.agent import run_agent_react
        result = await run_agent_react(
            agent_type=agent_type,
            user_message=user_message,
            context=context,
            conversation_history=conversation_history,
            db=db,
        )
        # If engine hard-failed, fall through to legacy
        if "error" not in result:
            return result
        logger.warning(
            "ReAct engine error for agent_type=%s: %s. Falling back to legacy.",
            agent_type,
            result.get("error"),
        )

    from app.ai._legacy import run_agent_legacy
    return await run_agent_legacy(
        agent_type=agent_type,
        user_message=user_message,
        context=context,
        conversation_history=conversation_history,
        db=db,
    )
```

### Phase Gate

```bash
python -c "
import asyncio, os
# Test without API key — should use legacy
os.environ.pop('OPENROUTER_API_KEY', None)
from app.ai import run_agent
print('Public API importable. Engine routing ready.')
"
# Expected: Public API importable. Engine routing ready.
```

---

## Phase A11: New Pydantic Schemas

### Goal

Add schemas for the six new endpoints introduced in Phase A12. These extend
`backend/app/schemas/__init__.py`.

### Additions to `backend/app/schemas/__init__.py`

Add the following classes to the end of the existing file:

```python
# ── AI Conversation Schemas ──────────────────────────────────────────────────

class ConversationMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str


class ConversationSummary(ORMModel):
    id: UUID
    agent_type: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_with_count(cls, obj: Any) -> "ConversationSummary":
        return cls(
            id=obj.id,
            agent_type=obj.agent_type,
            message_count=len(obj.messages),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class ConversationDetail(ORMModel):
    id: UUID
    agent_type: str
    messages: list[dict[str, Any]]
    context_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AIProposalResponse(BaseModel):
    request_id: UUID
    has_proposal: bool
    proposal: dict[str, Any] | None = None
    generated_at: datetime | None = None


class AIIntakeResponse(BaseModel):
    request_id: UUID
    response: str
    tool_calls_made: list[dict[str, Any]]
    recommended_venue: dict[str, Any] | None = None
    estimated_total_eur: float | None = None


class AIStreamChunk(BaseModel):
    chunk: str
    done: bool = False
    tool_call: dict[str, Any] | None = None
```

---

## Phase A12: Extended Router & Endpoints

### Goal

Add six new endpoints to `backend/app/routers/ai.py` while keeping all existing
four endpoints intact. The new endpoints cover conversation management, manual
intake trigger, AI proposal retrieval, and streaming chat.

### New API surface

```
GET    /api/v1/ai/conversations              → list current user's conversations
GET    /api/v1/ai/conversations/{id}         → get conversation with full messages
DELETE /api/v1/ai/conversations/{id}         → delete a conversation
POST   /api/v1/ai/intake/{request_id}        → manually trigger intake agent
GET    /api/v1/ai/proposal/{request_id}      → retrieve stored AI proposal for a request
POST   /api/v1/ai/stream                     → streaming SSE chat (line-delimited JSON)
```

### Complete `backend/app/routers/ai.py` (replaces existing file)

```python
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import run_agent
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_staff
from app.models import AiConversation, EventRequest, User
from app.schemas import (
    AIChatRequest,
    AIChatResponse,
    AIDesignRoomRequest,
    AIDetectConflictsRequest,
    AIIntakeResponse,
    AIProposalResponse,
    ConversationDetail,
    ConversationSummary,
)

router = APIRouter()


# ── Existing endpoints (unchanged logic, kept for backward compatibility) ────

@router.post("/chat", response_model=AIChatResponse)
async def route_ai_chat(
    data: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIChatResponse:
    conversation = None
    history: list[dict] = []
    if data.conversation_id:
        conversation = await db.get(AiConversation, data.conversation_id)
        if conversation and conversation.user_id == current_user.id:
            history = conversation.messages

    result = await run_agent(
        agent_type=data.agent_type,
        user_message=data.message,
        context={**data.context, "user_id": str(current_user.id)},
        conversation_history=history,
        db=db,
    )

    new_messages = history + [
        {"role": "user", "content": data.message},
        {"role": "assistant", "content": result["response"]},
    ]

    if conversation:
        conversation.messages = new_messages
        conversation.context_json = {**conversation.context_json, **data.context}
    else:
        conversation = AiConversation(
            user_id=current_user.id,
            agent_type=data.agent_type,
            messages=new_messages,
            context_json=data.context,
        )
        db.add(conversation)

    await db.commit()
    await db.refresh(conversation)

    return AIChatResponse(
        response=result["response"],
        tool_calls_made=result["tool_calls_made"],
        conversation_id=conversation.id,
    )


@router.post("/design-room")
async def route_design_room(
    data: AIDesignRoomRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    result = await run_agent(
        agent_type="room_designer",
        user_message=data.prompt,
        context={
            "venue_name": data.venue_name,
            "event_request_id": str(data.event_request_id) if data.event_request_id else None,
            "event_date_start": data.event_date_start.isoformat() if data.event_date_start else None,
            "event_date_end": data.event_date_end.isoformat() if data.event_date_end else None,
        },
        db=db,
    )
    return {
        "message": result["response"],
        "tool_calls_made": result["tool_calls_made"],
        "final_context": result["final_context"],
    }


@router.post("/detect-conflicts")
async def route_detect_conflicts(
    data: AIDetectConflictsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    result = await run_agent(
        agent_type="conflict_detector",
        user_message="Perform a full conflict analysis for this event request.",
        context={"request_id": str(data.request_id)},
        db=db,
    )
    return {
        "message": result["response"],
        "tool_calls_made": result["tool_calls_made"],
        "final_context": result["final_context"],
    }


@router.post("/generate-tasks/{request_id}")
async def route_ai_generate_tasks(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    result = await run_agent(
        agent_type="planner",
        user_message="Generate a complete operational task plan for this event.",
        context={"request_id": str(request_id)},
        db=db,
    )
    return {
        "message": result["response"],
        "tool_calls_made": result["tool_calls_made"],
        "final_context": result["final_context"],
    }


# ── New endpoints ─────────────────────────────────────────────────────────────

@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
) -> list[ConversationSummary]:
    stmt = (
        select(AiConversation)
        .where(AiConversation.user_id == current_user.id)
        .order_by(desc(AiConversation.updated_at))
        .limit(limit)
        .offset(offset)
    )
    conversations = list((await db.scalars(stmt)).all())
    return [ConversationSummary.from_orm_with_count(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetail:
    conv = await db.get(AiConversation, conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return ConversationDetail.model_validate(conv)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    conv = await db.get(AiConversation, conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    await db.delete(conv)
    await db.commit()


@router.post("/intake/{request_id}", response_model=AIIntakeResponse)
async def trigger_intake_agent(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> AIIntakeResponse:
    """
    Manually re-trigger the intake agent for a submitted request.
    Stores the result in event_request.ai_proposal_json.
    """
    req: EventRequest | None = await db.get(EventRequest, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

    context = {
        "request_id": str(request_id),
        "event_type": req.event_type,
        "attendee_count": req.attendee_count,
        "requested_date": str(req.requested_date),
        "start_time": str(req.start_time),
        "end_time": str(req.end_time),
        "special_requirements": req.special_requirements or "",
    }

    result = await run_agent(
        agent_type="intake",
        user_message=(
            f"Analyse this {req.event_type} event request for {req.attendee_count} attendees "
            f"on {req.requested_date} from {req.start_time} to {req.end_time}. "
            f"Title: {req.title}. Special requirements: {req.special_requirements or 'none'}."
        ),
        context=context,
        db=db,
    )

    # Persist the proposal in the request record
    proposal_data = {
        "agent_response": result["response"],
        "tool_calls": result["tool_calls_made"],
        "final_context": result["final_context"],
    }
    req.ai_proposal_json = proposal_data
    await db.commit()

    estimated_total: float | None = None
    final_ctx = result.get("final_context", {})
    if "estimate" in final_ctx:
        estimated_total = final_ctx["estimate"].get("total")

    return AIIntakeResponse(
        request_id=request_id,
        response=result["response"],
        tool_calls_made=result["tool_calls_made"],
        recommended_venue=final_ctx.get("recommended_venue"),
        estimated_total_eur=estimated_total,
    )


@router.get("/proposal/{request_id}", response_model=AIProposalResponse)
async def get_ai_proposal(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> AIProposalResponse:
    """Return the stored AI intake proposal for a request."""
    req: EventRequest | None = await db.get(EventRequest, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

    if not req.ai_proposal_json:
        return AIProposalResponse(request_id=request_id, has_proposal=False)

    return AIProposalResponse(
        request_id=request_id,
        has_proposal=True,
        proposal=req.ai_proposal_json,
        generated_at=req.updated_at,
    )


@router.post("/stream")
async def stream_ai_chat(
    data: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Streaming chat endpoint. Returns Server-Sent Events (line-delimited JSON).
    Each line: {"chunk": "...", "done": false} or {"chunk": "", "done": true, "conversation_id": "uuid"}.

    When OPENROUTER_API_KEY is absent, falls back to a single non-streamed response
    wrapped in the same line-delimited format.
    """
    history: list[dict] = []
    conversation: AiConversation | None = None
    if data.conversation_id:
        conversation = await db.get(AiConversation, data.conversation_id)
        if conversation and conversation.user_id == current_user.id:
            history = conversation.messages

    async def _generate() -> AsyncIterator[str]:
        if not settings.OPENROUTER_API_KEY:
            # Non-streaming fallback
            result = await run_agent(
                agent_type=data.agent_type,
                user_message=data.message,
                context={**data.context, "user_id": str(current_user.id)},
                conversation_history=history,
                db=db,
            )
            # Simulate streaming by yielding the full response in one chunk
            yield json.dumps({"chunk": result["response"], "done": False}) + "\n"
            yield json.dumps({"chunk": "", "done": True}) + "\n"
            return

        import httpx
        from app.ai.prompts import get_system_prompt
        from app.ai.tools import get_tools_for_agent

        system_prompt = get_system_prompt(data.agent_type, data.context)
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-20:])
        messages.append({"role": "user", "content": data.message})

        payload = {
            "model": settings.AI_MODEL,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
            "stream": True,
        }
        tools = get_tools_for_agent(data.agent_type)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        full_response = ""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": "http://localhost:8080",
                    "X-Title": "SpaceFlow",
                },
                json=payload,
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw.strip() == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(raw)
                        delta = chunk_data["choices"][0].get("delta", {})
                        chunk_text = delta.get("content") or ""
                        if chunk_text:
                            full_response += chunk_text
                            yield json.dumps({"chunk": chunk_text, "done": False}) + "\n"
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        # Persist conversation
        nonlocal conversation
        new_messages = history + [
            {"role": "user", "content": data.message},
            {"role": "assistant", "content": full_response},
        ]
        if conversation:
            conversation.messages = new_messages
        else:
            conversation = AiConversation(
                user_id=current_user.id,
                agent_type=data.agent_type,
                messages=new_messages,
                context_json=data.context,
            )
            db.add(conversation)
        await db.commit()
        if conversation:
            await db.refresh(conversation)

        yield json.dumps({"chunk": "", "done": True, "conversation_id": str(conversation.id) if conversation else None}) + "\n"

    return StreamingResponse(
        _generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### Endpoints Produced

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/ai/chat` | user | Multi-turn chat (existing, now uses ReAct) |
| POST | `/api/v1/ai/design-room` | staff | Room design agent (existing, now uses ReAct) |
| POST | `/api/v1/ai/detect-conflicts` | staff | Conflict detection (existing, now uses ReAct) |
| POST | `/api/v1/ai/generate-tasks/{id}` | staff | Task generation (existing, now uses ReAct) |
| GET  | `/api/v1/ai/conversations` | user | List user's conversations |
| GET  | `/api/v1/ai/conversations/{id}` | user | Get conversation detail |
| DELETE | `/api/v1/ai/conversations/{id}` | user | Delete conversation |
| POST | `/api/v1/ai/intake/{id}` | staff | Manually trigger intake agent |
| GET  | `/api/v1/ai/proposal/{id}` | staff | Get stored AI proposal |
| POST | `/api/v1/ai/stream` | user | Streaming SSE chat |

---

## Phase A13: Background Task Integration

### Goal

Wire the intake agent into the request submission flow so it runs automatically
when a client submits a new event request. Also ensure the conflict detector
runs automatically during intake. Both run as FastAPI `BackgroundTasks` — they
do not block the HTTP response.

### Changes to `backend/app/routers/requests.py`

The existing `create_request` endpoint already has a background task call. Verify
and ensure the following pattern is present (add if missing):

```python
# In app/routers/requests.py — inside create_request endpoint

from fastapi import BackgroundTasks

@router.post("", status_code=201, response_model=EventRequestSummary)
async def create_request(
    data: EventRequestCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventRequestSummary:
    req = await create_event_request(data, current_user.id, db)
    # Trigger AI intake in background — fires after response is sent
    background_tasks.add_task(_run_intake_background, req.id)
    return build_request_summary(req)


async def _run_intake_background(request_id: UUID) -> None:
    """
    Background coroutine that runs the intake agent after a request is submitted.
    Uses its own database session because the request session is already closed.
    """
    from app.database import AsyncSessionLocal
    from app.ai import run_agent
    from app.models import EventRequest

    async with AsyncSessionLocal() as db:
        try:
            req: EventRequest | None = await db.get(EventRequest, request_id)
            if not req:
                return
            context = {
                "request_id": str(request_id),
                "event_type": req.event_type,
                "attendee_count": req.attendee_count,
                "requested_date": str(req.requested_date),
                "start_time": str(req.start_time),
                "end_time": str(req.end_time),
                "special_requirements": req.special_requirements or "",
            }
            result = await run_agent(
                agent_type="intake",
                user_message=(
                    f"Analyse this {req.event_type} event request titled '{req.title}' "
                    f"for {req.attendee_count} attendees on {req.requested_date}."
                ),
                context=context,
                db=db,
            )
            req.ai_proposal_json = {
                "agent_response": result["response"],
                "tool_calls": result["tool_calls_made"],
                "final_context": result["final_context"],
            }
            await db.commit()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Background intake agent failed for request %s: %s", request_id, exc
            )
```

**Important note on the background session**: The background task runs outside the
HTTP request lifecycle. It opens its own `AsyncSessionLocal` session and must commit
and close it explicitly. The `async with AsyncSessionLocal() as db:` pattern handles
this correctly.

---

## Verification Checklist (Full Suite)

Run these against the running backend after implementation is complete.

### A — Module Structure

```bash
# All 10 new/modified AI modules import cleanly
python -c "
from app.ai import run_agent
from app.ai.agent import run_agent_react
from app.ai.prompts import get_system_prompt
from app.ai._legacy import run_agent_legacy
from app.ai.tools import get_tools_for_agent, execute_tool, ALL_TOOL_NAMES
from app.ai.tools.venue_tools import VENUE_TOOLS
from app.ai.tools.inventory_tools import INVENTORY_TOOLS
from app.ai.tools.layout_tools import LAYOUT_TOOLS
from app.ai.tools.quotation_tools import QUOTATION_TOOLS
from app.ai.tools.task_tools import TASK_TOOLS
print('All AI modules: OK')
print('Total registered tools:', len(ALL_TOOL_NAMES))
"
# Expected: All AI modules: OK  /  Total registered tools: 21
```

### B — Tool Registry Counts

```bash
python -c "
from app.ai.tools import TOOL_SETS
for agent, tools in TOOL_SETS.items():
    print(f'{agent}: {len(tools)} tools')
"
# Expected:
# intake: 11 tools
# room_designer: 9 tools
# conflict_detector: 8 tools
# planner: 9 tools
# copilot: 21 tools
```

### C — Legacy Fallback (no API key)

```bash
python -c "
import asyncio, os
os.environ['OPENROUTER_API_KEY'] = ''
# Re-import to pick up empty key
import importlib
import app.config, app.ai
importlib.reload(app.config)
# Should fall back to legacy without crashing
print('Legacy fallback path: available')
"
```

### D — Live Endpoint Smoke Tests

```bash
# 1. Chat endpoint (requires running server + valid auth token)
TOKEN="<your-jwt>"
curl -s -X POST http://localhost:8080/api/v1/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What venues are available?", "agent_type": "copilot", "context": {}}' \
  | python -m json.tool | grep response

# Expected: a non-empty "response" field

# 2. Conversation list
curl -s http://localhost:8080/api/v1/ai/conversations \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Expected: JSON array (may be empty if no conversations yet)

# 3. Room design
curl -s -X POST http://localhost:8080/api/v1/ai/design-room \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"venue_name":"Blue Room","prompt":"Set up for a 20-person workshop with tables and whiteboard"}' \
  | python -m json.tool | grep message

# Expected: message confirming items placed

# 4. Streaming chat
curl -s -N -X POST http://localhost:8080/api/v1/ai/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, what can you help me with?","agent_type":"copilot","context":{}}' 

# Expected: multiple {"chunk":"...","done":false} lines followed by {"chunk":"","done":true,...}
```

### E — WebSocket Layout Push

```bash
# With the 3D app open in browser at http://localhost:3000,
# trigger a room design from the admin side and confirm the
# Three.js visualization updates in real time.

# Verify WebSocket channels have connections
curl -s http://localhost:8080/ws-status | python -m json.tool
# Expected: {"channels": {"3d-bridge": N, "admin": M}}
```

---

## API Contract Reference for Frontend

### Chat

```
POST /api/v1/ai/chat
Body:  {message, agent_type, context, conversation_id?}
→     {response, tool_calls_made, conversation_id}
```

### Stream

```
POST /api/v1/ai/stream
Body:  {message, agent_type, context, conversation_id?}
→     NDJSON stream of {"chunk": str, "done": bool, "conversation_id"?: str}
```

### Room Design

```
POST /api/v1/ai/design-room
Body:  {venue_name, prompt, event_request_id?, event_date_start?, event_date_end?}
→     {message, tool_calls_made, final_context}
       final_context includes: three_d_room_id, layout_id, item_count
```

### Intake

```
POST /api/v1/ai/intake/{request_id}
→     {request_id, response, tool_calls_made, recommended_venue?, estimated_total_eur?}
```

### Proposal

```
GET /api/v1/ai/proposal/{request_id}
→   {request_id, has_proposal, proposal?, generated_at?}
```

### Conversations

```
GET    /api/v1/ai/conversations              → [{id, agent_type, message_count, created_at, updated_at}]
GET    /api/v1/ai/conversations/{id}         → {id, agent_type, messages, context_json, ...}
DELETE /api/v1/ai/conversations/{id}         → 204 No Content
```

---

*AI Implementation Blueprint — SpaceFlow / JunctionX Tirana 2026*
