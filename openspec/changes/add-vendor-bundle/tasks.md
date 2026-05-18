# Tasks: add-vendor-bundle

## 1. Implementation

- [x] Add `scripts/build_wheel.py` (build + `--verify`).
- [x] Add `scripts/build-wheel.ps1` and `scripts/build-wheel.sh`.

## 2. Docs

- [x] Add `docs/framework-vendor-bundle.md`.
- [x] Short pointers in `README.md` and `AGENTS.md`.

## 3. Tests & CI

- [x] Add `tests/packaging/test_build_wheel.py` with `slow` marker for pip integration.
- [x] Extend `pyproject.toml` pytest markers and default `-m "not slow"`.
- [x] Add `build-wheel` job to `.github/workflows/ci.yml`.

## 4. Spec

- [x] Add `openspec/changes/add-vendor-bundle/specs/packaging/spec.md`.
