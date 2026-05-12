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
    assert len(names) == 8
    expected = {
        "hylyre_run_plan",
        "hylyre_report_verify",
        "hylyre_device_list",
        "hylyre_doctor",
        "hylyre_ai_action",
        "hylyre_ai_query",
        "hylyre_ai_assert",
        "hylyre_mock_activate",
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
