"""
Inventory / asset-domain tools for the SpaceFlow AI agents.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    get_asset,
    get_reserved_quantity,
    list_assets,
)


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_inventory",
            "description": (
                "Return the full inventory of assets (furniture, AV equipment, etc.) "
                "with their total quantities and 3-D model keys."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "If true (default), return only active/available assets.",
                    }
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
                "Check how many units of a specific asset are available during a time window. "
                "Returns total_quantity, reserved_quantity, available_quantity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string", "description": "UUID of the asset."},
                    "start_datetime": {
                        "type": "string",
                        "description": "ISO 8601 datetime for the start of the window, e.g. '2025-09-15T09:00:00Z'.",
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "ISO 8601 datetime for the end of the window.",
                    },
                },
                "required": ["asset_id", "start_datetime", "end_datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_assets_bulk",
            "description": (
                "Bulk-check availability for a list of {name, quantity} asset requirements "
                "during a date/time window. Returns can_fulfill flag per item."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "requirements": {
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
                    "date": {"type": "string", "description": "ISO date string."},
                    "start_time": {"type": "string", "description": "ISO time string."},
                    "end_time": {"type": "string", "description": "ISO time string."},
                },
                "required": ["requirements", "date", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_3d_models",
            "description": (
                "Return a mapping of 3-D model keys to available counts for a time window. "
                "Used by the room-designer agent to know which furniture it can place."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_datetime": {"type": "string", "description": "ISO 8601 datetime or null for no window check."},
                    "end_datetime": {"type": "string", "description": "ISO 8601 datetime or null for no window check."},
                },
                "required": [],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------


def _coerce_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(str(value))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def list_inventory(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    active_only = bool(args.get("active_only", True))
    assets = await list_assets(db, active_only=active_only)
    return {
        "count": len(assets),
        "assets": [
            {
                "id": str(a.id),
                "name": a.name,
                "category": a.category,
                "total_quantity": a.total_quantity,
                "three_d_item_key": a.three_d_item_key,
                "is_active": a.is_active,
            }
            for a in assets
        ],
    }


async def check_asset_availability(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    asset_id = UUID(str(args["asset_id"]))
    start = _coerce_dt(args["start_datetime"])
    end = _coerce_dt(args["end_datetime"])
    if start is None or end is None:
        return {"error": "start_datetime and end_datetime are required."}
    asset = await get_asset(asset_id, db)
    reserved = await get_reserved_quantity(asset_id, start, end, db)
    available = max(0, asset.total_quantity - reserved)
    return {
        "asset_id": str(asset_id),
        "name": asset.name,
        "total_quantity": asset.total_quantity,
        "reserved_quantity": reserved,
        "available_quantity": available,
    }


async def check_assets_bulk(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    requirements: list[dict[str, Any]] = args["requirements"]
    event_date = date.fromisoformat(str(args["date"]))
    start_t = time.fromisoformat(str(args["start_time"]))
    end_t = time.fromisoformat(str(args["end_time"]))
    from datetime import datetime as _dt
    start = _dt.combine(event_date, start_t).replace(tzinfo=timezone.utc)
    end = _dt.combine(event_date, end_t).replace(tzinfo=timezone.utc)

    assets = await list_assets(db, active_only=True)
    lookup = {a.name.lower(): a for a in assets}
    results: list[dict[str, Any]] = []
    for req in requirements:
        name = str(req["name"])
        qty = int(req["quantity"])
        asset = lookup.get(name.lower())
        if not asset:
            results.append({"name": name, "requested": qty, "available": 0, "can_fulfill": False})
            continue
        reserved = await get_reserved_quantity(asset.id, start, end, db)
        available = max(0, asset.total_quantity - reserved)
        results.append(
            {
                "name": asset.name,
                "requested": qty,
                "available": available,
                "can_fulfill": available >= qty,
            }
        )
    shortfalls = sum(1 for r in results if not r["can_fulfill"])
    return {"results": results, "shortfall_count": shortfalls, "all_fulfilled": shortfalls == 0}


async def get_available_3d_models(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    start = _coerce_dt(args.get("start_datetime"))
    end = _coerce_dt(args.get("end_datetime"))
    assets = await list_assets(db, active_only=True)
    counts: dict[str, int] = {}
    for asset in assets:
        if not asset.three_d_item_key:
            continue
        available = asset.total_quantity
        if start and end:
            reserved = await get_reserved_quantity(asset.id, start, end, db)
            available = max(0, asset.total_quantity - reserved)
        key = asset.three_d_item_key
        counts[key] = counts.get(key, 0) + available
    return {"model_availability": counts}
