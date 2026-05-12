## MODIFIED Requirements

### Requirement: HylyreAgent public surface

The system SHALL expose `HylyreAgent` from `hylyre.api` (and `hylyre` package root) with Midscene-aligned methods: `ai_action`, `ai_query`, `ai_assert`, `ai_tap`, `ai_input`, `ai_wait_for`, `ai_locate`, plus `start_app`, `aclose`, and optional `mock_activate_group` / `mock_deactivate_all` when a `MockControllerBase` is configured.

#### Scenario: Import path stable

- **GIVEN** a consumer installs `hylyre` without device/mock extras
- **WHEN** they `from hylyre import HylyreAgent` or `from hylyre.api import HylyreAgent`
- **THEN** import succeeds without importing `hypium` or `lyrebird` inside `hylyre.api`

#### Scenario: Structured tap avoids VLM

- **WHEN** `ai_tap` is called with `by_text` / `by_id` / coordinates only (no `instruction=`)
- **THEN** `HylyreAgent` uses `UiDriverBase.touch` / `input_text` without a `VlmClientBase`

#### Scenario: Natural language requires VLM

- **WHEN** `ai_tap(instruction=...)` (or other `ai_*` NL overloads) is used
- **THEN** a `VlmClientBase` must be configured or a clear `ValueError` is raised

### Requirement: VLM client abstraction

The system SHALL provide `VlmClientBase` in `hylyre.drivers.base` and a concrete `HttpVlmClient` that reads `HYLYRE_VLM_ENDPOINT`, optional `HYLYRE_VLM_API_KEY`, `HYLYRE_VLM_MODEL`, posting OpenAI-compatible chat completions with vision.

#### Scenario: Env optional client

- **WHEN** `HYLYRE_VLM_ENDPOINT` is unset
- **THEN** `HttpVlmClient.from_env()` returns `None`

### Requirement: Agent wiring

The system SHALL provide `hylyre.wiring.create_hypium_agent` (and `create_hypium_agent_with_env_vlm`) that lazily construct `HypiumDriver` and optional `LyrebirdController` without placing those imports in `hylyre.api`.

#### Scenario: Lazy Hypium import

- **WHEN** `create_hypium_agent(device_sn=...)` is called
- **THEN** `HypiumDriver` is imported inside the factory implementation (not from `hylyre.api`)

### Requirement: CLI ai natural language

The system SHALL register `hylyre ai action`, `hylyre ai query`, and `hylyre ai assert` with working `--help`, using the wiring factory and failing with a clear message when the VLM endpoint env is missing.

#### Scenario: Help lists NL subcommands

- **WHEN** `hylyre ai --help`
- **THEN** output lists `action`, `query`, and `assert` alongside `tap` and `input`
