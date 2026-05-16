# Multi-Model Synthesis Experiment Protocol

## Research Question
Does multi-model rewrite-and-synthesize produce better writing than single-model originals? Is there "first-take magic" lost in synthesis, or does synthesis genuinely improve?

## Method

### Phase 1: Generation (in progress)
- 11 original essays × 10 model voices = 110 versions
- Models: Seed-2.0-mini, Hermes-70B, Qwen3.6-35B, Qwen3-235B, Seed-2.0-code
- Temperatures: 0.3 (conservative), 0.7 (default), 0.9 (creative), 1.2 (experimental)
- Special voices: fisherman, physicist

### Phase 2: Synthesis (3 rounds, different teams)

**Round 1: Team A (Seed + Qwen pair)**
- For each essay: read all 10 versions, synthesize the best single version
- Judge: which ideas from which versions are strongest? Combine them.
- Output: 11 synthesized essays

**Round 2: Team B (Hermes + Seed-code pair)**
- Same process, different model pair
- These models have different strengths: Hermes is scholarly, Seed-code is systems-thinking
- Output: 11 different synthesized essays

**Round 3: Team C (all 4 models vote)**
- For each essay: all 4 models independently rank all 10 versions + both syntheses
- Aggregate rankings via Borda count
- Output: final rankings for each essay

### Phase 3: Blind Comparison

**For each essay, compare:**
1. Original (first-take)
2. Best single version from the 10 (judge's pick)
3. Synthesis Round 1
4. Synthesis Round 2
5. Final synthesis (voted best)

**Judging criteria (each scored 1-10):**
- **Logic holes**: Are there gaps in the argument? (lower = more holes)
- **Voice authenticity**: Does it sound like a real person? (higher = more authentic)
- **Insight depth**: Does it reach non-obvious conclusions? (higher = deeper)
- **Prose quality**: Is the writing tight and earned? (higher = better craft)
- **First-take magic**: Does it have the energy of discovery? (higher = more magic)
- **Technical accuracy**: Are the fleet/architecture mappings correct? (higher = more accurate)

### Hypotheses
- **H1 (Technical)**: Synthesis wins on logic holes and technical accuracy. 10 perspectives catch what one misses.
- **H2 (Creative)**: Original wins on first-take magic and voice authenticity. Committees produce better logic but worse soul.
- **H3 (Insight)**: Best single version from the 10 wins on insight depth. One model can have a breakthrough that synthesis smooths out.
- **H4 (Prose)**: Synthesis wins on prose quality. Combining the best sentences from 10 versions produces better craft.

### Expected Outcome
The answer will be: **it depends on what you're optimizing for.**
- For technical writing: synthesis wins
- For creative writing: original or best-single-version wins
- For mixed (our essays): the synthesis is the best overall but the original or a single version wins on specific dimensions

### Files
- construct-versions/ (50 files)
- bathymetric-versions/ (60 files)
- other-versions/ (remaining)
- synthesis-round-1/ (11 files)
- synthesis-round-2/ (11 files)
- synthesis-final/ (11 files)
- BLIND-COMPARISON-RESULTS.md (the verdict)
