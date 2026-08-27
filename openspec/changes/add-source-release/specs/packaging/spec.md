# packaging — plain-source tree release for framework

## ADDED Requirements

### Requirement: source release build

`scripts/build_wheel.py --source [--out-dir <path>] [--clean]` SHALL stage a plain-source release (default out-dir `dist/release-src/`) alongside — not replacing — the wheel mode.

#### Scenario: staged layout

- **WHEN** the maintainer runs `python scripts/build_wheel.py --source --clean`
- **THEN** `<out-dir>/src/` contains `pyproject.toml` (copied verbatim, modulo EOL policy), `README.md` (required by pyproject `readme` for PEP 517 install), and `hylyre/**` including `hylyre.contracts` package-data (`*.json`/`*.yaml`/`*.yml`/`*.md`)
- **AND** `__pycache__/`, `*.pyc`, `*.egg-info/`, `build/`, `tests/` are excluded
- **AND** `<out-dir>/release.manifest.json` (schema 2) and the `integration_docs` handoff doc are written beside `src/`
- **AND** `pip install <out-dir>/src` succeeds via PEP 517 with the existing `setuptools>=61` + `wheel` backend

#### Scenario: EOL normalization

- **WHEN** source files are staged
- **THEN** all text files are written with LF line endings, and every `source.files[].sha256` is computed over the LF bytes as written
- **AND** if any staged file still contains CRLF (e.g. a text suffix missing from the normalization whitelist), the build fails with exit code `1` instead of shipping a sha that would drift on a downstream LF-normalizing checkout

### Requirement: manifest schema 2

The source-mode manifest SHALL declare `schema: 2`, `hylyre_version` equal to `pyproject.toml` `project.version`, and a `source` object with `root` (`"src"`), `file_count`, `total_bytes`, `tree_sha256`, and `files[]` entries `{path, sha256, size_bytes}` where `path` is POSIX-relative to `source.root`. The `wheel` field MAY be absent; the schema-1 wheel manifest is unchanged.

#### Scenario: deterministic tree hash

- **WHEN** `tree_sha256` is computed
- **THEN** all files under `source.root` are sorted by POSIX relative path byte order ascending, each file's sha256 (lowercase hex) is computed over its on-disk bytes, and `tree_sha256` is the sha256 of the UTF-8 bytes of the concatenation of `"<path>\n<sha256>\n"` per file

### Requirement: verify schema 2

`--verify <dir>` SHALL auto-detect schema 2 and keep the exit-code contract (`0` ok; `2` mismatch; `3` missing/invalid input).

#### Scenario: strict inside source.root

- **WHEN** verifying a schema-2 directory
- **THEN** every `source.files` entry must exist with matching sha256 and size (missing file → `3`; mismatch → `2`)
- **AND** `tree_sha256`, `file_count`, `total_bytes` must match the on-disk state (mismatch → `2`)
- **AND** `hylyre_version` must match `source.root`'s `pyproject.toml` `project.version` (mismatch → `2`)
- **AND** any file under `source.root` not declared in `source.files` → `2` (catches in-tree build pollution such as `build/`, `*.egg-info/`)

#### Scenario: downstream-owned vendor root

- **WHEN** files exist in `<dir>` outside `source.root` (e.g. a downstream `README.md`, a leftover `.whl`)
- **THEN** they are ignored — no exemption list is maintained

#### Scenario: lenient integration_docs

- **WHEN** an `integration_docs` entry's file exists in `<dir>`
- **THEN** its sha256 must match (mismatch → `2`)
- **WHEN** the file is absent, or the manifest lacks the `integration_docs` field entirely
- **THEN** verification passes — covering both the source-repo layout and the downstream layout whose pipeline strips the field
