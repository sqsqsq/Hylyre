"""Dispatch one planned JSON step dict to HylyreAgent (shared by scenario runner and batch steps)."""

from __future__ import annotations

from typing import Any

from hylyre.api.agent import HylyreAgent


async def dispatch_planned_step(
    agent: HylyreAgent,
    payload: dict[str, Any],
    *,
    case_id: str = "step",
) -> None:
    """Run a single planned step object (same root keys as test-plan rows after ``json.loads``)."""
    if "action" in payload:
        await agent.run_planned_action(payload)
    elif "touch" in payload:
        await agent.run_planned_tap(payload)
    elif "input" in payload:
        await agent.run_planned_input(payload)
    elif "swipe" in payload:
        await agent.run_planned_swipe(payload)
    elif "scroll" in payload:
        await agent.run_planned_scroll(payload)
    else:
        raise ValueError(
            f"{case_id}: JSON step must contain one of: action, touch, input, swipe, scroll"
        )
