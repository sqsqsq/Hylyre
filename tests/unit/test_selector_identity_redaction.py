"""Selector identity survives redaction; user-visible text does not.

The 0.4.1 fix (structured selector identity must stay verbatim so a target is
comparable across runs) must hold identically under Step Outcome Protocol v1,
where identity lives in ``selector.request.value`` and
``selector.resolution.selected/candidates`` instead of a flat ``selected_id``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from hylyre.api.agent import HylyreAgent
from hylyre.api.outcome import (
    ActionObservation,
    Failure,
    OperationFailed,
    OperationPassed,
    SelectorEvidence,
    SelectorRequest,
    SelectorResolution,
    expected_checked,
)
from hylyre.cli.__main__ import app
from hylyre.cli.commands import steps_cmd
from hylyre.contracts import RESULT_PROTOCOL, TRACE_SCHEMA_V1, validate_against
from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.results import redact_evidence, redact_selector
from hylyre.scenario.runner import ScenarioRunner
from hylyre.scenario.step_builder import build_step_result

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

SECRET = "6222021234567890"


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


# ------------------------------------------------- generic evidence redaction
@pytest.mark.parametrize("key", IDENTITY_KEYS)
@pytest.mark.parametrize("identity", IDENTITY_VALUES)
def test_selector_identity_matrix_is_verbatim(key: str, identity: str) -> None:
    assert redact_evidence({key: identity})[key] == identity


@pytest.mark.parametrize("key", IDENTITY_KEYS)
def test_selector_identity_null_is_preserved(key: str) -> None:
    assert redact_evidence({key: None})[key] is None


def test_selector_identity_values_do_not_collide() -> None:
    outputs = [
        redact_evidence({"selected_id": identity})["selected_id"]
        for identity in ("hc_bank_card_row", "amount_input")
    ]
    assert outputs == ["hc_bank_card_row", "amount_input"]


def test_identity_container_recurses_into_text_fields() -> None:
    serialized = redact_evidence(
        {
            "selected_id": {
                "id": "card_123456_container",
                "key": "account_selector",
                "text": f"account: {SECRET}",
                "nested": {"value": "amount: 1000.00"},
            }
        }
    )
    assert serialized["selected_id"]["id"] == "card_123456_container"
    assert serialized["selected_id"]["key"] == "account_selector"
    assert serialized["selected_id"]["text"] == "[REDACTED]"
    assert serialized["selected_id"]["nested"]["value"] == "[REDACTED]"


def test_text_and_value_fields_remain_redacted() -> None:
    sensitive = {
        "account": f"account: {SECRET}",
        "amount": "amount: 1000.00",
        "phone": "phone: 13800138000",
        "text": f"card: {SECRET}",
        "value": "amount: 1000.00",
        "instruction": f"向账号 {SECRET} 转账 1000 元",
        "expected": f"account: {SECRET} amount: 1000.00",
        "actual": "phone: 13800138000",
        "by_text": f"账户 {SECRET}",
        "error": f"account: {SECRET}",
        "notes": "phone: 13800138000",
    }
    encoded = _json(redact_evidence(sensitive))
    for raw in sensitive.values():
        assert raw not in encoded


# ------------------------------------------------------ v1 selector redaction
def test_structured_request_value_is_verbatim_and_text_is_not() -> None:
    """``request.value`` is an identity for by_id/by_key/by_type, text otherwise."""

    for kind in ("by_id", "by_key", "by_type"):
        out = redact_selector(
            {
                "request": {
                    "kind": kind,
                    "value": "hc_bank_card_row",
                    "match": None,
                    "constraints": {},
                },
                "resolution": {
                    "state": "not_found",
                    "candidate_count": 0,
                    "selected": None,
                    "candidates": [],
                },
            }
        )
        assert out["request"]["value"] == "hc_bank_card_row", kind

    out = redact_selector(
        {
            "request": {
                "kind": "by_text",
                "value": f"账户 {SECRET}",
                "match": "contains",
                "constraints": {},
            },
            "resolution": {
                "state": "not_found",
                "candidate_count": 0,
                "selected": None,
                "candidates": [],
            },
        }
    )
    assert SECRET not in _json(out)


def test_composite_request_keeps_the_identity_of_its_primary() -> None:
    """A composite built around by_id is still a structured target."""

    out = redact_selector(
        {
            "request": {
                "kind": "composite",
                "value": "hc_bank_card_row",
                "match": None,
                "constraints": {"within": {"by_type": "List"}, "primary": "by_id"},
            },
            "resolution": {
                "state": "not_found",
                "candidate_count": 0,
                "selected": None,
                "candidates": [],
            },
        }
    )
    assert out["request"]["value"] == "hc_bank_card_row"


def test_resolution_identity_and_bounds_are_machine_evidence() -> None:
    out = redact_selector(
        {
            "request": {
                "kind": "by_text",
                "value": f"账户 {SECRET}",
                "match": None,
                "constraints": {},
            },
            "resolution": {
                "state": "ambiguous",
                "candidate_count": 2,
                "selected": None,
                "candidates": [
                    {"id": "hc_bank_card_row", "bounds": "[0,0][200,40]"},
                    {"id": "amount_input", "bounds": "[0,100][200,140]"},
                ],
            },
        }
    )
    assert [c["id"] for c in out["resolution"]["candidates"]] == [
        "hc_bank_card_row",
        "amount_input",
    ]
    assert out["resolution"]["candidates"][0]["bounds"] == "[0,0][200,40]"
    assert SECRET not in _json(out)


def test_unresolvable_fragment_anchor_is_text_but_bounds_are_not() -> None:
    out = redact_selector(
        {
            "request": {"kind": "composite", "value": None, "match": None, "constraints": {}},
            "resolution": {
                "state": "unresolvable",
                "candidate_count": None,
                "selected": None,
                "candidates": [],
                "reason_code": "selector.inline_fragment_unresolvable",
                "facts": {
                    "dump_status": "available",
                    "request_complete": True,
                    "resolver_entered": True,
                    "candidate_countable": False,
                    "fragment_anchor": f"账户 {SECRET}",
                    "fragment_bounds": "[120,640][960,712]",
                },
            },
        }
    )
    facts = out["resolution"]["facts"]
    assert facts["fragment_bounds"] == "[120,640][960,712]"
    assert SECRET not in _json(out)


# --------------------------------------------------------- v1 StepResult rows
def test_passed_step_keeps_selected_id_and_redacts_text() -> None:
    step = build_step_result(
        OperationPassed(
            observation=ActionObservation(
                "touch", True, {"expected": f"account: {SECRET}", "actual": "amount: 1000.00"}
            ),
            selector=SelectorEvidence(
                SelectorRequest("by_id", "hc_bank_card_row"),
                SelectorResolution.unique("hc_bank_card_row", "[0,0][100,100]"),
            ),
            diagnostic=f"account: {SECRET} amount: 1000.00",
        ),
        index=0,
        kind="touch",
        role="action",
        device_session=True,
    )
    serialized = step.to_dict()
    resolution = serialized["selector"]["resolution"]
    assert resolution["selected"]["id"] == "hc_bank_card_row"
    assert resolution["selected"]["bounds"] == "[0,0][100,100]"
    assert serialized["outcome"]["observation"]["facts"]["expected"] == "[REDACTED]"
    assert SECRET not in _json(serialized)
    assert "1000.00" not in _json(serialized)
    assert not validate_against("/$defs/stepResultV1", serialized)


def test_failed_selector_step_keeps_identity_and_v1_code() -> None:
    step = build_step_result(
        OperationFailed(
            failure=Failure("selector", "selector.not_found"),
            observation=ActionObservation("touch", False),
            selector=SelectorEvidence(
                SelectorRequest("by_id", "account_selector"),
                SelectorResolution.not_found(),
            ),
            diagnostic=f"account: {SECRET} amount: 1000.00",
        ),
        index=0,
        kind="touch",
        role="action",
        device_session=False,
    )
    serialized = step.to_dict()
    assert serialized["outcome"]["failure"] == {
        "domain": "selector",
        "code": "selector.not_found",
    }
    assert serialized["selector"]["request"]["value"] == "account_selector"
    assert SECRET not in _json(serialized)


def test_vlm_expected_mismatch_reason_is_redacted() -> None:
    reason = f"account: {SECRET} amount: 1000.00 phone: 13800138000"
    outcome = HylyreAgent.interpret_assert_payload({"ok": False, "reason": reason})

    step = build_step_result(
        outcome, index=0, kind="expected_check", role="assertion"
    )
    serialized = step.to_dict()
    assert serialized["outcome"]["status"] == "failed"
    assert serialized["outcome"]["failure"]["code"] == "assertion.mismatch"
    assert serialized["outcome"]["observation"] == expected_checked(False).to_dict()
    for secret in (SECRET, "1000.00", "13800138000"):
        assert secret not in _json(serialized)


# ------------------------------------------------------------- end-to-end runs
@pytest.mark.asyncio
async def test_ambiguous_plan_trace_preserves_candidate_identity(tmp_path: Path) -> None:
    repeated_text = f"账户 {SECRET}"
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "hc_bank_card_row",
                "text": repeated_text,
                "bounds": "[0,0][200,40]",
                "clickable": "true",
            }
        ),
        _node(
            {
                "type": "Button",
                "id": "amount_input",
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
    serialized = result.case_results[0].steps[0].to_dict()
    assert serialized["outcome"]["failure"]["code"] == "selector.ambiguous"
    resolution = serialized["selector"]["resolution"]
    assert resolution["state"] == "ambiguous"
    assert [(c["id"], c["bounds"]) for c in resolution["candidates"]] == [
        ("hc_bank_card_row", "[0,0][200,40]"),
        ("amount_input", "[0,100][200,140]"),
    ]

    report = tmp_path / "ambiguous-report.md"
    trace = tmp_path / "ambiguous-trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)
    assert SECRET not in trace.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_plan_run_trace_keeps_success_selected_id(tmp_path: Path) -> None:
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
    plan = tmp_path / "success.md"
    _write_plan(
        plan,
        json.dumps(
            {"wait_for": {"by_id": "hc_bank_card_row", "timeout": 1}}, ensure_ascii=False
        ),
        case_id="TC-SUCCESS",
    )
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        plan,
        feature="selector-identity-success",
        check_expected=False,
    )
    report = tmp_path / "success-report.md"
    trace = tmp_path / "success-trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)

    trace_data = json.loads(trace.read_text(encoding="utf-8"))
    assert trace_data["schema_version"] == TRACE_SCHEMA_V1
    assert trace_data["result_protocol"] == RESULT_PROTOCOL
    step = trace_data["cases"][0]["steps"][0]
    assert step["selector"]["request"]["value"] == "hc_bank_card_row"
    assert trace_data["tool_calls"] == list(result.tool_calls)


@pytest.mark.asyncio
async def test_steps_file_batch_keeps_raw_identity_and_step_result() -> None:
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
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        [{"wait_for": {"by_id": "hc_bank_card_row", "timeout": 1}}],
    )
    row = batch["results"][0]
    assert row["step"]["wait_for"]["by_id"] == "hc_bank_card_row"
    assert row["step_result"]["selector"]["request"]["value"] == "hc_bank_card_row"
    assert not validate_against("/$defs/stepResultV1", row["step_result"])


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

    async def fake_with_hypium(*, device_sn=None, mock_port=None, lyrebird_url=None, fn=None):
        _ = (device_sn, mock_port, lyrebird_url)
        assert fn is not None
        return await fn(HylyreAgent(ui=FakeUiDriver(dump_tree=tree)))

    monkeypatch.setattr(steps_cmd, "_with_hypium_agent", fake_with_hypium)
    steps_path = tmp_path / "steps.json"
    steps_path.write_text(
        json.dumps([{"wait_for": {"by_id": "hc_bank_card_row", "timeout": 1}}]),
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
    assert result.exit_code == 0, result.stdout

    trace_data = json.loads(trace.read_text(encoding="utf-8"))
    assert trace_data["schema_version"] == TRACE_SCHEMA_V1
    assert trace_data["result_protocol"] == RESULT_PROTOCOL
    step = trace_data["cases"][0]["steps"][0]
    assert step["selector"]["request"]["value"] == "hc_bank_card_row"
    # tool_calls keeps the nested outcome shape; no flat failure_kind alias.
    assert trace_data["tool_calls"] == [
        {
            "case": "STEPS-BATCH",
            "index": 0,
            "kind": "wait_for",
            "role": "assertion",
            "outcome": {"status": "passed"},
        }
    ]
