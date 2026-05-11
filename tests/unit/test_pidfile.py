"""PID file helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hylyre.drivers.lyrebird import pidfile


def test_write_read_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "p" / "lyrebird.pid"
    pidfile.write_pid(p, 4242)
    assert pidfile.read_pid(p) == 4242


def test_clear_missing_ok(tmp_path: Path) -> None:
    pidfile.clear_pidfile(tmp_path / "none.pid")


def test_read_pid_bad_content(tmp_path: Path) -> None:
    p = tmp_path / "bad.pid"
    p.write_text("not-int", encoding="utf-8")
    assert pidfile.read_pid(p) is None


@patch("hylyre.drivers.lyrebird.pidfile.subprocess.run")
@patch("hylyre.drivers.lyrebird.pidfile.sys.platform", "win32")
def test_terminate_pid_windows(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(returncode=0)
    pidfile.terminate_pid(44)
    mock_run.assert_called_once()
    assert "taskkill" in mock_run.call_args[0][0]
