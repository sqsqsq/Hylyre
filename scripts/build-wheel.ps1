# SPDX-License-Identifier: MIT
# Thin wrapper: forward to Python entrypoint (single implementation).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$py = $env:PYTHON
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source }
if (-not $py) { $py = "python" }
& $py (Join-Path $here "build_wheel.py") @args
exit $LASTEXITCODE
