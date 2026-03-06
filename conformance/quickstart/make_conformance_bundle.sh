#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${1:-${PROJECT_ROOT}/conformance/quickstart/out}"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-${PROJECT_ROOT}/.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

mkdir -p "${OUT_DIR}"

PROFILE_PATH="${OUT_DIR}/adapter_profile.json"
REGISTRY_ENTRY_PATH="${OUT_DIR}/certification_registry.entry.json"
KEYRING_PATH="${OUT_DIR}/attestation_keys.json"
REPORT_PATH="${OUT_DIR}/conformance_report.json"

cp "${SCRIPT_DIR}/adapter_profile.template.json" "${PROFILE_PATH}"
cp "${SCRIPT_DIR}/certification_registry.entry.template.json" "${REGISTRY_ENTRY_PATH}"

ADAPTER_ID="${FAXP_ADAPTER_ID:-quickstart-adapter-$(date -u +%Y%m%d%H%M%S)}"
ENDPOINT_URL="${FAXP_ADAPTER_ENDPOINT_URL:-https://adapter.example/v1/verify}"
PROFILE_NAME="${FAXP_VERIFICATION_PROFILE:-US_VERIFICATION_BALANCED_V1}"
ATTEST_KID="${FAXP_ATTESTATION_KID:-quickstart-kid-$(date -u +%Y%m%d)}"
ATTEST_SECRET="${FAXP_ATTESTATION_SECRET:-}"
ATTESTED_BY="${FAXP_ATTESTED_BY:-Quickstart Security}"
ATTESTOR_ROLE="${FAXP_ATTESTOR_ROLE:-SecurityOfficer}"

if [[ -z "${ATTEST_SECRET}" ]]; then
  ATTEST_SECRET="$("${PYTHON_BIN}" - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)"
fi

"${PYTHON_BIN}" - <<PY
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

profile_path = Path("${PROFILE_PATH}")
registry_path = Path("${REGISTRY_ENTRY_PATH}")

profile = json.loads(profile_path.read_text(encoding="utf-8"))
entry = json.loads(registry_path.read_text(encoding="utf-8"))

now = datetime.now(timezone.utc).replace(microsecond=0)
expires = now + timedelta(days=180)
now_text = now.isoformat().replace("+00:00", "Z")
expires_text = expires.isoformat().replace("+00:00", "Z")

profile["adapterId"] = "${ADAPTER_ID}"
profile["endpointBaseUrl"] = "${ENDPOINT_URL}"
profile["profilesSupported"] = ["${PROFILE_NAME}"]
profile["selfAttestation"]["attestedBy"] = "${ATTESTED_BY}"
profile["selfAttestation"]["attestorRole"] = "${ATTESTOR_ROLE}"
profile["selfAttestation"]["kid"] = "${ATTEST_KID}"
profile["selfAttestation"]["signedAt"] = now_text
profile["selfAttestation"]["expiresAt"] = expires_text

entry["adapterId"] = "${ADAPTER_ID}"
entry["profilesSupported"] = ["${PROFILE_NAME}"]
entry["selfAttestationKid"] = "${ATTEST_KID}"
entry["lastCertifiedAt"] = now_text
entry["expiresAt"] = expires_text

profile_path.write_text(json.dumps(profile, indent=2) + "\\n", encoding="utf-8")
registry_path.write_text(json.dumps(entry, indent=2) + "\\n", encoding="utf-8")
PY

"${PYTHON_BIN}" - <<PY
import json
from pathlib import Path
Path("${KEYRING_PATH}").write_text(
    json.dumps({"keys": {"${ATTEST_KID}": "${ATTEST_SECRET}"}}, indent=2) + "\\n",
    encoding="utf-8",
)
PY

"${PYTHON_BIN}" "${PROJECT_ROOT}/conformance/generate_attestation.py" \
  --profile "${PROFILE_PATH}" \
  --keyring "${KEYRING_PATH}" \
  --kid "${ATTEST_KID}" \
  --in-place

"${PYTHON_BIN}" "${PROJECT_ROOT}/tests/run_conformance_bundle.py" \
  --profile "${PROFILE_PATH}" \
  --registry-entry "${REGISTRY_ENTRY_PATH}" \
  --keyring "${KEYRING_PATH}" \
  --output "${REPORT_PATH}"

"${PYTHON_BIN}" - <<PY
import json
from pathlib import Path
registry_path = Path("${REGISTRY_ENTRY_PATH}")
report_path = Path("${REPORT_PATH}")
entry = json.loads(registry_path.read_text(encoding="utf-8"))
report = json.loads(report_path.read_text(encoding="utf-8"))
entry["conformanceReportRef"] = report["reportHash"]
registry_path.write_text(json.dumps(entry, indent=2) + "\\n", encoding="utf-8")
PY

echo "[Quickstart] Conformance bundle ready in ${OUT_DIR}"
echo "[Quickstart] Adapter profile: ${PROFILE_PATH}"
echo "[Quickstart] Registry entry: ${REGISTRY_ENTRY_PATH}"
echo "[Quickstart] Keyring (test-only): ${KEYRING_PATH}"
echo "[Quickstart] Conformance report: ${REPORT_PATH}"
