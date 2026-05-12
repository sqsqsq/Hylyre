"""Wiring helpers (mocked drivers)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hylyre.wiring import create_hypium_agent, create_hypium_agent_with_env_vlm


def test_create_hypium_agent_ui_only() -> None:
    fake_ui = MagicMock()
    with patch("hylyre.drivers.hypium.HypiumDriver", return_value=fake_ui):
        ag = create_hypium_agent(device_sn="sn1")
    assert ag.ui is fake_ui
    assert ag.mock_controller is None
    assert ag.vlm is None


def test_create_hypium_agent_with_lyrebird_url() -> None:
    fake_ui = MagicMock()
    fake_mock = MagicMock()
    with patch("hylyre.drivers.hypium.HypiumDriver", return_value=fake_ui):
        with patch(
            "hylyre.drivers.lyrebird.LyrebirdController", return_value=fake_mock
        ):
            ag = create_hypium_agent(lyrebird_base_url="http://127.0.0.1:9090")
    assert ag.ui is fake_ui
    assert ag.mock_controller is fake_mock


def test_create_hypium_agent_with_env_vlm() -> None:
    fake_ui = MagicMock()
    fake_vlm = MagicMock()
    with patch("hylyre.drivers.hypium.HypiumDriver", return_value=fake_ui):
        with patch("hylyre.vlm.http_vlm.HttpVlmClient.from_env", return_value=fake_vlm):
            ag = create_hypium_agent_with_env_vlm(device_sn="s")
    assert ag.vlm is fake_vlm
