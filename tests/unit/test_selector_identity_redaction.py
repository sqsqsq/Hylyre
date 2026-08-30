"""0.4.1 regressions for structured selector identity redaction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from hylyre.api.agent import HylyreAgent
from hylyre.api.exceptions import AssertionMismatch, SelectorResolutionError
from hylyre.cli.__main__ import app
from hylyre.cli.commands import steps_cmd
from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.results import (
    StepResult,
    redact_evidence,
    result_from_exception,
)
from hylyre.scenario.runner import ScenarioRunner

from tests.contract.fakes.fake_ui_driver import FakeUiDriver


IDENTITY_KEYS = ("by_id", "by_key", "id", "key", "selected_id")
IDENTITY_VALUES = (
    "hc_bank_card_row",
    "amount_input",
    "account_selector",
    "phone_entry",
    "bank_card_agreement_span",
    "card_123456_container",
)


def _node(attrs: dict[str, Any], *children: dict[str, Any]) -> dict[str, Any]:
    return {"attributes": attrs, "children": list(children)}


def _root(*children: dict[str, Any]) -> dict[str, Any]:
    return _node({"type": "Root", "bounds": "[0,0][500,800]"}, *children)


def _write_plan(
    path: Path, step: str, *, case_id: str = "TC-SELECTOR", expected: str = "-"
) -> None:
    path.write_text(
        "# fixture\n\n## 测试用例清单\n\n"
        "| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        f"| {case_id} | selector identity | | {step} | {expected} | P0 | AC-SELECTOR |\n",
        encoding="utf-8",
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


@pytest.mark.parametrize("key", IDENTITY_KEYS)
@pytest.mark.parametrize("identity", IDENTITY_VALUES)
def test_selector_identity_matrix_is_verbatim(key: str, identity: str) -> None:
    serialized = redact_evidence({key: identity})
    assert serialized[key] == identity


@pytest.mark.parametrize("key", IDENTITY_KEYS)
def test_selector_identity_null_is_preserved(key: str) -> None:
    assert redact_evidence({key: None})[key] is None


def test_selector_identity_values_do_not_collide() -> None:
    outputs = [
        redact_evidence({"selected_id": identity})["selected_id"]
        for identity in ("hc_bank_card_row", "amount_input")
    ]
    assert outputs == ["hc_bank_card_row", "amount_input"]
    assert outputs[0] != outputs[1]


def test_identity_container_recurses_into_text_fields() -> None:
    payload = {
        "selected_id": {
            "id": "card_123456_container",
            "key": "account_selector",
            "text": "account: 6222021234567890",
            "nested": {"value": "amount: 1000.00"},
        }
    }
    serialized = redact_evidence(payload)
    assert serialized["selected_id"]["id"] == "card_123456_container"
    assert serialized["selected_id"]["key"] == "account_selector"
    assert serialized["selected_id"]["text"] == "[REDACTED]"
    assert serialized["selected_id"]["nested"]["value"] == "[REDACTED]"

    list_serialized = redact_evidence(
        {
            "selected_id": [
                "account: 6222021234567890",
                {"reason": "amount: 1000.00"},
            ]
        }
    )
    assert list_serialized["selected_id"] == [
        "[REDACTED]",
        {"reason": "[REDACTED]"},
    ]


def test_text_and_value_fields_remain_redacted() -> None:
    sensitive = {
        "account": "account: 6222021234567890",
        "amount": "amount: 1000.00",
        "phone": "phone: 13800138000",
        "card": "card: 6222021234567890",
        "text": "card: 6222021234567890",
        "value": "amount: 1000.00",
        "instruction": "向账号 6222021234567890 转账 1000 元",
        "expected": "account: 6222021234567890 amount: 1000.00",
        "actual": "phone: 13800138000",
        "expected_text": "account: 6222021234567890",
        "actual_text": "amount: 1000.00",
        "event_text": "card: 6222021234567890",
        "input_value": "13800138000",
        "by_text": "账户 6222021234567890",
        "by_value": "card: 6222021234567890",
        "error": "account: 6222021234567890 amount: 1000.00",
        "notes": "phone: 13800138000",
    }
    serialized = redact_evidence(sensitive)
    encoded = _json(serialized)
    for raw in sensitive.values():
        assert raw not in encoded
    assert serialized["expected"] == "[REDACTED]"
    assert serialized["actual"] == "[REDACTED]"


def test_success_step_result_keeps_selected_id_and_redacts_text() -> None:
    step = StepResult(
        index=0,
        kind="touch",
        role="action",
        status="passed",
        selector={
            "engine": "resolver",
            "requested_match": "exact",
            "effective_match": "exact",
            "candidate_count": 1,
            "selected_id": "hc_bank_card_row",
            "bounds": "[0,0][100,100]",
        },
        evidence={
            "expected": "account: 6222021234567890",
            "actual": "amount: 1000.00",
        },
        error="account: 6222021234567890 amount: 1000.00",
    )
    serialized = step.to_dict()
    assert serialized["selector"]["selected_id"] == "hc_bank_card_row"
    assert serialized["selector"]["bounds"] == "[0,0][100,100]"
    assert serialized["evidence"] == {
        "expected": "[REDACTED]",
        "actual": "[REDACTED]",
    }
    assert "6222021234567890" not in _json(serialized)
    assert "1000.00" not in _json(serialized)


def test_failure_step_results_preserve_identity_and_failure_codes() -> None:
    for failure_code, selected_id in (
        ("selector_not_found", "account_selector"),
        ("inline_target_unresolvable", "bank_card_agreement_span"),
    ):
        exc = SelectorResolutionError(
            "account: 6222021234567890 amount: 1000.00",
            failure_code=failure_code,
            selector={
                "engine": "resolver",
                "requested_match": "contains",
                "effective_match": "contains",
                "candidate_count": 1,
                "selected_id": selected_id,
                "bounds": None,
            },
            evidence={
                "candidates": [
                    {
                        "id": "hc_bank_card_row",
                        "key": "amount_input",
                        "text": "account: 6222021234567890",
                    }
                ]
            },
        )
        step = result_from_exception(
            exc=exc,
            index=0,
            kind="touch",
            role="action",
            duration_ms=1.0,
        )
        serialized = step.to_dict()
        assert serialized["failure_kind"] == "selector"
        assert serialized["failure_code"] == failure_code
        assert serialized["selector"]["selected_id"] == selected_id
        candidate = serialized["evidence"]["candidates"][0]
        assert candidate["id"] == "hc_bank_card_row"
        assert candidate["key"] == "amount_input"
        assert candidate["text"] == "[REDACTED]"
        assert "6222021234567890" not in _json(serialized)
        assert "1000.00" not in _json(serialized)


def test_vlm_assertion_reason_is_redacted_at_step_serialization() -> None:
    reason = "account: 6222021234567890 amount: 1000.00 phone: 13800138000"
    with pytest.raises(AssertionMismatch) as caught:
        HylyreAgent.interpret_assert_payload({"ok": False, "reason": reason})

    step = result_from_exception(
        exc=caught.value,
        index=0,
        kind="expected_check",
        role="assertion",
        duration_ms=1.0,
    )
    serialized = step.to_dict()
    assert serialized["failure_kind"] == "assertion"
    assert serialized["failure_code"] == "assertion_mismatch"
    assert serialized["evidence"]["reason"] == (
        "[REDACTED] [REDACTED] [REDACTED]"
    )
    for secret in ("6222021234567890", "1000.00", "13800138000"):
        assert secret not in _json(serialized)


@pytest.mark.asyncio
async def test_ambiguous_plan_trace_preserves_candidate_identity(tmp_path: Path) -> None:
    repeated_text = "账户 6222021234567890"
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "hc_bank_card_row",
                "key": "account_selector",
                "text": repeated_text,
                "bounds": "[0,0][200,40]",
                "clickable": "true",
            }
        ),
        _node(
            {
                "type": "Button",
                "id": "amount_input",
                "key": "phone_entry",
                "text": repeated_text,
                "bounds": "[0,100][200,140]",
                "clickable": "true",
            }
        ),
    )
    plan = tmp_path / "ambiguous.md"
    _write_plan(plan, json.dumps({"touch": {"by_text": repeated_text}}, ensure_ascii=False))
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        plan,
        feature="selector-identity-failure",
        check_expected=False,
    )
    step = result.case_results[0].steps[0]
    serialized_step = step.to_dict()
    assert serialized_step["failure_kind"] == "selector"
    assert serialized_step["failure_code"] == "selector_ambiguous"
    candidates = serialized_step["evidence"]["candidates"]
    assert [(row["id"], row["key"], row["bounds"]) for row in candidates] == [
        ("hc_bank_card_row", "account_selector", "[0,0][200,40]"),
        ("amount_input", "phone_entry", "[0,100][200,140]"),
    ]
    assert all(row["text"] == "[REDACTED]" for row in candidates)

    report = tmp_path / "ambiguous-report.md"
    trace = tmp_path / "ambiguous-trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)
    trace_data = json.loads(trace.read_text(encoding="utf-8"))
    trace_step = trace_data["cases"][0]["steps"][0]
    assert trace_step["evidence"]["candidates"][0]["id"] == "hc_bank_card_row"
    assert trace_step["evidence"]["candidates"][1]["id"] == "amount_input"
    assert "6222021234567890" not in trace.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_plan_run_trace_keeps_success_selected_id(tmp_path: Path) -> None:
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "hc_bank_card_row",
                "key": "account_selector",
                "text": "ready",
                "bounds": "[0,0][100,40]",
            }
        )
    )
    plan = tmp_path / "success.md"
    _write_plan(
        plan,
        json.dumps(
            {"wait_for": {"by_id": "hc_bank_card_row", "timeout": 1}},
            ensure_ascii=False,
        ),
        case_id="TC-SUCCESS",
    )
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        plan,
        feature="selector-identity-success",
        check_expected=False,
    )
    assert result.case_results[0].steps[0].to_dict()["selector"]["selected_id"] == (
        "hc_bank_card_row"
    )
    report = tmp_path / "success-report.md"
    trace = tmp_path / "success-trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)
    trace_data = json.loads(trace.read_text(encoding="utf-8"))
    assert trace_data["schema_version"] == "0.3-p0"
    assert trace_data["cases"][0]["steps"][0]["selector"]["selected_id"] == (
        "hc_bank_card_row"
    )
    assert trace_data["tool_calls"] == list(result.tool_calls)


@pytest.mark.asyncio
async def test_steps_file_batch_keeps_raw_identity_and_step_result() -> None:
    steps = [{"wait_for": {"by_id": "hc_bank_card_row", "timeout": 1}}]
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "hc_bank_card_row",
                "text": "ready",
                "bounds": "[0,0][100,40]",
            }
        )
    )
    batch = await steps_cmd.run_steps_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)), steps
    )
    row = batch["results"][0]
    assert row["step"]["wait_for"]["by_id"] == "hc_bank_card_row"
    assert row["step_result"]["selector"]["selected_id"] == "hc_bank_card_row"


def test_cli_steps_file_final_trace_uses_same_identity_ledger(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "hc_bank_card_row",
                "text": "ready",
                "bounds": "[0,0][100,40]",
            }
        )
    )

    async def fake_with_hypium(
        *, device_sn=None, mock_port=None, lyrebird_url=None, fn=None
    ):
        _ = (device_sn, mock_port, lyrebird_url)
        assert fn is not None
        return await fn(HylyreAgent(ui=FakeUiDriver(dump_tree=tree)))

    monkeypatch.setattr(steps_cmd, "_with_hypium_agent", fake_with_hypium)
    steps_path = tmp_path / "steps.json"
    steps_path.write_text(
        json.dumps(
            [{"wait_for": {"by_id": "hc_bank_card_row", "timeout": 1}}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report = tmp_path / "cli-report.md"
    trace = tmp_path / "cli-trace.json"
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--steps-file",
            str(steps_path),
            "--feature",
            "cli-selector-identity",
            "--report-out",
            str(report),
            "--trace-out",
            str(trace),
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    trace_data = json.loads(trace.read_text(encoding="utf-8"))
    assert trace_data["schema_version"] == "0.3-p0"
    assert trace_data["cases"][0]["steps"][0]["selector"]["selected_id"] == (
        "hc_bank_card_row"
    )
    assert trace_data["tool_calls"] == [
        {
            "case": "STEP-000",
            "index": 0,
            "kind": "wait_for",
            "role": "assertion",
            "status": "passed",
            "failure_kind": None,
            "failure_code": None,
        }
    ]
