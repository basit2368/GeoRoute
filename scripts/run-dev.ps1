#!/usr/bin/env pwsh
# Starts the FastAPI backend and Next.js frontend in separate terminal windows.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$engineDll = Join-Path $backendDir 'app/native/georoute_engine.dll'

if (-not (Test-Path $engineDll)) {
  Write-Host 'Native engine not found — building it first.'
  & (Join-Path $PSScriptRoot 'build-engine.ps1')
}

Start-Process powershell -ArgumentList @(
  '-NoExit',
  '-Command',
  'python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000'
) -WorkingDirectory $backendDir -WindowStyle Normal

Start-Process powershell -ArgumentList @(
  '-NoExit',
  '-Command',
  'npm run dev'
) -WorkingDirectory $frontendDir -WindowStyle Normal

Write-Host 'Backend:  http://localhost:8000/docs'
Write-Host 'Frontend: http://localhost:3000'
