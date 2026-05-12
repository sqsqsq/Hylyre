"""Run scenarios from a test plan."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
            raise NotImplementedError(
                "Real-device scenario runs are not implemented yet; "
                "use --use-fakes for CI and fixture runs."
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

