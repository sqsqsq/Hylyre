"""0.5.1: option ownership for the shared ``hylyre run`` callback.

Every option declared on the callback is registered in ``OWNERSHIP`` with its
Click default and the execution paths that consume it. With no device, the
tests prove that

* the registered key set and defaults equal what Typer/Click actually declares
  (and that ``RUN_OPTION_PATHS`` in production agrees with the fixture);
* on a supported path a non-default value reaches the owner boundary, shown as
  a difference against the canonical baseline at that boundary;
* on an unsupported path a non-default value is a usage error (exit 2, empty
  stdout, one stderr line), while a default-equivalent value passes unchanged;
* an option written before any of the 17 ``run`` subcommands is no longer
  swallowed by the callback's early return, and each subcommand's own options
  still bind through to its handler.
"""

from __future__ import annotations

import copy
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import typer.main as typer_main
from typer.testing import CliRunner

import hylyre.wiring as wiring
from hylyre.cli.__main__ import RUN_OPTION_PATHS, app, run_app, run_plan_batch
from hylyre.cli.commands import loop_cmd, run_cmd, steps_cmd

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "tests" / "e2e" / "fixtures" / "mock-test-plan.md"
STEPS = [{"back": {}}]
STEPS_JSON = json.dumps(STEPS)
TAP_JSON = '{"touch":{"by_id":"x"}}'

PATHS = ("plan", "steps_report", "steps_raw", "subcommand")
BATCH = frozenset({"plan", "steps_report", "steps_raw"})
STEPS_PATHS = frozenset({"steps_report", "steps_raw"})
REPORT_PATHS = frozenset({"plan", "steps_report"})

runner = CliRunner()


def _opt(
    flag: str,
    default: Any,
    paths: frozenset[str] | set[str],
    nondefault: list[str],
    *,
    value: Any,
    explicit_default: list[str] | None = None,
    kw: str | None = None,
    selector: bool = False,
) -> dict[str, Any]:
    """One ownership row.

    ``nondefault`` is a legal, executable argv fragment (``{tmp}`` is replaced
    by the test's temp directory); ``value`` is what must arrive at the owner
    boundary under ``kw`` (default: the param name), or a callable of ``tmp``.
    ``explicit_default`` is only given when the default is expressible on the
    CLI. ``selector`` marks options that choose the execution path.
    """

    return {
        "flag": flag,
        "default": default,
        "paths": frozenset(paths),
        "nondefault": nondefault,
        "explicit_default": explicit_default,
        "kw": kw,
        "value": value,
        "selector": selector,
    }


# Keyed by Click ``param.name``.
OWNERSHIP: dict[str, dict[str, Any]] = {
    "plan": _opt("--plan", None, {"plan"}, ["--plan", str(PLAN)], value=PLAN, selector=True),
    "steps": _opt(
        "--steps", None, STEPS_PATHS, ["--steps", STEPS_JSON], value=STEPS, selector=True
    ),
    "steps_file": _opt(
        "--steps-file",
        None,
        STEPS_PATHS,
        ["--steps-file", "{tmp}/steps.json"],
        value=STEPS,
        kw="steps",
        selector=True,
    ),
    "on_fail": _opt(
        "--on-fail",
        "abort",
        STEPS_PATHS,
        ["--on-fail", "skip"],
        value="skip",
        explicit_default=["--on-fail", "ABORT"],
    ),
    "steps_out": _opt(
        "--out",
        None,
        {"steps_raw"},
        ["--out", "{tmp}/steps-out.json"],
        value=lambda tmp: tmp / "steps-out.json",
    ),
    "session": _opt(
        "--session",
        None,
        STEPS_PATHS,
        ["--session", "{tmp}/session.json"],
        value=lambda tmp: tmp / "session.json",
        kw="session_file",
    ),
    "page_name": _opt(
        "--page-name", None, BATCH, ["--page-name", "MainAbility"], value="MainAbility"
    ),
    "start_wait_time": _opt(
        "--wait-time",
        1.0,
        BATCH,
        ["--wait-time", "2.5"],
        value=2.5,
        explicit_default=["--wait-time", "1.0"],
        kw="wait_time",
    ),
    "feature": _opt(
        "--feature", None, REPORT_PATHS, ["--feature", "ownership"], value="ownership", selector=True
    ),
    "report_out": _opt(
        "--report-out",
        None,
        REPORT_PATHS,
        ["--report-out", "{tmp}/report.md"],
        value=lambda tmp: tmp / "report.md",
        selector=True,
    ),
    "trace_out": _opt(
        "--trace-out",
        None,
        REPORT_PATHS,
        ["--trace-out", "{tmp}/trace.json"],
        value=lambda tmp: tmp / "trace.json",
        selector=True,
    ),
    "use_fakes": _opt("--use-fakes", False, BATCH, ["--use-fakes"], value=True),
    "device_sn": _opt("--device-sn", None, BATCH, ["--device-sn", "SN1"], value="SN1"),
    "bundle": _opt(
        "--bundle", None, BATCH, ["--bundle", "com.example.app"], value="com.example.app"
    ),
    "mock_port": _opt("--mock-port", None, BATCH, ["--mock-port", "9090"], value=9090),
    "lyrebird_url": _opt(
        "--lyrebird-url",
        None,
        BATCH,
        ["--lyrebird-url", "http://127.0.0.1:9090"],
        value="http://127.0.0.1:9090",
    ),
    "mock_group": _opt("--mock-group", None, {"plan"}, ["--mock-group", "g1"], value="g1"),
    "skip_assert_expected": _opt(
        "--skip-assert-expected", False, {"plan"}, ["--skip-assert-expected"], value=True
    ),
    "model_backend": _opt(
        "--model-backend", None, REPORT_PATHS, ["--model-backend", "mb"], value="mb"
    ),
    "failure_dir": _opt(
        "--failure-dir",
        None,
        BATCH,
        ["--failure-dir", "{tmp}/fails"],
        value=lambda tmp: tmp / "fails",
    ),
}

# The 17 real ``run`` subcommands: handler in loop_cmd + required argv.
SUBCOMMANDS: dict[str, tuple[str, list[str]]] = {
    "action": ("run_action_json", ["--json", '{"action":{"type":"back"}}']),
    "tap": ("run_tap_json", ["--json", TAP_JSON]),
    "input": ("run_input_json", ["--json", '{"input":{"text":"hi","by_id":"x"}}']),
    "swipe": ("run_swipe_json", ["--json", '{"swipe":{"direction":"DOWN"}}']),
    "scroll": ("run_scroll_json", ["--json", '{"scroll":{"direction":"down"}}']),
    "start-app": ("run_start_app_cli", ["--bundle", "com.example.app"]),
    "back": ("run_planned_step_json", ["--json", '{"back":{}}']),
    "home": ("run_planned_step_json", ["--json", '{"home":{}}']),
    "stop-app": ("run_planned_step_json", ["--json", '{"stop_app":{"bundle":"b"}}']),
    "clear-app": ("run_planned_step_json", ["--json", '{"clear_app":{"bundle":"b"}}']),
    "wait": ("run_planned_step_json", ["--json", '{"wait":{"seconds":0}}']),
    "wait-for": ("run_planned_step_json", ["--json", '{"wait_for":{"by_id":"x"}}']),
    "wait-gone": ("run_planned_step_json", ["--json", '{"wait_gone":{"by_id":"x"}}']),
    "wait-idle": ("run_planned_step_json", ["--json", '{"wait_idle":{}}']),
    "assert-toast": ("run_planned_step_json", ["--json", '{"assert_toast":{"text":"t"}}']),
    "scroll-to": ("run_planned_step_json", ["--json", '{"scroll_to":{"by_id":"x"}}']),
    "start-app-step": ("run_planned_step_json", ["--json", '{"start_app":{"bundle":"b"}}']),
}
REPRESENTATIVE_SUBCOMMAND = "tap"
REPRESENTATIVE_PARENT_OPTION = "on_fail"


# ----------------------------------------------------------------- helpers
def _fill(argv: list[str], tmp: Path) -> list[str]:
    return [a.replace("{tmp}", str(tmp)) for a in argv]


def _expected(entry: dict[str, Any], tmp: Path) -> Any:
    value = entry["value"]
    return value(tmp) if callable(value) else value


def _argv(
    path: str,
    tmp: Path,
    extra: list[str] = (),
    *,
    steps_opt: list[str] | None = None,
) -> list[str]:
    """Canonical argv for ``path`` with ``extra`` parent options inserted."""

    steps_opt = _fill(steps_opt or ["--steps", STEPS_JSON], tmp)
    report = _fill(
        ["--feature", "ownership", "--report-out", "{tmp}/report.md", "--trace-out", "{tmp}/trace.json"],
        tmp,
    )
    extra = _fill(list(extra), tmp)
    if path == "plan":
        return ["run", *extra, "--plan", str(PLAN), *report]
    if path == "steps_report":
        return ["run", *extra, *steps_opt, *report]
    if path == "steps_raw":
        return ["run", *extra, *steps_opt]
    sub, (_handler, sub_args) = REPRESENTATIVE_SUBCOMMAND, SUBCOMMANDS[REPRESENTATIVE_SUBCOMMAND]
    return ["run", *extra, sub, *sub_args]


def _click_callback_params() -> dict[str, Any]:
    """The callback's own options, straight from the Click command model."""

    declared = inspect.signature(run_plan_batch).parameters
    cmd = typer_main.get_command(run_app)
    return {p.name: p for p in cmd.params if p.name in declared}


def check_ownership(
    fixture: dict[str, dict[str, Any]],
    *,
    params: dict[str, Any] | None = None,
    production: dict[str, frozenset[str]] = RUN_OPTION_PATHS,
) -> None:
    """Reconcile fixture <-> Click model <-> production table. Raises on drift."""

    params = _click_callback_params() if params is None else params
    assert set(params) == set(fixture), (
        f"callback options {sorted(params)} != fixture {sorted(fixture)}"
    )
    assert set(production) == set(fixture), (
        f"RUN_OPTION_PATHS {sorted(production)} != fixture {sorted(fixture)}"
    )
    for name, entry in fixture.items():
        param = params[name]
        # ``1 == 1.0`` in Python, so compare the type too: a float option that
        # silently became an int is still default drift.
        assert (
            param.default == entry["default"]
            and type(param.default) is type(entry["default"])
        ), f"{name}: Click default {param.default!r} != fixture {entry['default']!r}"
        assert param.opts[0] == entry["flag"], f"{name}: flag {param.opts[0]}"
        assert production[name] == entry["paths"], (
            f"{name}: production paths {sorted(production[name])} != "
            f"fixture {sorted(entry['paths'])}"
        )
        assert entry["paths"] <= set(PATHS)
        assert entry["nondefault"], f"{name}: needs a representative argv"


@pytest.fixture
def no_device(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def boom(*_a: Any, **_k: Any) -> Any:  # pragma: no cover - must never run
        calls.append("agent")
        raise AssertionError("ownership tests must never construct a device agent")

    monkeypatch.setattr(loop_cmd, "create_hypium_agent", boom)
    monkeypatch.setattr(wiring, "create_hypium_agent_with_env_vlm", boom)
    monkeypatch.setattr(wiring, "create_hypium_agent", boom)
    return calls


def _success_result() -> Any:
    case = SimpleNamespace(
        raw_dict=lambda: {
            "execution": "completed",
            "verification": "passed",
            "evidence": "complete",
            "steps": [],
        }
    )
    return SimpleNamespace(case_results=[case])


@pytest.fixture
def boundary(monkeypatch: pytest.MonkeyPatch, no_device: list[str]) -> dict[str, list[dict]]:
    """Spy every owner boundary the callback dispatches to; nothing runs."""

    seen: dict[str, list[dict[str, Any]]] = {p: [] for p in PATHS}

    def plan_spy(**kw: Any) -> None:
        seen["plan"].append(kw)

    def report_spy(**kw: Any) -> tuple[str, Any]:
        seen["steps_report"].append(kw)
        return "ok", _success_result()

    def raw_spy(steps: list, **kw: Any) -> dict[str, Any]:
        seen["steps_raw"].append({"steps": steps, **kw})
        return {"results": []}

    monkeypatch.setattr(run_cmd, "run_scenario", plan_spy)
    monkeypatch.setattr(run_cmd, "execute_steps_scenario", report_spy)
    monkeypatch.setattr(steps_cmd, "execute_run_steps", raw_spy)
    for handler in {h for h, _ in SUBCOMMANDS.values()}:

        def sub_spy(_h: str = handler, **kw: Any) -> None:
            seen["subcommand"].append({"handler": _h, **kw})

        monkeypatch.setattr(loop_cmd, handler, sub_spy)
    return seen


def _write_steps_file(tmp: Path) -> Path:
    path = tmp / "steps.json"
    path.write_text(STEPS_JSON, encoding="utf-8")
    return path


def _invoke(argv: list[str]):
    return runner.invoke(app, argv)


def _assert_usage_error(result, *names: str) -> None:
    assert result.exit_code == 2, result.output
    assert result.stdout == ""
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1, result.stderr
    for name in names:
        assert name in lines[0], f"{name!r} missing from {lines[0]!r}"


# ------------------------------------------------- declaration reconciliation
def test_ownership_fixture_matches_click_declaration_and_production_table() -> None:
    check_ownership(OWNERSHIP)
    assert len(OWNERSHIP) == 20


@pytest.mark.parametrize(
    "mutate",
    [
        lambda f: f.pop("on_fail"),
        lambda f: f.update(extra=_opt("--extra", None, set(), ["--extra"], value=1)),
        lambda f: f["on_fail"].update(default="skip"),
        lambda f: f["start_wait_time"].update(default=1),
        lambda f: f["on_fail"].update(paths=frozenset({"plan"})),
        lambda f: f["steps_out"].update(flag="--output"),
    ],
    ids=["missing-key", "unknown-key", "default-drift", "default-type-drift", "path-drift", "flag-drift"],
)
def test_negative_self_check_broken_fixture_fails_reconciliation(mutate) -> None:
    broken = copy.deepcopy(OWNERSHIP)
    mutate(broken)
    with pytest.raises(AssertionError):
        check_ownership(broken)


def test_subcommand_table_matches_registered_run_subcommands() -> None:
    assert set(SUBCOMMANDS) == set(typer_main.get_command(run_app).commands)
    assert len(SUBCOMMANDS) == 17


# ----------------------------------------------------- supported path: reaches
SUPPORTED = [
    (name, path) for name, e in OWNERSHIP.items() for path in PATHS if path in e["paths"]
]


@pytest.mark.parametrize(("name", "path"), SUPPORTED, ids=[f"{n}@{p}" for n, p in SUPPORTED])
def test_supported_path_value_reaches_owner_boundary(
    name: str, path: str, tmp_path: Path, boundary: dict[str, list[dict]]
) -> None:
    entry = OWNERSHIP[name]
    _write_steps_file(tmp_path)
    key = entry["kw"] or name
    expected = _expected(entry, tmp_path)

    if entry["selector"]:
        steps_opt = entry["nondefault"] if name in ("steps", "steps_file") else None
        argv = _argv(path, tmp_path, steps_opt=steps_opt)
    else:
        baseline = _invoke(_argv(path, tmp_path))
        assert baseline.exit_code != 2, baseline.output
        base = boundary[path].pop()
        argv = _argv(path, tmp_path, entry["nondefault"])

    result = _invoke(argv)
    assert result.exit_code != 2, result.output
    assert len(boundary[path]) == 1, boundary
    captured = boundary[path][0]

    if name == "steps_out":
        # Owner boundary of --out is the callback itself: the batch JSON lands
        # in the file and stdout carries only the path.
        assert expected.is_file()
        assert json.loads(expected.read_text(encoding="utf-8")) == {"results": []}
        assert result.stdout.strip() == str(expected.resolve())
        assert "results" not in result.stdout
        return
    assert captured[key] == expected, (key, captured.get(key), expected)
    if not entry["selector"]:
        assert base[key] != captured[key], f"{name}: no behaviour difference at {path}"


# ---------------------------------------------------- unsupported path: reject
def _unsupported() -> list[tuple[str, str]]:
    rows = []
    for name, e in OWNERSHIP.items():
        for path in PATHS:
            if path in e["paths"]:
                continue
            if e["selector"] and path != "subcommand":
                continue  # path selectors switch the path; covered separately
            rows.append((name, path))
    return rows


UNSUPPORTED = _unsupported()


@pytest.mark.parametrize(
    ("name", "path"), UNSUPPORTED, ids=[f"{n}@{p}" for n, p in UNSUPPORTED]
)
def test_unsupported_path_nondefault_is_usage_error_with_zero_device(
    name: str,
    path: str,
    tmp_path: Path,
    boundary: dict[str, list[dict]],
    no_device: list[str],
) -> None:
    entry = OWNERSHIP[name]
    _write_steps_file(tmp_path)
    label = {"plan": "--plan", "subcommand": REPRESENTATIVE_SUBCOMMAND}.get(path, "--steps")

    result = _invoke(_argv(path, tmp_path, entry["nondefault"]))

    _assert_usage_error(result, entry["flag"], label)
    assert all(not calls for calls in boundary.values()), boundary
    assert no_device == []
    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "trace.json").exists()


@pytest.mark.parametrize(
    ("path", "extra", "message"),
    [
        ("plan", ["--steps", STEPS_JSON], "Cannot combine --plan"),
        ("plan", ["--steps-file", "{tmp}/steps.json"], "Cannot combine --plan"),
        ("steps_raw", ["--plan", str(PLAN)], "Cannot combine --plan"),
        ("steps_report", ["--plan", str(PLAN)], "Cannot combine --plan"),
        ("steps_raw", ["--feature", "x"], "Steps report mode requires"),
        ("steps_raw", ["--report-out", "{tmp}/r.md"], "Steps report mode requires"),
        ("steps_raw", ["--trace-out", "{tmp}/t.json"], "Steps report mode requires"),
    ],
)
def test_path_selectors_change_dispatch_instead_of_being_ignored(
    path: str,
    extra: list[str],
    message: str,
    tmp_path: Path,
    boundary: dict[str, list[dict]],
) -> None:
    """A selector on a foreign path re-routes (or conflicts); it never no-ops."""

    _write_steps_file(tmp_path)
    result = _invoke(_argv(path, tmp_path, extra))
    assert result.exit_code == 2, result.output
    assert message in result.stderr
    assert all(not calls for calls in boundary.values()), boundary


# ------------------------------------------- default-compatible: passes through
DEFAULT_COMPATIBLE = [
    (name, path)
    for name, e in OWNERSHIP.items()
    if e["explicit_default"]
    for path in PATHS
    if path not in e["paths"]
]


@pytest.mark.parametrize(
    ("name", "path"), DEFAULT_COMPATIBLE, ids=[f"{n}@{p}" for n, p in DEFAULT_COMPATIBLE]
)
def test_default_equivalent_value_on_unsupported_path_behaves_like_omitted(
    name: str, path: str, tmp_path: Path, boundary: dict[str, list[dict]]
) -> None:
    entry = OWNERSHIP[name]
    baseline = _invoke(_argv(path, tmp_path))
    assert baseline.exit_code != 2, baseline.output
    base = boundary[path].pop()

    result = _invoke(_argv(path, tmp_path, entry["explicit_default"]))

    assert result.exit_code == baseline.exit_code, result.output
    assert result.stderr == baseline.stderr
    assert boundary[path] == [base]


# ------------------------------------------------------------- P0-1: plan+on_fail
def _plan_cli(tmp: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "hylyre",
            "run",
            "--plan",
            str(PLAN),
            "--feature",
            "on-fail",
            "--report-out",
            str(tmp / "report.md"),
            "--trace-out",
            str(tmp / "trace.json"),
            "--use-fakes",
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def test_plan_with_non_default_on_fail_is_usage_error_in_a_real_process(
    tmp_path: Path,
) -> None:
    """One real process for the stdout/stderr shape; CliRunner covers the values."""

    proc = _plan_cli(tmp_path, "--on-fail", "skip")
    assert proc.returncode == 2, proc.stderr
    assert proc.stdout == ""
    lines = proc.stderr.strip().splitlines()
    assert len(lines) == 1, proc.stderr
    assert "--on-fail" in lines[0] and "--plan" in lines[0]
    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "trace.json").exists()


@pytest.mark.parametrize("value", ["skip", "bogus"])
def test_plan_with_non_default_on_fail_rejects_before_contract_check_and_device(
    tmp_path: Path, value: str, monkeypatch: pytest.MonkeyPatch, no_device: list[str]
) -> None:
    contract_checks: list[Path] = []
    monkeypatch.setattr(
        run_cmd, "reject_plan_before_run", lambda p: contract_checks.append(p)
    )
    (tmp_path / "report.md").write_text("PREVIOUS", encoding="utf-8")
    (tmp_path / "trace.json").write_text("{}", encoding="utf-8")

    result = _invoke(_argv("plan", tmp_path, ["--on-fail", value]))

    _assert_usage_error(result, "--on-fail", "--plan")
    assert contract_checks == []
    assert no_device == []
    assert (tmp_path / "report.md").read_text(encoding="utf-8") == "PREVIOUS"
    assert (tmp_path / "trace.json").read_text(encoding="utf-8") == "{}"


@pytest.mark.parametrize("explicit", [["--on-fail", "abort"], ["--on-fail", "ABORT"]])
def test_plan_fake_run_with_explicit_abort_is_byte_identical_to_omitted(
    tmp_path: Path, explicit: list[str]
) -> None:
    base, again = tmp_path / "base", tmp_path / "again"
    base.mkdir()
    again.mkdir()
    a = _invoke(_argv("plan", base, ["--use-fakes"]))
    b = _invoke(_argv("plan", again, ["--use-fakes", *explicit]))
    assert a.exit_code == 0, a.output
    assert b.exit_code == 0, b.output
    for name in ("report.md", "trace.json"):
        assert (base / name).read_bytes() == (again / name).read_bytes(), name


def test_plan_runner_boundary_has_no_on_fail_parameter() -> None:
    """P0-1 forbids forwarding on_fail into the plan runner."""

    from hylyre.scenario.runner import ScenarioRunner

    assert "on_fail" not in inspect.signature(run_cmd.run_scenario).parameters
    assert "on_fail" not in inspect.signature(ScenarioRunner.run_plan_on_agent).parameters


def test_run_help_documents_on_fail_scope() -> None:
    result = runner.invoke(app, ["run", "--help"], env={"COLUMNS": "400"})
    assert result.exit_code == 0
    line = next(l for l in result.output.splitlines() if "--on-fail" in l)
    assert "abort|skip" in line
    assert "--steps/--steps-file" in line
    assert "--plan accepts only the default abort" in line
    assert "usage error" in line


# ------------------------------------------ steps paths: on_fail semantics stay
BLOCKING_STEPS = json.dumps([{"wait_for": {"by_id": "later"}}, {"back": {}}])


def _steps_source(kind: str, tmp: Path) -> list[str]:
    if kind == "inline":
        return ["--steps", BLOCKING_STEPS]
    path = tmp / "blocking.json"
    path.write_text(BLOCKING_STEPS, encoding="utf-8")
    return ["--steps-file", str(path)]


@pytest.mark.parametrize("kind", ["inline", "file"])
@pytest.mark.parametrize(
    ("on_fail", "executed", "second"),
    [("abort", 1, "blocked"), ("ABORT", 1, "blocked"), ("skip", 2, "passed")],
)
def test_steps_raw_on_fail_semantics_unchanged(
    kind: str, on_fail: str, executed: int, second: str, tmp_path: Path, no_device: list[str]
) -> None:
    result = _invoke(["run", *_steps_source(kind, tmp_path), "--use-fakes", "--on-fail", on_fail])
    assert result.exit_code == 1, result.output  # the blocked assertion fails the batch
    batch = json.loads(result.stdout)
    assert batch["on_fail"] == (
        "abort" if on_fail.lower() == "abort" else "skip"
    )
    assert batch["executed"] == executed
    outcomes = [r["step_result"]["outcome"] for r in batch["results"]]
    assert outcomes[0]["status"] == "blocked"
    assert outcomes[1]["status"] == second
    if second == "blocked":
        assert outcomes[1]["cause"] == {"type": "prior_step", "step_index": 0}
    assert no_device == []


@pytest.mark.parametrize("fakes", [["--use-fakes"], []], ids=["fake", "device"])
@pytest.mark.parametrize("kind", ["inline", "file"])
def test_steps_raw_bogus_on_fail_still_rejected_by_normalizer(
    kind: str,
    fakes: list[str],
    tmp_path: Path,
    no_device: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Still ``_normalize_on_fail``'s verdict, now a usage error before any device.

    The ``device`` variant is the one that proves it: without ``--use-fakes`` the
    batch used to build the agent (and ``start_app`` with ``--bundle``) first and
    only then hit the normaliser.
    """

    def boom(**_k: Any) -> Any:  # pragma: no cover - must never run
        no_device.append("with_hypium_agent")
        raise AssertionError("bogus --on-fail must be rejected before the agent")

    monkeypatch.setattr(steps_cmd, "_with_hypium_agent", boom)
    result = _invoke(
        [
            "run",
            *_steps_source(kind, tmp_path),
            *fakes,
            "--bundle",
            "com.x",
            "--on-fail",
            "bogus",
        ]
    )
    assert result.exit_code == 2, result.output
    assert result.stdout == ""
    assert result.stderr.strip().splitlines() == ["on_fail must be abort or skip"]
    assert no_device == []


@pytest.mark.parametrize(
    ("on_fail", "second"), [("abort", "blocked"), ("skip", "passed"), ("bogus", None)]
)
def test_steps_report_on_fail_semantics_unchanged(
    on_fail: str, second: str | None, tmp_path: Path, no_device: list[str]
) -> None:
    result = _invoke(_argv("steps_report", tmp_path, ["--use-fakes", "--on-fail", on_fail], steps_opt=["--steps", BLOCKING_STEPS]))
    if second is None:
        assert result.exit_code == 2, result.output
        assert result.stdout == ""
        assert result.stderr.strip().splitlines() == ["on_fail must be abort or skip"]
        assert not (tmp_path / "trace.json").exists()
        assert not (tmp_path / "report.md").exists()
        return
    assert result.exit_code == 1, result.output  # blocked assertion -> not success
    trace = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    steps = trace["cases"][0]["steps"]
    assert steps[0]["outcome"]["status"] == "blocked"
    assert steps[1]["outcome"]["status"] == second
    assert no_device == []


def test_steps_file_use_fakes_regression_never_builds_a_device(
    tmp_path: Path, no_device: list[str]
) -> None:
    """0.5.0 fix kept: fake mode on the steps-file path must stay offline."""

    steps_file = _write_steps_file(tmp_path)
    result = _invoke(["run", "--steps-file", str(steps_file), "--use-fakes"])
    assert result.exit_code == 0, result.output
    batch = json.loads(result.stdout)
    assert batch["results"][0]["step_result"]["device_session"] is False
    assert no_device == []


# --------------------------------------------------------- subcommand path
@pytest.mark.parametrize("name", list(OWNERSHIP), ids=list(OWNERSHIP))
def test_every_parent_option_before_a_subcommand_is_rejected_not_swallowed(
    name: str, tmp_path: Path, boundary: dict[str, list[dict]], no_device: list[str]
) -> None:
    _write_steps_file(tmp_path)
    entry = OWNERSHIP[name]
    result = _invoke(_argv("subcommand", tmp_path, entry["nondefault"]))
    _assert_usage_error(result, entry["flag"], REPRESENTATIVE_SUBCOMMAND)
    # Most callback options are not declared by the subcommand at all, so the
    # message must not tell the operator to move them after it.
    assert "pass options after" not in result.stderr
    assert boundary["subcommand"] == []
    assert no_device == []


@pytest.mark.parametrize("sub", list(SUBCOMMANDS), ids=list(SUBCOMMANDS))
def test_every_subcommand_rejects_a_parent_option_written_before_it(
    sub: str, boundary: dict[str, list[dict]], no_device: list[str]
) -> None:
    entry = OWNERSHIP[REPRESENTATIVE_PARENT_OPTION]
    _handler, sub_args = SUBCOMMANDS[sub]
    result = _invoke(["run", *entry["nondefault"], sub, *sub_args])
    _assert_usage_error(result, entry["flag"], sub)
    assert "pass options after" not in result.stderr
    assert boundary["subcommand"] == []
    assert no_device == []


@pytest.mark.parametrize(
    "extra", [["--on-fail", "abort"], ["--on-fail", "ABORT"], ["--wait-time", "1.0"], ["--wait-time", "1"]]
)
def test_default_equivalent_parent_option_before_a_subcommand_passes(
    extra: list[str], tmp_path: Path, boundary: dict[str, list[dict]]
) -> None:
    result = _invoke(_argv("subcommand", tmp_path, extra))
    assert result.exit_code == 0, result.output
    assert len(boundary["subcommand"]) == 1
    assert boundary["subcommand"][0]["payload_json"] == TAP_JSON


@pytest.mark.parametrize("sub", list(SUBCOMMANDS), ids=list(SUBCOMMANDS))
def test_subcommand_own_options_bind_through_to_its_handler(
    sub: str, tmp_path: Path, boundary: dict[str, list[dict]]
) -> None:
    """Direct binding: the value reaches the handler call, not just the signature."""

    handler, sub_args = SUBCOMMANDS[sub]
    session = tmp_path / "session.json"
    result = _invoke(
        [
            "run",
            sub,
            *sub_args,
            "--device-sn",
            "SN1",
            "--session",
            str(session),
            "--mock-port",
            "1234",
            "--lyrebird-url",
            "http://127.0.0.1:1234",
        ]
    )
    assert result.exit_code == 0, result.output
    assert len(boundary["subcommand"]) == 1
    call = boundary["subcommand"][0]
    assert call["handler"] == handler
    assert call["device_sn"] == "SN1"
    assert call["session_file"] == session
    assert call["mock_port"] == 1234
    assert call["lyrebird_url"] == "http://127.0.0.1:1234"


def test_subcommand_spy_negative_self_check(
    tmp_path: Path, boundary: dict[str, list[dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A handler that drops a value must make the binding test fail."""

    def dropping(**kw: Any) -> None:
        kw.pop("device_sn")
        boundary["subcommand"].append({"handler": "run_tap_json", **kw})

    monkeypatch.setattr(loop_cmd, "run_tap_json", dropping)
    result = _invoke(["run", "tap", "--json", TAP_JSON, "--device-sn", "SN1"])
    assert result.exit_code == 0, result.output
    with pytest.raises(KeyError):
        _ = boundary["subcommand"][0]["device_sn"]


def test_package_version_matches_pyproject() -> None:
    """The release script pins manifest == pyproject; this pins __version__ too."""

    import tomllib

    import hylyre

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject.open("rb") as f:
        assert hylyre.__version__ == tomllib.load(f)["project"]["version"]
