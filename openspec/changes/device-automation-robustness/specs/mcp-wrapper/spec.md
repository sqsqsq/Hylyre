## ADDED Requirements

### Requirement: MCP scroll_to tool and failure_dir passthrough

The MCP wrapper SHALL register `hylyre_run_scroll_to` mirroring the `scroll_to` planned JSON root, and SHALL accept a `failure_dir` parameter on the batch (`hylyre_run_steps`) and generic step-dispatch tools, passing it through to the shared execution logic (including the session path) so diagnostics are written equivalently to the CLI. The atomic single-action tools (e.g. `hylyre_run_tap`, `hylyre_run_scroll`) are out of scope for `failure_dir`.

#### Scenario: scroll_to tool mirrors planned JSON

- **WHEN** `hylyre_run_scroll_to` is invoked with a `scroll_to` payload
- **THEN** it dispatches the same shared logic as the CLI `run scroll-to` / planned `scroll_to` step

#### Scenario: failure_dir flows through MCP

- **WHEN** the batch (`hylyre_run_steps`) or generic step-dispatch tool is called with `failure_dir`
- **THEN** on step failure the dump/screenshot artifacts are written under that directory, matching CLI behavior
