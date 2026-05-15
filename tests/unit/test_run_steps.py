"""Unit tests for batch planned steps."""

from __future__ import annotations

from pathlib import Path

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.api.step_dispatch import dispatch_planned_step
from hylyre.cli.commands import steps_cmd

from tests.contract.fakes.fake_ui_driver import FakeUiDriver


@pytest.mark.asyncio
async def test_run_steps_three_touch_ok() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    steps_arr = [
        {"touch": {"by_text": "a"}},
        {"touch": {"by_text": "b"}},
        {"touch": {"by_text": "c"}},
    ]
    result = await steps_cmd.run_steps_on_agent(agent, steps_arr, on_fail="abort")
    assert result["total"] == 3
    assert result["executed"] == 3
    assert all(r["status"] == "ok" for r in result["results"])
    taps = [e for e in ui.events if e[0] == "touch"]
    assert len(taps) == 3


@pytest.mark.asyncio
async def test_run_steps_abort_on_second_error(monkeypatch: pytest.MonkeyPatch) -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    seq = iter([None, RuntimeError("boom")])

    async def boom_touch(
        *,
        x: int | None = None,
        y: int | None = None,
        by_text: str | None = None,
        by_id: str | None = None,
        wait_time: float = 0.1,
    ) -> None:
        r = next(seq)
        if isinstance(r, Exception):
            raise r
        ui._validate_touch_kwargs(  # type: ignore[attr-defined]
            x=x, y=y, by_text=by_text, by_id=by_id
        )
        ui.events.append(
            (
                "touch",
                {
                    "x": x,
                    "y": y,
                    "by_text": by_text,
                    "by_id": by_id,
                    "wait_time": wait_time,
                },
            )
        )

    monkeypatch.setattr(ui, "touch", boom_touch)

    steps_arr = [{"touch": {"by_text": "a"}}, {"touch": {"by_text": "b"}}]
    result = await steps_cmd.run_steps_on_agent(agent, steps_arr, on_fail="abort")
    assert result["total"] == 2
    assert result["executed"] == 2
    assert result["results"][0]["status"] == "ok"
    assert result["results"][1]["status"] == "error"


@pytest.mark.asyncio
async def test_run_steps_skip_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    seq = iter([None, RuntimeError("boom"), None])

    async def boom_touch(
        *,
        x: int | None = None,
        y: int | None = None,
        by_text: str | None = None,
        by_id: str | None = None,
        wait_time: float = 0.1,
    ) -> None:
        r = next(seq)
        if isinstance(r, Exception):
            raise r
        ui._validate_touch_kwargs(  # type: ignore[attr-defined]
            x=x, y=y, by_text=by_text, by_id=by_id
        )
        ui.events.append(
            (
                "touch",
                {
                    "x": x,
                    "y": y,
                    "by_text": by_text,
                    "by_id": by_id,
                    "wait_time": wait_time,
                },
            )
        )

    monkeypatch.setattr(ui, "touch", boom_touch)

    steps_arr = [
        {"touch": {"by_text": "a"}},
        {"touch": {"by_text": "b"}},
        {"touch": {"by_text": "c"}},
    ]
    result = await steps_cmd.run_steps_on_agent(agent, steps_arr, on_fail="skip")
    assert result["executed"] == 3
    assert result["results"][0]["status"] == "ok"
    assert result["results"][1]["status"] == "error"
    assert result["results"][2]["status"] == "ok"


@pytest.mark.asyncio
async def test_run_steps_empty() -> None:
    agent = HylyreAgent(ui=FakeUiDriver(), vlm=None)
    result = await steps_cmd.run_steps_on_agent(agent, [], on_fail="abort")
    assert result["total"] == 0
    assert result["executed"] == 0
    assert result["results"] == []


def test_execute_run_steps_start_app_via_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """execute_run_steps + bundle invokes start_app on the agent."""
    captured: list[str] = []
    fake = FakeUiDriver()

    async def fake_with_hypium(
        *,
        device_sn=None,
        mock_port=None,
        lyrebird_url=None,
        fn=None,
    ):
        assert fn is not None
        ag = HylyreAgent(ui=fake, vlm=None)

        async def wrap():
            captured.append(device_sn or "nil")
            return await fn(ag)

        return await wrap()

    monkeypatch.setattr(
        "hylyre.cli.commands.steps_cmd._with_hypium_agent",
        fake_with_hypium,
    )

    out = steps_cmd.execute_run_steps(
        [{"touch": {"by_text": "x"}}],
        device_sn=None,
        session_file=None,
        on_fail="abort",
        bundle="com.example.app",
        page_name=None,
        wait_time=1.0,
    )
    assert out["results"][0]["status"] == "ok"
    starts = [e for e in fake.events if e[0] == "start_app"]
    assert len(starts) == 1
    assert starts[0][1]["bundle"] == "com.example.app"


def test_load_steps_invalid_not_array(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"touch": {"by_text": "nope"}}', encoding="utf-8")
    with pytest.raises(ValueError, match="array"):
        steps_cmd.load_steps_json_array(Path(bad))


def test_parse_steps_bad_type() -> None:
    with pytest.raises(ValueError, match="JSON array"):
        steps_cmd.parse_steps_inline('"{}"')


def test_normalize_on_fail() -> None:
    assert steps_cmd._normalize_on_fail("SKIP") == "skip"
    with pytest.raises(ValueError):
        steps_cmd._normalize_on_fail("nope")


@pytest.mark.asyncio
async def test_dispatch_invalid_root() -> None:
    ag = HylyreAgent(ui=FakeUiDriver(), vlm=None)
    with pytest.raises(ValueError, match="action"):
        await dispatch_planned_step(ag, {"foo": 1})
