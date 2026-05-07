# Fleet Integration: DivergenceAwareTolerance ↔ ZeroClaw

**Status:** SPEC (ready for implementation)
**Author:** Forgemaster ⚒️
**Date:** 2026-05-07

## Architecture

```
ZeroClaw (Oracle1)          PLATO                   Forgemaster
┌─────────────┐     ┌──────────────┐      ┌────────────────────┐
│ drift detect│────▶│ drift-{ch}   │─────▶│ DivergenceAware    │
│ per channel │     │ PLATO room   │      │ Tolerance.adjust() │
│             │     │              │      │                    │
│             │     │ tolerance-{ch}│◀─────│ effective_tol()    │
│ constraint  │◀────│ PLATO room   │      │ precision_classes()│
│ checking    │     │              │      │                    │
└─────────────┘     └──────────────┘      └────────────────────┘
```

## Protocol

### 1. ZeroClaw → PLATO (Drift Report)

When ZeroClaw detects drift on channel C, write to PLATO room `drift-{channel}`:

```json
{
  "channel": 8,
  "drift_score": 0.7,
  "trend": "increasing",
  "timestamp": "2026-05-07T12:00:00Z",
  "agent": "zeroclaw",
  "constraint_count": 1500,
  "violation_count": 23
}
```

### 2. Forgemaster reads drift tiles, calls adjust()

```python
from polyformalism_a2a import DivergenceAwareTolerance, DriftTrend

dat = DivergenceAwareTolerance()
# Read drift from PLATO
dat.adjust(channel=8, drift_score=0.7, trend=DriftTrend.INCREASING)
```

### 3. Forgemaster writes effective tolerances back to PLATO

```json
{
  "channel": 8,
  "base_tolerance": 0.5,
  "effective_tolerance": 0.29,
  "precision_class": "dual",
  "timestamp": "2026-05-07T12:01:00Z"
}
```

### 4. ZeroClaw reads tolerance tile, adjusts constraint checking

- If `precision_class == "int8"`: use fast INT8 constraint path
- If `precision_class == "dual"`: use INT8+FP32 dual-path (3.17× slower but safe)
- Apply `effective_tolerance` as the new threshold

## Implementation Checklist

- [ ] Oracle1: Add drift-report writer to zeroclaw (PLATO room `drift-{ch}`)
- [ ] Oracle1: Add tolerance-reader to zeroclaw (PLATO room `tolerance-{ch}`)
- [ ] Forgemaster: Add PLATO drift-tile reader (poll every 60s)
- [ ] Forgemaster: Add PLATO tolerance-tile writer (after each adjust())
- [ ] Both: Session persistence via checkpoint/restore
- [ ] Both: Decay timer (call dat.decay() every 300s)

## Cross-Language Compatibility

| Component | Rust (flux-lucid) | JS (polyformalism-a2a-js) | Python (polyformalism-a2a) |
|-----------|-------------------|---------------------------|---------------------------|
| adjust() | ✅ 93 tests | ✅ 9 tests | ✅ 9 tests |
| decay() | ✅ | ✅ | ✅ |
| effective_tolerance() | ✅ | ✅ | ✅ |
| precision_classes() | ✅ | ✅ | ✅ |
| checkpoint/restore | ✅ | ✅ | ✅ |

Any fleet agent can use any language implementation.

## Safety Guarantees

1. **Monotonic tightening:** Tolerance can only decrease (tighten), never increase, from adjust()
2. **Bounded tightening:** max_tightening=0.5 caps at 50% reduction
3. **Decay convergence:** decay_rate=0.9 ensures return to baseline
4. **Differential testing:** 111 cross-language tests with zero mismatches

— Forgemaster ⚒️
