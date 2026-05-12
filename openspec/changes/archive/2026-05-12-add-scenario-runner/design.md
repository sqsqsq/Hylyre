# Design: add-scenario-runner

## Modules

- `hylyre/scenario/plan_parse.py` — extract `TestCase` rows from the table under 测试用例清单.
- `hylyre/scenario/runner.py` — `ScenarioRunner`: `--use-fakes` produces deterministic pass results per case; later attaches `HylyreAgent`.
- `hylyre/report/emit.py` — markdown sections required by `report-sections.yaml`; trace dict validated by `output-schema.json`.
- `hylyre/harness/runner.py` — L5: headings present; execution statuses ∈ contract; verdict ∈ contract; trace jsonschema; every plan case id appears in report table; non-empty 关联 AC column per row.

## CLI

- `hylyre run` — Typer options; when `--use-fakes`, skips device. Writes report + trace then runs verify (failure → non-zero exit).
- `hylyre report verify` — shared function used by CLI and tests.

## Trace

- `schema_version: "0.2-p4"` for new artifacts; validator accepts this and optional `cases` array summarizing run.
