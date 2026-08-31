"""P0-7B: pre-run plan contract reject is a protocol decision, not a crash.

Proves the four Phase 0 claims that need the real CLI:

* stdout carries exactly one schema-valid ``pre_run_reject`` JSON object;
* the exit code is fixed at ``2``;
* no device is contacted;
* ``--trace-out`` / ``--report-out`` are neither created nor rewritten.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hylyre.cli.__main__ import app
from hylyre.contracts import RESULT_PROTOCOL, validate_against
from hylyre.scenario.plan_contract import (
    validate_plan_contract,
    validate_steps_contract,
)

ROOT = Path(__file__).resolve().parents[2]
PRE_RUN_REJECT_POINTER = "/$defs/pre_run_reject"

_PLAN_HEADER = """# fixture

## 测试用例清单

| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |
| --- | --- | --- | --- | --- | --- | --- |
"""


def _plan(tmp_path: Path, *rows: str, name: str = "plan.md") -> Path:
    path = tmp_path / name
    path.write_text(_PLAN_HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


EMPTY_CASE_ROW = "| TC-001 | 空步骤 | - |  | 首页展示 | P0 | AC-01 |"
INVALID_STEP_ROW = (
    '| TC-002 | 多根键 | - | {"touch":{"by_id":"a"},"back":{}} | x | P0 | AC-02 |'
)
INVALID_MATCH_ROW = (
    '| TC-003 | 非法 match | - | {"touch":{"by_text":"x","match":"regex"}} | x | P0 | AC-03 |'
)
INVALID_SELECTOR_ROW = (
    '| TC-004 | 双目标 | - | {"touch":{"by_text":"x","by_id":"y"}} | x | P0 | AC-04 |'
)
VALID_ROW = '| TC-OK | ok | - | {"touch":{"by_id":"a"}} | x | P0 | AC-OK |'


# ------------------------------------------------------------------- validator
@pytest.mark.parametrize(
    ("row", "code", "case_id"),
    [
        (EMPTY_CASE_ROW, "contract.empty_case", "TC-001"),
        (INVALID_STEP_ROW, "contract.invalid_step", "TC-002"),
        (INVALID_MATCH_ROW, "contract.invalid_match", "TC-003"),
        (INVALID_SELECTOR_ROW, "contract.invalid_selector", "TC-004"),
    ],
)
def test_plan_validator_emits_registered_contract_code(
    tmp_path: Path, row: str, code: str, case_id: str
) -> None:
    rejection = validate_plan_contract(_plan(tmp_path, row))
    assert rejection is not None
    assert rejection.code == code
    assert rejection.case_id == case_id
    assert not validate_against(PRE_RUN_REJECT_POINTER, rejection.envelope())


def test_plan_validator_accepts_contract_valid_plans(tmp_path: Path) -> None:
    assert validate_plan_contract(_plan(tmp_path, VALID_ROW)) is None
    for fixture in ("mock-test-plan.md", "json-steps-test-plan.md"):
        assert validate_plan_contract(ROOT / "tests" / "e2e" / "fixtures" / fixture) is None


def test_plan_validator_returns_first_violation_in_stable_order(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path, VALID_ROW, INVALID_MATCH_ROW, EMPTY_CASE_ROW)
    rejection = validate_plan_contract(plan)
    assert rejection is not None
    assert rejection.case_id == "TC-003"
    assert rejection.step_index == 0


def test_steps_validator_rejects_invalid_batch() -> None:
    rejection = validate_steps_contract([{"touch": {"by_id": "a"}, "back": {}}])
    assert rejection is not None
    assert rejection.code == "contract.invalid_step"
    assert rejection.path == "steps[0]"
    assert not validate_against(PRE_RUN_REJECT_POINTER, rejection.envelope())
    assert validate_steps_contract([{"touch": {"by_id": "a"}}]) is None


# ------------------------------------------------------------------- CLI shape
def _run_cli(plan: Path, tmp_path: Path, *, use_fakes: bool = True):
    args = [
        sys.executable,
        "-m",
        "hylyre",
        "run",
        "--plan",
        str(plan),
        "--feature",
        "pre-run-reject",
        "--report-out",
        str(tmp_path / "report.md"),
        "--trace-out",
        str(tmp_path / "trace.json"),
    ]
    if use_fakes:
        args.append("--use-fakes")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


@pytest.mark.parametrize(
    ("row", "code"),
    [
        (EMPTY_CASE_ROW, "contract.empty_case"),
        (INVALID_STEP_ROW, "contract.invalid_step"),
        (INVALID_MATCH_ROW, "contract.invalid_match"),
        (INVALID_SELECTOR_ROW, "contract.invalid_selector"),
    ],
)
def test_cli_reject_is_single_stdout_json_with_exit_2(
    tmp_path: Path, row: str, code: str
) -> None:
    result = _run_cli(_plan(tmp_path, row), tmp_path)

    assert result.returncode == 2
    envelope = json.loads(result.stdout)  # single object; extra output would raise
    assert result.stdout.strip().count("\n") == 0
    assert not validate_against(PRE_RUN_REJECT_POINTER, envelope)
    assert envelope["result_protocol"] == RESULT_PROTOCOL
    assert envelope["command_status"] == "rejected"
    assert envelope["phase"] == "pre_run_validation"
    assert envelope["rejection"]["domain"] == "contract"
    assert envelope["rejection"]["code"] == code

    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "trace.json").exists()


def test_cli_reject_does_not_rewrite_existing_artifacts(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    report.write_text("PREVIOUS REPORT", encoding="utf-8")
    trace.write_text('{"schema_version": "0.3-p0"}', encoding="utf-8")

    result = _run_cli(_plan(tmp_path, EMPTY_CASE_ROW), tmp_path)

    assert result.returncode == 2
    assert report.read_text(encoding="utf-8") == "PREVIOUS REPORT"
    assert trace.read_text(encoding="utf-8") == '{"schema_version": "0.3-p0"}'


def test_cli_reject_contacts_no_device(tmp_path: Path, monkeypatch) -> None:
    """The real-device path must not build an agent before validation."""

    import hylyre.wiring as wiring

    calls: list[str] = []

    def _boom(**_kwargs):  # pragma: no cover - must never run
        calls.append("agent")
        raise AssertionError("pre-run reject must not construct a device agent")

    monkeypatch.setattr(wiring, "create_hypium_agent_with_env_vlm", _boom)
    monkeypatch.setattr(wiring, "create_hypium_agent", _boom)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--plan",
            str(_plan(tmp_path, EMPTY_CASE_ROW)),
            "--feature",
            "pre-run-reject",
            "--report-out",
            str(tmp_path / "report.md"),
            "--trace-out",
            str(tmp_path / "trace.json"),
        ],
    )
    assert result.exit_code == 2
    assert calls == []
    assert not (tmp_path / "trace.json").exists()


def _run_steps_cli(steps_file: Path, tmp_path: Path):
    """`run --steps-file` in report mode — the second P0-7B entry."""

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "hylyre",
            "run",
            "--steps-file",
            str(steps_file),
            "--feature",
            "pre-run-reject-steps",
            "--report-out",
            str(tmp_path / "report.md"),
            "--trace-out",
            str(tmp_path / "trace.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


@pytest.mark.parametrize(
    ("payload", "code", "path"),
    [
        ('[{"touch":{"by_id":"a"},"back":{}}]', "contract.invalid_step", "steps[0]"),
        (
            '[{"touch":{"by_text":"x","match":"regex"}}]',
            "contract.invalid_match",
            "steps[0].touch.match",
        ),
        (
            '[{"back":{}},{"touch":{"by_text":"x","by_id":"y"}}]',
            "contract.invalid_selector",
            "steps[1].touch",
        ),
        ("[]", "contract.empty_case", "steps"),
    ],
)
def test_steps_file_report_mode_reject_is_single_stdout_json_with_exit_2(
    tmp_path: Path, payload: str, code: str, path: str
) -> None:
    steps_file = tmp_path / "steps.json"
    steps_file.write_text(payload, encoding="utf-8")

    result = _run_steps_cli(steps_file, tmp_path)

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert result.stdout.strip().count("\n") == 0
    assert not validate_against(PRE_RUN_REJECT_POINTER, envelope)
    assert envelope["result_protocol"] == RESULT_PROTOCOL
    assert envelope["rejection"]["code"] == code
    assert envelope["rejection"]["path"] == path
    assert envelope["rejection"]["case_id"] is None

    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "trace.json").exists()


def test_steps_file_reject_does_not_rewrite_existing_artifacts(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    trace = tmp_path / "trace.json"
    report.write_text("PREVIOUS REPORT", encoding="utf-8")
    trace.write_text('{"schema_version": "0.3-p0"}', encoding="utf-8")
    steps_file = tmp_path / "steps.json"
    steps_file.write_text('[{"touch":{"by_id":"a"},"back":{}}]', encoding="utf-8")

    result = _run_steps_cli(steps_file, tmp_path)

    assert result.returncode == 2
    assert report.read_text(encoding="utf-8") == "PREVIOUS REPORT"
    assert trace.read_text(encoding="utf-8") == '{"schema_version": "0.3-p0"}'


def test_steps_file_reject_contacts_no_device(tmp_path: Path, monkeypatch) -> None:
    import hylyre.cli.commands.loop_cmd as loop_cmd
    import hylyre.wiring as wiring

    calls: list[str] = []

    def _boom(*_args, **_kwargs):  # pragma: no cover - must never run
        calls.append("agent")
        raise AssertionError("pre-run reject must not construct a device agent")

    monkeypatch.setattr(wiring, "create_hypium_agent_with_env_vlm", _boom)
    monkeypatch.setattr(wiring, "create_hypium_agent", _boom)
    monkeypatch.setattr(loop_cmd, "_with_hypium_agent", _boom)

    steps_file = tmp_path / "steps.json"
    steps_file.write_text('[{"touch":{"by_id":"a"},"back":{}}]', encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--steps-file",
            str(steps_file),
            "--feature",
            "pre-run-reject-steps",
            "--report-out",
            str(tmp_path / "report.md"),
            "--trace-out",
            str(tmp_path / "trace.json"),
        ],
    )
    assert result.exit_code == 2
    assert calls == []
    assert not (tmp_path / "trace.json").exists()


def test_unparseable_steps_file_is_not_a_protocol_reject(tmp_path: Path) -> None:
    """exit=2 alone is not a reject signal; the envelope is."""

    steps_file = tmp_path / "steps.json"
    steps_file.write_text("{ not json", encoding="utf-8")

    result = _run_steps_cli(steps_file, tmp_path)

    assert '"command_status"' not in result.stdout
    assert not (tmp_path / "trace.json").exists()


def test_contract_valid_plan_still_runs_and_writes_artifacts(tmp_path: Path) -> None:
    result = _run_cli(
        ROOT / "tests" / "e2e" / "fixtures" / "mock-test-plan.md", tmp_path
    )
    assert result.returncode == 0
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "trace.json").is_file()


def test_unparseable_plan_is_not_a_protocol_reject(tmp_path: Path) -> None:
    """Only P0-7B rejects use the envelope; other failures stay crash-classified."""

    broken = tmp_path / "broken.md"
    broken.write_text("# no case table here\n", encoding="utf-8")

    result = _run_cli(broken, tmp_path)

    assert result.returncode != 0
    assert result.returncode != 2
    assert '"command_status"' not in result.stdout
    assert not (tmp_path / "trace.json").exists()
