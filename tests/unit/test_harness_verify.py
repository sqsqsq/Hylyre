"""L5: verify_report."""

from __future__ import annotations

from pathlib import Path

import pytest

from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.runner import ScenarioRunner

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PLAN = ROOT / "tests" / "e2e" / "fixtures" / "mock-test-plan.md"


def test_verify_happy_path(tmp_path: Path) -> None:
    report = tmp_path / "test-report.md"
    trace = tmp_path / "trace.json"
    runner = ScenarioRunner(use_fakes=True)
    result = runner.run_plan_file(FIXTURE_PLAN, feature="mock-fixture")
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, FIXTURE_PLAN) is True


def test_verify_rejects_bad_status(tmp_path: Path) -> None:
    report = tmp_path / "test-report.md"
    trace = tmp_path / "trace.json"
    runner = ScenarioRunner(use_fakes=True)
    result = runner.run_plan_file(FIXTURE_PLAN, feature="mock-fixture")
    write_run_artifacts(result, report_path=report, trace_path=trace)
    text = report.read_text(encoding="utf-8")
    text = text.replace("| 通过 |", "| BAD |", 1)
    report.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid execution status"):
        verify_report(report, trace, FIXTURE_PLAN)
