# FAXP (Freight Agent eXchange Protocol)

FAXP is a runnable protocol demo for autonomous freight booking.

This repository includes:
- `faxp_mvp_simulation.py` for CLI simulation (load flow + truck flow).
- `streamlit_app.py` for interactive demo UI.
- `fmcsa_adapter_server.py` as the reference hosted FMCSA adapter implementation.
- Security controls (message signing, verifier signing, replay/TTL, key rotation, incident drill).
- CI checks for parser regressions, Streamlit state regressions, and schema compatibility.

## Release Checkpoints

- `v0.2.0-alpha.1`: `/Users/zglitch009/projects/logistics-ai/FAXP/RELEASE_NOTES_v0.2.0-alpha.1.md`

## v0.2 Planning Artifacts

- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/RFC-v0.2-verification-neutrality.md`
- Implementation checklist: `/Users/zglitch009/projects/logistics-ai/FAXP/V2_IMPLEMENTATION_CHECKLIST.md`
- Test matrix: `/Users/zglitch009/projects/logistics-ai/FAXP/TEST_MATRIX_v0.2.md`
- Schema files:
  - v0.1.1: `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.schema.json`
  - v0.2 compatibility track: `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json`
- Governance model: `/Users/zglitch009/projects/logistics-ai/FAXP/FAXP_GOVERNANCE_MODEL.md`
- Verification profiles:
  - schema: `/Users/zglitch009/projects/logistics-ai/FAXP/profiles/verification/profile.schema.json`
  - strict: `/Users/zglitch009/projects/logistics-ai/FAXP/profiles/verification/US_FMCSA_STRICT_V1.json`
  - balanced: `/Users/zglitch009/projects/logistics-ai/FAXP/profiles/verification/US_FMCSA_BALANCED_V1.json`
- Conformance and registry artifacts:
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/README.md`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/certification_registry.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/certification_registry.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_profile.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_profile.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/attestation_keys.sample.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/generate_attestation.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/conformance_bundle.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/verifier_translator.py`
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
./generate_faxp_keys.sh /Users/zglitch009/.faxp-secrets
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
./run_secure_demo.sh sim
```

Live FMCSA simulation path:

```bash
python3 faxp_mvp_simulation.py \
  --provider FMCSA \
  --fmcsa-source live-fmcsa \
  --mc-number 498282 \
  --policy-profile-id US_FMCSA_BALANCED_V1 \
  --risk-tier 1 \
  --response Accept \
  --verification-status Success
```

Expected success line:
- `Booking completed successfully ...`

If verification fails in live FMCSA mode, that is expected when authority/insurance checks fail for the MC.

Degraded verification policy demo (provisional/hold path):

```bash
python3 faxp_mvp_simulation.py \
  --provider FMCSA \
  --fmcsa-source hosted-adapter \
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
  --fmcsa-source hosted-adapter \
  --mc-number 498282 \
  --response Accept \
  --verification-status Success
```

### 3) Run the Streamlit Demo (Local)

```bash
./run_secure_demo.sh streamlit
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
- `Verification Policy Profile` (`US_FMCSA_BALANCED_V1` or `US_FMCSA_STRICT_V1`)
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

Optional live FMCSA (authority API) secrets:
```toml
FAXP_FMCSA_WEBKEY="your_fmcsa_webkey"
FAXP_FMCSA_CLIENT_SECRET="your_fmcsa_client_secret"
FAXP_FMCSA_API_BASE_URL="https://mobile.fmcsa.dot.gov/qc/services"
FAXP_FMCSA_API_TIMEOUT_SECONDS="12"
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
```

Notes:
- Cloud FMCSA source selection order is: `hosted-adapter` (if configured), `live-fmcsa` (if configured), otherwise `authority-mock`.
- Without hosted adapter or live FMCSA credentials, cloud FMCSA mode automatically falls back to `authority-mock`.
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
./security_gate.sh /Users/zglitch009/.faxp-secrets/security.env.local
```

Run incident drill:

```bash
./incident_drill.sh /Users/zglitch009/.faxp-secrets/security.env.local
```

Run self-test mode:

```bash
./run_secure_demo.sh check
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
- Re-run `./generate_faxp_keys.sh /Users/zglitch009/.faxp-secrets`.

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
