# Developer Beta Promotion Criteria (Experimental)

This document defines the explicit go/no-go criteria for promoting FAXP from experimental sandbox evaluation to **Developer Beta (Sandbox-Only)** positioning.

This is not a production-release gate. It is a developer-beta promotion gate.

## Scope

Promotion criteria must remain within booking-plane protocol responsibilities:
1. protocol conformance and release-readiness controls,
2. public-safe documentation and contribution posture,
3. repeatable independent implementer evidence.

Out of scope for this decision:
1. dispatch operations execution quality,
2. settlement/payment orchestration outcomes,
3. partner-private implementation details.

## Criteria Tracker

| Criterion | Owner | Due | Status | Evidence |
| --- | --- | --- | --- | --- |
| Strict release-readiness checks pass in non-local strict mode | truckingadvantage | 2026-03-16 | Done | `tests/run_release_readiness.py`, `docs/governance/RELEASE_READINESS_CHECKLIST.md` |
| Replay operational gates fully closed | truckingadvantage | 2026-03-16 | Done | `docs/governance/REPLAY_OPERATIONS_GATES.md`, `tests/run_replay_operations_gates.py` |
| Security posture checkpoint captured with no active P0/P1 findings | truckingadvantage | 2026-03-16 | Done | `docs/governance/REPLAY_REDTEAM_DELTA_2026-03-08.md`, `docs/governance/REPLAY_INCIDENT_DRILL_EVIDENCE_2026-03-16.md` |
| Public-safe outreach and adapter packet published | truckingadvantage | 2026-03-16 | Done | `docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md`, `docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md` |
| Second independent implementer demo completed with anonymized evidence | truckingadvantage | 2026-03-31 | In Progress | `docs/builders/SECOND_IMPLEMENTER_DEMO_CHECKLIST.md`, `docs/builders/ANONYMIZED_INTEGRATION_OUTCOME_TEMPLATE.md`, `docs/builders/SECOND_IMPLEMENTER_EVIDENCE_BUNDLE_TEMPLATE.json`, `tests/run_second_implementer_evidence_bundle_template.py` |
| Open-source redaction/guardrail checks pass | truckingadvantage | 2026-03-16 | Done | `tests/run_public_redaction_guardrails.py`, `tests/run_open_source_guardrails.py` |

Status values:
- `Not Started`
- `In Progress`
- `Blocked`
- `Done`

## Current Decision

Current beta promotion decision: **Not Ready**.

Reason:
1. Second independent implementer demo evidence is still in progress.

## Normative Criteria Manifest (Test-Enforced Structure)

<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_BEGIN -->
{
  "updatedAt": "2026-03-16T22:15:00Z",
  "minimumIndependentImplementerDemos": 2,
  "betaDecision": "not_ready",
  "criteria": [
    {
      "id": "strict_release_readiness",
      "owner": "truckingadvantage",
      "due": "2026-03-16",
      "status": "done",
      "evidence": [
        "tests/run_release_readiness.py",
        "docs/governance/RELEASE_READINESS_CHECKLIST.md"
      ]
    },
    {
      "id": "replay_operational_gates_closed",
      "owner": "truckingadvantage",
      "due": "2026-03-16",
      "status": "done",
      "evidence": [
        "docs/governance/REPLAY_OPERATIONS_GATES.md",
        "tests/run_replay_operations_gates.py"
      ]
    },
    {
      "id": "security_posture_checkpoint",
      "owner": "truckingadvantage",
      "due": "2026-03-16",
      "status": "done",
      "evidence": [
        "docs/governance/REPLAY_REDTEAM_DELTA_2026-03-08.md",
        "docs/governance/REPLAY_INCIDENT_DRILL_EVIDENCE_2026-03-16.md"
      ]
    },
    {
      "id": "public_safe_packet_published",
      "owner": "truckingadvantage",
      "due": "2026-03-16",
      "status": "done",
      "evidence": [
        "docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md",
        "docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md"
      ]
    },
    {
      "id": "second_independent_implementer_demo",
      "owner": "truckingadvantage",
      "due": "2026-03-31",
      "status": "in_progress",
      "evidence": [
        "docs/builders/SECOND_IMPLEMENTER_DEMO_CHECKLIST.md",
        "docs/builders/ANONYMIZED_INTEGRATION_OUTCOME_TEMPLATE.md",
        "docs/builders/SECOND_IMPLEMENTER_EVIDENCE_BUNDLE_TEMPLATE.json",
        "tests/run_second_implementer_evidence_bundle_template.py"
      ]
    },
    {
      "id": "open_source_guardrails_green",
      "owner": "truckingadvantage",
      "due": "2026-03-16",
      "status": "done",
      "evidence": [
        "tests/run_public_redaction_guardrails.py",
        "tests/run_open_source_guardrails.py"
      ]
    }
  ]
}
<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_END -->
