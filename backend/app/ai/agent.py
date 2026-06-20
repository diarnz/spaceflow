"""
SpaceFlow ReAct Agent Engine.

Implements a multi-turn tool-calling loop over the OpenRouter API.
Each turn:
  1. Send messages + tool schemas to the LLM.
  2. If the model requests tool calls, execute them and append results.
  3. Repeat until the model produces a final text response or max_iterations hit.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import get_system_prompt
from app.ai.tools import execute_tool, get_tools_for_agent
from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Hard ceiling on ReAct iterations to prevent infinite loops
MAX_ITERATIONS = 8


async def run_react_agent(
    agent_type: str,
    user_message: str,
    context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Main entry point for the ReAct agent loop.

    Returns a dict with:
      response         — final assistant text
      tool_calls_made  — list of {tool, args, result} dicts
      iterations       — number of LLM turns used
    """
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured — cannot run ReAct agent.")
    if db is None:
        raise ValueError(f"Agent '{agent_type}' requires a database session.")

    system_prompt = get_system_prompt(agent_type)
    tools = get_tools_for_agent(agent_type)

    # Build the initial context message if context dict has relevant data
    context_block = _format_context(context)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history)
    if context_block:
        messages.append({"role": "user", "content": context_block})
    messages.append({"role": "user", "content": user_message})

    tool_calls_made: list[dict[str, Any]] = []
    final_context: dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=60) as client:
        for iteration in range(MAX_ITERATIONS):
            payload: dict[str, Any] = {
                "model": settings.AI_MODEL,
                "temperature": settings.AI_TEMPERATURE,
                "max_tokens": settings.AI_MAX_TOKENS,
                "messages": messages,
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
                logger.error("OpenRouter HTTP error %s: %s", exc.response.status_code, exc.response.text)
                raise
            except Exception as exc:
                logger.error("OpenRouter request failed: %s", exc)
                raise

            data = resp.json()
            choice = data["choices"][0]
            finish_reason = choice.get("finish_reason", "")
            assistant_message = choice["message"]

            # Append assistant message to history
            messages.append(assistant_message)

            # ---------- tool_calls branch ----------
            raw_tool_calls = assistant_message.get("tool_calls") or []
            if raw_tool_calls:
                tool_results: list[dict[str, Any]] = []
                for tc in raw_tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        tool_args = json.loads(tc["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.debug("Executing tool %s with args %s", tool_name, tool_args)
                    try:
                        result = await execute_tool(tool_name, tool_args, db)
                    except Exception as exc:
                        logger.warning("Tool %s raised: %s", tool_name, exc)
                        result = {"error": str(exc)}

                    tool_calls_made.append({"tool": tool_name, "args": tool_args, "result": result})
                    _merge_tool_result(final_context, tool_name, result)
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result, default=str),
                        }
                    )

                messages.extend(tool_results)
                # Continue loop for the LLM to process tool results
                continue

            # ---------- final text response ----------
            content = assistant_message.get("content") or ""
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict)
                ).strip()
            else:
                content = str(content).strip()

            return {
                "response": content,
                "tool_calls_made": tool_calls_made,
                "final_context": final_context,
                "iterations": iteration + 1,
            }

    # Exhausted iterations without a clean stop
    last_msg = messages[-1]
    fallback_content = last_msg.get("content") or "Agent reached maximum iterations without a final response."
    if isinstance(fallback_content, list):
        fallback_content = "".join(
            p.get("text", "") for p in fallback_content if isinstance(p, dict)
        ).strip()
    return {
        "response": str(fallback_content),
        "tool_calls_made": tool_calls_made,
        "final_context": final_context,
        "iterations": MAX_ITERATIONS,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_context(context: dict[str, Any]) -> str:
    """
    Render the structured context dict as a brief natural-language block
    the LLM can reference before the user's actual question.
    """
    if not context:
        return ""
    lines: list[str] = ["[Operational context provided by the system]"]
    field_labels = {
        "request_id": "Event request ID",
        "event_type": "Event type",
        "attendee_count": "Expected attendees",
        "requested_date": "Event date",
        "start_time": "Start time",
        "end_time": "End time",
        "special_requirements": "Special requirements",
        "venue_name": "Target venue",
        "event_request_id": "Linked request ID",
        "event_date_start": "Event window start",
        "event_date_end": "Event window end",
    }
    for key, label in field_labels.items():
        val = context.get(key)
        if val is not None and val != "":
            lines.append(f"- {label}: {val}")
    # Append any extra keys not in the label map
    for key, val in context.items():
        if key not in field_labels and val is not None:
            lines.append(f"- {key}: {val}")
    return "\n".join(lines)


def _merge_tool_result(final_context: dict[str, Any], tool_name: str, result: dict[str, Any]) -> None:
    """
    Carry forward the most operationally relevant structured tool outputs so API
    routes can reliably return machine-readable data even on the ReAct path.
    """
    if not isinstance(result, dict):
        return

    if result.get("error"):
        final_context.setdefault("tool_errors", []).append(
            {"tool": tool_name, "error": result["error"]}
        )
        return

    if tool_name == "recommend_venues_for_event":
        recommendations = result.get("recommendations", [])
        final_context["venue_recommendations"] = recommendations
        final_context["recommended_venue"] = recommendations[0] if recommendations else None
        return

    if tool_name == "check_venue_availability":
        final_context["venue_availability"] = result
        return

    if tool_name == "check_assets_bulk":
        final_context["asset_check"] = result
        final_context["asset_results"] = result.get("results", [])
        return

    if tool_name == "estimate_quotation":
        final_context["estimate"] = result
        return

    if tool_name == "get_request_quotation":
        final_context["quotation"] = result
        return

    if tool_name == "detect_conflicts":
        final_context["conflicts"] = result.get("conflicts", [])
        final_context["has_blocking_conflicts"] = result.get("has_blocking", False)
        return

    if tool_name == "generate_operational_tasks":
        final_context["tasks_created"] = result.get("tasks_created", 0)
        final_context["tasks"] = result.get("tasks", [])
        return

    if tool_name == "list_request_tasks":
        final_context["tasks"] = result.get("tasks", [])
        final_context["task_count"] = result.get("task_count", len(result.get("tasks", [])))
        return

    if tool_name == "get_request_summary":
        final_context["request_summary"] = result
        return

    if tool_name == "parse_design_prompt":
        final_context["design_spec"] = result.get("spec")
        final_context["three_d_room_id"] = result.get("three_d_room_id")
        return

    if tool_name == "generate_and_apply_layout":
        final_context["layout"] = result
        final_context["layout_id"] = result.get("layout_id")
        final_context["limitations"] = result.get("limitations", [])
        return

    if tool_name == "get_available_3d_models":
        final_context["model_availability"] = result.get("model_availability", {})
