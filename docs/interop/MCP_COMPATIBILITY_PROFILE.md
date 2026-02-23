# MCP Compatibility Profile (Loose-Coupled Tool Layer)

This profile defines how FAXP implementations can use MCP for agent-to-tool workflows without changing FAXP core protocol semantics.

## Scope
- FAXP core remains agent-to-agent booking/execution messaging.
- MCP is optional and used for tool/data/workflow delegation inside agent runtimes.
- FAXP does not require MCP for protocol conformance.

## Non-Goals
- No MCP fields in required FAXP envelope schema.
- No MCP endpoint dependency in FAXP core runtime.
- No centralized FAXP-hosted MCP execution service.

## Integration Rules
1. Treat MCP as internal/adjacent tool orchestration, not peer settlement messaging.
2. Keep FAXP wire payloads provider/tool neutral; include only normalized outputs and evidence references.
3. Preserve audit linkage from MCP tool actions to FAXP `MessageID` / `ContractID`.
4. Enforce least-privilege policy for MCP server access and fail closed on critical tool checks.

<!-- MCP_PROFILE_BEGIN -->
{
  "profileId": "FAXP_MCP_BRIDGE_V0_1",
  "status": "Draft",
  "mode": "LooseCoupledInterop",
  "coreProtocolChangesRequired": false,
  "mcpRequired": false,
  "hostingModel": "BuilderHosted",
  "supportedPatterns": [
    "HybridAgent",
    "ToolDelegation",
    "EvidenceDigestOnly"
  ],
  "allowedToolEvidenceFields": [
    "toolLayer",
    "serverId",
    "action",
    "outputDigest",
    "executedAt",
    "policyRef",
    "correlationRef"
  ],
  "requiredSecurityControls": [
    "LeastPrivilegeScopes",
    "ServerAllowlist",
    "AuditCorrelation",
    "FailClosedCriticalChecks"
  ],
  "faxpCorrelationFields": [
    "MessageID",
    "ContractID"
  ]
}
<!-- MCP_PROFILE_END -->

## Certification Direction
- Implementers can self-test MCP interoperability against FAXP MCP profile + contract artifacts.
- Certification should validate tool-evidence normalization and security control declarations, not MCP vendor specifics.
