"""Phase 1 conformance: the implementation matches the frozen Phase 0 contract.

Three layers, matching the frozen conformance plan (no entry x scenario
cartesian product):

1. builder / schema / reducer / verifier against the golden fixtures;
2. release-critical entries (real plan, fake, steps-file/batch) over the key
   positive and negative scenarios, proving nothing bypasses the builder;
3. one end-to-end smoke per non-critical entry (atomic CLI, MCP, session).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.cli.commands import loop_cmd, steps_cmd
from hylyre.contracts import (
    CROSSROW_DIR,
    GOLDEN_DIR,
    RESULT_PROTOCOL,
    TRACE_SCHEMA_V1,
    validate_against,
)
from hylyre.contracts import reference_reducer
from hylyre.harness.runner import trace_schema_kind, verify_report
from hylyre.report.emit import write_run_artifacts
from hylyre.scenario.reducer import reduce_case_axes, run_outcome, tool_calls_projection
from hylyre.scenario.results import StepResult
from hylyre.scenario.runner import ScenarioRunner

from tests.contract.fakes.fake_ui_driver import FakeUiDriver

PLAN_HEADER = (
    "# fixture\n\n## 测试用例清单\n\n"
    "| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |\n"
    "| --- | --- | --- | --- | --- | --- | --- |\n"
)


def _plan(path: Path, *rows: str) -> Path:
    path.write_text(PLAN_HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def _node(attrs: dict, *children: dict) -> dict:
    return {"attributes": attrs, "children": list(children)}


def _root(*children: dict) -> dict:
    return _node({"type": "Root", "bounds": "[0,0][500,800]"}, *children)


def _steps_from(raw: dict) -> list[StepResult]:
    return [
        StepResult(
            index=int(s["index"]),
            kind=s["kind"],
            role=s["role"],
            duration_ms=float(s.get("duration_ms", 0.0)),
            device_session=bool(s.get("device_session", False)),
            outcome=s["outcome"],
            selector=s.get("selector"),
            artifacts=tuple(s.get("artifacts") or ()),
            diagnostic=s.get("diagnostic"),
            extensions=dict(s.get("extensions") or {}),
        )
        for s in raw["steps"]
    ]


# ---------------------------------------------------------------- layer 1
def _valid_traces() -> list[Path]:
    return [
        p
        for p in sorted((GOLDEN_DIR / "trace" / "valid").glob("*.json"))
        if json.loads(p.read_text(encoding="utf-8")).get("schema_version")
        == TRACE_SCHEMA_V1
    ]


@pytest.mark.parametrize("path", _valid_traces(), ids=lambda p: p.name)
def test_production_reducer_agrees_with_the_shipped_oracle(path: Path) -> None:
    """The production reducer and the normative oracle must never diverge."""

    trace = json.loads(path.read_text(encoding="utf-8"))
    for case in trace["cases"]:
        derived = reduce_case_axes(
            _steps_from(case),
            expected_check_mode=case["expected_check_mode"],
            case_id=case["id"],
        )
        assert derived == reference_reducer.reduce_case(case)
        assert derived == {k: case[k] for k in derived}


@pytest.mark.parametrize("path", _valid_traces(), ids=lambda p: p.name)
def test_production_projection_agrees_with_the_oracle(path: Path) -> None:
    trace = json.loads(path.read_text(encoding="utf-8"))
    assert reference_reducer.tool_calls_projection(trace["cases"]) == trace["tool_calls"]


@pytest.mark.parametrize(
    "path", sorted(CROSSROW_DIR.glob("*.json")), ids=lambda p: p.name
)
def test_production_verifier_rejects_every_crossrow_negative(path: Path) -> None:
    """A tampered derivation must be rejected by the shipped verify path too."""

    trace = json.loads(path.read_text(encoding="utf-8"))
    assert validate_against("", trace) == [], "must be schema-valid by construction"
    assert reference_reducer.verify_trace(trace)


# ---------------------------------------------------------------- layer 2
@pytest.mark.asyncio
async def test_real_plan_entry_emits_conformant_trace(tmp_path: Path) -> None:
    """Root failure + blocked suffix + policy-skipped expected, end to end."""

    tree = _root(_node({"type": "Button", "id": "ok", "bounds": "[0,0][10,10]"}))
    plan = _plan(
        tmp_path / "plan.md",
        '| TC-ROOT | root | | {"touch":{"by_id":"ok"}};'
        '{"touch":{"by_text":"missing"}};{"wait":{"seconds":0}} | 首页 | P0 | AC-1 |',
    )
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        plan,
        feature="conformance",
        check_expected=True,
    )
    report = tmp_path / "r.md"
    trace = tmp_path / "t.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)

    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data["schema_version"] == TRACE_SCHEMA_V1
    assert data["result_protocol"] == RESULT_PROTOCOL
    assert validate_against("", data) == []
    assert reference_reducer.verify_trace(data) == []

    steps = data["cases"][0]["steps"]
    failed = [s for s in steps if s["outcome"]["status"] == "failed"]
    blocked = [s for s in steps if s["outcome"]["status"] == "blocked"]
    skipped = [s for s in steps if s["outcome"]["status"] == "skipped"]

    # Exactly one routable root event, and the suffix points at it without
    # inheriting its classification.
    assert len(failed) == 1
    assert failed[0]["outcome"]["failure"]["domain"] == "selector"
    assert blocked
    for step in blocked:
        assert step["outcome"]["cause"] == {
            "type": "prior_step",
            "step_index": failed[0]["index"],
        }
        assert "failure" not in step["outcome"]
    for step in skipped:
        assert "failure" not in step["outcome"]


def test_fake_entry_emits_conformant_trace(tmp_path: Path) -> None:
    plan = Path(__file__).parents[1] / "e2e" / "fixtures" / "mock-test-plan.md"
    result = ScenarioRunner(use_fakes=True).run_plan_file(plan, feature="fake")
    report = tmp_path / "r.md"
    trace = tmp_path / "t.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)
    assert verify_report(report, trace, plan)

    data = json.loads(trace.read_text(encoding="utf-8"))
    assert validate_against("", data) == []
    assert reference_reducer.verify_trace(data) == []
    # The stub never claims device evidence.
    for case in data["cases"]:
        for step in case["steps"]:
            assert step["device_session"] is False


@pytest.mark.asyncio
async def test_batch_entry_rows_are_builder_output() -> None:
    tree = _root(_node({"type": "Button", "id": "ok", "bounds": "[0,0][10,10]"}))
    batch = await steps_cmd.run_steps_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        [{"touch": {"by_id": "ok"}}, {"touch": {"by_text": "missing"}}, {"wait": {"seconds": 0}}],
    )
    assert batch["result_protocol"] == RESULT_PROTOCOL
    rows = [row["step_result"] for row in batch["results"]]
    for row in rows:
        assert validate_against("/$defs/stepResultV1", row) == []

    assert rows[0]["outcome"]["status"] == "passed"
    assert rows[1]["outcome"]["failure"]["domain"] == "selector"
    assert rows[2]["outcome"]["cause"] == {"type": "prior_step", "step_index": 1}


@pytest.mark.asyncio
async def test_assertion_without_observation_is_never_a_pass() -> None:
    """The empty-assertion false green must be structurally impossible."""

    class SilentUi(FakeUiDriver):
        async def wait_for_selector(self, **kwargs):
            return None

    batch = await steps_cmd.run_steps_on_agent(
        HylyreAgent(ui=SilentUi()),
        [{"wait_for": {"by_id": "whatever", "timeout": 0.01}}],
    )
    step = batch["results"][0]["step_result"]
    assert step["outcome"]["status"] == "failed"
    assert step["outcome"]["failure"]["domain"] == "capability"
    # spec section 6.1, native table row 4: a provider that could not answer
    # has resolved nothing, so the resolution must not claim a found target.
    assert step["selector"]["resolution"]["state"] == "not_attempted"
    assert step["selector"]["resolution"]["selected"] is None
    assert validate_against("/$defs/stepResultV1", step) == []


# ---------------------------------------------------------------- layer 3
@pytest.mark.asyncio
async def test_atomic_entry_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _root(_node({"type": "Button", "id": "ok", "bounds": "[0,0][10,10]"}))
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))
    response = await loop_cmd._run_atomic_ledger_step(agent, {"touch": {"by_id": "ok"}})
    assert response["result_protocol"] == RESULT_PROTOCOL
    assert validate_against("/$defs/stepResultV1", response["step_result"]) == []
    assert response["step_result"]["outcome"]["status"] == "passed"


@pytest.mark.asyncio
async def test_session_daemon_entry_smoke() -> None:
    from hylyre.session.daemon import _dispatch

    tree = _root(_node({"type": "Button", "id": "ok", "bounds": "[0,0][10,10]"}))
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))
    response = await _dispatch(agent, "run_step", {"payload": {"touch": {"by_id": "ok"}}})
    assert response["result_protocol"] == RESULT_PROTOCOL
    assert validate_against("/$defs/stepResultV1", response["step_result"]) == []


# ------------------------------------------------------- legacy isolation
def test_legacy_report_path_never_claims_the_v1_protocol(tmp_path: Path) -> None:
    """`report begin/record/finalize` stays legacy and is not evidence."""

    from hylyre.cli.commands import run_cmd

    draft = tmp_path / "draft.json"
    run_cmd.execute_report_begin(feature="adhoc", trace_path=draft, plan_path=None)
    run_cmd.execute_report_record(
        trace_path=draft,
        case_id="TC-L",
        name="legacy",
        priority="P0",
        ac_ref="AC-L",
        status="通过",
    )
    report = tmp_path / "r.md"
    trace = tmp_path / "t.json"
    run_cmd.execute_report_finalize(
        trace_path=draft, plan_path=None, report_out=report, trace_out=trace
    )
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data["schema_version"] != TRACE_SCHEMA_V1
    assert "result_protocol" not in data
    assert trace_schema_kind(data) == "legacy"


@pytest.mark.parametrize(
    ("schema_version", "protocol", "expected"),
    [
        (TRACE_SCHEMA_V1, RESULT_PROTOCOL, "current"),
        (TRACE_SCHEMA_V1, None, "unsupported"),
        (TRACE_SCHEMA_V1, "hylyre.step-outcome/2", "unsupported"),
        ("0.3-p0", None, "legacy"),
        ("0.3-p0", RESULT_PROTOCOL, "unsupported"),
        ("9.9-p0", None, "unsupported"),
        ("9.9-p0", RESULT_PROTOCOL, "unsupported"),
    ],
)
def test_schema_protocol_dispatch_is_fail_closed(
    schema_version: str, protocol: str | None, expected: str
) -> None:
    """Unknown combinations fail loudly; they never fall back to legacy."""

    trace: dict = {"schema_version": schema_version}
    if protocol is not None:
        trace["result_protocol"] = protocol
    assert trace_schema_kind(trace) == expected


# --------------------------------------- regressions from the Phase 1 review
@pytest.mark.asyncio
async def test_steps_file_report_mode_survives_an_abort_suffix(tmp_path: Path) -> None:
    """A batch that fails mid-way must still emit a verifier-clean trace.

    Projecting each row into its own single-step case stranded every abort
    suffix's ``cause.prior_step``, so the run wrote a trace its own verifier
    then rejected.
    """

    from hylyre.scenario.steps_report import steps_batch_to_scenario_result

    tree = _root(_node({"type": "Button", "id": "ok", "bounds": "[0,0][10,10]"}))
    batch = await steps_cmd.run_steps_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        [
            {"touch": {"by_id": "ok"}},
            {"touch": {"by_text": "missing"}},
            {"wait": {"seconds": 0}},
        ],
    )
    result = steps_batch_to_scenario_result(
        feature="abort", steps_path=tmp_path / "s.json", batch=batch
    )
    report, trace = tmp_path / "r.md", tmp_path / "t.json"
    write_run_artifacts(result, report_path=report, trace_path=trace)

    data = json.loads(trace.read_text(encoding="utf-8"))
    assert validate_against("", data) == []
    assert reference_reducer.verify_trace(data) == []
    assert verify_report(report, trace, None)

    steps = data["cases"][0]["steps"]
    root_step = next(s for s in steps if s["outcome"]["status"] == "failed")
    suffix = next(s for s in steps if s["outcome"]["status"] == "blocked")
    assert suffix["outcome"]["cause"]["step_index"] == root_step["index"]


@pytest.mark.asyncio
async def test_native_assertion_never_backfills_the_request() -> None:
    """``resolution`` reports what was found; a failed presence is not unique."""

    class Absent(FakeUiDriver):
        async def wait_for_selector(self, **kwargs):
            return {"evidence": {"observed_present": False}}

    outcome = await HylyreAgent(ui=Absent()).run_planned_wait_for(
        {"wait_for": {"by_id": "bank_row"}}
    )
    resolution = outcome.selector.resolution
    assert resolution.state == "not_found"
    assert resolution.selected is None
    assert outcome.outcome_dict()["failure"]["domain"] == "assertion"


@pytest.mark.asyncio
async def test_hypium_wait_timeout_is_an_assertion_not_a_selector_failure() -> None:
    """The real driver contract: a timeout is an observation, not an exception."""

    from unittest.mock import MagicMock, patch

    from hylyre.drivers.hypium.driver import HypiumDriver

    raw = MagicMock()
    shim = MagicMock()
    shim.UiDriver.connect.return_value = raw
    with patch("hylyre.drivers.hypium.driver.load_hypium_shim", return_value=shim):
        driver = HypiumDriver()
        await driver.connect()
        raw.wait_for_component.return_value = None
        outcome = await HylyreAgent(ui=driver).run_planned_wait_for(
            {"wait_for": {"by_id": "x", "timeout": 1}}
        )
    result = outcome.outcome_dict()
    assert result["failure"]["domain"] == "assertion"
    assert result["observation"]["facts"]["observed_present"] is False


@pytest.mark.asyncio
async def test_ai_wait_for_consumes_outcomes_not_exceptions() -> None:
    """A false answer must keep polling; it used to end the wait as success."""

    from tests.contract.fakes.fake_vlm_client import FakeVlmClient

    calls = {"n": 0}

    class Counting(FakeVlmClient):
        async def vision_json(self, **kwargs):
            calls["n"] += 1
            return await super().vision_json(**kwargs)

    agent = HylyreAgent(
        ui=FakeUiDriver(),
        vlm=Counting(responses=[{"ok": False, "reason": "no"}, {"ok": True}]),
    )
    await agent.ai_wait_for("home", timeout=2.0, interval=0.01)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_a_protocol_violating_return_still_produces_a_row() -> None:
    """Every dispatched step has a StepResult, even when the wiring is wrong."""

    from hylyre.scenario.ledger import execute_ledger_step

    class Broken(HylyreAgent):
        async def run_planned_home(self, payload):
            return None

    step = await execute_ledger_step(
        Broken(ui=FakeUiDriver()), {"home": {}}, index=0, case_id="p"
    )
    assert step.failure["code"] == "internal.unexpected_exception"
    assert validate_against("/$defs/stepResultV1", step.to_dict()) == []


def test_generic_value_error_is_not_blamed_on_the_plan() -> None:
    from hylyre.api.exceptions import PlannedStepContractError
    from hylyre.scenario.step_builder import outcome_from_exception

    driver_bug = outcome_from_exception(ValueError("internal invariant broke"))
    assert driver_bug.failure.code == "internal.unexpected_exception"

    plan_fault = outcome_from_exception(PlannedStepContractError("bad step"))
    assert plan_fault.failure.code == "contract.invalid_step"


def test_fake_selector_failure_carries_selector_evidence() -> None:
    """The stub must be usable as a consumer conformance gate."""

    from hylyre.scenario.plan_parse import TestCase

    case = TestCase(
        "TC-FAIL", "n", "", '{"touch":{"by_id":"bank_row"}}', "-", "P0", "AC"
    )
    step = ScenarioRunner._fake_case_result(case).steps[0]
    assert step.failure["code"] == "selector.not_found"
    assert step.selector["request"]["value"] == "bank_row"
    assert step.selector["resolution"]["state"] == "not_found"


@pytest.mark.asyncio
async def test_device_death_makes_the_next_case_its_own_root(tmp_path: Path) -> None:
    """Decision row D-23: no re-attempt, and no cross-case prior_step."""

    class Dying(FakeUiDriver):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.taps = 0

        async def touch(self, **kwargs):
            self.taps += 1
            if self.taps >= 2:
                raise ConnectionError("device gone")

        async def dump_ui(self):
            if self.taps >= 2:
                raise ConnectionError("device gone")
            return await super().dump_ui()

    plan = _plan(
        tmp_path / "death.md",
        '| TC-1 | a | | {"touch":{"x":1,"y":2}};{"touch":{"x":1,"y":2}} | - | P0 | AC-1 |',
        '| TC-2 | b | | {"touch":{"x":1,"y":2}} | - | P0 | AC-2 |',
    )
    ui = Dying(dump_tree=_root())
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=ui), plan, feature="death", check_expected=False
    )
    first = result.case_results[1].steps[0]
    assert first.status == "blocked"
    assert first.cause["type"] == "infrastructure"
    assert first.cause["facts"]["probe_source"] == "device_preflight"
    assert ui.taps == 2, "the dead device must not be dispatched against again"


def test_dispatch_exposes_the_frozen_machine_codes() -> None:
    from hylyre.harness.runner import trace_dispatch_code

    assert trace_dispatch_code({"schema_version": "0.3-p0"}) == (
        "legacy_unsupported_for_evidence"
    )
    assert trace_dispatch_code({"schema_version": "9.9-p0"}) == (
        "unsupported_schema_or_protocol"
    )
    assert (
        trace_dispatch_code(
            {"schema_version": TRACE_SCHEMA_V1, "result_protocol": RESULT_PROTOCOL}
        )
        is None
    )


@pytest.mark.asyncio
async def test_mcp_atomic_envelope_is_identical_with_and_without_failure_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One atomic MCP tool must not change protocol shape with an option.

    Passing ``failure_dir`` used to route the call through the batch runner, so
    the same tool returned ``total/results`` instead of
    ``result_protocol + step_result`` — a consumer could not typed-parse it
    without first guessing which shape it had received.
    """

    pytest.importorskip("fastmcp")
    from fastmcp import Client

    import hylyre.wiring as wiring
    from hylyre.mcp.server import build_mcp

    tree = _root(_node({"type": "Button", "id": "ok", "bounds": "[0,0][10,10]"}))
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=tree))
    monkeypatch.setattr(
        wiring, "create_hypium_agent_with_env_vlm", lambda **kwargs: agent
    )
    monkeypatch.setattr(wiring, "create_hypium_agent", lambda **kwargs: agent)

    shapes: dict[str, list[str]] = {}
    async with Client(build_mcp()) as client:
        for label, extra in (
            ("plain", {}),
            ("with failure_dir", {"failure_dir": str(tmp_path / "fd")}),
        ):
            result = await client.call_tool(
                "hylyre_run_wait", {"payload": {"wait": {"seconds": 0}}, **extra}
            )
            payload = json.loads(result.content[0].text)
            shapes[label] = sorted(payload)
            assert payload["result_protocol"] == RESULT_PROTOCOL, label
            assert validate_against("/$defs/stepResultV1", payload["step_result"]) == []

    assert shapes["plain"] == shapes["with failure_dir"] == [
        "result_protocol",
        "step_result",
    ]


def test_ai_action_failure_is_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public AI action entry returns an envelope, not a fixed "ok"."""

    import hylyre.wiring as wiring
    from hylyre.cli.commands import ai_cmd
    from tests.contract.fakes.fake_vlm_client import FakeVlmClient

    agent = HylyreAgent(
        ui=FakeUiDriver(dump_tree=_root()),
        vlm=FakeVlmClient(responses=[{"action": {"type": "touch", "by_text": "nope"}}]),
    )
    monkeypatch.setattr(
        wiring, "create_hypium_agent_with_env_vlm", lambda **kwargs: agent
    )

    response = ai_cmd.execute_ai_action(device_sn=None, instruction="tap")
    assert response["result_protocol"] == RESULT_PROTOCOL
    assert response["step_result"]["outcome"]["status"] == "failed"
    assert validate_against("/$defs/stepResultV1", response["step_result"]) == []


@pytest.mark.asyncio
async def test_failure_boundary_is_captured_without_an_explicit_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A readable device must yield real artifacts even with no dir configured.

    Reporting `capture unavailable` because nobody passed a directory invented
    a device fact that never happened, and skipped the evidence obligation.
    """

    monkeypatch.chdir(tmp_path)
    tree = _root(_node({"type": "Button", "id": "ok", "bounds": "[0,0][10,10]"}))
    batch = await steps_cmd.run_steps_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=tree)),
        [{"touch": {"by_text": "missing"}}],
    )
    step = batch["results"][0]["step_result"]
    assert step["outcome"]["failure"]["domain"] == "selector"
    assert {a["kind"] for a in step["artifacts"]} >= {"ui_dump", "screenshot"}
    assert "hylyre.capture" not in step["extensions"]
    assert validate_against("/$defs/stepResultV1", step) == []


# ------------------------------------------------- Q5: artifact path base
@pytest.mark.asyncio
async def test_artifact_paths_resolve_from_the_trace_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`resolve(dirname(trace_path), path)` must locate the file and match sha256.

    The producer used to record paths relative to the failure directory, so a
    trace written to a different directory could not locate its own evidence.
    """

    import hashlib

    traces = tmp_path / "traces"
    traces.mkdir()
    plan = _plan(
        tmp_path / "plan.md",
        '| TC-ART | artifact | | {"touch":{"by_text":"missing"}} | - | P0 | AC-1 |',
    )
    trace = traces / "t.json"
    result = await ScenarioRunner().run_plan_on_agent(
        HylyreAgent(ui=FakeUiDriver(dump_tree=_root())),
        plan,
        feature="artifact-base",
        check_expected=False,
        failure_dir=trace.parent / "failures",
        artifact_base=trace.parent,
    )
    write_run_artifacts(result, report_path=tmp_path / "r.md", trace_path=trace)

    data = json.loads(trace.read_text(encoding="utf-8"))
    artifacts = data["cases"][0]["steps"][0]["artifacts"]
    assert artifacts, "a selector root failure owes screen evidence"

    # Resolve from a completely unrelated working directory: the base is the
    # trace file, never the process cwd.
    monkeypatch.chdir(tmp_path.parent)
    for artifact in artifacts:
        assert not Path(artifact["path"]).is_absolute()
        resolved = (trace.parent / artifact["path"]).resolve()
        assert resolved.is_file(), artifact["path"]
        assert resolved.is_relative_to(trace.parent.resolve()), "must not escape"
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        assert digest == artifact["sha256"]


@pytest.mark.parametrize(
    "path",
    [
        "../outside.png",
        "sub/../../outside.png",
        "/abs/outside.png",
        "C:/tmp/outside.png",
        "\\\\server\\share\\outside.png",
        "\\rooted\\outside.png",
        "sub\\..\\..\\outside.png",
    ],
)
def test_artifact_paths_that_escape_the_trace_tree_are_rejected(path: str) -> None:
    """An escaping path would point evidence outside the run's own tree."""

    artifact = {"kind": "screenshot", "path": path, "sha256": "0" * 64}
    assert validate_against("/$defs/artifactRef", artifact)


def test_artifact_path_in_a_subdirectory_is_valid() -> None:
    artifact = {
        "kind": "screenshot",
        "path": "failures/TC-1-step-0.png",
        "sha256": "0" * 64,
    }
    assert validate_against("/$defs/artifactRef", artifact) == []


def test_golden_artifact_paths_are_trace_relative() -> None:
    """Every shipped fixture models the frozen base, not a producer-local one."""

    for path in sorted((GOLDEN_DIR / "trace" / "valid").glob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        if trace.get("schema_version") != TRACE_SCHEMA_V1:
            continue
        for case in trace["cases"]:
            for step in case["steps"]:
                for artifact in step["artifacts"]:
                    value = artifact["path"]
                    assert not Path(value).is_absolute(), (path.name, value)
                    assert ".." not in Path(value).parts, (path.name, value)


# ------------------------------------------------------ Q8: multi-root choice
def test_prior_step_may_reference_a_non_nearest_root() -> None:
    """Any earlier eligible root is legal; "nearest" is not a rule."""

    trace = json.loads(
        (GOLDEN_DIR / "trace" / "valid" / "prior-step-references-an-earlier-root.json")
        .read_text(encoding="utf-8")
    )
    assert validate_against("", trace) == []
    assert reference_reducer.verify_trace(trace) == []

    steps = trace["cases"][0]["steps"]
    roots = [s["index"] for s in steps if s["outcome"]["status"] == "failed"]
    blocked = next(s for s in steps if s["outcome"]["status"] == "blocked")
    referenced = blocked["outcome"]["cause"]["step_index"]

    assert len(roots) >= 2, "the point of the fixture is more than one eligible root"
    assert referenced == min(roots)
    assert referenced != max(roots), "it deliberately skips the nearest root"


# ------------------------------- round-4 regressions: atomic wiring integrity
def test_every_atomic_entry_binds_the_failure_dir_it_uses() -> None:
    """No public atomic entry may reference an undeclared ``failure_dir``.

    A bulk edit once added ``failure_dir=failure_dir`` to entries that never
    declared the parameter, so ``hylyre run action`` raised NameError before
    reaching a device — and no test called those entries.
    """

    import ast
    import inspect

    from hylyre.cli.commands import loop_cmd

    tree = ast.parse(inspect.getsource(loop_cmd))

    def declared(fn: ast.AST) -> set[str]:
        args = fn.args  # type: ignore[attr-defined]
        return {a.arg for a in args.args + args.kwonlyargs + args.posonlyargs}

    enclosing: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if (
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child is not node
                ):
                    enclosing[id(child)] = node

    unbound: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(
            isinstance(n, ast.Name)
            and n.id == "failure_dir"
            and isinstance(n.ctx, ast.Load)
            for n in ast.walk(node)
        ):
            continue
        names: set[str] = set()
        scope: ast.AST | None = node
        while scope is not None:
            names |= declared(scope)
            scope = enclosing.get(id(scope))
        if "failure_dir" not in names:
            unbound.append(f"{node.name}:{node.lineno}")

    assert unbound == [], f"failure_dir is unbound in {unbound}"


@pytest.mark.asyncio
async def test_atomic_entry_writes_artifacts_into_the_requested_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller-supplied failure_dir must actually be honoured, not dropped.

    Checking the response keys alone would have missed this: the envelope was
    right while the artifacts went to the default directory instead.
    """

    import hashlib

    monkeypatch.chdir(tmp_path)
    requested = tmp_path / "requested"
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=_root()))

    response = await loop_cmd._run_atomic_ledger_step(
        agent, {"touch": {"by_text": "missing"}}, failure_dir=requested
    )
    step = response["step_result"]
    assert response["result_protocol"] == RESULT_PROTOCOL
    assert step["outcome"]["failure"]["domain"] == "selector"
    assert step["artifacts"], "a selector root failure owes screen evidence"

    written = sorted(p.name for p in requested.rglob("*") if p.is_file())
    assert written, "artifacts must land in the requested directory"
    assert not (tmp_path / ".hylyre" / "failures").exists(), (
        "the default directory must not be used when one was requested"
    )
    for artifact in step["artifacts"]:
        resolved = requested / Path(artifact["path"]).name
        assert resolved.is_file()
        assert hashlib.sha256(resolved.read_bytes()).hexdigest() == artifact["sha256"]


@pytest.mark.asyncio
async def test_mcp_atomic_with_failure_dir_writes_where_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real FastMCP client: atomic envelope *and* artifact landing site."""

    pytest.importorskip("fastmcp")
    from fastmcp import Client

    import hylyre.wiring as wiring
    from hylyre.mcp.server import build_mcp

    monkeypatch.chdir(tmp_path)
    requested = tmp_path / "mcp-failures"
    agent = HylyreAgent(ui=FakeUiDriver(dump_tree=_root()))
    monkeypatch.setattr(
        wiring, "create_hypium_agent_with_env_vlm", lambda **kwargs: agent
    )
    monkeypatch.setattr(wiring, "create_hypium_agent", lambda **kwargs: agent)

    async with Client(build_mcp()) as client:
        result = await client.call_tool(
            "hylyre_run_wait_for",
            {
                "payload": {"wait_for": {"by_text": "missing", "timeout": 0.01}},
                "failure_dir": str(requested),
            },
        )
    payload = json.loads(result.content[0].text)

    assert sorted(payload) == ["result_protocol", "step_result"]
    step = payload["step_result"]
    assert validate_against("/$defs/stepResultV1", step) == []
    if step["outcome"]["status"] == "failed" and step["outcome"]["failure"][
        "domain"
    ] in ("selector", "assertion"):
        assert requested.exists(), "the requested directory must be used"
        assert any(requested.rglob("*"))


# ------------------------------- steps-file fake mode must never reach a device
def test_steps_file_fake_mode_constructs_no_device_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--use-fakes`` was accepted and ignored here, so the run connected.

    A silent fallback to a real device is worse than an unsupported flag: the
    operator believes they ran offline while the harness drove hardware.
    """

    import hylyre.wiring as wiring

    calls: list[str] = []

    def boom(**kwargs):  # pragma: no cover - must never run
        calls.append("agent")
        raise AssertionError("fake mode must never construct a device agent")

    # Patch the binding the batch path actually calls, not just the source
    # module: loop_cmd imports the factory by name at import time.
    monkeypatch.setattr(loop_cmd, "create_hypium_agent", boom)
    monkeypatch.setattr(wiring, "create_hypium_agent_with_env_vlm", boom)
    monkeypatch.setattr(wiring, "create_hypium_agent", boom)

    batch = steps_cmd.execute_run_steps(
        [{"touch": {"by_id": "ok"}}, {"wait": {"seconds": 0}}], use_fakes=True
    )

    assert calls == []
    assert batch["result_protocol"] == RESULT_PROTOCOL
    for row in batch["results"]:
        step = row["step_result"]
        assert validate_against("/$defs/stepResultV1", step) == []
        assert step["device_session"] is False
        # no 0.3 flat fields survive anywhere in the row
        assert {"failure_kind", "failure_code", "evidence", "error"}.isdisjoint(step)


def test_steps_file_without_fakes_still_uses_the_device_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real path must be untouched by the fake fix."""

    used: list[str] = []
    agent = HylyreAgent(
        ui=FakeUiDriver(dump_tree=_root(_node({"type": "Button", "id": "ok"})))
    )

    def factory(**kwargs):
        used.append("agent")
        return agent

    monkeypatch.setattr(loop_cmd, "create_hypium_agent", factory)

    batch = steps_cmd.execute_run_steps([{"wait": {"seconds": 0}}])

    assert used == ["agent"], "the device path must still build an agent"
    assert batch["result_protocol"] == RESULT_PROTOCOL


def test_fake_mode_and_a_live_session_are_refused_together() -> None:
    """A session is a live connection; the combination has no meaning."""

    with pytest.raises(ValueError, match="cannot be combined with --session"):
        steps_cmd.execute_run_steps(
            [{"wait": {"seconds": 0}}], use_fakes=True, session_file=Path("s.json")
        )


def test_steps_file_fake_report_is_protocol_conformant(tmp_path: Path) -> None:
    """The offline batch still emits a v1 trace the verifier accepts."""

    from hylyre.cli.commands import run_cmd

    steps_path = tmp_path / "steps.json"
    steps_path.write_text(
        json.dumps([{"touch": {"by_id": "ok"}}, {"wait_for": {"by_id": "later"}}]),
        encoding="utf-8",
    )
    report, trace = tmp_path / "r.md", tmp_path / "t.json"

    _msg, result = run_cmd.execute_steps_scenario(
        steps_path=steps_path,
        steps=json.loads(steps_path.read_text(encoding="utf-8")),
        feature="fake-steps",
        report_out=report,
        trace_out=trace,
        use_fakes=True,
    )

    assert result.use_fakes is True
    data = json.loads(trace.read_text(encoding="utf-8"))
    assert data["schema_version"] == TRACE_SCHEMA_V1
    assert data["result_protocol"] == RESULT_PROTOCOL
    assert data["environment"]["selector_engine"] == "fake"
    assert validate_against("", data) == []
    assert reference_reducer.verify_trace(data) == []
    for step in data["cases"][0]["steps"]:
        assert step["device_session"] is False


def test_plan_and_steps_fakes_share_one_outcome_decision() -> None:
    """Both fake entries must mean the same thing by construction."""

    from hylyre.scenario.runner import fake_step_outcome

    action = fake_step_outcome({"touch": {"by_id": "x"}}, kind="touch", role="action")
    assertion = fake_step_outcome(
        {"wait_for": {"by_id": "x"}}, kind="wait_for", role="assertion"
    )
    assert action.outcome_dict()["status"] == "passed"
    # A stub cannot observe, so it says so rather than emitting a green assertion.
    assert assertion.outcome_dict()["status"] == "blocked"
    assert assertion.outcome_dict()["cause"]["capability_id"] == "fake.ui_observation"
