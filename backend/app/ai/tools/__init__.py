"""
SpaceFlow AI Tool Registry.

Provides:
  - AGENT_TOOL_SCHEMAS   mapping agent_type → list of OpenRouter tool schemas
  - TOOL_EXECUTORS       mapping tool_name   → async executor(args, db) function
"""
from __future__ import annotations

from typing import Any, Callable, Coroutine

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools import inventory_tools, layout_tools, quotation_tools, task_tools, venue_tools

# ---------------------------------------------------------------------------
# Executor type alias
# ---------------------------------------------------------------------------
Executor = Callable[[dict[str, Any], AsyncSession], Coroutine[Any, Any, dict[str, Any]]]

# ---------------------------------------------------------------------------
# Tool schemas grouped by agent type
# ---------------------------------------------------------------------------

AGENT_TOOL_SCHEMAS: dict[str, list[dict[str, Any]]] = {
    "intake": (
        venue_tools.TOOL_SCHEMAS
        + inventory_tools.TOOL_SCHEMAS
        + quotation_tools.TOOL_SCHEMAS
        + task_tools.TOOL_SCHEMAS[:2]  # detect_conflicts + generate_operational_tasks
    ),
    "room_designer": (
        layout_tools.TOOL_SCHEMAS
        + inventory_tools.TOOL_SCHEMAS[-1:]  # get_available_3d_models
    ),
    "conflict_detector": (
        task_tools.TOOL_SCHEMAS[:1]  # detect_conflicts
        + venue_tools.TOOL_SCHEMAS[2:3]  # check_venue_availability
        + inventory_tools.TOOL_SCHEMAS[1:3]  # check_asset_availability + check_assets_bulk
    ),
    "planner": (
        task_tools.TOOL_SCHEMAS  # all task tools
        + venue_tools.TOOL_SCHEMAS[:1]  # list_active_venues
        + quotation_tools.TOOL_SCHEMAS[1:]  # get_request_quotation
    ),
    "copilot": (
        venue_tools.TOOL_SCHEMAS
        + inventory_tools.TOOL_SCHEMAS
        + quotation_tools.TOOL_SCHEMAS
        + task_tools.TOOL_SCHEMAS
        + layout_tools.TOOL_SCHEMAS
    ),
}

# ---------------------------------------------------------------------------
# Flat executor map (tool_name → async function)
# ---------------------------------------------------------------------------

TOOL_EXECUTORS: dict[str, Executor] = {
    # venue
    "list_active_venues": venue_tools.list_active_venues,
    "get_venue_detail": venue_tools.get_venue_detail,
    "check_venue_availability": venue_tools.check_venue_availability,
    "recommend_venues_for_event": venue_tools.recommend_venues_for_event,
    # inventory
    "list_inventory": inventory_tools.list_inventory,
    "check_asset_availability": inventory_tools.check_asset_availability,
    "check_assets_bulk": inventory_tools.check_assets_bulk,
    "get_available_3d_models": inventory_tools.get_available_3d_models,
    # layout
    "parse_design_prompt": layout_tools.parse_design_prompt,
    "generate_and_apply_layout": layout_tools.generate_and_apply_layout,
    "list_room_layouts": layout_tools.list_room_layouts,
    # quotation
    "estimate_quotation": quotation_tools.estimate_quotation,
    "get_request_quotation": quotation_tools.get_request_quotation,
    # tasks / conflicts
    "detect_conflicts": task_tools.detect_conflicts,
    "generate_operational_tasks": task_tools.generate_operational_tasks,
    "list_request_tasks": task_tools.list_request_tasks,
    "get_request_summary": task_tools.get_request_summary,
}


def get_tools_for_agent(agent_type: str) -> list[dict[str, Any]]:
    """Return the OpenRouter tool schema list for the given agent type."""
    return AGENT_TOOL_SCHEMAS.get(agent_type, AGENT_TOOL_SCHEMAS["copilot"])


async def execute_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Dispatch a tool call to its executor. Raises KeyError if unknown."""
    executor = TOOL_EXECUTORS.get(tool_name)
    if executor is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return await executor(tool_args, db)
