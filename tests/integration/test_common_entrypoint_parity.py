"""Real CLI/MCP/session routes with controlled UI facts and no device access."""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from hylyre import wiring
from hylyre.api.agent import HylyreAgent
from hylyre.api.common_operation_contract import COMMON_OPERATION_KEYS
from hylyre.api.exceptions import CapabilityUnsupported
from hylyre.cli.__main__ import app
from hylyre.cli.commands import loop_cmd, steps_cmd
from hylyre.drivers.hypium import hdc_cli
from hylyre.drivers.hypium.driver import HypiumDriver
from hylyre.session.daemon import _dispatch
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


POINT_A = {"x": 30, "y": 40}
POINT_B = {"x": 120, "y": 150}
AREA = {"by_id": "area"}
TARGET = {"by_id": "control"}
SHELL_TEXT = "printf '%s' \"中文;it's \\\"quoted\\\"\" | cat\nprintf '第二行；结束'"
PAYLOADS = {
    "touch": {"x": 30, "y": 40, "mode": "double", "wait_time": 0.001},
    "drag": {"start": POINT_A, "end": POINT_B, "press_time": 3, "drag_time": 0.4},
    "slide": {"start": POINT_A, "end": POINT_B, "duration": 0.4},
    "fling": {"direction": "UP", "distance": 45, "area": AREA, "speed": "slow"},
    "pinch_in": {"area": AREA, "scale": 0.5, "direction": "horizontal", "dead_zone_ratio": 0.1},
    "pinch_out": {"area": AREA, "scale": 1.5, "direction": "diagonal", "dead_zone_ratio": 0.1},
    "two_finger_swipe": {"start1": POINT_A, "end1": POINT_B, "start2": {"x": 70, "y": 80}, "end2": {"x": 160, "y": 190}, "duration": 0.5, "area": AREA},
    "multi_finger_touch": {"points": [POINT_A, POINT_B], "duration": 0.2, "area": AREA},
    "gesture": {"fingers": [{"points": [POINT_A, POINT_B, {"by_id": "control"}]}, {"points": [{"x": 60, "y": 70}, {"x": 90, "y": 100}]}], "speed": 1800},
    "press_key": {"key": "ENTER", "mode": "double"},
    "press_combination_key": {"keys": ["CTRL_LEFT", "A"]},
    "get_component_property": {"target": TARGET, "property": "checked"},
    "shell": {"command": SHELL_TEXT, "timeout": 1.25},
    "clear_text": {"target": TARGET},
    "move_cursor": {"direction": "begin", "times": 2},
    "set_checked": {"target": TARGET, "checked": True, "timeout": 0.1},
    "current_app": {},
    "has_app": {"bundle": "com.example.missing"},
    "recent_tasks": {},
    "wait_for": {"by_id": "control", "checked": True, "checkable": True, "focused": False, "timeout": 0.1},
    "wait_gone": {"by_id": "control", "checked": False, "timeout": 0.1},
}
STEPS = [{key: value} for key, value in PAYLOADS.items()]


class StubUi(FakeUiDriver):
    def __init__(self) -> None:
        super().__init__()
        self.shell_mode = "passed"
        self.dump_tree = {
            "attributes": {"type": "Root", "bounds": "[0,0][500,500]"},
            "children": [{
                "attributes": {"id": "area", "type": "Scroll", "bounds": "[0,0][400,400]"},
                "children": [{"attributes": {"id": "control", "type": "TextInput", "text": "输入", "bounds": "[200,200][250,250]", "checked": True, "checkable": True, "focused": False}}],
            }],
        }

    async def get_component_property(self, *, target, property):
        self.events.append(("get_component_property", {"target": target, "property": property}))
        return {"checked": True, "checkable": True, "text": ""}[property]

    async def current_app(self):
        return {"bundle": "com.example.stub", "ability": None}

    async def has_app(self, *, bundle):
        return False

    async def shell(self, command, *, timeout=60):
        self.events.append(("shell", {"command": command, "timeout": timeout}))
        if self.shell_mode == "blocked":
            raise CapabilityUnsupported("stub shell capability unavailable")
        return {
            "stdout": "  中文; output\n\n",
            "stderr": None,
            "stderr_available": False,
            "exit_code": 7 if self.shell_mode == "device-failure" else (None if self.shell_mode == "timeout" else 0),
            "transport_exit_code": 3 if self.shell_mode == "transport-failure" else 0,
            "transport_error": "stub transport failure" if self.shell_mode == "transport-failure" else None,
            "timed_out": self.shell_mode == "timeout",
            "remote_status_unknown": self.shell_mode == "timeout",
        }


class RecordingAgent(HylyreAgent):
    def __init__(self, ui: StubUi) -> None:
        super().__init__(ui=ui)
        self.received: list[dict[str, Any]] = []

    async def run_planned_common_operation(self, payload, **kwargs):
        self.received.append(copy.deepcopy(payload))
        return await super().run_planned_common_operation(payload, **kwargs)

    async def run_planned_tap(self, payload):
        self.received.append(copy.deepcopy(payload))
        return await super().run_planned_tap(payload)

    async def run_planned_wait_for(self, payload):
        self.received.append(copy.deepcopy(payload))
        return await super().run_planned_wait_for(payload)

    async def run_planned_wait_gone(self, payload):
        self.received.append(copy.deepcopy(payload))
        return await super().run_planned_wait_gone(payload)


@pytest.fixture
def routed_agent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    ui = StubUi()
    agent = RecordingAgent(ui)

    def forbid_device(*args, **kwargs):
        pytest.fail("offline entrypoint test attempted to use a real device")

    monkeypatch.setattr(HypiumDriver, "connect", forbid_device)
    monkeypatch.setattr(hdc_cli, "hdc_exe", forbid_device)
    monkeypatch.setattr(hdc_cli, "list_targets", forbid_device)
    monkeypatch.setattr(wiring, "create_hypium_agent", lambda **kwargs: agent)
    monkeypatch.setattr(wiring, "create_hypium_agent_with_env_vlm", lambda **kwargs: agent)
    monkeypatch.setattr(loop_cmd, "create_hypium_agent", lambda **kwargs: agent)

    def ipc(_path, method, params):
        # Preserve the actual daemon dispatch, substituting only its socket.
        wire_params = json.loads(json.dumps(params, ensure_ascii=False))
        return asyncio.run(_dispatch(agent, method, wire_params))

    monkeypatch.setattr(loop_cmd, "_session_ipc", ipc)
    monkeypatch.setattr(steps_cmd, "_session_ipc", ipc)
    return agent, ui


def cli_command(root: str) -> str:
    return "tap" if root == "touch" else root.replace("_", "-")


def invoke_atomic(root: str, payload: dict, *, session: bool = False):
    args = ["run", cli_command(root), "--json", json.dumps(payload, ensure_ascii=False)]
    if session:
        args += ["--session", "stub-session.json"]
    else:
        args += ["--device-sn", "stub-device"]
    return CliRunner().invoke(app, args)


@pytest.mark.parametrize("root", PAYLOADS)
@pytest.mark.parametrize("session", [False, True], ids=["one-shot", "daemon"])
def test_every_atomic_cli_reaches_the_shared_agent(routed_agent, root, session):
    agent, _ui = routed_agent
    payload = {root: PAYLOADS[root]}
    result = invoke_atomic(root, payload, session=session)
    assert result.exit_code == 0, result.output
    step = json.loads(result.stdout)["step_result"]
    assert step["kind"] == root
    assert step["outcome"]["status"] == "passed"
    assert agent.received == [payload]


@pytest.mark.parametrize("session", [False, True], ids=["one-shot", "mcp-session"])
async def test_every_atomic_mcp_reaches_the_shared_agent(routed_agent, session):
    from fastmcp import Client
    from hylyre.mcp.server import build_mcp

    agent, _ui = routed_agent
    async with Client(build_mcp()) as client:
        args = {"device_sn": "stub-device"}
        if session:
            opened = await client.call_tool("hylyre_open_session", args)
            args = {"session_id": json.loads(opened.content[0].text)["session_id"]}
        tools = {tool.name for tool in await client.list_tools()}
        for payload in STEPS:
            root = next(iter(payload))
            name = "hylyre_run_tap" if root == "touch" else f"hylyre_run_{root}"
            assert name in tools
            response = await client.call_tool(name, {"payload": payload, **args})
            step = json.loads(response.content[0].text)["step_result"]
            assert step["kind"] == root
            assert step["outcome"]["status"] == "passed", (root, step)
        if session:
            await client.call_tool("hylyre_close_session", args)
    assert agent.received == STEPS


@pytest.mark.parametrize("session", [False, True], ids=["one-shot", "daemon"])
def test_steps_file_preserves_every_operation(routed_agent, tmp_path, session):
    agent, _ui = routed_agent
    path = tmp_path / "steps.json"
    path.write_text(json.dumps(STEPS, ensure_ascii=False), encoding="utf-8")
    args = ["run", "--steps-file", str(path)]
    args += ["--session", "stub-session.json"] if session else ["--device-sn", "stub-device"]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)["results"]
    assert [row["step_result"]["kind"] for row in rows] == list(PAYLOADS)
    assert all(row["step_result"]["outcome"]["status"] == "passed" for row in rows)
    assert agent.received == STEPS


def test_plan_preserves_every_operation_and_verifies_report(routed_agent, tmp_path):
    agent, _ui = routed_agent
    plan = tmp_path / "test-plan.md"
    rows = [
        "## 测试用例清单",
        "| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, payload in enumerate(STEPS):
        text = json.dumps(payload, ensure_ascii=False).replace("|", "\\|")
        rows.append(f"| TC-{index} | operation | stub | `{text}` | | P2 | AC-1 |")
    plan.write_text("\n".join(rows), encoding="utf-8")
    report, trace = tmp_path / "report.md", tmp_path / "trace.json"
    result = CliRunner().invoke(app, ["run", "--plan", str(plan), "--feature", "common-entrypoint-parity", "--report-out", str(report), "--trace-out", str(trace), "--device-sn", "stub-device", "--skip-assert-expected"])
    assert result.exit_code == 0, result.output
    assert agent.received == STEPS
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert all(case["steps"][0]["outcome"]["status"] == "passed" for case in data["cases"])
    verified = CliRunner().invoke(app, ["report", "verify", "--report", str(report), "--trace", str(trace), "--plan", str(plan)])
    assert verified.exit_code == 0, verified.output


@pytest.mark.parametrize("mode,status", [("passed", "passed"), ("device-failure", "failed"), ("transport-failure", "failed"), ("timeout", "failed"), ("blocked", "blocked")])
@pytest.mark.parametrize("session", [False, True], ids=["one-shot", "daemon"])
def test_atomic_cli_shell_outcomes_are_honest(routed_agent, mode, status, session):
    agent, ui = routed_agent
    ui.shell_mode = mode
    payload = {"shell": {"command": SHELL_TEXT}}
    result = invoke_atomic("shell", payload, session=session)
    assert result.exit_code == (0 if status == "passed" else 1), result.output
    step = json.loads(result.stdout)["step_result"]
    assert step["outcome"]["status"] == status
    assert agent.received == [payload]
    assert ("shell", {"command": SHELL_TEXT, "timeout": 60}) in ui.events
    if mode == "timeout":
        assert step["outcome"]["observation"]["facts"]["remote_status_unknown"] is True


@pytest.mark.parametrize("session", [False, True], ids=["one-shot", "mcp-session"])
async def test_atomic_mcp_shell_failure_block_and_timeout(routed_agent, session):
    from fastmcp import Client
    from hylyre.mcp.server import build_mcp

    _agent, ui = routed_agent
    async with Client(build_mcp()) as client:
        args = {"device_sn": "stub-device"}
        if session:
            opened = await client.call_tool("hylyre_open_session", args)
            args = {"session_id": json.loads(opened.content[0].text)["session_id"]}
        for mode, status in [("device-failure", "failed"), ("transport-failure", "failed"), ("blocked", "blocked"), ("timeout", "failed")]:
            ui.shell_mode = mode
            response = await client.call_tool("hylyre_run_shell", {"payload": {"shell": {"command": SHELL_TEXT}}, **args})
            step = json.loads(response.content[0].text)["step_result"]
            assert step["outcome"]["status"] == status, (mode, step)
            if mode == "timeout":
                assert step["outcome"]["observation"]["facts"]["remote_status_unknown"] is True
        if session:
            await client.call_tool("hylyre_close_session", args)


def test_matrix_matches_the_entire_design_operation_list():
    assert set(PAYLOADS) == {*COMMON_OPERATION_KEYS, "touch", "wait_for", "wait_gone"}


def test_all_atomic_help_examples_pass_the_shared_json_contract():
    from typer.main import get_command
    from hylyre.scenario.plan_contract import validate_planned_step

    commands = get_command(app).commands["run"].commands
    for root in PAYLOADS:
        command = commands[cli_command(root)]
        payload_option = next(p for p in command.params if "--json" in p.opts)
        help_text = payload_option.help
        example = help_text[help_text.index("{"):help_text.rindex("}") + 1]
        assert validate_planned_step(json.loads(example), path=root) is None
        options = {opt for param in command.params for opt in param.opts}
        assert {"--json", "--device-sn", "--session"} <= options


@pytest.mark.parametrize("session", [False, True], ids=["one-shot", "daemon"])
def test_invalid_atomic_json_is_rejected_before_ui_calls(routed_agent, session):
    agent, ui = routed_agent
    payload = {"slide": {"start": POINT_A, "end": POINT_B, "speed": 500}}
    result = invoke_atomic("slide", payload, session=session)
    assert result.exit_code == 1
    step = json.loads(result.stdout)["step_result"]
    assert step["outcome"]["status"] == "failed"
    assert step["outcome"]["failure"]["domain"] == "contract"
    assert agent.received == []
    assert ui.events == []


def test_fake_cli_batch_never_constructs_a_live_operation(routed_agent, tmp_path):
    agent, ui = routed_agent
    steps = tmp_path / "offline.json"
    steps.write_text(json.dumps(STEPS, ensure_ascii=False), encoding="utf-8")
    result = CliRunner().invoke(app, ["run", "--steps-file", str(steps), "--use-fakes", "--on-fail", "skip"])
    batch = json.loads(result.stdout)
    assert batch["executed"] == len(STEPS)
    query_kinds = {"shell", "get_component_property", "current_app", "has_app", "set_checked", "wait_for", "wait_gone"}
    for row in batch["results"]:
        step = row["step_result"]
        assert step["device_session"] is False
        if step["kind"] in query_kinds:
            assert step["outcome"]["status"] == "blocked"
    assert agent.received == []
    assert ui.events == []
