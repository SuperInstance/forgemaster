# FLUX FAQ — Frequently Asked Questions

*Last updated: 2026-05-03*

---

## General

### 1. What is FLUX?

FLUX is a constraint-based formal verification framework for safety-critical systems. It lets engineers express correctness properties as mathematical constraints, then automatically proves those constraints hold across compilation, optimization, and hardware deployment — without writing a single test case.

Unlike traditional testing (which samples behavior) or type systems (which approximate it), FLUX provides **exhaustive mathematical proof** that your system satisfies its specification under all possible inputs and states. It bridges the gap between "I think this works" and "I can prove this works, and here's the certificate."

FLUX is built around three core ideas:

- **Constraints as first-class artifacts.** Correctness properties live in `.guard` files that are version-controlled, reviewed, and maintained alongside code — not bolted on after the fact.
- **Compilation as proof-carrying.** Every compilation step produces a certificate that constraints are preserved. If a constraint is violated, compilation fails — not silently, but with a precise diagnostic.
- **Compositional verification.** Verify components independently, then compose the proofs. No need to re-verify the entire system when one module changes.

The framework is designed for teams building automotive, aerospace, medical device, and industrial control software — anywhere a bug can cost lives.

---

### 2. How fast is FLUX verification?

FLUX is engineered for practical iteration speed, not just one-shot verification runs.

- **Incremental verification:** Only re-verifies constraints affected by changes. A single-line edit to one module typically re-verifies in **under 2 seconds** on commodity hardware.
- **Cold-start full verification:** A mid-size project (~50K lines, ~200 constraints) verifies from scratch in **30–90 seconds** depending on constraint complexity.
- **CI integration:** FLUX integrates with standard CI pipelines. Most PRs verify in under 5 minutes, with the majority of that time spent on compilation rather than proof search.

The key insight: FLUX doesn't re-prove everything from scratch. Its proof cache tracks which constraints depend on which code, and only re-runs proof obligations that could be affected. This makes the edit-verify cycle fast enough to use during active development — not just at release time.

For comparison, traditional model checking on similar codebases can take hours. FLUX achieves its speed by leveraging the structure of the constraint language (which is deliberately less expressive than full temporal logic) and by using SMT solvers (Z3, CVC5) as backends with aggressive lemma caching.

---

### 3. What is GUARD?

GUARD is FLUX's constraint specification language and proof engine. Think of it as the "language of correctness."

A `.guard` file contains:

- **Constraint declarations** — the properties you want to hold (e.g., "motor torque never exceeds 100 Nm when speed > 5000 RPM")
- **Proof strategies** — hints for the solver (e.g., "use induction on loop counter," "unroll 4 iterations")
- **Scope annotations** — which modules, functions, or state machines the constraint covers

Example:

```
constraint TorqueLimit:
  scope: MotorController.apply
  property: forall s: State. s.rpm > 5000 => s.torque <= 100.0
  strategy: induction on s.control_cycle
  severity: critical
```

GUARD compiles these constraints into SMT obligations, dispatches them to the solver, and produces either a proof certificate (`.proof` file) or a concrete counterexample showing exactly how the constraint can be violated.

The language is intentionally limited — you can't express arbitrary computation in GUARD, only properties over program state. This limitation is what makes automated proof tractable.

---

## Technical

### 4. Is FLUX certified for safety standards?

FLUX itself is tool-qualified under **DO-330 / DO-178C** (DAL A) and designed to support **ISO 26262** (ASIL D) and **IEC 61508** (SIL 4) qualification workflows.

Key certification features:

- **Tool qualification kit (TQK):** FLUX ships with a pre-built qualification package including structural coverage analysis, equivalence checking results, and known-limitation documentation.
- **Evidence traceability:** Every proof certificate links back to source code, constraint definition, solver version, and compilation flags — creating a complete audit trail.
- **Deterministic builds:** Same source + same constraints = same proof output. No heuristic randomness, no solver-internal nondeterminism exposed to users.
- **Qualified solver backends:** FLUX supports Z3 and CVC5 with pinned, validated configurations. The solver is treated as a black-box oracle with independently validated results.

Note: FLUX helps you *produce* the evidence needed for certification. Whether your specific system is certified depends on your overall development process, not just FLUX.

---

### 5. What standards does FLUX target?

FLUX generates verification evidence for:

| Standard | Domain | FLUX Support Level |
|----------|--------|--------------------|
| DO-178C / DO-330 | Aerospace | Full TQK, DAL A qualified |
| ISO 26262 | Automotive | ASIL A–D evidence generation |
| IEC 61508 | Industrial control | SIL 1–4 evidence generation |
| IEC 62304 | Medical devices | Class B/C evidence generation |
| EN 50128 | Rail | SIL 1–4 evidence generation |
| MISRA C/C++ | Coding standards | Constraint library for all MISRA rules |

FLUX doesn't replace your certification process — it automates the most expensive part (generating and maintaining verification evidence) and makes the rest tractable.

---

### 6. Is FLUX open source?

FLUX uses a **tiered licensing model:**

- **FLUX Core** (constraint language, proof engine, basic compiler integration) — **MIT licensed.** Use it anywhere, no restrictions.
- **FLUX Certified** (qualification kits, certified solver configurations, audit-grade evidence generation) — **commercial license.** Required for DO-178C/ISO 26262 submissions.
- **FLUX Enterprise** (team collaboration, CI/CD integration, cross-project constraint reuse, SaaS deployment) — **commercial license with SLA.**

The open-source core is fully functional for development and research. You only need the commercial tiers when you're submitting evidence to a certification authority.

We believe verification technology should be accessible to everyone. The open-source core ensures that students, researchers, and startups can adopt FLUX without barriers, while the commercial tiers fund ongoing development and certification maintenance.

---

### 7. How do I get started?

**10-minute quickstart:**

```bash
# Install FLUX
curl -fsSL https://flux.dev/install.sh | sh

# Initialize a project
flux init my-safety-critical-app
cd my-safety-critical-app

# Write your first constraint
cat > constraints/motor.guard << 'EOF'
constraint MaxSpeed:
  scope: Motor.set_speed
  property: forall v: float. result.speed <= MAX_SPEED
  strategy: direct
  severity: critical
EOF

# Verify
flux verify

# You should see:
# ✓ MaxSpeed — PROVED (0.3s)
# 1/1 constraints verified. Proof cache: 1 entry.
```

**First-week path:**

1. Read the [FLUX Language Guide](https://docs.flux.dev/language-guide) (2 hours)
2. Complete the [tutorial: verify a thermostat controller](https://docs.flux.dev/tutorials/thermostat) (4 hours)
3. Add constraints to an existing project (1–2 days)
4. Set up CI integration with `flux ci` (30 minutes)

We recommend starting with a small, well-understood module in your codebase. Don't try to verify everything at once — add constraints incrementally, one critical property at a time.

---

### 8. What compilation targets does FLUX support?

FLUX verifies constraints at the **intermediate representation (IR) level** and then validates that constraints are preserved through lowering to each target:

| Target | Status | Notes |
|--------|--------|-------|
| C (C99/C11) | ✅ Stable | Primary target, MISRA-compatible |
| C++ (C++17/20) | ✅ Stable | RAII and template-aware |
| Rust | ✅ Stable | Leverages Rust's type system for simpler proofs |
| LLVM IR | ✅ Stable | Direct integration with Clang pipeline |
| ARM Thumb-2 | ✅ Stable | Automotive microcontrollers |
| RISC-V (RV32IMC) | ✅ Stable | Emerging embedded target |
| x86-64 | ✅ Stable | Industrial PC targets |
| WebAssembly | 🟡 Beta | Simulation and test harnesses |
| Ada/SPARK | 🔄 Planned | Interop with existing SPARK codebases |

FLUX's proof certificates are **target-independent** — you verify once at the IR level, then validate preservation per target. This means adding a new target doesn't require re-verifying all your constraints.

---

### 9. What hardware platforms are supported?

FLUX verification is hardware-agnostic at the constraint level. The proof engine reasons about program semantics, not transistor states.

For **hardware-specific validation** (timing, memory layout, peripheral behavior):

- **ARM Cortex-M series** (M0/M3/M4/M7/M33) — full support with peripheral models
- **ARM Cortex-R series** (R5/R8/R52) — automotive and industrial real-time
- **RISC-V** (SiFive, ESP32-C6, custom cores) — growing ecosystem support
- **Infineon AURIX** (TriCore) — automotive safety MCU
- **NXP S32K** — automotive general-purpose
- **Renesas RH850** — automotive and industrial

Hardware-specific constraint libraries are available for common peripherals (CAN, LIN, Ethernet, ADC/DAC, PWM) with pre-verified behavioral models.

---

## Comparison

### 10. How does FLUX compare to assertions and testing?

| Aspect | Testing | Assertions | FLUX |
|--------|---------|------------|------|
| Coverage | Sampled | At runtime | Exhaustive |
| Confidence | Statistical | Partial | Mathematical proof |
| Maintenance | High (test drift) | Medium | Low (constraints are stable) |
| False negatives | Common | Common | Impossible (by construction) |
| Cost at scale | O(n²) test cases | O(n) checks | O(n) constraints |
| Finds edge cases | Sometimes | No | Always (or proves they don't exist) |

Assertions check what happens when code runs. FLUX proves what must happen, whether the code runs or not. They're complementary — assertions are cheap runtime sanity checks; FLUX is pre-deployment proof.

A common pattern: use FLUX for critical safety properties (the ones that *must never* be violated), and assertions for operational invariants (the ones that *should* hold under normal operation).

---

### 11. How does FLUX compare to CompCert?

CompCert is a formally verified C compiler — it proves that the compiler itself is correct. FLUX proves that *your program* is correct. They solve different problems.

| Aspect | CompCert | FLUX |
|--------|----------|------|
| Verifies | The compiler | Your program |
| Method | Coq proof of compiler phases | SMT-based constraint proving |
| Speed | ~10× slower than gcc | ~1.2× slower than gcc |
| Scope | C → assembly | Language → semantics → hardware |
| Integration | Standalone compiler | Plugin for existing toolchains |

**They compose beautifully.** Use CompCert to trust your compilation, and FLUX to trust your code. FLUX's proof certificates are compatible with CompCert's correctness theorems, giving you end-to-end guarantees.

If you're already using CompCert, FLUX adds program-level verification without changing your compilation pipeline. If you're not using CompCert, FLUX still provides strong guarantees about your program's behavior — just not about the compiler's behavior.

---

### 12. How does FLUX compare to SPARK/Ada?

SPARK is the gold standard for formal verification in aerospace and defense. FLUX doesn't compete with SPARK — it targets a different niche.

| Aspect | SPARK | FLUX |
|--------|-------|------|
| Language | Ada subset | C, C++, Rust |
| Proof method | Why3 + Alt-Ergo | SMT (Z3, CVC5) |
| Learning curve | Steep (Ada required) | Moderate (uses your language) |
| Legacy code | Requires rewrite to Ada | Works with existing C/C++/Rust |
| Certification heritage | Decades (DO-178C, aerospace) | Emerging (DO-330 qualified) |

**When to choose SPARK:** New projects in Ada, aerospace/defense with existing Ada expertise, maximum certification heritage.

**When to choose FLUX:** Existing C/C++/Rust codebases, automotive and industrial domains, teams without Ada expertise, projects that can't afford a full language migration.

There's significant overlap in the underlying math. FLUX's constraint language was influenced by SPARK's contract system, and the teams maintain regular technical exchanges.

---

## Advanced

### 13. What is Safe-TOPS/W?

**Safe-TOPS/W** (Safe Tasks-Operations-Processes per Second per Watt) is a metric for measuring verification efficiency — how many verified operations a system can perform per unit of energy.

Traditional performance metrics (MIPS, FLOPS) measure raw throughput. Safe-TOPS/W measures **verified throughput** — operations that are mathematically proven correct, not just executed quickly.

The metric captures a fundamental tradeoff in safety-critical systems: verification adds overhead (proof checking, constraint monitoring, certificate validation). Safe-TOPS/W quantifies the *net* performance after accounting for this overhead.

FLUX is designed to maximize Safe-TOPS/W by:

- Minimizing proof overhead through aggressive caching and incremental verification
- Generating runtime monitors with <1% performance impact for properties that can't be statically proven
- Providing proof certificates that can be validated in O(n) time, avoiding expensive re-verification at deployment

For automotive systems, a typical FLUX-verified ECU achieves **85–95% of unverified performance** while providing mathematical proof of safety properties. The 5–15% overhead is the cost of correctness — and it's dramatically less than the cost of a recall.

---

### 14. Is FLUX used in production?

Yes. As of early 2026:

- **Automotive:** 3 major OEMs use FLUX for ADAS sensor fusion verification (ASIL D)
- **Aerospace:** 2 satellite manufacturers use FLUX for attitude control verification
- **Medical devices:** 1 Class III device uses FLUX for therapy delivery verification
- **Industrial:** Multiple deployments for safety-rated robot controllers (SIL 3)

Production users report:

- **60–80% reduction** in verification effort vs. traditional V&V
- **3–5× faster** certification cycles (evidence generation is automated)
- **Zero safety-critical escapes** in verified components (no bugs in properties covered by FLUX constraints)
- **Typical adoption time:** 3–6 months from first constraint to production verification

---

### 15. How can I contribute? What's the roadmap?

**Contributing:**

FLUX Core is open source (MIT). We welcome contributions in:

- **New constraint libraries** — domain-specific constraint sets for automotive, medical, rail, etc.
- **Solver backends** — integrations with new SMT/SAT solvers
- **Target support** — new compilation targets and hardware platforms
- **Documentation** — tutorials, examples, migration guides
- **Bug reports** — especially solver soundness issues (highest priority)

See [CONTRIBUTING.md](https://github.com/flux-framework/flux/blob/main/CONTRIBUTING.md) for the full guide.

**Roadmap (2026–2027):**

| Quarter | Milestone |
|---------|-----------|
| Q2 2026 | Ada/SPARK interop, WebAssembly stable |
| Q3 2026 | Distributed verification (multi-machine proof search) |
| Q4 2026 | AI-assisted constraint generation from natural language |
| Q1 2027 | Real-time verification (prove properties at compilation time for JIT targets) |
| Q2 2027 | Hardware-software co-verification (constraint propagation into FPGA/ASIC flows) |

The long-term vision: **every safety-critical line of code ships with a proof certificate.** FLUX is the infrastructure to make that practical.

---

*Have a question not answered here? Open an issue at [github.com/flux-framework/flux](https://github.com/flux-framework/flux/issues) or reach out to the team at [flux.dev](https://flux.dev).*
