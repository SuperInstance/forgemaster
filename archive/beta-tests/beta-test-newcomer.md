# Newcomer Beta Test Report
## constraint-theory-ecosystem — Full Journey

**Date:** 2026-05-19
**Persona:** Software developer who found a link, knows nothing about constraint theory
**Background:** Generalist, comfortable with Python/JS/C, no hardware engineering background

---

## Step 1: First Impression

### What is this? (10-second scan)

The subtitle is clear: *"The math that hardware engineers already know. Tolerance stacks, interference fits, and o-rings — formalized. 47 implementations, 62B checks/sec, formally proven."*

In 10 seconds I know this is about replacing floating-point with integer checks for software verification. The "float lies" pitch is immediately compelling — every developer has hit NaN/precision bugs.

### Is the opening interesting enough?

**Yes, surprisingly.** The opening doesn't waste time with vision statements. It leads with the problem (float lies), the solution (integer range checks), and the evidence (62B checks/sec, zero mismatches). The benchmark table is right there on the first screen. I don't have to scroll past a manifesto to find the meat.

The FP16 row — *"76% mismatches"* — is the killer argument. That one line justifies the entire project.

### Questions after the first page

1. What's "Eisenstein" about? The main README mentions it but doesn't explain.
2. What's the "hex arithmetic"? I see hexgrid-gen and "hex" mentioned but no intro.
3. The pipeline says GUARD → FLUX-C → GPU/ARM/FPGA → Coq. Can I actually USE any of this as a regular developer, or is this purely an embedded/safety-critical tool?
4. The "47 languages" link — how complete are these ports? Toy implementations or real?
5. Who is this FOR? Embedded engineers? Game developers? Backend devs who want bounds checking?

---

## Step 2: Follow the Trail

### flux-vm-v3

**Does it make sense?** Yes, mostly. A stack-based VM with 60 opcodes, no backward jumps (termination guaranteed), proof certificates. The 10 industry presets (automotive, aviation, medical, etc.) immediately show me this is real-world stuff.

The insight table ("each opcode exists because a specific language revealed a need") is cool. Forth → stack ops, GD&T → bounds ops, Koka → effects. This gives me confidence the ISA wasn't designed in a vacuum.

**What confused me:** "Error mask (u8)" — took me a second to realize this is a bitmask where each bit = one constraint pass/fail. A one-sentence explanation earlier would help. (I figured it out from context, but there was a brief "wait, what?" moment.)

The 179M checks/sec benchmark number is striking. The JIT compilation path (ucomisd → bitmask construction → NaN trap at loop top) is nicely explained.

### guardc-v3

**What is GUARD?** It's a tiny DSL for defining numeric constraints with bounds and severity levels. Think: `constraint coolant_temp: -40.0 <= x <= 150.0 severity CAUTION`.

**Immediate thought:** This is basically YAML for bounds checking. Which... is actually a good idea? The severity levels (PASS/CAUTION/WARNING/CRITICAL) map cleanly to how real systems categorize violations.

The compiler pipeline diagram is clear: GUARD → Lexer → Parser → AST → FLUX-C bytecode → SHA-256 proof hash. I can follow every step.

**Confusion:** The syntax description says severity requires `">constraint <name>: <lo> <= x <= <hi> severity <level>"` — that leading `>` looks like a markdown artifact that leaked into the code block. Minor but distracting.

### flux-docs

**Read index and getting-started.** The README is sparse — it lists directories but doesn't give me a clear "start here" path beyond the 5-minute tutorial reference. The getting-started tutorial exists at `tutorials/quickstart-5min.md`.

**Can I follow the 5-minute tutorial?**

No. The tutorial tells me to clone `https://github.com/flux-rs/flux-compiler` — **this repo does not exist**. Dead end on step 1. The tutorial references a completely different org (`flux-rs`) that doesn't appear to be part of SuperInstance.

This is the worst moment in the entire journey. The documentation literally sends me to a nonexistent GitHub repo.

---

## Step 3: Documentation — The Concept Pages

### The concept pages don't exist

The directories `concepts/error-mask.md`, `concepts/nan-trap.md`, `concepts/fracture-coalesce.md`, and `concepts/sediment.md` all 404. I cloned flux-docs to check — there's no `concepts/` directory at all. The repo has `tutorials/`, `runbooks/`, `strategy/`, and `man/` but no concepts.

**This is a significant gap.** The main ecosystem README and multiple other repos reference fracture-coalesce and sediment as core concepts, but there's no dedicated explanation of them in the docs repo. The closest I got was the flux-check-js README which explains them inline.

What I gathered from piecing together references across repos:

- **Error mask:** A u8 bitmask where each bit = one constraint's pass/fail. Bit 0 = constraint 0, etc.
- **NaN trap:** A check that flags NaN as always-violating. The "bug that started this."
- **Fracture-coalesce:** Split independent constraints into blocks (BFS connected components on a bipartite graph), check each block separately, OR the results together. Lossless because independent blocks have disjoint event spaces.
- **Sediment:** Immutable correction layers that stack over time. "We widened the coolant temp range after the sensor upgrade." Append-only history.

These explanations are scattered across 4-5 repos. There's no single place that defines all four concepts together.

### Physical Engineer's Guide

**This is the best piece of documentation in the entire ecosystem.** O-rings, tolerance stacks, gauge blocks — I'm a software person and I understood every word. The rubber ruler metaphor for floating-point is perfect. The worked O-ring example (AS568-214) showing `squeeze in [15, 25]` → GUARD → FLUX-C bytecode makes the whole pipeline concrete.

The INT8 saturation / -128 problem section is excellent. "Imagine a torque wrench that reads -128 ft-lbs. You try to negate it and it still reads -128. Your wrench is broken." That's the kind of writing that teaches.

---

## Step 4: Try to Actually Use Something

### Python — polyformalism-a2a

**Installation:** `pip install polyformalism-a2a` — worked first try. Already installed, version 0.1.1.

**README says:**
```python
similarity = profile.align(other_profile)
```

**Reality:** `AttributeError: 'IntentProfile' object has no attribute 'align'`

The actual method is `cosine_similarity()`. The README example is wrong — it references a method that doesn't exist.

After finding the right method by inspecting `dir(profile)`, it works:
```
Similarity: 0.93
Flavor: [(Channel.STAKES: 9, 0.95), (Channel.PROCESS: 3, 0.9), (Channel.SOCIAL: 5, 0.9)]
```

**But wait** — this is the *intent alignment* library, not the constraint checking library. The README is for polyformalism (9-channel intent vectors), not for the core constraint engine. I'm not sure where the Python *constraint checking* library lives. The main README links to `polyformalism-a2a-python` as "Python — PyPI package" but that's the intent profiling thing, not bounds checking.

### JavaScript — @flux/check

**Installation:** `npm install @flux/check` — **404 Not Found**. Not published to npm.

The package.json says `name: "@flux/check"` but it's not on the registry. I had to clone the repo directly and use it locally.

**After cloning, it works:**
```javascript
const engine = new ConstraintEngine();
engine.addConstraint("coolant_temp", -40, 150);
// ...
result = engine.check({ coolant_temp: 3000, ... });
// Error mask: 11111011, 7 violations detected
```

The API is clean and the code works. But you can't `npm install` it. You have to know to clone the repo.

### C — eisenstein

The C header (`eisenstein.h`) is 600 lines, no deps, no math.h, ~1KB .text. Extremely clean for embedded use. But this is just the hex/Eisenstein arithmetic, not the full constraint engine. `flux-engine-c` would be the combined header but I didn't test it.

### Summary of Step 4

| Package | Install works? | README examples work? | Usable? |
|---------|---------------|----------------------|---------|
| polyformalism-a2a (Python) | ✅ Yes | ❌ `align()` doesn't exist | ⚠️ After fixing method name, yes |
| @flux/check (JS) | ❌ Not on npm | ✅ Code works locally | ⚠️ Must clone repo |
| eisenstein-c (C) | ✅ Clone & compile | ✅ | ✅ |

---

## Step 5: The Old Languages

### flux-cobol

**Does it teach me something?** Yes, actually. The "What COBOL Teaches Us" section is the best part:

- **OCCURS is a schema constraint, not a runtime check.** `OCCURS 8 TIMES` means the compiler won't let you access index 9. Safety by construction, not safety by testing.
- **DATA DIVISION forces you to design data before writing logic.** You must declare every record before writing a single line of procedure. "The schema IS the architecture."
- **Copybooks are compile-time dependency injection.** Every program sees the same layout. No runtime type mismatches. No version skew.

I've never written COBOL and I walked away with three genuinely useful architectural insights.

### flux-rpg

**The insight about indicators:** RPG has had bitmask-based error flags since 1959. `*IN01` through `*IN99` — the constraint engine's error mask is literally RPG's indicator array. That's not retro computing, that's frozen architecture.

**Control breaks as natural batching:** L1-L9 group boundaries = fracturing into independent blocks. RPG was doing block decomposition before graph theory formalized it.

**Packed decimal = exact arithmetic.** No float drift. The constraint engine uses Packed(7,0) for zero rounding error bounds checks.

### flux-mumps

**"COBOL computes. MUMPS remembers."** This is the best one-liner in the entire ecosystem. MUMPS globals (`^VAR`) persist across sessions, survive crashes, and are shared between processes. That's where sediment layers actually live — corrections that outlive any single execution.

The post-conditional syntax (`S:condition value` — execute SET only when condition is true) being "guard clauses as syntax" is a genuine insight.

**Overall on old languages:** These are the most surprising and valuable part of the ecosystem. Each one teaches a real architectural lesson, not just "look, COBOL exists." The "What [Language] Teaches Us" sections are worth reading even if you never touch the code.

---

## Step 6: Org Profile

The SuperInstance org README is... massive. It's not about constraint theory at all — it's about the entire Cocapn project: shells, tiles, PLATO, agents, fleets, MoS (Mixture of Shells), conservation laws.

As a newcomer who just found the constraint theory link, this is **overwhelming and confusing**. I came here for "replace float with int" and now I'm reading about γ + H = 1.283 − 0.159·ln(V) conservation laws and agent fleets.

The org profile doesn't help me understand constraint theory. It makes the project feel much bigger and more abstract than the ecosystem README led me to believe. If anything, it made me less confident — "is this a math project or an agent framework?"

**Recommendation:** The org profile needs a "Start here" section that routes newcomers to constraint-theory-ecosystem specifically, with a one-sentence framing like "Constraint theory is the foundation — start there."

---

## Step 7: Overall Assessment

| Dimension | Score | Notes |
|-----------|-------|-------|
| **First impression** | **8/10** | Strong problem statement, compelling FP16 comparison, benchmark table on page 1. Would keep reading. |
| **Learning curve** | **6/10** | Physical Engineer's Guide is excellent (9/10). But the concept pages are missing, and terms like "Eisenstein", "hex arithmetic", "fracture-coalesce" are used without introduction in the main README. |
| **Documentation quality** | **5/10** | The Physical Engineer's Guide is the best doc. But: concept pages don't exist, the 5-minute tutorial points to a nonexistent repo, the Python README has a wrong method name, and the JS package isn't on npm. The *writing* quality is high; the *accuracy* and *completeness* need work. |
| **Would you bookmark this** | **Yes** | The core idea (integer bounds checks instead of float comparisons) is genuinely useful. The 62B checks/sec number is memorable. I'd come back for the Physical Engineer's Guide alone. |
| **Would you recommend to a colleague** | **Yes, with caveats** | "Read the Physical Engineer's Guide and the old language repos. Don't try the quickstart tutorial. Clone flux-check-js directly if you want to play with it." |
| **ONE thing that would make me stay vs leave** | **A working quickstart.** The 5-minute tutorial is the single point of failure. It's the first thing a newcomer tries, and it's broken (nonexistent repo). Fix that and the rest of the friction is tolerable. Leave it broken and a lot of people will close the tab. |

---

## Step 8: Specific Feedback

### Broken Links / Dead Ends

1. **`flux-rs/flux-compiler`** — The 5-minute tutorial's `git clone https://github.com/flux-rs/flux-compiler.git` returns 404. This is Step 1 of the tutorial. **Critical.**
2. **`concepts/error-mask.md`** — 404. Referenced in the task but doesn't exist in the repo.
3. **`concepts/nan-trap.md`** — 404.
4. **`concepts/fracture-coalesce.md`** — 404.
5. **`concepts/sediment.md`** — 404.
6. **`@flux/check` on npm** — 404. Package exists in the repo but isn't published.
7. **Quickstart "Next Steps" links** — All reference `flux-rs.github.io/flux-compiler/` which presumably also doesn't exist (org doesn't exist).
8. **Physical Engineer's Guide "Part II" link** — Points to `../chapters/ch08-gpu-architecture.md`. I didn't verify but the path structure (`chapters/`) looks different from the actual `docs/` structure.

### Confusing Sentences / Unclear Jargon

1. **"Eisenstein"** — Used throughout (eisenstein crate, eisenstein-c, eisenstein-wasm) but never explained in the main README. Is this a person? A mathematical structure? I still don't know after reading everything.
2. **"Hex arithmetic"** — Same. What makes it "hex"? Hexagonal? Hexadecimal? The hexgrid-gen repo suggests hexagonal grids but the connection isn't stated.
3. **"SplineLinear (Eisenstein lattice weight parameterization)"** — In TOOLS.md context, sounds impressive but means nothing to a newcomer.
4. **Main README:** "The same constraint core has been ported to 47 languages and runtimes." — Are these all in the `ports/` directory? I didn't verify but the claim is front-and-center.
5. **"polyformalism a2a"** — What does "a2a" mean? Attention-to-activation? Agent-to-agent? Never explained.

### Wrong Documentation

1. **Python README:** `profile.align(other_profile)` → method is actually `profile.cosine_similarity(other_profile)`.
2. **5-minute tutorial:** References `flux-rs/flux-compiler` which doesn't exist.
3. **guardc README:** Syntax block has a leading `>` that looks like a markdown artifact: `: severity ">constraint <name>...`

### Things I Had to Google

1. **Eisenstein integers** — Wikipedia tells me these are complex numbers of the form a + bω where ω = e^(2πi/3). They form a hexagonal lattice. NOW the "hex arithmetic" makes sense. This should be explained in the README.
2. **Gauge blocks** — The Physical Engineer's Guide explains this well, so I didn't actually need to Google it. Good.
3. **GD&T** — Geometric Dimensioning and Tolerancing. The Physical Engineer's Guide assumes you know this. A one-sentence gloss would help non-engineers.
4. **DO-178C** — Aviation software certification standard. Referenced without explanation.
5. **ULP** — Unit in the Last Place. The Physical Engineer's Guide uses it without defining it initially (does define it later as "unit in the last place").

### Moments I Almost Gave Up

1. **The 5-minute tutorial dead end** — The very first thing I tried to follow was broken. If I weren't doing a deliberate test, I would have closed the tab here.
2. **The concept pages 404s** — After the tutorial failed, I went looking for conceptual docs. Four consecutive 404s.
3. **npm install 404** — Third attempt to actually USE something, third failure. At this point a real newcomer is gone.
4. **The org profile overwhelm** — Finally found something that works (Physical Engineer's Guide), then clicked through to the org profile and got hit with agent frameworks and conservation laws. Briefly thought "this isn't what I signed up for."

---

## Summary for the Authors

**What's great:**
- The core idea is clear and well-argued. "Float is a rubber ruler" is the best metaphor I've seen for the precision problem.
- The Physical Engineer's Guide is a genuine masterpiece of technical writing.
- The old language repos are surprisingly educational.
- The benchmark numbers are concrete and compelling.
- The negative results section (what DOESN'T work) builds massive credibility.

**What needs fixing urgently:**
1. The 5-minute tutorial references a nonexistent repo. This is the #1 priority.
2. Publish `@flux/check` to npm, or add a "clone from GitHub" instruction.
3. Fix the Python README's `align()` → `cosine_similarity()` method name.
4. Create the missing concept pages (error-mask, nan-trap, fracture-coalesce, sediment).
5. Explain "Eisenstein" and "hex" in the main README — a two-sentence sidebar is enough.

**What would be nice:**
- A one-page glossary (Eisenstein, GD&T, DO-178C, ULP, Galois connection)
- A clearer separation between constraint theory (the math) and Cocapn (the agent framework)
- Installation instructions that have actually been tested on a clean machine
