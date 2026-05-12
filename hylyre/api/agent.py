"""Midscene-style ``HylyreAgent``: structured UI ops + optional VLM for natural language."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from hylyre.drivers.base import MockControllerBase, UiDriverBase, VlmClientBase


class HylyreAgent:
    """High-level facade: uses only ``UiDriverBase`` / ``MockControllerBase`` / ``VlmClientBase``."""

    def __init__(
        self,
        *,
        ui: UiDriverBase,
        mock: MockControllerBase | None = None,
        vlm: VlmClientBase | None = None,
    ) -> None:
        self._ui = ui
        self._mock = mock
        self._vlm = vlm
        self._ui_connected = False

    @property
    def ui(self) -> UiDriverBase:
        return self._ui

    @property
    def mock_controller(self) -> MockControllerBase | None:
        return self._mock

    @property
    def vlm(self) -> VlmClientBase | None:
        return self._vlm

    def _require_vlm(self) -> VlmClientBase:
        if self._vlm is None:
            raise ValueError(
                "Natural-language step requires a VLM client (pass vlm= to HylyreAgent, "
                "use structured ai_tap / ai_input with by_id/by_text/coordinates only, "
                "or run_planned_* with JSON from an external planner)."
            )
        return self._vlm

    async def _ensure_ui(self) -> None:
        if not self._ui_connected:
            await self._ui.connect()
            self._ui_connected = True

    async def aclose(self) -> None:
        if self._ui_connected:
            await self._ui.close()
            self._ui_connected = False

    async def start_app(
        self,
        bundle: str,
        *,
        page_name: str | None = None,
        params: str = "",
        wait_time: float = 1.0,
    ) -> None:
        await self._ensure_ui()
        await self._ui.start_app(
            bundle, page_name=page_name, params=params, wait_time=wait_time
        )

    async def mock_activate_group(self, group_id: str) -> None:
        if self._mock is None:
            raise ValueError("No mock controller configured on this HylyreAgent")
        await self._mock.activate_group(group_id)

    async def mock_deactivate_all(self) -> None:
        if self._mock is None:
            raise ValueError("No mock controller configured on this HylyreAgent")
        await self._mock.deactivate_all()

    @staticmethod
    def _touch_from_payload(t: dict[str, Any]) -> dict[str, Any]:
        if "x" in t and "y" in t:
            return {"x": int(t["x"]), "y": int(t["y"])}
        if "by_text" in t:
            return {"by_text": str(t["by_text"])}
        if "by_id" in t:
            return {"by_id": str(t["by_id"])}
        raise ValueError(f"Unsupported touch payload: {t!r}")

    async def _apply_touch_block(
        self, touch: dict[str, Any], *, wait_time: float
    ) -> None:
        kwargs = self._touch_from_payload(touch)
        kwargs["wait_time"] = wait_time
        await self._ui.touch(**kwargs)

    async def _apply_input_block(
        self,
        block: dict[str, Any],
        *,
        value: str | None,
        by_text: str | None,
        by_id: str | None,
    ) -> None:
        text = value if value is not None else block.get("text")
        if text is None:
            raise ValueError("VLM input payload missing text and no value= provided")
        bt = block.get("by_text", by_text)
        bid = block.get("by_id", by_id)
        await self._ui.input_text(str(text), by_text=bt, by_id=bid)

    async def _apply_action_block(self, act: dict[str, Any]) -> None:
        t = act.get("type")
        if t == "touch":
            payload = {k: act[k] for k in ("x", "y", "by_text", "by_id") if k in act}
            kwargs = self._touch_from_payload(payload)
            kwargs["wait_time"] = float(act.get("wait_time", 0.1))
            await self._ui.touch(**kwargs)
        elif t == "input":
            txt = act.get("text")
            if txt is None:
                raise ValueError("action type=input requires text")
            await self._ui.input_text(
                str(txt),
                by_text=act.get("by_text"),
                by_id=act.get("by_id"),
            )
        else:
            raise ValueError(f"Unsupported action type: {t!r}")

    @staticmethod
    def interpret_query_payload(
        raw: dict[str, Any],
        *,
        schema: type | None = None,
    ) -> Any:
        """Coerce ``answer`` / ``dtype`` from a VLM-shaped query JSON (no UI)."""
        answer = raw.get("answer")
        dtype = str(raw.get("dtype", "string"))
        if schema is None:
            if dtype == "number":
                return float(answer) if isinstance(answer, str) else answer
            if dtype == "boolean":
                return bool(answer)
            return answer
        if schema is float:
            return float(answer)
        if schema is int:
            return int(answer)
        if schema is bool:
            return bool(answer)
        if schema is str:
            return str(answer)
        return answer

    @staticmethod
    def interpret_assert_payload(raw: dict[str, Any]) -> None:
        """Raise ``AssertionError`` unless ``ok`` is true (VLM-shaped assert JSON)."""
        if not raw.get("ok", False):
            raise AssertionError(str(raw.get("reason", "assertion failed")))

    async def run_planned_action(self, payload: dict[str, Any]) -> None:
        """Apply one UI step from external JSON matching ``response_schema="action"`` (no VLM)."""
        await self._ensure_ui()
        act = payload.get("action")
        if not isinstance(act, dict):
            raise ValueError(f"planned action payload missing action dict: {payload!r}")
        await self._apply_action_block(act)

    async def run_planned_tap(
        self, payload: dict[str, Any], *, wait_time: float = 0.1
    ) -> None:
        """Apply one touch from external JSON matching ``response_schema="tap"`` (no VLM)."""
        await self._ensure_ui()
        touch = payload.get("touch")
        if not isinstance(touch, dict):
            raise ValueError(f"planned tap payload missing touch dict: {payload!r}")
        await self._apply_touch_block(touch, wait_time=wait_time)

    async def run_planned_input(
        self,
        payload: dict[str, Any],
        *,
        value: str | None = None,
        by_text: str | None = None,
        by_id: str | None = None,
    ) -> None:
        """Apply one input from external JSON matching ``response_schema="input"`` (no VLM)."""
        await self._ensure_ui()
        block = payload.get("input")
        if not isinstance(block, dict):
            raise ValueError(f"planned input payload missing input dict: {payload!r}")
        await self._apply_input_block(
            block, value=value, by_text=by_text, by_id=by_id
        )

    async def ai_tap(
        self,
        *,
        instruction: str | None = None,
        x: int | None = None,
        y: int | None = None,
        by_text: str | None = None,
        by_id: str | None = None,
        wait_time: float = 0.1,
    ) -> None:
        await self._ensure_ui()
        if instruction is None:
            await self._ui.touch(
                x=x,
                y=y,
                by_text=by_text,
                by_id=by_id,
                wait_time=wait_time,
            )
            return
        vlm = self._require_vlm()
        png = await self._ui.screenshot()
        raw = await vlm.vision_json(
            instruction=instruction,
            screenshot_png=png,
            response_schema="tap",
        )
        touch = raw.get("touch")
        if not isinstance(touch, dict):
            raise ValueError(f"VLM tap response missing touch dict: {raw!r}")
        await self._apply_touch_block(touch, wait_time=wait_time)

    async def ai_input(
        self,
        value: str | None = None,
        *,
        instruction: str | None = None,
        by_text: str | None = None,
        by_id: str | None = None,
    ) -> None:
        await self._ensure_ui()
        if instruction is None:
            if value is None:
                raise ValueError("ai_input requires value= when instruction is omitted")
            await self._ui.input_text(value, by_text=by_text, by_id=by_id)
            return
        vlm = self._require_vlm()
        png = await self._ui.screenshot()
        raw = await vlm.vision_json(
            instruction=instruction,
            screenshot_png=png,
            response_schema="input",
        )
        block = raw.get("input")
        if not isinstance(block, dict):
            raise ValueError(f"VLM input response missing input dict: {raw!r}")
        await self._apply_input_block(
            block, value=value, by_text=by_text, by_id=by_id
        )

    async def ai_action(self, instruction: str) -> None:
        await self._ensure_ui()
        vlm = self._require_vlm()
        png = await self._ui.screenshot()
        raw = await vlm.vision_json(
            instruction=instruction,
            screenshot_png=png,
            response_schema="action",
        )
        act = raw.get("action")
        if not isinstance(act, dict):
            raise ValueError(f"VLM action response missing action dict: {raw!r}")
        await self._apply_action_block(act)

    async def ai_query(
        self,
        instruction: str,
        *,
        schema: type | None = None,
    ) -> Any:
        await self._ensure_ui()
        vlm = self._require_vlm()
        png = await self._ui.screenshot()
        raw = await vlm.vision_json(
            instruction=instruction,
            screenshot_png=png,
            response_schema="query",
        )
        return self.interpret_query_payload(raw, schema=schema)

    async def ai_assert(self, instruction: str) -> None:
        await self._ensure_ui()
        vlm = self._require_vlm()
        png = await self._ui.screenshot()
        raw = await vlm.vision_json(
            instruction=instruction,
            screenshot_png=png,
            response_schema="assert",
        )
        self.interpret_assert_payload(raw)

    async def ai_wait_for(
        self,
        instruction: str,
        *,
        timeout: float = 10.0,
        interval: float = 0.5,
    ) -> None:
        deadline = time.monotonic() + timeout
        last_err: AssertionError | None = None
        while time.monotonic() < deadline:
            try:
                await self.ai_assert(instruction)
                return
            except AssertionError as e:
                last_err = e
                await asyncio.sleep(interval)
        raise TimeoutError(
            last_err.args[0] if last_err else f"wait_for timeout: {instruction!r}"
        )

    async def ai_locate(self, instruction: str) -> dict[str, Any]:
        await self._ensure_ui()
        vlm = self._require_vlm()
        png = await self._ui.screenshot()
        return await vlm.vision_json(
            instruction=instruction,
            screenshot_png=png,
            response_schema="locate",
        )
