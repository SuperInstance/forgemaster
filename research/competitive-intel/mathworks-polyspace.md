## Agent 3: MathWorks Polyspace

### Overview & Market Position

MathWorks Polyspace is the **dominant commercial static analysis suite** for C, C++, and Ada, embedded within the MATLAB/Simulink ecosystem that commands near-ubiquitous presence in automotive, aerospace, and control systems engineering. Polyspace comprises three core products: **Bug Finder** (defect and security vulnerability detection), **Code Prover** (abstract interpretation-based proof of runtime error absence), and **Test** (test generation and coverage). The R2024b release introduced the unified **Polyspace Platform** integrating all three.

Polyspace Code Prover uses **abstract interpretation** — a sound static analysis technique that over-approximates program behavior to prove the absence of runtime errors (divide-by-zero, array bounds, null pointers, etc.) without executing the code. This distinguishes Polyspace from heuristic-based bug finders: Code Prover provides **orange/green/red coloring** where orange indicates unproven code requiring review.

MathWorks' market power comes from **ecosystem lock-in**: engineers already using MATLAB for control design and Simulink for model-based design naturally adopt Polyspace for code verification. The company has aggressively expanded into ISO 26262 automotive compliance, IEC 61508 industrial safety, and DO-178C avionics.

### Technology Comparison vs FLUX

| Dimension | MathWorks Polyspace | FLUX |
|-----------|---------------------|------|
| **Core paradigm** | Abstract interpretation (sound static analysis) | GPU-native constraint bytecode execution |
| **Analysis type** | Whole-program over-approximation | Explicit constraint checking on GPU |
| **Performance** | CPU-bound; hours for large codebases | 90.2B constraints/sec on RTX 4050 |
| **Soundness** | Sound (no false negatives for RTE) | Sound compiler (Galois connection); exhaustive input checking |
| **Scalability** | Struggles with large C++ codebases, complex pointers | Scales with GPU memory (187 GB/s bandwidth) |
| **Integration** | Deep MATLAB/Simulink integration | Standalone + embeddable (14 crates, Rust ecosystem) |
| **Open source** | No (proprietary, license-managed) | Apache 2.0 |
| **GPU acceleration** | None | Native; INT8 x8 packing |
| **Pricing accessibility** | Enterprise ($6,000–$13,000+ EUR/seat) | Free (open source) |
| **Certification kits** | DO Qualification Kit, IEC Certification Kit | Emerging |

Polyspace Code Prover and FLUX share the **soundness commitment** but diverge fundamentally in **approach**. Polyspace reasons about all possible executions via abstract domains; FLUX explicitly checks constraints across massive input spaces via GPU parallelism. Polyspace's strength is **completeness without execution**; FLUX's strength is **concrete execution speed** and **actual runtime verification**.

### Pricing Model

MathWorks publishes pricing (Euro standard perpetual, March 2026):
- **Polyspace Bug Finder**: ~€3,640 (Network Named User) / ~€6,000 (Concurrent).
- **Polyspace Code Prover**: ~€6,000 (Network Named User) / ~€8,350+ (Concurrent).
- **Polyspace Bug Finder Server / Code Prover Server**: Enterprise pricing (€8,000–€12,000+ per worker).
- **DO Qualification Kit**: €13,300 (Network Named User).
- **IEC Certification Kit**: €6,000 (Network Named User).
- **MATLAB + Simulink base required**: €2,410 + €3,640 minimum.

Total per-seat cost for a complete Polyspace safety workflow with certification kits easily exceeds **€20,000–€30,000** ($22,000–$33,000 USD). MathWorks also offers annual subscription models at approximately 60% of perpetual cost per year.

### Certification Status

MathWorks provides qualification kits rather than TÜV certification for the tools themselves:
- **DO-178C**: DO Qualification Kit available (tool qualification support materials).
- **IEC 61508 / ISO 26262**: IEC Certification Kit provides tool qualification evidence.
- **Standards support**: MISRA C:2012, AUTOSAR C++14, CERT C/C++, CWE, JSF AV C++.

The qualification kit model shifts certification burden to the user — MathWorks provides templates and evidence, but the user must complete qualification. This is weaker than AdaCore's or ANSYS's pre-certified tools but stronger than unqualified open-source alternatives.

### Weaknesses FLUX Can Exploit

1. **Orange code problem**: Polyspace Code Prover marks significant code portions "orange" (unproven) on complex programs — particularly with pointers, dynamic memory, and loops. FLUX can concretely verify constraints on these exact code paths via GPU execution, reducing the orange-code burden.

2. **Ecosystem tax**: Polyspace requires MATLAB/Simulink licenses, creating a $20K+ barrier to entry. FLUX's open-source model and standalone architecture eliminate ecosystem dependencies.

3. **No runtime component**: Polyspace is strictly development-time. FLUX can deploy constraint VMs to embedded GPUs (Jetson, automotive SoCs) for continuous runtime monitoring — critical for SOTIF (ISO 21448) and expected safety argumentation.

4. **Slow analysis on large codebases**: Abstract interpretation complexity grows non-linearly. FLUX's GPU throughput is linear in input space size and can partition analysis across devices.

5. **False positive management**: While sound for RTE, Polyspace Bug Finder generates false positives requiring triage. FLUX's constraint checking is deterministic — a constraint either holds or fails, with no "maybe" state.

### Customer Overlap Analysis

**Highest overlap**: Automotive (Bosch, Continental, ZF, OEMs using MATLAB for controls), aerospace (Boeing/Airbus suppliers using Simulink), industrial automation. FLUX should:
- Target **Polyspace users frustrated with orange-code ratios** on complex C++.
- Offer **runtime constraint monitoring** as a value-add MathWorks cannot match.
- Compete on **cost** for startups and smaller Tier-2 suppliers priced out of MathWorks.

### Prebuttal: What MathWorks Would Say to Attack FLUX

**MathWorks attack vector**: "Polyspace Code Prover uses abstract interpretation — a mathematically rigorous technique proven over 40 years of academic research and industrial use. FLUX's 'constraint checking' is merely testing with more inputs. Testing cannot prove absence of errors — Edsger Dijkstra's famous dictum applies. Our orange code honestly indicates what we cannot prove; FLUX's green checkmarks merely indicate what was tested, not what is true. Furthermore, MathWorks has 600+ DO-178C programs and 360+ customers — FLUX has zero certification pedigree."

**FLUX counter**:
1. **Galois connection is proof, not testing**: FLUX's compiler correctness theorem proves that every constraint in GUARD DSL is semantically preserved in FLUX-C bytecode execution. This is formal verification of the verification pipeline — not merely testing.
2. **Exhaustive at scale**: While abstract interpretation over-approximates, it often fails to concretize. FLUX's 90.2B constraints/sec enables exhaustive checking of critical paths with concrete values — a complementary verification strategy, not a replacement.
3. **Runtime verification = proof in operation**: Polyspace cannot verify deployed systems. FLUX's GPU VM can execute constraints on production inputs, providing evidence of safe operation under actual environmental conditions — something abstract interpretation can never do.
4. **Open source + formal proof > black box + qualification kit**: Users can inspect FLUX's 38 proofs. MathWorks qualification kits are proprietary templates that still require extensive user effort to complete.

---