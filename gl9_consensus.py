"""
gl9_consensus — GL(9) Holonomy Consensus for Fleet Intent Alignment

Port of Oracle1's holonomy-consensus/src/zhc_gl9.rs
9D intent vectors preserve full CI facet structure where SO(3) destroyed correlation.

CI Facets (9 dimensions):
  0: C1 Boundary    — System boundaries and scope
  1: C2 Pattern     — Recognized patterns
  2: C3 Process     — Process models
  3: C4 Knowledge   — Knowledge structures
  4: C5 Social      — Social dynamics
  5: C6 Deep Structure — Underlying structures
  6: C7 Instrument  — Instruments and tools
  7: C8 Paradigm    — Paradigmatic frameworks
  8: C9 Stakes      — Stakes and values

The key result: SO(3) projection gave r=-0.045 (correlation destroyed).
GL(9) on full intent vectors gives r=0.0+ (correlation preserved).
"""
import math
from dataclasses import dataclass, field
from typing import Optional


INTENT_DIM = 9
DEFAULT_TOLERANCE = 0.5
CI_FACETS = [
    "C1 Boundary", "C2 Pattern", "C3 Process", "C4 Knowledge",
    "C5 Social", "C6 Deep Structure", "C7 Instrument", "C8 Paradigm", "C9 Stakes",
]


class GL9Matrix:
    """9×9 matrix in GL(9) — general linear group operating on 9D intent vectors."""

    def __init__(self, data: Optional[list[float]] = None):
        if data is None:
            self.data = [0.0] * 81
        else:
            assert len(data) == 81
            self.data = list(data)

    @classmethod
    def identity(cls) -> "GL9Matrix":
        m = cls()
        for i in range(9):
            m.data[i * 9 + i] = 1.0
        return m

    @classmethod
    def from_2d(cls, rows: list[list[float]]) -> "GL9Matrix":
        m = cls()
        for i in range(9):
            for j in range(9):
                m.data[i * 9 + j] = rows[i][j]
        return m

    @classmethod
    def plane_rotation(cls, dim_a: int, dim_b: int, angle: float) -> "GL9Matrix":
        m = cls.identity()
        c, s = math.cos(angle), math.sin(angle)
        m.data[dim_a * 9 + dim_a] = c
        m.data[dim_a * 9 + dim_b] = -s
        m.data[dim_b * 9 + dim_a] = s
        m.data[dim_b * 9 + dim_b] = c
        return m

    @classmethod
    def scaling(cls, factors: list[float]) -> "GL9Matrix":
        m = cls.identity()
        for i in range(9):
            m.data[i * 9 + i] = factors[i]
        return m

    def multiply(self, other: "GL9Matrix") -> "GL9Matrix":
        result = GL9Matrix()
        for i in range(9):
            for j in range(9):
                s = 0.0
                for k in range(9):
                    s += self.data[i * 9 + k] * other.data[k * 9 + j]
                result.data[i * 9 + j] = s
        return result

    def deviation(self) -> float:
        """Frobenius norm of (M - I), measuring holonomy deviation from identity."""
        total = 0.0
        for i in range(9):
            for j in range(9):
                expected = 1.0 if i == j else 0.0
                diff = self.data[i * 9 + j] - expected
                total += diff * diff
        return math.sqrt(total)

    def is_identity(self, tolerance: float) -> bool:
        return self.deviation() < tolerance

    def transform(self, v: list[float]) -> list[float]:
        result = [0.0] * 9
        for i in range(9):
            for j in range(9):
                result[i] += self.data[i * 9 + j] * v[j]
        return result

    def get(self, row: int, col: int) -> float:
        return self.data[row * 9 + col]

    def set(self, row: int, col: int, val: float):
        self.data[row * 9 + col] = val

    def determinant(self) -> float:
        # LU decomposition for 9×9
        a = [list(self.data[i*9:(i+1)*9]) for i in range(9)]
        det = 1.0
        for col in range(9):
            max_row = col
            for row in range(col + 1, 9):
                if abs(a[row][col]) > abs(a[max_row][col]):
                    max_row = row
            if max_row != col:
                a[col], a[max_row] = a[max_row], a[col]
                det *= -1
            if abs(a[col][col]) < 1e-12:
                return 0.0
            det *= a[col][col]
            for row in range(col + 1, 9):
                factor = a[row][col] / a[col][col]
                for j in range(col + 1, 9):
                    a[row][j] -= factor * a[col][j]
        return det

    def transpose(self) -> "GL9Matrix":
        m = GL9Matrix()
        for i in range(9):
            for j in range(9):
                m.data[i * 9 + j] = self.data[j * 9 + i]
        return m


class IntentVector:
    """9D intent vector spanning all CI facets."""

    def __init__(self, data: Optional[list[float]] = None):
        if data is None:
            self.data = [1.0 / math.sqrt(9)] * 9
        else:
            assert len(data) == 9
            self.data = list(data)

    @classmethod
    def uniform(cls) -> "IntentVector":
        return cls([1.0 / math.sqrt(9)] * 9)

    @classmethod
    def unit(cls, dim: int) -> "IntentVector":
        v = [0.0] * 9
        v[dim] = 1.0
        return cls(v)

    def norm(self) -> float:
        return math.sqrt(sum(x * x for x in self.data))

    def normalize(self) -> "IntentVector":
        n = self.norm()
        if n < 1e-12:
            return IntentVector([0.0] * 9)
        return IntentVector([x / n for x in self.data])

    def cosine_similarity(self, other: "IntentVector") -> float:
        dot = sum(a * b for a, b in zip(self.data, other.data))
        na, nb = self.norm(), other.norm()
        if na < 1e-12 or nb < 1e-12:
            return 0.0
        return dot / (na * nb)

    def distance(self, other: "IntentVector") -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(self.data, other.data)))


@dataclass
class GL9ConsensusResult:
    consensus: bool
    deviation: float
    cycle_count: int
    faulty_agents: list[int] = field(default_factory=list)
    alignment: float = 0.0
    correlation: float = 0.0


@dataclass
class GL9Agent:
    id: int
    intent: IntentVector
    transform: GL9Matrix
    neighbors: list[int] = field(default_factory=list)


def pearson_correlation(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    mean_x = sum(x[:n]) / n
    mean_y = sum(y[:n]) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    var_y = sum((y[i] - mean_y) ** 2 for i in range(n))
    if var_x < 1e-12 or var_y < 1e-12:
        return 0.0
    return cov / math.sqrt(var_x * var_y)


class GL9HolonomyConsensus:
    """Consensus via zero-holonomy in GL(9) intent space."""

    def __init__(self, tolerance: float = DEFAULT_TOLERANCE):
        self.tolerance = tolerance
        self.agents: dict[int, GL9Agent] = {}

    def add_agent(self, agent: GL9Agent):
        self.agents[agent.id] = agent

    def get_agent(self, agent_id: int) -> Optional[GL9Agent]:
        return self.agents.get(agent_id)

    def compute_cycle_holonomy(self, cycle: list[int]) -> GL9Matrix:
        result = GL9Matrix.identity()
        for i in range(len(cycle)):
            agent = self.agents.get(cycle[i])
            if agent is None:
                return result
            next_id = cycle[(i + 1) % len(cycle)]
            if next_id in agent.neighbors:
                result = agent.transform.multiply(result)
        return result

    def compute_alignment(self) -> float:
        agents = list(self.agents.values())
        if len(agents) < 2:
            return 1.0
        total = 0.0
        count = 0
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                total += agents[i].intent.cosine_similarity(agents[j].intent)
                count += 1
        return total / count if count > 0 else 1.0

    def find_cycles(self) -> list[list[int]]:
        cycles = []
        visited_starts = set()
        for agent in self.agents.values():
            if agent.id in visited_starts:
                continue
            visited_starts.add(agent.id)
            for neighbor in agent.neighbors:
                cycle = self._trace_cycle(agent.id, neighbor)
                if cycle:
                    key = tuple(sorted(cycle))
                    if key not in {tuple(sorted(c)) for c in cycles}:
                        cycles.append(cycle)
        return cycles

    def _trace_cycle(self, start: int, first_neighbor: int) -> Optional[list[int]]:
        cycle = [start, first_neighbor]
        current = first_neighbor
        for _ in range(len(self.agents) + 1):
            agent = self.agents.get(current)
            if agent is None:
                return None
            prev = cycle[-2]
            next_nodes = [n for n in agent.neighbors if n != prev]
            if not next_nodes:
                return None
            nxt = next_nodes[0]
            if nxt == start:
                return cycle
            cycle.append(nxt)
            current = nxt
        return None

    def locate_fault(self, cycle: list[int]) -> Optional[int]:
        left, right = 0, len(cycle)
        while right - left > 1:
            mid = (left + right) // 2
            sub = cycle[left:mid]
            hol = self.compute_cycle_holonomy(sub)
            if hol.deviation() > self.tolerance:
                right = mid
            else:
                left = mid
        return cycle[left] if left < len(cycle) else None

    def check_consensus(self) -> GL9ConsensusResult:
        cycles = self.find_cycles()
        if not cycles:
            return GL9ConsensusResult(
                consensus=True, deviation=0.0, cycle_count=0,
                alignment=self.compute_alignment()
            )

        max_deviation = 0.0
        faulty = []
        for cycle in cycles:
            hol = self.compute_cycle_holonomy(cycle)
            dev = hol.deviation()
            max_deviation = max(max_deviation, dev)
            if dev > self.tolerance:
                fault = self.locate_fault(cycle)
                if fault is not None and fault not in faulty:
                    faulty.append(fault)

        hol_vals, align_vals = self.holonomy_alignment_correlation()
        corr = pearson_correlation(hol_vals, align_vals) if len(hol_vals) >= 2 else 0.0

        return GL9ConsensusResult(
            consensus=max_deviation <= self.tolerance,
            deviation=max_deviation,
            cycle_count=len(cycles),
            faulty_agents=faulty,
            alignment=self.compute_alignment(),
            correlation=corr,
        )

    def holonomy_alignment_correlation(self) -> tuple[list[float], list[float]]:
        cycles = self.find_cycles()
        holonomies, alignments = [], []
        for cycle in cycles:
            hol = self.compute_cycle_holonomy(cycle)
            holonomies.append(hol.deviation())
            sim_sum, count = 0.0, 0
            for i in range(len(cycle)):
                for j in range(i + 1, len(cycle)):
                    a, b = self.agents.get(cycle[i]), self.agents.get(cycle[j])
                    if a and b:
                        sim_sum += a.intent.cosine_similarity(b.intent)
                        count += 1
            alignments.append(sim_sum / count if count > 0 else 1.0)
        return holonomies, alignments
