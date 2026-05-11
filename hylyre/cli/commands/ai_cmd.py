"""Structured AI-like tap/input on a real device (P1: no VLM; P3 adds semantics)."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from hylyre.drivers.hypium import HypiumDriver

console = Console()


def run_ai_tap(
    *,
    device_sn: str | None,
    x: int | None,
    y: int | None,
    by_text: str | None,
    by_id: str | None,
    wait_time: float,
) -> None:
    async def _run() -> None:
        driver = HypiumDriver(device_sn=device_sn)
        try:
            await driver.connect()
            await driver.touch(
                x=x,
                y=y,
                by_text=by_text,
                by_id=by_id,
                wait_time=wait_time,
            )
        finally:
            await driver.close()

    try:
        asyncio.run(_run())
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except Exception as e:  # pragma: no cover - device/runtime failures
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1) from e


def run_ai_input(
    *,
    device_sn: str | None,
    value: str,
    by_text: str | None,
    by_id: str | None,
) -> None:
    async def _run() -> None:
        driver = HypiumDriver(device_sn=device_sn)
        try:
            await driver.connect()
            await driver.input_text(
                value, by_text=by_text, by_id=by_id
            )
        finally:
            await driver.close()

    try:
        asyncio.run(_run())
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    except Exception as e:  # pragma: no cover
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1) from e
