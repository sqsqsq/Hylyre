"""L1: CLI --help smoke tests."""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

ROOT_HELP = [["--help"]]
SUBCOMMANDS = [
    ["run", "--help"],
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


@pytest.mark.parametrize("args", ROOT_HELP + SUBCOMMANDS)
def test_cli_help_exits_zero(args: list[str]) -> None:
    cmd = _hylyre_exe() + args
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_main_help_lists_expected_groups() -> None:
    cmd = _hylyre_exe() + ["--help"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    assert proc.returncode == 0
    out = proc.stdout
    for name in ("run", "mock", "device", "report", "progress", "spec", "doctor", "bootstrap", "mcp", "ai"):
        assert name in out, f"missing top-level command {name!r} in:\n{out}"
