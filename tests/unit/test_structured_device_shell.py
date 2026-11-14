"""Structured HDC shell transport; never connects to a device."""

from __future__ import annotations

import base64
import shlex
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from hylyre.drivers.hypium import hdc_cli


NONCE = "0123456789abcdef"
MARKER = f"__HYLYRE_RC_{NONCE}".encode()


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    monkeypatch.setattr(hdc_cli, "hdc_exe", lambda: "fake-hdc")
    monkeypatch.setattr(hdc_cli.uuid, "uuid4", lambda: SimpleNamespace(hex=NONCE))
    proc = MagicMock(returncode=0)
    proc.__enter__.return_value = proc
    proc.communicate.return_value = (b"\n" + MARKER + b"=0\n", b"")
    popen = MagicMock(return_value=proc)
    monkeypatch.setattr(hdc_cli.subprocess, "Popen", popen)
    return popen, proc


def result_for(proc: MagicMock, output: bytes, *, code: int = 0) -> dict:
    proc.communicate.return_value = (output + b"\n" + MARKER + f"={code}\n".encode(), b"")
    return hdc_cli.structured_shell("printf output", serial="SN")


@pytest.mark.parametrize(
    "output",
    [b"", b"no newline", b"\n", b"  leading and trailing  \n\n", b"\r\ntext\r\n", "中文；\"引号\"\n".encode()],
)
def test_preserves_original_output_exactly(
    transport: tuple[MagicMock, MagicMock], output: bytes
) -> None:
    _popen, proc = transport
    facts = result_for(proc, output)
    assert facts["stdout"] == output.decode()
    assert facts["exit_code"] == 0
    assert facts["transport_exit_code"] == 0
    assert facts["stderr"] is None
    assert facts["stderr_available"] is False
    assert facts["transport_error"] is None
    assert facts["remote_status_unknown"] is False
    assert facts["raw_evidence"]["stdout"] == (output + b"\n" + MARKER + b"=0\n").decode()


def test_host_argv_binds_device_and_preserves_shell_text(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    popen, _proc = transport
    command = "printf '%s' \"中文;$(echo value)\" | cat\nprintf 'it\\\"s'; exit 7"
    serial = "local-device;literal"
    hdc_cli.structured_shell(command, serial=serial, timeout=2.5)
    argv = popen.call_args.args[0]
    assert argv[:4] == ["fake-hdc", "-t", serial, "shell"]
    assert len(argv) == 5
    # Only the remote shell interprets the command; shlex reverses its quoting.
    nested = shlex.split(argv[4].rsplit("; printf", 1)[0])
    assert nested == ["sh", "-c", command]
    assert f"__HYLYRE_RC_{NONCE}=%s" in argv[4]
    assert popen.call_args.kwargs == {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    _proc.communicate.assert_called_once_with(timeout=2.5)


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
@pytest.mark.parametrize("output", [b"", b"no newline", b"ends CR\r", b"ends CRLF\r\n", b"  padded\n\n"])
def test_transport_line_endings_strip_only_the_added_wrapper(
    transport: tuple[MagicMock, MagicMock], newline: bytes, output: bytes
) -> None:
    _popen, proc = transport
    raw = output + newline + MARKER + b"=7" + newline
    proc.communicate.return_value = (raw, b"")
    facts = hdc_cli.structured_shell("exit 7", serial="SN")
    assert facts["stdout"] == output.decode()
    assert facts["exit_code"] == 7
    assert facts["raw_evidence"]["stdout"] == raw.decode()


def test_device_failure_is_distinct_from_transport_success(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    _popen, proc = transport
    facts = result_for(proc, b"stdout\nmerged device stderr", code=7)
    assert facts["exit_code"] == 7
    assert facts["transport_exit_code"] == 0
    assert facts["transport_error"] is None
    assert facts["stdout"] == "stdout\nmerged device stderr"


def test_only_final_unique_marker_is_removed(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    _popen, proc = transport
    output = b"\n__HYLYRE_RC_other=2\n" + MARKER + b"=17\n"
    assert result_for(proc, output)["stdout"] == output.decode()


def test_each_invocation_uses_its_own_marker(
    transport: tuple[MagicMock, MagicMock], monkeypatch: pytest.MonkeyPatch
) -> None:
    popen, _proc = transport
    nonces = iter(("first", "second"))
    monkeypatch.setattr(
        hdc_cli.uuid, "uuid4", lambda: SimpleNamespace(hex=next(nonces))
    )
    hdc_cli.structured_shell("true", serial="SN")
    hdc_cli.structured_shell("true", serial="SN")
    first, second = [entry.args[0][-1] for entry in popen.call_args_list]
    assert "__HYLYRE_RC_first=" in first
    assert "__HYLYRE_RC_second=" in second


@pytest.mark.parametrize(
    "tail",
    [b"", b"\n__HYLYRE_RC_other=0\n", b"\n" + MARKER + b"=bad\n", b"\n" + MARKER + b"=256\n", b"\n" + MARKER + b"=0", b"\n" + MARKER + b"=0\nmore"],
)
def test_missing_or_malformed_marker_never_implies_success(
    transport: tuple[MagicMock, MagicMock], tail: bytes
) -> None:
    _popen, proc = transport
    raw = b"actual output" + tail
    proc.communicate.return_value = (raw, b"")
    facts = hdc_cli.structured_shell("exit 0", serial="SN")
    assert facts["exit_code"] is None
    assert facts["marker_found"] is False
    assert facts["transport_error"] == "hdc shell device exit marker is missing or malformed"
    assert facts["stdout"] == raw.decode()
    assert facts["remote_status_unknown"] is True


def test_transport_failure_takes_priority_and_retains_device_code(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    _popen, proc = transport
    proc.returncode = 3
    proc.communicate.return_value = (b"failed\n" + MARKER + b"=7\n", b"HDC connection error")
    facts = hdc_cli.structured_shell("exit 7", serial="SN")
    assert facts["transport_error"] == "HDC connection error"
    assert facts["transport_exit_code"] == 3
    assert facts["exit_code"] == 7
    assert facts["stderr"] is None
    assert facts["raw_evidence"]["stderr"] == "HDC connection error"


def test_timeout_kills_and_reaps_host_without_retry(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    popen, proc = transport
    proc.returncode = -9
    proc.communicate.side_effect = [
        subprocess.TimeoutExpired("fake-hdc", 1, output=b"partial"),
        (b"partial output", b"host diagnostics"),
    ]
    facts = hdc_cli.structured_shell("sleep 60", serial="SN", timeout=1)
    popen.assert_called_once()
    proc.kill.assert_called_once_with()
    assert proc.communicate.call_args_list == [call(timeout=1), call()]
    assert facts["timed_out"] is True
    assert facts["remote_status_unknown"] is True
    assert facts["exit_code"] is None
    assert facts["transport_exit_code"] == -9
    assert facts["stdout"] == "partial output"
    assert facts["raw_evidence"]["stderr"] == "host diagnostics"


def test_timeout_reaps_a_real_local_child(monkeypatch: pytest.MonkeyPatch) -> None:
    real_popen = subprocess.Popen
    children = []

    def local_child(_argv: list[str], **kwargs):
        child = real_popen(
            [sys.executable, "-c", "import time; time.sleep(30)"], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(hdc_cli, "hdc_exe", lambda: "unused-fake-hdc")
    monkeypatch.setattr(hdc_cli.subprocess, "Popen", local_child)
    facts = hdc_cli.structured_shell("unused", serial="unused-device", timeout=0.1)
    assert len(children) == 1
    assert children[0].poll() is not None
    assert facts["timed_out"] is True
    assert facts["remote_status_unknown"] is True


def test_failed_start_returns_transport_facts(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    popen, _proc = transport
    popen.side_effect = OSError("could not start")
    facts = hdc_cli.structured_shell("true", serial="SN")
    assert "could not start" in facts["transport_error"]
    assert facts["exit_code"] is None
    assert facts["transport_exit_code"] is None
    assert facts["remote_status_unknown"] is False


def test_communication_failure_also_reaps_host(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    _popen, proc = transport
    proc.communicate.side_effect = [OSError("pipe failed"), (b"", b"")]
    facts = hdc_cli.structured_shell("true", serial="SN")
    proc.kill.assert_called_once_with()
    assert proc.communicate.call_count == 2
    assert "pipe failed" in facts["transport_error"]
    assert facts["remote_status_unknown"] is True


def test_non_utf8_raw_evidence_is_lossless(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    _popen, proc = transport
    facts = result_for(proc, b"\xff\xfe")
    assert base64.b64decode(facts["raw_evidence"]["stdout_base64"]) == b"\xff\xfe\n" + MARKER + b"=0\n"


def test_large_output_is_complete_for_callers_artifact_path(
    transport: tuple[MagicMock, MagicMock],
) -> None:
    _popen, proc = transport
    output = b"large output\n" * 100_000
    facts = result_for(proc, output)
    assert facts["stdout"] == output.decode()
    assert facts["raw_evidence"]["stdout"] == (output + b"\n" + MARKER + b"=0\n").decode()


@pytest.mark.parametrize("serial", [None, "", " ", "SN\x00"])
def test_missing_binding_never_launches_hdc(
    transport: tuple[MagicMock, MagicMock], serial: str | None
) -> None:
    popen, _proc = transport
    with pytest.raises(ValueError, match="bound device serial"):
        hdc_cli.structured_shell("true", serial=serial)
    popen.assert_not_called()


@pytest.mark.parametrize("command", ["", " \n", "echo\x00x", None])
def test_invalid_command_never_launches_hdc(
    transport: tuple[MagicMock, MagicMock], command: str
) -> None:
    popen, _proc = transport
    with pytest.raises(ValueError, match="command"):
        hdc_cli.structured_shell(command, serial="SN")
    popen.assert_not_called()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, "2"])
def test_invalid_timeout_never_launches_hdc(
    transport: tuple[MagicMock, MagicMock], timeout: float
) -> None:
    popen, _proc = transport
    with pytest.raises(ValueError, match="timeout"):
        hdc_cli.structured_shell("true", serial="SN", timeout=timeout)
    popen.assert_not_called()


def test_missing_hdc_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hdc_cli, "hdc_exe", lambda: None)
    with pytest.raises(hdc_cli.HdcNotFoundError):
        hdc_cli.structured_shell("true", serial="SN")


def test_legacy_shell_still_strips_and_force_stop_keeps_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hdc_cli, "hdc_exe", lambda: "fake-hdc")
    run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="  original\n", stderr=""))
    monkeypatch.setattr(hdc_cli.subprocess, "run", run)
    assert hdc_cli.force_stop("com.example.app", serial="SN") == "original"
    assert run.call_args.args[0] == ["fake-hdc", "-t", "SN", "shell", "aa", "force-stop", "com.example.app"]
