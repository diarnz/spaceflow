"""
SpaceFlow AI API Router — 10 endpoints.

Covers: chat, design-room, detect-conflicts, generate-tasks, intake trigger,
conversation CRUD, tool listing, and SSE streaming.
"""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import run_agent
from app.database import AsyncSessionLocal, get_db
from app.dependencies import get_current_user, require_staff
from app.models import AiConversation, User
from app.schemas import (
    AIAgentResponse,
    AIConversationDetail,
    AIConversationSummary,
    AIChatRequest,
    AIChatResponse,
    AIDesignRoomRequest,
    AIDetectConflictsRequest,
    AIRunAgentRequest,
    AIToolInfo,
    PaginatedResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: persist / update conversation
# ---------------------------------------------------------------------------


async def _upsert_conversation(
    db: AsyncSession,
    user_id: UUID,
    agent_type: str,
    new_user_message: str,
    assistant_response: str,
    context: dict,
    conversation_id: UUID | None = None,
) -> AiConversation:
    conversation: AiConversation | None = None
    if conversation_id:
        conversation = await db.get(AiConversation, conversation_id)
        if conversation and conversation.user_id != user_id:
            conversation = None

    history = list(conversation.messages) if conversation else []
    history.extend([
        {"role": "user", "content": new_user_message},
        {"role": "assistant", "content": assistant_response},
    ])

    if conversation:
        conversation.messages = history
        conversation.context_json = {**(conversation.context_json or {}), **context}
    else:
        conversation = AiConversation(
            user_id=user_id,
            agent_type=agent_type,
            messages=history,
            context_json=context,
        )
        db.add(conversation)

    await db.commit()
    await db.refresh(conversation)
    return conversation


# ---------------------------------------------------------------------------
# 1. POST /ai/chat — general copilot chat
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=AIChatResponse)
async def route_ai_chat(
    data: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIChatResponse:
    history: list[dict] = []
    if data.conversation_id:
        conv = await db.get(AiConversation, data.conversation_id)
        if conv and conv.user_id == current_user.id:
            history = list(conv.messages)

    result = await run_agent(
        agent_type=data.agent_type,
        user_message=data.message,
        context={**data.context, "user_id": str(current_user.id)},
        conversation_history=history,
        db=db,
    )

    conversation = await _upsert_conversation(
        db=db,
        user_id=current_user.id,
        agent_type=data.agent_type,
        new_user_message=data.message,
        assistant_response=result["response"],
        context=data.context,
        conversation_id=data.conversation_id,
    )

    return AIChatResponse(
        response=result["response"],
        tool_calls_made=result.get("tool_calls_made", []),
        conversation_id=conversation.id,
    )


# ---------------------------------------------------------------------------
# 2. POST /ai/run — typed agent entry (returns AIAgentResponse)
# ---------------------------------------------------------------------------


@router.post("/run", response_model=AIAgentResponse)
async def route_ai_run(
    data: AIRunAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIAgentResponse:
    history: list[dict] = []
    if data.conversation_id:
        conv = await db.get(AiConversation, data.conversation_id)
        if conv and conv.user_id == current_user.id:
            history = list(conv.messages)

    result = await run_agent(
        agent_type=data.agent_type,
        user_message=data.message,
        context={**data.context, "user_id": str(current_user.id)},
        conversation_history=history,
        db=db,
    )

    conversation = await _upsert_conversation(
        db=db,
        user_id=current_user.id,
        agent_type=data.agent_type,
        new_user_message=data.message,
        assistant_response=result["response"],
        context=data.context,
        conversation_id=data.conversation_id,
    )

    return AIAgentResponse(
        response=result["response"],
        agent_type=data.agent_type,
        tool_calls_made=result.get("tool_calls_made", []),
        conversation_id=conversation.id,
        iterations=result.get("iterations", 0),
    )


# ---------------------------------------------------------------------------
# 3. POST /ai/design-room — room designer agent
# ---------------------------------------------------------------------------


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
    final_context = result.get("final_context", {})
    layout_payload = final_context.get("layout")
    if layout_payload is None and final_context.get("layout_id"):
        layout_payload = final_context

    return {
        "message": result["response"],
        "tool_calls_made": result.get("tool_calls_made", []),
        "layout": layout_payload,
        "final_context": final_context,
        "iterations": result.get("iterations", 0),
    }


# ---------------------------------------------------------------------------
# 4. POST /ai/detect-conflicts — conflict detector agent
# ---------------------------------------------------------------------------


@router.post("/detect-conflicts")
async def route_detect_conflicts(
    data: AIDetectConflictsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    result = await run_agent(
        agent_type="conflict_detector",
        user_message="Analyse all operational conflicts and provide a risk assessment.",
        context={"request_id": str(data.request_id)},
        db=db,
    )
    return {
        "message": result["response"],
        "tool_calls_made": result.get("tool_calls_made", []),
        "conflicts": result.get("final_context", {}).get("conflicts", []),
        "has_blocking_conflicts": result.get("final_context", {}).get("has_blocking_conflicts", False),
        "iterations": result.get("iterations", 0),
    }


# ---------------------------------------------------------------------------
# 5. POST /ai/generate-tasks/{request_id} — planner agent
# ---------------------------------------------------------------------------


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
        "tool_calls_made": result.get("tool_calls_made", []),
        "tasks_created": result.get("final_context", {}).get("tasks_created", 0),
        "tasks": result.get("final_context", {}).get("tasks", []),
        "iterations": result.get("iterations", 0),
    }


# ---------------------------------------------------------------------------
# 6. POST /ai/intake/{request_id} — trigger intake agent manually
# ---------------------------------------------------------------------------


@router.post("/intake/{request_id}")
async def route_ai_intake(
    request_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    """Manually re-trigger the intake agent for an existing event request."""
    background_tasks.add_task(_run_intake_background, request_id)
    return {"status": "queued", "request_id": str(request_id)}


async def _run_intake_background(request_id: UUID) -> None:
    from app.services import check_conflicts, conflicts_to_dict, get_request, update_ai_proposal

    async with AsyncSessionLocal() as db:
        req = await get_request(request_id, db)
        context = {
            "request_id": str(req.id),
            "event_type": req.event_type,
            "attendee_count": req.attendee_count,
            "requested_date": str(req.requested_date),
            "start_time": str(req.start_time),
            "end_time": str(req.end_time),
            "special_requirements": req.special_requirements or "",
        }
        result = await run_agent(
            agent_type="intake",
            user_message=f"Analyse request '{req.title}' and propose the best venue, assets, and quotation.",
            context=context,
            db=db,
        )
        conflicts = await check_conflicts(req.id, db)
        await update_ai_proposal(
            req.id,
            {
                "status": "complete",
                "summary": result["response"],
                "tool_calls": result.get("tool_calls_made", []),
                "conflicts": conflicts_to_dict(conflicts),
                "estimate": result.get("final_context", {}).get("estimate"),
                "recommended_venue": result.get("final_context", {}).get("recommended_venue"),
            },
            db,
        )


# ---------------------------------------------------------------------------
# 7. GET /ai/conversations — list current user's conversations
# ---------------------------------------------------------------------------


@router.get("/conversations", response_model=PaginatedResponse[AIConversationSummary])
async def route_list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[AIConversationSummary]:
    stmt = (
        select(AiConversation)
        .where(AiConversation.user_id == current_user.id)
        .order_by(AiConversation.updated_at.desc())
        .limit(50)
    )
    rows = list((await db.scalars(stmt)).all())
    items = [
        AIConversationSummary(
            id=c.id,
            agent_type=c.agent_type,
            message_count=len(c.messages or []),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in rows
    ]
    return PaginatedResponse(items=items, total=len(items), limit=50, offset=0)


# ---------------------------------------------------------------------------
# 8. GET /ai/conversations/{conversation_id} — get full conversation
# ---------------------------------------------------------------------------


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetail)
async def route_get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIConversationDetail:
    conv = await db.get(AiConversation, conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return AIConversationDetail(
        id=conv.id,
        agent_type=conv.agent_type,
        messages=conv.messages or [],
        context_json=conv.context_json or {},
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


# ---------------------------------------------------------------------------
# 9. DELETE /ai/conversations/{conversation_id} — delete conversation
# ---------------------------------------------------------------------------


@router.delete("/conversations/{conversation_id}", status_code=204)
async def route_delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    conv = await db.get(AiConversation, conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    await db.delete(conv)
    await db.commit()


# ---------------------------------------------------------------------------
# 10. GET /ai/tools — list all registered tools
# ---------------------------------------------------------------------------


@router.get("/tools", response_model=list[AIToolInfo])
async def route_list_tools(
    _: User = Depends(require_staff),
) -> list[AIToolInfo]:
    from app.ai.tools import AGENT_TOOL_SCHEMAS, TOOL_EXECUTORS

    # Build a tool → agent_types mapping
    tool_agents: dict[str, list[str]] = {}
    for agent_type, schemas in AGENT_TOOL_SCHEMAS.items():
        for schema in schemas:
            name = schema["function"]["name"]
            tool_agents.setdefault(name, []).append(agent_type)

    result: list[AIToolInfo] = []
    for name in TOOL_EXECUTORS:
        description = ""
        for schemas in AGENT_TOOL_SCHEMAS.values():
            for s in schemas:
                if s["function"]["name"] == name:
                    description = s["function"].get("description", "")
                    break
            if description:
                break
        result.append(
            AIToolInfo(
                name=name,
                description=description,
                agent_types=tool_agents.get(name, []),
            )
        )
    return result
