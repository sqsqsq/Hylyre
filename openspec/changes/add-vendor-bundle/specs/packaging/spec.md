# packaging — vendor wheel for framework

## ADDED Requirements

### Requirement: build_wheel script

The repository SHALL provide `scripts/build_wheel.py` invoked from the **repository root** context (script resolves parent directory as project root).

#### Scenario: default build

- **WHEN** the maintainer runs `python scripts/build_wheel.py [--out-dir <path>] [--clean]`
- **THEN** the tool runs `python -m pip wheel . --no-deps -w <out-dir>` with cwd = repo root
- **AND** exactly one file matching `hylyre-*-py3-none-any.whl` exists under `<out-dir>`
- **AND** `<out-dir>/release.manifest.json` is written with `schema: 1`, `hylyre_version` matching `pyproject.toml` `project.version`, and `wheel.filename` / `wheel.sha256` / `wheel.size_bytes` for that wheel
- **AND** stdout prints the absolute paths of the wheel and manifest (first two lines), then a copy/verify hint block (`format_cp_hints`) for downstream `vendor/` sync

#### Scenario: verify

- **WHEN** the maintainer runs `python scripts/build_wheel.py --verify <dir>`
- **THEN** the tool reads `<dir>/release.manifest.json` and recomputes SHA-256 of `<dir>/<wheel.filename>`
- **AND** returns exit code `0` if digests match, `2` if they differ, `3` if manifest or wheel is missing or invalid

#### Scenario: exit codes (build)

- **WHEN** `pip wheel` fails
- **THEN** the script exits with code `1`

### Requirement: thin wrappers

The repository SHALL provide `scripts/build-wheel.ps1` and `scripts/build-wheel.sh` that delegate to `build_wheel.py` with forwarded arguments.

### Requirement: documentation

The repository SHALL document the workflow in `docs/framework-vendor-bundle.md` (build, verify, copy to downstream vendor, example `pip install` with extras).
