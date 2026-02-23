#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$PROJECT_DIR/security.env.template}"
FAILED=0

note() { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
fail() { printf '[FAIL] %s\n' "$*"; FAILED=1; }

check_env_equals() {
  local file="$1"
  local key="$2"
  local expected="$3"
  local actual
  actual="$(awk -F= -v k="$key" '$1==k {print substr($0,index($0,"=")+1)}' "$file" | tail -n 1)"
  if [[ -z "$actual" ]]; then
    fail "Missing $key in $file"
    return
  fi
  if [[ "$actual" != "$expected" ]]; then
    fail "$key expected '$expected' but found '$actual'"
  else
    note "$key=$expected"
  fi
}

if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  note "Git repository detected. Running tracked-secret checks."
  tracked_sensitive="$(
    git -C "$PROJECT_DIR" ls-files | rg -n \
      '(^|/)(security\.env\.local|security\.env\.filled|faxp_agent_keys\.local\.json|faxp_agent_keys\.filled\.json|keys/|.*\.bak\.)' \
      || true
  )"
  if [[ -n "$tracked_sensitive" ]]; then
    fail "Sensitive files are tracked by git:\n$tracked_sensitive"
  else
    note "No tracked secret files detected."
  fi
else
  warn "No git repository found at $PROJECT_DIR. Skipping tracked-secret checks."
fi

if [[ -f "$ENV_FILE" ]]; then
  note "Validating security defaults in $ENV_FILE"
  check_env_equals "$ENV_FILE" "FAXP_REQUIRE_SIGNED_VERIFIER" "1"
  check_env_equals "$ENV_FILE" "FAXP_SIGNATURE_SCHEME" "ED25519"
  check_env_equals "$ENV_FILE" "FAXP_VERIFIER_SIGNATURE_SCHEME" "ED25519"
  check_env_equals "$ENV_FILE" "FAXP_FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER" "1"
  check_env_equals "$ENV_FILE" "FAXP_FMCSA_ADAPTER_SIGN_REQUESTS" "1"
else
  warn "Env file not found for checks: $ENV_FILE"
fi

if [[ "$FAILED" -ne 0 ]]; then
  exit 1
fi

note "Security gate checks passed."
