# FAXP Registry Admission Policy

This policy defines objective criteria for registry entry admission, renewal, and non-active status handling.

## Scope
- Applies to certification registry artifacts under `conformance/`.
- Applies to admission and renewal decisions represented in registry metadata.
- Does not define runtime booking behavior or adapter hosting operations.

## Entry Admission Rules
1. `status=Active` entries must use production-ready tiers:
- `Conformant`
- `TrustedProduction`
2. `securityAttestation` controls must all be `true`:
- `signedRequests`
- `signedResponses`
- `replayProtection`
3. `conformanceReportRef` must be digest-addressable (`sha256:<hex>`).
4. Every profile in `profilesSupported` must use a versioned identifier format (`..._V<integer>`).
5. `expiresAt` must be strictly later than `lastCertifiedAt`.
6. Certification validity window must not exceed tier policy limits.

## Renewal Rules
1. Renewal is evaluated per `adapterId` between current and updated entries.
2. Renewed entries must remain `status=Active`.
3. `lastCertifiedAt` must be monotonic non-decreasing.
4. `expiresAt` must strictly increase.
5. Tier progression must be allowed by policy transitions.

## Suspension/Revocation Rules
1. Non-active entries (`Suspended`, `Revoked`) must include a machine-readable reason code in `notes`.
2. Reason-code format: uppercase words separated by underscores (example: `KEY_COMPROMISE`).

## Normative Policy Config (Test-Enforced)

<!-- REGISTRY_ADMISSION_POLICY_BEGIN -->
{
  "entryAdmission": {
    "activeAllowedTiers": ["Conformant", "TrustedProduction"],
    "requireSecurityAttestationTrue": true,
    "conformanceReportRefPattern": "^sha256:[a-f0-9]{16,}$",
    "profileIdPattern": "^[A-Z0-9_]+_V[0-9]+$",
    "maxValidityDaysByTier": {
      "SelfAttested": 90,
      "Conformant": 365,
      "TrustedProduction": 365
    }
  },
  "renewal": {
    "requireAdapterIdStable": true,
    "requireStatusActive": true,
    "requireLastCertifiedMonotonic": true,
    "requireExpiresAtIncrease": true,
    "allowedTierTransitions": [
      ["Conformant", "Conformant"],
      ["Conformant", "TrustedProduction"],
      ["TrustedProduction", "TrustedProduction"]
    ]
  },
  "nonActiveHandling": {
    "requireReasonCodeInNotes": true,
    "reasonCodePattern": "\\b[A-Z]{3,}(?:_[A-Z0-9]{2,})+\\b"
  }
}
<!-- REGISTRY_ADMISSION_POLICY_END -->
