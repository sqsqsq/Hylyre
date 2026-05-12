"""Run scenarios from a test plan."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hylyre.api.agent import HylyreAgent
from hylyre.scenario.plan_parse import ParsedPlan, TestCase, parse_test_plan


@dataclass(frozen=True)
class CaseResult:
    case: TestCase
    status: str
    notes: str


def resolved_outcome(result: ScenarioRunResult) -> str:
    statuses = [r.status for r in result.case_results]
    if all(s == "通过" for s in statuses):
        return "success"
    if any(s == "失败" for s in statuses) and any(s == "通过" for s in statuses):
        return "partial"
    if any(s == "失败" for s in statuses) or any(s == "阻塞" for s in statuses):
        return "failed"
    return "success"


@dataclass(frozen=True)
class ScenarioRunResult:
    feature: str
    plan: ParsedPlan
    case_results: tuple[CaseResult, ...]
    use_fakes: bool
    tool_calls: tuple[dict[str, Any], ...] = ()


class ScenarioRunner:
    """Execute plan rows; fake mode is deterministic without devices."""

    def __init__(self, *, use_fakes: bool = False) -> None:
        self._use_fakes = use_fakes

    def run_plan_file(
        self,
        plan_path: Path | str,
        *,
        feature: str,
    ) -> ScenarioRunResult:
        if not self._use_fakes:
            raise ValueError(
                "Real-device runs use run_plan_on_agent(); "
                "pass use_fakes=True for run_plan_file()."
            )
        plan = parse_test_plan(plan_path)
        results: list[CaseResult] = []
        for case in plan.cases:
            status, notes = self._fake_execute(case)
            results.append(CaseResult(case=case, status=status, notes=notes))
        return ScenarioRunResult(
            feature=feature,
            plan=plan,
            case_results=tuple(results),
            use_fakes=True,
            tool_calls=(),
        )

    async def run_plan_on_agent(
        self,
        agent: HylyreAgent,
        plan_path: Path | str,
        *,
        feature: str,
        bundle: str | None = None,
        mock_group: str | None = None,
        check_expected: bool = True,
    ) -> ScenarioRunResult:
        """Drive ``HylyreAgent`` from plan rows (Hypium + optional VLM / Lyrebird)."""
        if self._use_fakes:
            raise ValueError("run_plan_on_agent requires ScenarioRunner(use_fakes=False)")
        plan = parse_test_plan(plan_path)
        tool_log: list[dict[str, Any]] = []
        if agent.mock_controller is not None and mock_group:
            await agent.mock_activate_group(mock_group)
            tool_log.append({"kind": "mock_activate_group", "group": mock_group})
        if bundle:
            await agent.start_app(bundle)
            tool_log.append({"kind": "start_app", "bundle": bundle})
        results: list[CaseResult] = []
        for case in plan.cases:
            try:
                await self._run_case_on_agent(
                    agent, case, tool_log, check_expected=check_expected
                )
                results.append(CaseResult(case=case, status="通过", notes=""))
            except Exception as e:
                results.append(
                    CaseResult(case=case, status="失败", notes=str(e)[:2000])
                )
        return ScenarioRunResult(
            feature=feature,
            plan=plan,
            case_results=tuple(results),
            use_fakes=False,
            tool_calls=tuple(tool_log),
        )

    async def _run_case_on_agent(
        self,
        agent: HylyreAgent,
        case: TestCase,
        tool_log: list[dict[str, Any]],
        *,
        check_expected: bool,
    ) -> None:
        for step in _iter_steps(case.steps):
            await _execute_one_step(agent, case.case_id, step, tool_log)
        if (
            check_expected
            and case.expected.strip()
            and agent.vlm is not None
        ):
            try:
                await agent.ai_assert(case.expected.strip())
            except AssertionError as e:
                raise AssertionError(
                    f"预期结果不满足 ({case.case_id}): {e}"
                ) from e
            tool_log.append(
                {
                    "case": case.case_id,
                    "kind": "ai_assert",
                    "instruction": case.expected.strip()[:200],
                }
            )

    @staticmethod
    def _fake_execute(case: TestCase) -> tuple[str, str]:
        if case.case_id.upper().endswith("-FAIL"):
            return "失败", "fake mode: case id suffix -FAIL forces failure"
        if "阻塞" in case.steps or case.case_id.upper().endswith("-BLOCK"):
            return "阻塞", "fake mode: blocked"
        if "跳过" in case.steps or case.case_id.upper().endswith("-SKIP"):
            return "跳过", "fake mode: skipped"
        return "通过", "fake mode: stub pass"


def _iter_steps(text: str) -> list[str]:
    normalized = text.replace("；", "\n").replace(";", "\n")
    return [ln.strip() for ln in normalized.splitlines() if ln.strip()]


_JSONISH = re.compile(r"^\s*\{.*\}\s*$", re.DOTALL)


async def _execute_one_step(
    agent: HylyreAgent,
    case_id: str,
    step: str,
    tool_log: list[dict[str, Any]],
) -> None:
    s = step.strip()
    if not s:
        return
    if _JSONISH.match(s):
        payload = json.loads(s)
        if "action" in payload:
            await agent.run_planned_action(payload)
        elif "touch" in payload:
            await agent.run_planned_tap(payload)
        elif "input" in payload:
            await agent.run_planned_input(payload)
        else:
            raise ValueError(
                f"{case_id}: JSON step must contain action, touch, or input key"
            )
        tool_log.append({"case": case_id, "kind": "planned_json", "payload": payload})
        return
    if agent.vlm is None:
        raise ValueError(
            f"{case_id}: 非 JSON 的测试步骤需要配置 VLM（HYLYRE_VLM_ENDPOINT 等）"
            f"，或在计划中使用单行 JSON：`"
            f'{{"action":{{"type":"touch","by_text":"…"}}}}`'
        )
    await agent.ai_action(s)
    tool_log.append({"case": case_id, "kind": "ai_action", "instruction": s[:500]})
