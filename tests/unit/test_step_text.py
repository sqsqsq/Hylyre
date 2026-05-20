"""Unit tests for planned step text normalization."""

from __future__ import annotations

import pytest

from hylyre.scenario.step_text import (
    json_step_syntax_error,
    looks_like_planned_json,
    non_json_step_error,
    normalize_planned_step_text,
)


def test_normalize_strips_single_backticks() -> None:
    raw = '`{"touch":{"by_text":"OK"}}`'
    assert normalize_planned_step_text(raw) == '{"touch":{"by_text":"OK"}}'


def test_normalize_strips_double_backticks() -> None:
    raw = '``{"back":{}}``'
    assert normalize_planned_step_text(raw) == '{"back":{}}'


def test_normalize_strips_json_fence() -> None:
    raw = '```json\n{"wait":{"seconds":1}}\n```'
    assert normalize_planned_step_text(raw) == '{"wait":{"seconds":1}}'


def test_looks_like_planned_json_with_backticks() -> None:
    assert looks_like_planned_json('`{"touch":{"by_text":"x"}}`')


def test_non_json_error_mentions_touch_and_action() -> None:
    msg = non_json_step_error("TC-1")
    assert "touch" in msg
    assert "action" in msg
    assert "反引号" in msg


def test_json_syntax_error_includes_case_id() -> None:
    msg = json_step_syntax_error("TC-2", ValueError("bad"), "{broken")
    assert "TC-2" in msg
