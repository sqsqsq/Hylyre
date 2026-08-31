"""Tests for hdc force-stop argv and agent rich touch."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.api.exceptions import StepSkipped
from hylyre.api.selector_ops import is_pure_by_text_pred, scroll_until_visible
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
    await agent.run_planned_tap(
        {"touch": {"by_text": "下一步", "scope": "top_overlay"}}
    )
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
    assert resolved_outcome(result) == "partial"


@pytest.mark.asyncio
async def test_failure_dir_captures_failure_boundary_artifacts(tmp_path: Path) -> None:
    """A selector root failure inside a device session owes screen evidence."""

    tree = {
        "attributes": {"type": "Root", "bounds": "[0,0][100,100]"},
        "children": [],
    }
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))
    batch = await steps_cmd.run_steps_on_agent(
        agent,
        [{"touch": {"by_text": "no such target"}}],
        failure_dir=tmp_path,
    )
    row = batch["results"][0]
    assert row["status"] == "error"
    step = row["step_result"]
    assert step["outcome"]["failure"]["domain"] == "selector"

    kinds = {a["kind"] for a in step["artifacts"]}
    assert {"ui_dump", "screenshot"} <= kinds
    for artifact in step["artifacts"]:
        # A reference is only ever produced from a file that exists, and its
        # digest is computed from the bytes actually written.
        written = tmp_path / Path(artifact["path"]).name
        assert written.is_file()
        assert artifact["sha256"] == hashlib.sha256(written.read_bytes()).hexdigest()
        assert not Path(artifact["path"]).is_absolute()


@pytest.mark.asyncio
async def test_failure_boundary_obligation_does_not_spread(tmp_path: Path) -> None:
    """Only selector/assertion root failures capture; the rule must stay narrow."""

    tree = {
        "attributes": {"type": "Root", "bounds": "[0,0][100,100]"},
        "children": [],
    }

    class FailUi(FakeUiDriver):
        async def touch(self, **kwargs: object) -> None:
            raise RuntimeError("tap failed")

    agent = HylyreAgent(ui=FailUi(dump_tree=tree))
    batch = await steps_cmd.run_steps_on_agent(
        agent, [{"touch": {"x": 1, "y": 2}}], failure_dir=tmp_path
    )
    step = batch["results"][0]["step_result"]
    assert step["outcome"]["failure"]["code"] == "internal.unexpected_exception"
    assert step["artifacts"] == []
    assert not list(tmp_path.glob("*.png"))


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


@pytest.mark.asyncio
async def test_input_by_type_focuses_then_types_at_cursor() -> None:
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,600]"},
        _tree_node(
            {"type": "Sheet", "bounds": "[0,200][500,600]"},
            _tree_node(
                {
                    "type": "TextInput",
                    "text": "",
                    "bounds": "[50,300][450,360]",
                    "clickable": "true",
                }
            ),
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_input(
        {
            "input": {
                "by_type": "TextInput",
                "scope": "top_overlay",
                "text": "123456",
            }
        }
    )
    touches = [e for e in ui.events if e[0] == "touch"]
    inputs = [e for e in ui.events if e[0] == "input_text"]
    assert len(touches) == 1
    assert touches[0][1]["x"] == 250
    assert touches[0][1]["y"] == 330
    assert len(inputs) == 1
    assert inputs[0][1]["text"] == "123456"
    assert inputs[0][1]["by_text"] is None
    assert inputs[0][1]["by_id"] is None


@pytest.mark.asyncio
async def test_input_into_one_step() -> None:
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][400,400]"},
        _tree_node(
            {
                "type": "TextInput",
                "text": "",
                "bounds": "[10,10][110,60]",
                "clickable": "true",
            }
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_input(
        {"input": {"into": {"by_type": "TextInput"}, "text": "abc"}}
    )
    assert any(e[0] == "touch" for e in ui.events)
    inp = next(e for e in ui.events if e[0] == "input_text")
    assert inp[1]["text"] == "abc"
    assert inp[1]["by_text"] is None


@pytest.mark.asyncio
async def test_legacy_action_input_rich_selector() -> None:
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][400,400]"},
        _tree_node(
            {
                "type": "TextInput",
                "text": "",
                "bounds": "[10,10][110,60]",
                "clickable": "true",
            }
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_action(
        {"action": {"type": "input", "by_type": "TextInput", "text": "xyz"}}
    )
    assert any(e[0] == "touch" for e in ui.events)
    inp = next(e for e in ui.events if e[0] == "input_text")
    assert inp[1]["text"] == "xyz"


@pytest.mark.asyncio
async def test_input_by_text_scope_keeps_text_in_predicate() -> None:
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,600]"},
        _tree_node(
            {
                "type": "TextInput",
                "text": "验证码",
                "bounds": "[0,0][100,40]",
                "clickable": "true",
            }
        ),
        _tree_node(
            {"type": "Sheet", "bounds": "[0,200][500,600]"},
            _tree_node(
                {
                    "type": "TextInput",
                    "text": "",
                    "bounds": "[50,280][450,340]",
                    "clickable": "true",
                }
            ),
            _tree_node(
                {
                    "type": "TextInput",
                    "text": "验证码",
                    "bounds": "[50,400][450,460]",
                    "clickable": "true",
                }
            ),
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_input(
        {
            "input": {
                "by_text": "验证码",
                "scope": "top_overlay",
                "text": "123456",
            }
        }
    )
    touches = [e for e in ui.events if e[0] == "touch"]
    assert len(touches) == 1
    assert touches[0][1]["x"] == 250
    assert touches[0][1]["y"] == 430


@pytest.mark.asyncio
async def test_input_by_id_within_keeps_id_in_predicate() -> None:
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,600]"},
        _tree_node(
            {
                "type": "TextInput",
                "id": "sms_field",
                "bounds": "[0,0][100,40]",
                "clickable": "true",
            }
        ),
        _tree_node(
            {"type": "Column", "bounds": "[0,100][500,600]"},
            _tree_node(
                {"type": "Text", "text": "短信验证", "bounds": "[0,120][100,150]"},
                _tree_node(
                    {
                        "type": "TextInput",
                        "text": "",
                        "bounds": "[0,160][100,200]",
                        "clickable": "true",
                    }
                ),
                _tree_node(
                    {
                        "type": "TextInput",
                        "id": "sms_field",
                        "bounds": "[0,220][100,260]",
                        "clickable": "true",
                    }
                ),
            ),
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_input(
        {
            "input": {
                "by_id": "sms_field",
                "within": {"by_text": "短信验证"},
                "text": "1234",
            }
        }
    )
    touches = [e for e in ui.events if e[0] == "touch"]
    assert len(touches) == 1
    assert touches[0][1]["x"] == 50
    assert touches[0][1]["y"] == 240
    inp = next(e for e in ui.events if e[0] == "input_text")
    assert inp[1]["text"] == "1234"
    assert inp[1]["by_id"] is None


@pytest.mark.asyncio
async def test_input_by_id_stays_native() -> None:
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][400,400]"},
        _tree_node(
            {
                "type": "TextInput",
                "id": "sms_field",
                "text": "",
                "bounds": "[10,10][110,60]",
            }
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_input({"input": {"by_id": "sms_field", "text": "99"}})
    assert not any(e[0] == "touch" for e in ui.events)
    inp = next(e for e in ui.events if e[0] == "input_text")
    assert inp[1]["by_id"] == "sms_field"


@pytest.mark.asyncio
async def test_scroll_until_visible_immediate_in_container() -> None:
    scroll = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "true",
            "bounds": "[0,100][500,600]",
        },
        _tree_node(
            {"type": "Text", "text": "华为支付", "bounds": "[0,200][100,230]"}
        ),
    )
    tree = _tree_node({"type": "Root", "bounds": "[0,0][500,800]"}, scroll)

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "华为支付"},
        container={"by_type": "Scroll"},
    )
    assert agent.swipes == 0
    assert hit.center == (50, 215)


@pytest.mark.asyncio
async def test_scroll_bounds_fallback_when_target_sibling_of_scroll() -> None:
    """Target visible inside scroll bounds but not under scroll_root subtree."""
    scroll = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "true",
            "bounds": "[0,100][500,600]",
        }
    )
    target = _tree_node(
        {"type": "Text", "text": "华为支付", "bounds": "[50,200][150,230]"}
    )
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        scroll,
        target,
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "华为支付"},
        container={"by_type": "Scroll"},
    )
    assert agent.swipes == 0
    assert hit.center == (100, 215)


@pytest.mark.asyncio
async def test_scroll_visible_when_container_not_scrollable() -> None:
    """TC-013: Scroll reports scrollable=false but target is visible inside."""
    scroll = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "false",
            "bounds": "[0,285][1320,2036]",
        },
        _tree_node(
            {
                "type": "Row",
                "clickable": "true",
                "enabled": "true",
                "bounds": "[48,1667][1272,1819]",
            },
            _tree_node(
                {
                    "type": "Text",
                    "text": "华为支付",
                    "bounds": "[96,1715][1199,1771]",
                }
            ),
        ),
    )
    tree = _tree_node({"type": "Root", "bounds": "[0,0][1320,2800]"}, scroll)

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "华为支付"},
        container={"by_type": "Scroll"},
    )
    assert agent.swipes == 0
    assert hit.center == (660, 1743)


@pytest.mark.asyncio
async def test_scroll_pre_lift_bounds_when_target_sibling_of_croot() -> None:
    scroll = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "false",
            "bounds": "[0,100][500,600]",
        }
    )
    target = _tree_node(
        {"type": "Text", "text": "华为支付", "bounds": "[50,200][150,230]"}
    )
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        scroll,
        target,
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "华为支付"},
        container={"by_type": "Scroll"},
    )
    assert agent.swipes == 0
    assert hit.center == (100, 215)


@pytest.mark.asyncio
async def test_scroll_pre_lift_bounds_when_lifted_center_outside() -> None:
    scroll = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "false",
            "bounds": "[0,285][1320,2036]",
        }
    )
    row = _tree_node(
        {
            "type": "Row",
            "clickable": "true",
            "enabled": "true",
            "bounds": "[0,1700][1320,2500]",
        },
        _tree_node(
            {
                "type": "Text",
                "text": "华为支付",
                "bounds": "[96,1715][1199,1771]",
            }
        ),
    )
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][1320,2800]"},
        scroll,
        row,
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "华为支付"},
        container={"by_type": "Scroll"},
    )
    assert agent.swipes == 0
    assert hit.center == (647, 1743)


@pytest.mark.asyncio
async def test_scroll_visible_when_container_none() -> None:
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        _tree_node(
            {"type": "Text", "text": "已可见", "bounds": "[10,10][110,40]"}
        ),
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "已可见"},
        container=None,
    )
    assert agent.swipes == 0
    assert hit.center == (60, 25)


@pytest.mark.asyncio
async def test_scroll_native_fallback_gate_with_container() -> None:
    from hylyre.api.exceptions import SelectorResolutionError

    outside = _tree_node(
        {"type": "Text", "text": "同名", "bounds": "[0,0][100,30]"}
    )
    scroll = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "false",
            "bounds": "[0,100][500,600]",
        },
        _tree_node({"type": "Text", "text": "其他", "bounds": "[0,120][100,150]"}),
    )
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        outside,
        scroll,
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    with pytest.raises(SelectorResolutionError):
        await scroll_until_visible(
            agent,
            target_pred={"by_text": "同名"},
            container={"by_type": "Scroll"},
            max_scrolls=2,
        )
    assert agent.swipes == 0


@pytest.mark.asyncio
async def test_scroll_list_fallback_to_scroll() -> None:
    scroll_only_before = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "true",
            "bounds": "[0,100][500,600]",
        },
        _tree_node({"type": "Text", "text": "工商银行", "bounds": "[0,120][100,150]"}),
    )
    scroll_with_target = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "true",
            "bounds": "[0,100][500,600]",
        },
        _tree_node({"type": "Text", "text": "工商银行", "bounds": "[0,120][100,150]"}),
        _tree_node({"type": "Text", "text": "招商银行", "bounds": "[0,400][100,430]"}),
    )
    tree_before = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        scroll_only_before,
    )
    tree_after = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        scroll_with_target,
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
        container=None,
        max_scrolls=5,
    )
    assert agent.swipes >= 1
    assert hit.center == (50, 415)


def test_is_pure_by_text_pred_ignores_visible() -> None:
    assert is_pure_by_text_pred({"by_text": "x", "visible": True}) is True
    assert is_pure_by_text_pred({"by_text": "x", "by_type": "Button"}) is False


@pytest.mark.asyncio
async def test_scroll_by_text_fallback_with_visible_pred() -> None:
    """visible=True filters zero-area nodes in-loop; fallback resolves without visible."""
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        _tree_node(
            {
                "type": "Text",
                "text": "回退目标",
                "bounds": "[10,10][10,10]",
                "clickable": "true",
            }
        ),
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "回退目标", "visible": True},
        container=None,
    )
    assert agent.swipes == 0
    assert hit.center == (10, 10)


@pytest.mark.asyncio
async def test_scroll_to_block_triggers_by_text_fallback_with_visible() -> None:
    """Production path: _apply_scroll_to_block injects visible=True before scroll_until_visible."""
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        _tree_node(
            {
                "type": "Text",
                "text": "回退目标",
                "bounds": "[10,10][10,10]",
                "clickable": "true",
            }
        ),
    )
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    await agent.run_planned_scroll_to({"scroll_to": {"by_text": "回退目标"}})
    assert not any(e[0] == "swipe" for e in ui.events)


@pytest.mark.asyncio
async def test_scroll_degenerate_clickable_falls_back_to_text_center() -> None:
    """Zero-area clickable lift yields (0,0); tap falls back to Text node center."""
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        _tree_node(
            {
                "type": "Row",
                "clickable": "true",
                "enabled": "true",
                "bounds": "[0,0][0,0]",
            },
            _tree_node(
                {"type": "Text", "text": "目标", "bounds": "[50,50][150,80]"}
            ),
        ),
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    hit = await scroll_until_visible(
        agent,
        target_pred={"by_text": "目标", "visible": True},
        container=None,
    )
    assert agent.swipes == 0
    assert hit.center == (100, 65)
    assert hit.center != (0, 0)


@pytest.mark.asyncio
async def test_scroll_pre_lift_prefers_clickable_ranked_hit() -> None:
    scroll = _tree_node(
        {
            "type": "Scroll",
            "scrollable": "false",
            "bounds": "[0,100][500,600]",
        }
    )
    plain = _tree_node(
        {"type": "Text", "text": "项", "bounds": "[50,150][80,180]"}
    )
    clickable = _tree_node(
        {
            "type": "Row",
            "clickable": "true",
            "enabled": "true",
            "bounds": "[50,300][200,340]",
        },
        _tree_node({"type": "Text", "text": "项", "bounds": "[60,310][90,330]"}),
    )
    tree = _tree_node(
        {"type": "Root", "bounds": "[0,0][500,800]"},
        scroll,
        plain,
        clickable,
    )

    class OneDumpAgent:
        swipes = 0

        async def dump_ui(self) -> dict:
            return {"tree": tree}

        async def run_planned_swipe(self, _payload: dict) -> None:
            self.swipes += 1

    agent = OneDumpAgent()
    with pytest.raises(Exception, match="ambiguous"):
        await scroll_until_visible(
            agent,
            target_pred={"by_text": "项"},
            container={"by_type": "Scroll"},
        )
    assert agent.swipes == 0


@pytest.mark.asyncio
async def test_scroll_native_by_text_locate_when_dump_empty() -> None:
    tree = _tree_node({"type": "Root", "bounds": "[0,0][500,800]"})
    ui = FakeUiDriver(
        dump_tree=tree,
        native_locate_by_text={"仅原生": (200, 300)},
    )
    agent = HylyreAgent(ui=ui)
    with pytest.raises(Exception, match="not found"):
        await scroll_until_visible(
            agent,
            target_pred={"by_text": "仅原生", "visible": True},
            container=None,
        )


@pytest.mark.asyncio
async def test_scroll_to_block_native_touch_when_all_resolve_misses() -> None:
    tree = _tree_node({"type": "Root", "bounds": "[0,0][500,800]"})
    ui = FakeUiDriver(dump_tree=tree)
    agent = HylyreAgent(ui=ui)
    with pytest.raises(Exception, match="not found"):
        await agent.run_planned_scroll_to(
            {"scroll_to": {"by_text": "原生点击", "tap": True}}
        )
    assert not [e for e in ui.events if e[0] == "touch"]
