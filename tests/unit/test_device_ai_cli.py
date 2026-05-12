"""CLI tests for device + ai commands (mocked)."""

from __future__ import annotations

from pathlib import Path
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


@patch("hylyre.cli.commands.ai_cmd.HypiumDriver")
def test_ai_tap_coordinate_mocked(mock_cls: MagicMock) -> None:
    inst = MagicMock()
    inst.connect = AsyncMock()
    inst.touch = AsyncMock()
    inst.close = AsyncMock()
    mock_cls.return_value = inst
    r = runner.invoke(app, ["ai", "tap", "--x", "1", "--y", "2"])
    assert r.exit_code == 0, r.stdout + r.stderr
    inst.touch.assert_awaited()


@patch("hylyre.cli.commands.ai_cmd.HypiumDriver")
def test_ai_input_mocked(mock_cls: MagicMock) -> None:
    inst = MagicMock()
    inst.connect = AsyncMock()
    inst.input_text = AsyncMock()
    inst.close = AsyncMock()
    mock_cls.return_value = inst
    r = runner.invoke(
        app,
        ["ai", "input", "hello", "--by-text", "user"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    inst.input_text.assert_awaited()


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
