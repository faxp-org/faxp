# Security Policy

## Supported Versions

Security fixes are prioritized for:
- `main`
- the latest tagged stable release
- the active release candidate branch/tag (if one is in soak)

Older tags may not receive fixes.

## Reporting a Vulnerability

Do not open public issues for suspected vulnerabilities.

Report privately to:
- `info@faxp.org`

Include:
- affected file(s) and commit/tag
- reproduction steps
- impact assessment
- proof-of-concept details (if available)

## Response Targets

- Acknowledgement: within 72 hours
- Initial triage: within 7 days
- Coordinated remediation plan: within 14 days for validated high-severity issues

Target timelines may be adjusted based on severity, exploitability, and operational risk.

## Disclosure Process

1. Confirm issue validity and severity.
2. Prepare and test a fix.
3. Coordinate disclosure timing with reporter.
4. Publish release notes and remediation guidance.

## Security Baseline in This Repository

- Signed envelopes and verifier attestations.
- Replay and TTL enforcement.
- Role-capability policy validation.
- Conformance and governance release gates in CI.

Operational verifier hosting and credentials remain outside protocol-core responsibilities.
