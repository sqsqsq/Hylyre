"""Final-review regressions for Toast evidence, nested selectors, and containers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.api.exceptions import SelectorResolutionError
from hylyre.cli.commands import steps_cmd
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.runner import ScenarioRunner
from hylyre.harness.runner import verify_report
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


def _node(attrs: dict, *children: dict) -> dict:
    return {"attributes": attrs, "children": list(children)}


def _root(*children: dict) -> dict:
    return _node({"type": "Root", "bounds": "[0,0][500,800]"}, *children)


def _write_plan(path: Path, steps: str) -> None:
    path.write_text(
        "# fixture\n\n## 测试用例清单\n\n"
        "| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        f"| TC-FINAL | final | | {steps} | - | P0 | AC-FINAL |\n",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_uncovered_toast_cannot_verify_or_pass_trace(tmp_path: Path) -> None:
    plan = tmp_path / "toast-only.md"
    _write_plan(plan, '{"assert_toast":{"text":"已保存"}}')
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver()),
        plan,
        feature="toast-only",
        check_expected=False,
    )
    case = result.case_results[0]
    assert case.steps[0].status == "passed"
    # An uncovered trigger window is explicit non-verifying evidence: it does
    # not flip `matched`, it downgrades the case evidence.
    assert case.steps[0].observation["facts"]["trigger_window_covered"] is False
    assert case.execution == "completed"
    assert case.verification == "inconclusive"
    assert case.evidence == "incomplete"
    assert case.status == "跳过"

    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)

    tampered = json.loads(trace.read_text(encoding="utf-8"))
    tampered_case = tampered["cases"][0]
    tampered_case["verification"] = "passed"
    tampered_case["evidence"] = "complete"
    tampered_case["status"] = "通过"
    trace.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        verify_report(report, trace, plan)


@pytest.mark.asyncio
async def test_aggregate_text_contract_signal_and_nested_all_fail_closed() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "rich_text_aggregate_dump.json"
    tree = json.loads(fixture.read_text(encoding="utf-8"))["tree"]
    assert "rich_text" not in tree["children"][0]["children"][0]["attributes"]
    assert tree["children"][0]["children"][0]["attributes"]["inline_target"] == "true"
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)

    for touch in (
        {"by_text": "银行信用卡关联还款协议"},
        {
            "all": [
                {"by_text": "银行信用卡关联还款协议"},
                {"by_type": "Row"},
            ]
        },
    ):
        with pytest.raises(SelectorResolutionError) as exc:
            await agent.run_planned_tap({"touch": touch})
        assert exc.value.failure_code == "inline_target_unresolvable"
    assert not any(event[0] == "touch" for event in ui.events)
    await agent.aclose()


@pytest.mark.asyncio
async def test_normal_dynamic_row_contains_remains_addressable() -> None:
    tree = _root(
        _node(
            {
                "type": "Row",
                "id": "balance-row",
                "bounds": "[0,0][300,60]",
                "clickable": "true",
            },
            _node(
                {
                    "type": "Text",
                    "text": "账户余额 100 元",
                    "bounds": "[20,10][280,50]",
                }
            ),
        )
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    for touch in (
        {"by_text": "账户余额", "match": "contains"},
        {
            "all": [
                {"by_text": "账户余额", "match": "contains"},
                {"by_type": "Row"},
            ]
        },
    ):
        result = await agent.run_planned_tap({"touch": touch})
        resolution = result.selector.resolution
        assert resolution.state == "unique"
        assert resolution.selected["id"] == "balance-row"
    assert [
        (event[1]["x"], event[1]["y"])
        for event in ui.events
        if event[0] == "touch"
    ] == [(150, 30), (150, 30)]
    await agent.aclose()


@pytest.mark.asyncio
async def test_nested_all_match_controls_execution_and_evidence() -> None:
    tree = _root(
        _node(
            {
                "type": "Button",
                "text": "foo",
                "bounds": "[0,0][100,40]",
                "clickable": "true",
            }
        )
    )
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))
    result = await agent.run_planned_tap(
        {
            "touch": {
                "all": [
                    {"by_text": "foo", "match": "exact"},
                    {"by_type": "Button"},
                ]
            }
        }
    )
    # The request records what the plan asked for, nesting included: here the
    # match lives inside the `all` predicate, so that is where it is reported.
    # The resolution records only what was found; the two are never conflated.
    request = result.selector.request
    assert request.constraints["all"][0]["match"] == "exact"
    assert result.selector.resolution.state == "unique"

    inherited = await agent.run_planned_tap(
        {
            "touch": {
                "match": "exact",
                "all": [{"by_text": "foo"}, {"by_type": "Button"}],
            }
        }
    )
    # A block-level match is reported at the top of the request.
    assert inherited.selector.request.match == "exact"
    assert inherited.selector.resolution.state == "unique"
    await agent.aclose()


@pytest.mark.asyncio
async def test_scroll_to_uses_scoped_container_node_not_background() -> None:
    background = _node(
        {"type": "Scroll", "scrollable": "true", "bounds": "[0,0][500,300]"},
        _node({"type": "Text", "text": "目标", "bounds": "[100,100][200,130]"}),
    )
    sheet_scroll = _node(
        {"type": "Scroll", "scrollable": "true", "bounds": "[0,300][500,800]"},
        _node({"type": "Text", "text": "目标", "bounds": "[100,600][200,630]"}),
    )
    sheet = _node(
        {"type": "Sheet", "bounds": "[0,300][500,800]"}, sheet_scroll
    )
    ui = FakeUiDriver(dump_tree=_root(background, sheet))
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_scroll_to(
        {
            "scroll_to": {
                "by_text": "目标",
                "in": {"by_type": "Scroll", "scope": "top_overlay"},
                "tap": True,
            }
        }
    )
    touches = [event[1] for event in ui.events if event[0] == "touch"]
    assert touches == [{"x": 150, "y": 615, "by_text": None, "by_id": None, "wait_time": 0.1}]
    await agent.aclose()


@pytest.mark.asyncio
async def test_blocked_suffix_preserves_assertion_root_and_actual_count() -> None:
    present = _node(
        {"type": "Text", "id": "present", "bounds": "[0,0][100,40]"}
    )
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=_root(present)))
    result = await steps_cmd.run_steps_on_agent(
        agent,
        [
            {"wait_gone": {"by_id": "present", "timeout": 0.01}},
            {"wait": {"seconds": 0}},
        ],
        on_fail="abort",
    )
    assert result["executed"] == 1
    assert len(result["results"]) == 2

    root = result["results"][0]["step_result"]
    assert root["outcome"]["status"] == "failed"
    assert root["outcome"]["failure"]["code"] == "assertion.mismatch"

    # The suffix carries a *cause* pointing at the root, and no failure of its
    # own. Copying the root's classification onto every unexecuted step is what
    # turned one real failure into dozens of downstream defects under 0.3-p0.
    suffix = result["results"][1]["step_result"]
    assert suffix["outcome"]["status"] == "blocked"
    assert suffix["outcome"]["cause"] == {"type": "prior_step", "step_index": 0}
    assert "failure" not in suffix["outcome"]
