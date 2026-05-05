# Open Strategy — Why We Don't Patent

## Decision

Everything FLUX is **Apache 2.0**. No patents. No provisional filings. No defensive claims.

## Why

Patents protect incumbents. We're challengers. Our moat isn't legal — it's ecosystem.

1. **Adoption > protection.** A patent that nobody infringes because nobody uses your tech is worthless. An open standard that everyone depends on is priceless.

2. **Going viral requires zero friction.** Every patent clause in a license is friction. Engineers skip patented tech for the open alternative, even if inferior.

3. **Standards win.** Safe-TOPS/W as an open benchmark gives us definitional authority. FLUX ISA as an open spec makes us the reference implementation. Neither works if gated by patents.

4. **The real moat:**
   - Running code (50 opcodes, 55 tests, published packages)
   - Ecosystem (compiler, VM, bridge, AST, assembler)
   - Community (first mover in a category we defined)
   - Certification expertise (can't patent a DO-254 audit)

5. **Historical precedent:**
   - ARM's business is IP licensing, not patents
   - RISC-V beat MIPS precisely because it was open
   - Linux won servers without a single patent
   - Kubernetes won orchestration by being open

## What We Keep Proprietary

Nothing. All code, all specs, all papers — Apache 2.0.

If someone wants to build a FLUX-compatible chip, great. They'll need our expertise to certify it, and that's the consulting revenue.

## Business Model (Revised)

| Revenue | Source | Timeline |
|---------|--------|----------|
| Certification consulting | Help OEMs pass DO-254 with FLUX | Months 1-12 |
| IP licensing (copyright, not patent) | FLUX compiler + toolchain enterprise | Year 1+ |
| Reference designs | Pre-certified FPGA/ASIC for specific platforms | Year 1-2 |
| Benchmark authority | Safe-TOPS/W scoring and auditing | Year 1+ |
| Training & certification | FLUX developer certification program | Year 2+ |

No patents needed for any of these.

## Action Items

- [x] Decision made: Apache 2.0 for everything
- [ ] Add Apache 2.0 headers to all source files
- [ ] Update investor one-pager (remove patent claims)
- [ ] Update strategic docs (remove patent references)
- [ ] Archive patent drafts (keep as prior art, not filings)
- [ ] Add CLA (Contributor License Agreement) for community contributions
- [ ] Publish FLUX ISA spec as open standard on website
