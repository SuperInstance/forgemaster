# The Cocapn Wheel — 6-Step Continuous Development Cycle

```
    6. SCOUT ─────────── 1. BUILD
   (research/novelty)    (implement code)
        │                     │
   5. FORMALIZE           2. EXPERIMENT
   (papers/findings)      (run studies)
        │                     │
   4. NOTICE ─────────── 3. OBSERVE
   (patterns/bugs)        (analyze results)
```

## Step 1: BUILD
Implement code, wire services, fix bugs found in previous cycles.
- Subagent type: implementation
- Input: architecture decisions from Step 5, bugs from Step 4
- Output: working code, new tests, git push

## Step 2: EXPERIMENT
Run studies to validate builds and test hypotheses.
- Subagent type: experimentation
- Input: code from Step 1, hypotheses from Step 5
- Output: study results, raw data, anomalies

## Step 3: OBSERVE
Analyze experiment results. What worked? What didn't? What's unexpected?
- Done by: Forgemaster (main session)
- Input: study results from Step 2
- Output: findings, accuracy scores, effect sizes

## Step 4: NOTICE
Pattern recognition. Connect findings across studies. Find bugs, gaps, contradictions.
- Done by: Forgemaster (main session)
- Input: findings from Step 3, accumulated knowledge
- Output: bugs to fix, patterns to formalize, anomalies to investigate

## Step 5: FORMALIZE
Write up findings. Update papers. Update architecture docs. Make decisions.
- Subagent type: documentation
- Input: patterns from Step 4, decisions to record
- Output: papers, architecture updates, experiment roadmap updates

## Step 6: SCOUT (Research & Novelty)
Before cycling back to build, check what's new in the field.
- Subagent type: research
- Input: current findings, open questions from experiments
- Output:
  - Recent papers/arxiv in relevant domains
  - Novel techniques we should try
  - Competitive landscape (what are others building?)
  - Cross-domain opportunities (can we apply X from field Y?)
  - Novelty assessment (are we doing something new, or reinventing?)
  - Next cycle recommendations

### Scout Domains:
1. **LLM Computation** — How do others handle math/vocabulary issues?
2. **Distributed Agent Systems** — New frameworks, protocols, architectures
3. **Conservation Laws in Networks** — Physics-inspired ML, neural ODEs
4. **Hebbian Learning** — Recent advances in online/continual learning
5. **Fault Detection** — Byzantine fault tolerance, anomaly detection
6. **Constraint Theory** — New work in constraint satisfaction, optimization
7. **Fleet Coordination** — Multi-agent systems, swarm intelligence

### Scout Questions:
- What did we discover that's genuinely novel?
- What's the closest prior art to our findings?
- What techniques from adjacent fields could accelerate our work?
- What are we missing that the field already knows?
- What would make our papers stronger (citations, comparisons, baselines)?

## Cycle Timing
- Steps 1-2: parallel subagents (5-15 min each)
- Steps 3-4: Forgemaster main session (1-2 min each)
- Step 5: subagent or direct (3-5 min)
- Step 6: subagent (5-10 min)
- Full cycle: ~20-30 min
- Multiple cycles can overlap (steps 1-2 of next cycle while 3-6 of current)

## Current State
- Cycle count this session: 6
- Studies completed: 51-63
- Active cycle: 6 (scout step being added)
- Next cycle: 7 (starts with build informed by scouting)
