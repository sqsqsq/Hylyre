"""L1: MITM CA resolution and hdc push helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hylyre.drivers.hypium import hdc_cli
from hylyre.drivers.lyrebird import cert_bootstrap


def test_resolve_mitm_ca_explicit(tmp_path: Path) -> None:
    pem = tmp_path / "ca.pem"
    pem.write_text("x", encoding="utf-8")
    assert cert_bootstrap.resolve_mitm_ca_cert(pem) == pem.resolve()


def test_resolve_mitm_ca_missing_explicit(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        cert_bootstrap.resolve_mitm_ca_cert(tmp_path / "nope.pem")


def test_push_mitm_ca_calls_file_send(tmp_path: Path) -> None:
    pem = tmp_path / "ca.pem"
    pem.write_text("pem", encoding="utf-8")
    with patch.object(hdc_cli, "file_send") as fs:
        local, remote = cert_bootstrap.push_mitm_ca_to_device(
            ca_cert=pem,
            serial="SN",
            remote_path="/data/local/tmp/x.pem",
        )
    fs.assert_called_once()
    assert local == pem.resolve()
    assert remote == "/data/local/tmp/x.pem"


def test_build_file_send_argv_serial(tmp_path: Path) -> None:
    f = tmp_path / "a.pem"
    f.write_bytes(b"x")
    argv = hdc_cli.build_file_send_argv(
        hdc_bin="/bin/hdc",
        local=f,
        remote="/data/local/tmp/y.pem",
        serial="ABC",
    )
    assert argv[:4] == ["/bin/hdc", "-t", "ABC", "file"]
    assert argv[4] == "send"
    assert argv[5] == str(f.resolve())
    assert argv[6] == "/data/local/tmp/y.pem"


def test_mitm_trust_contains_push_ca() -> None:
    t = cert_bootstrap.mitm_trust_instructions()
    assert "push-ca" in t
