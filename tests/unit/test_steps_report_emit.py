"""Verify steps-batch synthesis produces L5-valid artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.api.outcome import ActionObservation, OperationPassed
from hylyre.contracts import RESULT_PROTOCOL, TRACE_SCHEMA_V1
from hylyre.scenario.ledger import step_result_to_batch_row
from hylyre.scenario.step_builder import build_step_result
from hylyre.scenario.steps_report import steps_batch_to_scenario_result


def test_steps_report_writes_verifiable_trace(tmp_path: Path) -> None:
    steps_path = tmp_path / "nav.json"
    steps_path.write_text("[]", encoding="utf-8")
    step = build_step_result(
        OperationPassed(observation=ActionObservation("touch")),
        index=0,
        kind="touch",
        role="action",
        device_session=False,
    )
    batch = {"results": [step_result_to_batch_row(step, {"touch": {"by_text": "OK"}})]}
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
    assert data["schema_version"] == TRACE_SCHEMA_V1
    assert data["result_protocol"] == RESULT_PROTOCOL
    assert data["cases"][0]["id"] == "STEPS-BATCH"
