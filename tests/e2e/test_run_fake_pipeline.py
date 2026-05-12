"""E2E: fake scenario run + verify (no subprocess)."""

from __future__ import annotations

from pathlib import Path

from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.runner import ScenarioRunner

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "e2e" / "fixtures" / "mock-test-plan.md"


def test_full_fake_pipeline(tmp_path: Path) -> None:
    report = tmp_path / "out" / "test-report.md"
    trace = tmp_path / "out" / "trace.json"
    runner = ScenarioRunner(use_fakes=True)
    result = runner.run_plan_file(FIXTURE, feature="e2e-mock")
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, FIXTURE) is True
