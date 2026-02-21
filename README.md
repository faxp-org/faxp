# FAXP (Freight Agent eXchange Protocol)

FAXP is a runnable protocol demo for autonomous freight booking.

This repository includes:
- `faxp_mvp_simulation.py` for CLI simulation (load flow + truck flow).
- `streamlit_app.py` for interactive demo UI.
- Security controls (message signing, verifier signing, replay/TTL, key rotation, incident drill).
- CI checks for parser regressions, Streamlit state regressions, and schema compatibility.

## v0.2 Planning Artifacts

- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/RFC-v0.2-verification-neutrality.md`
- Implementation checklist: `/Users/zglitch009/projects/logistics-ai/FAXP/V2_IMPLEMENTATION_CHECKLIST.md`
- Test matrix: `/Users/zglitch009/projects/logistics-ai/FAXP/TEST_MATRIX_v0.2.md`
- Schema files:
  - v0.1.1: `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.schema.json`
  - v0.2 compatibility track: `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json`

## Protocol Neutrality Boundary

- Core FAXP handles envelope format, validation, message signing, replay/TTL controls, and conformance checks.
- Provider integrations (FMCSA, biometric vendors, future verifiers) are adapter concerns and should remain outside protocol-core contracts.
- `VerificationResult.provider` remains an opaque string in v0.2 compatibility schema; no vendor enum is required.

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
  --response Accept \
  --verification-status Success
```

Expected success line:
- `Booking completed successfully ...`

If verification fails in live FMCSA mode, that is expected when authority/insurance checks fail for the MC.

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

Notes:
- Without `FAXP_FMCSA_WEBKEY`, cloud FMCSA mode automatically falls back to `authority-mock`.
- Access key is enforced when `FAXP_APP_MODE` is non-local.

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
