"""Unit tests for MCP description token heuristic."""

from __future__ import annotations

from hylyre.mcp.description_budget import approximate_token_count, description_within_budget


def test_empty_within_budget() -> None:
    assert description_within_budget("", max_tokens=500)
    assert approximate_token_count("   ") == 0


def test_short_description() -> None:
    s = "Hello world."
    assert approximate_token_count(s) == 2
    assert description_within_budget(s, max_tokens=500)
