# Registry Changelog Policy

This policy defines deterministic requirements for registry changelog artifacts.

## Purpose
- Provide an auditable, append-style view of registry changes.
- Ensure changelog records cross-link to request, audit, decision, and snapshot artifacts.
- Keep change history machine-verifiable in CI.

## Scope
- Applies to changelog artifacts under `conformance/`.
- Applies to update/revoke/rollback operations captured by registry operations.
- Does not replace registry snapshots; it complements them.

## Policy Rules
1. Changelog must include top-level metadata and refs to supporting artifacts.
2. Each changelog entry must map to an operation in the registry update request.
3. Entries must be chronological by `effectiveAt`.
4. Reason codes must be machine-readable (`UPPER_SNAKE_CASE`).
5. Final changelog state must match the post-update registry snapshot.

## Normative Policy Config (Test-Enforced)

<!-- REGISTRY_CHANGELOG_POLICY_BEGIN -->
{
  "requiredTopLevelFields": [
    "changelogVersion",
    "generatedAt",
    "changeSetId",
    "requestRef",
    "auditTrailRef",
    "decisionRecordRef",
    "registrySnapshotBeforeRef",
    "registrySnapshotAfterRef",
    "entries",
    "notes"
  ],
  "requiredEntryFields": [
    "changeId",
    "opId",
    "action",
    "adapterId",
    "reasonCode",
    "effectiveAt",
    "statusBefore",
    "statusAfter",
    "tierBefore",
    "tierAfter",
    "status",
    "notes"
  ],
  "changeIdPattern": "^chg-[0-9]{3}$",
  "opIdPattern": "^op-[0-9]{3}$",
  "allowedActions": ["UPSERT", "SUSPEND", "REVOKE", "ROLLBACK"],
  "allowedStatuses": ["Active", "Suspended", "Revoked"],
  "allowedEntryStates": ["Applied"],
  "reasonCodePattern": "^[A-Z][A-Z0-9_]{2,}$",
  "requireChronologicalOrder": true,
  "requireRequestOperationMatch": true,
  "requireAuditTrailRef": true,
  "requireDecisionRecordRef": true
}
<!-- REGISTRY_CHANGELOG_POLICY_END -->
