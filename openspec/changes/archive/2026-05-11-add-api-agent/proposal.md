# Proposal: add-api-agent (P3)

## Why

Skill 6 / Midscene-style workflows need a single Python facade (`HylyreAgent`) that can mix **structured** Hypium taps/inputs with **natural-language** steps backed by a **mockable** VLM client, without importing vendor SDKs from `hylyre/api/`.

## What

- `VlmClientBase` + `HttpVlmClient` (OpenAI-compatible chat completions + vision, env `HYLYRE_VLM_*`).
- `HylyreAgent` with `ai_action`, `ai_query`, `ai_assert`, `ai_tap`, `ai_input`, `ai_wait_for`, `ai_locate`; structured paths avoid VLM.
- `hylyre.wiring.create_hypium_agent*` composes Hypium + optional Lyrebird + env VLM (concrete imports live outside `api/`).
- CLI: `hylyre ai action|query|assert` when VLM env is set.
- Tests: `FakeVlmClient`, L1 agent + HTTP VLM + wiring + CLI invocations; CI coverage ≥ 70%.

## Out of scope (later)

- P4 `ScenarioRunner` orchestration, real multi-step VLM plans, prompt tuning per vendor.
