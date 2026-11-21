"""Regression coverage for the Windows session daemon launch flags."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from hylyre.cli.__main__ import app
from hylyre.cli.commands import session_cmd


def test_session_start_uses_current_windows_python_without_console(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_file = tmp_path / "session.json"
    python_exe = str(tmp_path / "venv" / "Scripts" / "python.exe")

    def spawn_daemon(cmd: list[str], **kwargs: object) -> None:
        session_file.write_text('{"port": 12345}', encoding="utf-8")

    popen = Mock(side_effect=spawn_daemon)
    ping = Mock()
    win_subprocess = SimpleNamespace(
        Popen=popen,
        DEVNULL=-3,
        DETACHED_PROCESS=0x00000008,
        CREATE_NEW_PROCESS_GROUP=0x00000200,
        CREATE_NO_WINDOW=0x08000000,
    )
    monkeypatch.setattr(session_cmd, "sys", SimpleNamespace(platform="win32", executable=python_exe))
    monkeypatch.setattr(session_cmd, "subprocess", win_subprocess)
    monkeypatch.setattr(session_cmd, "session_ipc_call", ping)

    result = CliRunner().invoke(app, ["session", "start", "--session-file", str(session_file)])

    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == str(session_file.resolve())
    popen.assert_called_once()
    assert popen.call_args.args == ([python_exe, "-m", "hylyre", "session", "daemon"],)
    assert popen.call_args.kwargs["creationflags"] == (
        win_subprocess.CREATE_NEW_PROCESS_GROUP | win_subprocess.CREATE_NO_WINDOW
    )
    ping.assert_called_once_with(session_file, "ping", {}, timeout_s=10.0)
