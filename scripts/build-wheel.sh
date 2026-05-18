#!/usr/bin/env sh
# Thin wrapper: forward to Python entrypoint (single implementation).
set -e
HERE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
if [ -n "${PYTHON:-}" ]; then
  exec "${PYTHON}" "${HERE}/build_wheel.py" "$@"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 "${HERE}/build_wheel.py" "$@"
fi
exec python "${HERE}/build_wheel.py" "$@"
