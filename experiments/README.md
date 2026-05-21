# Experiments — Proof Repos for Cocapn Constraint Theory

Each directory is a self-contained, reproducible experiment that tests a specific claim about constraint systems, compilation, or representation. Read the README in each directory for hypothesis, results, and engineering implications.

## Experiments

| # | Experiment | Status | Claim | Key Number |
|---|-----------|--------|-------|------------|
| 1 | [laman-rigidity](laman-rigidity/) | ✅ PROVEN | The 2N−3 edge threshold governs graph rigidity | Threshold sharpens at N≈15 |
| 2 | [constraint-library-validation](constraint-library-validation/) | ✅ PROVEN | 248 real-world constraints validate at 99.6% | 85.1% INT8 deployable |
| 3 | [collect-select-compile](collect-select-compile/) | ✅ PROVEN | All pipelines decompose as COLLECT→SELECT→COMPILE | 141 regime transitions across 5 ecosystems |
| 4 | [pythagorean48-encoding](pythagorean48-encoding/) | ✅ PROVEN | Pythagorean triples give zero-drift direction encoding | Zero drift vs. 1.72e-05 for Float32 |
| 5 | [galois-connection](galois-connection/) | ⚠️ IN PROGRESS | GUARD→FLUX-C compilation is a sound Galois connection | Regex edge case blocks Phase 3 |

### Not Yet Started

| # | Experiment | Planned Claim |
|---|-----------|--------------|
| 6 | holonomy-convergence | Holonomy deviations converge under constraint tightening |
| 7 | eisenstein-quantization | Eisenstein integer lattice provides optimal quantization |
| 8 | deadband-snr | Deadband encoding maximizes SNR for bounded signals |
| 9 | bounded-drift | Drift bounds tighten monotonically under constraint addition |
| 10 | distributed-consensus | Distributed constraint checking converges to centralized result |
| 11 | gpu-loop | GPU-accelerated constraint loops achieve deterministic throughput |

## Summary

**4 of 5 active experiments PROVEN.** One (Galois connection) is 80% complete, blocked on a regex edge case. Six more experiments are planned but not yet implemented.

The core thesis is building: constraint systems have deep mathematical structure (Laman rigidity, Galois connections, phase transitions) that enables provably correct, deployably efficient (INT8), and drift-free (Pythagorean encoding) implementations.

## How to Run Everything

```bash
for dir in laman-rigidity constraint-library-validation collect-select-compile pythagorean48-encoding; do
  echo "=== $dir ==="
  cd experiments/$dir && python3 experiment.py && cd ../..
done
```

All experiments use only Python 3 standard library. No pip installs needed.
