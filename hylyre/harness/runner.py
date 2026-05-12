"""Report/trace verification harness (L5)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from hylyre.scenario.plan_parse import parse_test_plan

_CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"


def verify_report(report: Path | str, trace: Path | str, plan: Path | str) -> bool:
    """Verify artifacts against Hylyre contracts. Returns True or raises ValueError."""
    rpath = Path(report)
    tpath = Path(trace)
    ppath = Path(plan)
    report_text = rpath.read_text(encoding="utf-8")
    trace_data = json.loads(tpath.read_text(encoding="utf-8"))
    sections = _load_report_contract()

    _validate_trace_schema(trace_data)
    _validate_report_headings(report_text, sections["report_required_sections"])
    statuses = sections["execution_status_values"]
    verdicts = set(sections["verdict_values"])
    ids_status_ac = _parse_execution_table(report_text, statuses)
    _validate_verdict(report_text, verdicts)
    _validate_plan_report_ids(ppath, ids_status_ac)
    _trace_matches_plan(trace_data, ids_status_ac)
    return True


def _load_report_contract() -> dict[str, Any]:
    ypath = _CONTRACTS / "report-sections.yaml"
    data = yaml.safe_load(ypath.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("report-sections.yaml invalid")
    return data


def _validate_trace_schema(trace_data: dict[str, Any]) -> None:
    if trace_data.get("schema_version") == "0.2-p4" and not trace_data.get("cases"):
        raise ValueError("trace.json schema_version 0.2-p4 requires non-empty cases[]")
    schema_path = _CONTRACTS / "output-schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(trace_data), key=lambda e: e.path)
    if errors:
        msg = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
        raise ValueError(f"trace.json schema: {msg}")


def _validate_report_headings(report: str, required: list[str]) -> None:
    for title in required:
        if not re.search(rf"^##\s+{re.escape(title)}\s*$", report, re.MULTILINE):
            raise ValueError(f"test-report.md missing required section heading: ## {title}")


def _parse_execution_table(
    report: str,
    allowed_statuses: list[str],
) -> dict[str, tuple[str, str]]:
    """Map case_id -> (status, ac_ref) from 测试执行结果 table."""
    m = re.search(r"^##\s+测试执行结果\s*$", report, re.MULTILINE)
    if not m:
        raise ValueError("No ## 测试执行结果 section")
    rest = report[m.end() :]
    lines = rest.splitlines()
    table_lines: list[str] = []
    for line in lines:
        if "|" in line and line.strip().startswith("|"):
            table_lines.append(line)
        elif table_lines and line.strip() == "":
            break
        elif table_lines and line.startswith("#"):
            break
    if len(table_lines) < 2:
        raise ValueError("测试执行结果 has no markdown table")

    header = _split_md_row(table_lines[0])
    if "状态" not in header:
        raise ValueError("Execution table missing 状态 column")
    idx_id = header.index("用例编号")
    idx_ac = header.index("关联 AC")
    idx_status = header.index("状态")

    out: dict[str, tuple[str, str]] = {}
    for row_line in table_lines[2:]:
        cells = _split_md_row(row_line)
        if len(cells) <= max(idx_id, idx_ac, idx_status):
            continue
        cid = cells[idx_id].strip()
        status = cells[idx_status].strip()
        ac = cells[idx_ac].strip()
        if not cid or cid.startswith("---"):
            continue
        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid execution status {status!r} for case {cid}; "
                f"allowed: {allowed_statuses}"
            )
        if not ac:
            raise ValueError(f"关联 AC empty for case {cid}")
        out[cid] = (status, ac)
    if not out:
        raise ValueError("No execution rows parsed")
    return out


def _split_md_row(line: str) -> list[str]:
    s = line.strip().strip("|")
    return [c.strip() for c in s.split("|")]


def _validate_verdict(report: str, verdicts: set[str]) -> None:
    m = re.search(r"^##\s+结论\s*$", report, re.MULTILINE)
    if not m:
        raise ValueError("No ## 结论 section")
    rest = report[m.end() :]
    chunk = rest.split("\n##")[0]
    if not any(v in chunk for v in verdicts):
        raise ValueError(
            f"结论 must mention one of {sorted(verdicts)}; got:\n{chunk[:400]!r}"
        )


def _validate_plan_report_ids(
    plan_path: Path,
    report_cases: dict[str, tuple[str, str]],
) -> None:
    parsed = parse_test_plan(plan_path)
    plan_ids = {c.case_id for c in parsed.cases}
    report_ids = set(report_cases.keys())
    missing = plan_ids - report_ids
    if missing:
        raise ValueError(
            f"Report table missing plan cases: {sorted(missing)}"
        )
    extra = report_ids - plan_ids
    if extra:
        raise ValueError(
            f"Report table has unknown case ids vs plan: {sorted(extra)}"
        )


def _trace_matches_plan(
    trace_data: dict[str, Any],
    report_cases: dict[str, tuple[str, str]],
) -> None:
    cases = trace_data.get("cases")
    if not isinstance(cases, list):
        return
    for entry in cases:
        if not isinstance(entry, dict):
            continue
        cid = entry.get("id")
        st = entry.get("status")
        if cid in report_cases and st != report_cases[cid][0]:
            raise ValueError(
                f"trace case {cid} status {st!r} != report {report_cases[cid][0]!r}"
            )

