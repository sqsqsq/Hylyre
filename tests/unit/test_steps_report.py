"""Unit tests for steps-file → ScenarioRunResult synthesis."""

from __future__ import annotations

from pathlib import Path

from hylyre.scenario.steps_report import steps_batch_to_scenario_result


def test_steps_batch_to_scenario_result_maps_cases() -> None:
    batch = {
        "results": [
            {"index": 0, "step": {"touch": {"by_text": "A"}}, "status": "ok"},
            {
                "index": 1,
                "step": {"touch": {"by_text": "B"}},
                "status": "error",
                "error": "not found",
            },
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
    assert len(result.case_results) == 2
    assert result.case_results[0].case.case_id == "STEP-000"
    assert result.case_results[0].status == "通过"
    assert result.case_results[1].status == "失败"
    assert "not found" in result.case_results[1].notes
    assert result.tool_calls[0]["kind"] == "start_app"
    assert result.tool_calls[0]["page_name"] == "MainAbility"
    assert result.case_results[0].case.ac_ref == "AC-000"
