"""Offline acceptance: real entry points, substituting capture/transport only."""

import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest
from typer.testing import CliRunner

from hylyre.api.agent import HylyreAgent
from hylyre.cli.__main__ import app
from hylyre.cli.commands import loop_cmd, steps_cmd
from hylyre.scenario.runner import ScenarioRunner
from hylyre.session.daemon import _dispatch
from tests.contract.fakes.fake_ui_driver import FakeUiDriver
from tests.image_samples import image_bytes, invalid_images


def capture_boundary(monkeypatch, raw):
    class Capture(FakeUiDriver):
        def __init__(self, **kwargs):
            super().__init__()

        async def screenshot(self):
            if isinstance(raw, Exception):
                raise raw
            return raw

    monkeypatch.setattr(loop_cmd, "HypiumDriver", Capture)
    def ipc(*args):
        if isinstance(raw, Exception):
            raise raw
        # The client must determine MIME from bytes, even if transport lies.
        return {"mime": "image/wrong", "base64": base64.b64encode(raw).decode()}
    monkeypatch.setattr(loop_cmd, "_session_ipc", ipc)


@pytest.mark.parametrize("session", [False, True])
@pytest.mark.parametrize("source", ["JPEG", "PNG"])
@pytest.mark.parametrize("suffix", [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"])
def test_cli_file_entry_formats(tmp_path, monkeypatch, session, source, suffix):
    raw = image_bytes(source)
    capture_boundary(monkeypatch, raw)
    out = tmp_path / ("shot" + suffix)
    args = ["screenshot", "--out", str(out)]
    if session:
        args += ["--session", str(tmp_path / "session.json")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == str(out.resolve())
    assert result.stderr == ""
    with Image.open(out) as image:
        image.verify()
    with Image.open(out) as image, Image.open(BytesIO(raw)) as original:
        image.load()
        original.load()
        assert image.format == ("PNG" if suffix.lower() == ".png" else "JPEG")
        assert image.size == original.size
        if image.format == source:
            assert out.read_bytes() == raw
        elif image.format == "PNG":
            assert image.tobytes() == original.tobytes()
        else:
            for point in [(8, 8), (36, 24), (36, 8)]:
                assert max(abs(a-b) for a,b in zip(image.getpixel(point), original.getpixel(point))) <= 12


@pytest.mark.parametrize("session", [False, True])
@pytest.mark.parametrize("raw", invalid_images() + [RuntimeError("capture failed"), ImportError("Pillow unavailable")])
def test_cli_failure_no_success_or_old_image_reuse(tmp_path, monkeypatch, session, raw):
    capture_boundary(monkeypatch, raw)
    out = tmp_path / "old.png"
    old = image_bytes()
    args = ["screenshot", "--out", str(out)]
    if session:
        args += ["--session", str(tmp_path / "session.json")]
    for existing in (False, True):
        if existing:
            out.write_bytes(old)
        result = CliRunner().invoke(app, args)
        assert result.exit_code == (2 if isinstance(raw, ImportError) else 1)
        assert result.stdout == ""
        assert result.stderr.strip()
        if not isinstance(raw, Exception):
            assert "Screenshot is not a valid PNG/JPEG image:" in result.stderr
        assert out.exists() == existing
        if existing:
            assert out.read_bytes() == old


@pytest.mark.parametrize("session", [False, True])
def test_validation_dependency_importerror_keeps_cli_exit2(tmp_path, monkeypatch, session):
    capture_boundary(monkeypatch, image_bytes())
    def missing(*args, **kwargs):
        raise ImportError("Pillow plugin unavailable")
    monkeypatch.setattr(Image, "open", missing)
    args = ["screenshot", "--out", str(tmp_path / "missing.png")]
    if session:
        args += ["--session", str(tmp_path / "session.json")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Pillow plugin unavailable" in result.stderr
    assert "not a valid PNG/JPEG" not in result.stderr


@pytest.mark.parametrize("session", [False, True])
@pytest.mark.parametrize("name", ["shot", "shot.txt", "shot.bmp"])
def test_cli_suffix_rejected_before_capture_or_ipc(tmp_path, monkeypatch, session, name):
    def fail(*args, **kwargs):
        pytest.fail("device or IPC called for invalid suffix")
    monkeypatch.setattr(loop_cmd, "HypiumDriver", fail)
    monkeypatch.setattr(loop_cmd, "_session_ipc", fail)
    args = ["screenshot", "--out", str(tmp_path / name)]
    if session:
        args += ["--session", str(tmp_path / "session.json")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert ".png, .jpg or .jpeg" in result.stderr
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("session", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_cli_write_failure(tmp_path, monkeypatch, session, existing):
    from hylyre import image_io
    capture_boundary(monkeypatch, image_bytes("JPEG"))
    out = tmp_path / "shot.png"
    old = image_bytes()
    if existing:
        out.write_bytes(old)
    def fail(*args):
        raise OSError("replace blocked")
    monkeypatch.setattr(image_io.os, "replace", fail)
    args = ["screenshot", "--out", str(out)]
    if session:
        args += ["--session", str(tmp_path / "session.json")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "replace blocked" in result.stderr
    assert "not a valid PNG/JPEG" not in result.stderr
    assert list(tmp_path.iterdir()) == ([out] if existing else [])
    if existing:
        assert out.read_bytes() == old


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["plan", "steps", "atomic"])
@pytest.mark.parametrize("bad_capture", [False, True])
async def test_diagnostics_decode_and_hash_without_masking_failure(tmp_path, entry, bad_capture):
    raw = b"bad screenshot" if bad_capture else image_bytes("JPEG")
    class Capture(FakeUiDriver):
        async def screenshot(self):
            return raw
    agent = HylyreAgent(ui=Capture(dump_tree={"attributes": {"type": "Root", "bounds": "[0,0][100,100]"}, "children": []}))
    failure_dir = tmp_path / "failures"
    failure_dir.mkdir()
    # Existing valid screenshots must not be registered after a failed capture.
    old = image_bytes()
    for name in ["T-step-0.png", "step-0.png", "atomic-step-0.png"]:
        (failure_dir / name).write_bytes(old)
    payload = {"touch": {"by_text": "missing"}}
    if entry == "atomic":
        row = await loop_cmd._run_atomic_ledger_step(agent, payload, failure_dir=failure_dir)
        step = row["step_result"]
    elif entry == "steps":
        batch = await steps_cmd.run_steps_on_agent(agent, [payload], failure_dir=failure_dir)
        step = batch["results"][0]["step_result"]
    else:
        plan = tmp_path / "plan.md"
        plan.write_text('''# Test
## 测试用例清单
| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | AC 关联 |
| --- | --- | --- | --- | --- | --- | --- |
| T | missing | | {"touch":{"by_text":"missing"}} | - | P0 | AC-1 |
''', encoding="utf-8")
        result = await ScenarioRunner().run_plan_on_agent(agent, plan, feature="images", check_expected=False, failure_dir=failure_dir)
        step = result.case_results[0].steps[0].to_dict()
    assert step["outcome"]["status"] == "failed"
    assert step["outcome"]["failure"]["domain"] == "selector"
    artifacts = step["artifacts"]
    assert "ui_dump" in {a["kind"] for a in artifacts}
    assert ("screenshot" in {a["kind"] for a in artifacts}) == (not bad_capture)
    for artifact in artifacts:
        path = failure_dir / Path(artifact["path"]).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
        if artifact["kind"] == "screenshot":
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image, Image.open(BytesIO(raw)) as original:
                image.load()
                original.load()
                assert image.format == "PNG"
                assert image.tobytes() == original.tobytes()
    if bad_capture:
        assert all(p.read_bytes() == old for p in failure_dir.glob("*.png"))


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [image_bytes("JPEG"), image_bytes()] + invalid_images())
async def test_daemon_dispatch_and_cli_bytes(monkeypatch, raw):
    class Capture(FakeUiDriver):
        async def screenshot(self):
            return raw
    if raw in invalid_images():
        with pytest.raises(Exception):
            await _dispatch(HylyreAgent(ui=Capture()), "screenshot_bytes", {})
    else:
        result = await _dispatch(HylyreAgent(ui=Capture()), "screenshot_bytes", {})
        assert set(result) == {"mime", "base64"}
        assert result["mime"] == ("image/png" if raw.startswith(b"\x89PNG") else "image/jpeg")
        assert base64.b64decode(result["base64"]) == raw


@pytest.mark.asyncio
@pytest.mark.parametrize("session", [False, True])
@pytest.mark.parametrize("raw", [image_bytes("JPEG"), image_bytes()] + invalid_images())
async def test_mcp_modes_real_image_response(monkeypatch, raw, session):
    from fastmcp import Client
    from hylyre.mcp import server
    from hylyre import wiring
    class Capture(FakeUiDriver):
        async def screenshot(self):
            return raw
    agent = HylyreAgent(ui=Capture())
    monkeypatch.setattr(wiring, "create_hypium_agent", lambda **kwargs: agent)
    capture_boundary(monkeypatch, raw)
    async with Client(server.build_mcp()) as client:
        args = {}
        if session:
            opened = await client.call_tool("hylyre_open_session", {})
            args = {"session_id": json.loads(opened.content[0].text)["session_id"]}
        if raw in invalid_images():
            with pytest.raises(Exception):
                await client.call_tool("hylyre_screenshot", args)
        else:
            response = await client.call_tool("hylyre_screenshot", args)
            data = json.loads(response.content[0].text)
            assert set(data) == {"mime", "base64"}
            assert data["mime"] == ("image/png" if raw.startswith(b"\x89PNG") else "image/jpeg")
            assert base64.b64decode(data["base64"]) == raw
