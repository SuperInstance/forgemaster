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
    TAU = 5.0            # higher τ → gentler coupling → better conservation
    ACTIVATION = 'tanh'

    room_names = ['drift-detect', 'anomaly-flag', 'intent-classify', 
                  'spline-compress', 'deploy-pipeline']

    print(f"  Fleet: {N_ROOMS} rooms, dim={N}, coupling=attention (τ={TAU})")
    print(f"  Transient: {TRANSIENT} steps, Measurement: {N_STEPS} steps")
    print(f"  Running simulation...")
    print()

    # ---- Create rooms with state-dependent coupling ----
    rooms = []
    for name in room_names:
        # Random initial state
        x = np.random.randn(N) * 0.5
        # Tile embeddings dimension must match state
        n_tiles = N  # same as state dim for clean NxN coupling
        tiles = [Tile(f"{name}-t{i}", np.random.randn(N) * 0.3, source_room=name,
                      strength=np.random.uniform(0.5, 1.5)) for i in range(n_tiles)]
        C = room_coupling_matrix(tiles, method='attention', tau=TAU)
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
    # State-dependent coupling: C(x) is rebuilt each step from the tile
    # embeddings which evolve with the room state.
    # The Jazz Theorem says I should stabilize after transient.
    for step in range(1, N_STEPS + 1):
        # Exchange tiles between rooms every 10 steps
        if step % 10 == 0:
            rooms = exchange_tiles(rooms, exchange_rate=0.05)

        new_rooms = []
        for room in rooms:
            # Rebuild coupling from current tiles
            C = room_coupling_matrix(room.tiles, method='attention', tau=TAU)
            room.coupling_matrix = C

            # State evolution: x_{t+1} = tanh(C x_t) + noise
            x = room.state_vector
            N_room = len(x)
            if C.shape[0] != N_room or C.shape[1] != N_room:
                Cn = np.eye(N_room)
                md = min(C.shape[0], N_room, C.shape[1])
                Cn[:md, :md] = C[:md, :md]
                C = Cn

            x_new = np.tanh(C @ x) + 0.01 * np.random.randn(N_room)

            # Tiles evolve: each tile drifts slightly (knowledge accumulation)
            new_tiles = []
            for tile in room.tiles:
                v = tile.content_vector.copy()
                v += 0.03 * np.random.randn(len(v))  # small independent drift
                new_tiles.append(Tile(tile.tile_id, v, tile.source_room, 
                                     tile.target_room, tile.strength))

            new_rooms.append(RoomState(room.room_id, new_tiles, 
                                       room_coupling_matrix(new_tiles, 'attention', TAU),
                                       x_new))
        rooms = new_rooms

        # Compute integrity
        for room in rooms:
            snap = compute_integrity(room, activation=ACTIVATION)
            snap.step = step
            trackers[room.room_id].record(snap)

        # Progress
        if step in (TRANSIENT, N_STEPS // 2, N_STEPS):
            print(f"\n  Step {step}/{N_STEPS}:")
            for name, tracker in trackers.items():
                latest = tracker.latest()
                print(f"    {name:20s}  I={latest.integrity:.4f}  "
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
