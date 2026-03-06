#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="${FAXP_SECRETS_DIR:-$HOME/.faxp-secrets}"
ENV_FILE="${FAXP_ENV_FILE:-$SECRETS_DIR/security.env.local}"
LOCAL_ENV_FALLBACK="$PROJECT_DIR/security.env.local"
MODE="sim"
MODE_SET=0
USE_KMS_COMMAND=0
KMS_BUNDLE_COMMAND=""
KMS_BUNDLE_ENV_FILE=""
EXTRA_ARGS=()

usage() {
  cat <<EOF
Usage: $0 [sim|streamlit|check] [--use-kms-command] [--kms-command '<command>'] [--kms-env-file <file>] [extra args]

Options:
  --use-kms-command     Export FAXP_EXTERNAL_SECRET_BUNDLE_COMMAND using fetch_faxp_bundle.sh.
  --kms-command CMD     Override bundle command string directly.
  --kms-env-file FILE   Env file path passed to fetch_faxp_bundle.sh (defaults to loaded ENV_FILE).
  -h, --help            Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    sim|streamlit|check)
      if [[ "$MODE_SET" -eq 0 ]]; then
        MODE="$1"
        MODE_SET=1
      else
        EXTRA_ARGS+=("$1")
      fi
      shift
      ;;
    --use-kms-command)
      USE_KMS_COMMAND=1
      shift
      ;;
    --kms-command)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --kms-command" >&2
        exit 1
      fi
      USE_KMS_COMMAND=1
      KMS_BUNDLE_COMMAND="$2"
      shift 2
      ;;
    --kms-command=*)
      USE_KMS_COMMAND=1
      KMS_BUNDLE_COMMAND="${1#*=}"
      shift
      ;;
    --kms-env-file)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --kms-env-file" >&2
        exit 1
      fi
      KMS_BUNDLE_ENV_FILE="$2"
      shift 2
      ;;
    --kms-env-file=*)
      KMS_BUNDLE_ENV_FILE="${1#*=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -d "$PROJECT_DIR/.venv" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.venv/bin/activate"
fi

if [[ ! -f "$ENV_FILE" && -f "$LOCAL_ENV_FALLBACK" ]]; then
  ENV_FILE="$LOCAL_ENV_FALLBACK"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Security env file not found: $ENV_FILE" >&2
  echo "Set FAXP_ENV_FILE or place security.env.local in $SECRETS_DIR." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ "$USE_KMS_COMMAND" -eq 1 ]]; then
  KMS_BUNDLE_SCRIPT="${FAXP_KMS_BUNDLE_SCRIPT:-$PROJECT_DIR/scripts/fetch_faxp_bundle.sh}"
  if [[ -z "$KMS_BUNDLE_COMMAND" ]]; then
    if [[ -z "$KMS_BUNDLE_ENV_FILE" ]]; then
      KMS_BUNDLE_ENV_FILE="$ENV_FILE"
    fi
    if [[ ! -f "$KMS_BUNDLE_SCRIPT" ]]; then
      echo "KMS bundle helper not found: $KMS_BUNDLE_SCRIPT" >&2
      exit 1
    fi
    if [[ ! -f "$KMS_BUNDLE_ENV_FILE" ]]; then
      echo "KMS bundle env file not found: $KMS_BUNDLE_ENV_FILE" >&2
      exit 1
    fi
    printf -v KMS_BUNDLE_COMMAND "bash %q %q" "$KMS_BUNDLE_SCRIPT" "$KMS_BUNDLE_ENV_FILE"
  fi
  export FAXP_EXTERNAL_SECRET_BUNDLE_COMMAND="$KMS_BUNDLE_COMMAND"
  echo "[SecureRunner] Using external secret bundle command."
fi

required_vars=(
  FAXP_APP_MODE
  FAXP_SIGNATURE_SCHEME
  FAXP_AGENT_KEY_REGISTRY_FILE
  FAXP_REQUIRE_SIGNED_VERIFIER
  FAXP_VERIFIER_SIGNATURE_SCHEME
)

for key in "${required_vars[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env var: $key" >&2
    exit 1
  fi
done

if [[ ! -f "${FAXP_AGENT_KEY_REGISTRY_FILE}" ]]; then
  echo "Agent key registry not found: ${FAXP_AGENT_KEY_REGISTRY_FILE}" >&2
  exit 1
fi

check_ring_paths() {
  local ring="$1"
  local label="$2"
  [[ -z "$ring" ]] && return 0
  IFS=',' read -r -a entries <<< "$ring"
  for entry in "${entries[@]}"; do
    [[ -z "$entry" ]] && continue
    if [[ "$entry" == *:* ]]; then
      local path="${entry#*:}"
      if [[ ! -f "$path" ]]; then
        echo "Missing $label key path: $path" >&2
        exit 1
      fi
    fi
  done
}

if [[ "${FAXP_VERIFIER_SIGNATURE_SCHEME}" == "ED25519" ]]; then
  check_ring_paths "${FAXP_VERIFIER_ED25519_PUBLIC_KEYS:-}" "verifier public"
  check_ring_paths "${FAXP_VERIFIER_ED25519_PRIVATE_KEYS:-}" "verifier private"
fi

case "$MODE" in
  sim)
    if [[ "${#EXTRA_ARGS[@]}" -gt 0 ]]; then
      python3 "$PROJECT_DIR/faxp_mvp_simulation.py" --provider MockComplianceProvider "${EXTRA_ARGS[@]}"
    else
      python3 "$PROJECT_DIR/faxp_mvp_simulation.py" --provider MockComplianceProvider
    fi
    ;;
  streamlit)
    if command -v streamlit >/dev/null 2>&1; then
      if [[ "${#EXTRA_ARGS[@]}" -gt 0 ]]; then
        streamlit run "$PROJECT_DIR/streamlit_app.py" "${EXTRA_ARGS[@]}"
      else
        streamlit run "$PROJECT_DIR/streamlit_app.py"
      fi
    else
      if [[ "${#EXTRA_ARGS[@]}" -gt 0 ]]; then
        "$PROJECT_DIR/.venv/bin/streamlit" run "$PROJECT_DIR/streamlit_app.py" "${EXTRA_ARGS[@]}"
      else
        "$PROJECT_DIR/.venv/bin/streamlit" run "$PROJECT_DIR/streamlit_app.py"
      fi
    fi
    ;;
  check)
    if [[ "${#EXTRA_ARGS[@]}" -gt 0 ]]; then
      python3 "$PROJECT_DIR/faxp_mvp_simulation.py" --security-self-test --self-test-iterations 25 "${EXTRA_ARGS[@]}"
    else
      python3 "$PROJECT_DIR/faxp_mvp_simulation.py" --security-self-test --self-test-iterations 25
    fi
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
