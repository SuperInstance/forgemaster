#!/usr/bin/env python3
"""
PLATO Room Integrity Monitor — Demo
=====================================
Simulates 5 PLATO rooms exchanging tiles for 100 steps.
Demonstrates:
  - Integrity tracking (I = γ + H over time)
  - Chop detection (transitional regime)
  - Health reports
  - Conservation law verification (CV < threshold)

Forgemaster ⚒️ | 2026-05-17
"""

import sys
import os
import numpy as np

# Add impl dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plato_room_integrity import (
    Tile, RoomState, IntegrityTracker, RoomHealth,
    room_coupling_matrix, fleet_coupling_matrix,
    compute_integrity, step_room, exchange_tiles,
    detect_chop, detect_swell, detect_dead,
    health_report, fleet_health_report,
)


def create_room(room_id: str, n_tiles: int = 6, dim: int = 8,
                coupling_method: str = 'attention', tau: float = 1.0) -> RoomState:
    """Create a PLATO room with random tile embeddings."""
    tiles = []
    for i in range(n_tiles):
        vec = np.random.randn(dim) * 0.5
        tiles.append(Tile(
            tile_id=f"{room_id}-tile-{i}",
            content_vector=vec,
            source_room=room_id,
            strength=np.random.uniform(0.5, 1.5),
        ))

    C = room_coupling_matrix(tiles, method=coupling_method, tau=tau)
    state = np.array([t.content_vector for t in tiles]).mean(axis=0)

    return RoomState(
        room_id=room_id,
        tiles=tiles,
        coupling_matrix=C,
        state_vector=state,
    )


def main():
    np.random.seed(42)

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  PLATO ROOM INTEGRITY MONITOR — SPECTRAL FIRST INTEGRAL    ║")
    print("║  Jazz Theorem Demo: I = γ + H is conserved across rooms    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # ---- Configuration ----
    N_ROOMS = 5
    N = 8               # state dimension per room
    TRANSIENT = 30       # transient steps to discard
    N_STEPS = 200        # total steps
    ACTIVATION = 'tanh'

    room_names = ['drift-detect', 'anomaly-flag', 'intent-classify', 
                  'spline-compress', 'deploy-pipeline']

    print(f"  Fleet: {N_ROOMS} rooms, dim={N}")
    print(f"  State-dependent coupling: C(x) = softmax(x·x^T/τ) + α·I")
    print(f"  Transient: {TRANSIENT} steps, Measurement: {N_STEPS} steps")
    print(f"  Running simulation...")
    print()

    # ---- Create rooms ----
    # Each room has a different τ controlling its spectral focus
    room_taus = {'drift-detect': 0.5, 'anomaly-flag': 1.0, 'intent-classify': 2.0,
                 'spline-compress': 5.0, 'deploy-pipeline': 10.0}
    room_alphas = {'drift-detect': 0.2, 'anomaly-flag': 0.1, 'intent-classify': 0.15,
                   'spline-compress': 0.05, 'deploy-pipeline': 0.3}

    rooms = []
    for name in room_names:
        # Start with larger state to avoid immediate collapse
        x = np.random.randn(N) * 1.5
        n_tiles = N
        tiles = [Tile(f"{name}-t{i}", np.random.randn(N) * 0.5, source_room=name,
                      strength=np.random.uniform(0.5, 1.5)) for i in range(n_tiles)]
        # Initial coupling
        tau = room_taus[name]
        C = np.outer(x, x) / tau
        C = np.exp(C - np.max(C, axis=1, keepdims=True))
        C = C / np.sum(C, axis=1, keepdims=True)
        C = (C + C.T) / 2 + room_alphas[name] * np.eye(N)
        rooms.append(RoomState(room_id=name, tiles=tiles, coupling_matrix=C, state_vector=x))

    # ---- Trackers ----
    trackers = {name: IntegrityTracker(room_id=name) for name in room_names}

    # ---- Initial integrity ----
    print("  INITIAL STATE:")
    for room in rooms:
        snap = compute_integrity(room, activation=ACTIVATION)
        snap.step = 0
        trackers[room.room_id].record(snap)
        print(f"    {room.room_id:20s}  I={snap.integrity:.4f}  "
              f"γ={snap.gamma:.4f}  H={snap.entropy:.4f}  "
              f"||[D,C]||={snap.commutator_norm:.4f}")

    # ---- Run simulation ----
    # Each room has its own τ and α controlling spectral structure.
    # The Jazz Theorem: I = γ + H is conserved when ||[D,C]|| is small.
    # State-dependent coupling C(x) = softmax(x·x^T/τ) + α·I
    for step in range(1, N_STEPS + 1):
        new_rooms = []
        for room in rooms:
            x = room.state_vector.copy()
            tau = room_taus[room.room_id]
            alpha = room_alphas[room.room_id]

            # State-dependent attention coupling
            C = np.outer(x, x) / tau
            C_stable = C - np.max(C, axis=1, keepdims=True)
            C_exp = np.exp(C_stable)
            C = C_exp / np.sum(C_exp, axis=1, keepdims=True)
            C = (C + C.T) / 2 + alpha * np.eye(N)

            # State evolution with bias to prevent collapse
            # x_{t+1} = tanh(C(x_t) x_t + b) where b prevents zero attractor
            bias = 0.3 * np.sign(x)  # mild bias toward current sign pattern
            x_new = np.tanh(C @ x + bias) + 0.01 * np.random.randn(N)

            # Update tiles
            new_tiles = []
            for i, tile in enumerate(room.tiles):
                v = tile.content_vector.copy()
                v = 0.9 * v + 0.1 * x_new
                new_tiles.append(Tile(tile.tile_id, v, tile.source_room,
                                     tile.target_room, tile.strength))

            new_rooms.append(RoomState(room.room_id, new_tiles, C, x_new))

        # Exchange tiles every 10 steps
        if step % 10 == 0:
            new_rooms = exchange_tiles(new_rooms, exchange_rate=0.05)

        rooms = new_rooms

        # Compute integrity with state-dependent coupling
        for room in rooms:
            x = room.state_vector
            tau = room_taus[room.room_id]
            alpha = room_alphas[room.room_id]
            C = np.outer(x, x) / tau
            C_stable = C - np.max(C, axis=1, keepdims=True)
            C_exp = np.exp(C_stable)
            C = C_exp / np.sum(C_exp, axis=1, keepdims=True)
            C = (C + C.T) / 2 + alpha * np.eye(N)
            room.coupling_matrix = C

            snap = compute_integrity(room, activation=ACTIVATION)
            snap.step = step
            trackers[room.room_id].record(snap)

        # Progress
        if step in (TRANSIENT, N_STEPS // 2, N_STEPS):
            print(f"\n  Step {step}/{N_STEPS}:")
            for name, tracker in trackers.items():
                latest = tracker.latest()
                print(f"    {name:20s}  I={latest.integrity:.4f}  "
                      f"γ={latest.gamma:.3f}  H={latest.entropy:.3f}  "
                      f"||[D,C]||={latest.commutator_norm:.4f}")

    # ---- Final results ----
    print("\n")
    print("=" * 70)
    print("  SIMULATION COMPLETE")
    print("=" * 70)

    # ---- Conservation verification (KEY RESULT) ----
    print()
    print("=" * 70)
    print("  CONSERVATION LAW VERIFICATION (Jazz Theorem)")
    print("=" * 70)
    print()
    print("  Theory: I = γ + H is a spectral first integral (Koopman λ ≈ 1)")
    print("  Full trajectory CV includes transient — we report both:")
    print()

    print(f"  {'Room':20s}  {'CV(full)':>10s}  {'CV(steady)':>10s}  "
          f"{'mean I':>8s}  {'std I':>8s}  {'drift':>8s}")
    print("  " + "-" * 70)

    all_steady_cvs = []
    for name, tracker in trackers.items():
        # Full CV
        full_cv = tracker.cv

        # Steady-state CV (after transient)
        steady_snaps = [s for s in tracker.history if s.step >= TRANSIENT]
        if len(steady_snaps) >= 2:
            vals = np.array([s.integrity for s in steady_snaps])
            steady_cv = float(np.std(vals) / np.abs(np.mean(vals))) if np.mean(vals) != 0 else float('inf')
        else:
            steady_cv = full_cv

        all_steady_cvs.append(steady_cv)
        status = "✅" if steady_cv < 0.04 else "🌊"
        print(f"  {status} {name:18s}  {full_cv:10.6f}  {steady_cv:10.6f}  "
              f"{tracker.mean_integrity:8.4f}  {np.std(tracker.integrity_values):8.4f}  "
              f"{tracker.integrity_drift:+8.5f}")

    mean_steady = np.mean(all_steady_cvs)
    print()
    print(f"  Fleet mean CV (steady-state): {mean_steady:.6f}")
    print()

    if mean_steady < 0.04:
        print("  ✨ RESULT: Conservation law HOLDS (steady-state CV < 0.04)")
        print("     The spectral first integral I = γ + H is conserved.")
        print("     Koopman eigenvalue λ ≈ 1 (dynamical regime).")
    elif mean_steady < 0.10:
        print("  ✨ RESULT: Conservation is MODERATE (steady-state CV < 0.10)")
        print("     I varies but much less than state variables.")
        print("     Consistent with approximate Koopman eigenfunction.")
    else:
        print("  🌊 RESULT: High variation (transitional regime)")
        print("     Coupling may need higher τ or different architecture.")

    # ---- Health reports (compact) ----
    print()
    print("=" * 70)
    print("  ROOM HEALTH REPORTS")
    print("=" * 70)
    for name in room_names:
        print()
        print(health_report(trackers[name]))

    # Fleet summary
    print()
    print(fleet_health_report(trackers))

    # ---- Regime classification ----
    print()
    print("=" * 70)
    print("  REGIME CLASSIFICATION SUMMARY")
    print("=" * 70)
    print()

    for name, tracker in trackers.items():
        is_dead = detect_dead(tracker)
        is_chop = detect_chop(tracker)
        is_swell = detect_swell(tracker)

        if is_dead:
            regime = "💀 DEAD (rank-1 collapse)"
        elif is_chop:
            regime = "🌊 CHOP (transitional — knowledge degrading)"
        elif is_swell:
            regime = "✨ SWELL (dynamical — knowledge healthy)"
        else:
            regime = "❓ MIXED"

        print(f"    {name:20s}  {regime}")

    # ---- Time series (compact) ----
    print()
    print("=" * 70)
    print("  INTEGRITY TIME SERIES (sampled, steps ≥ {} = steady-state)".format(TRANSIENT))
    print("=" * 70)
    print()
    header = f"  {'Step':>6s}"
    for name in room_names:
        header += f"  {name[:12]:>12s}"
    print(header)
    print("  " + "-" * (6 + 14 * N_ROOMS))

    sample_steps = list(range(0, N_STEPS + 1, max(1, N_STEPS // 20)))
    for step_idx in sample_steps:
        row = f"  {step_idx:6d}"
        marker = "  →" if step_idx == TRANSIENT else "    "
        for name in room_names:
            if step_idx < len(trackers[name].history):
                val = trackers[name].history[step_idx].integrity
                row += f"  {val:12.4f}"
            else:
                row += f"  {'---':>12s}"
        if step_idx == TRANSIENT:
            row += "  ← transient ends"
        print(row)

    print()
    print("  [End of PLATO Room Integrity Demo]")
    print("  Forgemaster ⚒️ | 2026-05-17")
    print("  'The shape of the sound is the fossil record of the attractor.'")


if __name__ == '__main__':
    main()
