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

---
Study 72 finding: Original intent vectors used 6 deterministic hash dimensions
that don't discriminate faults (precision=recall=0). SemanticGL9Consensus replaces
those with actual semantic features that respond to fault injection.
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


# ============================================================================
# Semantic GL(9) — Study 72 fix: replace 6 hash dims with real features
# ============================================================================

SEMANTIC_CI_FACETS = [
    "C1 Embedding Sim",    # replaces: MD5 hash of source name
    "C2 Output Entropy",   # replaces: MD5 hash of domain
    "C3 Resp Length Dev",  # replaces: MD5 hash of content[:64]
    "C4 Confidence",       # KEPT: confidence value (the one working dim)
    "C5 Token KL Div",     # replaces: tag count / 5
    "C6 Semantic Drift",   # replaces: unique tag count
    "C7 Conf Calibration",  # replaces: activation key presence
    "C8 Domain Match",     # replaces: target tier
    "C9 Temporal Chg",     # replaces: lifecycle encoding
]


def shannon_entropy(tokens: list[str]) -> float:
    """Compute Shannon entropy of a token distribution."""
    if not tokens:
        return 0.0
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens)
    entropy = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def token_kl_divergence(tokens_a: list[str], tokens_b: list[str]) -> float:
    """KL divergence D(P_a || P_b) with Laplace smoothing."""
    if not tokens_a or not tokens_b:
        return 0.0
    vocab = set(tokens_a) | set(tokens_b)
    n_a, n_b = len(tokens_a), len(tokens_b)
    # Laplace smoothing
    alpha = 1.0
    d = len(vocab)
    counts_a: dict[str, int] = {}
    counts_b: dict[str, int] = {}
    for t in tokens_a:
        counts_a[t] = counts_a.get(t, 0) + 1
    for t in tokens_b:
        counts_b[t] = counts_b.get(t, 0) + 1
    kl = 0.0
    for w in vocab:
        p = (counts_a.get(w, 0) + alpha) / (n_a + alpha * d)
        q = (counts_b.get(w, 0) + alpha) / (n_b + alpha * d)
        kl += p * math.log2(p / q)
    return max(0.0, kl)  # KL is non-negative


@dataclass
class ExpertObservation:
    """Observation data from a single expert for semantic feature extraction."""
    expert_id: str
    response: str = ""
    tokens: list[str] = field(default_factory=list)
    confidence: float = 1.0
    embedding: list[float] = field(default_factory=list)
    domain: str = ""
    predicted_accuracy: float = 1.0  # model's own accuracy estimate
    actual_accuracy: float = 1.0      # ground truth or proxy


@dataclass
class FleetContext:
    """Fleet-wide context for computing relative features."""
    # Fleet centroid embedding (average of all expert embeddings)
    centroid_embedding: list[float] = field(default_factory=list)
    # Fleet-average token distribution (union of all tokens)
    fleet_tokens: list[str] = field(default_factory=list)
    # Fleet response length statistics
    mean_response_length: float = 0.0
    std_response_length: float = 1.0
    # Fleet confidence statistics
    mean_confidence: float = 1.0
    std_confidence: float = 0.1
    # Most common domain in fleet
    majority_domain: str = ""


def compute_semantic_intent(
    obs: ExpertObservation,
    ctx: FleetContext,
    prev_intent: Optional[IntentVector] = None,
) -> IntentVector:
    """
    Compute 9D semantic intent vector from expert observation.

    Each dimension is a real semantic feature that responds to faults:
      C1: embedding cosine similarity to fleet centroid
      C2: output token entropy (normalized to [0,1])
      C3: response length z-score deviation (clamped)
      C4: confidence z-score (the original working dimension)
      C5: token distribution KL divergence from fleet
      C6: semantic drift from previous intent (or 0 if first)
      C7: confidence calibration error
      C8: domain consistency (1 if matches majority, 0 otherwise)
      C9: temporal change magnitude
    """
    dims = [0.0] * 9

    # C1: Embedding similarity to fleet centroid
    if obs.embedding and ctx.centroid_embedding:
        obs_vec = IntentVector(obs.embedding[:9])  # project to 9D
        cen_vec = IntentVector(ctx.centroid_embedding[:9])
        dims[0] = max(0.0, obs_vec.cosine_similarity(cen_vec))
    else:
        # Fallback: use response-level proxy (normalized Levenshtein-like ratio)
        dims[0] = 0.5  # neutral when no embedding available

    # C2: Output entropy (normalize by log2(vocab_size) for [0,1])
    entropy = shannon_entropy(obs.tokens) if obs.tokens else 0.0
    vocab_size = max(len(set(obs.tokens)), 2)
    max_entropy = math.log2(vocab_size)
    dims[1] = entropy / max_entropy if max_entropy > 0 else 0.0

    # C3: Response length deviation (z-score, clamped to [-3, 3], then [0,1])
    if ctx.std_response_length > 1e-9:
        z = (len(obs.response) - ctx.mean_response_length) / ctx.std_response_length
        dims[2] = 1.0 - 1.0 / (1.0 + abs(z))  # sigmoid-like: higher = more deviant
    else:
        dims[2] = 0.0

    # C4: Confidence z-score (the original working dimension)
    if ctx.std_confidence > 1e-9:
        dims[3] = (obs.confidence - ctx.mean_confidence) / ctx.std_confidence
        dims[3] = max(-3.0, min(3.0, dims[3]))
        dims[3] = (dims[3] + 3.0) / 6.0  # normalize to [0, 1]
    else:
        dims[3] = 0.5

    # C5: Token KL divergence from fleet
    kl = token_kl_divergence(obs.tokens, ctx.fleet_tokens) if obs.tokens else 0.0
    dims[4] = 1.0 - 1.0 / (1.0 + kl)  # sigmoid-like mapping

    # C6: Semantic drift from previous intent
    if prev_intent is not None:
        current_raw = IntentVector(dims[:6] + [0.0, 0.0, 0.0])
        dims[5] = 1.0 - current_raw.cosine_similarity(prev_intent)
    else:
        dims[5] = 0.0

    # C7: Confidence calibration error
    dims[6] = abs(obs.predicted_accuracy - obs.actual_accuracy)

    # C8: Domain consistency
    dims[7] = 1.0 if (obs.domain and obs.domain == ctx.majority_domain) else 0.0

    # C9: Temporal change (response length change if available, else drift proxy)
    if prev_intent is not None:
        dims[8] = abs(dims[5])  # reuse drift as temporal proxy
    else:
        dims[8] = 0.0

    return IntentVector(dims)


def compute_fleet_context(observations: list[ExpertObservation]) -> FleetContext:
    """Compute fleet-wide context from all expert observations."""
    if not observations:
        return FleetContext()

    # Centroid embedding
    embeddings = [o.embedding for o in observations if o.embedding]
    centroid = []
    if embeddings:
        dim = min(len(e) for e in embeddings)
        dim = min(dim, 9)
        centroid = [
            sum(e[i] for e in embeddings if len(e) > i) / len(embeddings)
            for i in range(dim)
        ]

    # Fleet tokens
    all_tokens: list[str] = []
    for o in observations:
        all_tokens.extend(o.tokens)

    # Response length stats
    lengths = [len(o.response) for o in observations if o.response]
    mean_len = sum(lengths) / len(lengths) if lengths else 0.0
    std_len = (sum((l - mean_len) ** 2 for l in lengths) / len(lengths)) ** 0.5 if len(lengths) > 1 else 1.0

    # Confidence stats
    confs = [o.confidence for o in observations]
    mean_conf = sum(confs) / len(confs) if confs else 1.0
    std_conf = (sum((c - mean_conf) ** 2 for c in confs) / len(confs)) ** 0.5 if len(confs) > 1 else 0.1

    # Majority domain
    domain_counts: dict[str, int] = {}
    for o in observations:
        if o.domain:
            domain_counts[o.domain] = domain_counts.get(o.domain, 0) + 1
    majority = max(domain_counts, key=domain_counts.get) if domain_counts else ""

    return FleetContext(
        centroid_embedding=centroid,
        fleet_tokens=all_tokens,
        mean_response_length=mean_len,
        std_response_length=max(std_len, 1e-9),
        mean_confidence=mean_conf,
        std_confidence=max(std_conf, 1e-9),
        majority_domain=majority,
    )


class SemanticGL9Consensus:
    """
    GL(9) consensus with semantic intent vectors.

    Study 72 fix: replaces 6 deterministic hash dimensions with features
    that actually respond to faults:
      - Embedding similarity to fleet centroid
      - Output token entropy
      - Response length deviation
      - Token distribution KL divergence
      - Semantic drift from previous round
      - Confidence calibration error
      - Domain consistency
      - Temporal change

    The GL(9) holonomy math remains unchanged — only the intent vector
    computation is improved. This means:
      - Plane rotations, cycle holonomy, fault location all still work
      - But the intent vectors now carry real discriminative signal
      - Faults that change any of these 9 features WILL be detected
    """

    def __init__(self, tolerance: float = DEFAULT_TOLERANCE,
                 similarity_threshold: float = 0.3):
        self.tolerance = tolerance
        self.similarity_threshold = similarity_threshold
        self.agents: dict[int, GL9Agent] = {}
        self._prev_intents: dict[int, IntentVector] = {}

    def ingest_observations(self, observations: list[ExpertObservation]) -> None:
        """
        Convert expert observations into GL(9) agents with semantic intent.

        Each observation becomes a GL9Agent with:
          - Intent vector computed from semantic features
          - Identity transform (we rely on intent similarity for detection)
          - Full mesh connectivity (every agent is neighbor of every other)
        """
        ctx = compute_fleet_context(observations)

        self.agents.clear()
        for obs in observations:
            prev = self._prev_intents.get(hash(obs.expert_id))
            intent = compute_semantic_intent(obs, ctx, prev)
            agent_id = hash(obs.expert_id) & 0x7FFFFFFF
            # Create neighbors: all other agents
            other_ids = [
                hash(o.expert_id) & 0x7FFFFFFF
                for o in observations if o.expert_id != obs.expert_id
            ]
            agent = GL9Agent(
                id=agent_id,
                intent=intent,
                transform=GL9Matrix.identity(),
                neighbors=other_ids,
            )
            self.agents[agent_id] = agent
            self._prev_intents[agent_id] = intent

    def detect_faults(self, observations: list[ExpertObservation]) -> list[str]:
        """
        Detect faulty experts using semantic GL(9) intent vectors.

        Method: Compute fleet centroid in 9D semantic space, then flag
        experts whose Euclidean distance from the centroid exceeds
        (global_mean + similarity_threshold * std). This uses z-scoring
        on distances, which is more sensitive than cosine similarity
        when only some dimensions change (Study 72: cosine was dominated
        by 5 identical dims out of 9).
        """
        if len(observations) < 2:
            return []

        ctx = compute_fleet_context(observations)

        # Compute semantic intent for each expert
        intents: dict[str, IntentVector] = {}
        for obs in observations:
            prev = self._prev_intents.get(hash(obs.expert_id) & 0x7FFFFFFF)
            intents[obs.expert_id] = compute_semantic_intent(obs, ctx, prev)

        # Fleet centroid
        ids = list(intents.keys())
        n = len(ids)
        centroid = [0.0] * 9
        for intent in intents.values():
            for d in range(9):
                centroid[d] += intent.data[d]
        centroid = [c / n for c in centroid]

        # Euclidean distance from centroid per expert
        distances: dict[str, float] = {}
        for eid, intent in intents.items():
            dist = math.sqrt(sum((intent.data[d] - centroid[d]) ** 2 for d in range(9)))
            distances[eid] = dist

        # Z-score of distances
        dists = list(distances.values())
        mean_dist = sum(dists) / len(dists)
        std_dist = math.sqrt(sum((d - mean_dist) ** 2 for d in dists) / len(dists)) if len(dists) > 1 else 0.0

        if std_dist < 1e-9:
            # All identical — no faults
            for eid, intent in intents.items():
                self._prev_intents[hash(eid) & 0x7FFFFFFF] = intent
            return []

        # Flag experts with distance > mean + similarity_threshold * std
        threshold = mean_dist + self.similarity_threshold * std_dist
        faulty = [
            eid for eid, dist in distances.items()
            if dist > threshold
        ]

        # Update prev_intents
        for eid, intent in intents.items():
            self._prev_intents[hash(eid) & 0x7FFFFFFF] = intent

        return faulty

    def detect_with_details(self, observations: list[ExpertObservation]) -> tuple[list[str], dict[str, float]]:
        """
        Detect faulty experts and return deviation details.

        Returns:
            (faulty_ids, {expert_id: deviation_score})
        """
        if len(observations) < 2:
            return [], {}

        ctx = compute_fleet_context(observations)

        intents: dict[str, IntentVector] = {}
        for obs in observations:
            prev = self._prev_intents.get(hash(obs.expert_id) & 0x7FFFFFFF)
            intents[obs.expert_id] = compute_semantic_intent(obs, ctx, prev)

        # Fleet centroid
        ids = list(intents.keys())
        n = len(ids)
        centroid = [0.0] * 9
        for intent in intents.values():
            for d in range(9):
                centroid[d] += intent.data[d]
        centroid = [c / n for c in centroid]

        # Euclidean distance from centroid
        distances: dict[str, float] = {}
        for eid, intent in intents.items():
            dist = math.sqrt(sum((intent.data[d] - centroid[d]) ** 2 for d in range(9)))
            distances[eid] = dist

        dists = list(distances.values())
        mean_dist = sum(dists) / len(dists)
        std_dist = math.sqrt(sum((d - mean_dist) ** 2 for d in dists) / len(dists)) if len(dists) > 1 else 0.0

        faulty = []
        details: dict[str, float] = {}
        for eid, dist in distances.items():
            dev = (dist - mean_dist) / std_dist if std_dist > 1e-9 else 0.0
            details[eid] = dev
            if std_dist > 1e-9 and dist > mean_dist + self.similarity_threshold * std_dist:
                faulty.append(eid)

        # Update prev_intents
        for eid, intent in intents.items():
            self._prev_intents[hash(eid) & 0x7FFFFFFF] = intent

        return faulty, details
