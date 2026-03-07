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
- `security_gate.sh` static and obfuscated/encoded secret scanning.
- `gitleaks` repository secret scanning in CI using `.gitleaks.toml`.

Operational verifier hosting and credentials remain outside protocol-core responsibilities.

## GitHub Repository Security Settings (Required)

Maintainers should keep these GitHub settings enabled:

1. Secret scanning.
2. Push protection for secrets.
3. Dependabot alerts.
4. Dependabot security updates.
5. Branch protection requiring passing `verify` checks before merge.

If any of these are disabled, treat it as a security regression and restore immediately.
