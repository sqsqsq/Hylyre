"""Regression tests for the review-blocking deterministic-verification cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hylyre.api.agent import HylyreAgent
from hylyre.api.exceptions import CapabilityUnsupported, SelectorResolutionError
from hylyre.api.selector_resolve import resolve_action_one, resolve_targets
from hylyre.cli.__main__ import app
from hylyre.cli.commands import steps_cmd
from hylyre.harness.runner import trace_verification_label, verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.ledger import blocked_step_result
from hylyre.scenario.plan_parse import ParsedPlan, TestCase as PlanCase
from hylyre.scenario.results import (
    CaseResult,
    StepResult,
    case_verdict,
    outcome_from_case_results,
    redact_evidence,
    redact_text,
    result_from_exception,
)
from hylyre.scenario.runner import ScenarioRunResult, ScenarioRunner, resolved_outcome
from tests.contract.fakes.fake_ui_driver import FakeUiDriver
from tests.contract.fakes.fake_vlm_client import FakeVlmClient


def _node(attrs: dict, *children: dict) -> dict:
    return {"attributes": attrs, "children": list(children)}


def _root(*children: dict) -> dict:
    return _node({"type": "Root", "bounds": "[0,0][500,800]"}, *children)


def _write_plan(path: Path, steps: str, expected: str = "-") -> None:
    path.write_text(
        "# fixture\n\n## 测试用例清单\n\n"
        "| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        f"| TC-REVIEW | review | | {steps} | {expected} | P0 | AC-REVIEW |\n",
        encoding="utf-8",
    )


def test_verdict_rejects_aborted_skipped_and_empty_evidence() -> None:
    passing = StepResult(
        index=0,
        kind="wait_gone",
        role="assertion",
        status="passed",
        evidence={"assertion": "absence", "observed_present": False},
    )
    skipped = StepResult(
        index=1,
        kind="assert_toast",
        role="assertion",
        status="skipped",
        failure_kind="capability",
        failure_code="capability_unsupported",
        evidence={"result": "skipped"},
    )
    assert case_verdict(
        (passing, skipped), expected_check_mode="empty", execution="completed"
    )[:2] == ("inconclusive", "complete")

    failed_action = StepResult(
        index=1,
        kind="touch",
        role="action",
        status="failed",
        failure_kind="selector",
        failure_code="selector_not_found",
        evidence={"candidate_count": 0},
    )
    assert case_verdict(
        (passing, failed_action), expected_check_mode="empty", execution="aborted"
    )[0] != "passed"

    empty_evidence = StepResult(
        index=0,
        kind="wait_for",
        role="assertion",
        status="passed",
        evidence={},
    )
    assert case_verdict(
        (empty_evidence,), expected_check_mode="empty", execution="completed"
    )[:2] == ("inconclusive", "incomplete")


@pytest.mark.asyncio
async def test_runner_records_blocked_suffix_and_expected_mode_after_abort(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "abort.md"
    _write_plan(
        plan,
        '{"wait_gone":{"by_id":"gone","timeout":0.01}};'
        '{"touch":{"by_id":"missing"}};'
        '{"wait_for":{"by_id":"later","timeout":0.01}}',
        expected="页面完成",
    )
    agent = HylyreAgent(
        ui=FakeUiDriver(dump_tree=_root()), vlm=FakeVlmClient(responses=[])
    )
    result = await ScenarioRunner().run_plan_on_agent(
        agent, plan, feature="review", check_expected=True
    )
    case = result.case_results[0]
    assert case.execution == "aborted"
    assert case.verification == "failed"
    assert case.expected_check_mode == "checked_vlm"
    assert [step.index for step in case.steps] == [0, 1, 2, 3]
    assert case.steps[0].status == "passed"
    assert case.steps[1].status == "failed"
    assert case.steps[2].status == "blocked"
    assert case.steps[3].kind == "expected_check"
    assert case.steps[3].status == "blocked"
    await agent.aclose()


@pytest.mark.asyncio
async def test_actual_assertion_can_verify_when_expected_vlm_is_unavailable(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "actual-assertion.md"
    _write_plan(
        plan,
        '{"wait_gone":{"by_id":"missing","timeout":0.01}}',
        expected="人类预期但无 VLM",
    )
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=_root())),
        plan,
        feature="actual-assertion",
        check_expected=True,
    )
    case = result.case_results[0]
    assert case.expected_check_mode == "unavailable_no_vlm"
    assert case.steps[-1].status == "skipped"
    assert case.verification == "passed"
    report = tmp_path / "actual-report.md"
    trace = tmp_path / "actual-trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)


@pytest.mark.asyncio
async def test_batch_abort_records_blocked_suffix() -> None:
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=_root()))
    result = await steps_cmd.run_steps_on_agent(
        agent,
        [
            {"touch": {"by_id": "missing"}},
            {"wait": {"seconds": 0}},
        ],
        on_fail="abort",
    )
    assert result["executed"] == 1
    assert result["results"][0]["status"] == "error"
    assert result["results"][0]["step_result"]["status"] == "failed"
    assert result["results"][1]["step_result"]["status"] == "blocked"
    assert result["results"][1]["step_result"]["failure_kind"] == "selector"
    assert result["results"][1]["step_result"]["failure_code"] == "selector_not_found"
    assert not any(event[0] == "wait_seconds" for event in agent.ui.events)


def test_selector_constraints_are_fail_closed() -> None:
    normal = _root(
        _node(
            {
                "type": "Button",
                "text": "账户余额 100 元",
                "bounds": "[0,0][200,50]",
                "clickable": "true",
            }
        )
    )
    normal_hit = resolve_action_one(normal, {"by_text": "账户余额"})
    assert normal_hit.type == "Button"

    with pytest.raises(SelectorResolutionError) as overlay:
        resolve_action_one(normal, {"by_text": "账户余额", "scope": "top_overlay"})
    assert overlay.value.failure_code == "selector_not_found"

    assert resolve_targets(
        normal, {"by_text": "账户余额", "below": {"by_text": "不存在"}}
    ) == []

    with pytest.raises(SelectorResolutionError) as nested:
        resolve_targets(
            normal,
            {"by_text": "不存在", "within": {"by_text": "x", "match": "starts_with"}},
        )
    assert nested.value.failure_code == "selector_not_found"

    ordinary_span = _root(
        _node(
            {
                "type": "Span",
                "text": "链接",
                "bounds": "[0,0][100,40]",
                "clickable": "false",
            }
        )
    )
    with pytest.raises(SelectorResolutionError) as span:
        resolve_action_one(ordinary_span, {"by_text": "链接", "match": "exact"})
    assert span.value.failure_code == "inline_target_unresolvable"

    span_in_row = _root(
        _node(
            {
                "type": "Row",
                "bounds": "[0,0][200,50]",
                "clickable": "true",
            },
            _node(
                {
                    "type": "Span",
                    "text": "链接",
                    "bounds": "[10,10][80,40]",
                    "clickable": "false",
                }
            ),
        )
    )
    with pytest.raises(SelectorResolutionError) as row_span:
        resolve_action_one(span_in_row, {"by_text": "链接", "match": "exact"})
    assert row_span.value.failure_code == "inline_target_unresolvable"


@pytest.mark.asyncio
async def test_all_selector_and_gesture_containers_use_unique_resolution() -> None:
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "next",
                "bounds": "[10,10][110,60]",
                "clickable": "true",
            },
            _node({"type": "Text", "text": "下一步", "bounds": "[20,20][100,50]"}),
        ),
        _node(
            {"type": "Scroll", "scrollable": "true", "bounds": "[0,100][250,700]"}
        ),
        _node(
            {"type": "Scroll", "scrollable": "true", "bounds": "[250,100][500,700]"}
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    tap_result = await agent.run_planned_tap(
        {"touch": {"all": [{"by_text": "下一步"}, {"by_type": "Button"}]}}
    )
    assert tap_result["selector"]["candidate_count"] == 1
    with pytest.raises(SelectorResolutionError) as swipe:
        await agent.run_planned_swipe(
            {"swipe": {"direction": "UP", "area": {"by_type": "Scroll"}}}
        )
    assert swipe.value.failure_code == "selector_ambiguous"
    with pytest.raises(SelectorResolutionError) as scroll:
        await agent.run_planned_scroll(
            {"scroll": {"direction": "up", "steps": 1, "at": {"by_type": "Scroll"}}}
        )
    assert scroll.value.failure_code == "selector_ambiguous"
    with pytest.raises(SelectorResolutionError) as scroll_to:
        await agent.run_planned_scroll_to(
            {
                "scroll_to": {
                    "by_text": "目标",
                    "in": {"by_type": "Scroll"},
                }
            }
        )
    assert scroll_to.value.failure_code == "selector_ambiguous"
    assert not any(event[0] == "swipe" for event in ui.events)
    assert not any(event[0] == "mouse_scroll" for event in ui.events)
    await agent.aclose()


@pytest.mark.asyncio
async def test_toast_listener_unsupported_skip_keeps_trigger_and_typed_row() -> None:
    ui = FakeUiDriver(toast_unsupported=True)
    agent = HylyreAgent(ui=ui)
    result = await steps_cmd.run_steps_on_agent(
        agent,
        [
            {"touch": {"x": 10, "y": 20}},
            {"assert_toast": {"text": "已保存", "on_unsupported": "skip"}},
        ],
    )
    assert result["results"][0]["status"] == "ok"
    assert result["results"][0]["step_result"]["evidence"]["toast_listener"]["result"] == "unsupported"
    toast_row = result["results"][1]["step_result"]
    assert toast_row["status"] == "skipped"
    assert toast_row["failure_kind"] == "capability"
    assert toast_row["failure_code"] == "capability_unsupported"
    assert any(event[0] == "touch" for event in ui.events)
    assert not any(event[0] == "assert_toast" for event in ui.events)

    blocked = result_from_exception(
        exc=CapabilityUnsupported("no Toast"),
        index=0,
        kind="assert_toast",
        role="assertion",
        duration_ms=0,
    )
    assert blocked.status == "blocked"
    await agent.aclose()


@pytest.mark.asyncio
async def test_atomic_toast_makes_missing_trigger_window_explicit() -> None:
    agent = HylyreAgent(ui=FakeUiDriver())
    result = await agent.run_planned_assert_toast(
        {"assert_toast": {"text": "已保存"}}
    )
    assert result["evidence"]["trigger_window"] == "assertion_only"
    assert result["evidence"]["trigger_window_covered"] is False
    await agent.aclose()


@pytest.mark.asyncio
async def test_toast_skip_does_not_swallow_non_capability_listener_error() -> None:
    agent = HylyreAgent(ui=FakeUiDriver())

    async def broken_listener() -> dict:
        raise RuntimeError("listener transport broke")

    agent.start_toast_listening = broken_listener  # type: ignore[method-assign]
    result = await steps_cmd.run_steps_on_agent(
        agent,
        [
            {"touch": {"x": 1, "y": 2}},
            {"assert_toast": {"text": "x", "on_unsupported": "skip"}},
        ],
    )
    assert result["results"][0]["step_result"]["status"] == "failed"
    assert result["results"][0]["step_result"]["failure_code"] == "driver_failure"
    assert result["results"][1]["step_result"]["status"] == "blocked"


def test_cli_atomic_toast_skip_returns_typed_step_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = HylyreAgent(ui=FakeUiDriver(toast_unsupported=True))

    async def fake_with_hypium(*, device_sn=None, mock_port=None, lyrebird_url=None, fn=None):
        assert fn is not None
        return await fn(agent)

    monkeypatch.setattr(
        "hylyre.cli.commands.loop_cmd._with_hypium_agent", fake_with_hypium
    )
    response = CliRunner().invoke(
        app,
        [
            "run",
            "assert-toast",
            "--json",
            json.dumps(
                {"assert_toast": {"text": "已保存", "on_unsupported": "skip"}},
                ensure_ascii=False,
            ),
        ],
    )
    assert response.exit_code == 0, response.stdout + response.stderr
    step = json.loads(response.stdout)
    assert step["status"] == "skipped"
    assert step["failure_kind"] == "capability"


@pytest.mark.asyncio
async def test_trace_requires_selector_evidence_fields(tmp_path: Path) -> None:
    plan = tmp_path / "trace.md"
    _write_plan(plan, '{"wait_gone":{"by_id":"missing","timeout":0.01}}')
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=_root())),
        plan,
        feature="schema",
        check_expected=False,
    )
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    data = json.loads(trace.read_text(encoding="utf-8"))
    data["cases"][0]["steps"][0]["selector"] = {}
    trace.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="trace.json schema"):
        verify_report(report, trace, plan)


def test_sensitive_selector_error_and_notes_are_redacted() -> None:
    step = StepResult(
        index=0,
        kind="touch",
        role="action",
        status="failed",
        failure_kind="selector",
        failure_code="selector_not_found",
        selector={
            "engine": "resolver",
            "requested_match": None,
            "effective_match": "contains",
            "candidate_count": 0,
            "predicate": {"by_text": "账号 123456"},
        },
        evidence={"by_text": "金额 100 元"},
        error="selector={'by_text': '账号 123456'} amount: ￥100",
    )
    case = CaseResult(
        case=PlanCase("TC-RED", "redact", "", "", "", "P0", "AC-RED"),
        status="失败",
        notes="selector={'by_text': '账号 123456'} amount: ￥100",
        execution="aborted",
        verification="failed",
        evidence="incomplete",
        steps=(step,),
    )
    serialized = json.dumps({"step": step.to_dict(), "case": case.to_dict()}, ensure_ascii=False)
    assert "123456" not in serialized
    assert "￥100" not in serialized
    assert redact_evidence({"by_text": "secret"})["by_text"] == "[REDACTED]"
    assert "123456" not in (redact_text("账号: 123456") or "")


def test_runtime_outcome_matches_blocked_projection() -> None:
    case_ok = PlanCase("OK", "ok", "", "", "", "P0", "AC-OK")
    case_blocked = PlanCase("BLOCK", "blocked", "", "", "", "P0", "AC-BLOCK")
    passing_step = StepResult(
        index=0,
        kind="wait_for",
        role="assertion",
        status="passed",
        evidence={"assertion": "presence"},
    )
    blocked_step = blocked_step_result({"wait": {"seconds": 1}}, index=0, reason="prior failure")
    result = ScenarioRunResult(
        feature="mixed",
        plan=ParsedPlan(Path("mixed.md"), (case_ok, case_blocked)),
        case_results=(
            CaseResult(
                case=case_ok,
                execution="completed",
                verification="passed",
                evidence="complete",
                steps=(passing_step,),
            ),
            CaseResult(
                case=case_blocked,
                execution="aborted",
                verification="failed",
                evidence="complete",
                steps=(blocked_step,),
            ),
        ),
        use_fakes=False,
    )
    assert resolved_outcome(result) == "failed"
    assert outcome_from_case_results(result.case_results) == "failed"


def test_cli_steps_file_reaches_real_planned_dispatcher(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "ready",
                "bounds": "[0,0][100,40]",
                "clickable": "true",
            }
        )
    )
    fake_agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))

    async def fake_with_hypium(*, device_sn=None, mock_port=None, lyrebird_url=None, fn=None):
        assert fn is not None
        return await fn(fake_agent)

    monkeypatch.setattr(
        "hylyre.cli.commands.steps_cmd._with_hypium_agent", fake_with_hypium
    )
    steps_file = tmp_path / "steps.json"
    steps_file.write_text(
        json.dumps([{"wait_for": {"by_id": "ready", "timeout": 1}}]),
        encoding="utf-8",
    )
    response = CliRunner().invoke(app, ["run", "--steps-file", str(steps_file)])
    assert response.exit_code == 0, response.stdout + response.stderr
    payload = json.loads(response.stdout)
    step = payload["results"][0]["step_result"]
    assert step["role"] == "assertion"
    assert step["evidence"]["observed_present"] is True


def test_cli_report_verify_labels_legacy_trace(tmp_path: Path) -> None:
    plan = tmp_path / "legacy.md"
    _write_plan(plan, '{"touch":{"x":1,"y":2}}')
    result = ScenarioRunner(use_fakes=True).run_plan_file(
        plan, feature="legacy"
    )
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    write_run_artifacts(
        result,
        report_path=report,
        trace_path=trace,
        schema_version="0.2-p4",
    )
    response = CliRunner().invoke(
        app,
        ["report", "verify", "--report", str(report), "--trace", str(trace)],
    )
    assert response.exit_code == 0, response.stdout + response.stderr
    assert "legacy" in response.stdout


@pytest.mark.asyncio
async def test_mcp_session_batch_reaches_shared_dispatcher_and_toast_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("fastmcp")
    from fastmcp import Client

    from hylyre.mcp.server import build_mcp

    tree = _root(
        _node(
            {
                "type": "Button",
                "id": "ready",
                "bounds": "[0,0][100,40]",
                "clickable": "true",
            }
        )
    )
    fake_agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))
    monkeypatch.setattr(
        "hylyre.wiring.create_hypium_agent",
        lambda **_kwargs: fake_agent,
    )
    mcp = build_mcp()
    async with Client(mcp) as client:
        opened = await client.call_tool("hylyre_open_session", {})
        session_id = json.loads(opened.content[0].text)["session_id"]
        wait_out = await client.call_tool(
            "hylyre_run_steps",
            {
                "session_id": session_id,
                "steps": [{"wait_for": {"by_id": "ready", "timeout": 1}}],
            },
        )
        wait_payload = json.loads(wait_out.content[0].text)
        assert wait_payload["results"][0]["step_result"]["evidence"]["observed_present"] is True

        fake_agent.ui.toast_unsupported = True
        toast_out = await client.call_tool(
            "hylyre_run_steps",
            {
                "session_id": session_id,
                "steps": [
                    {"touch": {"x": 1, "y": 2}},
                    {"assert_toast": {"text": "已保存", "on_unsupported": "skip"}},
                ],
            },
        )
        toast_payload = json.loads(toast_out.content[0].text)
        assert toast_payload["results"][1]["step_result"]["status"] == "skipped"
        atomic_out = await client.call_tool(
            "hylyre_run_assert_toast",
            {
                "session_id": session_id,
                "payload": {
                    "assert_toast": {
                        "text": "已保存",
                        "on_unsupported": "skip",
                    }
                },
            },
        )
        atomic_payload = json.loads(atomic_out.content[0].text)
        assert atomic_payload["step_result"]["status"] == "skipped"
        await client.call_tool(
            "hylyre_close_session", {"session_id": session_id}
        )

    assert "legacy" in trace_verification_label({"schema_version": "0.2-p4"})
