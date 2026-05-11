"""Device commands: hdc list / install (P1)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from hylyre.drivers.hypium import hdc_cli

console = Console()


def run_device_list() -> None:
    try:
        targets = hdc_cli.list_targets()
    except hdc_cli.HdcNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except hdc_cli.HdcError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=e.exit_code or 1) from e
    table = Table(title="hdc targets")
    table.add_column("#", style="dim")
    table.add_column("serial", style="cyan")
    if not targets:
        console.print(table)
        console.print("[yellow]No devices reported by hdc.[/yellow]")
        return
    for i, t in enumerate(targets, start=1):
        table.add_row(str(i), t)
    console.print(table)


def run_device_install(hap: Path, serial: str | None) -> None:
    try:
        hdc_cli.install_hap(hap, serial=serial)
    except hdc_cli.HdcNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except hdc_cli.HdcError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=e.exit_code or 1) from e
    suffix = f" (-t {serial})" if serial else ""
    console.print(f"[green]Installed[/green] {hap}{suffix}")
