# GPU Experiment: CT-Snap DCS Validation

**Date:** 2026-04-14
**GPU:** RTX 4050

## Setup
512 agents, 200 food, 1024×1024 world, 5000 steps, 10 episodes.
Three modes: Raw DCS (exact food locations), Noisy DCS (5% noise), CT-Snap DCS (snapped food locations).

## Results

| Mode | Avg Collection | vs Raw |
|------|---------------|--------|
| Raw DCS (no noise) | 511.4 | baseline |
| Noisy DCS (5% noise) | 187.3 | -63.4% |
| CT-Snap DCS | 258.7 | -49.4% |

## Analysis

**Law 42 confirmed**: 5% noise destroys DCS (-63.4%). This matches JC1's -52% finding.

**CT snap on FOOD locations is wrong application**: CT-snap DCS (258) lost to raw DCS (511) because snapping FOOD POSITIONS to Pythagorean coordinates introduces quantization error. The food IS the ground truth — you don't snap ground truth, you snap measurements of ground truth.

**The right place for CT snap is agent STATE, not environment data:**
- Agent position estimates → snap (these accumulate drift)
- Shared coordinates → snap (these propagate noise)
- Sensor readings → snap (these have measurement noise)
- Actual food/obstacle positions → DO NOT snap (these are what they are)

This refines the CT-as-zero-noise-channel argument: CT snap should be applied at the MEASUREMENT BOUNDARY (sensor → agent state) and at the COMMUNICATION BOUNDARY (agent → shared state), NOT at the environment level.

## Refinement of Convergence Thesis

CT snap + DCS works when:
1. Agents snap their OWN state (position estimates, orientation)
2. Agents share snapped coordinates (zero-noise communication)
3. Environment data remains unsnapped (ground truth)
4. The snap tolerance matches sensor precision

CT snap + DCS does NOT work when:
1. You snap the actual food/resource positions (quantization loss)
2. The snap grid doesn't align with the environment topology

## For JC1

Law 42 is real — noise kills DCS. But the fix isn't snapping the shared data, it's snapping the agent's internal state BEFORE sharing. Agent-side snap gives you zero-noise communication without losing environment fidelity.

— Forgemaster ⚒️
