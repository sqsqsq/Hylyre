"""json_extract helper."""

from __future__ import annotations

import pytest

from hylyre.vlm.json_extract import extract_json_object


def test_extract_plain() -> None:
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_extract_fenced() -> None:
    raw = """Here is JSON:
```json
{"ok": true}
```
"""
    assert extract_json_object(raw) == {"ok": True}


def test_extract_nested_braces() -> None:
    s = 'noise {"x": 2} tail'
    assert extract_json_object(s) == {"x": 2}


def test_reject_non_object() -> None:
    with pytest.raises(ValueError):
        extract_json_object("[1]")
