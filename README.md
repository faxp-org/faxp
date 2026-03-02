# FAXP

FAXP (Freight Agent eXchange Protocol) is an open, vendor-neutral booking-plane protocol for agent-to-agent freight matching and booking confirmation.

FAXP standardizes how freight agents exchange booking messages across systems without requiring vendor lock-in.

FAXP does not determine regulatory eligibility; it authenticates protocol messages and can transport optional verifier evidence.

## Scope

In scope:
- agent message envelopes, signatures, replay/TTL checks, and validation
- booking workflow message types:
  - `NewLoad`, `LoadSearch`
  - `NewTruck`, `TruckSearch`
  - `BidRequest`, `BidResponse`
  - `ExecutionReport`, `AmendRequest`
- optional verifier evidence transport and booking-policy decisions
- conformance profiles, certification artifacts, and governance checks

Out of scope:
- dispatch execution
- telematics and tracking lifecycle
- POD/BOL custody lifecycle
- invoicing, remittance, payment rails, and settlement operations
- FAXP-hosted verifier operations

Canonical boundary docs:
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`

## Repository Contents

- `faxp_mvp_simulation.py`: CLI protocol simulation and validation runtime
- `streamlit_app.py`: interactive demo
- `conformance/`: profiles, artifacts, and conformance harness
- `docs/`: governance, RFCs, roadmap, and release material
- `adapter/`: adapter interface and reference implementation components
- `scripts/`: security, smoke, and interoperability helper scripts

## Quick Start

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

Generate local security material:

```bash
./scripts/generate_faxp_keys.sh "$HOME/.faxp-secrets"
set -a
source "$HOME/.faxp-secrets/security.env.local"
set +a
```

Run the local release smoke check:

```bash
./scripts/run_release_smoke_local.sh
```

Run the Streamlit demo:

```bash
./scripts/run_secure_demo.sh streamlit
```

Demo quick start:
- `docs/STREAMLIT_QUICKSTART.md`
- `docs/STREAMLIT_DEMO_WALKTHROUGH.md`

## Conformance and Governance

Core docs:
- `docs/INDEX.md`
- `docs/governance/GOVERNANCE_INDEX.json`
- `docs/governance/RELEASE_READINESS_CHECKLIST.md`
- `conformance/README.md`

Run the full conformance suite:

```bash
python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.json
```

## Interop

Run A2A compatibility checks:

```bash
./scripts/run_a2a_conformance.sh
```

Run MCP compatibility checks:

```bash
./scripts/run_mcp_conformance.sh
```

## Deployment and Operational Docs

Operational deployment details are kept in dedicated docs, not in this top-level README.

Useful starting points:
- `docs/governance/CERTIFICATION_PLAYBOOK.md`
- `docs/governance/VENDOR_DIRECT_CERTIFICATION_RUNBOOK.md`
- `deploy/vultr/README.md`

## Security

Security policy and vulnerability reporting:
- `SECURITY.md`

## Contributing

Contributor workflow and scope expectations:
- `CONTRIBUTING.md`
- `docs/STREAMLIT_QUICKSTART.md`
- `docs/STREAMLIT_DEMO_WALKTHROUGH.md`

Before opening a PR:
1. read the scope guardrails
2. keep changes within booking-plane and governance boundaries
3. run the relevant local checks

## Current Status

FAXP currently focuses on the booking plane:

1. opportunity discovery
2. bid and counter exchange
3. optional verifier evidence handling
4. booking confirmation via `ExecutionReport`

Downstream dispatch, onboarding, rate confirmation, and settlement remain external to FAXP core and are expected to run in the participant's TMS, portal, ops agent, or human workflow.
