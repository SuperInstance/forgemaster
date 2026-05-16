# Seed-Mini Fleet Workhorse Protocol

## Why Seed-2.0-mini is the Fleet Workhorse

| Property | Value |
|----------|-------|
| Math accuracy | ~100% (Tier 1) |
| Cost | ~$0.01/query (DeepInfra) |
| Latency | ~2-5s typical |
| Parallel capacity | 50+ concurrent calls before rate limits |
| Domain | Math, code, general reasoning |
| API | OpenAI-compatible (DeepInfra) |

## Use Cases

### 1. PLATO Room Parallel Simulation
Fan out computations across rooms, collect results, aggregate.
```python
# 50 rooms × 1 query each = $0.50 for full fleet simulation
results = await gather(*[seed_mini_query(room.task) for room in rooms])
```

### 2. Spreader Tool (Fan-Out Compute)
Distribute a computation across N parallel calls, merge results.
- Monte Carlo sampling: 100 samples in parallel
- Parameter sweeps: N configurations simultaneously  
- Ensemble predictions: K models, majority vote

### 3. Murmur (Lightweight Consensus)
Quick quorum check — ask 5+ Seed-mini instances, verify agreement.
- Fault detection probes
- Conservation compliance checks  
- GL(9) alignment verification

### 4. Rapid Iteration
Cache-optimized loop: tweak prompt, run, check, repeat at $0.01/cycle.
- Prompt engineering
- Test case generation
- Counter-example search

## Routing Rule

```
IF math_domain AND parallel_fan_out:
    → Seed-2.0-mini (workhorse)
ELIF math_domain AND single_query:
    → Seed-2.0-mini (default Tier 1)
ELIF code_domain:
    → Seed-2.0-mini or local model
ELIF content_domain:
    → glm-5-turbo (z.ai, paid plan)
ELSE:
    → fleet router decides
```

## Cost Math

| Operation | Calls | Cost |
|-----------|-------|------|
| Single query | 1 | $0.01 |
| Room simulation (50 rooms) | 50 | $0.50 |
| Monte Carlo (100 samples) | 100 | $1.00 |
| Full fleet sweep (200 calls) | 200 | $2.00 |
| Daily heavy use (1000 calls) | 1000 | $10.00 |

Compare: 1000 GPT-4 calls = ~$30-60. Seed-mini = $10.

## Implementation

- Model ID: `ByteDance/Seed-2.0-mini`
- Endpoint: `https://api.deepinfra.com/v1/openai/chat/completions`
- Key: `~/.openclaw/workspace/.credentials/deepinfra-api-key.txt`
- Max concurrent: 10-20 (DeepInfra rate limit), batch with backoff for 50+
