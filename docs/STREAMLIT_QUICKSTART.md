# FAXP Streamlit Quick Start

This guide is the fastest path from a fresh clone to a working local FAXP demo.

## Who This Is For

Use this guide if you want to:
- see the demo flow quickly
- test FAXP locally before making code changes
- review booking-plane behavior without setting up any cloud infrastructure

This is not the production deployment guide. It is the local contributor/demo path.

## What You Need

- Python 3
- `openssl`
- a local clone of the repository

## 5-Minute Local Setup

### 1) Create the local testing environment

```bash
./scripts/bootstrap_demo_env.sh
```

This creates `.venv`, installs dependencies, and prints the next commands.

### 2) Generate local demo secrets and keys

```bash
./scripts/generate_faxp_keys.sh "$HOME/.faxp-secrets"
```

This creates:
- `"$HOME/.faxp-secrets/security.env.local"`
- `"$HOME/.faxp-secrets/faxp_agent_keys.local.json"`
- local key material under `"$HOME/.faxp-secrets/keys/"`

These files stay outside the repo.

### 3) Load the local demo environment

```bash
set -a
source "$HOME/.faxp-secrets/security.env.local"
set +a
```

### 4) Run the local smoke checks

```bash
./scripts/run_release_smoke_local.sh
```

This is the fastest way to confirm the local demo environment is wired correctly.

### 5) Start the Streamlit demo

```bash
./scripts/run_secure_demo.sh streamlit
```

Then open the local Streamlit URL shown in your terminal.

## What the Demo Covers

The Streamlit demo is a booking-plane demo. It is meant to show:
- load and truck posting flows
- bid / counter / accept behavior
- policy-driven verification decisions
- booking confirmation through `ExecutionReport`
- booking-plane commercial terms

It is not a dispatch, tracking, or payment workflow.

## Local Testing Modes

### Streamlit demo

```bash
./scripts/run_secure_demo.sh streamlit
```

### CLI simulation

```bash
./scripts/run_secure_demo.sh sim
```

### Security self-test mode

```bash
./scripts/run_secure_demo.sh check
```

## Recommended Contributor Validation

Before opening a PR that changes booking, trust, or demo behavior, run:

```bash
./scripts/run_release_smoke_local.sh
./scripts/run_a2a_conformance.sh
./scripts/run_mcp_conformance.sh
python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.local.json
python3 tests/run_release_readiness.py
```

## Common Local Setup Problems

### `Security env file not found`

Generate keys first:

```bash
./scripts/generate_faxp_keys.sh "$HOME/.faxp-secrets"
```

Then load:

```bash
set -a
source "$HOME/.faxp-secrets/security.env.local"
set +a
```

### `streamlit` command not found

Run the bootstrap script:

```bash
./scripts/bootstrap_demo_env.sh
```

The secure runner will use the local `.venv` copy if needed.

### Local repo is fine, but Streamlit Cloud behaves differently

That is expected. Cloud mode uses stricter non-local policy behavior and may require configured external verifier endpoints or cloud-safe settings. Local contributor testing should start with the local path in this guide.

## Related Docs

- `README.md`
- `CONTRIBUTING.md`
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`
