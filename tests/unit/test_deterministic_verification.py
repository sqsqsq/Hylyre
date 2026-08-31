"""P0/P1 regressions for deterministic selectors, verdicts, and evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from hylyre.api.agent import HylyreAgent
from hylyre.api.exceptions import (
    AssertionMismatch,
    SelectorResolutionError,
    StepSkipped,
)
from hylyre.api.selector_resolve import resolve_targets
from hylyre.drivers.hypium import HypiumDriver
from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.runner import ScenarioRunner, resolved_outcome
from hylyre.scenario.results import redact_evidence
from hylyre.cli.__main__ import app
from hylyre.cli.commands import steps_cmd
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


def _node(attrs: dict[str, Any], *children: dict[str, Any]) -> dict[str, Any]:
    return {"attributes": attrs, "children": list(children)}


def _root(*children: dict[str, Any]) -> dict[str, Any]:
    return _node({"type": "Root", "bounds": "[0,0][500,800]"}, *children)


def _fake_shim(raw: MagicMock) -> MagicMock:
    from hypium.model import MatchPattern

    ui_driver = MagicMock()
    ui_driver.connect.return_value = raw
    by = MagicMock()
    by.text.side_effect = lambda txt, mp=None: ("text", txt, mp)
    by.id.side_effect = lambda value, mp=None: ("id", value, mp)
    by.type.side_effect = lambda value, mp=None: ("type", value, mp)
    by.key.side_effect = lambda value, mp=None: ("key", value, mp)
    shim = MagicMock()
    shim.UiDriver = ui_driver
    shim.BY = by
    shim.hypium_mod = MagicMock()
    shim.hypium_mod.MatchPattern = MatchPattern
    shim.hypium_mod.__version__ = "6.0.7.210"
    return shim


def test_exact_contains_and_invalid_match_are_shared() -> None:
    tree = _root(
        _node(
            {
                "type": "Button",
                "text": "银行信用卡关联还款协议",
                "bounds": "[0,0][200,40]",
                "clickable": "true",
            }
        )
    )
    assert resolve_targets(tree, {"by_text": "银行信用卡"})
    assert resolve_targets(
        tree, {"by_text": "银行信用卡关联还款协议", "match": "exact"}
    )
    assert resolve_targets(tree, {"by_text": "银行信用卡", "match": "exact"}) == []
    with pytest.raises(SelectorResolutionError) as exc:
        resolve_targets(tree, {"by_text": "银行", "match": "starts_with"})
    assert getattr(exc.value, "failure_code") == "selector_not_found"
    assert exc.value.selector["requested_match"] == "starts_with"
    assert exc.value.selector["effective_match"] is None


@pytest.mark.asyncio
async def test_action_ambiguity_is_fail_closed_and_index_disambiguates() -> None:
    tree = _root(
        _node(
            {"type": "Button", "id": "a", "text": "下一步", "bounds": "[0,0][100,40]", "clickable": "true"}
        ),
        _node(
            {"type": "Button", "id": "b", "text": "下一步", "bounds": "[0,100][100,140]", "clickable": "true"}
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    with pytest.raises(SelectorResolutionError) as exc:
        await agent.run_planned_tap({"touch": {"by_text": "下一步"}})
    assert exc.value.failure_code == "selector_ambiguous"
    assert {row["id"] for row in exc.value.candidates_summary} == {"a", "b"}
    await agent.run_planned_tap(
        {"touch": {"by_text": "下一步", "index": 1}}
    )
    touch = [event for event in ui.events if event[0] == "touch"][-1][1]
    assert (touch["x"], touch["y"]) == (50, 120)


@pytest.mark.asyncio
async def test_selector_failure_keeps_typed_result_and_failed_outcome(tmp_path: Path) -> None:
    plan = tmp_path / "missing.md"
    _write_plan(plan, '{"touch":{"by_id":"missing"}}')
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=_root())),
        plan,
        feature="missing",
        check_expected=False,
    )
    case = result.case_results[0]
    assert case.steps[0].failure == {
        "domain": "selector",
        "code": "selector.not_found",
        "facts": {"resolver_code": "selector_not_found"},
    }
    assert resolved_outcome(result) == "failed"
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)


@pytest.mark.asyncio
async def test_aggregate_rich_text_is_not_clicked() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "rich_text_aggregate_dump.json"
    tree = json.loads(fixture.read_text(encoding="utf-8"))["tree"]
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    with pytest.raises(SelectorResolutionError) as exc:
        await agent.run_planned_tap(
            {"touch": {"by_text": "银行信用卡关联还款协议"}}
        )
    assert exc.value.failure_code == "inline_target_unresolvable"
    assert not [event for event in ui.events if event[0] == "touch"]


@pytest.mark.asyncio
async def test_real_fragment_bounds_are_used_for_rich_text() -> None:
    text = "已阅读并同意银行信用卡关联还款协议"
    tree = _root(
        _node(
            {
                "type": "Text",
                "text": text,
                "bounds": "[0,0][500,50]",
                "spans": [
                    {
                        "text": "银行信用卡关联还款协议",
                        "bounds": "[200,10][450,40]",
                        "clickable": True,
                    }
                ],
            }
        )
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    result = await agent.run_planned_tap(
        {"touch": {"by_text": "银行信用卡关联还款协议"}}
    )
    touch = [event for event in ui.events if event[0] == "touch"][-1][1]
    assert (touch["x"], touch["y"]) == (325, 25)
    assert result.observation.facts["resolution_kind"] == "span_bounds"


@pytest.mark.asyncio
async def test_native_wait_return_contracts() -> None:
    raw = MagicMock()
    shim = _fake_shim(raw)
    with patch("hylyre.drivers.hypium.driver.load_hypium_shim", return_value=shim):
        driver = HypiumDriver()
        await driver.connect()
        # A timeout is an observation, not an exception. Raising a selector
        # error here is what put `failure.domain=selector` on an assertion row
        # on real hardware — the contradiction the protocol exists to remove.
        raw.wait_for_component.return_value = None
        absent = await driver.wait_for_selector(by_id="missing", timeout=2)
        assert absent["evidence"]["observed_present"] is False

        raw.wait_for_component_disappear.return_value = object()
        remains = await driver.wait_for_selector_gone(by_id="present", timeout=2)
        assert remains["evidence"]["observed_present"] is True

        # End to end, the agent classifies both as assertion mismatches that
        # carry their own observation.
        agent = HylyreAgent(ui=driver)
        raw.wait_for_component.return_value = None
        outcome = await agent.run_planned_wait_for(
            {"wait_for": {"by_id": "missing", "timeout": 2}}
        )
        result = outcome.outcome_dict()
        assert result["failure"] == {
            "domain": "assertion",
            "code": "assertion.mismatch",
            "facts": {"assertion": "presence"},
        }
        assert result["observation"]["facts"]["observed_present"] is False
        assert outcome.selector.resolution.state == "not_found"

        outcome = await agent.run_planned_wait_gone(
            {"wait_gone": {"by_id": "present", "timeout": 2}}
        )
        result = outcome.outcome_dict()
        assert result["failure"]["domain"] == "assertion"
        assert result["observation"]["facts"]["observed_present"] is True


@pytest.mark.asyncio
async def test_native_match_pattern_is_forwarded() -> None:
    from hypium.model import MatchPattern

    raw = MagicMock()
    shim = _fake_shim(raw)
    with patch("hylyre.drivers.hypium.driver.load_hypium_shim", return_value=shim):
        driver = HypiumDriver()
        await driver.connect()
        await driver.touch(by_text="协议", match="contains")
        assert shim.BY.text.call_args.args == ("协议", MatchPattern.CONTAINS)
        with pytest.raises(SelectorResolutionError):
            await driver.touch(by_text="协议", match="typo")
        with pytest.raises(SelectorResolutionError):
            await driver.touch(by_text="协议", match="starts_with")
        raw.wait_for_component.return_value = object()
        await driver.wait_for_selector(by_text="协议")
        assert shim.BY.text.call_args.args == ("协议", MatchPattern.CONTAINS)
        raw.find_all_components.return_value = [object(), object()]
        with pytest.raises(SelectorResolutionError) as ambiguous:
            await driver.touch(by_id="duplicate")
        assert ambiguous.value.failure_code == "selector_ambiguous"
        assert len(ambiguous.value.candidates_summary) == 2


@pytest.mark.asyncio
async def test_toast_false_true_and_unsupported_are_distinct() -> None:
    raw = MagicMock()
    shim = _fake_shim(raw)
    with patch("hylyre.drivers.hypium.driver.load_hypium_shim", return_value=shim):
        driver = HypiumDriver()
        await driver.connect()
        raw.check_toast.side_effect = [False, True]
        evidence = await driver.assert_toast("已保存", timeout=1, poll_interval=0.01)
        assert evidence["result"] is True
        assert raw.start_listen_toast.call_count >= 2
        raw.check_toast.reset_mock()
        raw.check_toast.side_effect = None
        raw.check_toast.return_value = False
        with pytest.raises(AssertionMismatch):
            await driver.assert_toast("不会出现", timeout=0.01)
        raw.check_toast.side_effect = RuntimeError("toast unsupported")
        with pytest.raises(StepSkipped):
            await driver.assert_toast(
                "系统不支持", timeout=1, on_unsupported="skip"
            )


def _write_plan(path: Path, steps: str, expected: str = "-") -> None:
    path.write_text(
        "# fixture\n\n## 测试用例清单\n\n"
        "| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        f"| T | fixture | | {steps} | {expected} | P0 | AC-T |\n",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_runner_verdict_axes_and_expected_modes(tmp_path: Path) -> None:
    action_plan = tmp_path / "action.md"
    _write_plan(action_plan, '{"touch":{"x":1,"y":2}}')
    action_result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver()),
        action_plan,
        feature="action",
        check_expected=False,
    )
    case = action_result.case_results[0]
    assert case.execution == "completed"
    assert case.verification == "inconclusive"
    assert case.status == "跳过"

    expected_plan = tmp_path / "expected.md"
    _write_plan(expected_plan, '{"touch":{"x":1,"y":2}}', "页面已打开")
    disabled = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver()),
        expected_plan,
        feature="disabled",
        check_expected=False,
    )
    assert disabled.case_results[0].expected_check_mode == "disabled_by_flag"
    unavailable = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver()),
        expected_plan,
        feature="unavailable",
        check_expected=True,
    )
    assert unavailable.case_results[0].expected_check_mode == "unavailable_no_vlm"


@pytest.mark.asyncio
async def test_touch_input_wait_share_contains_semantics() -> None:
    tree = _root(
        _node(
            {
                "type": "TextInput",
                "text": "验证码 1234",
                "id": "code",
                "bounds": "[0,0][200,50]",
                "clickable": "true",
            }
        )
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_tap({"touch": {"by_text": "验证码"}})
    await agent.run_planned_input(
        {"input": {"by_text": "验证码", "text": "9999"}}
    )
    await agent.run_planned_wait_for(
        {"wait_for": {"by_text": "验证码", "timeout": 1}}
    )
    assert len([event for event in ui.events if event[0] == "touch"]) == 2
    assert any(event[0] == "input_text" for event in ui.events)


def test_evidence_redaction_and_trace_report_case_set_validation(tmp_path: Path) -> None:
    plan = Path(__file__).parents[1] / "e2e" / "fixtures" / "mock-test-plan.md"
    result = ScenarioRunner(use_fakes=True).run_plan_file(plan, feature="redact")
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    data = json.loads(trace.read_text(encoding="utf-8"))
    data["cases"][0]["steps"][0]["outcome"]["observation"]["facts"]["text"] = (
        "secret account"
    )
    trace.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    # A tampered trace is caught by the Markdown projection check, while the
    # serialized evidence path itself remains the redaction boundary.
    with pytest.raises(ValueError, match="outcome mismatch"):
        verify_report(report, trace, plan)

    write_run_artifacts(result, report_path=report, trace_path=trace)
    data = json.loads(trace.read_text(encoding="utf-8"))
    data["cases"].pop()
    trace.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    # Dropping a case is now caught by the cross-row oracle (the tool_calls
    # projection no longer matches) before the case-id set comparison runs;
    # either way the tampered trace is rejected, not silently accepted.
    with pytest.raises(ValueError, match="cross-row|case id set mismatch"):
        verify_report(report, trace, plan)
    assert redact_evidence({"text": "card 123", "amount": "100"}) == {
        "text": "[REDACTED]",
        "amount": "[REDACTED]",
    }


@pytest.mark.asyncio
async def test_all_skipped_and_assertion_evidence(tmp_path: Path) -> None:
    skipped_plan = tmp_path / "skip.md"
    _write_plan(skipped_plan, '{"assert_toast":{"text":"x","on_unsupported":"skip"}}')
    ui = FakeUiDriver(toast_unsupported=True)
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=ui), skipped_plan, feature="skip", check_expected=False
    )
    step = result.case_results[0].steps[0]
    # on_unsupported=skip is an explicit plan policy, so it is a reason, not a
    # fabricated capability *failure* as 0.3-p0 recorded it.
    assert step.status == "skipped"
    assert step.reason["type"] == "policy"
    assert step.reason["code"] == "optional_check.on_unsupported_skip"
    assert step.reason["facts"]["probe_status"] == "unsupported"
    assert step.failure is None
    assert resolved_outcome(result) != "success"

    assertion_plan = tmp_path / "assert.md"
    _write_plan(assertion_plan, '{"wait_gone":{"by_id":"missing","timeout":0.1}}')
    assertion_result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=_root())),
        assertion_plan,
        feature="assert",
        check_expected=False,
    )
    step = assertion_result.case_results[0].steps[0]
    assert step.role == "assertion"
    assert step.status == "passed"
    # A passing assertion must carry the observation that justifies it.
    assert step.observation is not None
    assert step.observation["assertion_type"] == "absence"
    assert step.observation["matched"] is True
    assert assertion_result.case_results[0].verification == "passed"


def test_trace_tool_calls_and_report_are_ledger_projections(tmp_path: Path) -> None:
    plan = Path(__file__).parents[1] / "e2e" / "fixtures" / "mock-test-plan.md"
    result = ScenarioRunner(use_fakes=True).run_plan_file(plan, feature="trace")
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data["cases"][0]["steps"]
    assert data["tool_calls"] == list(result.tool_calls)
    data["cases"][0]["steps"].append(dict(data["cases"][0]["steps"][0]))
    trace.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate step index"):
        verify_report(report, trace, plan)


@pytest.mark.asyncio
async def test_steps_file_public_entry_emits_step_result() -> None:
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "ready",
                "text": "ready",
                "bounds": "[0,0][100,40]",
                "clickable": "true",
            }
        )
    )
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))
    batch = await steps_cmd.run_steps_on_agent(
        agent, [{"wait_for": {"by_id": "ready", "timeout": 1}}]
    )
    row = batch["results"][0]
    assert row["status"] == "ok"
    assert row["step_result"]["role"] == "assertion"
    observation = row["step_result"]["outcome"]["observation"]
    assert observation["kind"] == "assertion"
    assert observation["facts"]["observed_present"] is True


def test_cli_plan_public_entry_writes_new_trace(tmp_path: Path) -> None:
    plan = Path(__file__).parents[1] / "e2e" / "fixtures" / "mock-test-plan.md"
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--plan",
            str(plan),
            "--feature",
            "cli-conformance",
            "--report-out",
            str(report),
            "--trace-out",
            str(trace),
            "--use-fakes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.4-p0"
    assert data["result_protocol"] == "hylyre.step-outcome/1"
    assert data["cases"][0]["steps"]


def test_fake_cli_skip_flag_is_recorded(tmp_path: Path) -> None:
    plan = Path(__file__).parents[1] / "e2e" / "fixtures" / "mock-test-plan.md"
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    CliRunner().invoke(
        app,
        [
            "run",
            "--plan",
            str(plan),
            "--feature",
            "cli-mode",
            "--report-out",
            str(report),
            "--trace-out",
            str(trace),
            "--use-fakes",
            "--skip-assert-expected",
        ],
    )
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data["cases"][0]["expected_check_mode"] == "disabled_by_flag"


def test_fake_plan_does_not_claim_stub_assertion_as_verified(tmp_path: Path) -> None:
    plan = tmp_path / "assertion.md"
    _write_plan(plan, '{"wait_for":{"by_id":"ready"}}')
    result = ScenarioRunner(use_fakes=True).run_plan_file(plan, feature="fake")
    step = result.case_results[0].steps[0]
    # The offline stub cannot observe a device, so it says so rather than
    # emitting a green assertion row with no evidence behind it.
    assert step.status == "blocked"
    assert step.cause["type"] == "capability"
    assert step.cause["capability_id"] == "fake.ui_observation"
    assert result.case_results[0].verification == "failed"
