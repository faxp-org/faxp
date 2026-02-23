#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="${FAXP_SECRETS_DIR:-$HOME/.faxp-secrets}"
SECURITY_ENV_FILE="${1:-$SECRETS_DIR/security.env.local}"
AGENT_REGISTRY_FILE="${2:-$SECRETS_DIR/faxp_agent_keys.local.json}"
KEY_DIR="${3:-$SECRETS_DIR/keys}"
KEEP_GENERATIONS="${4:-${FAXP_KEEP_KEY_GENERATIONS:-5}}"

mkdir -p "$KEY_DIR"

if [[ ! -f "$SECURITY_ENV_FILE" ]]; then
  echo "Missing security env file: $SECURITY_ENV_FILE" >&2
  exit 1
fi
if [[ ! -f "$AGENT_REGISTRY_FILE" ]]; then
  echo "Missing agent key registry file: $AGENT_REGISTRY_FILE" >&2
  exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl not found in PATH." >&2
  exit 1
fi
if ! [[ "$KEEP_GENERATIONS" =~ ^[0-9]+$ ]] || [[ "$KEEP_GENERATIONS" -lt 1 ]]; then
  echo "KEEP_GENERATIONS must be a positive integer." >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%d%H%M%S)"
ISSUED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
BACKUP_SUFFIX="bak.$STAMP"

BROKER_KID="broker-$STAMP"
CARRIER_KID="carrier-$STAMP"
VERIFIER_KID="verifier-$STAMP"
MESSAGE_HMAC_KID="msg-$STAMP"
VERIFIER_HMAC_KID="verhmac-$STAMP"

BROKER_PRIV="$KEY_DIR/${BROKER_KID}-private.pem"
BROKER_PUB="$KEY_DIR/${BROKER_KID}-public.pem"
CARRIER_PRIV="$KEY_DIR/${CARRIER_KID}-private.pem"
CARRIER_PUB="$KEY_DIR/${CARRIER_KID}-public.pem"
VERIFIER_PRIV="$KEY_DIR/${VERIFIER_KID}-private.pem"
VERIFIER_PUB="$KEY_DIR/${VERIFIER_KID}-public.pem"

generate_ed25519_pair() {
  local priv="$1"
  local pub="$2"
  openssl genpkey -algorithm ED25519 -out "$priv" >/dev/null 2>&1
  openssl pkey -in "$priv" -pubout -out "$pub" >/dev/null 2>&1
  chmod 600 "$priv"
  chmod 644 "$pub"
}

generate_ed25519_pair "$BROKER_PRIV" "$BROKER_PUB"
generate_ed25519_pair "$CARRIER_PRIV" "$CARRIER_PUB"
generate_ed25519_pair "$VERIFIER_PRIV" "$VERIFIER_PUB"

MESSAGE_HMAC_KEY="$(openssl rand -hex 32)"
VERIFIER_HMAC_KEY="$(openssl rand -hex 32)"

cp "$SECURITY_ENV_FILE" "$SECURITY_ENV_FILE.$BACKUP_SUFFIX"
cp "$AGENT_REGISTRY_FILE" "$AGENT_REGISTRY_FILE.$BACKUP_SUFFIX"

export AGENT_REGISTRY_FILE SECURITY_ENV_FILE ISSUED_AT KEEP_GENERATIONS
export BROKER_KID CARRIER_KID VERIFIER_KID
export BROKER_PRIV BROKER_PUB CARRIER_PRIV CARRIER_PUB VERIFIER_PRIV VERIFIER_PUB
export MESSAGE_HMAC_KID MESSAGE_HMAC_KEY VERIFIER_HMAC_KID VERIFIER_HMAC_KEY

python3 - <<'PY'
import json
import os
from pathlib import Path

keep_generations = int(os.environ["KEEP_GENERATIONS"])


def load_registry(path):
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)


def ensure_agent(registry, agent_name):
    agent = registry.setdefault(agent_name, {})
    if not isinstance(agent, dict):
        agent = {}
        registry[agent_name] = agent
    keys = agent.setdefault("keys", {})
    if not isinstance(keys, dict):
        keys = {}
        agent["keys"] = keys
    return agent


def add_agent_key(registry, agent_name, kid, priv, pub, issued_at):
    agent = ensure_agent(registry, agent_name)
    agent["keys"][kid] = {
        "private_key_path": priv,
        "public_key_path": pub,
        "issued_at": issued_at,
    }
    agent["active_kid"] = kid


def trim_agent_keys(registry):
    for _, agent in registry.items():
        if not isinstance(agent, dict):
            continue
        keys = agent.get("keys")
        if not isinstance(keys, dict):
            continue
        ordered = sorted(
            keys.items(),
            key=lambda item: (
                str(item[1].get("issued_at", "")) if isinstance(item[1], dict) else "",
                item[0],
            ),
            reverse=True,
        )
        kept = dict(ordered[:keep_generations])
        agent["keys"] = kept
        active = agent.get("active_kid")
        if active not in kept and kept:
            agent["active_kid"] = next(iter(kept.keys()))


def parse_ring(value):
    pairs = []
    if not value:
        return pairs
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            kid, val = chunk.split(":", 1)
        elif "=" in chunk:
            kid, val = chunk.split("=", 1)
        else:
            continue
        kid = kid.strip()
        val = val.strip()
        if kid and val:
            pairs.append((kid, val))
    return pairs


def prepend_ring(current, kid, value):
    merged = [(kid, value)]
    for existing_kid, existing_value in parse_ring(current):
        if existing_kid != kid:
            merged.append((existing_kid, existing_value))
    merged = merged[:keep_generations]
    return ",".join(f"{k}:{v}" for k, v in merged)


def update_env_file(path, updates):
    original_lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    index_by_key = {}
    for idx, line in enumerate(original_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        index_by_key.setdefault(key, []).append(idx)

    lines = list(original_lines)
    for key, value in updates.items():
        replacement = f"{key}={value}\n"
        if key in index_by_key:
            first = index_by_key[key][0]
            lines[first] = replacement
            for extra in index_by_key[key][1:]:
                lines[extra] = f"# {lines[extra].rstrip()} (superseded)\n"
        else:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] = lines[-1] + "\n"
            lines.append(replacement)
    Path(path).write_text("".join(lines), encoding="utf-8")


registry_path = os.environ["AGENT_REGISTRY_FILE"]
registry = load_registry(registry_path)
issued_at = os.environ["ISSUED_AT"]

add_agent_key(
    registry,
    "Broker Agent",
    os.environ["BROKER_KID"],
    os.environ["BROKER_PRIV"],
    os.environ["BROKER_PUB"],
    issued_at,
)
add_agent_key(
    registry,
    "Carrier Agent",
    os.environ["CARRIER_KID"],
    os.environ["CARRIER_PRIV"],
    os.environ["CARRIER_PUB"],
    issued_at,
)
add_agent_key(
    registry,
    "Verifier Wrapper",
    os.environ["VERIFIER_KID"],
    os.environ["VERIFIER_PRIV"],
    os.environ["VERIFIER_PUB"],
    issued_at,
)
trim_agent_keys(registry)
Path(registry_path).write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

env_path = os.environ["SECURITY_ENV_FILE"]
env_map = {}
for raw_line in Path(env_path).read_text(encoding="utf-8").splitlines():
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    key, value = stripped.split("=", 1)
    env_map[key.strip()] = value.strip()

updates = {
    "FAXP_SIGNATURE_SCHEME": "ED25519",
    "FAXP_AGENT_KEY_REGISTRY_FILE": registry_path,
    "FAXP_REQUIRE_SIGNED_VERIFIER": "1",
    "FAXP_VERIFIER_SIGNATURE_SCHEME": "ED25519",
    "FAXP_VERIFIER_ED25519_PUBLIC_KEYS": prepend_ring(
        env_map.get("FAXP_VERIFIER_ED25519_PUBLIC_KEYS", ""),
        os.environ["VERIFIER_KID"],
        os.environ["VERIFIER_PUB"],
    ),
    "FAXP_VERIFIER_ED25519_PRIVATE_KEYS": prepend_ring(
        env_map.get("FAXP_VERIFIER_ED25519_PRIVATE_KEYS", ""),
        os.environ["VERIFIER_KID"],
        os.environ["VERIFIER_PRIV"],
    ),
    "FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID": os.environ["VERIFIER_KID"],
    "FAXP_MESSAGE_SIGNING_KEYS": prepend_ring(
        env_map.get("FAXP_MESSAGE_SIGNING_KEYS", ""),
        os.environ["MESSAGE_HMAC_KID"],
        os.environ["MESSAGE_HMAC_KEY"],
    ),
    "FAXP_MESSAGE_SIGNING_ACTIVE_KEY_ID": os.environ["MESSAGE_HMAC_KID"],
    "FAXP_VERIFIER_SIGNING_KEYS": prepend_ring(
        env_map.get("FAXP_VERIFIER_SIGNING_KEYS", ""),
        os.environ["VERIFIER_HMAC_KID"],
        os.environ["VERIFIER_HMAC_KEY"],
    ),
    "FAXP_VERIFIER_SIGNING_ACTIVE_KEY_ID": os.environ["VERIFIER_HMAC_KID"],
    "FAXP_MESSAGE_ACTIVE_KEY_ISSUED_AT": issued_at,
    "FAXP_VERIFIER_ACTIVE_KEY_ISSUED_AT": issued_at,
}
update_env_file(env_path, updates)
PY

# Prune old key files not referenced in the trimmed registry.
export KEY_DIR
python3 - <<'PY'
import json
import os
from pathlib import Path

registry = json.loads(Path(os.environ["AGENT_REGISTRY_FILE"]).read_text(encoding="utf-8"))
key_dir = Path(os.environ["KEY_DIR"]).resolve()

referenced = set()
for _, agent in registry.items():
    keys = agent.get("keys", {}) if isinstance(agent, dict) else {}
    if not isinstance(keys, dict):
        continue
    for _, details in keys.items():
        if not isinstance(details, dict):
            continue
        for field in ("private_key_path", "public_key_path"):
            value = details.get(field)
            if isinstance(value, str) and value:
                referenced.add(str(Path(value).resolve()))

for path in key_dir.glob("*-private.pem"):
    resolved = str(path.resolve())
    if resolved not in referenced:
        path.unlink(missing_ok=True)
for path in key_dir.glob("*-public.pem"):
    resolved = str(path.resolve())
    if resolved not in referenced:
        path.unlink(missing_ok=True)
PY

chmod 600 "$SECURITY_ENV_FILE" "$AGENT_REGISTRY_FILE"

echo "Rotated FAXP keys successfully."
echo "Retention: KEEP_GENERATIONS=$KEEP_GENERATIONS"
echo "Backups:"
echo "- $SECURITY_ENV_FILE.$BACKUP_SUFFIX"
echo "- $AGENT_REGISTRY_FILE.$BACKUP_SUFFIX"
echo
echo "Updated files:"
echo "- $SECURITY_ENV_FILE"
echo "- $AGENT_REGISTRY_FILE"
echo "- $KEY_DIR"
