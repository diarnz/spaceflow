"""
Venue-domain tools for the SpaceFlow AI agents.

Each public function is an async executor called by the tool registry.
Input arrives as a plain dict matching the JSON-schema in TOOL_SCHEMAS.
"""
from __future__ import annotations

import json
from datetime import date, time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    event_duration_hours,
    get_venue_availability,
    list_venues,
)

# ---------------------------------------------------------------------------
# JSON schemas consumed by OpenRouter's tool-calling API
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_active_venues",
            "description": (
                "Return all active (bookable) venues with their capacity, pricing per hour, "
                "3-D room ID, and current availability flag."
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
            "name": "get_venue_detail",
            "description": "Retrieve detailed information for a single venue by its UUID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {
                        "type": "string",
                        "description": "UUID of the venue to look up.",
                    }
                },
                "required": ["venue_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_venue_availability",
            "description": (
                "Check whether a specific venue is available on a given date and time window. "
                "Returns is_fully_available and a list of available_slots."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string", "description": "UUID of the venue."},
                    "date": {"type": "string", "description": "ISO date string, e.g. '2025-09-15'."},
                    "start_time": {"type": "string", "description": "ISO time string, e.g. '09:00:00'."},
                    "end_time": {"type": "string", "description": "ISO time string, e.g. '17:00:00'."},
                },
                "required": ["venue_id", "date", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_venues_for_event",
            "description": (
                "Given attendee count and event date/time, score all active venues and return "
                "a ranked list with availability status and capacity fit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "attendee_count": {"type": "integer", "description": "Expected number of attendees."},
                    "date": {"type": "string", "description": "ISO date string."},
                    "start_time": {"type": "string", "description": "ISO time string."},
                    "end_time": {"type": "string", "description": "ISO time string."},
                },
                "required": ["attendee_count", "date", "start_time", "end_time"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Executor implementations
# ---------------------------------------------------------------------------


async def list_active_venues(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    venues = await list_venues(db, active_only=True)
    return {
        "count": len(venues),
        "venues": [
            {
                "id": str(v.id),
                "name": v.name,
                "capacity_min": v.capacity_min,
                "capacity_max": v.capacity_max,
                "base_price_per_hour": float(v.base_price_per_hour),
                "three_d_room_id": v.three_d_room_id,
                "is_active": v.is_active,
            }
            for v in venues
        ],
    }


async def get_venue_detail(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    venue_id = UUID(str(args["venue_id"]))
    venues = await list_venues(db, active_only=False)
    for v in venues:
        if v.id == venue_id:
            return {
                "id": str(v.id),
                "name": v.name,
                "description": v.description,
                "capacity_min": v.capacity_min,
                "capacity_max": v.capacity_max,
                "base_price_per_hour": float(v.base_price_per_hour),
                "three_d_room_id": v.three_d_room_id,
                "amenities": v.amenities or [],
                "is_active": v.is_active,
            }
    return {"error": f"Venue {venue_id} not found."}


async def check_venue_availability(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    venue_id = UUID(str(args["venue_id"]))
    event_date = date.fromisoformat(str(args["date"]))
    start_t = time.fromisoformat(str(args["start_time"]))
    end_t = time.fromisoformat(str(args["end_time"]))
    duration = float(event_duration_hours(start_t, end_t))
    avail = await get_venue_availability(venue_id, event_date, duration, db)
    return {
        "venue_id": str(venue_id),
        "date": str(event_date),
        "is_fully_available": avail.is_fully_available,
        "available_slots": [slot.model_dump() for slot in avail.available_slots],
    }


async def recommend_venues_for_event(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    attendee_count = int(args["attendee_count"])
    event_date = date.fromisoformat(str(args["date"]))
    start_t = time.fromisoformat(str(args["start_time"]))
    end_t = time.fromisoformat(str(args["end_time"]))
    duration = float(event_duration_hours(start_t, end_t))

    venues = await list_venues(db, active_only=True)
    fitting = [v for v in venues if v.capacity_max >= attendee_count]
    results: list[dict[str, Any]] = []
    for v in fitting:
        avail = await get_venue_availability(v.id, event_date, duration, db)
        score = v.capacity_max - attendee_count
        if not avail.is_fully_available and not avail.available_slots:
            score += 10_000
        results.append(
            {
                "id": str(v.id),
                "name": v.name,
                "capacity_max": v.capacity_max,
                "base_price_per_hour": float(v.base_price_per_hour),
                "is_fully_available": avail.is_fully_available,
                "score": score,
            }
        )
    results.sort(key=lambda x: x["score"])
    return {"attendee_count": attendee_count, "recommendations": results}
