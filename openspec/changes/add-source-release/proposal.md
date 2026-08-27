# Proposal: add-source-release (plain-source tree vendor mode)

## Why

The downstream **framework** repo (maison) must be mirrored into a corporate repository that forbids committing `.whl` files (and, most likely, `.tar.gz` sdists). The hylyre package is pure text (~77 files: `.py` + contracts json/yaml/md), so a plain-source tree can be committed as-is and installed with `pip install <src-dir>` — extras, PyPI-mirror transitive deps, and manifest-driven auto-alignment stay unchanged. The wheel mode remains; both modes coexist and downstream consumers dispatch on the manifest `schema`.

## What

- `scripts/build_wheel.py --source`: stage `src/` (`pyproject.toml` + `README.md` + `hylyre/**` incl. contracts package-data; excluding `__pycache__/`, `*.pyc`, `*.egg-info/`, `build/`, `tests/`) into `dist/release-src/`, LF-normalized, plus `release.manifest.json` **schema 2** (per-file sha256/size, `tree_sha256`/`file_count`/`total_bytes`) and the `integration_docs` handoff doc.
- `--verify <dir>` auto-detects schema 2: strict per-file + aggregate + undeclared-file checks inside `source.root`; vendor-root files outside it are downstream-owned and ignored; `integration_docs` files must match when present, pass when absent (field absent also passes).
- `docs/framework-vendor-bundle.md`: source-release chapter (build, EOL/tree-hash algorithm, copy list, verify semantics, downstream install via PEP 517 build isolation).
- CI: build + verify the source release in the `build-wheel` job.

## Out of scope

- Downstream (maison) harness changes: schema 1/2 dual consumption, temp-dir install, `planned_step_keys.py` SSOT reading.
- Publishing to PyPI; changing the wheel mode (schema 1) in any way.

## Versioning

Released as **0.3.2** (also realigns the long-stale `hylyre.__version__`, stuck at 0.1.0 since the first release, with `pyproject.toml`). The manifest↔pyproject consistency self-check runs on both build and verify.
