from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.ai.tools import layout_tools
from app.database import AsyncSessionLocal
from app.models import Venue
from app.services import get_current_layout, sync_layout_from_3d
from app.websocket.manager import ws_manager


router = APIRouter()
logger = logging.getLogger(__name__)
_active_designs: set[str] = set()


async def _sync_layout_from_3d(room_id: str, items: list) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await sync_layout_from_3d(room_id, items, db)
        await ws_manager.broadcast_to_channel(
            "admin",
            {
                "type": "LAYOUT_SAVED",
                "payload": {"roomId": room_id, "item_count": len(items)},
            },
        )
    except Exception:
        logger.exception("Failed to sync layout from 3D for room %s", room_id)


@router.websocket("/ws/3d-bridge")
async def three_d_bridge(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket, "3d-bridge")
    await ws_manager.send_to_one(
        websocket,
        {
            "type": "CONNECTED",
            "payload": {
                "message": "SpaceFlow 3D Bridge ready",
                "version": "1.0.0",
                "connections": ws_manager.connection_count("3d-bridge"),
            },
        },
    )
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Ignoring invalid JSON from 3D bridge")
                continue
            await _handle_upstream_message(message, websocket)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "3d-bridge")


async def _handle_upstream_message(message: dict, websocket: WebSocket) -> None:
    msg_type = message.get("type")
    payload = message.get("payload", {})

    if msg_type == "LAYOUT_SAVED":
        room_id = payload.get("roomId")
        items = payload.get("items", [])
        if room_id:
            asyncio.create_task(_sync_layout_from_3d(str(room_id), items))
        return

    if msg_type == "REQUEST_LAYOUT":
        room_id = payload.get("roomId")
        if room_id:
            async with AsyncSessionLocal() as db:
                layout = await get_current_layout(room_id, db)
            if layout:
                await ws_manager.send_to_one(
                    websocket,
                    {
                        "type": "APPLY_LAYOUT",
                        "payload": {
                            "roomId": room_id,
                            "items": layout.items_json,
                            "source": "db_sync",
                            "layout_name": layout.name,
                        },
                    },
                )
        return

    if msg_type == "ROOM_ENTERED":
        await ws_manager.broadcast_to_channel("admin", {"type": "USER_VIEWING_ROOM", "payload": payload})
        return

    if msg_type == "AI_DESIGN":
        room_id = payload.get("roomId")
        prompt = str(payload.get("prompt") or "").strip()
        existing_items = payload.get("existingItems") or payload.get("existing_items") or []
        previous_style = payload.get("previousLayoutStyle") or payload.get("previous_layout_style")
        if room_id and prompt:
            if room_id in _active_designs:
                await ws_manager.send_to_one(
                    websocket,
                    {
                        "type": "AI_DESIGN_ERROR",
                        "payload": {
                            "roomId": room_id,
                            "message": "A layout is already being generated for this room. Please wait.",
                        },
                    },
                )
                return
            asyncio.create_task(
                _run_ai_design(
                    websocket,
                    str(room_id),
                    prompt,
                    existing_items if isinstance(existing_items, list) else [],
                    str(previous_style) if previous_style else None,
                )
            )


def _build_ai_design_message(result: dict) -> str:
    added = result.get("added_models") or []
    if added:
        msg = f"Added {', '.join(added)} to your current layout."
    else:
        style = str(result.get("layout_style") or "custom").replace("_", " ")
        seats = result.get("placed_seats", 0)
        count = result.get("item_count", 0)
        models = result.get("models_used") or []
        msg = f"I composed a custom {style} layout with {seats} seats and {count} items."
        if models:
            msg += f" Models used: {', '.join(models)}."
    limitations = result.get("limitations") or []
    if limitations:
        msg += f" {limitations[0]}"
    return msg


async def _run_ai_design(
    websocket: WebSocket,
    room_id: str,
    prompt: str,
    existing_items: list | None = None,
    previous_style: str | None = None,
) -> None:
    if room_id in _active_designs:
        return
    _active_designs.add(room_id)
    await ws_manager.send_to_one(
        websocket,
        {"type": "AI_DESIGN_STARTED", "payload": {"roomId": room_id}},
    )
    try:
        async with AsyncSessionLocal() as db:
            venue = await db.scalar(select(Venue).where(Venue.three_d_room_id == room_id))
            if not venue:
                await ws_manager.send_to_one(
                    websocket,
                    {
                        "type": "AI_DESIGN_ERROR",
                        "payload": {
                            "roomId": room_id,
                            "message": f"No SpaceFlow venue is linked to room '{room_id}'.",
                        },
                    },
                )
                return

            result = await asyncio.wait_for(
                layout_tools.generate_and_apply_layout(
                    {
                        "venue_name": venue.name,
                        "prompt": prompt,
                        "existing_items": existing_items or [],
                        "previous_layout_style": previous_style,
                    },
                    db,
                ),
                timeout=30.0,
            )

        if result.get("error"):
            await ws_manager.send_to_one(
                websocket,
                {
                    "type": "AI_DESIGN_ERROR",
                    "payload": {"roomId": room_id, "message": str(result["error"])},
                },
            )
            return

        await ws_manager.send_to_one(
            websocket,
            {
                "type": "AI_DESIGN_DONE",
                "payload": {
                    "roomId": room_id,
                    "message": _build_ai_design_message(result),
                    "item_count": result.get("item_count"),
                    "layout_id": result.get("layout_id"),
                    "models_used": result.get("models_used") or [],
                    "layout_style": result.get("layout_style"),
                    "modified": bool(result.get("modified")),
                    "added_models": result.get("added_models") or [],
                },
            },
        )
    except asyncio.TimeoutError:
        await ws_manager.send_to_one(
            websocket,
            {
                "type": "AI_DESIGN_ERROR",
                "payload": {
                    "roomId": room_id,
                    "message": "Layout design timed out. Please try again.",
                },
            },
        )
    except Exception as exc:
        logger.exception("3D bridge AI design failed for room %s", room_id)
        await ws_manager.send_to_one(
            websocket,
            {
                "type": "AI_DESIGN_ERROR",
                "payload": {"roomId": room_id, "message": str(exc)},
            },
        )
    finally:
        _active_designs.discard(room_id)
