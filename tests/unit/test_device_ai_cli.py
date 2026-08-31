"""CLI tests for device + ai commands (mocked)."""

from __future__ import annotations

from pathlib import Path
import json
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from hylyre.cli.__main__ import app
from hylyre.drivers.hypium import hdc_cli

runner = CliRunner()


@patch("hylyre.cli.commands.device.hdc_cli.list_targets", return_value=["DEV1"])
def test_device_list_ok(_m: MagicMock) -> None:
    r = runner.invoke(app, ["device", "list"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "DEV1" in r.stdout


@patch("hylyre.cli.commands.device.hdc_cli.list_targets", return_value=["FIRST", "SECOND"])
def test_device_list_first_only(_m: MagicMock) -> None:
    r = runner.invoke(app, ["device", "list", "--first"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "FIRST"


@patch("hylyre.cli.commands.device.hdc_cli.list_targets", return_value=[])
def test_device_list_first_only_no_device(_m: MagicMock) -> None:
    r = runner.invoke(app, ["device", "list", "--first"])
    assert r.exit_code == 1


@patch(
    "hylyre.cli.commands.device.hdc_cli.list_targets",
    side_effect=hdc_cli.HdcNotFoundError("nohdc"),
)
def test_device_list_missing_hdc(_m: MagicMock) -> None:
    r = runner.invoke(app, ["device", "list"])
    assert r.exit_code == 2


@patch("hylyre.cli.commands.device.hdc_cli.install_hap")
def test_device_install_ok(mock_install: MagicMock, tmp_path: Path) -> None:
    hap = tmp_path / "a.hap"
    hap.write_bytes(b"x")
    r = runner.invoke(
        app,
        ["device", "install", str(hap), "--serial", "SN"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    mock_install.assert_called_once()


@patch("hylyre.wiring.create_hypium_agent_with_env_vlm")
def test_ai_tap_reaches_the_driver_and_returns_an_envelope(
    mock_create: MagicMock,
) -> None:
    """`ai tap` is a protocol step now, not a bare driver poke."""

    from hylyre.api.agent import HylyreAgent
    from hylyre.contracts import RESULT_PROTOCOL, validate_against
    from tests.contract.fakes.fake_ui_driver import FakeUiDriver

    ui = FakeUiDriver()
    mock_create.return_value = HylyreAgent(ui=ui)
    r = runner.invoke(app, ["ai", "tap", "--x", "1", "--y", "2"])
    assert r.exit_code == 0, r.stdout

    assert any(event[0] == "touch" for event in ui.events)
    payload = json.loads(r.stdout)
    assert payload["result_protocol"] == RESULT_PROTOCOL
    assert payload["step_result"]["outcome"]["status"] == "passed"
    assert validate_against("/$defs/stepResultV1", payload["step_result"]) == []


@patch("hylyre.wiring.create_hypium_agent_with_env_vlm")
def test_ai_input_reaches_the_driver_and_returns_an_envelope(
    mock_create: MagicMock,
) -> None:
    from hylyre.api.agent import HylyreAgent
    from hylyre.contracts import RESULT_PROTOCOL
    from tests.contract.fakes.fake_ui_driver import FakeUiDriver

    tree = {
        "attributes": {"type": "Root", "bounds": "[0,0][500,800]"},
        "children": [
            {
                "attributes": {
                    "type": "TextInput",
                    "id": "user_field",
                    "text": "user",
                    "bounds": "[0,0][200,40]",
                },
                "children": [],
            }
        ],
    }
    ui = FakeUiDriver(dump_tree=tree)
    mock_create.return_value = HylyreAgent(ui=ui)
    r = runner.invoke(app, ["ai", "input", "hello", "--by-text", "user"])
    assert r.exit_code == 0, r.stdout

    assert any(event[0] == "input_text" for event in ui.events)
    payload = json.loads(r.stdout)
    assert payload["result_protocol"] == RESULT_PROTOCOL
    assert payload["step_result"]["outcome"]["status"] == "passed"


@patch("hylyre.wiring.create_hypium_agent_with_env_vlm")
def test_ai_action_failure_is_not_reported_as_success(
    mock_create: MagicMock,
) -> None:
    """The public AI action entry must not turn a failure into "ok"."""

    from hylyre.api.agent import HylyreAgent
    from tests.contract.fakes.fake_ui_driver import FakeUiDriver
    from tests.contract.fakes.fake_vlm_client import FakeVlmClient

    ui = FakeUiDriver(dump_tree={"attributes": {"type": "Root", "bounds": "[0,0][9,9]"}, "children": []})
    vlm = FakeVlmClient(responses=[{"action": {"type": "touch", "by_text": "nope"}}])
    mock_create.return_value = HylyreAgent(ui=ui, vlm=vlm)

    r = runner.invoke(app, ["ai", "action", "tap the missing thing"])
    assert r.exit_code == 1, r.stdout
    payload = json.loads(r.stdout)
    assert payload["step_result"]["outcome"]["status"] == "failed"


@patch("hylyre.wiring.create_hypium_agent_with_env_vlm")
def test_ai_action_cli_uses_agent(mock_create: MagicMock) -> None:
    from tests.contract.fakes.fake_ui_driver import FakeUiDriver
    from tests.contract.fakes.fake_vlm_client import FakeVlmClient

    ui = FakeUiDriver()
    vlm = FakeVlmClient(
        responses=[{"action": {"type": "touch", "x": 5, "y": 6}}],
    )
    from hylyre.api.agent import HylyreAgent

    ag = HylyreAgent(ui=ui, vlm=vlm)
    mock_create.return_value = ag
    r = runner.invoke(app, ["ai", "action", "tap"])
    assert r.exit_code == 0, r.stdout + r.stderr


@patch("hylyre.wiring.create_hypium_agent_with_env_vlm")
def test_ai_query_cli_prints(mock_create: MagicMock) -> None:
    from tests.contract.fakes.fake_ui_driver import FakeUiDriver
    from tests.contract.fakes.fake_vlm_client import FakeVlmClient

    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"answer": "yes", "dtype": "string"}])
    from hylyre.api.agent import HylyreAgent

    ag = HylyreAgent(ui=ui, vlm=vlm)
    mock_create.return_value = ag
    r = runner.invoke(app, ["ai", "query", "visible?", "--schema", "string"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "yes" in r.stdout


@patch("hylyre.wiring.create_hypium_agent_with_env_vlm")
def test_ai_assert_cli_ok(mock_create: MagicMock) -> None:
    from tests.contract.fakes.fake_ui_driver import FakeUiDriver
    from tests.contract.fakes.fake_vlm_client import FakeVlmClient

    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"ok": True, "reason": ""}])
    from hylyre.api.agent import HylyreAgent

    ag = HylyreAgent(ui=ui, vlm=vlm)
    mock_create.return_value = ag
    r = runner.invoke(app, ["ai", "assert", "home visible"])
    assert r.exit_code == 0, r.stdout + r.stderr
