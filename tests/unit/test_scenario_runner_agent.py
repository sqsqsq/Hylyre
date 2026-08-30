"""L1: ScenarioRunner with HylyreAgent (fake UI + VLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.scenario.runner import ScenarioRunner
from tests.contract.fakes.fake_ui_driver import FakeUiDriver
from tests.contract.fakes.fake_vlm_client import FakeVlmClient


_PLAN_TABLE = """# T

## 测试用例清单

| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |
| --- | --- | --- | --- | --- | --- | --- |
"""


@pytest.mark.asyncio
async def test_run_on_agent_json_step_no_vlm(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    step = '{"action":{"type":"touch","by_id":"btn"}}'
    plan.write_text(
        _PLAN_TABLE + f"| TC-1 | n |  | {step} |  | P0 | AC-1 |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(
            ag, plan, feature="feat", check_expected=False
        )
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "跳过"
    assert any(e[0] == "touch" and e[1].get("by_id") == "btn" for e in ui.events)


@pytest.mark.asyncio
async def test_run_on_agent_swipe_root_step(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    step = '{"swipe":{"direction":"DOWN","distance":55}}'
    plan.write_text(
        _PLAN_TABLE + f"| TC-S | n |  | {step} |  | P0 | AC-S |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(
            ag, plan, feature="feat", check_expected=False
        )
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "跳过"
    assert any(e[0] == "swipe" for e in ui.events)


@pytest.mark.asyncio
async def test_run_on_agent_nl_step_needs_vlm(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    plan.write_text(
        _PLAN_TABLE + "| TC-1 | n |  | tap home |  | P0 | AC-1 |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(ag, plan, feature="feat", check_expected=False)
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "阻塞"
    assert "VLM" in r.case_results[0].notes


@pytest.mark.asyncio
async def test_run_on_agent_nl_with_vlm(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    plan.write_text(
        _PLAN_TABLE + "| TC-1 | n |  | tap home |  | P0 | AC-1 |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"action": {"type": "touch", "x": 10, "y": 20}}])
    ag = HylyreAgent(ui=ui, vlm=vlm)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(ag, plan, feature="feat", check_expected=False)
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "跳过"
    assert vlm.calls


@pytest.mark.asyncio
async def test_run_plan_on_agent_passes_page_name_to_start_app(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    plan.write_text(
        _PLAN_TABLE + '| TC-PN | n |  | {"touch":{"by_text":"OK"}} |  | P0 | AC-PN |\n',
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    runner = ScenarioRunner(use_fakes=False)
    try:
        await runner.run_plan_on_agent(
            ag,
            plan,
            feature="feat",
            bundle="com.example.app",
            page_name="MainAbility",
            wait_time=2.5,
            check_expected=False,
        )
    finally:
        await ag.aclose()
    starts = [e for e in ui.events if e[0] == "start_app"]
    assert len(starts) == 1
    assert starts[0][1]["bundle"] == "com.example.app"
    assert starts[0][1]["page_name"] == "MainAbility"
    assert starts[0][1]["wait_time"] == 2.5


@pytest.mark.asyncio
async def test_run_on_agent_backtick_json_step_no_vlm(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    step = '`{"touch":{"x":10,"y":20}}`'
    plan.write_text(
        _PLAN_TABLE + f"| TC-BT | n |  | {step} |  | P0 | AC-BT |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(
            ag, plan, feature="feat", check_expected=False
        )
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "跳过"
    assert any(e[0] == "touch" for e in ui.events)


@pytest.mark.asyncio
async def test_run_on_agent_fence_json_step(tmp_path: Path) -> None:
    from hylyre.scenario.runner import _execute_one_step

    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    log: list = []
    try:
        await _execute_one_step(
            ag,
            "TC-F",
            '```json\n{"back":{}}\n```',
            log,
        )
    finally:
        await ag.aclose()
    assert any(e[0] == "press_back" for e in ui.events)
    assert log == []


@pytest.mark.asyncio
async def test_run_on_agent_broken_json_friendly_error(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    plan.write_text(
        _PLAN_TABLE + "| TC-BR | n |  | {broken |  | P0 | AC-BR |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(
            ag, plan, feature="feat", check_expected=False
        )
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "阻塞"
    assert "JSON 语法错误" in r.case_results[0].notes
    assert "TC-BR" in r.case_results[0].notes


@pytest.mark.asyncio
async def test_run_on_agent_expected_assert(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    plan.write_text(
        _PLAN_TABLE
        + "| TC-1 | n |  | go | see OK | P0 | AC-1 |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    vlm = FakeVlmClient(
        responses=[
            {"action": {"type": "touch", "x": 1, "y": 2}},
            {"ok": True, "reason": ""},
        ],
    )
    ag = HylyreAgent(ui=ui, vlm=vlm)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(ag, plan, feature="feat", check_expected=True)
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "通过"
    assert len(vlm.calls) == 2
    assert r.case_results[0].expected_check_mode == "checked_vlm"
    assert r.case_results[0].steps[-1].role == "assertion"
