#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-${HOME}/.faxp-secrets/security.env.local}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

python3 - <<'PY'
import json
import os
import sys

keys = [
    "FAXP_SIGNATURE_SCHEME",
    "FAXP_MESSAGE_SIGNING_KEY",
    "FAXP_MESSAGE_SIGNING_KEYS",
    "FAXP_MESSAGE_SIGNING_ACTIVE_KEY_ID",
    "FAXP_MESSAGE_ACTIVE_KEY_ISSUED_AT",
    "FAXP_VERIFIER_SIGNATURE_SCHEME",
    "FAXP_VERIFIER_SIGNING_KEY",
    "FAXP_VERIFIER_SIGNING_KEYS",
    "FAXP_VERIFIER_SIGNING_ACTIVE_KEY_ID",
    "FAXP_VERIFIER_ACTIVE_KEY_ISSUED_AT",
    "FAXP_VERIFIER_ED25519_PRIVATE_KEYS",
    "FAXP_VERIFIER_ED25519_PUBLIC_KEYS",
    "FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID",
    "FAXP_AGENT_KEY_REGISTRY",
    "FAXP_AGENT_KEY_REGISTRY_FILE",
]

bundle = {}
for key in keys:
    value = os.getenv(key, "").strip()
    if value:
        bundle[key] = value

if not bundle:
    print("No FAXP secret bundle values found in env file.", file=sys.stderr)
    sys.exit(1)

print(json.dumps(bundle, sort_keys=True, separators=(",", ":")))
PY
