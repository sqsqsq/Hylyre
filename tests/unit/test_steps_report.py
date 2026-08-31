"""steps-file batch -> ScenarioRunResult synthesis (Step Outcome Protocol v1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hylyre.api.outcome import ActionObservation, Failure, OperationFailed, OperationPassed
from hylyre.scenario.ledger import step_result_to_batch_row
from hylyre.scenario.step_builder import build_step_result
from hylyre.scenario.steps_report import steps_batch_to_scenario_result


def _row(index: int, outcome, *, kind: str = "touch", role: str = "action") -> dict:
    step = build_step_result(
        outcome, index=index, kind=kind, role=role, device_session=False
    )
    return step_result_to_batch_row(step, {kind: {"by_text": "x"}})


def test_steps_batch_to_scenario_result_maps_cases() -> None:
    batch = {
        "results": [
            _row(0, OperationPassed(observation=ActionObservation("touch"))),
            _row(
                1,
                OperationFailed(
                    failure=Failure("selector", "selector.not_found"),
                    observation=ActionObservation("touch", False),
                    diagnostic="not found",
                ),
            ),
        ]
    }
    result = steps_batch_to_scenario_result(
        feature="wallet-x",
        steps_path=Path("nav.json"),
        batch=batch,
        bundle="com.example.app",
        page_name="MainAbility",
    )
    assert result.feature == "wallet-x"
    # One batch is one case: prior_step causality is only defined inside a
    # case, so per-row cases would strand every abort-suffix reference.
    assert len(result.case_results) == 1
    case = result.case_results[0]
    assert case.case_id if hasattr(case, "case_id") else case.case.case_id
    assert case.case.case_id == "STEPS-BATCH"
    assert [s.index for s in case.steps] == [0, 1]
    assert case.status == "失败"
    assert "not found" in case.notes

    call = result.tool_calls[1]
    assert call["kind"] == "touch"
    assert call["outcome"]["failure"] == {
        "domain": "selector",
        "code": "selector.not_found",
    }


def test_batch_row_without_step_result_is_refused() -> None:
    """P0-7: a missing ledger row is a wiring bug, never a status to guess from.

    0.3-p0 inferred `capability`/`infrastructure` from a row's flat status here,
    which is how a batch could invent a classification nothing observed.
    """

    batch = {"results": [{"index": 0, "step": {"touch": {}}, "status": "error"}]}
    with pytest.raises(ValueError, match="no step_result"):
        steps_batch_to_scenario_result(
            feature="x", steps_path=Path("nav.json"), batch=batch
        )
