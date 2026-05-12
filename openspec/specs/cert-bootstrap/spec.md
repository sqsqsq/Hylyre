# cert-bootstrap Specification

## Purpose

Host-side 辅助将 mitmproxy / Lyrebird MITM 根证书推到 HarmonyOS 设备（`hdc file send`），并保留与静态清单一致的文档指引；与 `openspec/changes/add-cert-bootstrap` 设计一致。

## Requirements

### Requirement: Executable CA bootstrap path

The system SHALL provide a Hylyre CLI entry that runs host-side `hdc file send` for a PEM (default `~/.mitmproxy/mitmproxy-ca-cert.pem`, or `HYLYRE_MITM_CA`, or `--ca-cert`), with explicit non-zero exits when `hdc` is missing or the transfer fails (aligned with `hylyre doctor` messaging).

#### Scenario: Missing hdc

- **WHEN** `hylyre mock push-ca` runs and `hdc` is not on PATH
- **THEN** the command exits with code 2 and prints actionable text

#### Scenario: Unit-test hook

- **WHEN** tests mock `push_mitm_ca_to_device` / `hdc_cli.file_send`
- **THEN** no real `hdc` process is required and argv shape stays stable

### Requirement: Checklist alignment

The system SHALL keep `mitm_trust_instructions()` consistent with the executable path (`mock push-ca` referenced in prose; post-push steps for on-device install).
