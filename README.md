# FAXP (Freight Agent eXchange Protocol)

FAXP is a runnable protocol demo for autonomous freight booking.

This repository includes:
- `faxp_mvp_simulation.py` for CLI simulation (load flow + truck flow).
- `streamlit_app.py` for interactive demo UI.
- `adapter/fmcsa_live.py` for FMCSA live-query parser/client code used by builder-hosted adapters.
- `adapter/INTERFACE.md` for the stable adapter request/response and security contract.
- `fmcsa_adapter_server.py` as the reference hosted FMCSA adapter implementation.
- Security controls (message signing, verifier signing, replay/TTL, key rotation, incident drill).
- CI checks for parser regressions, Streamlit state regressions, and schema compatibility.

## Release Checkpoints

- `v0.2.0-alpha.1`: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/releases/RELEASE_NOTES_v0.2.0-alpha.1.md`
- `v0.2.0-rc.1`: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.1.md`
- `v0.2.0-rc.2`: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.2.md`
- `v0.2.0-rc.3`: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.3.md`
- `v0.2.0`: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/releases/RELEASE_NOTES_v0.2.0.md`

## Post-v0.2 Planning Tracks

- `v0.2.1` patch-only plan: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V0_2_1_PATCH_PLAN.md`
- `v0.3.0` RFC backlog (planning-only): `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V0_3_0_RFC_BACKLOG.md`
- `v0.3.0` governance checkpoint: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V0_3_0_GOVERNANCE_CHECKPOINT.md`
- `v0.3.0` commercial model backlog: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V0_3_0_COMMERCIAL_MODEL_BACKLOG.md`
- `v0.3.0` scenario catalog: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V0_3_0_SCENARIO_CATALOG.md`
- Active RFC draft: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Active RFC draft: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-shipper-orchestration-minimal.md`
- Active RFC draft: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-schema-version-negotiation.md`
- Active RFC draft: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-adapter-certification-profile-v2.md`
- Active RFC draft: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-provisional-booking-policy-contract.md`
- Active RFC draft: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-a2a-mcp-interop-maturity.md`

## v0.2 Planning Artifacts

- Docs index: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/INDEX.md`
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.2-verification-neutrality.md`
- A2A compatibility profile: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_COMPATIBILITY_PROFILE.md`
- A2A change management: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_CHANGE_MANAGEMENT.md`
- A2A upstream tracking config: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_UPSTREAM_TRACKING.json`
- MCP compatibility profile: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/MCP_COMPATIBILITY_PROFILE.md`
- MCP change management: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/MCP_CHANGE_MANAGEMENT.md`
- MCP upstream tracking config: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/MCP_UPSTREAM_TRACKING.json`
- Implementation checklist: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V2_IMPLEMENTATION_CHECKLIST.md`
- Test matrix: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/TEST_MATRIX_v0.2.md`
- Policy profiles (normative): `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/POLICY_PROFILES.md`
- Schema files:
  - v0.1.1: `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.schema.json`
  - v0.2 compatibility track: `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json`
- Governance model: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/FAXP_GOVERNANCE_MODEL.md`
- Builder handoff checklist: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/adapters/ADAPTER_IMPLEMENTER_HANDOFF.md`
- Certification playbook: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/CERTIFICATION_PLAYBOOK.md`
- Decision records runbook: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/DECISION_RECORDS_RUNBOOK.md`
- Registry operations runbook: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/REGISTRY_OPERATIONS_RUNBOOK.md`
- Registry changelog policy: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/REGISTRY_CHANGELOG_POLICY.md`
- Governance index: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/GOVERNANCE_INDEX.json`
- Release readiness checklist: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/RELEASE_READINESS_CHECKLIST.md`
- Verification profiles:
  - schema: `/Users/zglitch009/projects/logistics-ai/FAXP/profiles/verification/profile.schema.json`
  - strict: `/Users/zglitch009/projects/logistics-ai/FAXP/profiles/verification/US_FMCSA_STRICT_V1.json`
  - soft-hold: `/Users/zglitch009/projects/logistics-ai/FAXP/profiles/verification/US_FMCSA_SOFTHOLD_V1.json`
  - balanced: `/Users/zglitch009/projects/logistics-ai/FAXP/profiles/verification/US_FMCSA_BALANCED_V1.json`
- Conformance and registry artifacts:
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/README.md`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/certification_registry.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/certification_registry.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_profile.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_profile.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_test_profile.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/fmcsa_adapter_test_profile.v1.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/submission_manifest.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/submission_manifest.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/submission_manifest_keys.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/key_lifecycle_policy.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/key_lifecycle_policy.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/sample_conformance_report.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_update.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_update.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_update.sample.audit.log`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_changelog.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_governance_index.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_release_readiness.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_update_keys.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/certification_registry.sample.after_update.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/attestation_keys.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/generate_attestation.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/create_submission_manifest.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/create_registry_update.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/apply_registry_update.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/run_all_checks.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/submission_manifest_signing.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_update_signing.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/conformance_bundle.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/verifier_translator.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/a2a_bridge_translator.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/a2a_translator_contract.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/a2a_roundtrip_fixtures.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/mcp_tooling_contract.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/quickstart/`

## Protocol Neutrality Boundary

- Core FAXP handles envelope format, validation, message signing, replay/TTL controls, and conformance checks.
- Provider integrations (FMCSA, biometric vendors, future verifiers) are adapter concerns and should remain outside protocol-core contracts.
- `VerificationResult.provider` remains an opaque string in v0.2 compatibility schema; no vendor enum is required.
- Production adapters are expected to be implementer-hosted; FAXP provides reference implementation + certification contracts.

## Legacy Field Deprecation Timeline

Legacy provider-shaped fields remain supported for compatibility in v0.2:
- `providerAlias`
- `source`
- `sourceAuthority`
- `mcNumber`
- `carrier`
- `error`

Planned lifecycle:
1. v0.2.x: Supported and validated.
2. v0.3.x: Still accepted, marked deprecated in docs and conformance notes.
3. v0.4.0 target: move legacy fields to optional adapter-profile extensions; core conformance will only require neutral fields.

Operational rule:
- New integrations should write neutral fields first (`category`, `method`, `provider`, `assuranceLevel`, `evidenceRef`, `attestation`) and treat legacy fields as optional metadata.

A2A bridge quick check:
```bash
./scripts/run_a2a_conformance.sh
```

MCP interop quick check:
```bash
./scripts/run_mcp_conformance.sh
```

MCP upstream watch check:
```bash
python3 scripts/check_mcp_upstream.py \
  --tracking docs/interop/MCP_UPSTREAM_TRACKING.json \
  --output /tmp/mcp_watch_report.json \
  --issue-body /tmp/mcp_watch_issue.md
```

## Runbook

### 1) Local Setup (Recommended)

```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

Generate local keys and env bundle:

```bash
./scripts/generate_faxp_keys.sh /Users/zglitch009/.faxp-secrets
```

Load secrets:

```bash
set -a
source /Users/zglitch009/.faxp-secrets/security.env.local
set +a
```

### 2) Run the Simulation (CLI)

Default secure simulation:

```bash
./scripts/run_secure_demo.sh sim
```

Hosted FMCSA adapter simulation path:

```bash
python3 faxp_mvp_simulation.py \
  --provider FMCSA \
  --fmcsa-source implementer-adapter \
  --mc-number 498282 \
  --policy-profile-id US_FMCSA_BALANCED_V1 \
  --risk-tier 1 \
  --response Accept \
  --verification-status Success
```

Expected success line:
- `Booking completed successfully ...`

If verification fails in adapter mode, that is expected when authority/insurance checks fail for the MC or the adapter fails closed.

Degraded verification policy demo (provisional/hold path):

```bash
python3 faxp_mvp_simulation.py \
  --provider FMCSA \
  --fmcsa-source implementer-adapter \
  --mc-number 498282 \
  --policy-profile-id US_FMCSA_BALANCED_V1 \
  --risk-tier 2 \
  --exception-approved \
  --exception-approval-ref APPROVAL-DEMO-001 \
  --response Accept \
  --verification-status Success
```

Hosted FMCSA adapter simulation path:

```bash
python3 faxp_mvp_simulation.py \
  --provider FMCSA \
  --fmcsa-source implementer-adapter \
  --mc-number 498282 \
  --response Accept \
  --verification-status Success
```

### 3) Run the Streamlit Demo (Local)

```bash
./scripts/run_secure_demo.sh streamlit
```

Open:
- `http://localhost:8501`

Known-good preset:
1. `Quick Preset` -> `MockBiometric success`
2. `Apply Preset`
3. `Run NewLoad -> Bid Flow`

Expected:
- `Status: Booking completed.`
- `VerifiedBadge: Premium`
- `Validation Errors: 0`

Policy controls in sidebar:
- `Verification Policy Profile` (`US_FMCSA_BALANCED_V1`, `US_FMCSA_SOFTHOLD_V1`, or `US_FMCSA_STRICT_V1`)
- `Risk Tier` (`0-3`)
- `Exception Approved` + `Exception Approval Ref`

### 4) Streamlit Cloud Deployment

Set app entrypoint:
- `streamlit_app.py`

Set secrets in Streamlit Cloud.

Minimum cloud-safe secrets:
```toml
FAXP_APP_MODE="prod"
FAXP_CLOUD_SAFE_MODE="1"
FAXP_STREAMLIT_ACCESS_KEY="set-a-strong-random-string"
FAXP_MAX_VERIFICATIONS_PER_HOUR="30"
FAXP_AUTH_MAX_FAILURES="5"
FAXP_AUTH_LOCKOUT_SECONDS="300"
```

Recommended hosted FMCSA adapter secrets:
```toml
FAXP_FMCSA_ADAPTER_BASE_URL="https://your-hosted-verifier.example/v1/fmcsa/verify"
FAXP_FMCSA_ADAPTER_AUTH_TOKEN="your_adapter_access_token"
FAXP_FMCSA_ADAPTER_TIMEOUT_SECONDS="10"
FAXP_FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER="1"
FAXP_FMCSA_ADAPTER_SIGN_REQUESTS="1"
FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_KEYS="adapter-req-2026-02:your_adapter_request_hmac"
FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID="adapter-req-2026-02"
FAXP_ENFORCE_TRUSTED_VERIFIER_REGISTRY="1"
# Optional override (runtime falls back to conformance/trusted_verifier_registry.sample.json)
# FAXP_TRUSTED_VERIFIER_REGISTRY='{"registryVersion":"1.0.0","entries":[...]}'
```

Notes:
- Non-local mode requires `implementer-adapter` or `vendor-direct` compliance verification and fails closed if the adapter URL is missing.
- `hosted-adapter` remains accepted as a backward-compatible alias for `implementer-adapter`.
- Non-local mode enforces trusted verifier registry validation on verification results.
- Access key is enforced when `FAXP_APP_MODE` is non-local.

### 4.1) Hosted FMCSA Adapter Deployment (Vultr)

Vultr deployment artifacts:

- `/Users/zglitch009/projects/logistics-ai/FAXP/fmcsa_adapter_server.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/deploy/vultr/README.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/deploy/vultr/fmcsa_adapter.env.example`
- `/Users/zglitch009/projects/logistics-ai/FAXP/deploy/vultr/fmcsa-adapter.service`
- `/Users/zglitch009/projects/logistics-ai/FAXP/deploy/vultr/Caddyfile.fmcsa-adapter`

### 5) Security/Health Checks

Run security gate:

```bash
./scripts/security_gate.sh /Users/zglitch009/.faxp-secrets/security.env.local
```

Run incident drill:

```bash
./scripts/incident_drill.sh /Users/zglitch009/.faxp-secrets/security.env.local
```

Run self-test mode:

```bash
./scripts/run_secure_demo.sh check
```

### 6) Regression Checks

Parser fixture checks:

```bash
python3 tests/run_fmcsa_parser_fixtures.py
```

Streamlit state guard checks:

```bash
python3 tests/run_streamlit_state_logic.py
```

Schema compatibility checks (`v0.1.1` and `v0.2`):

```bash
python3 tests/run_schema_compatibility.py
```

Certification/profile artifact checks:

```bash
python3 tests/run_certification_artifacts.py
```

This check now validates:

- verification policy profile schemas,
- certification registry schemas,
- adapter self-attestation payload digest and HMAC signature,
- registry/profile consistency (ID, tier, hosting model, supported profiles, key ID).

Verification policy decision checks:

```bash
python3 tests/run_policy_decisions.py
```

Attestation generator checks:

```bash
python3 tests/run_generate_attestation.py
```

Conformance bundle checks:

```bash
python3 tests/run_conformance_bundle.py \
  --profile conformance/adapter_profile.sample.json \
  --registry-entry conformance/certification_registry.sample.json \
  --keyring conformance/attestation_keys.sample.json \
  --output /tmp/faxp_conformance_report.json
```

Adapter test profile checks:

```bash
python3 tests/run_adapter_test_profile.py
```

Submission manifest bundle checks:

```bash
python3 tests/run_submission_manifest.py
```

Submission manifest create helper checks:

```bash
python3 tests/run_create_submission_manifest.py
```

Create signed submission manifest:

```bash
python3 conformance/create_submission_manifest.py \
  --template conformance/submission_manifest.sample.json \
  --keyring conformance/submission_manifest_keys.sample.json \
  --kid faxp-submission-kid-2026q1 \
  --output /tmp/faxp_submission_manifest.signed.json
```

Key lifecycle policy checks:

```bash
python3 tests/run_key_lifecycle_policy.py
```

Conformance suite orchestrator check:

```bash
python3 tests/run_conformance_suite.py
```

Run full conformance suite and emit one report:

```bash
python3 conformance/run_all_checks.py \
  --output /tmp/faxp_conformance_suite_report.json
```

Registry operations artifact checks:

```bash
python3 tests/run_registry_ops_artifacts.py
```

Registry apply tool checks:

```bash
python3 tests/run_apply_registry_update.py
```

Registry update create helper checks:

```bash
python3 tests/run_create_registry_update.py
```

Create signed registry update request:

```bash
python3 conformance/create_registry_update.py \
  --template conformance/registry_update.sample.json \
  --keyring conformance/registry_update_keys.sample.json \
  --kid faxp-regops-kid-2026q1 \
  --output /tmp/faxp_registry_update.signed.json
```

Apply registry update request and write output:

```bash
python3 conformance/apply_registry_update.py \
  --request conformance/registry_update.sample.json \
  --keyring conformance/registry_update_keys.sample.json \
  --output /tmp/faxp_registry_after_update.json
```

Verifier translator checks:

```bash
python3 tests/run_verifier_translator.py
```

Regenerate adapter self-attestation fields (digest/signature):

```bash
python3 conformance/generate_attestation.py \
  --profile conformance/adapter_profile.sample.json \
  --keyring conformance/attestation_keys.sample.json \
  --kid faxp-lab-selfattest-2026q1 \
  --in-place
```

Quickstart onboarding bundle (templates + attestation + report):

```bash
bash conformance/quickstart/make_conformance_bundle.sh
```

### 7) Troubleshooting

`streamlit: command not found`
- Use venv binary: `./.venv/bin/streamlit run streamlit_app.py`

`Missing active ED25519 private key for sender`
- Confirm `FAXP_AGENT_KEY_REGISTRY_FILE` points to your generated key registry.
- Re-run `./scripts/generate_faxp_keys.sh /Users/zglitch009/.faxp-secrets`.

`Verifier signature key ID missing`
- Ensure verifier signing vars exist in your loaded env.
- Confirm `FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID` matches a key in verifier key ring.

`repository/branch/file does not exist` in Streamlit deploy
- Verify repo path, branch `main`, and main file `streamlit_app.py`.
- Re-authorize GitHub app permissions for Streamlit if repo visibility changed.

`Process completed with exit code 1` in CI
- Open failing job logs, then run the same script locally from this runbook section 6.

### 8) Protocol Versions

- Current runtime protocol in simulation: `0.1.1`.
- Added schema compatibility track for `0.2.0`: `faxp.v0.2.schema.json`.
- CI enforces backward compatibility checks between `0.1.1` and `0.2.0`.
