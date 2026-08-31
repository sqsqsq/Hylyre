"""Phase 0 machine check: schema / spec / decision table / golden fixtures agree.

Covers the four Phase 0 acceptance claims that are provable without a device:

1. every ``golden/**/valid/*.json`` passes its schema node;
2. every ``golden/**/invalid/*.json`` is rejected by that node;
3. the normative registries in ``step-outcome-v1.md`` equal the schema enums;
4. every ``builder-decision-table.md`` row maps onto a golden fixture whose
   status / carrier / code (or reduced CaseResult axes) actually match.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from hylyre.contracts import (
    BUILDER_DECISION_TABLE_PATH,
    GOLDEN_DIR,
    GOLDEN_TARGETS,
    REPORT_SECTIONS_PATH,
    RESULT_PROTOCOL,
    STEP_OUTCOME_SPEC_PATH,
    TRACE_SCHEMA_V1,
    load_output_schema,
    validate_against,
)
from hylyre.contracts.reference_reducer import (
    _verify_selectors,
    reduce_case,
    run_outcome,
    tool_calls_projection,
    verify_trace,
)
from hylyre.scenario.plan_contract import PRE_RUN_REJECT_CODES

ROOT = Path(__file__).resolve().parents[2]
CROSSROW_DIR = GOLDEN_DIR / "trace" / "invalid-crossrow"

DASH = "—"


# --------------------------------------------------------------- markdown utils
ESCAPED_PIPE = "\\|"


def _split_md_row(line: str) -> list[str]:
    """Split one markdown row, honouring escaped pipes inside cells."""

    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith(ESCAPED_PIPE):
        body = body[:-1]
    return [
        cell.strip().replace(ESCAPED_PIPE, "|")
        for cell in re.split(r"(?<!\\)\|", body)
    ]


def _md_tables(text: str) -> list[list[list[str]]]:
    """Return every markdown table as a list of cell rows (header included)."""

    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = _split_md_row(stripped)
            if cells and all(set(c) <= set("-: ") for c in cells):
                continue  # separator row
            current.append(cells)
            continue
        if current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def _sections(text: str, level: str = "### ") -> dict[str, str]:
    out: dict[str, str] = {}
    title: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith(level):
            if title is not None:
                out[title] = "\n".join(buf)
            title = line[len(level) :].strip()
            buf = []
        elif title is not None:
            buf.append(line)
    if title is not None:
        out[title] = "\n".join(buf)
    return out


def _rows(table: list[list[str]]) -> list[dict[str, str]]:
    header = [h.strip("` ") for h in table[0]]
    return [dict(zip(header, row)) for row in table[1:] if len(row) == len(header)]


def _column(text: str, column: str) -> set[str]:
    found: set[str] = set()
    for table in _md_tables(text):
        for row in _rows(table):
            value = row.get(column)
            if value:
                found.add(value.strip("` "))
    return found


def _strip_code(value: str) -> str:
    return value.strip().strip("`").strip()


SPEC_TEXT = STEP_OUTCOME_SPEC_PATH.read_text(encoding="utf-8")
TABLE_TEXT = BUILDER_DECISION_TABLE_PATH.read_text(encoding="utf-8")
SCHEMA = load_output_schema()
DEFS = SCHEMA["$defs"]


def _core_enum(name: str) -> set[str]:
    return set(DEFS[name]["anyOf"][0]["enum"])


# ------------------------------------------------------------ golden fixtures
def _fixture_cases() -> list[tuple[str, str, Path]]:
    items: list[tuple[str, str, Path]] = []
    for target, pointer in GOLDEN_TARGETS.items():
        for expectation in ("valid", "invalid"):
            directory = GOLDEN_DIR / target / expectation
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                items.append((pointer, expectation, path))
    return items


FIXTURES = _fixture_cases()


def test_golden_fixture_tree_is_populated() -> None:
    assert FIXTURES, "golden fixtures are missing from the contract package"
    covered = {p.relative_to(GOLDEN_DIR).parts[0] for _, _, p in FIXTURES}
    assert covered == set(GOLDEN_TARGETS), (
        "golden directories and GOLDEN_TARGETS disagree: "
        f"{sorted(covered)} vs {sorted(GOLDEN_TARGETS)}"
    )
    for target, pointer in GOLDEN_TARGETS.items():
        if not pointer:
            continue
        assert pointer.split("/")[-1] in DEFS, f"{target} points at a missing $defs node"


@pytest.mark.parametrize(
    ("pointer", "expectation", "path"),
    FIXTURES,
    ids=[f"{e}:{p.relative_to(GOLDEN_DIR).as_posix()}" for _, e, p in FIXTURES],
)
def test_golden_fixture_matches_expectation(
    pointer: str, expectation: str, path: Path
) -> None:
    instance = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_against(pointer, instance)
    if expectation == "valid":
        assert not errors, f"{path.name} must pass the schema: {errors[:3]}"
    else:
        assert errors, f"{path.name} must be rejected by the schema"


# --------------------------------------------------------------- code registry
def test_failure_code_registry_matches_schema() -> None:
    spec = {
        _strip_code(v)
        for v in _column(_sections(SPEC_TEXT)["4.1 `failure.code`（域前缀命名空间）"], "core code")
    }
    assert spec == _core_enum("failureCode")


def test_cause_code_registry_matches_schema() -> None:
    spec = {
        _strip_code(v)
        for v in _column(_sections(SPEC_TEXT)["4.2 `cause.code`"], "core code")
    }
    assert spec == _core_enum("causeCapabilityCode") | _core_enum(
        "causeInfrastructureCode"
    )


def test_reason_code_registry_matches_schema() -> None:
    spec = {
        _strip_code(v)
        for v in _column(_sections(SPEC_TEXT)["4.3 `reason.code`"], "core code")
    }
    assert spec == _core_enum("reasonPolicyCode") | _core_enum(
        "reasonNotApplicableCode"
    )


def test_resolution_reason_code_registry_matches_schema() -> None:
    spec = {
        _strip_code(v)
        for v in _column(
            _sections(SPEC_TEXT)["4.4 `resolution.reason_code`（仅 `resolution.state=unresolvable`）"],
            "core code",
        )
    }
    assert spec == _core_enum("resolutionReasonCode")


def test_pre_run_reject_codes_match_schema_and_validator() -> None:
    assert set(DEFS["preRunRejectCode"]["enum"]) == set(PRE_RUN_REJECT_CODES)


def test_protocol_and_schema_constants_are_bound() -> None:
    assert DEFS["environmentV1"]["properties"]["result_protocol"]["const"] == (
        RESULT_PROTOCOL
    )
    assert DEFS["environmentV1"]["properties"]["trace_schema_version"]["const"] == (
        TRACE_SCHEMA_V1
    )
    assert SCHEMA["properties"]["result_protocol"]["enum"] == [RESULT_PROTOCOL]
    assert TRACE_SCHEMA_V1 in SCHEMA["properties"]["schema_version"]["enum"]


def test_spec_golden_target_table_matches_code() -> None:
    mapping: dict[str, str] = {}
    for table in _md_tables(_sections(SPEC_TEXT, "## ")["15. Golden fixtures"]):
        for row in _rows(table):
            if "<target>" in row and "schema 节点" in row:
                target = _strip_code(row["<target>"])
                node = _strip_code(row["schema 节点"])
                mapping[target] = "" if node == "schema root" else node.lstrip("#")
    assert mapping == GOLDEN_TARGETS


# ------------------------------------------------------- builder decision table
def _decision_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in _md_tables(TABLE_TEXT):
        parsed = _rows(table)
        if parsed and {"id", "status", "carrier", "code", "fixture"} <= set(parsed[0]):
            rows.extend(parsed)
    return rows


def _reducer_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in _md_tables(TABLE_TEXT):
        parsed = _rows(table)
        if parsed and {"id", "execution", "verification", "evidence", "fixture"} <= set(
            parsed[0]
        ):
            rows.extend(parsed)
    return rows


DECISION_ROWS = _decision_rows()
REDUCER_ROWS = _reducer_rows()


def test_decision_table_is_populated_and_unique() -> None:
    assert len(DECISION_ROWS) >= 30
    ids = [r["id"] for r in DECISION_ROWS] + [r["id"] for r in REDUCER_ROWS]
    assert len(ids) == len(set(ids)), "duplicate decision-table row id"
    assert REDUCER_ROWS, "reducer derivation table is missing"
    # A row whose cells fail to parse would silently drop out of the matrix.
    declared = sorted(
        int(m.group(1))
        for m in re.finditer(r"(?m)^\|\s*D-(\d+)\s*\|", TABLE_TEXT)
    )
    parsed = sorted(int(r["id"].split("-")[1]) for r in DECISION_ROWS)
    assert parsed == declared, "some decision-table rows were not parsed"
    assert declared == list(range(1, len(declared) + 1)), "decision ids must be contiguous"


def _all_steps(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, dict) and "cases" in document:
        return [s for case in document["cases"] for s in case["steps"]]
    if isinstance(document, dict) and "steps" in document:
        return list(document["steps"])
    return [document]


def _carrier_code(outcome: dict[str, Any]) -> str | None:
    status = outcome["status"]
    if status == "failed":
        return outcome["failure"]["code"]
    if status == "blocked":
        return outcome["cause"].get("code")
    if status == "skipped":
        return outcome["reason"]["code"]
    return None


@pytest.mark.parametrize(
    "row", DECISION_ROWS, ids=[r["id"] for r in DECISION_ROWS]
)
def test_decision_row_matches_its_golden_fixture(row: dict[str, str]) -> None:
    fixture = GOLDEN_DIR / _strip_code(row["fixture"])
    assert fixture.is_file(), f"{row['id']} references a missing fixture {fixture}"
    document = json.loads(fixture.read_text(encoding="utf-8"))
    status = _strip_code(row["status"])
    code = _strip_code(row["code"])
    code = None if code == DASH else code

    if status == "pre_run_reject":
        assert document["result_protocol"] == RESULT_PROTOCOL
        assert document["command_status"] == "rejected"
        assert document["phase"] == "pre_run_validation"
        assert document["rejection"]["domain"] == "contract"
        assert document["rejection"]["code"] == code
        return

    steps = _all_steps(document)
    matching = [s for s in steps if s["outcome"]["status"] == status]
    assert matching, f"{row['id']}: no step with status={status} in {fixture.name}"
    if code is not None:
        assert any(_carrier_code(s["outcome"]) == code for s in matching), (
            f"{row['id']}: no {status} step carrying code {code} in {fixture.name}"
        )


@pytest.mark.parametrize("row", REDUCER_ROWS, ids=[r["id"] for r in REDUCER_ROWS])
def test_reducer_row_is_actually_reduced_from_steps(row: dict[str, str]) -> None:
    """The declared axes must be *recomputed* from steps[], not merely echoed."""

    fixture = GOLDEN_DIR / _strip_code(row["fixture"])
    assert fixture.is_file()
    trace = json.loads(fixture.read_text(encoding="utf-8"))

    expected = {
        "execution": _strip_code(row["execution"]),
        "verification": _strip_code(row["verification"]),
        "evidence": _strip_code(row["evidence"]),
        "status": _strip_code(row["legacy status"]),
    }
    derived = [reduce_case(case) for case in trace["cases"]]
    assert expected in derived, (
        f"{row['id']}: decision-table row {expected} is not produced by reducing "
        f"any case in {fixture.name}; reduced = {derived}"
    )
    assert run_outcome(trace["cases"]) == _strip_code(row["run outcome"])


# ------------------------------------------------------------- cross-row rules
def _trace_fixtures() -> list[Path]:
    return sorted((GOLDEN_DIR / "trace" / "valid").glob("*.json"))


@pytest.mark.parametrize("path", _trace_fixtures(), ids=lambda p: p.name)
def test_valid_trace_passes_the_reference_verifier(path: Path) -> None:
    """Every valid trace must survive the full cross-row oracle."""

    trace = json.loads(path.read_text(encoding="utf-8"))
    if trace.get("schema_version") != TRACE_SCHEMA_V1:
        pytest.skip("legacy fixture kept for dispatch coverage only")
    assert verify_trace(trace) == []


@pytest.mark.parametrize("path", _trace_fixtures(), ids=lambda p: p.name)
def test_valid_trace_axes_are_reduced_not_declared(path: Path) -> None:
    """Sections 9.1-9.5: the three axes plus legacy status must recompute."""

    trace = json.loads(path.read_text(encoding="utf-8"))
    if trace.get("schema_version") != TRACE_SCHEMA_V1:
        pytest.skip("legacy fixture kept for dispatch coverage only")
    for case in trace["cases"]:
        derived = reduce_case(case)
        assert {k: case[k] for k in derived} == derived, case["id"]
    assert trace["outcome"] == run_outcome(trace["cases"])
    assert trace["tool_calls"] == tool_calls_projection(trace["cases"])


def _crossrow_fixtures() -> list[Path]:
    return sorted(CROSSROW_DIR.glob("*.json"))


def test_crossrow_bucket_is_populated() -> None:
    fixtures = _crossrow_fixtures()
    assert len(fixtures) >= 10, "cross-row negatives are the only guard on the reducer"


@pytest.mark.parametrize("path", _crossrow_fixtures(), ids=lambda p: p.name)
def test_crossrow_fixture_passes_schema_but_fails_the_verifier(path: Path) -> None:
    """The third bucket: schema-legal single objects, verifier-illegal as a set.

    If these ever pass the verifier, the cross-row layer is not running at all.
    """

    trace = json.loads(path.read_text(encoding="utf-8"))
    assert validate_against("", trace) == [], (
        f"{path.name} must be schema-valid; it exists to catch the verifier"
    )
    assert verify_trace(trace), f"{path.name} must be rejected by the verifier"


def test_bc_opencard_ledger_has_one_root_failure() -> None:
    """§3/§9: one real root failure must not be multiplied into N defects."""

    trace = json.loads(
        (GOLDEN_DIR / "trace" / "valid" / "bc-opencard-1.json").read_text(
            encoding="utf-8"
        )
    )
    steps = trace["cases"][0]["steps"]
    failed = [s for s in steps if s["outcome"]["status"] == "failed"]
    blocked = [s for s in steps if s["outcome"]["status"] == "blocked"]
    skipped = [s for s in steps if s["outcome"]["status"] == "skipped"]
    assert len(failed) == 1
    assert failed[0]["outcome"]["failure"] == {
        "domain": "selector",
        "code": "selector.not_found",
    }
    assert len(blocked) >= 1
    assert all(
        s["outcome"]["cause"] == {"type": "prior_step", "step_index": failed[0]["index"]}
        for s in blocked
    ), "blocked suffix must point directly at the root failure"
    assert not any("failure" in s["outcome"] for s in blocked + skipped)
    assert len(skipped) == 1


def test_spec_deletes_the_legacy_non_pass_failure_rule() -> None:
    """The old `status != passed -> failure_kind/failure_code` rule is retired."""

    assert re.search(r"status\s*!=\s*passed", SPEC_TEXT)
    assert "必须删除" in SPEC_TEXT


def test_golden_fixtures_are_declared_as_package_data() -> None:
    """P0-13: the protocol package must be installable and readable offline."""

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'golden/**/*.json' in pyproject
    for name in (
        "step-outcome-v1.md",
        "builder-decision-table.md",
        "output-schema.json",
        "report-sections.yaml",
    ):
        assert (GOLDEN_DIR.parent / name).is_file()


def test_contracts_readme_has_no_unshipped_doc_reference() -> None:
    """P0-13: contracts/README must not point outside the shipped package."""

    readme = (GOLDEN_DIR.parent / "README.md").read_text(encoding="utf-8")
    assert "../../docs/" not in readme


# ------------------------------------------- review round 1 follow-up coverage
def test_pre_run_reject_registry_is_separate_from_failure_codes() -> None:
    """R2 P0-1: an empty case has no legal StepResult, so it is not a failure code."""

    spec_pre_run = {
        _strip_code(v)
        for v in _column(
            _sections(SPEC_TEXT, "#### ")["4.1.1 pre-run reject code（独立注册面）"],
            "pre-run code",
        )
    }
    assert spec_pre_run == set(DEFS["preRunRejectCode"]["enum"])
    assert "contract.empty_case" not in _core_enum("failureCode")
    assert "contract.empty_case" in set(DEFS["preRunRejectCode"]["enum"])


def test_tool_call_projection_reuses_the_same_registries() -> None:
    """R2 P0-2: the projection may not classify what the ledger would reject."""

    tool_call = json.dumps(DEFS["toolCallOutcomeV1"])
    assert "domainCodeAgreement" in tool_call
    assert "reasonPolicyCode" in tool_call
    assert "reasonNotApplicableCode" in tool_call
    assert "failureCode" in tool_call


def test_report_sections_yaml_declares_the_current_protocol() -> None:
    """R2 P1-6: no parallel 0.3-p0 SSOT inside the shipped contract package."""

    import yaml

    data = yaml.safe_load(REPORT_SECTIONS_PATH.read_text(encoding="utf-8"))

    assert data["current"]["trace_schema_version"] == TRACE_SCHEMA_V1
    assert data["current"]["result_protocol"] == RESULT_PROTOCOL
    # The flat 0.3-p0 taxonomy may only exist under an explicit legacy key.
    assert "failure_kind_values" not in data
    assert "trace_schema_version" not in data
    assert data["legacy"]["0.3-p0"]["evidence_eligible"] is False
    assert data["legacy"]["0.3-p0"]["result_protocol"] is None
    assert "failure_kind_values" in data["legacy"]["0.3-p0"]

    # The current block must agree with the schema enums, not drift from them.
    assert set(data["current"]["failure_domain_values"]) == set(
        DEFS["failureDomain"]["enum"]
    )
    assert set(data["current"]["outcome_status_values"]) == {
        variant["properties"]["status"]["const"]
        for variant in DEFS["outcomeV1"]["oneOf"]
    }
    assert set(data["current"]["cause_type_values"]) == {
        variant["properties"]["type"]["const"] for variant in DEFS["causeV1"]["oneOf"]
    }
    assert set(data["current"]["reason_type_values"]) == {
        variant["properties"]["type"]["const"] for variant in DEFS["reasonV1"]["oneOf"]
    }
    assert set(data["current"]["resolution_state_values"]) == {
        variant["properties"]["state"]["const"]
        for variant in DEFS["selectorResolutionV1"]["oneOf"]
    }


def test_artifact_paths_reject_windows_absolute_and_traversal_forms() -> None:
    """R2 P1-5: the relative-path guarantee must hold on Windows too."""

    for bad in (
        r"..\a.png",
        r"\rooted\a.png",
        r"\\server\share\a.png",
        r"sub\..\..\a.png",
        r"C:\tmp\a.png",
        "/abs/a.png",
        "../a.png",
    ):
        assert validate_against(
            "/$defs/artifactRef",
            {"kind": "screenshot", "path": bad, "sha256": "0" * 64},
        ), f"{bad!r} must be rejected"
    for good in ("failures/ok.png", r"failures\ok.png", "a.png"):
        assert not validate_against(
            "/$defs/artifactRef",
            {"kind": "screenshot", "path": good, "sha256": "0" * 64},
        ), f"{good!r} must be accepted"


def test_candidate_count_exemption_matches_the_spec_clause() -> None:
    """Review round 2 P1: section 6.1's exemption must exist in the oracle too.

    A resolver may enumerate part of a virtualized list without being able to
    compute the total. The spec exempts that case from candidate_count
    recomputation; the shipped oracle must agree, or Phase 1 and Maison would
    follow two contradictory normative assets.
    """

    clause = _sections(SPEC_TEXT, "### ")["6.1 resolution 状态机不变量"]
    assert "candidate_countable=false" in clause and "豁免" in clause

    partial = {
        "id": "TC-X",
        "expected_check_mode": "empty",
        "steps": [
            {
                "index": 0,
                "kind": "touch",
                "role": "action",
                "duration_ms": 1.0,
                "device_session": True,
                "outcome": {
                    "status": "failed",
                    "failure": {
                        "domain": "selector",
                        "code": "selector.inline_unresolvable",
                    },
                },
                "selector": {
                    "request": {
                        "kind": "by_text",
                        "value": "[REDACTED]",
                        "match": "contains",
                        "constraints": {},
                    },
                    "resolution": {
                        "state": "unresolvable",
                        "candidate_count": None,
                        "selected": None,
                        "candidates": [
                            {"id": "row_a", "bounds": None},
                            {"id": "row_b", "bounds": None},
                        ],
                        "reason_code": "selector.resolver_unsupported_form",
                        "facts": {
                            "dump_status": "available",
                            "request_complete": True,
                            "resolver_entered": True,
                            "candidate_countable": False,
                            "provider_probe": {
                                "probe_status": "unsupported",
                                "probe_source": "resolver.virtual_list_total",
                            },
                        },
                    },
                },
                "artifacts": [
                    {
                        "kind": "ui_dump",
                        "path": "failures/x.json",
                        "sha256": "0" * 64,
                    }
                ],
                "diagnostic": None,
                "extensions": {},
            }
        ],
    }
    # Schema-legal, and exempt from recomputation.
    assert validate_against("/$defs/stepResultV1", partial["steps"][0]) == []
    assert _verify_selectors(partial) == []

    # The exemption is scoped: a countable resolution still recomputes.
    countable = json.loads(json.dumps(partial))
    resolution = countable["steps"][0]["selector"]["resolution"]
    resolution["facts"]["candidate_countable"] = True
    resolution["candidate_count"] = 7
    assert _verify_selectors(countable)
