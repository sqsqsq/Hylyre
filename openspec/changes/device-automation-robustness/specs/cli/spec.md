## ADDED Requirements

### Requirement: Device force-stop and cold-restart commands

The CLI SHALL register `hylyre device force-stop --bundle <id> [--device-sn]` (positional `aa force-stop`) and `hylyre device cold-restart --bundle <id> [--ability] [--wait-time]` (force-stop then `aa start`, with a post-start wait for the main Ability), both with working `--help`.

#### Scenario: force-stop uses positional form

- **WHEN** `hylyre device force-stop --bundle com.example.app` runs
- **THEN** it issues `aa force-stop <bundle>` (positional) rather than the `-b` form

#### Scenario: cold-restart resets to a clean start

- **WHEN** `hylyre device cold-restart --bundle com.example.app` runs
- **THEN** the app is force-stopped and then started, with a stabilization wait before returning

### Requirement: Failure diagnostics flag and scroll_to subcommand

The CLI SHALL expose `--failure-dir` on `hylyre run` and `hylyre run --steps-file` (default: a `failures/` directory beside the report output) and pass it through to the runner (including the session path). The CLI SHALL register `hylyre run scroll-to` mirroring the `scroll_to` planned JSON.

#### Scenario: run records failures to dir

- **WHEN** `hylyre run --plan ... --failure-dir <dir>` runs and a step fails
- **THEN** diagnostics artifacts are written under `<dir>`

#### Scenario: scroll-to subcommand exists

- **WHEN** `hylyre run scroll-to --help` is invoked
- **THEN** it documents the `scroll_to` JSON shape and runs it like other Tier A run subcommands

### Requirement: app page save single-device fallback and root-cause stderr

`hylyre app page save` SHALL, when none of `--from-dump`/`--session`/`--device-sn` is given and exactly one device is connected, auto-select that device instead of exiting with code 2; when zero or multiple devices are connected it SHALL print an actionable error listing connected devices. On dump/persist failure it SHALL emit the root cause (which stage failed) to stderr.

#### Scenario: Auto-select the only connected device

- **GIVEN** exactly one device is connected and no source flag is passed
- **WHEN** `hylyre app page save <bundle> <name>` runs
- **THEN** it captures from that device and saves the snapshot (no exit code 2)

#### Scenario: Clear error on ambiguous device

- **WHEN** no source flag is passed and zero or multiple devices are connected
- **THEN** the command prints an actionable error listing the connected devices
