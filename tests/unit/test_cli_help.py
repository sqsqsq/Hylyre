"""L1: CLI --help smoke tests."""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

ROOT_HELP = [["--help"]]
SUBCOMMANDS = [
    ["run", "--help"],
    ["run", "action", "--help"],
    ["run", "tap", "--help"],
    ["run", "input", "--help"],
    ["run", "swipe", "--help"],
    ["run", "scroll", "--help"],
    ["run", "start-app", "--help"],
    ["screenshot", "--help"],
    ["dump-ui", "--help"],
    ["mock", "--help"],
    ["mock", "start", "--help"],
    ["mock", "stop", "--help"],
    ["mock", "status", "--help"],
    ["mock", "activate", "--help"],
    ["mock", "deactivate", "--help"],
    ["mock", "capture", "--help"],
    ["mock", "cert", "--help"],
    ["mock", "push-ca", "--help"],
    ["bootstrap", "--help"],
    ["bootstrap", "mock", "--help"],
    ["device", "--help"],
    ["device", "list", "--help"],
    ["device", "install", "--help"],
    ["progress", "show", "--help"],
    ["progress", "append", "--help"],
    ["progress", "path", "--help"],
    ["spec", "list", "--help"],
    ["report", "--help"],
    ["report", "verify", "--help"],
    ["report", "begin", "--help"],
    ["report", "record", "--help"],
    ["report", "finalize", "--help"],
    ["progress", "--help"],
    ["spec", "--help"],
    ["doctor", "--help"],
    ["mcp", "--help"],
    ["mcp", "serve", "--help"],
    ["ai", "--help"],
    ["ai", "tap", "--help"],
    ["ai", "input", "--help"],
    ["ai", "action", "--help"],
    ["ai", "query", "--help"],
    ["ai", "assert", "--help"],
]


def _hylyre_exe() -> list[str]:
    exe = shutil.which("hylyre")
    if exe:
        return [exe]
    return [sys.executable, "-m", "hylyre"]


def _run_cli(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


@pytest.mark.parametrize("args", ROOT_HELP + SUBCOMMANDS)
def test_cli_help_exits_zero(args: list[str]) -> None:
    cmd = _hylyre_exe() + args
    proc = _run_cli(cmd)
    so = proc.stdout or ""
    se = proc.stderr or ""
    assert proc.returncode == 0, se + so


def test_main_help_lists_expected_groups() -> None:
    cmd = _hylyre_exe() + ["--help"]
    proc = _run_cli(cmd)
    assert proc.returncode == 0
    out = proc.stdout or ""
    for name in (
        "run",
        "mock",
        "device",
        "report",
        "progress",
        "spec",
        "doctor",
        "bootstrap",
        "mcp",
        "ai",
        "screenshot",
        "dump-ui",
    ):
        assert name in out, f"missing top-level command {name!r} in:\n{out}"
