# Tasks: add-source-release

## 1. Implementation

- [x] `scripts/build_wheel.py`: `--source` build mode (stage `src/`, LF normalization, schema 2 manifest with `tree_sha256`).
- [x] `--verify` schema-2 support (strict `src/` subtree, undeclared-file detection, lenient `integration_docs`, version cross-check).

## 2. Docs

- [x] `docs/framework-vendor-bundle.md`: plain-source release chapter (build, EOL/tree-hash algorithm, copy list, verify semantics, downstream install).
- [x] Short pointers in `README.md` and `AGENTS.md`.

## 3. Tests & CI

- [x] `tests/packaging/test_build_source.py`: unit + roundtrip + tamper/undeclared/downstream-layout scenarios; `slow` pip-install integration.
- [x] Extend `build-wheel` CI job with source build + verify steps.

## 4. Spec

- [x] Add `openspec/changes/add-source-release/specs/packaging/spec.md`.
