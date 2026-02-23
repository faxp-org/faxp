#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 not found in PATH." >&2
  exit 1
fi

echo "[A2AConformance] Using Python: $PYTHON_BIN"

echo "[A2AConformance] Running profile contract checks..."
"$PYTHON_BIN" "$PROJECT_DIR/tests/run_a2a_profile_check.py"

echo "[A2AConformance] Running round-trip translation checks..."
"$PYTHON_BIN" "$PROJECT_DIR/tests/run_a2a_roundtrip_translation.py"

echo "[A2AConformance] Running A2A watch artifact checks..."
"$PYTHON_BIN" "$PROJECT_DIR/tests/run_a2a_watch_artifacts.py"

echo "[A2AConformance] All A2A conformance checks passed."
