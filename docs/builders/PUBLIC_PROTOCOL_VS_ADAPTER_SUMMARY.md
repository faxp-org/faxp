# Public Protocol vs Adapter Summary

Use this summary in public docs to keep protocol claims and integration claims
clearly separated.

## Protocol (FAXP)

FAXP defines the booking-plane interoperability contract:
1. canonical message shapes (`NewLoad`, `Bid`, `ExecutionReport`, etc.),
2. envelope/body validation requirements, and
3. profile/conformance expectations.

FAXP does not implement source-system business logic.

## Adapter (Implementer Side)

The adapter is the source-system bridge:
1. handles source API/session/auth behavior,
2. maps source records to/from FAXP messages, and
3. applies deterministic source update mechanics.

## Public Claim Pattern

Use this split in public write-ups:
1. Protocol claim: "FAXP envelope/body validation passed."
2. Adapter claim: "Deterministic update contract worked when existing source IDs were reused."

## Public-Safe Rule

Do not include partner-attributable details. Keep examples synthetic and vendor-neutral.
