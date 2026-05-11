"""Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from hylyre.cli.commands import (
    ai_cmd,
    device as device_cmd,
    doctor as doctor_cmd,
    mock_cmd,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Hylyre — Hypium + Lyrebird unified device testing (HarmonyOS).",
    pretty_exceptions_enable=False,
)
report_app = typer.Typer(help="Test report tools")
app.add_typer(report_app, name="report")

device_app = typer.Typer(help="Device helpers (HDC + Hypium)")
app.add_typer(device_app, name="device")

ai_app = typer.Typer(help="Structured UI actions (P1); natural language in P3")
app.add_typer(ai_app, name="ai")

mock_app = typer.Typer(help="Lyrebird mock control (P2)")
app.add_typer(mock_app, name="mock")


def _p0_placeholder() -> None:
    typer.echo("not implemented in P0")


@app.command()
def run() -> None:
    """Execute a test plan end-to-end (P4)."""
    _p0_placeholder()


@device_app.command("list")
def device_list() -> None:
    """List HarmonyOS device targets via hdc."""
    device_cmd.run_device_list()


@device_app.command("install")
def device_install(
    hap: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    serial: Optional[str] = typer.Option(
        None,
        "--serial",
        "-t",
        help="Device serial (hdc -t); default first/only device.",
    ),
) -> None:
    """Install a .hap onto the device via hdc."""
    device_cmd.run_device_install(hap, serial)


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


@ai_app.callback()
def ai_callback() -> None:
    """P1: coordinate / selector based tap and text input (requires hypium extra)."""


@mock_app.callback()
def mock_callback() -> None:
    """Mock / Lyrebird: start daemon, activate groups, export flows."""


@mock_app.command("start")
def mock_start(
    mock_port: int = typer.Option(
        9090,
        "--mock-port",
        "-p",
        help="Port passed to `lyrebird --mock` (admin API base).",
    ),
    data: Optional[Path] = typer.Option(
        None,
        "--data",
        "-d",
        help="Mock data root for `lyrebird --data` (directory).",
    ),
    pid_file: Optional[Path] = typer.Option(
        None,
        "--pid-file",
        help="Where to store Lyrebird PID (default: ./.hylyre/lyrebird.pid).",
    ),
) -> None:
    """Start Lyrebird in the background (requires hylyre[mock])."""
    mock_cmd.run_mock_start(
        mock_port=mock_port,
        data=data,
        pid_path=pid_file,
    )


@mock_app.command("stop")
def mock_stop(
    pid_file: Optional[Path] = typer.Option(
        None,
        "--pid-file",
        help="PID file from `mock start` (default: ./.hylyre/lyrebird.pid).",
    ),
) -> None:
    """Stop Lyrebird using the PID file written by `mock start`."""
    mock_cmd.run_mock_stop(pid_path=pid_file)


@mock_app.command("status")
def mock_status(
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="Mock API base URL (default env HYLYRE_LYREBIRD_URL or http://127.0.0.1:9090).",
    ),
) -> None:
    """GET /api/status from a running Lyrebird."""
    mock_cmd.run_mock_status(base_url=url)


@mock_app.command("activate")
def mock_activate(
    group_id: str = typer.Argument(..., help="Mock group id (UUID)."),
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="Mock API base URL (or HYLYRE_LYREBIRD_URL).",
    ),
) -> None:
    """PUT /api/mock/{group}/activate."""
    mock_cmd.run_mock_activate(group_id, base_url=url)


@mock_app.command("deactivate")
def mock_deactivate(
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="Mock API base URL (or HYLYRE_LYREBIRD_URL).",
    ),
) -> None:
    """Deactivate all mock groups."""
    mock_cmd.run_mock_deactivate(base_url=url)


@mock_app.command("capture")
def mock_capture(
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Where to write JSON snapshot of /api/flow.",
    ),
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="Mock API base URL (or HYLYRE_LYREBIRD_URL).",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Fetch each /api/flow/{id} detail (slower).",
    ),
) -> None:
    """Export captured flows from Lyrebird to JSON (not strict HAR)."""
    mock_cmd.run_mock_capture(output=output, base_url=url, full=full)


@mock_app.command("cert")
def mock_cert(
    ca_cert: Optional[Path] = typer.Option(
        None,
        "--ca-cert",
        help="Optional path to mitmproxy CA for copy/paste instructions.",
    ),
    serial: Optional[str] = typer.Option(
        None,
        "--serial",
        "-t",
        help="Optional device serial for hdc -t hints.",
    ),
) -> None:
    """Print HarmonyOS MITM trust checklist (automation pending add-cert-bootstrap)."""
    mock_cmd.run_mock_cert_instructions(ca_cert=ca_cert, serial=serial)


@ai_app.command("tap")
def ai_tap(
    device_sn: Optional[str] = typer.Option(
        None,
        "--device-sn",
        help="Device serial; omit to use hdc default device.",
    ),
    x: Optional[int] = typer.Option(None, "--x", help="Tap X (requires --y)."),
    y: Optional[int] = typer.Option(None, "--y", help="Tap Y (requires --x)."),
    by_text: Optional[str] = typer.Option(None, help="Tap component matching text."),
    by_id: Optional[str] = typer.Option(None, help="Tap component matching id/key."),
    wait_time: float = typer.Option(0.1, help="Hypium touch wait_time."),
) -> None:
    """Tap using coordinates or a single selector (hypium extra)."""
    ai_cmd.run_ai_tap(
        device_sn=device_sn,
        x=x,
        y=y,
        by_text=by_text,
        by_id=by_id,
        wait_time=wait_time,
    )


@ai_app.command("input")
def ai_input(
    value: str = typer.Argument(..., help="Text to input."),
    device_sn: Optional[str] = typer.Option(
        None,
        "--device-sn",
        help="Device serial; omit to use hdc default device.",
    ),
    by_text: Optional[str] = typer.Option(None, help="Target component matching text."),
    by_id: Optional[str] = typer.Option(None, help="Target component matching id/key."),
) -> None:
    """Type text into focused field or into a matched component (hypium extra)."""
    ai_cmd.run_ai_input(
        device_sn=device_sn,
        value=value,
        by_text=by_text,
        by_id=by_id,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
