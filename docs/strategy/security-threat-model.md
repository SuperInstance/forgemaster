# FLUX Security Threat Model

*Last updated: 2026-05-03*

---

## Overview

This document describes the security threat model for FLUX — the constraint-based formal verification framework. It covers threats to the toolchain itself, the verification evidence it produces, and the systems that rely on FLUX proofs.

**Scope:** FLUX Core (open source), FLUX Certified (commercial), and FLUX Enterprise (SaaS).

**Threat model philosophy:** FLUX occupies a privileged position in safety-critical development. A compromised FLUX could produce false proofs, allowing unsafe software to pass verification. The threat model therefore treats proof integrity as the highest-priority security property.

---

## Threats

### Threat 1: Malicious `.guard` Constraint Files

**Description:** An attacker crafts a `.guard` file that exploits parser ambiguities or solver edge cases to produce a false proof — making the system believe a constraint is satisfied when it isn't.

**Attack vector:**
- Supply chain compromise of a shared constraint library
- Malicious PR adding/modifying a `.guard` file in a verified project
- Compromised developer account pushing crafted constraints

**Impact:** **Critical.** A false proof could allow safety-critical violations to reach production. This is the most dangerous threat because it directly undermines FLUX's core value proposition.

**Likelihood:** **Low.** Requires deep knowledge of FLUX internals, solver behavior, and the target domain. The constraint language is intentionally limited to reduce attack surface.

**Mitigations:**
- **Constraint review requirement:** All `.guard` files must be peer-reviewed (enforced by FLUX Enterprise CI policies)
- **Solver validation:** Proof certificates are independently validated by a second solver (Z3 proofs checked by CVC5 and vice versa)
- **Proof auditing:** `.proof` files include full solver traces that can be independently replayed
- **Parser strictness:** The GUARD parser rejects ambiguous inputs and has no extension points that could introduce unsoundness
- **Constraint linter:** Static analysis on `.guard` files detects suspicious patterns (overly broad scopes, trivially true properties, contradictory constraints)

---

### Threat 2: Supply Chain Attacks on FLUX Dependencies

**Description:** FLUX depends on external libraries (Z3, CVC5, LLVM, language frontends). A compromise in any dependency could introduce vulnerabilities that affect proof soundness.

**Attack vector:**
- Compromised Z3 or CVC5 release producing false "sat" results
- Malicious LLVM pass that miscompiles verified IR while preserving proof certificates
- Typosquatting or dependency confusion in build system

**Impact:** **Critical.** A compromised solver could produce false proofs. A compromised compiler could invalidate proof preservation guarantees.

**Likelihood:** **Medium.** Supply chain attacks are increasing in frequency across the industry. FLUX's dependency chain is relatively small but includes high-value targets (Z3, LLVM).

**Mitigations:**
- **Pinned dependencies:** All dependencies are pinned to specific, audited versions. No floating version ranges.
- **Reproducible builds:** FLUX builds are deterministic. Any deviation from the expected binary indicates tampering.
- **Dependency auditing:** Automated daily audits of all transitive dependencies against CVE databases and advisory feeds.
- **Solver diversity:** Dual-solver verification (Z3 + CVC5) means a single compromised solver cannot produce a false proof without detection.
- **Trusted builder pipeline:** Release builds are performed in an isolated, auditable CI environment with signed build artifacts.

---

### Threat 3: Vulnerabilities in Generated Code

**Description:** FLUX generates runtime monitors, proof scaffolding, and verification harnesses. Vulnerabilities in this generated code could be exploited in the target system.

**Attack vector:**
- Buffer overflow in generated runtime monitor
- Integer overflow in generated constraint checking code
- Incorrect memory management in generated harness code

**Impact:** **High.** Generated code runs in the safety-critical target system. A vulnerability there is as dangerous as any other runtime bug.

**Likelihood:** **Low.** Generated code follows strict templates that have been formally verified. The code generator itself is part of the qualified toolchain.

**Mitigations:**
- **Template-based generation:** All generated code comes from a fixed set of templates that have been independently verified (including by FLUX itself — FLUX verifies its own generated code).
- **MISRA compliance:** Generated C/C++ code complies with MISRA rules and is checked by static analysis tools.
- **Memory safety:** Generated code uses bounded operations exclusively — no dynamic allocation, no unbounded loops, no unchecked array accesses.
- **Fuzzing:** The code generator is continuously fuzzed with random constraint inputs to detect edge cases.
- **Generated code review:** FLUX Enterprise provides diff-based review of generated code between versions, highlighting any changes in generated output.

---

### Threat 4: Proof Preservation Failures (Miscompilation)

**Description:** An optimization pass or code transformation invalidates a previously proven constraint, but the proof certificate is not correctly invalidated.

**Attack vector:**
- Bug in proof preservation checking logic
- Race condition in incremental verification cache
- Incorrect scope analysis causing stale proof reuse

**Impact:** **Critical.** A stale proof certificate is equivalent to a false proof — it claims a property holds when it doesn't.

**Likelihood:** **Low–Medium.** This is a correctness bug, not a malicious attack, but the impact is equivalent. Proof preservation is the most rigorously tested component of FLUX.

**Mitigations:**
- **Conservative invalidation:** The proof cache is invalidated on any change that *might* affect a constraint, even if the change turns out to be irrelevant. False negatives (unnecessary re-verification) are preferred over false positives (stale proofs).
- **Dependency tracking:** Every proof certificate records its exact dependencies (source lines, compiler flags, optimization level, target). Any change to any dependency invalidates the certificate.
- **Full re-verification option:** `flux verify --full` bypasses the cache and re-verifies everything. Recommended for release builds.
- **Smoke testing:** FLUX's own test suite includes adversarial cases where known-invalid code is paired with stale proof certificates to verify they're correctly rejected.

---

### Threat 5: Credential and Key Leakage

**Description:** FLUX Certified and Enterprise use signing keys for proof certificates, release artifacts, and license validation. Leakage of these keys would allow an attacker to forge proof certificates or distribute tampered FLUX builds.

**Attack vector:**
- Compromised CI/CD pipeline exposing signing keys
- Developer laptop compromise with cached credentials
- Insider access to key storage

**Impact:** **Critical.** Forged proof certificates would undermine the entire trust chain. Forged release signatures would allow distribution of compromised FLUX builds.

**Likelihood:** **Low.** Keys are stored in HSMs with strict access controls.

**Mitigations:**
- **Hardware Security Modules (HSMs):** All signing keys are stored in FIPS 140-3 Level 3 HSMs. Keys never leave the HSM.
- **Key rotation:** Signing keys are rotated annually. Old keys are revoked and certificates re-signed.
- **Multi-party signing:** Release artifacts require signatures from two independent key holders (no single point of compromise).
- **Certificate transparency:** All proof certificate signing events are logged to an append-only transparency log, auditable by customers.
- **License key isolation:** FLUX Enterprise license keys are scoped to specific organizations and cannot be used to sign proof certificates.

---

### Threat 6: Denial of Service (Verification Overload)

**Description:** An attacker crafts inputs (source code or constraints) that cause FLUX verification to consume excessive resources — CPU, memory, or time — blocking legitimate verification.

**Attack vector:**
- Pathological constraint that causes exponential solver blowup
- Crafted source code that generates quadratic proof obligations
- Filing many CI verification requests simultaneously

**Impact:** **Medium.** CI pipeline stalls, delayed releases, potential engineering productivity loss. No safety impact (FLUX fails closed — if it can't verify, it reports failure).

**Likelihood:** **Medium.** SMT solvers are known to have pathological cases. Accidental triggers are as likely as intentional ones.

**Mitigations:**
- **Resource limits:** FLUX enforces configurable per-constraint timeouts (default: 60s) and memory limits (default: 4GB). Exceeding limits is a verification failure, not a hang.
- **Solver strategy selection:** FLUX automatically detects pathological cases and switches to alternative proof strategies (e.g., bounded model checking instead of full induction).
- **CI queue management:** FLUX Enterprise limits concurrent verification jobs per organization and per project.
- **Constraint complexity budget:** Projects can set a maximum proof obligation count per constraint to prevent accidentally complex specifications.

---

### Threat 7: Timing Side-Channel in Proof Engine

**Description:** An attacker observes verification timing to infer properties of the constraints or source code being verified — potentially extracting proprietary algorithms or safety parameters.

**Attack vector:**
- Remote timing of FLUX Enterprise SaaS API responses
- Co-tenant observation on shared CI infrastructure
- Network traffic analysis of solver communication

**Impact:** **Medium.** Could reveal proprietary constraint definitions, algorithm details, or safety thresholds that should be confidential.

**Likelihood:** **Low.** Requires sophisticated attacker with access to the same network or infrastructure.

**Mitigations:**
- **Timing normalization:** FLUX Enterprise API adds randomized delay to verification responses, reducing timing signal.
- **Constant-time proof checking:** Certificate validation (the operation most exposed to external timing) is implemented in constant-time relative to constraint content.
- **Network encryption:** All solver communication uses TLS 1.3 with certificate pinning.
- **Infrastructure isolation:** FLUX Enterprise SaaS runs verification in isolated containers with no shared resources between tenants.

---

### Threat 8: Insider Threat

**Description:** A trusted insider with access to FLUX's build pipeline, signing infrastructure, or source repository introduces malicious changes.

**Attack vector:**
- Engineer commits subtle soundness bug to proof engine
- Build engineer modifies release artifacts after signing
- DevOps engineer exfiltrates signing keys from CI environment

**Impact:** **Critical.** Insider attacks bypass most external security controls and can directly compromise proof integrity.

**Likelihood:** **Low.** FLUX has a small, vetted team. But the impact warrants rigorous controls.

**Mitigations:**
- **Multi-party review:** All changes to the proof engine, solver integration, or certificate generation require review by at least two engineers, including one with formal methods expertise.
- **Hermetic builds:** Release artifacts are built in a hermetic environment with no human access. Build inputs and outputs are logged and auditable.
- **Reproducible builds:** Any engineer can reproduce any release build from source. Deviations from the expected output are immediately detectable.
- **Access segmentation:** No individual has access to both the source repository and the signing infrastructure.
- **Audit logging:** All access to sensitive systems (HSM, build pipeline, release bucket) is logged and reviewed weekly.

---

## Security Policy

### Responsible Disclosure

We welcome security research on FLUX. If you believe you've found a security vulnerability:

1. **Email:** security@flux.dev (PGP key available at [flux.dev/.well-known/security.txt](https://flux.dev/.well-known/security.txt))
2. **Encrypt** your report using our PGP key
3. **Include:** affected component, reproduction steps, potential impact, and any proof-of-concept
4. **Do not** file security issues in the public GitHub tracker

**Response timeline:**
- Acknowledgment within 24 hours
- Initial assessment within 72 hours
- Remediation plan within 7 days
- Patch release within 30 days (or coordinated disclosure timeline)

**We do not pursue legal action against good-faith security researchers.** See our full responsible disclosure policy at [flux.dev/security](https://flux.dev/security).

### CVE Process

FLUX participates in the CVE (Common Vulnerabilities and Exposures) program:

- All security vulnerabilities affecting proof soundness, certificate integrity, or build pipeline security receive CVE IDs
- CVEs are published after remediation is available
- Severity is assessed using CVSS v3.1 with safety-specific extensions (the impact of a false proof in a safety-critical system is assessed as "physical harm potential")
- CVE records include full technical details, affected versions, and remediation guidance
- We maintain a public CVE feed at [flux.dev/security/cves](https://flux.dev/security/cves) and an advisory mailing list

### Release Signing

All FLUX releases are cryptographically signed:

- **Source tarballs:** Signed with the FLUX release key (RSA-4096, stored in HSM)
- **Binary packages:** Signed with platform-specific keys (APT, RPM, Homebrew)
- **Proof certificates:** Signed with the FLUX Certificate Authority key (separate from release key)
- **Docker images:** Signed with Cosign (Sigstore) with transparency log entry

**Verification commands:**

```bash
# Verify source tarball
gpg --verify flux-2.1.0.tar.gz.asc flux-2.1.0.tar.gz

# Verify proof certificate
flux cert verify --ca flux-ca.pem build/output/proof.cert

# Verify Docker image
cosign verify fluxframework/flux:2.1.0
```

All signing keys are documented at [flux.dev/security/keys](https://flux.dev/security/keys) with fingerprints and expiration dates.

---

## Summary

| Threat | Impact | Likelihood | Primary Mitigation |
|--------|--------|------------|-------------------|
| Malicious .guard files | Critical | Low | Dual-solver validation, peer review |
| Supply chain attacks | Critical | Medium | Pinned deps, reproducible builds, solver diversity |
| Generated code vulns | High | Low | Template-based generation, MISRA compliance |
| Miscompilation / stale proofs | Critical | Low–Medium | Conservative cache invalidation, full re-verification |
| Credential leakage | Critical | Low | HSM storage, multi-party signing |
| DoS / verification overload | Medium | Medium | Resource limits, complexity budgets |
| Timing side-channels | Medium | Low | Timing normalization, infrastructure isolation |
| Insider threat | Critical | Low | Multi-party review, access segmentation |

**Highest-priority investment areas:** Supply chain hardening (increasing threat landscape), proof preservation correctness (core value proposition), and insider controls (highest impact per incident).
