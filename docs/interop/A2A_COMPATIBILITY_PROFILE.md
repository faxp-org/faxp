# A2A Compatibility Profile (Bridge-Only)

This profile defines how FAXP interoperates with A2A environments through a translator layer.

## Scope
- FAXP core remains unchanged.
- A2A compatibility is achieved by a builder-hosted translator.
- FAXP does not host centralized adapter or translator operations in production.

## Non-Goals
- No replacement of FAXP envelopes with A2A-native envelopes.
- No requirement that every FAXP deployment must use A2A.
- No protocol-core dependency on A2A transport/runtime.

## Bridge Rules
1. Preserve all original FAXP envelope + body content for signing/audit.
2. Map each FAXP message to a deterministic A2A task type.
3. Carry a reversible mapping (`faxpEnvelope`, `a2aTask`) for audit replay.
4. Enforce fail-closed behavior on malformed mappings.

<!-- A2A_PROFILE_BEGIN -->
{
  "profileId": "FAXP_A2A_BRIDGE_V0_1",
  "status": "Draft",
  "mode": "TranslatorOnly",
  "a2aExtensionUri": "faxp://profile/a2a/v0.1",
  "coreProtocolChangesRequired": false,
  "hostingModel": "BuilderHosted",
  "requiredFaxpMessageTypes": [
    "NewLoad",
    "LoadSearch",
    "NewTruck",
    "TruckSearch",
    "BidRequest",
    "BidResponse",
    "ExecutionReport",
    "AmendRequest"
  ],
  "taskMappings": {
    "NewLoad": {"a2aTaskType": "faxp.new_load", "direction": "broker_to_carrier"},
    "LoadSearch": {"a2aTaskType": "faxp.load_search", "direction": "carrier_to_broker"},
    "NewTruck": {"a2aTaskType": "faxp.new_truck", "direction": "carrier_to_broker"},
    "TruckSearch": {"a2aTaskType": "faxp.truck_search", "direction": "broker_to_carrier"},
    "BidRequest": {"a2aTaskType": "faxp.bid_request", "direction": "both"},
    "BidResponse": {"a2aTaskType": "faxp.bid_response", "direction": "both"},
    "ExecutionReport": {"a2aTaskType": "faxp.execution_report", "direction": "both"},
    "AmendRequest": {"a2aTaskType": "faxp.amend_request", "direction": "both"}
  },
  "securityParityRequirements": [
    "Preserve FAXP signatures in translated payload metadata.",
    "Do not strip FAXP replay/TTL fields before verification.",
    "Reject task payloads if reverse mapping to a valid FAXP envelope fails."
  ]
}
<!-- A2A_PROFILE_END -->

## Certification Direction
- Builders can implement translator wrappers using this profile.
- FAXP certification can validate translator conformance against this profile and contract artifacts.
