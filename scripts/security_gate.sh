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

scan_tracked_content_secrets() {
  local pattern
  # SECURITY_GATE_SELFSCAN_IGNORE_BEGIN
  pattern='AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}|sk_live_[0-9A-Za-z]{24,}|sk_test_[0-9A-Za-z]{24,}'
  # SECURITY_GATE_SELFSCAN_IGNORE_END
  local hits
  hits="$(git -C "$PROJECT_DIR" grep -nE "$pattern" -- . ':!security.env.template' || true)"
  if [[ -n "$hits" ]]; then
    fail "Potential secret material detected in tracked content:\n$hits"
  else
    note "No high-signal secret patterns detected in tracked content."
  fi
}

scan_tracked_content_obfuscated_and_encoded() {
  local hits
  hits="$(
    python3 - "$PROJECT_DIR" <<'PY'
import base64
import binascii
from pathlib import Path
import re
import subprocess
import sys

project_dir = Path(sys.argv[1]).resolve()

# SECURITY_GATE_SELFSCAN_IGNORE_BEGIN
high_signal_pattern = re.compile(
    r"AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}|sk_live_[0-9A-Za-z]{24,}|sk_test_[0-9A-Za-z]{24,}",
    re.IGNORECASE,
)

normalized_patterns = [
    ("aws-access-key-id", re.compile(r"(AKIA|ASIA)[A-Z0-9]{16}")),
    ("github-classic-token", re.compile(r"GHP[A-Z0-9]{36}")),
    ("github-fine-grained-token", re.compile(r"GITHUBPAT[A-Z0-9]{60,}")),
    ("slack-token", re.compile(r"XOX[BAPRS][A-Z0-9]{10,}")),
    ("google-api-key", re.compile(r"AIZA[0-9A-Z]{35}")),
    ("stripe-live-key", re.compile(r"SKLIVE[0-9A-Z]{24,}")),
    ("stripe-test-key", re.compile(r"SKTEST[0-9A-Z]{24,}")),
    ("private-key-marker", re.compile(r"BEGIN[A-Z]*PRIVATEKEY")),
]

base64_candidate_pattern = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/])")
chunked_base64_fragment_pattern = re.compile(r"[A-Za-z0-9+/]{3,}={0,2}")
# SECURITY_GATE_SELFSCAN_IGNORE_END
max_base64_candidates_per_file = 50000
max_base64_decoded_bytes_per_file = 8 * 1024 * 1024

completed = subprocess.run(
    ["git", "-C", str(project_dir), "ls-files", "-z"],
    check=True,
    capture_output=True,
)
tracked_files = [
    item
    for item in completed.stdout.decode("utf-8", "ignore").split("\0")
    if item and item != "security.env.template"
]

findings = []

def _normalize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def _evaluate_decoded_candidate(token: str):
    token = token.strip()
    if not token:
        return False, 0
    padded = token + ("=" * ((4 - len(token) % 4) % 4))
    try:
        decoded = base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError):
        return False, 0
    if len(decoded) < 12:
        return False, 0
    printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in decoded)
    if printable / len(decoded) < 0.85:
        return False, len(decoded)
    decoded_text = decoded.decode("utf-8", "ignore")
    if not decoded_text:
        return False, len(decoded)
    decoded_normalized = _normalize(decoded_text)
    hit = bool(high_signal_pattern.search(decoded_text))
    if not hit:
        for _, pattern in normalized_patterns:
            if pattern.search(decoded_normalized):
                hit = True
                break
    return hit, len(decoded)


for rel_path in tracked_files:
    path = project_dir / rel_path
    try:
        raw_bytes = path.read_bytes()
    except OSError:
        continue
    if b"\x00" in raw_bytes:
        continue
    text = raw_bytes.decode("utf-8", "ignore")
    lines = text.splitlines()
    candidate_count = 0
    decoded_bytes = 0
    budget_exhausted = False
    in_selfscan_ignore_block = False
    for line_no, line in enumerate(lines, start=1):
        if rel_path == "scripts/security_gate.sh":
            if "SECURITY_GATE_SELFSCAN_IGNORE_BEGIN" in line:
                in_selfscan_ignore_block = True
                continue
            if "SECURITY_GATE_SELFSCAN_IGNORE_END" in line:
                in_selfscan_ignore_block = False
                continue
            if in_selfscan_ignore_block:
                continue

        normalized_line = _normalize(line)
        for label, pattern in normalized_patterns:
            if pattern.search(normalized_line):
                findings.append(f"{rel_path}:{line_no}:normalized-{label}")
                break

        for match in base64_candidate_pattern.finditer(line):
            candidate_count += 1
            if candidate_count > max_base64_candidates_per_file:
                findings.append(
                    f"{rel_path}:{line_no}:base64-scan-budget-exhausted(candidates)"
                )
                budget_exhausted = True
                break

            token = match.group(0).strip()
            hit, consumed_bytes = _evaluate_decoded_candidate(token)
            decoded_bytes += consumed_bytes
            if decoded_bytes > max_base64_decoded_bytes_per_file:
                findings.append(
                    f"{rel_path}:{line_no}:base64-scan-budget-exhausted(bytes)"
                )
                budget_exhausted = True
                break
            if hit:
                findings.append(f"{rel_path}:{line_no}:base64-decoded-secret-like-content")
                break
        if not budget_exhausted:
            fragments = chunked_base64_fragment_pattern.findall(line)
            has_chunk_separators = bool(re.search(r"[^A-Za-z0-9+/=\s]", line))
            if has_chunk_separators and len(fragments) >= 4:
                rebuilt = "".join(
                    fragment.rstrip("=") if idx < len(fragments) - 1 else fragment
                    for idx, fragment in enumerate(fragments)
                )
                if len(rebuilt) >= 24:
                    candidate_count += 1
                    if candidate_count > max_base64_candidates_per_file:
                        findings.append(
                            f"{rel_path}:{line_no}:base64-scan-budget-exhausted(candidates)"
                        )
                        budget_exhausted = True
                    else:
                        hit, consumed_bytes = _evaluate_decoded_candidate(rebuilt)
                        decoded_bytes += consumed_bytes
                        if decoded_bytes > max_base64_decoded_bytes_per_file:
                            findings.append(
                                f"{rel_path}:{line_no}:base64-scan-budget-exhausted(bytes)"
                            )
                            budget_exhausted = True
                        elif hit:
                            findings.append(
                                f"{rel_path}:{line_no}:base64-decoded-secret-like-content"
                            )
        if budget_exhausted:
            break

if findings:
    print("\n".join(findings))
PY
  )"

  if [[ -n "$hits" ]]; then
    fail "Potential obfuscated/encoded secret material detected in tracked content:\n$hits"
  else
    note "No obfuscated/encoded secret patterns detected in tracked content."
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
  scan_tracked_content_secrets
  scan_tracked_content_obfuscated_and_encoded
else
  warn "No git repository found at $PROJECT_DIR. Skipping tracked-secret checks."
fi

if [[ -f "$ENV_FILE" ]]; then
  note "Validating security defaults in $ENV_FILE"
  check_env_equals "$ENV_FILE" "FAXP_REQUIRE_SIGNED_VERIFIER" "1"
  check_env_equals "$ENV_FILE" "FAXP_SIGNATURE_SCHEME" "ED25519"
  check_env_equals "$ENV_FILE" "FAXP_VERIFIER_SIGNATURE_SCHEME" "ED25519"
  check_env_equals "$ENV_FILE" "FAXP_ENFORCE_TRUSTED_VERIFIER_REGISTRY" "1"
else
  warn "Env file not found for checks: $ENV_FILE"
fi

if [[ "$FAILED" -ne 0 ]]; then
  exit 1
fi

note "Security gate checks passed."
