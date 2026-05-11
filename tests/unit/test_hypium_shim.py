"""Hypium lazy import messaging."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import hylyre.drivers.hypium.driver as hypdrv


def test_load_hypium_shim_import_error_message() -> None:
    hypdrv.reset_hypium_shim_for_tests()
    with patch("importlib.import_module", side_effect=ImportError("missing")):
        with pytest.raises(ImportError) as ei:
            hypdrv.load_hypium_shim()
        assert "hylyre[device]" in str(ei.value)
