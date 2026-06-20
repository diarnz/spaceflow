"""
Legacy deterministic AI agent implementations.
Used as fallback when OPENROUTER_API_KEY is not configured or the ReAct engine fails.
All core logic here is rule-based; LLM is called only for optional prose polish.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Asset, EventRequest, User, Venue
from app.services import (
    THREE_D_ROOM_DIMENSIONS,
    BOOKED_REQUEST_STATUSES,
    check_conflicts,
    conflicts_to_dict,
    event_duration_hours,
    generate_tasks_for_request,
    get_asset,
    get_request,
    get_reserved_quantity,
    get_venue_availability,
    list_assets,
    list_venues,
    save_ai_layout,
)
from app.websocket.manager import ws_manager


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def run_agent_legacy(
    agent_type: str,
    user_message: str,
    context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    tool_calls: list[dict[str, Any]] = []

    if agent_type == "room_designer":
        if db is None:
            raise ValueError("room_designer agent requires a database session")
        result = await _run_room_designer(user_message, context, db, tool_calls)
        return {"response": result["response"], "tool_calls_made": tool_calls, "final_context": result}

    if agent_type == "intake":
        if db is None:
            raise ValueError("intake agent requires a database session")
        result = await _run_intake_agent(user_message, context, db, tool_calls)
        return {"response": result["response"], "tool_calls_made": tool_calls, "final_context": result}

    if agent_type == "conflict_detector":
        if db is None:
            raise ValueError("conflict_detector agent requires a database session")
        result = await _run_conflict_detector(context, db, tool_calls)
        return {"response": result["response"], "tool_calls_made": tool_calls, "final_context": result}

    if agent_type == "planner":
        if db is None:
            raise ValueError("planner agent requires a database session")
        result = await _run_planner(context, db, tool_calls)
        return {"response": result["response"], "tool_calls_made": tool_calls, "final_context": result}

    result = await _run_copilot(user_message, context, db, tool_calls)
    return {"response": result["response"], "tool_calls_made": tool_calls, "final_context": result}


async def _run_copilot(
    user_message: str,
    context: dict[str, Any],
    db: AsyncSession | None,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    if db and context.get("request_id"):
        req = await get_request(UUID(str(context["request_id"])), db)
        conflicts = await check_conflicts(req.id, db)
        tool_calls.append({"tool": "load_request_context", "args": {"request_id": str(req.id)}, "result": {"status": req.status}})
        summary = (
            f"Request '{req.title}' is currently '{req.status}' for {req.attendee_count} attendees on "
            f"{req.requested_date}. Conflicts detected: {len(conflicts)}."
        )
        polished = await _maybe_llm_rewrite(
            system_prompt="You are an operations copilot for the Pyramid of Tirana. Rewrite the backend summary into a concise, practical assistant reply.",
            user_prompt=f"User asked: {user_message}\n\nStructured summary:\n{summary}\n\nConflicts:\n{conflicts_to_dict(conflicts)}",
            fallback=summary,
        )
        return {"response": polished}

    if db and ("available" in user_message.lower() or "venue" in user_message.lower()):
        venues = await list_venues(db, active_only=True)
        tool_calls.append({"tool": "list_venues", "args": {}, "result": {"count": len(venues)}})
        listing = ", ".join(f"{venue.name} (cap {venue.capacity_max})" for venue in venues)
        fallback = f"Currently active venues are: {listing}."
        polished = await _maybe_llm_rewrite(
            system_prompt="You are a venue booking copilot. Answer clearly and briefly.",
            user_prompt=f"User asked: {user_message}\nAvailable venues: {listing}",
            fallback=fallback,
        )
        return {"response": polished}

    fallback = (
        "I can help with venue availability, request analysis, room layout generation, conflict checks, "
        "quotations, and operational task planning. Tell me the request ID or the room you want to work on."
    )
    polished = await _maybe_llm_rewrite(
        system_prompt="You are a concise operations copilot.",
        user_prompt=user_message,
        fallback=fallback,
    )
    return {"response": polished}


async def _run_intake_agent(
    user_message: str,
    context: dict[str, Any],
    db: AsyncSession,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    attendee_count = int(context.get("attendee_count") or 0)
    event_type = str(context.get("event_type") or "other")
    requested_date = date.fromisoformat(str(context["requested_date"]))
    start_time = time.fromisoformat(str(context["start_time"]))
    end_time = time.fromisoformat(str(context["end_time"]))
    special = str(context.get("special_requirements") or "")

    venues = await list_venues(db, active_only=True)
    fitting_venues = [venue for venue in venues if venue.capacity_max >= attendee_count]
    duration_hours = float(event_duration_hours(start_time, end_time))

    scored: list[tuple[int, Venue, dict[str, Any]]] = []
    for venue in fitting_venues:
        availability = await get_venue_availability(venue.id, requested_date, duration_hours, db)
        score = venue.capacity_max - attendee_count
        if not availability.is_fully_available and not availability.available_slots:
            score += 10_000
        scored.append(
            (
                score,
                venue,
                {
                    "is_fully_available": availability.is_fully_available,
                    "available_slots": [slot.model_dump() for slot in availability.available_slots],
                },
            )
        )
    scored.sort(key=lambda item: item[0])
    chosen = scored[0] if scored else None
    tool_calls.append({"tool": "match_request_to_venues", "args": {"attendee_count": attendee_count}, "result": {"candidates": len(scored)}})

    required_assets = _estimate_assets_from_request(event_type, attendee_count, special)
    availability_results = await _check_assets_by_name(required_assets, requested_date, start_time, end_time, db)
    tool_calls.append({"tool": "check_asset_availability", "args": {"assets": required_assets}, "result": availability_results})

    estimate = _estimate_quotation(chosen[1] if chosen else None, duration_hours, availability_results, event_type)
    tool_calls.append({"tool": "estimate_quotation", "args": {"duration_hours": duration_hours}, "result": estimate})

    summary = {
        "recommended_venue": {
            "id": str(chosen[1].id) if chosen else None,
            "name": chosen[1].name if chosen else None,
            "reason": "Closest capacity fit with current availability." if chosen else "No fitting venue found.",
        },
        "availability": chosen[2] if chosen else {"is_fully_available": False, "available_slots": []},
        "required_assets": availability_results,
        "estimate": estimate,
    }
    fallback = (
        f"Recommended venue: {summary['recommended_venue']['name'] or 'none'}. "
        f"Estimated quotation: EUR {estimate['total']:.2f}. "
        f"Asset shortfalls: {sum(1 for item in availability_results if not item['can_fulfill'])}."
    )
    response = await _maybe_llm_rewrite(
        system_prompt="You are an event intake specialist. Write a concise operational assessment from the structured data.",
        user_prompt=f"Request analysis data:\n{summary}",
        fallback=fallback,
    )
    return {"response": response, **summary}


async def _run_conflict_detector(
    context: dict[str, Any],
    db: AsyncSession,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    request_id = UUID(str(context["request_id"]))
    conflicts = await check_conflicts(request_id, db)
    structured = conflicts_to_dict(conflicts)
    tool_calls.append({"tool": "check_conflicts", "args": {"request_id": str(request_id)}, "result": {"count": len(structured)}})
    fallback = "No conflicts detected." if not structured else "Conflicts detected:\n" + "\n".join(
        f"- [{item['severity']}] {item['description']} Suggestion: {item['suggestion']}"
        for item in structured
    )
    response = await _maybe_llm_rewrite(
        system_prompt="You are an operations conflict reviewer. Summarize risks and suggest concrete next steps.",
        user_prompt=f"Conflict data:\n{structured}",
        fallback=fallback,
    )
    return {"response": response, "conflicts": structured}


async def _run_planner(
    context: dict[str, Any],
    db: AsyncSession,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    request_id = UUID(str(context["request_id"]))
    tasks = await generate_tasks_for_request(request_id, db, ai_generated=True)
    tool_calls.append({"tool": "generate_tasks", "args": {"request_id": str(request_id)}, "result": {"tasks_created": len(tasks)}})
    fallback = f"Generated {len(tasks)} operational tasks for the event."
    response = await _maybe_llm_rewrite(
        system_prompt="You are an event operations planner. Summarize the generated task list.",
        user_prompt=f"Generated {len(tasks)} tasks.",
        fallback=fallback,
    )
    return {"response": response, "tasks_created": len(tasks)}


async def _run_room_designer(
    user_message: str,
    context: dict[str, Any],
    db: AsyncSession,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    from fastapi import HTTPException
    from app.ai.tools import layout_tools

    venue_name = context.get("venue_name")
    event_request_id = UUID(str(context["event_request_id"])) if context.get("event_request_id") else None
    venue = await _resolve_venue_by_name(venue_name, db)
    if not venue or not venue.three_d_room_id:
        raise HTTPException(status_code=404, detail="Venue not found or not linked to a 3D room.")

    parsed = await layout_tools.parse_design_prompt(
        {"prompt": user_message, "venue_name": venue.name},
        db,
    )
    if parsed.get("error"):
        raise HTTPException(status_code=400, detail=str(parsed["error"]))
    tool_calls.append(
        {
            "tool": "parse_design_prompt",
            "args": {"prompt": user_message, "venue_name": venue.name},
            "result": parsed,
        }
    )

    availability = await layout_tools._get_furniture_availability(  # type: ignore[attr-defined]
        layout_tools._coerce_dt(context.get("event_date_start")),  # type: ignore[attr-defined]
        layout_tools._coerce_dt(context.get("event_date_end")),  # type: ignore[attr-defined]
        db,
    )
    tool_calls.append(
        {
            "tool": "get_available_3d_models",
            "args": {
                "start_datetime": context.get("event_date_start"),
                "end_datetime": context.get("event_date_end"),
            },
            "result": {"model_availability": availability},
        }
    )

    layout_result = await layout_tools.generate_and_apply_layout(
        {
            "venue_name": venue.name,
            "prompt": user_message,
            "event_request_id": str(event_request_id) if event_request_id else None,
            "start_datetime": context.get("event_date_start"),
            "end_datetime": context.get("event_date_end"),
        },
        db,
    )
    if layout_result.get("error"):
        raise HTTPException(status_code=400, detail=str(layout_result["error"]))
    tool_calls.append(
        {
            "tool": "generate_and_apply_layout",
            "args": {
                "venue_name": venue.name,
                "prompt": user_message,
                "event_request_id": str(event_request_id) if event_request_id else None,
            },
            "result": layout_result,
        }
    )

    spec = parsed.get("spec", {})
    limitations = layout_result.get("limitations", [])
    feature_notes: list[str] = []
    if spec.get("include_monitors"):
        feature_notes.append("monitors at the workstations")
    if spec.get("include_whiteboard"):
        feature_notes.append("a visible whiteboard")
    if spec.get("include_tv"):
        feature_notes.append("a presentation screen")
    if spec.get("include_registration"):
        feature_notes.append("a registration/check-in table")

    features_text = ""
    if feature_notes:
        features_text = " It includes " + ", ".join(feature_notes[:-1]) + (
            f", and {feature_notes[-1]}." if len(feature_notes) > 1 else f"{feature_notes[0]}."
        )

    response = (
        f"I composed a custom {layout_result.get('layout_style', spec.get('event_type', 'event'))} layout in {venue.name} "
        f"with {layout_result.get('placed_seats', 0)} workstations/seats and {layout_result.get('item_count', 0)} total items."
        f"{features_text}"
    )
    models_used = layout_result.get("models_used") or []
    if models_used:
        response += f" Models used: {', '.join(models_used)}."
    if limitations:
        response += " Current constraints: " + "; ".join(limitations)

    return {
        "response": response,
        "venue_id": str(venue.id),
        "three_d_room_id": venue.three_d_room_id,
        "layout_id": layout_result.get("layout_id"),
        "item_count": layout_result.get("item_count", 0),
        "placed_seats": layout_result.get("placed_seats", 0),
        "limitations": limitations,
        "layout_style": layout_result.get("layout_style"),
    }


async def _resolve_venue_by_name(venue_name: str | None, db: AsyncSession) -> Venue | None:
    if not venue_name:
        return None
    lowered = venue_name.lower().strip()
    venues = await list_venues(db, active_only=False)
    for venue in venues:
        if venue.name.lower() == lowered:
            return venue
    for venue in venues:
        if lowered in venue.name.lower():
            return venue
    return None


def _estimate_assets_from_request(event_type: str, attendee_count: int, special: str) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    if attendee_count:
        required.append({"name": "Chair (Standard)", "quantity": attendee_count})
    if event_type in {"conference", "dinner"}:
        required.append({"name": "Round Table (6-person)", "quantity": max(1, math.ceil(attendee_count / 6))})
    elif event_type in {"workshop", "hackathon"}:
        required.append({"name": "Rectangular Table", "quantity": max(1, math.ceil(attendee_count / 4))})

    text = special.lower()
    if "microphone" in text or "mic" in text:
        qty = _extract_number_near_keyword(text, ["microphone", "microphones", "mic", "mics"]) or 1
        required.append({"name": "Microphone (wireless)", "quantity": qty})
    if "tv" in text or "screen" in text:
        qty = _extract_number_near_keyword(text, ["tv", "screen", "screens"]) or 1
        required.append({"name": "TV Display (65\")", "quantity": qty})
    if "whiteboard" in text:
        qty = _extract_number_near_keyword(text, ["whiteboard", "whiteboards"]) or 1
        required.append({"name": "Whiteboard", "quantity": qty})
    if "pc" in text or "laptop" in text:
        qty = _extract_number_near_keyword(text, ["pc", "pcs", "laptop", "laptops"]) or max(1, attendee_count // 2)
        required.append({"name": "Laptop/PC", "quantity": qty})

    merged: dict[str, int] = {}
    for item in required:
        merged[item["name"]] = merged.get(item["name"], 0) + int(item["quantity"])
    return [{"name": name, "quantity": qty} for name, qty in merged.items()]


def _extract_number_near_keyword(text: str, keywords: list[str]) -> int | None:
    for keyword in keywords:
        match = re.search(rf"(\d+)\s+{re.escape(keyword)}", text)
        if match:
            return int(match.group(1))
    return None


async def _check_assets_by_name(
    required_assets: list[dict[str, Any]],
    requested_date: date,
    start_time: time,
    end_time: time,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    start_dt = _combine_datetime(requested_date, start_time)
    end_dt = _combine_datetime(requested_date, end_time)
    assets = await list_assets(db, active_only=True)
    lookup = {asset.name.lower(): asset for asset in assets}
    results: list[dict[str, Any]] = []
    for item in required_assets:
        asset = lookup.get(item["name"].lower())
        if not asset:
            results.append({"name": item["name"], "requested": item["quantity"], "available": 0, "can_fulfill": False})
            continue
        reserved = await get_reserved_quantity(asset.id, start_dt, end_dt, db)
        available = max(0, asset.total_quantity - reserved)
        results.append(
            {
                "name": asset.name,
                "requested": item["quantity"],
                "available": available,
                "can_fulfill": available >= int(item["quantity"]),
            }
        )
    return results


def _estimate_quotation(
    venue: Venue | None,
    duration_hours: float,
    asset_results: list[dict[str, Any]],
    event_type: str,
) -> dict[str, Any]:
    subtotal = Decimal("0")
    breakdown: list[dict[str, Any]] = []
    if venue:
        venue_total = venue.base_price_per_hour * Decimal(str(duration_hours))
        subtotal += venue_total
        breakdown.append({"category": "venue", "name": venue.name, "total": float(venue_total)})
    for item in asset_results:
        multiplier = Decimal("5.00")
        total = multiplier * int(item["requested"])
        subtotal += total
        breakdown.append({"category": "asset", "name": item["name"], "total": float(total)})
    for label, qty, unit in _service_fees_for_event(event_type):
        total = unit * qty
        subtotal += total
        breakdown.append({"category": "service", "name": label, "total": float(total)})
    tax = (subtotal * Decimal("0.20")).quantize(Decimal("0.01"))
    return {"subtotal": float(subtotal), "tax": float(tax), "total": float(subtotal + tax), "breakdown": breakdown}


def _service_fees_for_event(event_type: str) -> list[tuple[str, int, Decimal]]:
    from app.services import SERVICE_FEES
    return SERVICE_FEES.get(event_type, SERVICE_FEES["other"])


def _combine_datetime(d: date, t: time) -> datetime:
    return datetime.combine(d, t).replace(tzinfo=timezone.utc)


async def _available_models_for_window(
    start_dt: datetime | str | None,
    end_dt: datetime | str | None,
    db: AsyncSession,
) -> dict[str, int]:
    def _coerce(dt: datetime | str | None) -> datetime | None:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(str(dt))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    start = _coerce(start_dt)
    end = _coerce(end_dt)
    assets = await list_assets(db, active_only=True)
    counts: dict[str, int] = {}
    for asset in assets:
        if not asset.three_d_item_key:
            continue
        available = asset.total_quantity
        if start and end:
            reserved = await get_reserved_quantity(asset.id, start, end, db)
            available = max(0, asset.total_quantity - reserved)
        counts[asset.three_d_item_key] = counts.get(asset.three_d_item_key, 0) + available
    return counts


def _parse_layout_prompt(prompt: str, venue_name: str, room_dims: dict[str, float]) -> dict[str, Any]:
    text = prompt.lower()
    attendee_count = _extract_number_near_keyword(text, ["person", "people", "attendee", "attendees", "seat", "seats"]) or 24
    event_type = "conference"
    for candidate in ["hackathon", "workshop", "conference", "concert", "exhibition", "classroom"]:
        if candidate in text:
            event_type = candidate
            break
    if "theater" in text or "auditorium" in text:
        event_type = "conference"
    include_tv = "tv" in text or "screen" in text or "display" in text
    include_whiteboard = "whiteboard" in text or event_type in {"workshop", "classroom", "hackathon"}
    include_monitors = "pc" in text or "computer" in text or "monitor" in text or event_type == "hackathon"
    include_microphones = _extract_number_near_keyword(text, ["microphone", "microphones", "mic", "mics"]) or (1 if "microphone" in text or "mic" in text else 0)
    side_tables = "coffee" in text or "registration" in text or "table" in text or event_type in {"workshop", "hackathon"}
    return {
        "venue_name": venue_name,
        "event_type": event_type,
        "attendee_count": attendee_count,
        "include_tv": include_tv,
        "include_whiteboard": include_whiteboard,
        "include_monitors": include_monitors,
        "include_microphones": include_microphones,
        "side_tables": side_tables,
        "room_dims": room_dims,
    }


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


def _layout_conference(room_dims: dict[str, float], spec: dict[str, Any], availability: dict[str, int]) -> dict[str, Any]:
    w = room_dims["w"]
    d = room_dims["d"]
    chairs_available = availability.get("simple_chair", spec["attendee_count"])
    attendee_target = min(spec["attendee_count"], chairs_available)
    items: list[dict[str, Any]] = []
    limitations: list[str] = []

    if attendee_target < spec["attendee_count"]:
        limitations.append(f"Only {attendee_target} standard chairs were available for the selected time window.")

    if spec["include_tv"] and availability.get("wall_flat_tv", 1) > 0:
        items.append(_wall_item("wall_flat_tv", w, d, room_dims["h"], wall="back", offset_x=0.0))
    if spec["include_whiteboard"] and availability.get("whiteboard", 0) > 0:
        items.append({"modelKey": "whiteboard", "x": -w * 0.22, "z": -(d / 2 - 0.5), "rotY": 0.0, "type": "floor"})
        if availability.get("whiteboard", 0) > 1:
            items.append({"modelKey": "whiteboard", "x": w * 0.22, "z": -(d / 2 - 0.5), "rotY": 0.0, "type": "floor"})

    mic_count = min(int(spec["include_microphones"]), availability.get("microphone_stand", int(spec["include_microphones"])))
    if mic_count < int(spec["include_microphones"]):
        limitations.append(f"Only {mic_count} microphone stands were available.")
    for idx in range(mic_count):
        items.append({"modelKey": "microphone_stand", "x": (idx - (mic_count - 1) / 2) * 0.7, "z": -(d / 2 - 1.25), "rotY": 0.0, "type": "floor"})

    usable_w = max(1.6, w - 1.0)
    usable_d = max(1.6, d - 1.5)
    cols = max(2, min(10, int(usable_w / 0.62)))
    rows = max(1, int(usable_d / 0.72))
    placed = min(attendee_target, cols * rows)
    if placed < attendee_target:
        limitations.append(f"The room footprint fits {placed} seats in a clean conference layout.")

    x_positions = _evenly_spaced_positions(cols, usable_w / 2)
    seat_index = 0
    for row in range(rows):
        z = 0.1 + row * 0.62
        for x in x_positions:
            if seat_index >= placed:
                break
            items.append({"modelKey": "simple_chair", "x": x, "z": z, "rotY": math.pi, "type": "floor"})
            seat_index += 1
        if seat_index >= placed:
            break

    if spec["side_tables"] and availability.get("simple_table", 0) > 0:
        items.append({"modelKey": "simple_table", "x": -(w / 2 - 0.8), "z": d / 2 - 0.9, "rotY": math.pi / 2, "type": "floor"})
        if availability.get("simple_table", 0) > 1:
            items.append({"modelKey": "simple_table", "x": w / 2 - 0.8, "z": d / 2 - 0.9, "rotY": -math.pi / 2, "type": "floor"})

    return {"items": items, "placed_seats": placed, "limitations": limitations}


def _layout_workshop(room_dims: dict[str, float], spec: dict[str, Any], availability: dict[str, int]) -> dict[str, Any]:
    w = room_dims["w"]
    d = room_dims["d"]
    tables_available = availability.get("simple_table", 0)
    chairs_available = availability.get("simple_chair", spec["attendee_count"])
    attendee_target = min(spec["attendee_count"], chairs_available)
    cluster_size = 4
    cluster_count = max(1, min(tables_available or 1, math.ceil(attendee_target / cluster_size)))
    items: list[dict[str, Any]] = []
    limitations: list[str] = []

    if tables_available and cluster_count > tables_available:
        limitations.append(f"Only {tables_available} tables were available.")

    if spec["include_tv"] and availability.get("wall_flat_tv", 0) > 0:
        items.append(_wall_item("wall_flat_tv", w, d, room_dims["h"], wall="back", offset_x=0.0))
    if spec["include_whiteboard"] and availability.get("whiteboard", 0) > 0:
        items.append({"modelKey": "whiteboard", "x": -(w / 2 - 0.45), "z": -(d / 2 - 0.8), "rotY": math.pi / 2, "type": "floor"})

    grid_cols = max(1, min(cluster_count, 2 if w < 6 else 3))
    grid_rows = max(1, math.ceil(cluster_count / grid_cols))
    x_positions = _evenly_spaced_positions(grid_cols, max(1.1, w / 2 - 0.9))
    z_positions = _evenly_spaced_positions(grid_rows, max(0.9, d / 2 - 1.1), start_bias=0.2)

    placed_chairs = 0
    table_indices: list[int] = []
    for _row, z in enumerate(z_positions):
        for _col, x in enumerate(x_positions):
            if len(table_indices) >= cluster_count:
                break
            table_indices.append(len(items))
            items.append({"modelKey": "simple_table", "x": x, "z": z, "rotY": 0.0, "type": "floor"})
            for dx, dz, rot in [(0, 0.62, math.pi), (0, -0.62, 0.0), (0.72, 0, -math.pi / 2), (-0.72, 0, math.pi / 2)]:
                if placed_chairs >= attendee_target:
                    break
                items.append({"modelKey": "simple_chair", "x": x + dx, "z": z + dz, "rotY": rot, "type": "floor"})
                placed_chairs += 1

    return {"items": items, "placed_seats": placed_chairs, "limitations": limitations}


def _layout_hackathon(room_dims: dict[str, float], spec: dict[str, Any], availability: dict[str, int]) -> dict[str, Any]:
    w = room_dims["w"]
    d = room_dims["d"]
    pod_size = 4
    target_seats = min(spec["attendee_count"], availability.get("simple_chair", spec["attendee_count"]))
    pod_count = max(1, math.ceil(target_seats / pod_size))
    pod_count = min(pod_count, availability.get("simple_table", pod_count))
    items: list[dict[str, Any]] = []
    limitations: list[str] = []
    if pod_count * pod_size < spec["attendee_count"]:
        limitations.append(f"Current furniture availability supports approximately {pod_count * pod_size} hackathon seats.")

    grid_cols = max(1, min(pod_count, 2 if w < 7 else 3))
    grid_rows = math.ceil(pod_count / grid_cols)
    x_positions = _evenly_spaced_positions(grid_cols, max(1.0, w / 2 - 1.0))
    z_positions = _evenly_spaced_positions(grid_rows, max(0.9, d / 2 - 0.9), start_bias=0.0)
    monitors_available = availability.get("office_monitor", 0)
    speakers_available = availability.get("speaker", 0)
    placed_seats = 0

    for z in z_positions:
        for x in x_positions:
            if pod_count <= 0:
                break
            pod_count -= 1
            table_index = len(items)
            items.append({"modelKey": "simple_table", "x": x, "z": z, "rotY": 0.0, "type": "floor"})
            for dx, dz, rot in [(0, 0.62, math.pi), (0, -0.62, 0.0), (0.82, 0, -math.pi / 2), (-0.82, 0, math.pi / 2)]:
                if placed_seats >= target_seats:
                    break
                items.append({"modelKey": "simple_chair", "x": x + dx, "z": z + dz, "rotY": rot, "type": "floor"})
                placed_seats += 1
            if monitors_available > 0:
                items.append({"modelKey": "office_monitor", "x": x, "z": z + 0.18, "rotY": 0.0, "type": "floor", "stackOn": table_index, "lxf": 0.0, "lzf": 0.28})
                monitors_available -= 1
            if monitors_available > 0:
                items.append({"modelKey": "office_monitor", "x": x, "z": z - 0.18, "rotY": math.pi, "type": "floor", "stackOn": table_index, "lxf": 0.0, "lzf": -0.28})
                monitors_available -= 1
            if speakers_available > 0:
                items.append({"modelKey": "speaker", "x": x, "z": z, "rotY": 0.0, "type": "floor", "stackOn": table_index, "scale": {"h": 0.22}})
                speakers_available -= 1

    if spec["include_whiteboard"] and availability.get("whiteboard", 0) > 0:
        items.append({"modelKey": "whiteboard", "x": w / 2 - 0.55, "z": -(d / 2 - 0.8), "rotY": -math.pi / 2, "type": "floor"})

    return {"items": items, "placed_seats": placed_seats, "limitations": limitations}


def _layout_exhibition(room_dims: dict[str, float], spec: dict[str, Any], availability: dict[str, int]) -> dict[str, Any]:
    w = room_dims["w"]
    d = room_dims["d"]
    items: list[dict[str, Any]] = []
    limitations: list[str] = []
    table_count = min(availability.get("simple_table", 0), 6 if w >= 6 else 4)
    if table_count == 0:
        limitations.append("No display tables were available.")
    side_positions = _evenly_spaced_positions(max(1, table_count // 2 or 1), max(0.8, d / 2 - 1.0))
    used = 0
    for z in side_positions:
        if used >= table_count:
            break
        items.append({"modelKey": "simple_table", "x": -(w / 2 - 0.8), "z": z, "rotY": math.pi / 2, "type": "floor"})
        used += 1
    for z in side_positions:
        if used >= table_count:
            break
        items.append({"modelKey": "simple_table", "x": w / 2 - 0.8, "z": z, "rotY": -math.pi / 2, "type": "floor"})
        used += 1
    if spec["include_tv"] and availability.get("wall_flat_tv", 0) > 0:
        items.append(_wall_item("wall_flat_tv", w, d, room_dims["h"], wall="back", offset_x=0.0))
    return {"items": items, "placed_seats": 0, "limitations": limitations}


def _wall_item(model_key: str, room_w: float, room_d: float, room_h: float, *, wall: str = "back", offset_x: float = 0.0) -> dict[str, Any]:
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


def _evenly_spaced_positions(count: int, extent: float, *, start_bias: float = 0.0) -> list[float]:
    if count <= 1:
        return [start_bias]
    start = -extent
    step = (extent * 2) / (count - 1)
    return [start + idx * step + start_bias for idx in range(count)]


async def _maybe_llm_rewrite(system_prompt: str, user_prompt: str, fallback: str) -> str:
    if not settings.OPENROUTER_API_KEY:
        return fallback
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": "http://localhost:8080",
                    "X-Title": "SpaceFlow",
                },
                json={
                    "model": settings.AI_MODEL,
                    "temperature": settings.AI_TEMPERATURE,
                    "max_tokens": min(settings.AI_MAX_TOKENS, 700),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, list):
                return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip() or fallback
            return str(content).strip() or fallback
    except Exception:
        return fallback
