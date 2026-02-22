# FAXP Conformance Quickstart

This quickstart creates a starter adapter profile + registry entry + signed attestation + conformance report.

Run:

```bash
bash conformance/quickstart/make_conformance_bundle.sh
```

Output directory defaults to:

- `conformance/quickstart/out`

Environment overrides (optional):

- `FAXP_ADAPTER_ID`
- `FAXP_ADAPTER_ENDPOINT_URL`
- `FAXP_VERIFICATION_PROFILE`
- `FAXP_ATTESTATION_KID`
- `FAXP_ATTESTATION_SECRET`
- `FAXP_ATTESTED_BY`
- `FAXP_ATTESTOR_ROLE`

Generated files:

- `adapter_profile.json`
- `certification_registry.entry.json`
- `attestation_keys.json` (test-only)
- `conformance_report.json`
