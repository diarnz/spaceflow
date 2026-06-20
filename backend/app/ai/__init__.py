"""
SpaceFlow Agentic AI — public API.

Primary entry point: run_agent()
  - Attempts the full ReAct engine (multi-turn tool-calling over OpenRouter).
  - Falls back to the deterministic legacy implementation when the LLM is
    unavailable or raises an unrecoverable error.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_agent(
    agent_type: str,
    user_message: str,
    context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Unified agent entry point.

    Tries the ReAct engine first; on any failure falls back to the
    rule-based legacy implementation so the application always returns
    a useful response.
    """
    from app.config import settings

    if settings.OPENROUTER_API_KEY:
        try:
            from app.ai.agent import run_react_agent

            result = await run_react_agent(
                agent_type=agent_type,
                user_message=user_message,
                context=context,
                conversation_history=conversation_history,
                db=db,
            )
            # Normalise: legacy returns tool_calls_made, agent returns same key
            if "tool_calls_made" not in result:
                result["tool_calls_made"] = []
            if "final_context" not in result:
                result["final_context"] = {}
            return result
        except Exception as exc:
            logger.warning(
                "ReAct agent failed for '%s' (%s), falling back to legacy.",
                agent_type,
                exc,
            )
            if agent_type == "room_designer" and db is not None:
                try:
                    return await _run_direct_room_designer_fallback(user_message, context, db)
                except Exception as fallback_exc:
                    logger.warning("Direct room designer fallback failed (%s). Continuing to legacy.", fallback_exc)

    # ---- Legacy fallback ----
    from app.ai._legacy import run_agent_legacy

    return await run_agent_legacy(
        agent_type=agent_type,
        user_message=user_message,
        context=context,
        conversation_history=conversation_history,
        db=db,
    )


async def _run_direct_room_designer_fallback(
    user_message: str,
    context: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Deterministic room-designer fallback used when the paid/tool-calling LLM path
    is unavailable. This ensures layout quality does not depend on OpenRouter.
    """
    from app.ai.tools import layout_tools

    venue_name = str(context.get("venue_name") or "").strip()
    if not venue_name:
        return {
            "response": "Room design requires a venue name.",
            "tool_calls_made": [],
            "final_context": {"error": "venue_name missing"},
        }

    parsed = await layout_tools.parse_design_prompt(
        {"prompt": user_message, "venue_name": venue_name},
        db,
    )
    if parsed.get("error"):
        return {
            "response": str(parsed["error"]),
            "tool_calls_made": [{"tool": "parse_design_prompt", "args": {"prompt": user_message, "venue_name": venue_name}, "result": parsed}],
            "final_context": parsed,
        }

    layout = await layout_tools.generate_and_apply_layout(
        {
            "venue_name": venue_name,
            "prompt": user_message,
            "event_request_id": context.get("event_request_id"),
            "start_datetime": context.get("event_date_start"),
            "end_datetime": context.get("event_date_end"),
        },
        db,
    )

    tool_calls = [
        {
            "tool": "parse_design_prompt",
            "args": {"prompt": user_message, "venue_name": venue_name},
            "result": parsed,
        },
        {
            "tool": "generate_and_apply_layout",
            "args": {"venue_name": venue_name, "prompt": user_message},
            "result": layout,
        },
    ]

    if layout.get("error"):
        return {
            "response": str(layout["error"]),
            "tool_calls_made": tool_calls,
            "final_context": layout,
        }

    response = (
        f"I composed a custom {layout.get('layout_style', 'room')} layout in {venue_name} "
        f"with {layout.get('placed_seats', 0)} seats and {layout.get('item_count', 0)} items."
    )
    models_used = layout.get("models_used") or []
    if models_used:
        response += f" Models used: {', '.join(models_used)}."
    limitations = layout.get("limitations") or []
    if limitations:
        response += " Current constraints: " + "; ".join(limitations)

    return {
        "response": response,
        "tool_calls_made": tool_calls,
        "final_context": layout,
    }
