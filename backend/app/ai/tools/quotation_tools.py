"""
Quotation-domain tools for the SpaceFlow AI agents.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    SERVICE_FEES,
    event_duration_hours,
    get_request,
    list_venues,
)


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "estimate_quotation",
            "description": (
                "Produce a cost breakdown (venue rental + asset fees + service fees + 20% tax) "
                "for a potential event booking. Use before confirming any reservation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {
                        "type": "string",
                        "description": "UUID of the venue to price.",
                    },
                    "duration_hours": {
                        "type": "number",
                        "description": "Total event duration in hours.",
                    },
                    "event_type": {
                        "type": "string",
                        "description": "One of: conference, workshop, hackathon, exhibition, concert, dinner, other.",
                    },
                    "asset_requirements": {
                        "type": "array",
                        "description": "List of {name, quantity} objects.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "integer"},
                            },
                            "required": ["name", "quantity"],
                        },
                    },
                },
                "required": ["venue_id", "duration_hours", "event_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_request_quotation",
            "description": "Retrieve or recalculate the quotation already stored on an event request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "UUID of the event request."},
                },
                "required": ["request_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------


async def estimate_quotation(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    venue_id = UUID(str(args["venue_id"]))
    duration_hours = float(args["duration_hours"])
    event_type = str(args.get("event_type", "other"))
    asset_requirements: list[dict[str, Any]] = args.get("asset_requirements") or []

    venues = await list_venues(db, active_only=False)
    venue = next((v for v in venues if v.id == venue_id), None)
    if not venue:
        return {"error": f"Venue {venue_id} not found."}

    subtotal = Decimal("0")
    breakdown: list[dict[str, Any]] = []

    venue_total = venue.base_price_per_hour * Decimal(str(duration_hours))
    subtotal += venue_total
    breakdown.append({"category": "venue", "name": venue.name, "total": float(venue_total)})

    for item in asset_requirements:
        qty = int(item.get("quantity", 0))
        unit = Decimal("5.00")
        line_total = unit * qty
        subtotal += line_total
        breakdown.append({"category": "asset", "name": str(item["name"]), "total": float(line_total)})

    service_fees = SERVICE_FEES.get(event_type, SERVICE_FEES["other"])
    for label, qty, unit in service_fees:
        line_total = unit * qty
        subtotal += line_total
        breakdown.append({"category": "service", "name": label, "total": float(line_total)})

    tax = (subtotal * Decimal("0.20")).quantize(Decimal("0.01"))
    return {
        "venue": venue.name,
        "duration_hours": duration_hours,
        "event_type": event_type,
        "subtotal": float(subtotal),
        "tax": float(tax),
        "total": float(subtotal + tax),
        "breakdown": breakdown,
    }


async def get_request_quotation(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    request_id = UUID(str(args["request_id"]))
    req = await get_request(request_id, db)
    proposal = req.ai_proposal_json or {}
    estimate = proposal.get("estimate")
    if estimate:
        return {"request_id": str(request_id), "source": "ai_proposal", **estimate}
    return {
        "request_id": str(request_id),
        "source": "none",
        "message": "No quotation computed yet. Use estimate_quotation with the assigned venue.",
    }
