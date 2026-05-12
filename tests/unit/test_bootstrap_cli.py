"""CLI smoke for bootstrap subgroup (no pip by default)."""

from __future__ import annotations

from typer.testing import CliRunner

from hylyre.cli.__main__ import app

runner = CliRunner()


def test_bootstrap_mock_without_install() -> None:
    r = runner.invoke(app, ["bootstrap", "mock"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "Tip:" in r.stdout or "doctor" in r.stdout
