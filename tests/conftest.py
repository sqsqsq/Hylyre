"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from hylyre.drivers.hypium.driver import reset_hypium_shim_for_tests


@pytest.fixture(autouse=True)
def _reset_hypium_singleton() -> None:
    reset_hypium_shim_for_tests()
    yield
    reset_hypium_shim_for_tests()
