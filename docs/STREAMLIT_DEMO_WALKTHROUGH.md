# FAXP Streamlit Demo Walkthrough

This guide explains how to test the Streamlit demo and what the demo is doing at each stage.

Use this after:
- `docs/STREAMLIT_QUICKSTART.md`
- `./scripts/bootstrap_demo_env.sh`

## What the Demo Is

The Streamlit app is a booking-plane walkthrough for FAXP.

It demonstrates:
- opportunity discovery
- bid / counter / accept flow
- policy-aware verification behavior
- booking confirmation through `ExecutionReport`
- booking-plane commercial terms

It does not demonstrate:
- dispatch execution
- tracking / telematics
- document custody
- invoice or payment workflows

## Before You Start

Make sure you have:

```bash
./scripts/bootstrap_demo_env.sh
./scripts/generate_faxp_keys.sh "$HOME/.faxp-secrets"
set -a
source "$HOME/.faxp-secrets/security.env.local"
set +a
```

Then launch the demo:

```bash
./scripts/run_secure_demo.sh streamlit
```

## Recommended First Test

Use the simplest happy-path first.

### Step 1: Start with a standard booking

In the sidebar:
- choose a quick preset if available, or leave defaults
- `BidResponse`: `Accept`
- verification policy: leave default
- verification provider/source: leave default local-safe option
- mock verification status: `Success`

Then click:
- `Run`

### What should happen

You should see:
1. validated messages count increase
2. verification succeed
3. an `ExecutionReport`
4. status showing booking completed

### What the app is doing

Under the hood, the demo runs:
1. `NewLoad`
2. `LoadSearch`
3. `BidRequest`
4. `BidResponse`
5. verification / policy evaluation
6. `ExecutionReport`

That is the core FAXP booking-plane path.

## Step-by-Step Message Flow

### 1) `NewLoad`

What it means:
- a broker-side agent posts a load opportunity

What to look for:
- load ID
- origin / destination
- rate model
- commercial terms

Why it matters:
- this is the first booking-plane contract object

### 2) `LoadSearch`

What it means:
- a carrier-side agent expresses matching criteria for available loads

What to look for:
- search constraints
- equipment compatibility
- rate expectations

Why it matters:
- it shows how a carrier agent discovers opportunities without manual re-keying

### 3) `BidRequest`

What it means:
- the carrier agent submits a bid against the load

What to look for:
- proposed rate
- rate model semantics
- agreed miles or other commercial terms if applicable

Why it matters:
- this is where commercial negotiation starts

### 4) `BidResponse`

What it means:
- the broker agent accepts, rejects, or counters the bid

What to test:
- `Accept`
- `Counter`
- `Reject`

Expected behavior:
- `Accept` continues toward verification/booking
- `Counter` stops with negotiation still open
- `Reject` stops with no booking

### 5) Verification / Policy Decision

What it means:
- the system evaluates optional verifier evidence and policy rules that can affect booking outcome

What to test:
- `Success`
- failure paths
- different verification policy profiles
- different risk tiers

Expected behavior:
- some profiles allow booking
- some profiles hold or block
- diagnostics should explain what happened

Why it matters:
- this demonstrates that FAXP can carry trust-related evidence and policy effects without becoming the verifier itself

### 6) `ExecutionReport`

What it means:
- the booking is confirmed at the protocol level

What to look for:
- booking status
- agreed commercial terms
- final normalized rate data
- references preserved for downstream handoff

Why it matters:
- this is the end of the FAXP booking-plane workflow

## Suggested Test Cases

### Test A: Happy path

Goal:
- confirm baseline booking works

Settings:
- `BidResponse = Accept`
- verification status `Success`

Expected:
- booking completes

### Test B: Counter path

Goal:
- confirm negotiation can stop without booking

Settings:
- `BidResponse = Counter`

Expected:
- no `ExecutionReport`
- app indicates negotiation is still open

### Test C: Reject path

Goal:
- confirm rejection exits cleanly

Settings:
- `BidResponse = Reject`

Expected:
- no booking confirmation

### Test D: Verification fail path

Goal:
- confirm policy and verifier failure handling

Settings:
- verification status `Fail`

Expected:
- booking blocked or held according to current policy/profile

### Test E: Rate-model variation

Goal:
- confirm different booking-plane commercial models behave correctly

Try:
- `PerMile`
- `Flat`
- `PerPallet`
- `CWT`
- `PerHour`
- `LaneMinimum`

Expected:
- fields and validation behavior change appropriately by model

## What to Read on the Screen

### Status cards

These summarize:
- current booking outcome
- verification outcome
- validated message count
- validation errors

### Message log

This is the most important area for contributors.

Use it to inspect:
- exact message types
- normalized payload structure
- policy and verification outcomes
- whether the flow stopped where you expected

### Diagnostics panels

Use these when a run does not complete.

They help answer:
- did verification fail?
- did policy block the booking?
- was a provider/source missing?
- was the flow intentionally stopped by a counter or reject outcome?

## What the Demo Does Not Mean

If the demo ends with `ExecutionReport`, that does not mean dispatch has happened.

It means:
- the booking is complete in FAXP terms

It does not mean:
- dispatch packet sent
- pickup number issued
- rate confirmation delivered
- carrier onboarding complete
- payment setup complete

Those remain outside FAXP core and belong to the participant's TMS, portal, ops agent, or human workflow.

## Recommended Contributor Testing Sequence

1. Run the happy path once
2. Run counter and reject paths
3. Run verification failure path
4. Change rate models and inspect payload differences
5. Review message log for each run
6. Only after that, start editing code

## Related Docs

- `docs/STREAMLIT_QUICKSTART.md`
- `README.md`
- `CONTRIBUTING.md`
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`
