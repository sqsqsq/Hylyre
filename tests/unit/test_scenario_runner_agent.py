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
    assert r.case_results[0].status == "通过"
    assert any(e[0] == "touch" and e[1].get("by_id") == "btn" for e in ui.events)


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
    assert r.case_results[0].status == "失败"
    assert "VLM" in r.case_results[0].notes


@pytest.mark.asyncio
async def test_run_on_agent_nl_with_vlm(tmp_path: Path) -> None:
    plan = tmp_path / "p.md"
    plan.write_text(
        _PLAN_TABLE + "| TC-1 | n |  | tap home |  | P0 | AC-1 |\n",
        encoding="utf-8",
    )
    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"action": {"type": "touch", "by_text": "OK"}}])
    ag = HylyreAgent(ui=ui, vlm=vlm)
    runner = ScenarioRunner(use_fakes=False)
    try:
        r = await runner.run_plan_on_agent(ag, plan, feature="feat", check_expected=False)
    finally:
        await ag.aclose()
    assert r.case_results[0].status == "通过"
    assert vlm.calls


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
