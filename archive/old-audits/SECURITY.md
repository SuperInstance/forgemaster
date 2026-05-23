# Security Policy for FLUX Constraint Compiler

## Security Policy
This project is licensed under the Apache License 2.0. The FLUX Constraint Compiler validates, compiles, and enforces structured constraint rules across cloud and on-premises systems. We prioritize user and supply chain security, following responsible disclosure practices to mitigate risks promptly. As an open-source project, we rely on our community to identify and resolve security issues, and we commit to transparent communication of resolved vulnerabilities to our user base.

## Reporting a Vulnerability
Do NOT file public GitHub issues for security vulnerabilities, as this could expose exploits to malicious actors before patches are available. Send detailed, actionable reports to `security@cocapn.io`. Include affected versions, step-by-step reproduction steps, proof-of-concept inputs/code, and relevant error logs. We will acknowledge your report within 48 hours, provide regular progress updates, and adhere to a 90-day disclosure window from initial submission, unless extended by mutual agreement. Do not share sensitive details publicly until the embargo concludes.

## Supported Versions
Only the latest patch release of the 0.x major version track receives active security updates. Older pre-0.x or unsupported 0.x minor releases will not get backported fixes, with critical actively exploited vulnerabilities evaluated on a case-by-case basis. This aligns with standard pre-1.0 open-source versioning practices, where breaking changes are frequent and only the latest release receives focused support.

## Threat Model Summary
Our formal threat model covers 8 key risks to the FLUX ecosystem:
1.  Unauthorized injection of malicious custom constraint rules into shared multi-tenant compiler pipelines
2.  Insecure parsing of untrusted constraint inputs leading to denial-of-service (DoS) or remote code execution (RCE)
3.  Tampering with compiled constraint artifacts during distribution via man-in-the-middle (MitM) attacks
4.  Excessive CPU/memory consumption via overly complex or recursively nested constraint definitions
5.  Accidental leakage of sensitive host or user context during constraint evaluation workflows
6.  Compromise of third-party dependencies leading to tainted compiler outputs or supply chain attacks
7.  Bypasses of input validation checks that enforce constraint policy boundaries and access controls
8.  Forgery of official release binaries or signatures due to inadequate cryptographic signing practices

## CVE Process
Upon confirming a valid vulnerability, we will collaborate directly with the reporter to secure a unique CVE ID via GitHub Security Advisories or direct MITRE submission. We will credit the reporter in the advisory unless they request anonymity. We will publish a fixed release promptly, coordinate embargoed disclosure, and post a detailed security advisory in the GitHub Security Advisories tab alongside formal release notes.

## Security Updates
Security patches are exclusively backported to the supported 0.x version track for consistency. Fixed releases include updated semver tags, signed artifacts, and announcements via GitHub Releases, the project’s official mailing list, and community channels. We also publish SBOMs for all official releases to support dependency vulnerability tracking, with changelog entries detailing each vulnerability and remediation steps.

## Signing of Releases
All official FLUX Constraint Compiler release artifacts—pre-built binaries, OCI container images, and source tarballs—are signed using cosign. The official cosign public key is hosted in the repo root at `/cosign.pub`. Users can verify artifacts with commands like `cosign verify --key cosign.pub ghcr.io/cocapn/flux-compiler:v0.1.0` to confirm authenticity and integrity.

## Audit Schedule
We run weekly dependency scans via GitHub Dependabot to catch third-party library flaws early. We conduct quarterly internal security audits of core compiler parsing and evaluation logic. Annually, we commission third-party supply chain audits and penetration testing of integrated constraint enforcement workflows to mitigate unaddressed supply chain and runtime risks.