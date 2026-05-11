"""Typer CLI entrypoint."""

from __future__ import annotations

import typer

from hylyre.cli.commands import doctor as doctor_cmd

app = typer.Typer(
    no_args_is_help=True,
    help="Hylyre — Hypium + Lyrebird unified device testing (HarmonyOS).",
    pretty_exceptions_enable=False,
)
report_app = typer.Typer(help="Test report tools")
app.add_typer(report_app, name="report")


def _p0_placeholder() -> None:
    typer.echo("not implemented in P0")


@app.command()
def run() -> None:
    """Execute a test plan end-to-end (P4)."""
    _p0_placeholder()


@app.command()
def mock() -> None:
    """Lyrebird mock lifecycle (P2)."""
    _p0_placeholder()


@app.command()
def device() -> None:
    """Device / Hypium helpers (P1)."""
    _p0_placeholder()


@report_app.command("verify")
def report_verify() -> None:
    """Verify test-report.md + trace.json against Hylyre contracts (P4)."""
    _p0_placeholder()


@app.command()
def progress() -> None:
    """Show or append progress notes (P0+)."""
    _p0_placeholder()


@app.command()
def spec() -> None:
    """OpenSpec helpers (P0+)."""
    _p0_placeholder()


@app.command()
def doctor() -> None:
    """Check Python, Node, npm, hdc, mitmproxy readiness."""
    doctor_cmd.run_doctor()


mcp_app = typer.Typer(help="MCP server (P5)")
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("serve")
def mcp_serve() -> None:
    """Start MCP stdio server (P5)."""
    _p0_placeholder()


@app.command()
def ai() -> None:
    """Natural-language AI actions (P3)."""
    _p0_placeholder()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
