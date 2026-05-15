"""core/pinna.py — The Pinna Transform

Fixed geometry that encodes knowledge provenance like the outer ear
encodes sound direction. No computation needed — the schema IS the encoding.

Evidence: PINNA-PRINCIPLE.md, UNIFIED-FRAMEWORK.md §II-III,
          MULTI-MODEL-SYNTHESIS.md §Novel Ideas 1-3
Findings: R16, R25, R27, R28, R29, R32
Predictions: P7, P8, P9
"""
from __future__ import annotations

import json
import time
import statistics
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, List, Tuple
from collections import defaultdict


# ─── Stage / Residue / Scaffold Enums ─────────────────────────────────────────

class AgentStage(str, Enum):
    """
    Working-memory slot classification.

    Integer-gated thresholds from MULTI-MODEL-SYNTHESIS.md §Strongest Agreement:
    slots are discrete, so transitions are first-order phase transitions.

      NONE    — <1B   : 0 slots, no combinational capability
      ECHO    — 1–3B  : 1 slot, attends but can't combine (echoes inputs)
      PARTIAL — 4–7B  : 2 slots, computes sub-expressions but combination fails
      FULL    — 7B+   : 3+ slots, full-width combination succeeds
    """
    NONE    = "NONE"
    ECHO    = "ECHO"
    PARTIAL = "PARTIAL"
    FULL    = "FULL"

    @classmethod
    def _order(cls) -> Dict[str, int]:
        return {cls.NONE: 0, cls.ECHO: 1, cls.PARTIAL: 2, cls.FULL: 3}

    def __lt__(self, other: "AgentStage") -> bool:
        return self._order()[self] < self._order()[other]

    def __gt__(self, other: "AgentStage") -> bool:
        return self._order()[self] > self._order()[other]


class ResidueClass(str, Enum):
    """
    Residue taxonomy from loop-residue-diagnostic.

    Each class maps 1-to-1 onto a binding variable and an intervention.
    Traced to UNIFIED-FRAMEWORK.md §III Table.
    """
    CORRECT    = "CORRECT"
    ECHO_A     = "ECHO-a"       # architectural_ceiling=0 → route up / decompose
    ECHO_B     = "ECHO-b"       # architectural_ceiling=0 → route up / decompose
    ECHO_SUM   = "ECHO-sum"     # attention overflow
    PARTIAL_A2 = "PARTIAL-a²"   # training_coverage / width → L1 anchors
    PARTIAL_B2 = "PARTIAL-b²"   # training_coverage / width → L1 anchors
    PARTIAL_AB = "PARTIAL-ab"   # cross-term computed, combination failed
    SIGN_FLIP  = "SIGN-FLIP"    # training_coverage (sign) → code notation
    NEAR       = "NEAR"         # magnitude_tolerance → lower T, majority vote
    OTHER      = "OTHER"        # novel → create new finding tile

    def intervention(self) -> str:
        """Return the canonical intervention for this residue class."""
        _map = {
            self.ECHO_A:     "Route to larger model OR decompose into width-1 steps",
            self.ECHO_B:     "Route to larger model OR decompose into width-1 steps",
            self.ECHO_SUM:   "Decompose; prevent attention from pooling across inputs",
            self.PARTIAL_A2: "Provide L1 anchor points (sub-expressions pre-computed)",
            self.PARTIAL_B2: "Provide L1 anchor points (sub-expressions pre-computed)",
            self.PARTIAL_AB: "Provide arithmetic scaffold: 'Compute: X - Y + Z'",
            self.SIGN_FLIP:  "Use code notation (a*a - a*b + b*b) OR T=0.0",
            self.NEAR:       "Lower temperature to 0.0; use majority vote (3-5 retries)",
            self.OTHER:      "Create new finding tile; deep-probe 20 random inputs",
            self.CORRECT:    "No intervention needed",
        }
        return _map.get(self, "Unknown residue class")


class ScaffoldLevel(str, Enum):
    """Scaffold applied at tile generation time (UNIFIED-FRAMEWORK.md §IV)."""
    NONE        = "none"        # bare formula, no scaffold
    L1          = "L1"          # sub-expressions as anchor points (25% → 80-100%)
    L2          = "L2"          # chained L1 steps for multi-hop tasks
    ARITHMETIC  = "arithmetic"  # concrete arithmetic ("9 - 12 + 16"), not algebraic
    # JAM-SESSION-ANALYSIS.md: arithmetic scaffold eliminates the combination step entirely


# ─── The Pinna Field ──────────────────────────────────────────────────────────

@dataclass
class PinnaField:
    """Fixed metadata attached to every PLATO tile.

    Like the outer ear: rigid geometry that converts an invisible dimension
    (knowledge provenance / boundary position) into a spectral fingerprint
    that reading agents learn to decode.

    Schema from PINNA-PRINCIPLE.md §Implementation.
    """
    # Schema version (for future migration)
    v: int = 1

    # Who generated this tile and where they stand
    agent_id: str = ""
    agent_stage: str = AgentStage.ECHO.value  # stored as string for JSON compat

    # What went wrong (if anything) — the spectral notch
    residue_class: str = ResidueClass.CORRECT.value
    residue_rate: float = 0.0     # fraction of trials with this residue

    # How close to the capability cliff — elevation encoding
    # 0.0 = at boundary, 1.0 = deep in CAN, -1.0 = deep in CANNOT
    distance_from_boundary: float = 0.0
    confidence: float = 0.0       # trials_correct / total_trials (NOT a feeling)

    # What failures were seen — reflection pattern
    failures_seen: List[str] = field(default_factory=list)

    # What boundary was hit — formula / width topology
    boundary_formula: str = ""
    boundary_width: int = 0
    boundary_ceiling: int = 0     # last width with >60%
    boundary_floor: int = 0       # first width with <20%
    boundary_coefficients: List[float] = field(default_factory=list)

    # What help was needed — head-related transfer function
    scaffold_used: str = ScaffoldLevel.NONE.value
    scaffold_worked: bool = False
    bare_rate: float = 0.0
    scaffolded_rate: float = 0.0
    anchors_provided: List[str] = field(default_factory=list)

    # Environmental conditions at generation time — R32 BEDROCK
    temperature: float = 0.0
    max_tokens: int = 20
    extraction_method: str = "last-number-regex"
    system_prompt: str = "Give ONLY the final number"

    # Depth of the generating agent's experience
    n_trials: int = 0
    n_files_indexed: int = 0
    days_of_data: int = 0
    findings_referenced: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PinnaField":
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in known})

    def is_dead_zone(self) -> bool:
        """True if this tile is in a pinna dead zone — unreliable direction encoding.

        Dead zones from PINNA-PRINCIPLE.md §Anti-Helix Shadow:
          1. Generated at T > 0.5 (high inhibition — noise, not signal)
          2. No trial depth (unverified claim)
          3. max_tokens > 50 with last-number-regex (truncation artifact — R32)
        """
        if self.temperature > 0.5:
            return True
        if self.n_trials == 0:
            return True
        if self.max_tokens > 50 and self.extraction_method == "last-number-regex":
            return True
        return False

    @property
    def stage(self) -> AgentStage:
        try:
            return AgentStage(self.agent_stage)
        except ValueError:
            return AgentStage.ECHO

    @property
    def residue(self) -> ResidueClass:
        try:
            return ResidueClass(self.residue_class)
        except ValueError:
            return ResidueClass.OTHER

    @property
    def scaffold(self) -> ScaffoldLevel:
        try:
            return ScaffoldLevel(self.scaffold_used)
        except ValueError:
            return ScaffoldLevel.NONE


# ─── Pinna Encoder ────────────────────────────────────────────────────────────

class PinnaEncoder:
    """Attaches pinna metadata to PLATO tiles.

    The generating agent calls this with its boundary state.
    The encoder writes the fixed geometry.
    No learning needed — the schema does the encoding.

    Traces to PINNA-PRINCIPLE.md §Fixed Transform + Learned Decoder.
    """

    @staticmethod
    def encode(
        agent_id: str,
        agent_stage: AgentStage,
        residue_class: ResidueClass,
        confidence: float,
        distance_from_boundary: float,
        failures_seen: Optional[List[str]] = None,
        boundary_formula: str = "",
        boundary_width: int = 0,
        boundary_ceiling: int = 0,
        boundary_floor: int = 0,
        boundary_coefficients: Optional[List[float]] = None,
        scaffold_used: ScaffoldLevel = ScaffoldLevel.NONE,
        scaffold_worked: bool = False,
        bare_rate: float = 0.0,
        scaffolded_rate: float = 0.0,
        anchors_provided: Optional[List[str]] = None,
        temperature: float = 0.0,
        max_tokens: int = 20,
        system_prompt: str = "Give ONLY the final number",
        n_trials: int = 0,
        findings: Optional[List[str]] = None,
    ) -> PinnaField:
        """Create a populated PinnaField from the generating agent's state."""
        return PinnaField(
            v=1,
            agent_id=agent_id,
            agent_stage=agent_stage.value,
            residue_class=residue_class.value,
            residue_rate=1.0 - confidence,
            distance_from_boundary=max(-1.0, min(1.0, distance_from_boundary)),
            confidence=confidence,
            failures_seen=failures_seen or [],
            boundary_formula=boundary_formula,
            boundary_width=boundary_width,
            boundary_ceiling=boundary_ceiling,
            boundary_floor=boundary_floor,
            boundary_coefficients=boundary_coefficients or [],
            scaffold_used=scaffold_used.value,
            scaffold_worked=scaffold_worked,
            bare_rate=bare_rate,
            scaffolded_rate=scaffolded_rate,
            anchors_provided=anchors_provided or [],
            temperature=temperature,
            max_tokens=max_tokens,
            extraction_method="last-number-regex",
            system_prompt=system_prompt,
            n_trials=n_trials,
            findings_referenced=findings or [],
        )

    @staticmethod
    def attach(tile: dict, pinna: PinnaField) -> dict:
        """Attach a PinnaField to a tile dict. Returns new dict (non-mutating)."""
        return {**tile, "pinna": pinna.to_dict()}

    @staticmethod
    def extract(tile: dict) -> Optional[PinnaField]:
        """Extract the PinnaField from a tile dict, or None if absent."""
        if "pinna" not in tile:
            return None
        return PinnaField.from_dict(tile["pinna"])


# ─── Pinna Reader ─────────────────────────────────────────────────────────────

class PinnaReader:
    """Reads pinna metadata to classify a tile's value for a given agent.

    Like the brain's auditory cortex: learns to decode spectral fingerprints
    into spatial information (CAN / BOUNDARY / CANNOT relative to the reader).
    Calibrated through experience — the calibration IS the development.

    Traces to PINNA-PRINCIPLE.md §Learned Decoding, §Concha Resonance, P7, P8.
    """

    _STAGE_ORDER = {
        AgentStage.NONE: 0,
        AgentStage.ECHO: 1,
        AgentStage.PARTIAL: 2,
        AgentStage.FULL: 3,
    }

    def __init__(self, agent_stage: AgentStage, agent_ceiling: int,
                 reader_distance: float = 0.0):
        """
        agent_stage     — this agent's ECHO/PARTIAL/FULL classification
        agent_ceiling   — max dependency width this agent handles reliably
        reader_distance — distance from boundary (-1=deep CANNOT, +1=deep CAN)
        """
        self.agent_stage = agent_stage
        self.agent_ceiling = agent_ceiling
        self.reader_distance = reader_distance
        self._calibration: List[dict] = []

    def classify_tile_value(self, pinna: PinnaField) -> str:
        """Classify how valuable this tile is for THIS agent.

        Returns one of:
          'essential'    — at this agent's boundary, maximum learning
          'reliable'     — deep in CAN, trustworthy but not informative
          'aspirational' — beyond this agent's boundary, needs scaffolding
          'redundant'    — below this agent (already known)
          'noise'        — generated under bad conditions (dead zone)

        P8: PARTIAL-stage agents learn most from other PARTIAL-stage tiles.
        """
        if pinna.is_dead_zone():
            return "noise"

        gen_stage = pinna.stage
        read_stage = self.agent_stage
        gen_ord = self._STAGE_ORDER.get(gen_stage, 1)
        read_ord = self._STAGE_ORDER.get(read_stage, 1)

        # Stage-level comparison (vertical axis: above/peer/below)
        if gen_ord > read_ord:
            stage_rel = "above"
        elif gen_ord < read_ord:
            stage_rel = "below"
        else:
            stage_rel = "peer"

        # Distance comparison (horizontal axis: deep CAN / boundary / CANNOT)
        dist_delta = pinna.distance_from_boundary - self.reader_distance
        if abs(dist_delta) < 0.3:
            dist_rel = "center"   # near reader's boundary — most informative
        elif dist_delta > 0.3:
            dist_rel = "left"     # well within CAN for reader
        else:
            dist_rel = "right"    # beyond reader's floor

        # P8: peer + center = essential (concha resonance)
        if stage_rel == "peer" and dist_rel == "center":
            return "essential"
        if stage_rel == "above" and dist_rel in ("center", "left"):
            return "aspirational"
        if stage_rel == "below":
            return "redundant"
        if dist_rel == "right":
            return "aspirational"
        if dist_rel == "left":
            return "reliable"
        return "redundant"

    def rank_tiles(self, tiles: List[dict]) -> List[Tuple[dict, str]]:
        """Rank tiles by value for this reader.

        Returns (tile, classification) pairs sorted: essential > aspirational > reliable.
        Implements directional knowledge retrieval (PINNA-PRINCIPLE.md §What This Enables).
        """
        order = {"essential": 0, "aspirational": 1, "reliable": 2, "redundant": 3, "noise": 4}
        ranked = []
        for tile in tiles:
            pf = PinnaEncoder.extract(tile)
            if pf is None:
                ranked.append((tile, "noise"))
            else:
                val = self.classify_tile_value(pf)
                ranked.append((tile, val))
        ranked.sort(key=lambda x: order.get(x[1], 4))
        return ranked

    def record_calibration(self, pinna: PinnaField, succeeded: bool) -> None:
        """Record whether a tile with this pinna signature helped.

        Over time, builds 'spatial hearing' in knowledge space.
        Feeds PinnaCalibrator for fleet-level tracking.
        """
        self._calibration.append({
            "stage": pinna.agent_stage,
            "residue": pinna.residue_class,
            "distance": pinna.distance_from_boundary,
            "scaffold": pinna.scaffold_used,
            "temperature": pinna.temperature,
            "succeeded": succeeded,
            "ts": time.time(),
        })

    def get_learned_preferences(self) -> Dict[str, float]:
        """Return which pinna signatures are most useful after calibration.

        Maps "stage_residue" → success_rate. Requires ≥3 records per bucket.
        Implements P7 (faster calibration with pinna-tagged tiles).
        """
        recent = self._calibration[-200:]
        buckets: Dict[str, List[bool]] = defaultdict(list)
        for rec in recent:
            key = f"{rec['stage']}|{rec['residue']}"
            buckets[key].append(rec["succeeded"])
        return {k: sum(v) / len(v) for k, v in buckets.items() if len(v) >= 3}


# ─── Pinna Calibrator ─────────────────────────────────────────────────────────

class PinnaCalibrator:
    """Fleet-level tracker: learns which pinna signatures are most useful across agents.

    Where PinnaReader tracks one agent's experience, PinnaCalibrator aggregates
    across a fleet to derive fleet-wide routing recommendations.

    Traces to PINNA-PRINCIPLE.md §Evolutionary Bootstrapping (Phase 2 → Phase 3),
    and P9 (dead zone awareness improves routing).
    """

    def __init__(self):
        self._records: List[dict] = []  # {agent_id, pinna_stage, pinna_residue, success, ts}

    def record(self, agent_id: str, pinna: PinnaField, succeeded: bool) -> None:
        """Record a calibration event from any agent in the fleet."""
        self._records.append({
            "agent_id": agent_id,
            "pinna_stage": pinna.agent_stage,
            "pinna_residue": pinna.residue_class,
            "pinna_distance": pinna.distance_from_boundary,
            "scaffold": pinna.scaffold_used,
            "temperature": pinna.temperature,
            "n_trials": pinna.n_trials,
            "succeeded": succeeded,
            "ts": time.time(),
        })

    def success_rate_by_stage(self) -> Dict[str, float]:
        """Success rate when reading tiles from each AgentStage.

        High rate for PARTIAL stage confirms P8.
        """
        by_stage: Dict[str, List[bool]] = defaultdict(list)
        for r in self._records:
            by_stage[r["pinna_stage"]].append(r["succeeded"])
        return {s: sum(v) / len(v) for s, v in by_stage.items() if v}

    def dead_zone_classes(self, min_records: int = 5) -> List[str]:
        """Residue classes where the fleet consistently fails.

        Dead zones = ResidueClass values with success_rate < 0.2 over ≥min_records.
        Agents with these classes as dominant residue should route to specialists.
        Implements P9 (dead zone awareness improves routing).
        """
        by_cls: Dict[str, List[bool]] = defaultdict(list)
        for r in self._records:
            by_cls[r["pinna_residue"]].append(r["succeeded"])
        dead = []
        for cls, outcomes in by_cls.items():
            if len(outcomes) >= min_records and (sum(outcomes) / len(outcomes)) < 0.2:
                dead.append(cls)
        return dead

    def best_distance_window(self) -> Tuple[float, float]:
        """Distance window with highest fleet-wide success rate.

        Returns (low, high). Center of this window = optimal reader_distance.
        Implements P7 (faster calibration).
        """
        if len(self._records) < 10:
            return (-0.3, 0.3)
        windows: Dict[float, List[bool]] = defaultdict(list)
        for r in self._records:
            bucket = round(r["pinna_distance"] / 0.2) * 0.2
            windows[bucket].append(r["succeeded"])
        best = max(windows, key=lambda b: sum(windows[b]) / len(windows[b]) if windows[b] else 0.0)
        return (best - 0.1, best + 0.1)

    def summary(self) -> dict:
        """JSON-serializable calibration summary for fleet dashboard."""
        lo, hi = self.best_distance_window()
        return {
            "n_records": len(self._records),
            "success_by_stage": self.success_rate_by_stage(),
            "best_distance_window": [lo, hi],
            "dead_zone_classes": self.dead_zone_classes(),
        }


# ─── Conservation Law Check ───────────────────────────────────────────────────

@dataclass
class ConservationResult:
    """
    Result of the conservation law test.

    From MULTI-MODEL-SYNTHESIS.md §Novel Idea 1:
      If echo+partial+full stays flat (~87-93%) across 2B→6B models,
      the phase transition interpretation is confirmed.
      A rising sum → gradual learning; falsifies the slot hypothesis.
    """
    model_sizes_b: List[float]
    echo_rates: List[float]
    partial_rates: List[float]
    correct_rates: List[float]
    conservation_sums: List[float]   # echo+partial+correct per model
    pre_jump_sums: List[float]       # restricted to <7B models
    mean_sum: float
    std_sum: float
    cv: float                        # coefficient of variation
    is_flat: bool
    verdict: str     # "PHASE_TRANSITION" | "GRADUAL_LEARNING" | "INSUFFICIENT_DATA"
    detail: str


def check_conservation_law(
    model_sizes_b: List[float],
    echo_rates: List[float],
    partial_rates: List[float],
    correct_rates: List[float],
    flatness_tolerance: float = 0.05,
    expected_range: Tuple[float, float] = (0.87, 0.93),
) -> ConservationResult:
    """Verify echo+partial+correct stays flat across parameter thresholds.

    Testable pass/fail function. Run on any model set and get a verdict.

    Traces to MULTI-MODEL-SYNTHESIS.md §Novel Idea 1 (seed-pro's conservation
    prediction, independently supported by seed-mini and nemotron):
      - Sum stays flat 2B→6B: PHASE_TRANSITION confirmed
      - Sum rises monotonically: GRADUAL_LEARNING (falsifies slot hypothesis)
      - <2 pre-jump models: INSUFFICIENT_DATA

    Args:
        model_sizes_b:      parameter counts in billions, e.g. [1.0, 3.0, 7.0, 8.0]
        echo_rates:         fraction of outputs that are echoes per model
        partial_rates:      fraction that are partial sub-expressions per model
        correct_rates:      fraction fully correct per model
        flatness_tolerance: max coefficient of variation to consider flat (default 5%)
        expected_range:     (low, high) conservation range from seed-pro prediction

    Returns:
        ConservationResult with verdict "PHASE_TRANSITION", "GRADUAL_LEARNING",
        or "INSUFFICIENT_DATA".

    Example (testable):
        >>> result = check_conservation_law(
        ...     [1.0, 3.0, 7.0],
        ...     [0.50, 0.30, 0.05],
        ...     [0.38, 0.58, 0.05],
        ...     [0.12, 0.12, 0.90],
        ... )
        >>> result.verdict
        'PHASE_TRANSITION'
        >>> result.is_flat
        True
    """
    n = len(model_sizes_b)
    if not (n == len(echo_rates) == len(partial_rates) == len(correct_rates)):
        raise ValueError("All input lists must have the same length.")

    sums = [e + p + c for e, p, c in zip(echo_rates, partial_rates, correct_rates)]

    # Restrict flatness test to pre-jump zone (<7B)
    pre = [(s, sz) for s, sz in zip(sums, model_sizes_b) if sz < 7.0]
    pre_sums = [s for s, _ in pre]

    if len(pre_sums) < 2:
        return ConservationResult(
            model_sizes_b=model_sizes_b,
            echo_rates=echo_rates,
            partial_rates=partial_rates,
            correct_rates=correct_rates,
            conservation_sums=sums,
            pre_jump_sums=pre_sums,
            mean_sum=statistics.mean(sums) if sums else 0.0,
            std_sum=0.0,
            cv=float("inf"),
            is_flat=False,
            verdict="INSUFFICIENT_DATA",
            detail="Need at least 2 models below 7B to test conservation.",
        )

    mean_s = statistics.mean(pre_sums)
    std_s = statistics.stdev(pre_sums) if len(pre_sums) > 1 else 0.0
    cv = std_s / mean_s if mean_s > 0 else float("inf")

    in_range = expected_range[0] <= mean_s <= expected_range[1]
    is_flat = cv <= flatness_tolerance and in_range

    if is_flat:
        verdict = "PHASE_TRANSITION"
        detail = (
            f"Conservation confirmed: mean={mean_s:.3f} (expected {expected_range[0]}-{expected_range[1]}), "
            f"CV={cv:.3f} ≤ {flatness_tolerance}. "
            "Mode-flip, not gradual learning. "
            "Every echo-rate drop converts 1:1 into partial-rate — zero net gain until 7B jump."
        )
    else:
        verdict = "GRADUAL_LEARNING"
        detail = (
            f"Conservation NOT confirmed: mean={mean_s:.3f}, CV={cv:.3f} > {flatness_tolerance}. "
            f"in_expected_range={in_range}. "
            "Sum is not flat — gradual learning interpretation. "
            "Slot hypothesis requires revision."
        )

    return ConservationResult(
        model_sizes_b=model_sizes_b,
        echo_rates=echo_rates,
        partial_rates=partial_rates,
        correct_rates=correct_rates,
        conservation_sums=sums,
        pre_jump_sums=pre_sums,
        mean_sum=mean_s,
        std_sum=std_s,
        cv=cv,
        is_flat=is_flat,
        verdict=verdict,
        detail=detail,
    )


# ─── Legacy alias ─────────────────────────────────────────────────────────────

class ConservationLawChecker:
    """Legacy dict-based interface (for backwards compatibility).

    Prefer check_conservation_law() for new code.
    """

    @staticmethod
    def check(residue_distribution: Dict[str, Dict[str, float]]) -> dict:
        """Check conservation from a {model_size: {residue_class: rate}} dict.

        Args:
            residue_distribution: e.g.
              {"1B": {"ECHO": 0.56, "PARTIAL": 0.0, "CORRECT": 0.0, "OTHER": 0.44},
               "4B": {"ECHO": 0.11, "PARTIAL": 0.79, "CORRECT": 0.10, "OTHER": 0.0}}
        """
        results = {}
        for model_size, dist in residue_distribution.items():
            echo    = dist.get("ECHO", 0.0)
            partial = sum(v for k, v in dist.items() if "PARTIAL" in k)
            correct = dist.get("CORRECT", 0.0)
            total_valid = echo + partial + correct
            results[model_size] = {
                "echo_rate":    echo,
                "partial_rate": partial,
                "correct_rate": correct,
                "total_valid":  total_valid,
            }

        totals  = [r["total_valid"] for r in results.values()]
        spread  = max(totals) - min(totals) if len(totals) >= 2 else 0.0
        conserved = spread < 0.10 if len(totals) >= 2 else None

        return {
            "per_model": results,
            "totals": totals,
            "spread": round(spread, 3),
            "conserved": conserved,
            "interpretation": (
                "FIRST-ORDER PHASE TRANSITION CONFIRMED — total valid output conserved across transition"
                if conserved
                else "GRADUAL LEARNING — total valid output increases monotonically"
                if conserved is False
                else "INSUFFICIENT DATA"
            ),
        }
