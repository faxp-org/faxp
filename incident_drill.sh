#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${HOME}/.faxp-secrets"
ENV_FILE="${1:-${SECRETS_DIR}/security.env.local}"
MC_NUMBER="${FAXP_INCIDENT_DRILL_MC_NUMBER:-498282}"
ROTATE_ON_DRILL="${FAXP_INCIDENT_DRILL_ROTATE:-0}"

SIM_SCRIPT="${PROJECT_ROOT}/faxp_mvp_simulation.py"
ROTATE_SCRIPT="${PROJECT_ROOT}/rotate_faxp_keys.sh"
SECURITY_GATE="${PROJECT_ROOT}/security_gate.sh"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[IncidentDrill] Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[IncidentDrill] python3 not found." >&2
  exit 1
fi

echo "[IncidentDrill] Loading environment from ${ENV_FILE}"
set -a
source "${ENV_FILE}"
set +a

tmp_ok="$(mktemp)"
tmp_fail="$(mktemp)"
trap 'rm -f "${tmp_ok}" "${tmp_fail}"' EXIT

echo "[IncidentDrill] Step 1/4: Baseline verification run (expect success)."
"${PYTHON_BIN}" "${SIM_SCRIPT}" \
  --provider FMCSA \
  --response Accept \
  --verification-status Success \
  --mc-number "${MC_NUMBER}" >"${tmp_ok}" 2>&1

if ! rg -q "Booking completed successfully" "${tmp_ok}" || ! rg -q "Truck capacity booking complete" "${tmp_ok}"; then
  echo "[IncidentDrill] Baseline run did not complete both flows." >&2
  tail -n 80 "${tmp_ok}" >&2
  exit 1
fi
echo "[IncidentDrill] Baseline run passed."

echo "[IncidentDrill] Step 2/4: Simulate verifier signing key incident (expect detection/fail-close)."
FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID="incident-compromised-kid" \
  "${PYTHON_BIN}" "${SIM_SCRIPT}" \
    --provider FMCSA \
    --response Accept \
    --verification-status Success \
    --mc-number "${MC_NUMBER}" >"${tmp_fail}" 2>&1 || true

if ! rg -q "verification failed|Verifier|active key ID .* not found in configured key ring" "${tmp_fail}"; then
  echo "[IncidentDrill] Incident scenario did not produce expected verification failure." >&2
  tail -n 80 "${tmp_fail}" >&2
  exit 1
fi
echo "[IncidentDrill] Incident detection/fail-close behavior confirmed."

echo "[IncidentDrill] Step 3/4: Security gate check."
bash "${SECURITY_GATE}" "${ENV_FILE}"
echo "[IncidentDrill] Security gate passed."

if [[ "${ROTATE_ON_DRILL}" == "1" ]]; then
  echo "[IncidentDrill] Step 4/4: Optional key rotation response."
  REGISTRY_FILE="${FAXP_AGENT_KEY_REGISTRY_FILE:-${SECRETS_DIR}/faxp_agent_keys.local.json}"
  KEY_DIR="${SECRETS_DIR}/keys"
  bash "${ROTATE_SCRIPT}" "${ENV_FILE}" "${REGISTRY_FILE}" "${KEY_DIR}" "5"
  echo "[IncidentDrill] Rotation completed."
else
  echo "[IncidentDrill] Step 4/4: Rotation skipped (set FAXP_INCIDENT_DRILL_ROTATE=1 to enable)."
fi

echo "[IncidentDrill] Complete."
