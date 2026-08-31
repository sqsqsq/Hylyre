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
from hylyre.api.outcome_from_error import typed_exception_outcome
from hylyre.contracts import RESULT_PROTOCOL
from hylyre.scenario.step_builder import blocked_by_prior_step, build_step_result
from hylyre.scenario.plan_parse import ParsedPlan, TestCase as PlanCase
from hylyre.api.outcome import (
    ActionObservation,
    Failure,
    OperationFailed,
    OperationPassed,
    OperationSkipped,
    Reason,
    SelectorEvidence,
    SelectorRequest,
    SelectorResolution,
    absence_observed,
    presence_observed,
)
from hylyre.scenario.reducer import make_case_result, reduce_case_axes, run_outcome
from hylyre.scenario.results import CaseResult, StepResult, redact_evidence, redact_text
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
    """The three axes are reduced from steps; no entry may assert a pass."""

    passing = build_step_result(
        OperationPassed(observation=absence_observed(False)),
        index=0,
        kind="wait_gone",
        role="assertion",
    )
    skipped = build_step_result(
        OperationSkipped(
            reason=Reason("policy", "expected_check.disabled_by_flag")
        ),
        index=1,
        kind="expected_check",
        role="assertion",
    )
    blocked = blocked_by_prior_step(
        index=1, kind="wait_for", role="assertion", root_index=0
    )

    axes = reduce_case_axes((passing,), expected_check_mode="empty")
    assert axes == {
        "execution": "completed",
        "verification": "passed",
        "evidence": "complete",
        "status": "通过",
    }

    # A skipped required assertion can never be a pass.
    axes = reduce_case_axes((passing, skipped), expected_check_mode="checked_vlm")
    assert axes["verification"] == "inconclusive"
    assert axes["status"] == "跳过"

    # A blocked step is not a pass either, and carries no failure of its own.
    axes = reduce_case_axes((passing, blocked), expected_check_mode="empty")
    assert axes["verification"] == "failed"
    assert axes["status"] == "阻塞"
    assert blocked.failure is None


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
    assert tap_result.selector.resolution.candidate_count == 1
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
    # The trigger action is unaffected by a missing Toast capability; only the
    # Toast assertion itself carries the consequence.
    assert result["results"][0]["status"] == "ok"
    toast_row = result["results"][1]["step_result"]
    assert toast_row["outcome"]["status"] == "skipped"
    assert toast_row["outcome"]["reason"]["code"] == "optional_check.on_unsupported_skip"
    assert toast_row["outcome"]["reason"]["facts"]["probe_status"] == "unsupported"
    assert "failure" not in toast_row["outcome"]
    assert any(event[0] == "touch" for event in ui.events)
    assert not any(event[0] == "assert_toast" for event in ui.events)

    # A capability gap raised from *inside* a dispatched operation was
    # attempted, so it is a failure, not a pre-dispatch block. Only a probe
    # that runs before dispatch produces a blocked cause.
    dispatched = typed_exception_outcome(CapabilityUnsupported("no Toast"))
    attempted = build_step_result(
        dispatched, index=0, kind="assert_toast", role="assertion"
    )
    assert attempted.status == "failed"
    assert attempted.failure["domain"] == "capability"
    assert attempted.failure["facts"]["dispatched"] is True
    await agent.aclose()


@pytest.mark.asyncio
async def test_atomic_toast_makes_missing_trigger_window_explicit() -> None:
    agent = HylyreAgent(ui=FakeUiDriver())
    result = await agent.run_planned_assert_toast(
        {"assert_toast": {"text": "已保存"}}
    )
    assert result.observation.facts["trigger_window"] == "assertion_only"
    assert result.observation.facts["trigger_window_covered"] is False
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
    # The trigger action itself succeeded and is reported as such.
    assert result["results"][0]["step_result"]["outcome"]["status"] == "passed"

    # The listener belongs to the Toast assertion, so the transport error lands
    # there — and `on_unsupported=skip` does NOT swallow it, because a broken
    # listener is not the same fact as a missing capability.
    toast = result["results"][1]["step_result"]
    assert toast["outcome"]["status"] == "failed"
    assert toast["outcome"]["failure"]["code"] == "internal.unexpected_exception"
    assert "listener transport broke" in toast["diagnostic"]


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
    payload = json.loads(response.stdout)
    # Every entry declares the same protocol as the trace, so a consumer
    # dispatches on one field everywhere instead of guessing per entry.
    assert payload["result_protocol"] == RESULT_PROTOCOL
    step = payload["step_result"]
    assert step["outcome"]["status"] == "skipped"
    assert step["outcome"]["reason"]["code"] == "optional_check.on_unsupported_skip"


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
    step = build_step_result(
        OperationFailed(
            failure=Failure("selector", "selector.not_found"),
            observation=ActionObservation("touch", False, {"by_text": "金额 100 元"}),
            selector=SelectorEvidence(
                SelectorRequest("by_text", "账号 123456", "contains"),
                SelectorResolution.not_found(),
            ),
            diagnostic="selector={'by_text': '账号 123456'} amount: ￥100",
        ),
        index=0,
        kind="touch",
        role="action",
    )
    case = make_case_result(
        PlanCase("TC-RED", "redact", "", "", "", "P0", "AC-RED"),
        (step,),
        notes="selector={'by_text': '账号 123456'} amount: ￥100",
    )
    serialized = json.dumps(
        {"step": step.to_dict(), "case": case.to_dict()}, ensure_ascii=False
    )
    assert "123456" not in serialized
    assert "￥100" not in serialized
    assert redact_evidence({"by_text": "secret"})["by_text"] == "[REDACTED]"
    assert "123456" not in (redact_text("账号: 123456") or "")


def test_runtime_outcome_matches_blocked_projection() -> None:
    case_ok = PlanCase("OK", "ok", "", "", "", "P0", "AC-OK")
    case_blocked = PlanCase("BLOCK", "blocked", "", "", "", "P0", "AC-BLOCK")
    passing_step = build_step_result(
        OperationPassed(observation=presence_observed(True)),
        index=0,
        kind="wait_for",
        role="assertion",
    )
    root = build_step_result(
        OperationFailed(
            failure=Failure("assertion", "assertion.mismatch"),
            observation=presence_observed(False),
        ),
        index=0,
        kind="wait_for",
        role="assertion",
    )
    blocked_step = blocked_by_prior_step(
        index=1, kind="wait", role="action", root_index=0
    )
    result = ScenarioRunResult(
        feature="mixed",
        plan=ParsedPlan(Path("mixed.md"), (case_ok, case_blocked)),
        case_results=(
            make_case_result(case_ok, (passing_step,)),
            make_case_result(case_blocked, (root, blocked_step)),
        ),
        use_fakes=False,
    )
    assert resolved_outcome(result) == "failed"
    assert run_outcome(result.case_results) == "failed"


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
    assert step["outcome"]["observation"]["facts"]["observed_present"] is True


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
        wait_step = wait_payload["results"][0]["step_result"]
        assert wait_step["outcome"]["observation"]["facts"]["observed_present"] is True

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
        assert (
            toast_payload["results"][1]["step_result"]["outcome"]["status"] == "skipped"
        )
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
        assert atomic_payload["step_result"]["outcome"]["status"] == "skipped"
        await client.call_tool(
            "hylyre_close_session", {"session_id": session_id}
        )

    assert "legacy" in trace_verification_label({"schema_version": "0.2-p4"})
