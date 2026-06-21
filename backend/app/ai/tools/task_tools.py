"""
Task & conflict-domain tools for the SpaceFlow AI agents.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    check_conflicts,
    conflicts_to_dict,
    generate_tasks_for_request,
    decode_task_operations,
    get_request,
    list_tasks,
)


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "detect_conflicts",
            "description": (
                "Run the conflict-detection engine against a specific event request. "
                "Returns a list of conflicts with severity (blocking / warning) and "
                "suggested resolutions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "UUID of the event request."},
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_operational_tasks",
            "description": (
                "Generate a full set of operational tasks for an approved event request "
                "(setup, AV, catering reminders, teardown, etc.). "
                "Should be called after the request is approved."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "UUID of the event request."},
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_request_tasks",
            "description": "Return all tasks already generated for an event request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "UUID of the event request."},
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_request_summary",
            "description": (
                "Return a lightweight summary of an event request: title, status, "
                "attendee_count, dates, venue, and ai_proposal snippet."
            ),
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


async def detect_conflicts(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    request_id = UUID(str(args["request_id"]))
    conflicts = await check_conflicts(request_id, db)
    structured = conflicts_to_dict(conflicts)
    return {
        "request_id": str(request_id),
        "conflict_count": len(structured),
        "has_blocking": any(c["severity"] == "blocking" for c in structured),
        "conflicts": structured,
    }


async def generate_operational_tasks(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    request_id = UUID(str(args["request_id"]))
    tasks = await generate_tasks_for_request(request_id, db, ai_generated=True)
    return {
        "request_id": str(request_id),
        "tasks_created": len(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "task_type": t.task_type,
                **decode_task_operations(t.description),
                "due_at": str(t.due_at),
                "priority": t.priority,
            }
            for t in tasks
        ],
    }


async def list_request_tasks(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    request_id = UUID(str(args["request_id"]))
    tasks = await list_tasks(db, request_id=request_id)
    return {
        "request_id": str(request_id),
        "task_count": len(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "task_type": t.task_type,
                **decode_task_operations(t.description),
                "due_at": str(t.due_at),
                "priority": t.priority,
            }
            for t in tasks
        ],
    }


async def get_request_summary(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    request_id = UUID(str(args["request_id"]))
    req = await get_request(request_id, db)
    return {
        "id": str(req.id),
        "title": req.title,
        "status": req.status,
        "event_type": req.event_type,
        "attendee_count": req.attendee_count,
        "requested_date": str(req.requested_date),
        "start_time": str(req.start_time),
        "end_time": str(req.end_time),
        "venue_id": str(req.venue_id) if req.venue_id else None,
        "special_requirements": req.special_requirements or "",
        "has_ai_proposal": req.ai_proposal_json is not None,
    }
