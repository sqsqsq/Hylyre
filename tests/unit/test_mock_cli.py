"""CLI tests for mock subgroup (mocked controller / subprocess)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from hylyre.cli.__main__ import app

runner = CliRunner()


def test_mock_cert_cli() -> None:
    r = runner.invoke(app, ["mock", "cert", "--serial", "SERIAL"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "HarmonyOS" in r.stdout


@patch("hylyre.cli.commands.mock_cmd.LyrebirdController")
def test_mock_activate_calls_controller(mock_cls: MagicMock) -> None:
    inst = MagicMock()
    inst.activate_group = AsyncMock()
    inst.aclose = AsyncMock()
    mock_cls.return_value = inst
    r = runner.invoke(
        app,
        ["mock", "activate", "abc-uuid", "--url", "http://127.0.0.1:1"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    inst.activate_group.assert_awaited_once_with("abc-uuid")


@patch(
    "hylyre.cli.commands.mock_cmd.require_lyrebird_distribution",
    side_effect=ImportError("missing lyrebird"),
)
@patch("hylyre.cli.commands.mock_cmd.asyncio.run")
def test_mock_start_missing_dist(mock_run: MagicMock, _req: MagicMock) -> None:
    r = runner.invoke(app, ["mock", "start", "--mock-port", "9099"])
    assert r.exit_code == 2
    mock_run.assert_not_called()


@patch("hylyre.cli.commands.mock_cmd.LyrebirdController")
def test_mock_deactivate_calls_controller(mock_cls: MagicMock) -> None:
    inst = MagicMock()
    inst.deactivate_all = AsyncMock()
    inst.aclose = AsyncMock()
    mock_cls.return_value = inst
    r = runner.invoke(app, ["mock", "deactivate"])
    assert r.exit_code == 0, r.stdout + r.stderr
    inst.deactivate_all.assert_awaited_once()


@patch("hylyre.cli.commands.mock_cmd.LyrebirdController")
def test_mock_capture_calls_export(mock_cls: MagicMock, tmp_path) -> None:
    inst = MagicMock()
    inst.export_flows = AsyncMock()
    inst.aclose = AsyncMock()
    mock_cls.return_value = inst
    out = tmp_path / "flows.json"
    r = runner.invoke(app, ["mock", "capture", "--output", str(out)])
    assert r.exit_code == 0, r.stdout + r.stderr
    inst.export_flows.assert_awaited()


def test_mock_stop_missing_pid(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["mock", "stop"])
    assert r.exit_code == 1


@patch("hylyre.cli.commands.mock_cmd.pidfile.terminate_pid")
@patch("hylyre.cli.commands.mock_cmd.pidfile.is_pid_alive", return_value=True)
def test_mock_stop_kills_when_alive(
    _alive: MagicMock, term: MagicMock, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    from hylyre.drivers.lyrebird import pidfile as pf

    pf.write_pid(pf.default_pid_path(), 424242)
    r = runner.invoke(app, ["mock", "stop"])
    assert r.exit_code == 0, r.stdout + r.stderr
    term.assert_called_once_with(424242)


@patch("hylyre.cli.commands.mock_cmd.pidfile.is_pid_alive", return_value=False)
def test_mock_stop_dead_pid_clears(_alive: MagicMock, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    from hylyre.drivers.lyrebird import pidfile as pf

    p = pf.default_pid_path()
    pf.write_pid(p, 999001)
    r = runner.invoke(app, ["mock", "stop"])
    assert r.exit_code == 0
    assert not p.is_file()
