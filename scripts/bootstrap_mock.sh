#!/usr/bin/env bash
# Run mock toolchain bootstrap from repo root without requiring a prior editable install:
# sets PYTHONPATH to this checkout, then `python -m hylyre bootstrap mock …`
# Usage: scripts/bootstrap_mock.sh [--install]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

exec "$PY" -m hylyre bootstrap mock "$@"
