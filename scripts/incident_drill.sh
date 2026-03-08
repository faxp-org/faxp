#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="${HOME}/.faxp-secrets"
ENV_FILE="${1:-${SECRETS_DIR}/security.env.local}"
MC_NUMBER="${FAXP_INCIDENT_DRILL_MC_NUMBER:-498282}"
ROTATE_ON_DRILL="${FAXP_INCIDENT_DRILL_ROTATE:-0}"
DRILL_PROVIDER="${FAXP_INCIDENT_DRILL_PROVIDER:-MockComplianceProvider}"
REQUIRE_TRUCK_FLOW="${FAXP_INCIDENT_DRILL_REQUIRE_TRUCK_FLOW:-1}"
INCIDENT_ARTIFACT_PATH="${FAXP_INCIDENT_ARTIFACT_PATH:-/tmp/faxp_replay_incident_artifact.json}"
INCIDENT_ROUTING_TARGET="${FAXP_INCIDENT_ROUTING_TARGET:-replay-oncall}"
INCIDENT_TICKET_REF="${FAXP_INCIDENT_TICKET_REF:-none}"

SIM_SCRIPT="${PROJECT_ROOT}/faxp_mvp_simulation.py"
ROTATE_SCRIPT="${PROJECT_ROOT}/scripts/rotate_faxp_keys.sh"
SECURITY_GATE="${PROJECT_ROOT}/scripts/security_gate.sh"

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

DRILL_STARTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
STEP1_TIME="${DRILL_STARTED_AT}"
STEP2_TIME="${DRILL_STARTED_AT}"
STEP3_TIME="${DRILL_STARTED_AT}"
STEP4_TIME="${DRILL_STARTED_AT}"
BASELINE_RESULT="not_run"
INCIDENT_FAILCLOSE_RESULT="not_run"
SECURITY_GATE_RESULT="not_run"
ROTATION_RESULT="not_run"
LAST_FAILURE_REASON=""

finalize() {
  local exit_code="$1"
  local finished_at
  local status
  finished_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  if [[ "${exit_code}" -eq 0 ]]; then
    status="pass"
  else
    status="fail"
  fi
  mkdir -p "$(dirname "${INCIDENT_ARTIFACT_PATH}")"
  "${PYTHON_BIN}" - <<'PY' "${INCIDENT_ARTIFACT_PATH}" "${status}" "${DRILL_STARTED_AT}" "${finished_at}" "${STEP1_TIME}" "${STEP2_TIME}" "${STEP3_TIME}" "${STEP4_TIME}" "${BASELINE_RESULT}" "${INCIDENT_FAILCLOSE_RESULT}" "${SECURITY_GATE_RESULT}" "${ROTATION_RESULT}" "${LAST_FAILURE_REASON}" "${INCIDENT_ROUTING_TARGET}" "${INCIDENT_TICKET_REF}" "${ROTATE_ON_DRILL}"
import json
import sys
from pathlib import Path

(
    artifact_path,
    status,
    started_at,
    finished_at,
    step1_time,
    step2_time,
    step3_time,
    step4_time,
    baseline_result,
    incident_result,
    security_gate_result,
    rotation_result,
    failure_reason,
    routing_target,
    incident_ticket_ref,
    rotate_on_drill,
) = sys.argv[1:17]

payload = {
    "artifactVersion": "1.0.0",
    "drillType": "replay_incident",
    "startedAt": started_at,
    "finishedAt": finished_at,
    "status": status,
    "routingTarget": routing_target,
    "incidentTicketRef": incident_ticket_ref,
    "timeline": [
        {"time": step1_time, "event": "baseline_verification", "result": baseline_result},
        {"time": step2_time, "event": "incident_fail_closed_check", "result": incident_result},
        {"time": step3_time, "event": "security_gate_check", "result": security_gate_result},
        {"time": step4_time, "event": "rotation_response", "result": rotation_result},
    ],
    "decisions": [
        f"rotation_requested={rotate_on_drill}",
        f"fail_closed_observed={str(incident_result == 'pass').lower()}",
        f"routing_target={routing_target}",
    ],
    "closureNotes": (
        "Incident drill completed successfully."
        if status == "pass"
        else f"Incident drill failed: {failure_reason or 'unspecified-error'}"
    ),
    "correctiveActions": [
        "Re-run incident drill after any replay/runtime policy changes.",
        "Review replay override audit entries and on-call routing ownership.",
        "Update gate status and attach incident artifact evidence."
    ],
}
Path(artifact_path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
  rm -f "${tmp_ok}" "${tmp_fail}"
}
trap 'finalize "$?"' EXIT

echo "[IncidentDrill] Step 1/4: Baseline verification run (expect success)."
baseline_cmd=(
  "${PYTHON_BIN}" "${SIM_SCRIPT}"
  --provider "${DRILL_PROVIDER}"
  --response Accept
  --verification-status Success
)
if [[ "${DRILL_PROVIDER}" == "FMCSA" ]]; then
  baseline_cmd+=(--mc-number "${MC_NUMBER}")
fi
"${baseline_cmd[@]}" >"${tmp_ok}" 2>&1

if ! rg -q "Booking completed successfully" "${tmp_ok}"; then
  BASELINE_RESULT="fail"
  LAST_FAILURE_REASON="baseline-load-flow-missing"
  echo "[IncidentDrill] Baseline run did not complete load flow." >&2
  tail -n 80 "${tmp_ok}" >&2
  exit 1
fi
if [[ "${REQUIRE_TRUCK_FLOW}" == "1" ]] && ! rg -q "Truck capacity booking complete" "${tmp_ok}"; then
  BASELINE_RESULT="fail"
  LAST_FAILURE_REASON="baseline-truck-flow-missing"
  echo "[IncidentDrill] Baseline run did not complete truck flow." >&2
  tail -n 80 "${tmp_ok}" >&2
  exit 1
fi
BASELINE_RESULT="pass"
echo "[IncidentDrill] Baseline run passed."

echo "[IncidentDrill] Step 2/4: Simulate verifier signing key incident (expect detection/fail-close)."
STEP2_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
incident_cmd=(
  "${PYTHON_BIN}" "${SIM_SCRIPT}"
  --provider "${DRILL_PROVIDER}"
  --response Accept
  --verification-status Success
)
if [[ "${DRILL_PROVIDER}" == "FMCSA" ]]; then
  incident_cmd+=(--mc-number "${MC_NUMBER}")
fi
FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID="incident-compromised-kid" \
  "${incident_cmd[@]}" >"${tmp_fail}" 2>&1 || true

if ! rg -q "verification failed|Verifier|active key ID .* not found in configured key ring" "${tmp_fail}"; then
  INCIDENT_FAILCLOSE_RESULT="fail"
  LAST_FAILURE_REASON="incident-fail-close-signal-missing"
  echo "[IncidentDrill] Incident scenario did not produce expected verification failure." >&2
  tail -n 80 "${tmp_fail}" >&2
  exit 1
fi
INCIDENT_FAILCLOSE_RESULT="pass"
echo "[IncidentDrill] Incident detection/fail-close behavior confirmed."

echo "[IncidentDrill] Step 3/4: Security gate check."
STEP3_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
bash "${SECURITY_GATE}" "${ENV_FILE}"
SECURITY_GATE_RESULT="pass"
echo "[IncidentDrill] Security gate passed."

if [[ "${ROTATE_ON_DRILL}" == "1" ]]; then
  echo "[IncidentDrill] Step 4/4: Optional key rotation response."
  STEP4_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  REGISTRY_FILE="${FAXP_AGENT_KEY_REGISTRY_FILE:-${SECRETS_DIR}/faxp_agent_keys.local.json}"
  KEY_DIR="${SECRETS_DIR}/keys"
  bash "${ROTATE_SCRIPT}" "${ENV_FILE}" "${REGISTRY_FILE}" "${KEY_DIR}" "5"
  ROTATION_RESULT="pass"
  echo "[IncidentDrill] Rotation completed."
else
  STEP4_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  ROTATION_RESULT="skipped"
  echo "[IncidentDrill] Step 4/4: Rotation skipped (set FAXP_INCIDENT_DRILL_ROTATE=1 to enable)."
fi

echo "[IncidentDrill] Incident artifact: ${INCIDENT_ARTIFACT_PATH}"
echo "[IncidentDrill] Complete."
