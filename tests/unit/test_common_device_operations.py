"""Common-operation validation, native mapping, state and observation regressions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.api.common_operation_contract import COMMON_OPERATION_KEYS
from hylyre.api.component_properties import property_value
from hylyre.api.exceptions import CapabilityUnsupported, PlannedStepContractError, SelectorResolutionError
from hylyre.api.outcome import OperationBlocked, OperationFailed, OperationPassed
from hylyre.api.selector_resolve import resolve_targets
from hylyre.api.step_dispatch import dispatch_planned_step
from hylyre.drivers.hypium import HypiumDriver
from hylyre.scenario.ledger import execute_ledger_step
from hylyre.scenario.plan_contract import iter_plan_steps, validate_planned_step
from hylyre.scenario.runner import _iter_steps, fake_step_outcome, FAKE_NAMESPACE
from tests.contract.fakes.fake_ui_driver import FakeUiDriver

P = {"x": 100, "y": 120}
Q = {"x": 200, "y": 220}
AREA = {"by_id": "area"}
TARGET = {"by_id": "field"}
EXAMPLES = {
    "drag": {"start": P, "end": Q}, "slide": {"start": P, "end": Q},
    "fling": {"direction": "up"}, "pinch_in": {"area": AREA}, "pinch_out": {"area": AREA},
    "two_finger_swipe": {"start1": P, "end1": Q, "start2": Q, "end2": P},
    "multi_finger_touch": {"points": [P, Q]},
    "gesture": {"fingers": [{"points": [P, Q, P]}]},
    "press_key": {"key": "ENTER"}, "press_combination_key": {"keys": ["CTRL_LEFT", "A"]},
    "get_component_property": {"target": TARGET, "property": "text"},
    "shell": {"command": "printf '中文;；\\n'"}, "clear_text": {"target": TARGET},
    "move_cursor": {"direction": "left"}, "set_checked": {"target": TARGET, "checked": True},
    "current_app": {}, "has_app": {"bundle": "com.example.test"}, "recent_tasks": {},
}


def node(id="field", **attrs):
    return {"attributes": {"id": id, "type": "TextInput", "text": "", "key": "key",
                           "bounds": "[80,100][300,400]", "enabled": True,
                           "checked": False, "checkable": True, "focused": "false", **attrs}, "children": []}


def tree(*children):
    return {"attributes": {"type": "Root", "bounds": "[0,0][1000,1000]"},
            "children": [node("area", type="Canvas", bounds="[50,60][600,700]"), *children]}


class StateDriver(FakeUiDriver):
    def __init__(self, **kwargs):
        super().__init__(dump_tree=tree(node()), **kwargs)
        self.values = {"checked": False, "checkable": True, "text": "", "enabled": "true"}
        self.apply_toggle = True

    async def get_component_property(self, *, target, property):
        self.events.append(("get_component_property", {"property": property}))
        return property_value(self.values, property)

    async def touch(self, **kwargs):
        await super().touch(**kwargs)
        if self.apply_toggle:
            self.values["checked"] = not self.values["checked"]

    async def current_app(self):
        return {"bundle": "com.example.test", "ability": None, "ability_unavailable": "stub"}

    async def has_app(self, *, bundle):
        return False

    async def shell(self, **kwargs):
        return {"stdout": "中文;；\n", "stderr": None, "stderr_available": False, "exit_code": 0,
                "transport_exit_code": 0, "timed_out": False, "remote_status_unknown": False,
                "raw_evidence": {"stdout": "中文;；\n\n__HYLYRE_RC_x=0\n", "stderr": ""}}


@pytest.mark.parametrize("root", COMMON_OPERATION_KEYS)
async def test_every_common_root_validates_executes_and_keeps_action_role(root, tmp_path):
    driver = StateDriver()
    agent = HylyreAgent(ui=driver)
    payload = {root: EXAMPLES[root]}
    assert validate_planned_step(payload, path="step") is None
    result = await execute_ledger_step(agent, payload, index=0, case_id="common", artifact_dir=tmp_path)
    assert result.status == "passed", result.to_dict()
    assert result.kind == root and result.role == "action"
    assert result.observation["kind"] == "action"
    if root == "has_app":
        assert result.observation["facts"]["installed"] is False
    if root == "get_component_property":
        assert result.observation["facts"]["value"] == ""
    if root == "shell":
        assert (tmp_path / result.artifacts[0]["path"]).is_file()


INVALID = [
    ("touch", {"x": 1, "y": 2, "mode": "double", "press_time": 3}),
    ("touch", {"x": 1, "y": 2, "mode": "long", "press_time": float("nan")}),
    ("drag", {"start": P, "end": Q, "speed": 10, "drag_time": 1}),
    ("drag", {"start": P}), ("slide", {"start": P, "end": Q, "speed": 4}),
    ("slide", {"start": {"x": 1.2, "y": 2}, "end": Q}),
    ("fling", {"direction": "up", "speed": 5}), ("fling", {"direction": "around"}),
    ("fling", {"direction": "up", "distance": 101}),
    ("pinch_in", {"area": AREA, "scale": 1}),
    ("pinch_out", {"area": AREA, "scale": float("inf")}),
    ("pinch_out", {"area": AREA, "dead_zone_ratio": 0.5}),
    ("two_finger_swipe", {"start1": P, "end1": Q, "start2": P}),
    ("multi_finger_touch", {"points": [P]}),
    ("multi_finger_touch", {"points": [P] * 5}),
    ("gesture", {"fingers": [{"points": [P]}]}),
    ("gesture", {"fingers": []}),
    ("press_key", {"key": "NOT_A_KEY"}), ("press_key", {"key": True}),
    ("press_combination_key", {"keys": ["A"]}),
    ("press_combination_key", {"keys": ["A", "A"]}),
    ("press_combination_key", {"keys": ["A", "B"], "mode": "long"}),
    ("get_component_property", {"target": TARGET, "property": "unknown"}),
    ("clear_text", {"target": P}), ("move_cursor", {"direction": "left", "times": 0}),
    ("set_checked", {"target": TARGET, "checked": "false"}),
    ("current_app", {"guess": True}), ("has_app", {"bundle": ""}),
    ("shell", {"command": "printf ok", "timeout": -1}),
    ("shell", {"command": ""}),
    ("wait_gone", {"by_id": "field", "checked": "false"}),
]


@pytest.mark.parametrize("root,block", INVALID)
async def test_invalid_input_is_rejected_before_connect(root, block):
    driver = StateDriver()
    agent = HylyreAgent(ui=driver)
    payload = {root: block}
    assert validate_planned_step(payload, path="step") is not None
    with pytest.raises(PlannedStepContractError):
        await dispatch_planned_step(agent, payload)
    assert driver.events == []


@pytest.mark.parametrize("raw,expected", [
    ('点击A；点击B', ["点击A", "点击B"]), ('点击"确定";返回', ['点击"确定"', '返回']),
    ('`{"shell":{"command":"a;b"}}`;{"back":{}}', ['{"shell":{"command":"a;b"}}', '{"back":{}}']),
    ('```json\n{\n"input": {"text": "中文；;\\n\\\"引号\\\""}\n}\n```', ['{\n"input": {"text": "中文；;\\n\\\"引号\\\""}\n}']),
])
def test_plan_splitting_is_shared_and_preserves_json(raw, expected):
    assert iter_plan_steps(raw) == _iter_steps(raw) == expected


@pytest.mark.parametrize("name", ["checked", "checkable", "focused", "enabled", "clickable", "scrollable"])
def test_boolean_filters_preserve_false_and_reject_missing(name):
    observed = tree(node(**{name: "false"}))
    assert len(resolve_targets(observed, {"by_id": "field", name: False})) == 1
    assert resolve_targets(observed, {"by_id": "field", name: True}) == []
    observed["children"][1]["attributes"].pop(name)
    with pytest.raises(CapabilityUnsupported):
        resolve_targets(observed, {"by_id": "field", name: False})


async def test_missing_property_never_proves_wait_gone():
    driver = StateDriver()
    driver.dump_tree["children"][1]["attributes"].pop("checked")
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {"wait_gone": {"by_id": "field", "checked": True, "timeout": 0}})
    assert isinstance(result, OperationBlocked)


async def test_property_predicate_mismatch_and_disappearance_keep_assertion_semantics():
    agent = HylyreAgent(ui=StateDriver())
    result = await dispatch_planned_step(agent, {"wait_for": {"by_id": "field", "checked": True, "timeout": 0}})
    assert isinstance(result, OperationFailed) and result.failure.code == "assertion.mismatch"
    result = await dispatch_planned_step(agent, {"wait_for": {"by_id": "field", "checked": False, "timeout": 0}})
    assert isinstance(result, OperationPassed)
    result = await dispatch_planned_step(agent, {"wait_gone": {"by_id": "missing", "checked": True, "timeout": 0}})
    assert isinstance(result, OperationPassed)


@pytest.mark.parametrize("before,desired,checkable,toggle,status,clicks", [
    (True, True, True, True, OperationPassed, 0),
    (False, True, True, True, OperationPassed, 1),
    (True, False, True, True, OperationPassed, 1),
    (False, True, False, True, OperationFailed, 0),
    (False, True, True, False, OperationFailed, 1),
])
async def test_set_checked_is_idempotent_and_confirms_once(before, desired, checkable, toggle, status, clicks):
    driver = StateDriver()
    driver.values.update(checked=before, checkable=checkable)
    driver.apply_toggle = toggle
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {"set_checked": {"target": TARGET, "checked": desired, "timeout": 0.001}})
    assert isinstance(result, status)
    assert len([event for event in driver.events if event[0] == "touch"]) == clicks
    if result.observation:
        assert result.observation.facts["changed"] == bool(clicks)
        assert result.observation.facts["before"] == before


@pytest.mark.parametrize("end", [{"by_id": "missing"}, {"x": 2000, "y": 20}])
async def test_all_endpoints_validate_before_touch(end):
    driver = StateDriver()
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"drag": {"start": P, "end": end}}, index=0, case_id="endpoint")
    assert result.status == "failed"
    assert result.failure["code"] == ("contract.invalid_step" if "x" in end else "selector.not_found")
    assert not any(event[0] == "drag" for event in driver.events)


async def test_ambiguous_endpoint_and_area_rejected_before_injection():
    driver = StateDriver()
    driver.dump_tree["children"].append(node())
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {"drag": {"start": P, "end": TARGET}})
    assert isinstance(result, OperationFailed) and result.failure.code == "selector.ambiguous"
    assert not any(event[0] == "drag" for event in driver.events)


@pytest.fixture
def native(monkeypatch):
    pytest.importorskip("hypium")
    raw = MagicMock()
    raw.device_sn = "selected-device"
    shim = MagicMock()
    shim.BY.id.side_effect = lambda value: ("id", value)
    monkeypatch.setattr("hylyre.drivers.hypium.driver.load_hypium_shim", lambda: shim)
    driver = HypiumDriver()
    driver._raw = raw
    return driver, raw


@pytest.mark.parametrize("mode,press_time", [("normal", None), ("double", None), ("long", None), ("long", 3)])
@pytest.mark.parametrize("target", [{"x": 100, "y": 200}, {"by_id": "field"}])
async def test_native_touch_modes_preserve_wait(native, monkeypatch, mode, press_time, target):
    driver, raw = native
    sleep = AsyncMock()
    monkeypatch.setattr("hylyre.drivers.hypium.driver.asyncio.sleep", sleep)
    kwargs = {**target, "mode": mode, "wait_time": 0.5}
    if press_time is not None:
        kwargs["press_time"] = press_time
    await driver.touch(**kwargs)
    if mode == "long":
        raw.long_click.assert_called_once()
        assert raw.long_click.call_args.kwargs["press_time"] == (press_time or 2)
        raw.touch.assert_not_called()
        sleep.assert_awaited_once_with(0.5)
    else:
        assert raw.touch.call_args.kwargs["mode"] == mode
        assert raw.touch.call_args.kwargs["wait_time"] == 0.5


@pytest.mark.parametrize("mode,press_time", [("double", None), ("long", 3)])
async def test_rich_touch_keeps_mode_and_duration(mode, press_time):
    driver = StateDriver()
    block = {"by_id": "field", "focused": False, "mode": mode}
    if press_time is not None:
        block["press_time"] = press_time
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {"touch": block})
    assert isinstance(result, OperationPassed)
    event = [event for event in driver.events if event[0] == "touch"][0][1]
    assert event["mode"] == mode and event["x"] == 190
    if press_time is not None:
        assert event["press_time"] == press_time


async def test_native_gesture_injects_whole_paths_once(native):
    driver, raw = native
    fingers = [[(100, 100), (150, 180), (200, 200)], [(200, 200), (300, 300)]]
    await driver.gesture(fingers=fingers[:1])
    gesture = raw.inject_gesture.call_args.args[0]
    assert [s.pos for s in gesture.steps] == fingers[0]
    assert [s.type for s in gesture.steps] == ["start", "move", "move"]
    assert raw.inject_gesture.call_args.kwargs == {"speed": 2000}
    await driver.gesture(fingers=fingers, speed=2500)
    gestures = raw.inject_multi_finger_gesture.call_args.args[0]
    assert [[s.pos for s in g.steps] for g in gestures] == fingers
    raw.inject_gesture.assert_called_once()
    raw.inject_multi_finger_gesture.assert_called_once()
    raw.slide.assert_not_called()


@pytest.mark.parametrize("operation", ["two_finger_swipe", "multi_finger_touch"])
async def test_native_area_rect_and_screen_integer_pixels(native, operation):
    driver, raw = native
    area = (50, 60, 600, 700)
    points = [(50, 60), (51, 61), (200, 300), (400, 500)]
    if operation == "two_finger_swipe":
        await driver.two_finger_swipe(start1=points[0], end1=points[1], start2=points[2], end2=points[3], area=area, duration=2)
        args = raw.two_finger_swipe.call_args.args
    else:
        await driver.multi_finger_touch(points=points, area=area, duration=2)
        args = raw.multi_finger_touch.call_args.args[0]
    call = getattr(raw, operation).call_args
    rect = call.kwargs["area"]
    assert (rect.left, rect.top, rect.right, rect.bottom) == area
    assert list(args) == [(0, 0), (1, 1), (150, 240), (350, 440)]
    assert all(type(v) is int for p in args for v in p)
    assert call.kwargs["duration"] == 2


@pytest.mark.parametrize("direction", ["up", "DOWN", "Left", "right"])
async def test_fling_and_cursor_direction_mapping(native, direction):
    driver, raw = native
    await driver.fling(direction=direction)
    raw.fling.assert_called_once_with(direction.upper(), distance=50, area=None, speed="fast")
    await driver.move_cursor(direction=direction.lower())
    raw.move_cursor.assert_called_once_with(direction.upper(), times=1)


async def test_native_keys_slide_drag_pinch_and_edit_mapping(native):
    from hypium.model.basic_data_type import KeyCode
    driver, raw = native
    await driver.press_key(key="ENTER", mode="double")
    raw.press_key.assert_called_once_with(KeyCode.ENTER, mode="double")
    raw._driver_impl.driver.get_os_info.return_value = ("OpenHarmony", "6")
    await driver.press_combination_key(keys=["CTRL_LEFT", "A", 2054])
    raw.press_combination_key.assert_called_once_with(KeyCode.CTRL_LEFT, KeyCode.A, 2054)
    await driver.slide(start=(100, 200), end=(300, 400))
    raw.slide.assert_called_once_with((100, 200), (300, 400), slide_time=0.3)
    raw._driver_impl.driver.get_api_level.return_value = 20
    await driver.drag(start=(100, 200), end=(300, 400), press_time=3, speed=1000)
    raw.drag.assert_called_once_with((100, 200), (300, 400), press_time=3, drag_time=1, speed=1000)
    await driver.pinch_in(area=(50, 60, 600, 700), scale=0.5, direction="horizontal", dead_zone_ratio=0.1)
    assert raw.pinch_in.call_args.kwargs == {"scale": 0.5, "direction": "horizontal", "dead_zone_ratio": 0.1}
    await driver.pinch_out(area=(50, 60, 600, 700))
    assert raw.pinch_out.call_args.kwargs["scale"] == 1.6
    await driver.move_cursor(direction="begin", times=2)
    raw.move_cursor.assert_called_once_with("begin", times=2)
    await driver.recent_tasks()
    raw.swipe_to_recent_task.assert_called_once_with()


async def test_custom_drag_press_time_cannot_be_ignored(native):
    driver, raw = native
    raw._driver_impl.driver.get_api_level.return_value = 19
    with pytest.raises(CapabilityUnsupported):
        await driver.drag(start=(1, 2), end=(3, 4), press_time=3)
    raw.drag.assert_not_called()


async def test_native_property_identity_and_empty_text(native):
    from hypium.model.basic_data_type import Rect
    driver, raw = native
    first, second = object(), object()
    raw.find_all_components.return_value = [first, second]
    def read(component, name):
        if name == "bounds":
            return Rect(left=80 if component is second else 0, top=100, right=300, bottom=400)
        return "false" if name == "checked" else "" if name == "text" else "TextInput"
    raw.get_component_property.side_effect = read
    target = {"id": "field", "bounds": "[80,100][300,400]", "point": [190, 250]}
    assert await driver.get_component_property(target=target, property="checked") is False
    assert await driver.get_component_property(target=target, property="text") == ""
    await driver.clear_text(target=target)
    raw.clear_text.assert_called_once_with(second)


async def test_has_app_exact_match_without_bundle_interpolation(native, monkeypatch):
    driver, raw = native
    shell = AsyncMock(return_value={"exit_code": 0, "stdout": "bundle list:\ncom.example.test.extra\ncom.installed\n", "transport_exit_code": 0})
    monkeypatch.setattr(driver, "shell", shell)
    assert await driver.has_app(bundle="com.example.test") is False
    assert await driver.has_app(bundle="com.installed") is True
    assert all(call.kwargs == {"command": "bm dump -a"} for call in shell.await_args_list)
    raw.has_app.assert_not_called()


@pytest.mark.parametrize("value", [(None, None), ("", ""), None])
async def test_current_app_requires_observed_bundle(native, value):
    driver, raw = native
    raw.current_app.return_value = value
    with pytest.raises(CapabilityUnsupported):
        await driver.current_app()


@pytest.mark.parametrize("root", ["get_component_property", "current_app", "has_app", "set_checked", "shell", "wait_for", "wait_gone"])
def test_fake_never_invents_query_or_state_facts(root):
    result = fake_step_outcome({root: EXAMPLES.get(root, {})}, kind=root, role="assertion" if root.startswith("wait_") else "action")
    assert isinstance(result, OperationBlocked)
    assert result.extensions[FAKE_NAMESPACE]["device"] is False


async def test_old_driver_subclass_instantiates_and_optional_operation_blocks():
    driver = FakeUiDriver()
    assert not driver.__class__.__abstractmethods__
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {"current_app": {}})
    assert isinstance(result, OperationBlocked)


@pytest.mark.parametrize("raw", ['{"back":{}}junk', '{"back":{}} {"home":{}}'])
def test_json_without_a_step_separator_is_rejected_as_one_step(raw):
    steps = iter_plan_steps(raw)
    assert steps == [raw]
    assert validate_planned_step(steps[0], path="step") is not None


async def test_missing_nested_property_never_proves_absence():
    driver = StateDriver()
    driver.dump_tree["children"][1]["attributes"].pop("checked")
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {"wait_gone": {"all": [{"by_id": "field"}, {"checked": True}], "timeout": 0}})
    assert isinstance(result, OperationBlocked)


async def test_unverifiable_screen_and_outside_area_do_not_inject():
    driver = StateDriver()
    driver.dump_tree["attributes"].pop("bounds")
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {"drag": {"start": P, "end": Q}})
    assert isinstance(result, OperationBlocked)
    assert not any(event[0] == "drag" for event in driver.events)
    driver.dump_tree = tree(node())
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"multi_finger_touch": {"points": [P, {"x": 600, "y": 700}], "area": AREA}}, index=0, case_id="area")
    assert result.failure["code"] == "contract.invalid_step"
    assert not any(event[0] == "multi_finger_touch" for event in driver.events)


async def test_sdk_cannot_silently_ignore_short_drag_hold(native):
    driver, raw = native
    with pytest.raises(CapabilityUnsupported):
        await driver.drag(start=(100, 100), end=(200, 200), press_time=0.5)
    raw.drag.assert_not_called()


async def test_batch_and_daemon_validate_all_steps_before_first_action_or_start_app():
    from hylyre.cli.commands.steps_cmd import run_steps_on_agent
    from hylyre.session.daemon import _dispatch
    driver = StateDriver()
    agent = HylyreAgent(ui=driver)
    steps = [{"touch": {"x": 100, "y": 100}}, {"slide": {"start": P, "end": Q, "speed": 3}}]
    assert (await run_steps_on_agent(agent, steps))["command_status"] == "rejected"
    assert (await _dispatch(agent, "run_steps", {"steps": steps, "bundle": "com.example.test"}))["command_status"] == "rejected"
    assert driver.events == []


def test_sync_batch_rejects_before_constructing_agent(monkeypatch):
    from hylyre.cli.commands import steps_cmd
    called = MagicMock(side_effect=AssertionError("must not construct agent"))
    monkeypatch.setattr(steps_cmd, "_with_hypium_agent", called)
    steps = [{"touch": {"x": 100, "y": 100}}, {"slide": {"start": P, "end": Q, "speed": 3}}]
    assert steps_cmd.execute_run_steps(steps, bundle="com.example.test")["command_status"] == "rejected"
    called.assert_not_called()


async def test_session_shell_log_is_relative_to_authoritative_trace_directory(tmp_path):
    from hylyre.session.daemon import _dispatch
    result = await _dispatch(HylyreAgent(ui=StateDriver()), "run_steps", {
        "steps": [{"shell": {"command": "printf ok"}}],
        "failure_dir": str(tmp_path / "failures"), "artifact_base": str(tmp_path),
    })
    artifact = result["results"][0]["step_result"]["artifacts"][0]
    assert artifact["path"].startswith("failures/")
    assert (tmp_path / artifact["path"]).is_file()


@pytest.mark.parametrize("operation", ["pinch_in", "pinch_out"])
async def test_review_b1_vertical_pinch_rejected_before_connect(operation):
    driver = StateDriver()
    payload = {operation: {"area": AREA, "direction": "vertical"}}
    assert validate_planned_step(payload, path="step") is not None
    with pytest.raises(PlannedStepContractError):
        await dispatch_planned_step(HylyreAgent(ui=driver), payload)
    assert driver.events == []


@pytest.mark.parametrize("bounds", ["[50,60][50,60]", "not bounds", ""])
async def test_review_b2_invalid_area_is_contract_not_missing_target(bounds):
    driver = StateDriver()
    driver.dump_tree["children"][0]["attributes"]["bounds"] = bounds
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"multi_finger_touch": {"points": [P, Q], "area": AREA}}, index=0, case_id="area")
    assert result.failure["code"] == "contract.invalid_step"
    assert not any(event[0] == "multi_finger_touch" for event in driver.events)


async def test_review_b2_noncheckable_is_contract_with_real_unique_target():
    driver = StateDriver()
    driver.values["checkable"] = False
    driver.values.pop("checked")
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"set_checked": {"target": TARGET, "checked": True}}, index=0, case_id="noncheckable")
    assert result.failure["code"] == "contract.invalid_step"
    assert result.selector["resolution"]["state"] == "unique"
    assert not any(event[0] == "touch" for event in driver.events)


async def test_review_b2_noninput_clear_is_contract(native, monkeypatch):
    driver, raw = native
    component = object()
    monkeypatch.setattr(driver, "_native_identity", AsyncMock(return_value=component))
    raw.get_component_property.return_value = "Text"
    with pytest.raises(PlannedStepContractError):
        await driver.clear_text(target={"id": "text"})
    raw.clear_text.assert_not_called()


@pytest.mark.parametrize("error", [
    CapabilityUnsupported("property channel unavailable after click"),
    SelectorResolutionError("target moved after click"),
    SelectorResolutionError("two candidates after click", failure_code="selector_ambiguous"),
    ConnectionError("device disconnected after click"),
])
async def test_review_b3_confirmation_exception_retains_dispatched_facts(error):
    class ConfirmFails(StateDriver):
        async def get_component_property(self, *, target, property):
            if any(event[0] == "touch" for event in self.events):
                raise error
            return await super().get_component_property(target=target, property=property)
    driver = ConfirmFails()
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"set_checked": {"target": TARGET, "checked": True}}, index=0, case_id="confirmation")
    assert result.status == "failed"
    assert result.failure["code"] == "infrastructure.x_hylyre.state_confirmation_failed"
    assert result.observation["performed"] is True
    facts = result.observation["facts"]
    assert facts["before"] is False and facts["changed"] is True and facts["after"] is None
    assert facts["confirmation_error"]["type"] == type(error).__name__
    assert len([event for event in driver.events if event[0] == "touch"]) == 1


def nested_control_tree():
    child = node(text="张三", checked=True, clickable=False, bounds="[100,120][200,160]")
    parent = node("parent", text="", type="ListItem", checked=False, checkable=False,
                  clickable=True, bounds="[50,80][500,400]")
    parent["children"] = [child]
    return tree(parent)


@pytest.mark.parametrize("operation", ["get_component_property", "clear_text", "set_checked"])
async def test_review_b4_data_target_by_text_keeps_matching_child(operation):
    class NodeDriver(StateDriver):
        async def get_component_property(self, *, target, property):
            if property == "text":
                return target["text"]
            return await super().get_component_property(target=target, property=property)
    driver = NodeDriver()
    driver.dump_tree = nested_control_tree()
    payload = {"target": {"by_text": "张三"}}
    if operation == "get_component_property":
        payload["property"] = "text"
    elif operation == "set_checked":
        payload["checked"] = True
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {operation: payload})
    assert isinstance(result, OperationPassed)
    assert result.observation.facts["target"]["id"] == "field"
    if operation == "get_component_property":
        assert result.observation.facts["value"] == "张三"
    if operation == "clear_text":
        assert [event for event in driver.events if event[0] == "clear_text"][0][1]["target"]["id"] == "field"


async def test_review_b4_property_wait_reads_child_and_touch_still_lifts_parent():
    driver = StateDriver()
    driver.dump_tree = nested_control_tree()
    agent = HylyreAgent(ui=driver)
    result = await dispatch_planned_step(agent, {"wait_for": {"by_text": "张三", "checked": True, "timeout": 0}})
    assert isinstance(result, OperationPassed)
    assert result.selector.resolution.selected["id"] == "field"
    assert result.observation.facts["property_observations"][0]["properties"]["checked"] is True
    result = await dispatch_planned_step(agent, {"wait_for": {"all": [{"by_text": "张三"}, {"checked": True}], "timeout": 0}})
    assert isinstance(result, OperationPassed)
    result = await dispatch_planned_step(agent, {"wait_for": {"all": [{"by_text": "张三", "checked": False}], "timeout": 0}})
    assert isinstance(result, OperationFailed) and result.failure.code == "assertion.mismatch"
    result = await dispatch_planned_step(agent, {"touch": {"by_text": "张三"}})
    assert isinstance(result, OperationPassed)
    event = [event for event in driver.events if event[0] == "touch"][-1][1]
    assert (event["x"], event["y"]) == (275, 240)


@pytest.mark.parametrize("predicate", [{"scrollable": True}, {"all": [{"scrollable": True}, {"by_type": "Scroll"}]}])
def test_review_root_empty_boolean_placeholders_do_not_pollute_property_only_search(predicate):
    from hylyre.api.component_properties import BOOLEAN_PROPERTIES
    flags = {name: "false" for name in BOOLEAN_PROPERTIES}
    wrapper = {"attributes": {"bounds": "[0,0][1000,1000]", **{name: "" for name in BOOLEAN_PROPERTIES}},
               "children": [node("list", type="Scroll", **{**flags, "scrollable": "true"})]}
    hits = resolve_targets(wrapper, predicate)
    assert [hit.id for hit in hits] == ["list"]
    wrapper["children"][0]["attributes"].pop("scrollable")
    with pytest.raises(CapabilityUnsupported):
        resolve_targets(wrapper, predicate)


@pytest.mark.parametrize("os_info,supported", [(('OpenHarmony', '6'), True), (('HarmonyOS', '6'), False), (('HMOS', '5'), False), (None, False)])
async def test_review_three_keys_never_degrade_on_hmos(native, os_info, supported):
    from hypium.model.basic_data_type import KeyCode
    driver, raw = native
    raw._driver_impl.driver.get_os_info.return_value = os_info
    if supported:
        await driver.press_combination_key(keys=["CTRL_LEFT", "SHIFT_LEFT", "A"])
        raw.press_combination_key.assert_called_once_with(KeyCode.CTRL_LEFT, KeyCode.SHIFT_LEFT, KeyCode.A)
    else:
        with pytest.raises(CapabilityUnsupported):
            await driver.press_combination_key(keys=["CTRL_LEFT", "SHIFT_LEFT", "A"])
        raw.press_combination_key.assert_not_called()


async def test_review_has_app_transport_failure_keeps_transport_domain(native, monkeypatch):
    driver, raw = native
    monkeypatch.setattr(driver, "shell", AsyncMock(return_value={"exit_code": 0, "transport_exit_code": 1, "stdout": "com.example.test"}))
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"has_app": {"bundle": "com.example.test"}}, index=0, case_id="query")
    assert result.status == "failed" and result.failure["code"] == "infrastructure.transport_failure"


@pytest.mark.parametrize("root", ["wait_for", "wait_gone"])
@pytest.mark.parametrize("predicate", [
    {"by_text": "张三", "clickable": True},
    {"all": [{"by_text": "张三"}, {"by_type": "ListItem"}]},
])
async def test_review_r2_legacy_rich_wait_still_observes_lifted_parent(root, predicate):
    driver = StateDriver()
    driver.dump_tree = nested_control_tree()
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {root: {**predicate, "timeout": 0}})
    assert isinstance(result, OperationPassed if root == "wait_for" else OperationFailed)
    assert result.selector.resolution.selected["id"] == "parent"
    if root == "wait_gone":
        assert result.observation.matched is False


@pytest.mark.parametrize("root", ["wait_for", "wait_gone"])
@pytest.mark.parametrize("predicate", [
    {"by_text": "张三", "checked": True},
    {"all": [{"by_text": "张三"}, {"checkable": True}]},
    {"all": [{"by_text": "张三", "focused": False}]},
])
async def test_review_r2_new_state_wait_observes_actual_child_including_nested(root, predicate):
    driver = StateDriver()
    driver.dump_tree = nested_control_tree()
    driver.dump_tree["children"][1]["attributes"]["focused"] = True
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {root: {**predicate, "timeout": 0}})
    assert isinstance(result, OperationPassed if root == "wait_for" else OperationFailed)
    assert result.selector.resolution.selected["id"] == "field"
    assert result.observation.facts["property_observations"][0]["id"] == "field"


@pytest.mark.parametrize("root", ["wait_for", "wait_gone"])
@pytest.mark.parametrize("predicate", [
    {"by_text": "张三", "clickable": True, "checked": True},
    {"all": [{"by_text": "张三"}, {"by_type": "ListItem"}, {"checked": True}]},
])
async def test_review_r2_mixed_state_predicate_cannot_combine_child_and_parent_facts(root, predicate):
    driver = StateDriver()
    driver.dump_tree = nested_control_tree()
    result = await dispatch_planned_step(HylyreAgent(ui=driver), {root: {**predicate, "timeout": 0}})
    assert isinstance(result, OperationFailed if root == "wait_for" else OperationPassed)
    assert result.observation.facts["observed_present"] is False


@pytest.mark.parametrize("index", [0, 1, 99])
@pytest.mark.parametrize("root", ["wait_for", "wait_gone"])
async def test_device_wait_index_zero_matches_reaches_presence_absence_contract(index, root):
    driver = StateDriver()
    driver.dump_tree["children"][1]["attributes"].update(type="checkBox", checked=True)
    payload = {root: {"by_type": "checkBox", "index": index, "checked": False, "timeout": 0}}
    result = await execute_ledger_step(HylyreAgent(ui=driver), payload, index=0, case_id="device-index")
    assert result.status == ("passed" if root == "wait_gone" else "failed")
    assert result.observation["facts"]["observed_present"] is False
    assert result.observation["assertion_type"] == ("absence" if root == "wait_gone" else "presence")
    assert result.observation["facts"]["property_observations"] == [{"id": "field", "properties": {"checked": True}}]
    if root == "wait_for":
        assert result.failure["code"] == "assertion.mismatch"


@pytest.mark.parametrize("index", [0, 3])
async def test_device_wait_index_target_disappearance_is_real_absence(index):
    result = await execute_ledger_step(HylyreAgent(ui=StateDriver()), {"wait_gone": {
        "by_type": "checkBox", "index": index, "checked": False, "timeout": 0,
    }}, index=0, case_id="gone")
    assert result.status == "passed"
    assert result.observation["facts"]["property_observations"] == []


@pytest.mark.parametrize("index", [1, 99])
async def test_device_wait_nonempty_wrong_index_never_proves_absence(index):
    result = await execute_ledger_step(HylyreAgent(ui=StateDriver()), {"wait_gone": {
        "by_id": "field", "index": index, "checked": False, "timeout": 0,
    }}, index=0, case_id="wrong-index")
    assert result.status == "failed" and result.failure["domain"] == "selector"
    assert "out of range for 1 hit" in result.diagnostic
    assert result.observation is None


@pytest.mark.parametrize("index", [-1, True, "0", 1.5])
async def test_device_wait_invalid_index_never_becomes_absence(index):
    result = await execute_ledger_step(HylyreAgent(ui=StateDriver()), {"wait_gone": {
        "by_id": "missing", "index": index, "checked": False, "timeout": 0,
    }}, index=0, case_id="invalid-index")
    assert result.status == "failed" and result.failure["domain"] == "contract"
    assert result.observation is None


async def test_device_wait_multiple_matching_candidates_are_not_absent():
    driver = StateDriver()
    driver.dump_tree["children"].append(node("second", checked=False))
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"wait_gone": {
        "by_type": "TextInput", "checked": False, "timeout": 0,
    }}, index=0, case_id="multiple")
    assert result.status == "failed" and result.failure["code"] == "assertion.mismatch"
    assert result.observation["facts"]["observed_present"] is True
    assert result.selector["resolution"]["state"] == "ambiguous"


def test_device_wait_empty_index_option_does_not_change_action_resolver():
    from hylyre.api.selector_resolve import resolve_one
    with pytest.raises(SelectorResolutionError):
        resolve_one(tree(node()), {"by_id": "missing", "index": 0})
    with pytest.raises(SelectorResolutionError):
        resolve_targets(tree(node()), {"by_id": "field", "index": 1}, allow_empty=True)


async def test_device_wait_index_observation_uses_the_selected_matching_node():
    driver = StateDriver()
    driver.dump_tree["children"][1]["attributes"]["checked"] = True
    driver.dump_tree["children"].append(node("second", checked=False))
    result = await execute_ledger_step(HylyreAgent(ui=driver), {"wait_for": {
        "by_type": "TextInput", "index": 0, "checked": False, "timeout": 0,
    }}, index=0, case_id="selected")
    assert result.status == "passed"
    assert result.selector["resolution"]["selected"]["id"] == "second"
    assert result.observation["facts"]["property_observations"] == [{"id": "second", "properties": {"checked": False}}]



def test_future_registered_observation_operation_uses_registration_fake_policy(monkeypatch):
    from hylyre.api.common_operation_contract import COMMON_OPERATION_REQUIRES_OBSERVATION
    monkeypatch.setitem(COMMON_OPERATION_REQUIRES_OBSERVATION, "future_device_query", True)
    result = fake_step_outcome({"future_device_query": {}}, kind="future_device_query", role="action")
    assert isinstance(result, OperationBlocked)
    assert result.cause.capability_id == "fake.ui_observation"
    assert result.extensions[FAKE_NAMESPACE]["device"] is False


@pytest.mark.parametrize("root", ["drag", "slide", "fling", "pinch_in", "pinch_out", "two_finger_swipe", "multi_finger_touch", "gesture", "press_key", "press_combination_key", "clear_text", "move_cursor", "recent_tasks"])
def test_registered_action_fake_policy_keeps_simulated_behavior(root):
    result = fake_step_outcome({root: EXAMPLES[root]}, kind=root, role="action")
    assert isinstance(result, OperationPassed)
    assert result.observation.facts["channel"] == "fake"
    assert result.extensions[FAKE_NAMESPACE]["device"] is False
