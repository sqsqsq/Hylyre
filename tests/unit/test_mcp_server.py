"""P5 FastMCP server: tool surface and parity with shared CLI helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastmcp")

from fastmcp import Client  # noqa: E402

from hylyre.mcp.server import build_mcp  # noqa: E402


@pytest.mark.asyncio
async def test_mcp_tool_inventory() -> None:
    mcp = build_mcp()
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) == 31
    expected = {
        "hylyre_run_plan",
        "hylyre_report_verify",
        "hylyre_open_session",
        "hylyre_close_session",
        "hylyre_screenshot",
        "hylyre_dump_ui",
        "hylyre_start_app",
        "hylyre_run_action",
        "hylyre_run_tap",
        "hylyre_run_input",
        "hylyre_run_swipe",
        "hylyre_run_scroll",
        "hylyre_collect_list",
        "hylyre_find",
        "hylyre_app_page_save",
        "hylyre_app_page_load",
        "hylyre_app_page_list",
        "hylyre_app_page_diff",
        "hylyre_app_page_delete",
        "hylyre_app_find",
        "hylyre_app_fingerprint",
        "hylyre_report_begin",
        "hylyre_report_record",
        "hylyre_report_finalize",
        "hylyre_device_list",
        "hylyre_doctor",
        "hylyre_ai_action",
        "hylyre_ai_query",
        "hylyre_ai_assert",
        "hylyre_mock_activate",
        "hylyre_progress_show",
    }
    assert names == expected
    desc_lens = [len((t.description or "")) for t in tools]
    assert max(desc_lens) < 2000
    from hylyre.mcp.description_budget import description_within_budget

    for t in tools:
        d = t.description or ""
        assert description_within_budget(
            d, max_tokens=500
        ), f"tool {t.name!r} description over ~500-token heuristic: {d!r}"


@pytest.mark.asyncio
async def test_mcp_doctor_tool_returns_text() -> None:
    mcp = build_mcp()
    async with Client(mcp) as client:
        result = await client.call_tool("hylyre_doctor", {})
    text = result.content[0].text
    assert "Hylyre doctor" in text
    assert "Python:" in text


@pytest.mark.asyncio
async def test_mcp_run_plan_matches_cli_fake_pipeline(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    plan = root / "tests" / "e2e" / "fixtures" / "mock-test-plan.md"
    report = tmp_path / "test-report.md"
    trace = tmp_path / "trace.json"
    mcp = build_mcp()
    async with Client(mcp) as client:
        out = await client.call_tool(
            "hylyre_run_plan",
            {
                "plan_path": str(plan),
                "feature": "mcp-fake",
                "report_out": str(report),
                "trace_out": str(trace),
                "use_fakes": True,
            },
        )
        msg = out.content[0].text
        assert "Wrote" in msg
        assert report.is_file() and trace.is_file()
        v = await client.call_tool(
            "hylyre_report_verify",
            {
                "report_path": str(report),
                "trace_path": str(trace),
                "plan_path": str(plan),
            },
        )
        assert "Contracts OK" in v.content[0].text


@pytest.mark.asyncio
async def test_mcp_progress_show_returns_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "hylyre"\n', encoding="utf-8"
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "progress.md").write_text("# hi\nline2\n", encoding="utf-8")
    mcp = build_mcp()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "hylyre_progress_show",
            {"tail_lines": 10},
        )
    text = result.content[0].text
    assert "progress.md" in text
    assert "line2" in text


@pytest.mark.asyncio
async def test_mcp_incremental_report_without_plan(tmp_path: Path) -> None:
    import json

    report = tmp_path / "rep.md"
    trace = tmp_path / "trace.json"
    mcp = build_mcp()
    async with Client(mcp) as client:
        b = await client.call_tool(
            "hylyre_report_begin",
            {"feature": "mcp-loop", "model_backend": "none"},
        )
        state = json.loads(b.content[0].text)
        r = await client.call_tool(
            "hylyre_report_record",
            {
                "trace_state": state,
                "case_id": "TC-MCP-01",
                "name": "Inc",
                "priority": "P0",
                "ac_ref": "AC-MCP-01",
                "status": "通过",
                "notes": "",
            },
        )
        state2 = json.loads(r.content[0].text)
        msg = await client.call_tool(
            "hylyre_report_finalize",
            {
                "trace_state": state2,
                "report_out": str(report),
                "trace_out": str(trace),
            },
        )
        assert "Wrote" in msg.content[0].text
        v = await client.call_tool(
            "hylyre_report_verify",
            {"report_path": str(report), "trace_path": str(trace)},
        )
        assert "Contracts OK" in v.content[0].text
