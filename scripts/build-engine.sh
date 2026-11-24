#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INCLUDE="$ROOT/engine/include"
SOURCES=("$ROOT/engine/src/closest_pair.cpp" "$ROOT/engine/src/tsp.cpp")
TEST_SOURCE="$ROOT/engine/tests/engine_tests.cpp"
NATIVE_DIR="$ROOT/backend/app/native"
LIB_NAME="libgeoroute_engine-$(date +%Y%m%d-%H%M%S).so"
LIB_PATH="$NATIVE_DIR/$LIB_NAME"
ACTIVE_PATH="$NATIVE_DIR/active.txt"
TEST_PATH="$ROOT/engine/build/engine_tests"

mkdir -p "$NATIVE_DIR" "$(dirname "$TEST_PATH")"

CXX_BIN="${CXX:-g++}"
if ! command -v "$CXX_BIN" >/dev/null 2>&1; then
  echo "g++ was not found. Set CXX to a C++17 compiler." >&2
  exit 1
fi

echo "Using compiler: $CXX_BIN"
echo "Building native engine: $LIB_PATH"
"$CXX_BIN" -std=c++17 -O3 -Wall -Wextra -fPIC -shared \
  -I"$INCLUDE" "${SOURCES[@]}" -o "$LIB_PATH"

printf '%s' "$LIB_NAME" > "$ACTIVE_PATH"
find "$NATIVE_DIR" -maxdepth 1 -name 'libgeoroute_engine-*.so' \
  ! -name "$LIB_NAME" -delete 2>/dev/null || true

echo "Building native tests"
"$CXX_BIN" -std=c++17 -O3 -Wall -Wextra \
  -I"$INCLUDE" "${SOURCES[@]}" "$TEST_SOURCE" -o "$TEST_PATH"

"$TEST_PATH"
echo "Engine build and tests completed successfully."
