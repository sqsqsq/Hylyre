"""Tests for hdc force-stop argv and agent rich touch."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.api.exceptions import StepSkipped
from hylyre.api.selector_ops import scroll_until_visible
from hylyre.cli.commands import steps_cmd
from hylyre.drivers.hypium import hdc_cli
from hylyre.scenario.runner import resolved_outcome, ScenarioRunResult
from hylyre.scenario.plan_parse import ParsedPlan, TestCase
from hylyre.scenario.runner import CaseResult
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


def test_build_force_stop_argv_positional() -> None:
    argv = hdc_cli.build_force_stop_argv(
        hdc_bin="hdc",
        bundle="com.example.app",
        serial="SN001",
    )
    assert argv == ["hdc", "-t", "SN001", "shell", "aa", "force-stop", "com.example.app"]


@pytest.mark.asyncio
async def test_by_text_uses_resolver_coordinate_tap() -> None:
    tree = {
        "attributes": {"type": "Root", "bounds": "[0,0][500,500]"},
        "children": [
            {
                "attributes": {"type": "Sheet", "bounds": "[0,200][500,500]"},
                "children": [
                    {
                        "attributes": {
                            "type": "Button",
                            "text": "下一步",
                            "bounds": "[0,300][100,350]",
                            "clickable": "true",
                        },
                        "children": [],
                    }
                ],
            },
            {
                "attributes": {
                    "type": "Button",
                    "text": "下一步",
                    "bounds": "[0,0][100,50]",
                    "clickable": "true",
                },
                "children": [],
            },
        ],
    }
    ui = FakeUiDriver(dump_tree=tree, fail_touch_by_text={"下一步"})
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_tap({"touch": {"by_text": "下一步"}})
    touches = [e for e in ui.events if e[0] == "touch"]
    assert len(touches) == 1
    assert touches[0][1]["x"] == 50
    assert touches[0][1]["y"] == 325


@pytest.mark.asyncio
async def test_legacy_action_touch_scope() -> None:
    tree = {
        "attributes": {"type": "Root", "bounds": "[0,0][500,600]"},
        "children": [
            {
                "attributes": {"type": "Sheet", "bounds": "[0,200][500,600]"},
                "children": [
                    {
                        "attributes": {
                            "type": "Button",
                            "text": "下一步",
                            "bounds": "[0,400][100,450]",
                            "clickable": "true",
                        },
                        "children": [],
                    }
                ],
            }
        ],
    }
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_action(
        {"action": {"type": "touch", "by_text": "下一步", "scope": "top_overlay"}}
    )
    touches = [e for e in ui.events if e[0] == "touch"]
    assert touches[0][1]["y"] == 425


@pytest.mark.asyncio
async def test_step_skipped_in_batch() -> None:
    class SkipUi(FakeUiDriver):
        async def assert_toast(
            self,
            text: str,
            *,
            timeout: float = 3.0,
            fuzzy: str = "equal",
            poll_interval: float = 0.3,
            on_unsupported: str = "error",
        ) -> None:
            if on_unsupported == "skip":
                raise StepSkipped("toast unsupported")
            await super().assert_toast(
                text,
                timeout=timeout,
                fuzzy=fuzzy,
                poll_interval=poll_interval,
                on_unsupported=on_unsupported,
            )

    agent = HylyreAgent(ui=SkipUi())
    batch = await steps_cmd.run_steps_on_agent(
        agent,
        [{"assert_toast": {"text": "x", "on_unsupported": "skip"}}],
    )
    assert batch["results"][0]["status"] == "skipped"


def test_resolved_outcome_skips_not_failed() -> None:
    tc = TestCase(
        case_id="T",
        name="n",
        preconditions="",
        steps="",
        expected="",
        priority="P0",
        ac_ref="",
    )
    result = ScenarioRunResult(
        feature="f",
        plan=ParsedPlan(path=Path("p.md"), cases=(tc,)),
        case_results=(CaseResult(case=tc, status="跳过", notes=""),),
        use_fakes=False,
    )
    assert resolved_outcome(result) == "success"


@pytest.mark.asyncio
async def test_failure_dir_captures_artifacts(tmp_path: Path) -> None:
    tree = {
        "attributes": {"type": "Root", "bounds": "[0,0][100,100]"},
        "children": [],
    }

    class FailUi(FakeUiDriver):
        async def touch(self, **kwargs: object) -> None:
            raise RuntimeError("tap failed")

    agent = HylyreAgent(ui=FailUi(dump_tree=tree))
    batch = await steps_cmd.run_steps_on_agent(
        agent,
        [{"touch": {"x": 1, "y": 2}}],
        failure_dir=tmp_path,
    )
    assert batch["results"][0]["status"] == "error"
    assert (tmp_path / "step-0.json").is_file()
    assert (tmp_path / "step-0.png").is_file()
    assert "failure_artifacts" in batch["results"][0]["error"]


def _tree_node(attrs: dict, *children: dict) -> dict:
    return {"attributes": attrs, "children": list(children)}


@pytest.mark.asyncio
async def test_scroll_until_visible_only_searches_inside_list() -> None:
    outside = _tree_node({"type": "Text", "text": "招商银行", "bounds": "[0,0][100,30]"})
    list_only_other = _tree_node(
        {
            "type": "List",
            "scrollable": "true",
            "bounds": "[0,100][500,600]",
        },
        _tree_node({"type": "Text", "text": "工商银行", "bounds": "[0,120][100,150]"}),
    )
    tree_before = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        outside,
        list_only_other,
    )
    list_with_target = _tree_node(
        {
            "type": "List",
            "scrollable": "true",
            "bounds": "[0,100][500,600]",
        },
        _tree_node({"type": "Text", "text": "工商银行", "bounds": "[0,120][100,150]"}),
        _tree_node({"type": "Text", "text": "招商银行", "bounds": "[0,400][100,430]"}),
    )
    tree_after = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        outside,
        list_with_target,
    )

    class SeqAgent:
        def __init__(self) -> None:
            self.dumps = [tree_before, tree_before, tree_after]
            self.i = 0
            self.swipes = 0

        async def dump_ui(self) -> dict:
            t = self.dumps[min(self.i, len(self.dumps) - 1)]
            self.i += 1
            return {"tree": t}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = SeqAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "招商银行"},
        container={"by_type": "List"},
        max_scrolls=5,
    )
    assert agent.swipes >= 1
    assert hit.center == (50, 415)
