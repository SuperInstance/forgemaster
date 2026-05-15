#!/usr/bin/env python3
"""Forgemaster Local PLATO + Hebbian — boots local PLATO and runs Hebbian analysis.

Architecture:
    Local PLATO (:8848) ←→ Hebbian Layer ←→ Sync ←→ Remote PLATO (:8847)
                                      ↕
                              GitHub twin (async I2I)

This is Forgemaster's autonomous cognition loop:
    1. Boot local PLATO from SQLite (14K tiles, 11 rooms)
    2. Run Hebbian analysis on tile flow patterns
    3. Detect emergent room clusters
    4. When connected: sync with Oracle1's remote PLATO
    5. When disconnected: keep working locally, sync later via git
"""

import sys
import os
import time
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bin'))

from local_plato import LocalPlatoStore

def boot_local_plato():
    """Boot local PLATO and return the store."""
    db_path = os.path.join(os.path.dirname(__file__), "plato.db")
    store = LocalPlatoStore(db_path)
    result = store.boot()
    print(f"⚒️  Local PLATO booted: {result['rooms']} rooms, {result['tiles']} tiles")
    return store


def analyze_tile_flow(store):
    """Analyze tile flow patterns across rooms."""
    from conservation_hebbian import ConservationHebbianKernel, coupling_entropy, algebraic_normalized

    rooms = list(store.rooms.keys())
    n_rooms = len(rooms)
    room_index = {name: i for i, name in enumerate(rooms)}

    print(f"\n📊 Analyzing tile flow across {n_rooms} rooms...")

    # Build a coupling matrix from shared sources/tags between rooms
    coupling = np.zeros((n_rooms, n_rooms), dtype=np.float32)

    for i, name_a in enumerate(rooms):
        room_a = store.rooms[name_a]
        sources_a = set(room_a.key_sources)
        tags_a = set(room_a.tags.keys())

        for j, name_b in enumerate(rooms):
            if i == j:
                continue
            room_b = store.rooms[name_b]
            sources_b = set(room_b.key_sources)
            tags_b = set(room_b.tags.keys())

            # Jaccard similarity of sources + tags
            source_sim = len(sources_a & sources_b) / max(len(sources_a | sources_b), 1)
            tag_sim = len(tags_a & tags_b) / max(len(tags_a | tags_b), 1)
            coupling[i, j] = 0.6 * source_sim + 0.4 * tag_sim

    # Diagonal = self-connection (max)
    np.fill_diagonal(coupling, 1.0)

    # Analyze
    gamma = algebraic_normalized(coupling)
    H = coupling_entropy(coupling)

    print(f"  γ (algebraic connectivity): {gamma:.4f}")
    print(f"  H (spectral entropy):       {H:.4f}")
    print(f"  γ + H =                     {gamma + H:.4f}")
    print(f"  Predicted (V={n_rooms}):    {1.283 - 0.159 * np.log(n_rooms):.4f}")

    # Top connections
    print(f"\n  Top inter-room connections:")
    for i in range(n_rooms):
        for j in range(i + 1, n_rooms):
            if coupling[i, j] > 0.3:
                print(f"    {rooms[i]:30s} ↔ {rooms[j]:30s}  strength={coupling[i,j]:.3f}")

    # Run Hebbian simulation on this coupling structure
    kernel = ConservationHebbianKernel(n_rooms=n_rooms, V=min(n_rooms, 30))

    # Seed with observed coupling
    kernel.set_weights(coupling.astype(np.float32))

    # Simulate 1000 tile flows weighted by coupling
    rng = np.random.RandomState(42)
    for step in range(1000):
        pre = np.zeros(n_rooms, dtype=np.float32)
        post = np.zeros(n_rooms, dtype=np.float32)

        # Pick source proportional to tile count
        tile_counts = np.array([store.rooms[r].tile_count for r in rooms], dtype=np.float32)
        probs = tile_counts / tile_counts.sum()

        src = rng.choice(n_rooms, p=probs)
        # Destination biased by coupling
        dest_probs = coupling[src] + 0.01
        dest_probs /= dest_probs.sum()
        dst = rng.choice(n_rooms, p=dest_probs)

        pre[src] = 1.0
        post[dst] = 0.5 + 0.5 * rng.random()

        kernel.update(pre, post)

    # Show results
    report = kernel.conservation_report()
    print(f"\n  Hebbian simulation (1000 steps):")
    print(f"    Compliance rate: {kernel.compliance_rate():.1%}")
    print(f"    Calibrated target: {kernel._warmup_target:.4f}")
    print(f"    Corrections: {kernel._correction_count}")

    return kernel, rooms, coupling


def show_clusters(store, kernel, rooms):
    """Show emergent room clusters."""
    print(f"\n🔗 Room Cluster Analysis:")

    w = kernel.get_weights()

    # Find strongest pairs
    pairs = []
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            strength = max(w[i, j], w[j, i])
            pairs.append((rooms[i], rooms[j], float(strength)))

    pairs.sort(key=lambda x: -x[2])
    print(f"  Top 10 strongest connections:")
    for src, dst, s in pairs[:10]:
        print(f"    {src:30s} → {dst:30s}  w={s:.4f}")

    # Simple clustering: group rooms with mutual strong connections
    threshold = 0.01
    clusters = []
    assigned = set()

    for src, dst, s in pairs:
        if s < threshold:
            break
        if src in assigned and dst in assigned:
            continue

        # Find or create cluster
        found = None
        for cluster in clusters:
            if src in cluster or dst in cluster:
                found = cluster
                break

        if found is not None:
            found.add(src)
            found.add(dst)
        else:
            clusters.append({src, dst})
        assigned.add(src)
        assigned.add(dst)

    print(f"\n  Detected {len(clusters)} clusters:")
    for i, cluster in enumerate(clusters):
        print(f"    Cluster {i+1}: {', '.join(sorted(cluster)[:5])}")


def write_state_tile(store, kernel, rooms):
    """Write a state tile to local PLATO documenting the Hebbian analysis."""
    report = kernel.conservation_report()
    state = {
        "gamma": round(report.gamma, 4),
        "H": round(report.H, 4),
        "gamma_plus_H": round(report.gamma_plus_H, 4),
        "predicted": round(report.predicted, 4),
        "conserved": report.conserved,
        "update_count": report.update_count,
        "compliance_rate": f"{kernel.compliance_rate():.1%}",
        "rooms_analyzed": len(rooms),
        "calibrated_target": round(kernel._warmup_target, 4) if kernel._auto_calibrated else None,
    }

    from local_plato import Tile
    tile = Tile(
        tile_id=f"hebbian-state-{int(time.time())}",
        room="forgemaster-local",
        domain="forgemaster-local",
        question="hebbian-rooms-analysis",
        answer=json.dumps(state),
        source="forgemaster-hebbian",
        tags=["hebbian", "conservation", "room-analysis", "auto"],
        confidence=0.9,
        timestamp=time.time(),
    )
    store.write_tile(tile)
    print(f"\n✅ State tile written to forgemaster-local: {json.dumps(state, indent=2)}")


if __name__ == "__main__":
    print("⚒️  Forgemaster Local PLATO + Hebbian Analysis\n")
    print("=" * 60)

    store = boot_local_plato()
    kernel, rooms, coupling = analyze_tile_flow(store)
    show_clusters(store, kernel, rooms)
    write_state_tile(store, kernel, rooms)

    print("\n" + "=" * 60)
    print("⚒️  Analysis complete. Local PLATO has Hebbian state.")
    print("   Run local_plato_server.py to serve at :8848")
    print("   Run with --sync to pull latest from Oracle1's :8847")
