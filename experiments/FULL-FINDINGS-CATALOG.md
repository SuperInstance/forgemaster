# Full Findings Catalog: Vocabulary Rerouting Effect (R27-R56)
## Forgemaster ⚒️ | 2026-05-15 | 27 Studies | 30 Findings

---

## BEDROCK (18 findings — build on these)

| R# | Finding | Study | Key Evidence |
|----|---------|:-----:|-------------|
| R27 | Scaffolding is architecture-dependent (thinking vs non-thinking) | 9 | phi4-mini 64% with scaffold, qwen3:4b 0% with same scaffold |
| R31 | The Vocabulary Wall | 10 | Hermes-405B: 25% vocab → 100% bare arithmetic |
| R32 | Active params determine stage | 10,17 | Qwen3.6-35B (3B active) = Stage 2 despite 35B total |
| R33 | Seed-2.0 is Stage 4 | 10 | 100% on all tasks regardless of framing |
| R34 | Stage 4 = training threshold, not size | 10,24 | Hermes-70B (70B) is Stage 3; Seed-2.0 (smaller) is Stage 4 |
| R38 | Echo is general (not math-specific) | 12 | 18-40% echo in summarization tasks |
| R39 | Three tiers of vocabulary interference | 18 | Tier 1 (clean), Tier 2 (partial), Tier 3 (lethal: Eisenstein/Penrose) |
| R40 | Penrose-Eisenstein Dead Zone | 19 | Only 2/20 names kill; all others survive |
| R41 | Pre-computation rescues, rephrasing doesn't | 20 | Stripping vocab fails; only "compute 1/√3" works |
| R42 | Fleet auto-translation achieves 100% | 23 | Hermes-70B: 33%→100%, Qwen3-235B: 17%→100% |
| R46 | Temperature dissolves wall at T≈0.7 | 28 | 0% at T=0, 67% at T=0.7, 0% at T=1.0 |
| R47 | Bidirectional Vocabulary Rerouting | 13 | Vocab poisons arithmetic (100%→0%) but aids logic (20%→100%) |
| R48 | Consensus cannot overcome wall | 21 | Majority vote: 25% vs 46% individual |
| R49 | Variables trigger wall too | 33 | "a=3,b=5, compute a²-ab+b²" → 49 ✗; "9-15+25" → 19 ✓ |
| R52 | Pre-substituted arithmetic immune to ALL labels | 35 | All 8 domain labels → 19 ✓ when numbers pre-computed |
| R56 | Wall is language×model×task interaction | 36 | Japanese helps Hermes (100%), Spanish kills Qwen (0%) |
| R57 | Wall is discrete minefield, not gradient | 40 | Pearson r=+0.33 vs predicted -0.92, specific tokens trigger overrides |
| R58 | First-token commitment conditional on load | 41 | 100% across all prefills when formula given |
| R59 | Substitution Burden WRONG for Hermes-70B | 39 | Bare arithmetic 67% WORSE than Eisenstein 100% |
| R60 | Prospective landmine prediction fails | 42 | 3/12 predictions correct, safe terms worse than predicted landmines |
| R61 | Vocabulary is formula SELECTOR, not toxin | 44 | Formula-no-label 0%, formula+landmine-label 100% |

## SOLID (11 findings — build with caution)

| R# | Finding | Study | Key Evidence |
|----|---------|:-----:|-------------|
| R28 | Math vocabulary triggers echo in thinking models | 9 | qwen3:4b echo_partial rate 80% when scaffolded |
| R29 | Optimal information dose for scaffolding | 9 | phi4-mini: partial(64%) > step-by-step(56%) > scaffolded(40%) |
| R35 | Multi-rep 1.38× tighter covering | 16 | Z[ζ₁₂] 6 pairs vs Eisenstein single pair |
| R36 | All Z[ζ₁₂] pairs contribute | 16 | Win distribution: 13-19% per pair (uniform) |
| R43 | Translation > model selection | 23 | Right framing beats right model |
| R44 | Stage is probabilistic | 24 | Qwen3-235B gets some right, some wrong |
| R45 | 6 probes sufficient for stage classification | 26 | Echo rate converges after 6 probes |
| R50 | Rerouting happens at token 1 | 32 | "W" = discourse, "4" = compute; sealed at first token |
| R51 | Stage 4 uses unified reasoning pathway | 32 | Seed-2.0 always starts "Let/Got..." → correct answer |
| R53 | Few-shot cannot inoculate | 34 | 0-shot/1-shot/3-shot all fail (7, 65, 45) |
| R54 | Euler Effect (over-activation) | 30 | Euler scored 0/3 — too many competing associations |

## SUGGESTIVE (3 findings — interesting but weak)

| R# | Finding | Study | Key Evidence |
|----|---------|:-----:|-------------|
| R30 | Scaffolding is model-architecture dependent | 9 | Opposite prescriptions for same-size models |
| R37 | Permutation consensus too sparse | 16 | Only 2% full consensus across permutations |
| R55 | Wall is format-dependent | 30 | Eisenstein 0% in one format, 100% in another |

| R57 | Wall is discrete minefield, not gradient | 40 | Pearson r=+0.33 vs predicted -0.92. Specific tokens trigger formula overrides. |
| R58 | First-token commitment conditional on load | 41 | 100% across all prefills when formula given. Commitment only under load. |
| R59 | Substitution Burden WRONG for Hermes-70B | 39 | Bare arithmetic 67% WORSE than Eisenstein 100%. Context deprivation penalty. |

## Summary

- **Total findings**: 35 (R27-R61)
- **BEDROCK**: 18 (51%)
- **SOLID**: 11 (31%)
- **SUGGESTIVE**: 3 (9%)
- **FALSIFIED theories**: 3 (substitution burden, gradient hypothesis, CPA-ABD)
- **Studies**: 44 (9-44)
- **Models tested**: 6 local + 8 API = 14
- **Total experimental trials**: ~5,500+
