# Builder Integration Profile

Use this document when you need to declare what a builder actually supports at the booking-plane level.

If you are new to the repo, start with:
- `README.md`
- `docs/BUILDERS_START_HERE.md`

If you need verification-runtime hosting requirements, use:
- `docs/builders/BUILDER_VERIFICATION_RUNTIME_HANDOFF.md`

If you need certification intake/review rules, use:
- `docs/governance/CERTIFICATION_PLAYBOOK.md`

## Plain-English Purpose

This profile is a standard capability sheet for builders.

If a TMS, load board, portal, or agent platform says it "supports FAXP," outside parties need to know what that actually means.

The builder integration profile answers practical questions like:
- Which roles does this implementation support?
- Which booking flows does it support?
- Which booking-plane profiles does it implement?
- How does it handle verification integration?
- Does it also support optional A2A or MCP interop?
- Which conformance checks back those claims?

Without a standard profile, every builder has to explain its support level differently, which creates adoption friction.

## Practical Examples

### Example 1: A broker TMS
A broker TMS might support:
- Broker role
- `LoadCentric` and `TruckCapacity` flows
- booking identity profile
- operational handoff profile
- standard rate model profile
- `vendor-direct` verification integration

That tells outside integrators the TMS can participate in booking, confirm deals, and route bookings downstream, but it is not claiming shipper-origin flow or hosted verification infrastructure.

### Example 2: A carrier-side agent builder
A carrier-focused builder might support:
- Carrier role
- `LoadCentric` and `TruckCapacity` flows
- booking identity profile
- operational handoff profile
- equipment profile
- `implementer-adapter` verification integration
- optional A2A interop

That tells an outside party the implementation is stronger in carrier workflows than in shipper-origin workflows.

### Example 3: A shipper-origin workflow builder
A shipper-oriented implementation might support:
- Shipper and Broker roles
- `ShipperOrigin` flow
- shipper orchestration profile
- booking identity profile
- operational handoff profile

That tells others the builder can originate freight through a shipper path, not just broker/carrier negotiation.

## What This Profile Is Not

This profile is not:
- a central registry of all FAXP participants
- a universal trust score
- a dispatch capability declaration
- a replacement for certification evidence

It is a normalized way to declare what a builder actually supports.

## What This Document Answers

This document is intentionally narrow.

It answers:
1. how a builder describes supported roles and flows
2. how a builder declares supported booking-plane profiles
3. how verification integration patterns and optional interop tracks are claimed

It does not explain:
1. how to host a verification runtime
2. how certification intake and review are performed

## Required Claim Areas

A builder integration claim should declare:
1. supported roles
2. supported flows
3. supported booking-plane profile IDs
4. verification integration pattern(s)
5. optional interop tracks (if any)
6. conformance evidence backing the claim

## Relationship to Certification

Certification still depends on evidence and test results.

The builder integration profile does not replace the certification playbook. It makes builder claims easier to compare and easier to review.

Use this profile together with:
- `docs/governance/CERTIFICATION_PLAYBOOK.md`
- `docs/builders/BUILDER_VERIFICATION_RUNTIME_HANDOFF.md`
- `conformance/builder_integration_profile.v1.json`
