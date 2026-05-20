"""L1: test-plan.md parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from hylyre.scenario.plan_parse import parse_test_plan

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "e2e" / "fixtures" / "mock-test-plan.md"
JSON_STEPS_FIXTURE = ROOT / "tests" / "e2e" / "fixtures" / "json-steps-test-plan.md"


def test_parse_mock_fixture() -> None:
    parsed = parse_test_plan(FIXTURE)
    assert len(parsed.cases) == 2
    assert parsed.cases[0].case_id == "TC-MOCK-01"
    assert parsed.cases[0].ac_ref == "AC-M-01"
    assert parsed.cases[1].case_id == "TC-MOCK-02"


def test_parse_json_steps_fixture() -> None:
    parsed = parse_test_plan(JSON_STEPS_FIXTURE)
    assert len(parsed.cases) == 2
    c0 = parsed.cases[0]
    assert c0.case_id == "TC-JSON-01"
    assert '{"action":' in c0.steps
    assert '{"input":' in c0.steps
    assert ";" in c0.steps or "；" in c0.steps
    c1 = parsed.cases[1]
    assert c1.case_id == "TC-JSON-02"
    assert '{"back":' in c1.steps


def test_parse_rejects_missing_table(tmp_path: Path) -> None:
    p = tmp_path / "empty.md"
    p.write_text("# X\n\nNo table here.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="测试用例清单"):
        parse_test_plan(p)
