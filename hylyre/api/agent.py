"""Midscene-style ``HylyreAgent``: structured UI ops + optional VLM for natural language."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from hylyre.drivers.base import MockControllerBase, UiDriverBase, VlmClientBase
from hylyre.ui_dump_hints import augment_ui_dump_payload


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

    async def ensure_connected(self) -> None:
        """Connect Hypium once; safe for session daemons and MCP ``open_session``."""
        await self._ensure_ui()

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

    async def dump_ui(self) -> dict[str, Any]:
        """Return structured UI tree for external agents (no VLM)."""
        await self._ensure_ui()
        raw = await self._ui.dump_ui()
        if isinstance(raw, dict):
            return augment_ui_dump_payload(raw)
        return raw

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
        elif t == "swipe":
            block = {k: v for k, v in act.items() if k != "type"}
            await self._apply_swipe_block(block)
        elif t == "scroll":
            block = {k: v for k, v in act.items() if k != "type"}
            await self._apply_scroll_block(block)
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

    @staticmethod
    def _swipe_area_kwargs(area: dict[str, Any] | None) -> dict[str, str | None]:
        blank = {
            "area_by_text": None,
            "area_by_id": None,
            "area_by_type": None,
            "area_by_key": None,
        }
        if area is None:
            return blank
        if not isinstance(area, dict):
            raise ValueError("swipe.area must be an object or omitted")
        found = [
            k
            for k in ("by_text", "by_id", "by_type", "by_key")
            if area.get(k) is not None
        ]
        if len(found) > 1:
            raise ValueError(
                "swipe.area allows at most one of by_text, by_id, by_type, by_key"
            )
        out = dict(blank)
        if len(found) == 1:
            k = found[0]
            out[f"area_{k}"] = str(area[k])
        return out

    async def _apply_swipe_block(self, block: dict[str, Any]) -> None:
        direction = block.get("direction")
        if not isinstance(direction, str) or not direction.strip():
            raise ValueError("swipe requires non-empty string direction")
        area_kw = self._swipe_area_kwargs(block.get("area"))
        sp_raw = block.get("start_point")
        sp: tuple[float, float] | None = None
        if sp_raw is not None:
            if (
                not isinstance(sp_raw, (list, tuple))
                or len(sp_raw) != 2
            ):
                raise ValueError("swipe start_point must be a pair [x, y]")
            sp = (float(sp_raw[0]), float(sp_raw[1]))
        speed_raw = block.get("speed")
        speed_i = None if speed_raw is None else int(speed_raw)
        side_raw = block.get("side")
        await self._ui.swipe(
            direction=direction,
            distance=int(block.get("distance", 60)),
            side=str(side_raw) if side_raw is not None else None,
            start_point=sp,
            swipe_time=float(block.get("swipe_time", 0.3)),
            speed=speed_i,
            **area_kw,
        )

    @staticmethod
    def _scroll_xy_or_none(
        *, at: dict[str, Any] | None, block: dict[str, Any]
    ) -> tuple[int | None, int | None]:
        bx = block.get("x")
        by = block.get("y")
        if bx is not None or by is not None:
            if at is not None:
                raise ValueError(
                    "scroll: use top-level x/y or scroll.at, not both"
                )
            if bx is None or by is None:
                raise ValueError("scroll x and y must be provided together")
            return int(bx), int(by)
        if at is None:
            return None, None
        if not isinstance(at, dict):
            raise ValueError("scroll.at must be an object or omitted")
        if at.get("x") is not None or at.get("y") is not None:
            if at.get("x") is None or at.get("y") is None:
                raise ValueError("scroll.at x and y must be provided together")
            sel_keys = [
                k
                for k in ("by_text", "by_id", "by_type", "by_key")
                if at.get(k) is not None
            ]
            if sel_keys:
                raise ValueError("scroll.at cannot mix x/y with selector keys")
            return int(at["x"]), int(at["y"])
        return None, None

    @staticmethod
    def _scroll_selector_kwargs(at: dict[str, Any] | None) -> dict[str, str | None]:
        blank = {
            "at_by_text": None,
            "at_by_id": None,
            "at_by_type": None,
            "at_by_key": None,
        }
        if at is None:
            return blank
        if not isinstance(at, dict):
            raise ValueError("scroll.at must be an object or omitted")
        if at.get("x") is not None or at.get("y") is not None:
            return blank
        found = [
            k
            for k in ("by_text", "by_id", "by_type", "by_key")
            if at.get(k) is not None
        ]
        if len(found) > 1:
            raise ValueError(
                "scroll.at allows at most one of by_text, by_id, by_type, by_key"
            )
        out = dict(blank)
        if len(found) == 1:
            k = found[0]
            out[f"at_{k}"] = str(at[k])
        return out

    async def _apply_scroll_block(self, block: dict[str, Any]) -> None:
        direction = block.get("direction")
        if not isinstance(direction, str) or not direction.strip():
            raise ValueError("scroll requires non-empty string direction")
        steps_raw = block.get("steps")
        if steps_raw is None:
            raise ValueError("scroll requires steps")
        steps = int(steps_raw)
        at = block.get("at")
        if at is not None and not isinstance(at, dict):
            raise ValueError("scroll.at must be an object or omitted")
        xy = self._scroll_xy_or_none(at=at, block=block)
        sel_kw = self._scroll_selector_kwargs(at)
        k1 = block.get("key1")
        k2 = block.get("key2")
        await self._ui.mouse_scroll(
            direction=direction,
            steps=steps,
            x=xy[0],
            y=xy[1],
            key1=None if k1 is None else int(k1),
            key2=None if k2 is None else int(k2),
            **sel_kw,
        )

    async def run_planned_swipe(self, payload: dict[str, Any]) -> None:
        """Apply ``swipe`` block (Hypium directional swipe; no VLM)."""
        await self._ensure_ui()
        block = payload.get("swipe")
        if not isinstance(block, dict):
            raise ValueError(f"planned swipe payload missing swipe dict: {payload!r}")
        await self._apply_swipe_block(block)

    async def run_planned_scroll(self, payload: dict[str, Any]) -> None:
        """Apply ``scroll`` block (Hypium mouse_scroll; vertical wheel; no VLM)."""
        await self._ensure_ui()
        block = payload.get("scroll")
        if not isinstance(block, dict):
            raise ValueError(f"planned scroll payload missing scroll dict: {payload!r}")
        await self._apply_scroll_block(block)

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

    async def ai_string(self, instruction: str) -> str:
        out = await self.ai_query(instruction, schema=str)
        return str(out)

    async def ai_number(self, instruction: str) -> float:
        out = await self.ai_query(instruction, schema=float)
        return float(out)

    async def ai_boolean(self, instruction: str) -> bool:
        out = await self.ai_query(instruction, schema=bool)
        return bool(out)

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
