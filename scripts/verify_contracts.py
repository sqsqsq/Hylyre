#!/usr/bin/env python
"""Phase 0 contract-freeze machine check (Step Outcome Protocol v1).

Runs, in one command, the four checks the freeze package must survive:

1. ``output-schema.json`` is a valid draft 2020-12 schema and every
   ``$defs`` node referenced by the contract package exists;
2. every ``golden/**/valid/*.json`` passes its schema node and every
   ``golden/**/invalid/*.json`` is rejected by it;
3. the code registries in ``step-outcome-v1.md`` equal the schema enums, and
   every ``builder-decision-table.md`` row maps onto a matching fixture;
4. ``hylyre run --plan`` rejects a contract-invalid plan with exactly one
   stdout JSON object, exit code 2, no device call and no trace/report write.

Usage::

    python scripts/verify_contracts.py            # all checks
    python scripts/verify_contracts.py --no-cli   # skip the subprocess check
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hylyre.contracts import (  # noqa: E402
    CROSSROW_DIR,
    GOLDEN_DIR,
    GOLDEN_TARGETS,
    OUTPUT_SCHEMA_PATH,
    REPORT_SECTIONS_PATH,
    RESULT_PROTOCOL,
    TRACE_SCHEMA_V1,
    load_output_schema,
    validate_against,
)
from hylyre.contracts.reference_reducer import verify_trace  # noqa: E402

PLAN_HEADER = """# pre-run reject fixture

## 测试用例清单

| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |
| --- | --- | --- | --- | --- | --- | --- |
"""

PLAN_ROWS: dict[str, str] = {
    "contract.empty_case": "| TC-001 | 空步骤 | - |  | 首页展示 | P0 | AC-01 |",
    "contract.invalid_step": (
        '| TC-002 | 多根键 | - | {"touch":{"by_id":"a"},"back":{}} | x | P0 | AC-02 |'
    ),
    "contract.invalid_match": (
        '| TC-003 | 非法 match | - | {"touch":{"by_text":"x","match":"regex"}} '
        "| x | P0 | AC-03 |"
    ),
    "contract.invalid_selector": (
        '| TC-004 | 双目标 | - | {"touch":{"by_text":"x","by_id":"y"}} | x | P0 | AC-04 |'
    ),
}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.counts: dict[str, int] = {}

    def ok(self, bucket: str) -> None:
        self.counts[bucket] = self.counts.get(bucket, 0) + 1

    def fail(self, message: str) -> None:
        self.failures.append(message)


def check_schema(report: Report) -> None:
    from jsonschema import Draft202012Validator

    schema = load_output_schema()
    Draft202012Validator.check_schema(schema)
    report.ok("schema")
    defs = schema["$defs"]
    for target, pointer in GOLDEN_TARGETS.items():
        if pointer and pointer.split("/")[-1] not in defs:
            report.fail(f"golden target {target!r} points at missing node {pointer}")
        else:
            report.ok("schema-node")


def check_fixtures(report: Report) -> None:
    for target, pointer in GOLDEN_TARGETS.items():
        for expectation in ("valid", "invalid"):
            directory = GOLDEN_DIR / target / expectation
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                rel = path.relative_to(GOLDEN_DIR).as_posix()
                errors = validate_against(
                    pointer, json.loads(path.read_text(encoding="utf-8"))
                )
                if expectation == "valid" and errors:
                    report.fail(f"{rel} should PASS: {errors[:2]}")
                elif expectation == "invalid" and not errors:
                    report.fail(f"{rel} should FAIL but passed")
                else:
                    report.ok(f"fixture-{expectation}")


def check_crossrow(report: Report) -> None:
    """Cross-row rules JSON Schema cannot express (reducer/verifier oracle)."""

    for path in sorted((GOLDEN_DIR / "trace" / "valid").glob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        if trace.get("schema_version") != TRACE_SCHEMA_V1:
            continue
        problems = verify_trace(trace)
        if problems:
            report.fail(f"trace/valid/{path.name}: {problems[:2]}")
        else:
            report.ok("crossrow-valid")

    fixtures = sorted(CROSSROW_DIR.glob("*.json"))
    if len(fixtures) < 10:
        report.fail(
            f"only {len(fixtures)} cross-row negatives; the reducer would be unguarded"
        )
    for path in fixtures:
        trace = json.loads(path.read_text(encoding="utf-8"))
        schema_errors = validate_against("", trace)
        if schema_errors:
            report.fail(
                f"invalid-crossrow/{path.name} must be schema-valid: {schema_errors[:1]}"
            )
        elif not verify_trace(trace):
            report.fail(f"invalid-crossrow/{path.name} was NOT rejected by the verifier")
        else:
            report.ok("crossrow-invalid")


def check_report_sections(report: Report) -> None:
    """The shipped YAML must not carry a parallel 0.3-p0 SSOT."""

    import yaml

    data = yaml.safe_load(REPORT_SECTIONS_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []
    if data.get("current", {}).get("trace_schema_version") != TRACE_SCHEMA_V1:
        problems.append("current.trace_schema_version is not 0.4-p0")
    if data.get("current", {}).get("result_protocol") != RESULT_PROTOCOL:
        problems.append("current.result_protocol is not the v1 protocol")
    for leaked in ("trace_schema_version", "failure_kind_values"):
        if leaked in data:
            problems.append(f"top-level {leaked!r} is a legacy field; move it under legacy:")
    if data.get("legacy", {}).get("0.3-p0", {}).get("evidence_eligible") is not False:
        problems.append("legacy 0.3-p0 must be marked evidence_eligible: false")
    if problems:
        report.fail("report-sections.yaml: " + "; ".join(problems))
    else:
        report.ok("report-sections")


def check_consistency(report: Report) -> None:
    """Delegate the spec/table/fixture cross-checks to their pytest module."""

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/schema/test_step_outcome_contract.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        report.fail("spec/decision-table/fixture consistency suite failed:\n" + result.stdout[-4000:])
    else:
        report.ok("consistency")


def check_pre_run_reject(report: Report) -> None:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for code, row in PLAN_ROWS.items():
            plan = tmpdir / f"{code.replace('.', '_')}.md"
            plan.write_text(PLAN_HEADER + row + "\n", encoding="utf-8")
            report_out = tmpdir / f"{code}.report.md"
            trace_out = tmpdir / f"{code}.trace.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hylyre",
                    "run",
                    "--plan",
                    str(plan),
                    "--feature",
                    "phase0",
                    "--report-out",
                    str(report_out),
                    "--trace-out",
                    str(trace_out),
                    "--use-fakes",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            problems: list[str] = []
            if proc.returncode != 2:
                problems.append(f"exit={proc.returncode} (expected 2)")
            try:
                envelope = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                problems.append(f"stdout is not a single JSON object: {exc}")
                envelope = None
            if envelope is not None:
                errors = validate_against("/$defs/pre_run_reject", envelope)
                if errors:
                    problems.append(f"envelope schema errors: {errors[:2]}")
                if envelope.get("result_protocol") != RESULT_PROTOCOL:
                    problems.append("wrong result_protocol")
                if envelope.get("rejection", {}).get("code") != code:
                    problems.append(
                        f"code={envelope.get('rejection', {}).get('code')} (expected {code})"
                    )
            if report_out.exists() or trace_out.exists():
                problems.append("trace/report was created by a rejected run")
            if problems:
                report.fail(f"pre-run reject {code}: " + "; ".join(problems))
            else:
                report.ok("pre-run-reject")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-cli",
        action="store_true",
        help="skip the pre-run reject subprocess check",
    )
    args = parser.parse_args()

    report = Report()
    print(f"schema : {OUTPUT_SCHEMA_PATH.relative_to(ROOT).as_posix()}")
    print(f"golden : {GOLDEN_DIR.relative_to(ROOT).as_posix()}")
    check_schema(report)
    check_fixtures(report)
    check_crossrow(report)
    check_report_sections(report)
    check_consistency(report)
    if not args.no_cli:
        check_pre_run_reject(report)

    print()
    for bucket, count in sorted(report.counts.items()):
        print(f"  {bucket:<18} {count}")
    if report.failures:
        print(f"\nFAILED ({len(report.failures)}):")
        for failure in report.failures:
            print(f"  - {failure}")
        return 1
    print("\nPhase 0 contract freeze: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
