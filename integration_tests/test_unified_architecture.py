"""
Cross-ecosystem integration tests proving the unified architecture works end-to-end.

These tests exercise the five core synergies described in SYNERGY.md:
1. Eisenstein × Deadband = Bounded Drift
2. Laman × Holonomy = Zero-Communication Consensus
3. Metronome Convergence
4. Sunset Inheritance
5. Full Pipeline: PLATO tile → constraint check → holonomy verify
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

import pytest

# ---------------------------------------------------------------------------
# Synergy 1: Eisenstein × Deadband = Bounded Drift
# ---------------------------------------------------------------------------

class TestEisensteinDeadbandBoundedDrift:
    def test_ten_thousand_snaps_zero_anomalies(self):
        """Snap 10 000 random points and prove zero anomalies in steady state."""
        from constraint_theory_core.lattice import snap, covering_radius
        from constraint_theory_core.temporal import TemporalAgent, FunnelPhase

        rng = random.Random(42)
        agent = TemporalAgent(
            decay_rate=0.05,
            epsilon_0=covering_radius(),
            delta=covering_radius(),
        )

        anomalies = 0
        for i in range(1, 10_001):
            x = rng.uniform(-10.0, 10.0)
            y = rng.uniform(-10.0, 10.0)
            result = agent.observe(x, y, t=float(i) * 0.1)

            # When snap error is below the current deadband, no anomaly
            # (and therefore no communication) is needed.
            if result.error < result.deadband:
                assert result.phase != FunnelPhase.ANOMALY

            if result.phase == FunnelPhase.ANOMALY:
                anomalies += 1

        # Covering-radius guarantee: error ≤ ρ for *every* point, and δ = ρ,
        # so anomalies can never occur.
        assert anomalies == 0, f"Expected 0 anomalies, got {anomalies}"
        # Deadband narrows monotonically in steady state.
        assert agent.epsilon < covering_radius() * 0.01


# ---------------------------------------------------------------------------
# Synergy 2: Laman × Holonomy = Zero-Communication Consensus
# ---------------------------------------------------------------------------

class TestLamanHolonomyZeroCommunicationConsensus:
    def test_nine_agent_laman_fault_isolation(self):
        """Build a Laman graph for 9 agents, assign directions to cycles,
        and prove O(log N) fault isolation finds the single bad cycle."""
        from constraint_theory_core.rigidity import henneberg_construct, is_laman
        from constraint_theory_core.holonomy import (
            cycle_holonomy,
            verify_consistency,
            isolate_fault,
        )
        import constraint_theory_core.holonomy as _holonomy

        N = 9
        edges = henneberg_construct(N, seed=42)
        assert is_laman(N, edges)

        edge_set = {tuple(sorted(e)) for e in edges}

        # Extract triangles (3-cycles) from the Laman graph.
        triangles: List[List[Tuple[int, int]]] = []
        for i in range(N):
            for j in range(i + 1, N):
                for k in range(j + 1, N):
                    if (
                        (i, j) in edge_set
                        and (j, k) in edge_set
                        and (i, k) in edge_set
                    ):
                        triangles.append([(i, j), (j, k), (i, k)])

        assert len(triangles) >= 1, "Need at least one cycle to test fault isolation"

        rng = random.Random(99)

        def _consistent_directions(length: int) -> List[int]:
            dirs = [rng.randint(0, 47) for _ in range(length - 1)]
            total = sum(dirs) % 48
            dirs.append((-total) % 48)
            return dirs

        def _inconsistent_directions(length: int) -> List[int]:
            dirs = [rng.randint(0, 47) for _ in range(length)]
            if sum(dirs) % 48 == 0:
                dirs[0] = (dirs[0] + 1) % 48
            return dirs

        # All triangles consistent except one injected fault.
        bad_index = len(triangles) // 2
        tiles: List[Tuple[List[Tuple[int, int]], List[int]]] = []
        for idx, cyc in enumerate(triangles):
            if idx == bad_index:
                dirs = _inconsistent_directions(len(cyc))
            else:
                dirs = _consistent_directions(len(cyc))
            tiles.append((cyc, dirs))

        # Verify exactly one fault exists.
        bad_cycles = [i for i, (e, d) in enumerate(tiles) if cycle_holonomy(e, d) != 0]
        assert bad_cycles == [bad_index]

        # Monkey-patch verify_consistency to count calls and prove O(log N).
        original_verify = _holonomy.verify_consistency
        call_count = 0

        def _counting_verify(t):
            nonlocal call_count
            call_count += 1
            return original_verify(t)

        _holonomy.verify_consistency = _counting_verify
        try:
            found = isolate_fault(tiles)
        finally:
            _holonomy.verify_consistency = original_verify

        assert found == bad_index
        # isolate_fault performs one initial full-list check plus a binary search.
        max_calls = 1 + math.ceil(math.log2(len(tiles)))
        assert call_count <= max_calls, (
            f"Fault isolation used {call_count} checks, "
            f"expected ≤ {max_calls} for O(log N)"
        )


# ---------------------------------------------------------------------------
# Synergy 3: Metronome Convergence
# ---------------------------------------------------------------------------

class TestMetronomeConvergence:
    def test_nine_agents_converge_within_delta(self):
        """Create 9 Metronome agents on a Laman topology,
        run 500 ticks with correction, and prove convergence within δ."""
        from constraint_theory_core.metronome import Metronome
        from constraint_theory_core.rigidity import henneberg_construct

        N = 9
        edges = henneberg_construct(N, seed=123)
        adj: dict[int, List[int]] = {i: [] for i in range(N)}
        for u, v in edges:
            adj[u].append(v)
            adj[v].append(u)

        rng = random.Random(456)
        delta = 0.1
        epsilon = 0.1
        agents: List[Metronome] = []
        for i in range(N):
            phi0 = rng.uniform(0.0, 2.0 * math.pi)
            m = Metronome(
                T=1.0,
                phi0=phi0,
                epsilon=epsilon,
                delta=delta,
                neighbors=adj[i],
                edges=edges,
                n_agents=N,
            )
            agents.append(m)

        for _ in range(500):
            for a in agents:
                a.tick()
            phases = [a.phase for a in agents]
            for a in agents:
                nbr_phases = [phases[j] for j in a.neighbors]
                a.correct(nbr_phases)

        # Measure maximum pairwise circular distance.
        max_diff = 0.0
        for i in range(N):
            for j in range(i + 1, N):
                diff = abs(agents[i].phase - agents[j].phase)
                diff = min(diff, 2.0 * math.pi - diff)
                max_diff = max(max_diff, diff)

        assert max_diff <= delta, (
            f"Max phase difference {max_diff} exceeds delta {delta}"
        )
        assert all(a.converged for a in agents), "Not all agents marked converged"


# ---------------------------------------------------------------------------
# Synergy 4: Sunset Inheritance
# ---------------------------------------------------------------------------

class TestSunsetInheritance:
    def test_successor_inherits_better_precision(self):
        """Simulate agent death and successor spawn;
        prove successor starts with better precision than predecessor."""
        from constraint_theory_core.metronome import Metronome
        from constraint_theory_core.lattice import covering_radius

        # Predecessor operates for 200 ticks observing a safe reference.
        predecessor = Metronome(
            T=1.0,
            phi0=0.0,
            epsilon=covering_radius(),
            delta=covering_radius(),
        )
        for _ in range(200):
            predecessor.tick()
            predecessor.observe(0.01, 0.01)

        inherited_epsilon = predecessor.state().epsilon
        assert inherited_epsilon < covering_radius()
        assert predecessor.anomaly_count == 0

        # Successor spawns with the predecessor's narrowed deadband.
        successor = Metronome(
            T=1.0,
            phi0=0.0,
            epsilon=inherited_epsilon,
            delta=covering_radius(),
        )

        assert successor.epsilon == inherited_epsilon
        assert successor.epsilon < covering_radius(), (
            "Successor must start with better precision than predecessor's initial ε"
        )


# ---------------------------------------------------------------------------
# Synergy 5: Full Pipeline — PLATO tile → constraint check → holonomy verify
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PLATOTile:
    """Minimal PLATO tile standing in for the 384-byte constraint block."""
    domain: str
    edges: List[Tuple[int, int]]
    directions: List[int]
    reliability: float = 1.0


class TestFullPipelinePlatoHolonomy:
    def test_plato_tiles_consistency_and_fault_isolation(self):
        """Create PLATO tiles with constraint data, verify consistency,
        and isolate an injected fault."""
        from constraint_theory_core.holonomy import (
            verify_consistency,
            isolate_fault,
            fault_boundaries,
        )

        # Consistent triangle: 16+16+16 = 48 ≡ 0 (mod 48)
        good_dirs = [16, 16, 16]
        # Inconsistent triangle
        bad_dirs = [1, 2, 3]  # sum = 6 ≠ 0

        tiles = [
            PLATOTile("fleet", [(0, 1), (1, 2), (2, 0)], good_dirs),
            PLATOTile("fleet", [(0, 3), (3, 4), (4, 0)], good_dirs),
            PLATOTile("fleet", [(1, 5), (5, 6), (6, 1)], good_dirs),
            PLATOTile("fleet", [(2, 7), (7, 8), (8, 2)], bad_dirs),  # injected fault
        ]

        raw = [(t.edges, t.directions) for t in tiles]

        assert verify_consistency(raw[:3]) is True
        assert verify_consistency(raw) is False

        idx = isolate_fault(raw)
        assert idx == 3

        bad_indices = fault_boundaries(raw)
        assert bad_indices == [3]
