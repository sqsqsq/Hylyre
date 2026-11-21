"""L1: test-plan.md parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hylyre.scenario.plan_parse import parse_test_plan
from hylyre.scenario.plan_contract import validate_plan_contract
from hylyre.scenario.step_text import iter_plan_steps

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


def _write_plan(
    tmp_path: Path, steps: str, *, name: str = "name<br/>next",
    preconditions: str = '已有"a<br/>b"', expected: str = "expected<br/>next",
) -> Path:
    path = tmp_path / "test-plan.md"
    path.write_text(
        "# Plan\n\n## 测试用例清单\n\n"
        "| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        f'| TC-001 | {name} | {preconditions} | {steps} | {expected} | P0 | AC-1 |\n',
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("separator", [";", "；"])
@pytest.mark.parametrize("command,text", [
    ("printf '%s' '<br/>'", "<br/>"),
    ("printf 'a<br/>b'", "a<br/>b"),
    (r'''printf '中文;；\"<br/>end' | cat''', r'''C:\tmp\<br/>"quoted"\n'''),
    (r'''printf 'backslash\\<br/>end' ''', r'''escaped\"<br/>then\\<br/>end'''),
])
def test_markdown_plan_json_values_round_trip_exactly(tmp_path: Path, separator: str, command: str, text: str) -> None:
    steps = [{"shell": {"command": command}}, {"input": {"by_id": "field", "text": text}}, {"back": {}}]
    cell = separator.join(json.dumps(step, ensure_ascii=False) for step in steps)
    path = _write_plan(tmp_path, cell.replace("|", r"\|"))

    parsed = parse_test_plan(path)
    actual = [json.loads(step) for step in iter_plan_steps(parsed.cases[0].steps)]
    assert actual == steps
    assert actual[0]["shell"]["command"] == command
    assert actual[1]["input"]["text"] == text
    assert validate_plan_contract(path) is None
    assert parsed.cases[0].name == "name next"
    assert parsed.cases[0].preconditions == '已有"a b"'
    assert parsed.cases[0].expected == "expected next"


def test_markdown_breaks_outside_json_strings_keep_existing_behavior(tmp_path: Path) -> None:
    path = _write_plan(tmp_path, '{"input":<br/>{"by_id":"field","text":"a<br/>b"}};点击"a<br/>b"')
    case = parse_test_plan(path).cases[0]
    steps = iter_plan_steps(case.steps)
    assert json.loads(steps[0]) == {"input": {"by_id": "field", "text": "a<br/>b"}}
    assert steps[1] == '点击"a b"'


def test_markdown_break_is_not_a_new_step_separator(tmp_path: Path) -> None:
    path = _write_plan(tmp_path, '{"back":{}}<br/>{"home":{}}')
    case = parse_test_plan(path).cases[0]
    assert case.steps == '{"back":{}} {"home":{}}'
    assert len(iter_plan_steps(case.steps)) == 1
    rejection = validate_plan_contract(path)
    assert rejection is not None and rejection.code == "contract.invalid_step"


def test_ordinary_markdown_quotes_and_other_break_spellings_are_unchanged(tmp_path: Path) -> None:
    path = _write_plan(tmp_path, '点击"a<br/>b"；返回<br>主页<br />')
    assert parse_test_plan(path).cases[0].steps == '点击"a b"；返回<br>主页<br />'


def test_non_step_json_shaped_descriptions_still_replace_markdown_breaks(tmp_path: Path) -> None:
    description = '{"text":"a<br/>b"}'
    path = _write_plan(tmp_path, '{"input":{"by_id":"field","text":"a<br/>b"}}',
                       name=description, preconditions=description, expected=description)
    case = parse_test_plan(path).cases[0]
    assert case.name == case.preconditions == case.expected == '{"text":"a b"}'
    assert json.loads(case.steps)["input"]["text"] == "a<br/>b"


@pytest.mark.parametrize("wrapper", ["whole", "first", "last", "each"])
@pytest.mark.parametrize("opening,closing", [("```json ", "```"), ("```", "```"), ("`", "`"), ("``", "``")])
def test_existing_json_fences_and_mixed_step_wrappers_preserve_payloads(
    tmp_path: Path, wrapper: str, opening: str, closing: str,
) -> None:
    steps = [{"shell": {"command": "printf '%s' '<br/>'"}},
             {"input": {"by_id": "field", "text": r'escaped\"<br/>backslash\\'}}]
    first, last = (json.dumps(step, ensure_ascii=False) for step in steps)
    def fence(value: str) -> str:
        return opening + value + closing
    if wrapper == "whole":
        cell = fence(first + ";" + last)
    else:
        cell = (fence(first) if wrapper in {"first", "each"} else first) + ";" + (fence(last) if wrapper in {"last", "each"} else last)
    path = _write_plan(tmp_path, cell)
    parsed = parse_test_plan(path)
    assert [json.loads(step) for step in iter_plan_steps(parsed.cases[0].steps)] == steps
    assert validate_plan_contract(path) is None


@pytest.mark.parametrize("position", ["prefix", "suffix", "both"])
@pytest.mark.parametrize("opening,closing", [("`", "`"), ("``", "``"), ("```json ", "```")])
def test_markdown_breaks_outside_wrapper_keep_existing_wrapper_removal(
    tmp_path: Path, position: str, opening: str, closing: str,
) -> None:
    step = {"shell": {"command": "printf '%s' '<br/>'"}}
    body = json.dumps(step, ensure_ascii=False)
    cell = ("<br/>" if position in {"prefix", "both"} else "") + opening + body + closing + ("<br/>" if position in {"suffix", "both"} else "")
    path = _write_plan(tmp_path, cell)
    case = parse_test_plan(path).cases[0]
    assert case.steps == body
    assert json.loads(case.steps) == step
    assert validate_plan_contract(path) is None


@pytest.mark.parametrize("opening,closing", [
    ("``` json ", "```"), ("```<br/>json ", "```"),
    ("``` <br/> JSON ", "```"), ("```` json ", "````"),
])
@pytest.mark.parametrize("root", ["shell", "input"])
def test_existing_mixed_fence_language_prefixes_preserve_json_values(
    tmp_path: Path, opening: str, closing: str, root: str,
) -> None:
    step = ({"shell": {"command": "printf '%s' '<br/>'"}} if root == "shell"
            else {"input": {"by_id": "field", "text": r'escaped\"<br/>tail\\'}})
    cell = '{"back":{}};' + opening + json.dumps(step) + closing + '；{"home":{}}'
    path = _write_plan(tmp_path, cell)
    case = parse_test_plan(path).cases[0]
    assert [json.loads(part) for part in iter_plan_steps(case.steps)] == [{"back": {}}, step, {"home": {}}]
    assert validate_plan_contract(path) is None
