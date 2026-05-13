"""L1: hylyre run entry smoke (no real device)."""

from __future__ import annotations

from pathlib import Path

from hylyre.cli.commands import run_cmd

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "e2e" / "fixtures" / "mock-test-plan.md"


def test_run_scenario_use_fakes_writes_artifacts(tmp_path: Path) -> None:
    report = tmp_path / "r.md"
    trace = tmp_path / "t.json"
    run_cmd.run_scenario(
        plan=FIXTURE,
        feature="cli-entry",
        report_out=report,
        trace_out=trace,
        use_fakes=True,
    )
    assert report.is_file()
    assert trace.is_file()
    assert "测试概览" in report.read_text(encoding="utf-8")


def test_run_scenario_use_fakes_model_backend_override(tmp_path: Path) -> None:
    import json

    report = tmp_path / "r.md"
    trace = tmp_path / "t.json"
    run_cmd.run_scenario(
        plan=FIXTURE,
        feature="cli-entry",
        report_out=report,
        trace_out=trace,
        use_fakes=True,
        model_backend="my-vendor-model",
    )
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data.get("model_backend") == "my-vendor-model"


def test_incremental_report_finalize_without_plan(tmp_path: Path) -> None:
    draft = tmp_path / "draft.json"
    report = tmp_path / "out-report.md"
    final_trace = tmp_path / "out-trace.json"
    run_cmd.execute_report_begin(
        feature="adhoc-feature",
        trace_path=draft,
        plan_path=None,
        model_backend="none",
    )
    run_cmd.execute_report_record(
        trace_path=draft,
        case_id="TC-AH-01",
        name="Smoke",
        priority="P0",
        ac_ref="AC-AH-01",
        status="通过",
        notes="incremental",
    )
    msg = run_cmd.execute_report_finalize(
        trace_path=draft,
        plan_path=None,
        report_out=report,
        trace_out=final_trace,
    )
    assert "Wrote" in msg
    assert report.is_file() and final_trace.is_file()
    run_cmd.execute_report_verify(report=report, trace=final_trace, plan=None)
