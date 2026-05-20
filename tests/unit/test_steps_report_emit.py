"""Verify steps-batch synthesis produces L5-valid artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.steps_report import steps_batch_to_scenario_result


def test_steps_report_writes_verifiable_trace(tmp_path: Path) -> None:
    steps_path = tmp_path / "nav.json"
    steps_path.write_text("[]", encoding="utf-8")
    batch = {
        "results": [
            {"index": 0, "step": {"touch": {"by_text": "OK"}}, "status": "ok"},
        ]
    }
    result = steps_batch_to_scenario_result(
        feature="feat-x",
        steps_path=steps_path,
        batch=batch,
    )
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    write_run_artifacts(
        result, report_path=report, trace_path=trace, model_backend="none"
    )
    verify_report(report, trace, None)
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data["feature"] == "feat-x"
    assert data["cases"][0]["id"] == "STEP-000"
