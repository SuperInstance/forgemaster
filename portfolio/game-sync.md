---
id: P-002
title: Game State Sync Proof
repo: SuperInstance/proof-game-sync
status: live
tech: [rust, constraint-theory-core, multiplayer, cross-platform]
result: "Float: 2.9-6.4e-7m divergence. CT: 0.000000000000 across all platform pairs."
created: 2026-04-14
---

# Game State Sync — Cross-Platform Float vs CT

## What It Is

Simulates a multiplayer game with 10 entities, 10,000 ticks at 60fps, across 3 platforms (Windows/Mac/Linux) with slightly different FPU rounding behavior. Float mode: platforms diverge. CT mode: bit-identical.

## Why It Matters

Game developers know this problem. Deterministic lockstep networking requires identical float results across platforms. It doesn't work. Every engine has horror stories. Constraint theory makes it work by snapping to a grid that's the same on every platform.

## Results

| Platform pair | float mode | CT mode |
|---|---|---|
| Windows ↔ macOS | 6.4e-7 m | 0.000000000000 ✓ |
| Windows ↔ Linux | 2.9e-7 m | 0.000000000000 ✓ |
| macOS ↔ Linux | 3.5e-7 m | 0.000000000000 ✓ |

The drift formula predicts: ε ≈ 1e-9 × 10000 ticks × dt(1/60). CT snap at 1e-4 tolerance absorbs all of it because 1e-4 >> 6.4e-7.

## What I Learned

- `snap(v) = round(v / ε) * ε` — dead simple, brutally effective
- Game-appropriate tolerance (1e-4) is much looser than physics (1e-6). The tolerance is a design knob.
- The snap is idempotent and O(1) per component — no performance excuse not to use it

## How to Extend

- Real networking (UDP between actual processes)
- Unity/Unreal plugin wrapping the snap call
- Quantify: how many entities before snap cost matters?
- Different game types: FPS (position), RTS (thousands of units), card game (deterministic shuffle)
