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

echo "[MCPConformance] Using Python: $PYTHON_BIN"

echo "[MCPConformance] Running MCP profile contract checks..."
"$PYTHON_BIN" "$PROJECT_DIR/tests/run_mcp_profile_check.py"

echo "[MCPConformance] MCP conformance checks passed."
