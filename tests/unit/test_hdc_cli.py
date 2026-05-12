"""L1: hdc CLI parsing / invocation (mocked subprocess)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hylyre.drivers.hypium import hdc_cli


@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_list_targets_missing_hdc(mock_which: MagicMock) -> None:
    mock_which.return_value = None
    with pytest.raises(hdc_cli.HdcNotFoundError):
        hdc_cli.list_targets()


@patch("hylyre.drivers.hypium.hdc_cli.subprocess.run")
@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_list_targets_ok(mock_which: MagicMock, mock_run: MagicMock) -> None:
    mock_which.return_value = "/bin/hdc"
    mock_run.return_value = MagicMock(returncode=0, stdout="SN12345\n")
    rows = hdc_cli.list_targets()
    assert rows == ["SN12345"]


@patch("hylyre.drivers.hypium.hdc_cli.subprocess.run")
@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_install_hap_invokes_hdc(
    mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
) -> None:
    mock_which.return_value = "/bin/hdc"
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    hap = tmp_path / "x.hap"
    hap.write_bytes(b"x")
    hdc_cli.install_hap(hap, serial="SN")
    assert mock_run.call_count == 1
    cmd = mock_run.call_args[0][0]
    assert cmd[:4] == ["/bin/hdc", "-t", "SN", "install"]


@patch("hylyre.drivers.hypium.hdc_cli.subprocess.run")
@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_list_targets_nonzero_exit(
    mock_which: MagicMock, mock_run: MagicMock
) -> None:
    mock_which.return_value = "/bin/hdc"
    mock_run.return_value = MagicMock(returncode=3, stdout="", stderr="boom")
    with pytest.raises(hdc_cli.HdcError) as ei:
        hdc_cli.list_targets()
    assert ei.value.exit_code == 3
    assert "boom" in str(ei.value)


@patch("hylyre.drivers.hypium.hdc_cli.subprocess.run")
@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_list_targets_skips_connected_banner_line(
    mock_which: MagicMock, mock_run: MagicMock
) -> None:
    mock_which.return_value = "/bin/hdc"
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="127.0.0.1:5555\n[HINT] Connected to one device\n",
    )
    assert hdc_cli.list_targets() == ["127.0.0.1:5555"]


@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_install_hap_missing_hdc(mock_which: MagicMock, tmp_path: Path) -> None:
    mock_which.return_value = None
    hap = tmp_path / "x.hap"
    hap.write_bytes(b"x")
    with pytest.raises(hdc_cli.HdcNotFoundError):
        hdc_cli.install_hap(hap)


def test_install_hap_not_a_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        hdc_cli.install_hap(tmp_path / "nope.hap")


@patch("hylyre.drivers.hypium.hdc_cli.subprocess.run")
@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_install_hap_nonzero_exit(
    mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
) -> None:
    mock_which.return_value = "/bin/hdc"
    mock_run.return_value = MagicMock(returncode=7, stdout="fail", stderr="")
    hap = tmp_path / "x.hap"
    hap.write_bytes(b"x")
    with pytest.raises(hdc_cli.HdcError) as ei:
        hdc_cli.install_hap(hap)
    assert ei.value.exit_code == 7


@patch("hylyre.drivers.hypium.hdc_cli.subprocess.run")
@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_file_send_invokes_hdc(
    mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
) -> None:
    mock_which.return_value = "/bin/hdc"
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    src = tmp_path / "c.pem"
    src.write_bytes(b"x")
    hdc_cli.file_send(src, "/data/local/tmp/c.pem", serial="ZZ")
    cmd = mock_run.call_args[0][0]
    assert cmd[:4] == ["/bin/hdc", "-t", "ZZ", "file"]
    assert cmd[4] == "send"
    assert cmd[6] == "/data/local/tmp/c.pem"


@patch("hylyre.drivers.hypium.hdc_cli.shutil.which")
def test_file_send_missing_hdc(mock_which: MagicMock, tmp_path: Path) -> None:
    mock_which.return_value = None
    p = tmp_path / "c.pem"
    p.write_bytes(b"x")
    with pytest.raises(hdc_cli.HdcNotFoundError):
        hdc_cli.file_send(p, "/data/local/tmp/c.pem")
