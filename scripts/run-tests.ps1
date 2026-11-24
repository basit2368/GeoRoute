#!/usr/bin/env pwsh
# Runs the full GeoRoute test suite on Windows.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot

Write-Host "`n[1/3] Building and testing the C++ engine"
& (Join-Path $PSScriptRoot 'build-engine.ps1')

Write-Host "`n[2/3] Running backend tests"
Push-Location (Join-Path $root 'backend')
try {
  python -m unittest discover -s tests -v
  if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
} finally {
  Pop-Location
}

Write-Host "`n[3/3] Type-checking and building the frontend"
Push-Location (Join-Path $root 'frontend')
try {
  npm run typecheck
  if ($LASTEXITCODE -ne 0) { throw 'Frontend type check failed.' }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally {
  Pop-Location
}

Write-Host "`nAll GeoRoute tests completed successfully."
