# Proposal: add-vendor-bundle (framework wheel)

## Why

Downstream **framework** repos may reach PyPI but not GitHub; they need an installable **hylyre** artifact without cloning this repo. Hylyre is pure Python, so one `py3-none-any` wheel covers all platforms. Transitive deps (`hypium`, `fastmcp`, etc.) can be resolved from PyPI / mirrors on the consumer side.

## What

- `scripts/build_wheel.py`: `pip wheel . --no-deps` → single wheel + `release.manifest.json` with SHA-256.
- `scripts/build-wheel.ps1` / `scripts/build-wheel.sh`: thin wrappers.
- `docs/framework-vendor-bundle.md`: maintainer steps + verify + copy example.
- `tests/packaging/test_build_wheel.py`: unit tests + optional `@pytest.mark.slow` integration.
- CI: `build-wheel` job after tests.

## Out of scope

- Vendoring third-party wheels (hypium, fastmcp, …) into this repo.
- Publishing to public PyPI or GitHub Releases.
- Changing Hylyre CLI / runtime behaviour.
