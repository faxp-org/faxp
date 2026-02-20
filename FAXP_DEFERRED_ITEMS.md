# FAXP Deferred Items (Revisit for V2)

This note tracks governance/tooling items intentionally deferred while v0.1.x stabilizes.

## Deferred

1. `rulesync.jsonc`-style centralized agent/tool sync orchestration.
2. Lockfile-driven frozen installs for all agent tooling (`rulesync.lock` equivalent).
3. CI policy gates enforcing frozen dependency/config state on every PR.
4. Automated protocol-change approval workflow (security/compliance reviewer integration).
5. Full external handoff packaging for white-label partner SDK/export pipelines.

## Current Scope (Implemented Now)

1. Canonical protocol schema at `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.schema.json`.
2. Runtime message validation inside `/Users/zglitch009/projects/logistics-ai/FAXP/faxp_mvp_simulation.py`.
3. Explicit protocol metadata in message envelope: `Protocol` + `ProtocolVersion`.

## Revisit Trigger

Revisit deferred items when either condition is met:

1. V2 rate structures/scenarios are finalized.
2. FAXP is prepared for multi-agent/multi-repo external integrations.
