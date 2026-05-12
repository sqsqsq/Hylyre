# Run mock toolchain bootstrap from repo root (PYTHONPATH = this checkout).
# Usage: ./scripts/bootstrap_mock.ps1 [--install]
#   or:  pwsh -File scripts/bootstrap_mock.ps1 [--install]

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($env:PYTHONPATH) {
  $env:PYTHONPATH = "$RepoRoot;$env:PYTHONPATH"
} else {
  $env:PYTHONPATH = $RepoRoot
}
Set-Location $RepoRoot
python -m hylyre bootstrap mock @args
exit $LASTEXITCODE
