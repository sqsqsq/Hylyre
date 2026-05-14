"""FastMCP stdio server — curated atomic tools mapped to Hylyre CLI logic (P5)."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class _McpSession:
    agent: Any  # HylyreAgent
    trace_state: dict[str, Any] | None = None


def _mcp_log(message: str) -> None:
    """Best-effort diagnostics; never write to stdout (stdio transport)."""
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"{ts} pid={os.getpid()} {message}\n"
    try:
        log_path = Path.cwd() / ".hylyre" / "mcp-server.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    try:
        sys.stderr.write(line)
        sys.stderr.flush()
    except Exception:
        pass


def _call_logged(tool_name: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
    start = time.perf_counter()
    _mcp_log(f"tool_start name={tool_name}")
    try:
        result = fn(*args, **kwargs)
    except Exception:
        elapsed = time.perf_counter() - start
        _mcp_log(
            f"tool_error name={tool_name} elapsed_s={elapsed:.3f}\n"
            f"{traceback.format_exc()}"
        )
        raise
    elapsed = time.perf_counter() - start
    _mcp_log(f"tool_end name={tool_name} elapsed_s={elapsed:.3f}")
    return result


def build_mcp():  # type: ignore[no-untyped-def]
    """Construct FastMCP app with registered tools (lazy-imports fastmcp)."""
    _mcp_log("build_mcp start")
    from fastmcp import FastMCP

    from hylyre.cli.commands import ai_cmd, device, doctor, loop_cmd, mock_cmd, run_cmd
    from hylyre.progress import store as progress_store
    from hylyre.wiring import create_hypium_agent

    sessions: dict[str, _McpSession] = {}

    mcp = FastMCP(
        name="hylyre",
        instructions=(
            "Hylyre: HarmonyOS UI + Lyrebird mock testing. "
            "Safer CI path: hylyre_run_plan use_fakes=true. "
            "Agent-loop (no VLM): dump_ui / screenshot / run_* JSON "
            "(action tap input swipe scroll) + report_* . "
            "hylyre_open_session reuses Hypium for faster MCP loops; optional for parity with CLI."
        ),
    )

    def _session_agent(session_id: str) -> Any:
        sess = sessions.get(session_id)
        if sess is None:
            raise ValueError(f"unknown session_id {session_id!r}")
        return sess.agent

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
        description=(
            "Validate test-report.md + trace.json (L5 harness). "
            "plan_path optional for ad-hoc traces."
        ),
    )
    def hylyre_report_verify(
        report_path: str,
        trace_path: str,
        plan_path: str | None = None,
    ) -> str:
        plan_arg = Path(plan_path) if plan_path else None
        run_cmd.execute_report_verify(
            report=Path(report_path),
            trace=Path(trace_path),
            plan=plan_arg,
        )
        return "Contracts OK"

    @mcp.tool(
        name="hylyre_open_session",
        description=(
            "MCP-only: keep Hypium agent connection open (mock optional). "
            "Pass session_id to screenshot/dump/run/report tools."
        ),
    )
    async def hylyre_open_session(
        device_sn: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
    ) -> str:
        _mcp_log(f"open_session enter device_sn={device_sn}")
        t0 = time.perf_counter()
        agent = create_hypium_agent(
            device_sn=device_sn,
            vlm=None,
            mock_port=mock_port,
            lyrebird_base_url=lyrebird_url,
        )
        _mcp_log(f"open_session agent_created {time.perf_counter()-t0:.2f}s")
        await agent.ensure_connected()
        _mcp_log(f"open_session connected {time.perf_counter()-t0:.2f}s")
        sid = str(uuid.uuid4())
        sessions[sid] = _McpSession(agent=agent, trace_state=None)
        _mcp_log(f"open_session done sid={sid} {time.perf_counter()-t0:.2f}s")
        return json.dumps({"session_id": sid})

    @mcp.tool(
        name="hylyre_close_session",
        description="Close MCP session opened by hylyre_open_session.",
    )
    async def hylyre_close_session(session_id: str) -> str:
        sess = sessions.pop(session_id, None)
        if sess is None:
            raise ValueError(f"unknown session_id {session_id!r}")
        await sess.agent.aclose()
        return "ok"

    @mcp.tool(
        name="hylyre_screenshot",
        description=(
            "Device screenshot bytes as base64 ({mime, base64}). "
            "session_id uses persistent agent; else one-shot via device_sn."
        ),
    )
    async def hylyre_screenshot(
        device_sn: str | None = None,
        session_id: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            raw = await agent.ui.screenshot()
        else:
            import anyio

            _mime, raw = await anyio.to_thread.run_sync(
                lambda: loop_cmd.execute_screenshot_bytes(device_sn=device_sn)
            )
        mime = "image/jpeg" if raw.startswith(b"\xff\xd8\xff") else "image/png"
        payload = {
            "mime": mime,
            "base64": base64.standard_b64encode(raw).decode("ascii"),
        }
        return json.dumps(payload)

    @mcp.tool(
        name="hylyre_dump_ui",
        description=(
            "Hypium UiTree JSON for non-multimodal planners; "
            "session_id or device_sn."
        ),
    )
    async def hylyre_dump_ui(
        device_sn: str | None = None,
        session_id: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            tree = await agent.dump_ui()
        else:
            import anyio

            tree = await anyio.to_thread.run_sync(
                lambda: loop_cmd.execute_dump_ui_dict(device_sn=device_sn)
            )
        return json.dumps(tree, ensure_ascii=False)

    @mcp.tool(
        name="hylyre_start_app",
        description="Hypium start_app (atomic); optional MCP session_id.",
    )
    async def hylyre_start_app(
        bundle: str,
        device_sn: str | None = None,
        session_id: str | None = None,
        page_name: str | None = None,
        params: str = "",
        wait_time: float = 1.0,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            await agent.start_app(
                bundle,
                page_name=page_name,
                params=params,
                wait_time=wait_time,
            )
            return "ok"
        import anyio

        await anyio.to_thread.run_sync(
            lambda: loop_cmd.execute_start_app(
                bundle=bundle,
                device_sn=device_sn,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
                page_name=page_name,
                params=params,
                wait_time=wait_time,
            )
        )
        return "ok"

    @mcp.tool(
        name="hylyre_run_action",
        description='One planned JSON step root key "action" (no VLM).',
    )
    async def hylyre_run_action(
        payload: dict[str, Any],
        device_sn: str | None = None,
        session_id: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            await agent.run_planned_action(payload)
            return "ok"
        import anyio

        await anyio.to_thread.run_sync(
            lambda: loop_cmd.execute_run_action(
                payload=payload,
                device_sn=device_sn,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
            )
        )
        return "ok"

    @mcp.tool(
        name="hylyre_run_tap",
        description='One planned tap JSON root key "touch" (no VLM).',
    )
    async def hylyre_run_tap(
        payload: dict[str, Any],
        device_sn: str | None = None,
        session_id: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            await agent.run_planned_tap(payload)
            return "ok"
        import anyio

        await anyio.to_thread.run_sync(
            lambda: loop_cmd.execute_run_tap(
                payload=payload,
                device_sn=device_sn,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
            )
        )
        return "ok"

    @mcp.tool(
        name="hylyre_run_input",
        description='One planned input JSON root key "input" (no VLM).',
    )
    async def hylyre_run_input(
        payload: dict[str, Any],
        device_sn: str | None = None,
        session_id: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            await agent.run_planned_input(payload)
            return "ok"
        import anyio

        await anyio.to_thread.run_sync(
            lambda: loop_cmd.execute_run_input(
                payload=payload,
                device_sn=device_sn,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
            )
        )
        return "ok"

    @mcp.tool(
        name="hylyre_run_swipe",
        description=(
            "Hypium swipe JSON root swipe (UP/DOWN/LEFT/RIGHT); "
            "half-modal lists need area.by_type Scroll."
        ),
    )
    async def hylyre_run_swipe(
        payload: dict[str, Any],
        device_sn: str | None = None,
        session_id: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            await agent.run_planned_swipe(payload)
            return "ok"
        import anyio

        await anyio.to_thread.run_sync(
            lambda: loop_cmd.execute_run_swipe(
                payload=payload,
                device_sn=device_sn,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
            )
        )
        return "ok"

    @mcp.tool(
        name="hylyre_run_scroll",
        description=(
            "Hypium mouse_scroll JSON scroll (up/down, steps); "
            "modal lists prefer at.by_type Scroll."
        ),
    )
    async def hylyre_run_scroll(
        payload: dict[str, Any],
        device_sn: str | None = None,
        session_id: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
    ) -> str:
        if session_id:
            agent = _session_agent(session_id)
            await agent.run_planned_scroll(payload)
            return "ok"
        import anyio

        await anyio.to_thread.run_sync(
            lambda: loop_cmd.execute_run_scroll(
                payload=payload,
                device_sn=device_sn,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
            )
        )
        return "ok"

    @mcp.tool(
        name="hylyre_report_begin",
        description=(
            "Start incremental trace dict (draft schema). "
            "Optional session_id stores state on MCP session."
        ),
    )
    def hylyre_report_begin(
        feature: str,
        plan_path: str | None = None,
        model_backend: str = "none",
        session_id: str | None = None,
    ) -> str:
        pp = Path(plan_path) if plan_path else None
        state = run_cmd.execute_report_begin(
            feature=feature,
            trace_path=None,
            plan_path=pp,
            trace_state=None,
            model_backend=model_backend,
        )
        if session_id:
            sess = sessions.get(session_id)
            if sess is None:
                raise ValueError(f"unknown session_id {session_id!r}")
            sess.trace_state = state
        return json.dumps(state, ensure_ascii=False)

    @mcp.tool(
        name="hylyre_report_record",
        description="Append one case to trace_state dict (pass JSON or use session_id).",
    )
    def hylyre_report_record(
        case_id: str,
        name: str,
        priority: str,
        ac_ref: str,
        status: str,
        notes: str = "",
        trace_state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> str:
        effective: dict[str, Any] | None = trace_state
        if session_id:
            sess = sessions.get(session_id)
            if sess is None:
                raise ValueError(f"unknown session_id {session_id!r}")
            effective = sess.trace_state if trace_state is None else trace_state
        if effective is None:
            raise ValueError("Provide trace_state dict or session_id with prior begin")
        updated = run_cmd.execute_report_record(
            trace_path=None,
            trace_state=effective,
            case_id=case_id,
            name=name,
            priority=priority,
            ac_ref=ac_ref,
            status=status,
            notes=notes,
        )
        if session_id:
            sessions[session_id].trace_state = updated
        return json.dumps(updated, ensure_ascii=False)

    @mcp.tool(
        name="hylyre_report_finalize",
        description="Write report.md + final trace.json + L5 verify from trace_state.",
    )
    def hylyre_report_finalize(
        report_out: str,
        trace_out: str,
        trace_state: dict[str, Any] | None = None,
        session_id: str | None = None,
        plan_path: str | None = None,
        model_backend: str | None = None,
    ) -> str:
        effective = trace_state
        if session_id:
            sess = sessions.get(session_id)
            if sess is None:
                raise ValueError(f"unknown session_id {session_id!r}")
            effective = sess.trace_state if trace_state is None else trace_state
        if effective is None:
            raise ValueError("Provide trace_state or session_id with recorded cases")
        pp = Path(plan_path) if plan_path else None
        msg = run_cmd.execute_report_finalize(
            trace_path=None,
            trace_state=effective,
            plan_path=pp,
            report_out=Path(report_out),
            trace_out=Path(trace_out),
            model_backend=model_backend,
        )
        return msg

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

    @mcp.tool(
        name="hylyre_collect_list",
        description=(
            "Swipe UP in scroll area and merge Text rows until stable "
            "(virtualized sheets). session_id, session_path, or device_sn."
        ),
    )
    async def hylyre_collect_list(
        session_id: str | None = None,
        session_path: str | None = None,
        device_sn: str | None = None,
        mock_port: int | None = None,
        lyrebird_url: str | None = None,
        scroll_by_type: str | None = None,
        scroll_by_text: str | None = None,
        scroll_by_id: str | None = None,
        scroll_by_key: str | None = None,
        item_pattern: str | None = None,
        max_scrolls: int = 10,
        swipe_distance: int = 60,
        max_stable_rounds: int = 2,
    ) -> str:
        from hylyre.cli.commands import collect_cmd

        modes = sum(bool(x) for x in (session_id, session_path, device_sn))
        if modes > 1:
            raise ValueError(
                "pass at most one of session_id, session_path, device_sn "
                "(omit device_sn when using MCP session_id)"
            )

        payload = {
            "scroll_by_type": scroll_by_type,
            "scroll_by_text": scroll_by_text,
            "scroll_by_id": scroll_by_id,
            "scroll_by_key": scroll_by_key,
            "item_pattern": item_pattern,
            "max_scrolls": max_scrolls,
            "swipe_distance": swipe_distance,
            "max_stable_rounds": max_stable_rounds,
        }

        if session_id:
            agent = _session_agent(session_id)
            result = await collect_cmd.collect_list_on_agent(agent, payload)
            return json.dumps(result, ensure_ascii=False)

        import anyio

        sess = Path(session_path) if session_path else None
        result = await anyio.to_thread.run_sync(
            lambda: collect_cmd.execute_collect_list(
                params=payload,
                device_sn=device_sn,
                mock_port=mock_port,
                lyrebird_url=lyrebird_url,
                session_file=sess,
            )
        )
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool(
        name="hylyre_progress_show",
        description="Tail of docs/progress.md from repo root (cwd). Default last 120 lines.",
    )
    def hylyre_progress_show(tail_lines: int = 120) -> str:
        return progress_store.format_progress_excerpt(tail_lines=tail_lines)

    _mcp_log("build_mcp end")
    return mcp


def serve_stdio(*, show_banner: bool = False) -> None:
    """Run MCP over stdio (Cursor / Claude Desktop).

    Important: stdio transport reserves ``sys.stdout`` for JSON-RPC protocol
    framing. Anything written there breaks the client. We must:

    1. Pre-import Hypium so its xdevice ``StreamHandler(sys.stdout)`` binds to
       a safe sink. Lazy import inside an MCP tool is *unsafe* — once stdio
       transport rebinds stdout, ``StreamHandler.addHandler`` can deadlock
       against MCP's anyio reader.
    2. Temporarily redirect ``sys.stdout`` -> ``sys.stderr`` during the import
       so any handlers Hypium captures already point at stderr.
    3. After the eager import, scrub any handler that still points at the
       original real stdout.
    """
    _mcp_log(f"serve_stdio start show_banner={show_banner}")

    import logging

    real_stdout = sys.stdout
    real_stdout_buffer = getattr(real_stdout, "buffer", None)
    sys.stdout = sys.stderr
    try:
        _mcp_log("eager_hypium_import start (stdout->stderr)")
        from hylyre.drivers.hypium.driver import load_hypium_shim

        load_hypium_shim()
        _mcp_log("eager_hypium_import done")
    except ImportError as e:
        _mcp_log(f"eager_hypium_import skipped (not installed): {e}")
    except Exception as e:  # pragma: no cover - defensive
        _mcp_log(f"eager_hypium_import failed: {e}")
    finally:
        sys.stdout = real_stdout

    # Belt-and-braces: rewrite any logging StreamHandler still bound to the real
    # stdout (or its buffer) over to stderr, so future Hypium logs never touch
    # the JSON-RPC channel.
    def _rebind_handler(h: logging.Handler) -> None:
        try:
            stream = getattr(h, "stream", None)
            if stream is real_stdout or (
                real_stdout_buffer is not None
                and getattr(stream, "buffer", None) is real_stdout_buffer
            ):
                h.stream = sys.stderr  # type: ignore[attr-defined]
                _mcp_log(f"rebound_handler {h!r} -> stderr")
        except Exception:
            pass

    try:
        for h in list(logging.getLogger().handlers):
            _rebind_handler(h)
        for name in list(logging.Logger.manager.loggerDict):
            lg = logging.getLogger(name)
            for h in list(getattr(lg, "handlers", []) or []):
                _rebind_handler(h)
    except Exception as e:  # pragma: no cover
        _mcp_log(f"rebind_handlers_failed: {e}")

    mcp = build_mcp()
    try:
        mcp.run(transport="stdio", show_banner=show_banner)
    finally:
        _mcp_log("serve_stdio stop")
