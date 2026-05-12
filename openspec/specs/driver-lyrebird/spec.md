# driver-lyrebird Specification

## Purpose

HTTP Mock 侧 Lyrebird 适配：`MockControllerBase` / `LyrebirdController`（生命周期、分组、数据、抓包）、`hylyre mock` CLI；P2 已交付。设备侧 MITM 证书自动化见 OpenSpec change **`add-cert-bootstrap`**。

## Requirements

### Requirement: Lyrebird controller

The system SHALL provide `hylyre.drivers.lyrebird.LyrebirdController` implementing `MockControllerBase` against Lyrebird HTTP admin APIs on configurable `base_url` (default `http://127.0.0.1:9090`).

#### Scenario: Optional extra

- **GIVEN** install without `[mock]` extra
- **WHEN** `require_lyrebird_distribution()` or `start_local()` needs the `lyrebird` distribution
- **THEN** an `ImportError` guides `pip install 'hylyre[mock]'`

#### Scenario: Activate group

- **WHEN** `activate_group("uuid")` is awaited against a healthy Lyrebird
- **THEN** the client issues `PUT /api/mock/{uuid}/activate` and treats HTTP errors or `code != 1000` as failure

#### Scenario: Capture flows

- **WHEN** `export_flows(path, full_detail=False|True)` is awaited
- **THEN** the client reads `/api/flow` and optionally each `/api/flow/{id}` and writes UTF-8 JSON to `path`

---

### Requirement: Mock CLI

The system SHALL register `hylyre mock` with subcommands `start`, `stop`, `status`, `activate`, `deactivate`, `capture`, `cert` documented in `--help`.

#### Scenario: Start writes pidfile

- **WHEN** `hylyre mock start` succeeds
- **THEN** a pidfile is written (default `./.hylyre/lyrebird.pid`) for `mock stop`

---

### Requirement: MockControllerBase ABC

The system SHALL expose `hylyre.drivers.base.MockControllerBase` as the async contract for mock backends (parallel to `UiDriverBase`).

#### Scenario: Fake implements offline

- **WHEN** CI runs `FakeMockController` against `MockControllerBase` contract tests
- **THEN** all abstract methods are implemented without Lyrebird installed

---

### Requirement: MITM trust checklist (P2 placeholder)

The system SHALL expose `mitm_trust_instructions()` and `hylyre mock cert` printing actionable steps until automated `add-cert-bootstrap` lands.

#### Scenario: CLI prints checklist

- **WHEN** `hylyre mock cert` runs
- **THEN** stdout contains HarmonyOS / hdc / MITM trust guidance
