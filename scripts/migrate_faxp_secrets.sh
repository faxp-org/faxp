#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-$HOME/.faxp-secrets}"
SOURCE_ENV="${2:-$PROJECT_DIR/security.env.local}"
SOURCE_REGISTRY="${3:-$PROJECT_DIR/faxp_agent_keys.local.json}"
SOURCE_KEYS_DIR="${4:-$PROJECT_DIR/keys}"

if [[ ! -f "$SOURCE_ENV" ]]; then
  echo "Missing source env file: $SOURCE_ENV" >&2
  exit 1
fi
if [[ ! -f "$SOURCE_REGISTRY" ]]; then
  echo "Missing source registry file: $SOURCE_REGISTRY" >&2
  exit 1
fi
if [[ ! -d "$SOURCE_KEYS_DIR" ]]; then
  echo "Missing source keys dir: $SOURCE_KEYS_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR/keys"
chmod 700 "$TARGET_DIR"

TARGET_ENV="$TARGET_DIR/security.env.local"
TARGET_REGISTRY="$TARGET_DIR/faxp_agent_keys.local.json"

cp -a "$SOURCE_KEYS_DIR/." "$TARGET_DIR/keys/"
cp "$SOURCE_ENV" "$TARGET_ENV"
cp "$SOURCE_REGISTRY" "$TARGET_REGISTRY"
chmod 600 "$TARGET_ENV" "$TARGET_REGISTRY"
find "$TARGET_DIR/keys" -type f -name '*private.pem' -exec chmod 600 {} \;
find "$TARGET_DIR/keys" -type f -name '*public.pem' -exec chmod 644 {} \;

export TARGET_ENV TARGET_REGISTRY SOURCE_KEYS_DIR TARGET_DIR
python3 - <<'PY'
import json
import os
from pathlib import Path

source_keys = os.path.realpath(os.environ["SOURCE_KEYS_DIR"])
target_dir = os.path.realpath(os.environ["TARGET_DIR"])
target_keys = os.path.realpath(os.path.join(target_dir, "keys"))
registry_path = Path(os.environ["TARGET_REGISTRY"])
env_path = Path(os.environ["TARGET_ENV"])

registry = json.loads(registry_path.read_text(encoding="utf-8"))
for _, agent in registry.items():
    if not isinstance(agent, dict):
        continue
    keys = agent.get("keys")
    if not isinstance(keys, dict):
        continue
    for _, details in keys.items():
        if not isinstance(details, dict):
            continue
        for field in ("private_key_path", "public_key_path"):
            raw = details.get(field)
            if not isinstance(raw, str):
                continue
            normalized = os.path.realpath(raw)
            if normalized.startswith(source_keys + os.sep):
                rel = os.path.relpath(normalized, source_keys)
                details[field] = os.path.join(target_keys, rel)
registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

lines = env_path.read_text(encoding="utf-8").splitlines()
updated = []
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        updated.append(line)
        continue
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()

    if key == "FAXP_AGENT_KEY_REGISTRY_FILE":
        value = str(registry_path)

    if key in {"FAXP_VERIFIER_ED25519_PUBLIC_KEYS", "FAXP_VERIFIER_ED25519_PRIVATE_KEYS"}:
        parts = []
        for chunk in value.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if ":" in chunk:
                kid, path = chunk.split(":", 1)
            elif "=" in chunk:
                kid, path = chunk.split("=", 1)
            else:
                parts.append(chunk)
                continue
            path_real = os.path.realpath(path.strip())
            if path_real.startswith(source_keys + os.sep):
                rel = os.path.relpath(path_real, source_keys)
                path_real = os.path.join(target_keys, rel)
            parts.append(f"{kid.strip()}:{path_real}")
        value = ",".join(parts)

    updated.append(f"{key}={value}")
env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
PY

cat <<EOF
Migration complete.
- New env: $TARGET_ENV
- New registry: $TARGET_REGISTRY
- New keys dir: $TARGET_DIR/keys

Recommended:
1) source $TARGET_ENV with:
   set -a; source $TARGET_ENV; set +a
2) Use ./scripts/run_secure_demo.sh
3) Remove in-repo local secret files if no longer needed.
EOF
