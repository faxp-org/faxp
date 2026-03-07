#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[install_precommit] python3 is required but not found in PATH." >&2
  exit 1
fi

python3 -m pip install --upgrade pip pre-commit
cd "$PROJECT_DIR"
python3 -m pre_commit install

echo "[install_precommit] pre-commit hook installed."
echo "[install_precommit] Run manually anytime with: pre-commit run --all-files"
