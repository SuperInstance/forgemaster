## Agent 1: ANSYS SCADE Suite

### Overview & Market Position

ANSYS SCADE Suite is the market-leading model-based development environment for safety-critical embedded software, with particular dominance in aerospace (flight controls, engine control), rail signaling, and automotive ECUs. SCADE Suite is built around a formally defined synchronous dataflow language (Lustre/SCADE) with graphical and textual modeling capabilities. Its crown jewel is the **KCG (Qualified Code Generator)**, which transforms models into C or Ada code and holds TQL-1 qualification under DO-178C/DO-330 — the highest possible tool qualification level.

ANSYS's 2024/2025 product evolution has focused on multicore code generation via the Multicore Code Generator, AUTOSAR integration for automotive, and continuous integration pipelines (notably the Volkswagen partnership). SCADE Suite is deeply embedded in the supply chains of Airbus, Boeing, Bombardier, Alstom, and major automotive OEMs. The product is positioned as a **premium enterprise solution** with pricing models that reflect its quasi-monopoly in qualified model-based code generation.

### Technology Comparison vs FLUX

| Dimension | ANSYS SCADE Suite | FLUX |
|-----------|-------------------|------|
| **Core paradigm** | Model-based design (synchronous dataflow) | Constraint-safety verification (GUARD DSL → bytecode) |
| **Verification approach** | Formal model verification + qualified code gen | GPU-native constraint checking + compiler correctness proof |
| **Execution target** | CPU (generated C/Ada) | GPU (FLUX-C bytecode VM, 43 opcodes) |
| **Performance** | Limited by CPU/RTOS; real-time deterministic | 90.2B constraints/sec (RTX 4050, 46.2W) |
| **Compiler correctness** | KCG qualified (TQL-1) via extensive testing | Galois connection mathematical proof (strongest theorem) |
| **Open source** | No (proprietary, closed) | Yes (Apache 2.0, 14 crates on crates.io) |
| **Language ecosystem** | SCADE, Lustre, imported Simulink | GUARD DSL (constraint-specification language) |
| **GPU acceleration** | None | Native INT8 x8 packing, 341B peak |
| **Certification pedigree** | DO-178C TQL-1, IEC 61508 SIL 3/4, ISO 26262 ASIL D, EN 50128 SIL 3/4 | Emerging (38 formal proofs, zero differential mismatches) |
| **Memory model** | Target-dependent (RTOS/embedded) | Memory-bound ~187 GB/s, INT8 quantization |

ANSYS SCADE and FLUX are **complementary at the architecture level but competitive at the verification level**. SCADE generates code; FLUX verifies constraints on code (or models). A powerful integration path exists: FLUX could verify safety constraints on SCADE-generated C code at GPU speeds, complementing SCADE's internal model verification with external, exhaustive constraint checking.

### Pricing Model

ANSYS does not publicly disclose SCADE Suite pricing, but industry intelligence indicates:
- **SCADE Suite + KCG**: Enterprise perpetual licenses typically **$30,000–$60,000 per seat**, with annual maintenance at 15–20%.
- **SCADE Test**: Additional **$10,000–$20,000** per seat for test and coverage modules.
- **DO-178C Certification Kit**: Sold separately as a premium add-on; quoted in the **six figures** for project-specific qualification evidence.
- **Multicore Code Generator**: Premium tier pricing, often bundled with consulting services.

ANSYS operates a high-touch enterprise sales model with substantial professional services revenue. The total cost of ownership for a DAL-A avionics project using SCADE can exceed **$500,000** in tooling alone before engineering labor.

### Certification Status

SCADE Suite KCG holds the most comprehensive certification portfolio in the model-based segment:
- **DO-178C / DO-330**: TQL-1 (highest tool qualification level) — qualified code generator for Level A software.
- **IEC 61508**: SIL 3 / SIL 4.
- **EN 50128**: SIL 3 / SIL 4 (rail).
- **ISO 26262**: ASIL D (automotive).
- **ECSS-E-ST-40C / ECSS-Q-ST-80C**: European space standards.

The KCG qualification is the primary competitive moat. No open-source or alternative tool has achieved TQL-1 for C/Ada code generation from synchronous models. ANSYS claims SCADE can deliver **up to 50% cost reduction** for DO-178C Level A projects compared to manual coding through elimination of coding errors and reduced verification effort.

### Weaknesses FLUX Can Exploit

1. **No GPU acceleration**: SCADE's verification and simulation are CPU-bound. As systems grow in complexity (multicore, AI-adjacent sensor fusion), CPU-based verification becomes a bottleneck. FLUX's 90.2B constraints/sec offers 3–4 orders of magnitude throughput advantage.

2. **Closed ecosystem lock-in**: SCADE models are not portable. Vendor lock-in creates long-term risk and suppresses innovation. FLUX's open-source model and standard bytecode VM enable portability and community extension.

3. **High cost and slow adoption cycle**: The enterprise sales model and pricing exclude mid-market players and startups. FLUX's open-source approach can penetrate the market bottom-up, analogous to how LLVM disrupted proprietary compilers.

4. **Limited runtime verification**: SCADE focuses on design-time verification. FLUX can perform continuous runtime constraint checking on deployed systems — a capability increasingly demanded in software-defined vehicles and autonomous systems.

5. **Model not code**: SCADE verifies models, but the gap between model and generated code (despite KCG qualification) remains a concern for some certifiers. FLUX verifies actual runtime behavior against constraints, closing the model-code-reality gap.

### Customer Overlap Analysis

**High overlap sectors**: Aerospace (Airbus, Boeing tier-1s), rail (Alstom, Siemens), automotive Tier-1s (Continental, Bosch). FLUX should target:
- SCADE users seeking **supplemental verification** (not replacement) for generated code.
- New entrants who cannot afford SCADE but need DO-178C/ISO 26262 compliance.
- Multicore avionics projects where SCADE's multicore codegen is nascent and expensive.

### Prebuttal: What ANSYS Would Say to Attack FLUX

**ANSYS attack vector**: "FLUX has no certification pedigree, no TQL-1 qualification, and no track record in safety-critical programs. Using an unqualified GPU bytecode VM for safety-critical constraint checking would introduce unacceptable certification risk. The DO-178C/DO-330 framework requires rigorous tool qualification evidence that FLUX cannot provide. Furthermore, GPU execution is inherently non-deterministic due to scheduling variability — unacceptable for DAL-A systems."

**FLUX counter**:
1. **Certification is a process, not a birthright**: FLUX's 38 formal proofs and zero differential mismatches across 10M+ inputs provide stronger evidential foundation than many TQL-3 tools had at qualification. FLUX can pursue TQL-1 via the same DO-330/ED-215 framework ANSYS uses.
2. **Deterministic GPU execution**: FLUX-C bytecode VM is deterministic by design (43 opcodes, fixed execution semantics). GPU scheduling variability does not affect computational results — only timing. FLUX separates functional correctness (verified) from timing analysis (profiled).
3. **Complementary, not replacement**: FLUX does not seek to replace KCG but to augment SCADE-generated code with GPU-accelerated constraint verification, reducing testing burden and finding corner cases CPU analysis misses.
4. **Open source = inspectable**: Apache 2.0 licensing means certifiers can inspect every line of FLUX — unlike ANSYS's black-box KCG.

---