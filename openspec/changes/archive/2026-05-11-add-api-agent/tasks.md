# Tasks: add-api-agent

## Spec

- [x] 1. Delta under `openspec/changes/add-api-agent/specs/api-agent/spec.md` + merge into `openspec/specs/api-agent/spec.md`

## Implementation

- [x] 2. `VlmClientBase` in `hylyre/drivers/base/`
- [x] 3. `HttpVlmClient` + `extract_json_object` + `FakeVlmClient`
- [x] 4. `HylyreAgent` (`ai_*` + `start_app` + optional mock helpers)
- [x] 5. `hylyre/wiring.py` + root `__init__` exports `HylyreAgent`
- [x] 6. CLI `hylyre ai action|query|assert` + `test_cli_help`
- [x] 7. L1 tests: agent, json extract, http vlm respx, wiring, device+ai CLI

## Exit

- [x] 8. `pytest --cov=hylyre --cov-fail-under=70` green
- [x] 9. 已归档至 `openspec/changes/archive/2026-05-11-add-api-agent/`，`docs/progress.md` 已记录
