#!/usr/bin/env pwsh
# Builds the C++17 algorithm engine and runs its native unit tests.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$include = Join-Path $root 'engine/include'
$sources = @(
  (Join-Path $root 'engine/src/closest_pair.cpp'),
  (Join-Path $root 'engine/src/tsp.cpp')
)
$testSource = Join-Path $root 'engine/tests/engine_tests.cpp'
$nativeDir = Join-Path $root 'backend/app/native'
# Versioned output avoids Windows file locks when a running backend has the
# previous engine loaded. active.txt tells the backend which build to load.
$dllName = "georoute_engine-$(Get-Date -Format 'yyyyMMdd-HHmmss').dll"
$dllPath = Join-Path $nativeDir $dllName
$activePath = Join-Path $nativeDir 'active.txt'
$testPath = Join-Path $root 'engine/build/engine_tests.exe'

New-Item -ItemType Directory -Force -Path $nativeDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $testPath) | Out-Null

$gpp = (Get-Command g++ -ErrorAction SilentlyContinue).Source
if (-not $gpp) {
  $candidates = @(
    'C:\msys64\ucrt64\bin\g++.exe',
    'C:\msys64\mingw64\bin\g++.exe',
    'C:\MinGW\bin\g++.exe'
  )
  $gpp = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $gpp) {
  throw 'g++ was not found. Install a C++17 toolchain or add g++ to PATH.'
}

# MSYS2 compilers need their bin directory on PATH to find cc1plus/as/ld.
# Restore PATH afterwards so callers keep using their normal Python/Node tools.
$originalPath = $env:PATH
try {
  $env:PATH = "$(Split-Path -Parent $gpp);$env:PATH"

  Write-Host "Using compiler: $gpp"
  Write-Host "Building native engine: $dllPath"
  & $gpp -std=c++17 -O3 -Wall -Wextra -shared -static-libgcc -static-libstdc++ `
    "-I$include" $sources -o $dllPath
  if ($LASTEXITCODE -ne 0) { throw 'Failed to build the shared library.' }

  # MSYS2 builds still depend on libwinpthread. Keep the runtime beside the DLL
  # so Python can load it without changing PATH.
  $pthread = Join-Path (Split-Path -Parent $gpp) 'libwinpthread-1.dll'
  $pthreadTarget = Join-Path $nativeDir 'libwinpthread-1.dll'
  if ((Test-Path $pthread) -and -not (Test-Path $pthreadTarget)) {
    Copy-Item $pthread $pthreadTarget -Force
  }

  Set-Content -Path $activePath -Value $dllName -Encoding ascii -NoNewline
  Get-ChildItem -Path $nativeDir -Filter 'georoute_engine-*.dll' |
    Where-Object { $_.Name -ne $dllName } |
    ForEach-Object {
      try { Remove-Item $_.FullName -Force } catch { }
    }

  Write-Host 'Building native tests'
  & $gpp -std=c++17 -O3 -Wall -Wextra -static-libgcc -static-libstdc++ `
    "-I$include" $sources $testSource -o $testPath
  if ($LASTEXITCODE -ne 0) { throw 'Failed to build native tests.' }

  & $testPath
  if ($LASTEXITCODE -ne 0) { throw 'Native tests failed.' }

  Write-Host 'Engine build and tests completed successfully.'
} finally {
  $env:PATH = $originalPath
}
