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

REPORT_PATH="${1:-/tmp/faxp_conformance_suite_report.local_smoke.json}"

echo "[ReleaseSmokeLocal] Project: $PROJECT_DIR"
echo "[ReleaseSmokeLocal] Python:  $PYTHON_BIN"
echo "[ReleaseSmokeLocal] Report:  $REPORT_PATH"
echo "[ReleaseSmokeLocal] Forcing FAXP_APP_MODE=local for this run."

(
  export FAXP_APP_MODE=local
  "$PROJECT_DIR/scripts/run_a2a_conformance.sh"
  "$PROJECT_DIR/scripts/run_mcp_conformance.sh"
  "$PYTHON_BIN" "$PROJECT_DIR/conformance/run_all_checks.py" --output "$REPORT_PATH"
  "$PYTHON_BIN" "$PROJECT_DIR/tests/run_release_readiness.py"
)

echo "[ReleaseSmokeLocal] Complete."
