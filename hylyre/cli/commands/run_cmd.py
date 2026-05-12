"""hylyre run — scenario runner entry."""

from __future__ import annotations

from pathlib import Path

import typer

from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.runner import ScenarioRunner


def run_scenario(
    *,
    plan: Path,
    feature: str,
    report_out: Path,
    trace_out: Path,
    use_fakes: bool,
) -> None:
    runner = ScenarioRunner(use_fakes=use_fakes)
    result = runner.run_plan_file(plan, feature=feature)
    write_run_artifacts(result, report_path=report_out, trace_path=trace_out)
    try:
        verify_report(report_out, trace_out, plan)
    except ValueError as exc:
        typer.secho(f"verify_report failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Wrote {report_out} and {trace_out}")


def run_report_verify(
    *,
    report: Path,
    trace: Path,
    plan: Path,
) -> None:
    try:
        verify_report(report, trace, plan)
    except ValueError as exc:
        typer.secho(f"verify_report failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Contracts OK")
