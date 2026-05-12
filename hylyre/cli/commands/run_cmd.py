"""hylyre run — scenario runner entry."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer

from hylyre.harness.runner import verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.runner import ScenarioRunResult


def run_scenario(
    *,
    plan: Path,
    feature: str,
    report_out: Path,
    trace_out: Path,
    use_fakes: bool,
    device_sn: str | None = None,
    bundle: str | None = None,
    mock_port: int | None = None,
    lyrebird_url: str | None = None,
    mock_group: str | None = None,
    skip_assert_expected: bool = False,
) -> None:
    if use_fakes:
        runner = ScenarioRunner(use_fakes=True)
        result = runner.run_plan_file(plan, feature=feature)
        write_run_artifacts(result, report_path=report_out, trace_path=trace_out)
        model_backend = "fake"
    else:
        result, model_backend = asyncio.run(
            _run_on_device(
                plan=plan,
                feature=feature,
                device_sn=device_sn,
                bundle=bundle,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
                mock_group=mock_group,
                skip_assert_expected=skip_assert_expected,
            )
        )
        write_run_artifacts(
            result,
            report_path=report_out,
            trace_path=trace_out,
            model_backend=model_backend,
        )
    try:
        verify_report(report_out, trace_out, plan)
    except ValueError as exc:
        typer.secho(f"verify_report failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Wrote {report_out} and {trace_out}")


async def _run_on_device(
    *,
    plan: Path,
    feature: str,
    device_sn: str | None,
    bundle: str | None,
    mock_port: int | None,
    lyrebird_url: str | None,
    mock_group: str | None,
    skip_assert_expected: bool,
) -> tuple[ScenarioRunResult, str]:
    from hylyre.wiring import create_hypium_agent_with_env_vlm

    agent = create_hypium_agent_with_env_vlm(
        device_sn=device_sn,
        mock_port=mock_port,
        lyrebird_base_url=lyrebird_url,
    )
    model_backend = (
        os.environ.get("HYLYRE_VLM_MODEL", "").strip()
        or (
            "http-vlm"
            if os.environ.get("HYLYRE_VLM_ENDPOINT", "").strip()
            else "none"
        )
    )
    try:
        runner = ScenarioRunner(use_fakes=False)
        result = await runner.run_plan_on_agent(
            agent,
            plan,
            feature=feature,
            bundle=bundle or None,
            mock_group=mock_group or None,
            check_expected=not skip_assert_expected,
        )
        return result, model_backend
    finally:
        await agent.aclose()


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
