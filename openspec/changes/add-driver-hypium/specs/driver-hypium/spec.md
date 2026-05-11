## ADDED Requirements

### Requirement: UiDriverBase ABC

The system SHALL expose `hylyre.drivers.base.UiDriverBase` as an async abstract contract for HarmonyOS UI control, covering at minimum: `connect`, `close`, `start_app`, `touch` (coordinate or single selector), `input_text` (focused field or selector), and `screenshot` returning raster bytes.

#### Scenario: Touch target exclusivity

- **WHEN** a caller invokes `touch` with more than one of: coordinate pair, `by_text`, `by_id`
- **THEN** the implementation raises `ValueError` before issuing device commands

---

### Requirement: HypiumDriver adapter

The system SHALL provide `hylyre.drivers.hypium.HypiumDriver` implementing `UiDriverBase` using the optional `hypium` distribution.

#### Scenario: Lazy import without device extra

- **GIVEN** an environment where `hypium` is not installed
- **WHEN** `HypiumDriver.connect()` is awaited
- **THEN** an `ImportError` is raised with guidance to `pip install 'hylyre[device]'`

#### Scenario: No import-time hard dependency

- **GIVEN** `pip install hylyre` without extras
- **WHEN** user imports `hylyre.drivers.hypium.HypiumDriver`
- **THEN** import succeeds without importing `hypium` (defer until connect)

---

### Requirement: Device & structured AI CLI (P1)

The system SHALL ship Typer commands `hylyre device list`, `hylyre device install`, `hylyre ai tap`, and `hylyre ai input` documented in `--help`, where device install uses `hdc` and tap/input use `HypiumDriver`.

#### Scenario: Help surfaces subcommands

- **WHEN** `hylyre device --help` and `hylyre ai --help`
- **THEN** outputs list the P1 subcommands and key options

---

### Requirement: Fake UI driver for tests

The system SHALL provide `tests.contract.fakes.fake_ui_driver.FakeUiDriver` implementing `UiDriverBase` with deterministic in-memory event recording for L2/L3 tests.

#### Scenario: Contract suite passes offline

- **WHEN** CI runs `pytest` with Hypium mocked / absent
- **THEN** L1/L2/L3 UI driver tests pass and coverage gate `cov-fail-under` is satisfied
