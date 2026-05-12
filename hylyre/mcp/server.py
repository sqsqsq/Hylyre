"""FastMCP stdio server — curated atomic tools mapped to Hylyre CLI logic (P5)."""

from __future__ import annotations

from pathlib import Path


def build_mcp():  # type: ignore[no-untyped-def]
    """Construct FastMCP app with registered tools (lazy-imports fastmcp)."""
    from fastmcp import FastMCP

    from hylyre.cli.commands import ai_cmd, device, doctor, mock_cmd, run_cmd

    mcp = FastMCP(
        name="hylyre",
        instructions=(
            "Hylyre: HarmonyOS UI + Lyrebird mock testing. "
            "Safer CI path: hylyre_run_plan with use_fakes=true. "
            "NL AI tools need HYLYRE_VLM_* and hylyre[device]."
        ),
    )

    @mcp.tool(
        name="hylyre_run_plan",
        description=(
            "Execute test-plan.md → test-report.md + trace.json; runs L5 verify. "
            "Set use_fakes=true for stubbed runs without a device."
        ),
    )
    def hylyre_run_plan(
        plan_path: str,
        feature: str,
        report_out: str,
        trace_out: str,
        use_fakes: bool = False,
        device_sn: str | None = None,
        bundle: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
        mock_group: str | None = None,
        skip_assert_expected: bool = False,
        model_backend: str | None = None,
    ) -> str:
        return run_cmd.execute_scenario(
            plan=Path(plan_path),
            feature=feature,
            report_out=Path(report_out),
            trace_out=Path(trace_out),
            use_fakes=use_fakes,
            device_sn=device_sn,
            bundle=bundle,
            mock_port=mock_port,
            lyrebird_url=lyrebird_url,
            mock_group=mock_group,
            skip_assert_expected=skip_assert_expected,
            model_backend=model_backend,
        )

    @mcp.tool(
        name="hylyre_report_verify",
        description="Validate test-report.md + trace.json vs plan (L5 harness).",
    )
    def hylyre_report_verify(
        report_path: str,
        trace_path: str,
        plan_path: str,
    ) -> str:
        run_cmd.execute_report_verify(
            report=Path(report_path),
            trace=Path(trace_path),
            plan=Path(plan_path),
        )
        return "Contracts OK"

    @mcp.tool(
        name="hylyre_device_list",
        description="List hdc device serials (requires hdc on PATH).",
    )
    def hylyre_device_list() -> str:
        return device.format_device_list_text()

    @mcp.tool(
        name="hylyre_doctor",
        description="Environment readiness: Python, node, npm, hdc, mitmproxy, lyrebird.",
    )
    def hylyre_doctor() -> str:
        rows = doctor.gather_doctor_checks()
        return doctor.format_doctor_plain(rows)

    @mcp.tool(
        name="hylyre_ai_action",
        description="One VLM-planned UI action (needs HYLYRE_VLM_* + hylyre[device]).",
    )
    def hylyre_ai_action(instruction: str, device_sn: str | None = None) -> str:
        return ai_cmd.execute_ai_action(device_sn=device_sn, instruction=instruction)

    @mcp.tool(
        name="hylyre_ai_query",
        description=(
            "VLM visual query; schema is string|number|boolean. "
            "Returns answer text."
        ),
    )
    def hylyre_ai_query(
        instruction: str,
        device_sn: str | None = None,
        schema: str = "string",
    ) -> str:
        return ai_cmd.execute_ai_query(
            device_sn=device_sn, instruction=instruction, schema=schema
        )

    @mcp.tool(
        name="hylyre_ai_assert",
        description="VLM assertion on current screen; raises if condition fails.",
    )
    def hylyre_ai_assert(instruction: str, device_sn: str | None = None) -> str:
        return ai_cmd.execute_ai_assert(device_sn=device_sn, instruction=instruction)

    @mcp.tool(
        name="hylyre_mock_activate",
        description="Activate Lyrebird mock group UUID against admin API base URL.",
    )
    def hylyre_mock_activate(
        group_id: str,
        lyrebird_url: str | None = None,
    ) -> str:
        return mock_cmd.execute_mock_activate(group_id, lyrebird_url)

    return mcp


def serve_stdio(*, show_banner: bool = False) -> None:
    """Run MCP over stdio (Cursor / Claude Desktop)."""
    mcp = build_mcp()
    mcp.run(transport="stdio", show_banner=show_banner)
