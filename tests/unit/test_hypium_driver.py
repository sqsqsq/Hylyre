"""L1: HypiumDriver delegates to hypium.UiDriver (mocked; no device)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hylyre.drivers.hypium import HypiumDriver


def _fake_shim(raw: MagicMock) -> MagicMock:
    UiDriver = MagicMock()
    UiDriver.connect.return_value = raw
    BY = MagicMock()
    BY.text.side_effect = lambda txt, mp=None: f"text:{txt}"
    BY.id.side_effect = lambda comp_id, mp=None: f"id:{comp_id}"
    shim = MagicMock()
    shim.UiDriver = UiDriver
    shim.BY = BY
    shim.hypium_mod = MagicMock()
    return shim


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_connect_and_close(mock_load: MagicMock) -> None:
    raw = MagicMock()
    shim = _fake_shim(raw)
    mock_load.return_value = shim
    d = HypiumDriver(device_sn="abc")
    await d.connect()
    shim.UiDriver.connect.assert_called_once()
    await d.close()
    raw.close.assert_called_once()


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_touch_coordinate(mock_load: MagicMock) -> None:
    raw = MagicMock()
    mock_load.return_value = _fake_shim(raw)
    d = HypiumDriver(device_sn="abc")
    await d.connect()
    await d.touch(x=3, y=4)
    raw.touch.assert_called_once()
    args, kwargs = raw.touch.call_args
    assert args[0] == (3, 4)
    assert kwargs["wait_time"] == 0.1


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_touch_by_selector(mock_load: MagicMock) -> None:
    raw = MagicMock()
    shim = _fake_shim(raw)
    mock_load.return_value = shim
    d = HypiumDriver()
    await d.connect()
    await d.touch(by_text="OK")
    raw.touch.assert_called_once()
    assert raw.touch.call_args[0][0] == "text:OK"


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_input_text_cursor(mock_load: MagicMock) -> None:
    raw = MagicMock()
    mock_load.return_value = _fake_shim(raw)
    d = HypiumDriver()
    await d.connect()
    await d.input_text("x")
    raw.input_text_on_current_cursor.assert_called_once_with("x")


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_input_text_with_component(mock_load: MagicMock) -> None:
    raw = MagicMock()
    comp = MagicMock()
    raw.find_component.return_value = comp
    mock_load.return_value = _fake_shim(raw)
    d = HypiumDriver()
    await d.connect()
    await d.input_text("hi", by_id="username")
    raw.find_all_components.assert_called_once()
    raw.input_text.assert_called_once()


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_locate_by_text(mock_load: MagicMock) -> None:
    raw = MagicMock()
    comp = MagicMock()
    comp.getBounds.return_value = [10, 20, 110, 80]
    raw.find_component.return_value = comp
    mock_load.return_value = _fake_shim(raw)
    d = HypiumDriver()
    await d.connect()
    center = await d.locate_by_text(by_text="OK")
    assert center == (60, 50)
    raw.find_component.assert_called_once()


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_screenshot_reads_file(mock_load: MagicMock, tmp_path) -> None:
    raw = MagicMock()

    def _capture(path: str, in_pc: bool, area) -> str:
        p = __import__("pathlib").Path(path)
        p.write_bytes(b"abc")
        return str(p)

    raw.capture_screen.side_effect = _capture
    mock_load.return_value = _fake_shim(raw)
    d = HypiumDriver()
    await d.connect()
    data = await d.screenshot()
    assert data == b"abc"


@pytest.mark.asyncio
@patch("hylyre.drivers.hypium.driver.load_hypium_shim")
async def test_hypium_install_app(mock_load: MagicMock, tmp_path) -> None:
    raw = MagicMock()
    mock_load.return_value = _fake_shim(raw)
    hap = tmp_path / "a.hap"
    hap.write_bytes(b"hap")
    d = HypiumDriver()
    await d.connect()
    await d.install_app(hap)
    raw.install_app.assert_called_once()
