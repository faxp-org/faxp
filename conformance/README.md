# FAXP Conformance and Certification

FAXP is a protocol and certification authority model, not a centralized transaction host.

This folder defines machine-readable artifacts for implementer-hosted adapters:

- `certification_registry.schema.json`: schema for registry metadata.
- `certification_registry.sample.json`: sample registry entry.
- `adapter_profile.schema.json`: schema for adapter self-attestation profile.
- `adapter_profile.sample.json`: sample adapter profile with self-attestation payload.
- `adapter_test_profile.schema.json`: schema for adapter API test-profile contracts.
- `fmcsa_adapter_test_profile.v1.json`: FMCSA adapter certification test profile.
- `submission_manifest.schema.json`: schema for certification submission manifest bundles.
- `submission_manifest.sample.json`: sample certification submission manifest.
- `submission_manifest_keys.sample.json`: test-only keyring for signing submission manifests.
- `sample_conformance_report.json`: sample conformance report referenced by submission manifest.
- `key_lifecycle_policy.schema.json`: schema for key age/rotation overlap governance.
- `key_lifecycle_policy.sample.json`: sample policy binding active KIDs to signed artifacts.
- `registry_update.schema.json`: schema for registry operations request payloads.
- `registry_update.sample.json`: sample registry operations request with upsert/revoke/rollback.
- `registry_update.sample.audit.log`: sample audit log for registry operations.
- `registry_update_keys.sample.json`: test-only keyring for signing registry update requests.
- `certification_registry.sample.after_update.json`: expected sample registry after applying `registry_update.sample.json`.
- `../docs/governance/REGISTRY_ADMISSION_POLICY.md`: policy contract for admission/renewal/suspension criteria (normative block).
- `../docs/governance/REGISTRY_CHANGELOG_POLICY.md`: policy contract for changelog integrity and cross-link requirements.
- `../docs/governance/GOVERNANCE_INDEX.json`: machine-readable index of governance artifacts and required checks.
- `../docs/governance/RELEASE_READINESS_CHECKLIST.md`: go/no-go release gate checklist with test-enforced requirements.
- `registry_changelog.sample.json`: sample changelog aligned to registry update operations and snapshots.
- `../docs/governance/CERTIFICATION_DECISION_RECORD_TEMPLATE.md`: decision artifact template for deterministic approval/rejection records.
- `certification_decision_record.sample.json`: sample decision artifact aligned to template requirements.
- `attestation_keys.sample.json`: test-only keyring for local/CI attestation verification.
- `generate_attestation.py`: helper to regenerate payload digest/signature for adapter profiles.
- `create_submission_manifest.py`: helper to generate signed submission manifests from template payloads.
- `create_registry_update.py`: helper to generate signed registry update requests from template payloads.
- `apply_registry_update.py`: deterministic registry update applier (upsert/revoke/rollback).
- `run_all_checks.py`: one-command conformance orchestrator with JSON summary report.
- `submission_manifest_signing.py`: shared canonicalization/sign/verify helpers for submission manifests.
- `registry_update_signing.py`: shared canonicalization/sign/verify helpers for registry update requests.
- `conformance_bundle.py`: reusable conformance evaluator for profile + registry bundles.
- `verifier_translator.py`: reference wrapper for translating provider-native payloads to neutral FAXP verification output.
- `a2a_translator_contract.json`: bridge contract for optional A2A translator implementations.
- `a2a_bridge_translator.py`: reference reversible FAXP<->A2A translator module.
- `quickstart/`: onboarding templates + bundle builder script.

Human-readable adapter contract:
- `adapter/INTERFACE.md`: implementer handoff contract for request/response, security, and conformance expectations.
- `docs/governance/CERTIFICATION_PLAYBOOK.md`: certification intake workflow and tier decision rules.
- `docs/governance/REGISTRY_OPERATIONS_RUNBOOK.md`: operational process for update/revoke/rollback and rollback safety.

Adapter hosting model:

1. FAXP foundation publishes protocol/profile specs and conformance tests.
2. Implementers (agent builders, TMS integrators, brokers) host adapters.
3. Registry entries record conformance/security tier and supported profiles.

Suggested certification tiers:

1. `SelfAttested`: developer/self-reported compliance.
2. `Conformant`: passes FAXP conformance test harness.
3. `TrustedProduction`: conformant plus operational security/SLA evidence.

Required minimum controls for `Conformant`:

1. Signed adapter requests and responses.
2. Replay protection and timestamp skew enforcement.
3. Auditable decision trail.

Self-attestation profile checks:

1. Profile JSON must validate against `adapter_profile.schema.json`.
2. `selfAttestation.payloadDigestSha256` must match canonical payload hash.
3. `selfAttestation.sig` must verify using the declared `kid` in the attestation keyring.
4. Registry and adapter profile must agree on adapter ID, tier, hosting model, and supported profiles.

Note:

- `attestation_keys.sample.json` is intentionally non-secret and for conformance harness testing only.
- Production implementers should store attestation keys in their own secure key management system.

Attestation helper usage:

```bash
python3 conformance/generate_attestation.py \
  --profile conformance/adapter_profile.sample.json \
  --keyring conformance/attestation_keys.sample.json \
  --kid faxp-lab-selfattest-2026q1 \
  --in-place
```

One-command conformance report:

```bash
python3 tests/run_conformance_bundle.py \
  --profile conformance/adapter_profile.sample.json \
  --registry-entry conformance/certification_registry.sample.json \
  --keyring conformance/attestation_keys.sample.json \
  --output /tmp/faxp_conformance_report.json
```

Quickstart bundle:

```bash
bash conformance/quickstart/make_conformance_bundle.sh
```

Adapter API test profile check:

```bash
python3 tests/run_adapter_test_profile.py
```

Submission manifest bundle check:

```bash
python3 tests/run_submission_manifest.py
```

Submission manifest generation (signed):

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

One-command conformance suite:

```bash
python3 conformance/run_all_checks.py \
  --output /tmp/faxp_conformance_suite_report.json
```

Registry operations artifact check:

```bash
python3 tests/run_registry_ops_artifacts.py
```

Registry admission policy check:

```bash
python3 tests/run_registry_admission_policy.py
```

Registry changelog artifact check:

```bash
python3 tests/run_registry_changelog_artifacts.py
```

Certification decision record template check:

```bash
python3 tests/run_decision_record_template.py
```

Certification decision record artifact check:

```bash
python3 tests/run_decision_record_artifacts.py
```

Governance index check:

```bash
python3 tests/run_governance_index.py
```

Release readiness check:

```bash
python3 tests/run_release_readiness.py
```

A2A compatibility profile check:

```bash
python3 tests/run_a2a_profile_check.py
```

A2A round-trip translator check:

```bash
python3 tests/run_a2a_roundtrip_translation.py
```

Registry update request generation (signed):

```bash
python3 conformance/create_registry_update.py \
  --template conformance/registry_update.sample.json \
  --keyring conformance/registry_update_keys.sample.json \
  --kid faxp-regops-kid-2026q1 \
  --output /tmp/faxp_registry_update.signed.json
```

Apply registry update request (deterministic output):

```bash
python3 conformance/apply_registry_update.py \
  --request conformance/registry_update.sample.json \
  --keyring conformance/registry_update_keys.sample.json \
  --output /tmp/faxp_registry_after_update.json
```

Translator wrapper quick usage:

```python
from conformance.verifier_translator import translate_verifier_payload

result = translate_verifier_payload(
    "fmcsa",
    {"payload": {"mcNumber": "498282"}, "signature": {"alg": "HMAC_SHA256", "kid": "k1", "sig": "..."}},
    source="hosted-adapter",
    signature_keys={"k1": "shared-secret"},
    require_signed_wrapper=True,
)
```

Production note:

- `/Users/zglitch009/projects/logistics-ai/FAXP/fmcsa_adapter_server.py` now routes FMCSA lookup output through this translator wrapper by default before signing responses.
