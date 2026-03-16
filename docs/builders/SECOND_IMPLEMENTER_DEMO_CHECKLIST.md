# Second Implementer Demo Checklist (Public-Safe)

Use this checklist to run one additional independent TMS/implementer demo before beta-promotion decisions.

Maturity status:
- Experimental and early-stage.
- Sandbox-only evaluation.
- Not a production rollout template.

## Purpose

Confirm that FAXP behavior is repeatable across at least two independent implementations without partner-specific dependencies.

## Scope Guardrails

Keep demo scope inside booking-plane interoperability:
1. Message exchange and envelope handling.
2. Adapter translation and deterministic update behavior.
3. Conformance and governance checks.

Do not include:
1. Dispatch execution logic.
2. Tracking lifecycle management.
3. Settlement/payment orchestration.
4. Partner-private artifacts or credentials.

## Pre-Demo Inputs

1. Public packet baseline:
   - `docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md`
   - `docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md`
2. One sandbox-capable implementer/TMS target.
3. An anonymized adapter mapping plan (`source fields -> FAXP fields`).
4. Deterministic test case definition:
   - create/read/update path,
   - expected stable IDs/correlation behavior,
   - expected FAXP envelope output.
5. Evidence bundle scaffold:
   - `docs/builders/SECOND_IMPLEMENTER_EVIDENCE_BUNDLE_TEMPLATE.json`

## Execution Checklist

1. Validate protocol-vs-adapter boundary before coding.
2. Run sandbox auth and baseline create/read operations.
3. Run deterministic update cycle and verify ID/stop/reference stability.
4. Build/validate FAXP message body and signed envelope.
5. Run local conformance/readiness baseline:
   - `.venv/bin/python tests/run_open_source_guardrails.py`
   - `.venv/bin/python tests/run_release_readiness.py`
   - `.venv/bin/python tests/run_conformance_suite.py`
6. Produce anonymized evidence artifacts only.
7. Populate and retain one evidence bundle using:
   - `docs/builders/SECOND_IMPLEMENTER_EVIDENCE_BUNDLE_TEMPLATE.json`

## Required Evidence Artifacts

1. Anonymized source payload sample (create/read/update).
2. Anonymized deterministic update payload sample.
3. Anonymized FAXP message body sample.
4. Anonymized FAXP envelope sample.
5. Short protocol-vs-adapter responsibility summary.
6. Outcome summary using:
   - `docs/builders/ANONYMIZED_INTEGRATION_OUTCOME_TEMPLATE.md`
7. Structured evidence bundle record:
   - `docs/builders/SECOND_IMPLEMENTER_EVIDENCE_BUNDLE_TEMPLATE.json`

## Exit Criteria

1. End-to-end sandbox flow passes without ad hoc manual patching.
2. Deterministic identifiers remain stable through update/readback checks.
3. Public artifacts remain partner-safe and anonymized.
4. Protocol scope remains unchanged (no out-of-scope expansion).
5. Evidence is sufficient to support beta-promotion discussion.
