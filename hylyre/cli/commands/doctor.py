"""Environment diagnostics."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _python_check() -> CheckResult:
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 10
    detail = f"{v.major}.{v.minor}.{v.micro} ({sys.executable})"
    return CheckResult("Python", ok, detail)


def _cmd_version(exe: str, *version_args: str) -> tuple[bool, str]:
    path = shutil.which(exe)
    if not path:
        return False, f"{exe} not found on PATH"
    try:
        out = subprocess.run(
            [path, *version_args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        line = (out.stdout or out.stderr or "").strip().splitlines()[0:1]
        ver = line[0] if line else "(no output)"
        return True, f"{path} → {ver}"
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def run_doctor() -> None:
    """Print environment readiness for Hylyre development and execution."""
    rows: list[CheckResult] = [_python_check()]

    ok_node, node_detail = _cmd_version("node", "--version")
    rows.append(CheckResult("Node.js", ok_node, node_detail))

    ok_npm, npm_detail = _cmd_version("npm", "--version")
    rows.append(CheckResult("npm", ok_npm, npm_detail))

    hdc_ok, hdc_detail = _cmd_version("hdc", "version")
    rows.append(CheckResult("hdc (HarmonyOS)", hdc_ok, hdc_detail))

    mitm_ok = bool(shutil.which("mitmproxy") or shutil.which("mitmdump"))
    mitm_detail = (
        "mitmproxy / mitmdump on PATH"
        if mitm_ok
        else "Install mitmproxy: https://mitmproxy.org/ (required for Lyrebird proxy)"
    )
    rows.append(CheckResult("mitmproxy", mitm_ok, mitm_detail))

    table = Table(title="Hylyre doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Detail")

    all_ok = True
    for r in rows:
        all_ok = all_ok and r.ok
        status = "[green]OK[/green]" if r.ok else "[red]MISSING[/red]"
        table.add_row(r.name, status, r.detail)

    console.print(table)

    if not rows[0].ok:
        console.print(
            "\n[bold red]Python 3.10+ required.[/bold red] "
            "Install from https://www.python.org/downloads/ and ensure `python` is on PATH."
        )
    if not all_ok:
        console.print(
            "\n[yellow]Some optional tools are missing; Hypium/Lyrebird paths may fail until installed.[/yellow]"
        )
    else:
        console.print("\n[green]All checks passed.[/green]")
