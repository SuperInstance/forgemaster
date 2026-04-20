# Fleet Trust Patterns

## What This Skill Is
Design patterns for trust-based decision making across the fleet. Trust drives: deployment tiers, lock enforcement, message routing, and agent selection. Understanding these patterns prevents drift and maintains coherence.

## When to Use It
- Designing new trust-aware systems
- Refactoring existing trust models
- Debugging trust-related issues (agents blocked, tiles ignored)
- Integrating new agents into fleet with existing trust

## How It Works

### Trust Sources

| Source | Use Case | Example |
|---------|-----------|----------|
| **Peer reputation** | Agent-to-agent communication | JC1's flux-trust |
| **Evidence-based** | Track record of successes/failures | plato-trust-beacon events |
| **Constraint-based** | Rules from safety audits | plato-lab-guard gating |
| **Consensus** | Multiple agents agree | Multi-agent DCS voting |

### Core Patterns

#### Pattern 1: Bayesian Fusion
Combine evidence from multiple sources into a single trust score.

```
trust = (w1 * score1 + w2 * score2 + ... + wn * scoren) / sum(weights)
```

**Fleet implementations:**
- `plato-unified-belief` — 3D fusion (confidence × trust × relevance)
- `flux-trust` (JC1) — Weighted average with decay

**When to use:**
- Multiple agents rate same tile/agent
- You have different evidence types (successes, timeouts, corruptions)
- You need to combine them into a single decision

#### Pattern 2: Decay Over Time
Trust decreases if not reinforced. Prevents old trust from dominating.

```
trust(t) = trust(t-1) * (1 - decay_rate)
```

**Fleet implementations:**
- `plato-trust-beacon` — Exponential decay e^(-λt)
- `flux-trust` (JC1) — Linear decay 0.01 per tick

**When to use:**
- Trust scores become stale
- Agents go offline or stop contributing
- You need to auto-reduce trust after inactivity

#### Pattern 3: Threshold-Based Decisioning
Convert continuous trust score into discrete action (execute/block/monitor).

```
if trust >= live_threshold: execute
elif trust >= monitored_threshold: execute + log
else: block
```

**Fleet implementations:**
- `plato-deploy-policy` — 3-tier (Live/Monitored/HumanGated)
- `flux-trust` (JC1) — 5 levels (Unknown/Suspicious/Neutral/Trusted/Verified)

**When to use:**
- Deployment decisions (DCS flywheel)
- Message routing (reject from untrusted sources)
- Command execution (dangerous operations need high trust)

#### Pattern 4: Lock Accumulation
Failed operations accumulate constraints that prevent repetition.

```
if operation fails:
    if not already_locked:
        add_lock(trigger_pattern, enforcement, strength)
```

**Fleet implementations:**
- `plato-dynamic-locks` — LockRegistry with LockSource (Observation/Inconsistency/Expert/etc.)
- `flux-trust` (JC1) — TrustTable.set/get/update/decay

**When to use:**
- Safety failures (deletions, destructive operations)
- Recurring errors (API timeouts, data corruption)
- Need to prevent loops (same bad command repeated)

#### Pattern 5: Consensus-Based Promotion
Multiple agents agree before promoting from monitored → live.

```
if consensus > threshold && duration > min_deploy_time:
    promote_to_live()
```

**Fleet implementations:**
- `plato-deploy-policy` — rollout_pct (5% → 10% → 100%)
- `flux-trust` (JC1) — Multiple sources verify before promotion

**When to use:**
- Gradual rollout to production
- Multiple agents need to verify safety
- Need to detect failure before 100% rollout

### Implementation Guidelines

#### Error Handling
- Trust scores should be clamped [0.0, 1.0]
- Decay should not go negative (min 0.0)
- Missing trust = default (0.5 or Unknown)

#### Testing
- Test decay (score goes down over time)
- Test reinforcement (score goes up with positive events)
- Test threshold crossing (behavior changes at boundary)
- Test consensus (multiple agents agree)

#### Documentation
- Document decay rate formula
- Document threshold values with reasoning
- Explain what "blocked" means in your context

## Fleet Implementations

| Crate | Pattern | Notes |
|-------|----------|--------|
| plato-unified-belief | Bayesian Fusion | 3D: confidence × trust × relevance |
| plato-trust-beacon | Decay + Threshold | Exponential e^(-λt), Beacon events |
| flux-trust (JC1) | Weighted Average + Linear Decay | Consensus from multiple sources |
| plato-dynamic-locks | Lock Accumulation | LockSource (Observation/Inconsistency/Expert/etc.) |
| plato-deploy-policy | Threshold + Consensus | 3-tier rollout, DeployLedger |

## Examples

**Trust-based routing (plato-i2i):**
- Query finds 5 peers
- Filter out negative trust (avoid_negative)
- Select best_peer by routing_score (trust × decay × success_rate)

**DCS flywheel (plato-kernel):**
- Belief score → Deploy tier (Live/Monitored/HumanGated)
- If human-gated, block execution
- After success, reinforce belief; after fail, undermine

**Hypothesis gating (plato-lab-guard):**
- Check for absolute quantifiers ("always", "never")
- Gate on mechanism (proportional claims need "because" or numbers)
- Reject unfalsifiable claims

## Related Skills
- `fleet-audit-checklist` — Security patterns to check
- `fleet-crate-standard` — Testing patterns for trust systems
- `fleet-bottle-protocol` — Coordinating trust changes across agents
