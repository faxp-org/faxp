#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 not found in PATH." >&2
  exit 1
fi

cd "$PROJECT_DIR"

if [[ ! -d ".venv" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"

python3 -m pip install -U pip
python3 -m pip install -r requirements.txt

cat <<'EOF'
[BootstrapDemoEnv] Local demo environment is ready.

Next steps:
1) Generate local demo secrets:
   ./scripts/generate_faxp_keys.sh "$HOME/.faxp-secrets"

2) Load the generated env:
   set -a
   source "$HOME/.faxp-secrets/security.env.local"
   set +a

3) Run local smoke checks:
   ./scripts/run_release_smoke_local.sh

4) Start the Streamlit demo:
   ./scripts/run_secure_demo.sh streamlit

Guide:
   docs/STREAMLIT_QUICKSTART.md
EOF
