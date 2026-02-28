# FAXP v0.2 Implementation Checklist (From RFC Verification Neutrality)

Status: Alpha Candidate  
Source RFC: `docs/rfc/RFC-v0.2-verification-neutrality.md`  
Updated: 2026-02-21 (alpha evidence closure)

## Phase 0: Branch + Baseline

- [ ] Create branch: `codex/v0.2-verification-neutrality`
- [ ] Tag current state as baseline: `v0.1.1-cloud-demo`
- [ ] Run baseline checks before changes:
  - [ ] `./scripts/run_secure_demo.sh sim --use-kms-command`
  - [ ] `./scripts/incident_drill.sh`
  - [ ] `./scripts/security_gate.sh /Users/zglitch009/.faxp-secrets/security.env.local`

## Phase 1: Schema Updates (Provider-Agnostic Verification)

Target files:
- `faxp.schema.json` (v0.1.1 baseline)
- `faxp.v0.2.schema.json` (compatibility track)

- [x] Extend `ExecutionReport.VerificationResult` to neutral fields (in v0.2 schema):
  - [x] `status`
  - [x] `category`
  - [x] `method`
  - [x] `provider` (opaque string)
  - [x] `assuranceLevel`
  - [x] `score`
  - [x] `token`
  - [x] `evidenceRef`
  - [x] `verifiedAt`
  - [x] `expiresAt` (optional)
  - [x] `attestation.alg`
  - [x] `attestation.kid`
  - [x] `attestation.sig`
- [x] Keep backward-compatibility fields for one version (deprecation notice in docs).
- [x] Disallow raw biometric artifact fields in schema.

Acceptance:
- [x] Schema validates existing v0.1.1 examples (compat mode).
- [x] Schema validates new v0.2 neutral verification examples.

## Phase 2: Simulation/Validator Changes

Target file: `faxp_mvp_simulation.py`

- [x] Update validation logic for `ExecutionReport.VerificationResult` neutral object.
- [x] Add verifier attestation validation hook:
  - [x] enforce `alg`/`kid` presence when signed verifier mode is enabled.
  - [x] reject unknown/invalid attestation structure.
- [x] Add "no raw biometric payload" guardrails in validation.
- [x] Replace vendor-specific defaults in demo responses with neutral examples.
- [x] Preserve existing `VerifiedBadge` behavior (`None`/`Basic`/`Premium`) as policy mapping.

Acceptance:
- [x] Load flow still completes.
- [x] Truck flow still completes.
- [x] Existing security tests pass.
- [x] New invalid verification payloads are rejected.

## Phase 3: Capability Negotiation (Optional Metadata in v0.2)

Targets:
- `faxp_mvp_simulation.py`
- `streamlit_app.py`

- [x] Add optional `VerificationCapabilities` structure (agent-level metadata).
- [x] Add matching logic stub:
  - [x] If broker/carrier capabilities conflict, fail early with clear reason.
- [x] Keep transport placement minimal for v0.2 (no new message type yet).

Acceptance:
- [x] Capability metadata is optional and non-breaking.
- [x] Capability mismatch path is deterministic and logged.

## Phase 4: Streamlit Cloud Alignment

Target file: `streamlit_app.py`

- [x] Add cloud-safe mode switch in UI/config:
  - [x] hide/disable non-cloud-safe local verifier paths.
- [x] Display verification object in neutral format.
- [x] Add clearer status text for verifier unavailable vs verification failure.

Acceptance:
- [x] Streamlit cloud demo succeeds with known-good settings.
- [x] No ED25519 private-key file dependency in cloud mode.

## Phase 5: Tests and Conformance

Targets:
- `faxp_mvp_simulation.py` (self-test paths)
- New test notes/doc file (optional):
  - `docs/roadmap/TEST_MATRIX_v0.2.md`

- [x] Add neutral-verification happy-path test vectors:
  - [x] mock provider A
  - [x] mock provider B
- [x] Add negative tests:
  - [x] missing attestation when required
  - [x] malformed attestation
  - [x] raw biometric payload rejection
  - [x] unknown category/method handling
- [x] Add explicit conformance checks for:
  - [x] no vendor-mandatory schema fields
  - [x] protocol acceptance independent of provider name

Acceptance:
- [x] Two-provider neutrality tests pass.
- [x] Negative tests fail-closed as expected.

## Phase 6: Docs + Governance

Targets:
- `README.md`
- `docs/roadmap/FAXP_DEFERRED_ITEMS.md`
- `docs/rfc/RFC-v0.2-verification-neutrality.md`

- [x] Add protocol-neutral verification section to README.
- [x] Document adapter pattern boundaries (core protocol vs provider adapters).
- [x] Add deprecation note/timeline for legacy provider-shaped fields.
- [x] Add conformance language snippet for foundation/governance docs.

Acceptance:
- [x] Developer can implement a new provider adapter without core schema changes.

## Suggested Implementation Order

1. Phase 1 (schema)  
2. Phase 2 (validator/simulation)  
3. Phase 4 (Streamlit cloud-safe UX)  
4. Phase 5 (tests/conformance)  
5. Phase 6 (docs/governance)  
6. Phase 3 (capabilities) can run in parallel after Phase 2

## Definition of Done (v0.2 Neutral Verification)

- [x] Core protocol schema is provider-neutral.
- [x] Core code has no vendor-specific required fields.
- [x] Cloud demo remains functional.
- [x] Security controls remain enforced.
- [x] Conformance tests prove multi-provider neutrality.

## Evidence Notes (2026-02-21)

- CI has remained green across schema compatibility, attestation enforcement, unknown taxonomy rejection, and two-provider neutrality smoke checks.
- Load/truck completion validated in simulation output (`Booking completed successfully` + truck completion path).
- Streamlit cloud behavior validated manually with cloud-safe settings in production mode.
- Adapter implementation acceptance supported by:
  - opaque neutral `VerificationResult.provider` IDs,
  - legacy `providerAlias` compatibility path,
  - conformance language requiring provider-agnostic protocol handling.
