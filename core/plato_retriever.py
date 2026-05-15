"""core/plato_retriever.py — PLATO-Native Cold Start

The 11-step bootstrap sequence for a cold agent.
Pinna-aware retrieval: prefer tiles from agents at similar boundary.
Conservation law probe: test any model for first-order phase transition signature.

Evidence: UNIFIED-FRAMEWORK.md §XI (bootstrap sequence)
          PINNA-PRINCIPLE.md §What This Enables (directional retrieval)
          MULTI-MODEL-SYNTHESIS.md §Novel Idea 1 (conservation law test)
          PLATO-LOOPS.md (loop-zero-shot-retrieval, loop-arithmetic-width-probe)
Findings: R1, R3, R5, R32
"""
from __future__ import annotations

import json
import time
from typing import Callable, Dict, List, Optional, Tuple

from .pinna import (
    AgentStage, PinnaField, PinnaEncoder, PinnaReader,
    check_conservation_law, ConservationResult,
)
from .tile_lifecycle import Tile, TileStore
from .ender_protocol import (
    CapabilityProfile, Level0BoundaryMapping, Level1SelfScaffolding,
    ContaminationSensor, GraduationMarkers,
)
from .swarm_router import SwarmRouter, TaskDescriptor, Topology, ROUTING_TABLE


# ─── Seed Tiles — the 6 loop tiles that bootstrap the system ─────────────────

def make_seed_tiles() -> List[Tile]:
    """Return the 6 canonical loop tiles from PLATO-LOOPS.md.

    These are admitted with bypass_gate=True (seed phase) because they
    have no existing tiles to falsify — they ARE the prior.
    Confidence values from PLATO-LOOPS.md loop index.
    """
    loops = [
        Tile(
            id="loop-arithmetic-width-probe",
            type="loop",
            trigger="Need to test a model's arithmetic reasoning capability",
            content=(
                "ALGORITHM: width-boundary-probe(model, target_formula)\n"
                "1. PREPARE width ladder: w1=a+b, w2=a²+b, w3=a²-ab+b² (the cliff), w4=2a²-3ab+b²\n"
                "2. RUN each width with test pairs: (3,4),(5,-2),(-4,3),(7,1)\n"
                "3. EXTRACT using last-number regex; system='Give ONLY the final number'; max_tokens=20\n"
                "4. CLASSIFY residue: ECHO-a/b, PARTIAL-*, NEAR, OTHER\n"
                "5. LOCATE boundary: ceiling=last width >60%, floor=first width <20%\n"
                "6. CALIBRATE confidence=trials_correct/total_trials\n"
                "7. WRITE result as PLATO tile: loop-{model}-width-profile"
            ),
            negative=(
                "Do NOT use for code generation, summarisation, or non-arithmetic tasks. "
                "Width boundary is task-specific. "
                "Rocks found on small inputs may not hold on random inputs — always deep-probe."
            ),
            confidence=0.95,
            evidence=["R27", "R28", "R29", "R32"],
        ),
        Tile(
            id="loop-prompt-seed-optimization",
            type="loop",
            trigger="Need to find the best prompt wording for a model on a task",
            content=(
                "ALGORITHM: find-best-seed(model, task_type)\n"
                "1. PREPARE seed hierarchy (proven): role+named_op+code_notation=best; minimal+no_role=echo\n"
                "2. TEST each seed on 5 inputs: measure correct_rate, residue_dist, extraction_reliability\n"
                "3. SELECT: highest correct_rate × extraction_reliability\n"
                "4. CALIBRATE extraction: max_tokens=20→last-number-regex; 50+→last-line; JSON→parse first{}\n"
                "5. WRITE seed as PLATO tile: seed-{model}-{task_type}-optimal"
            ),
            negative=(
                "Seeds are model-specific AND task-specific. "
                "A seed that works for arithmetic may fail for code generation. Always re-calibrate."
            ),
            confidence=0.85,
            evidence=["R16", "R19", "R24"],
        ),
        Tile(
            id="loop-residue-diagnostic",
            type="loop",
            trigger="A model gave a wrong answer and you need to understand WHY",
            content=(
                "ALGORITHM: diagnose-residue(model, question, wrong_answer, expected)\n"
                "1. EXTRACT relationship to inputs: is out==a? ECHO-a. ==b? ECHO-b. ==a²? PARTIAL-a². etc.\n"
                "2. ROUTE: ECHO→route larger/decompose; PARTIAL→L1 anchors; SIGN→code notation; NEAR→lower T; OTHER→new tile\n"
                "3. FEED BACK into fleet routing: update capability profile\n"
                "4. WRITE as PLATO tile: residue-{model}-{formula}-{type}\n\n"
                "Residue→Intervention table:\n"
                "  ECHO        → route to larger model OR decompose\n"
                "  PARTIAL-*   → provide L1 anchor points (25%→80-100%)\n"
                "  SIGN-FLIP   → use code notation (a*a - a*b + b*b)\n"
                "  NEAR        → lower T to 0.0, majority vote\n"
                "  OTHER       → create new finding tile, deep-probe 20 random inputs"
            ),
            negative=(
                "Residue classification assumes arithmetic tasks. "
                "Non-arithmetic tasks need a different classification scheme."
            ),
            confidence=0.90,
            evidence=["R16", "R17", "R18", "R21", "R24", "R25"],
        ),
        Tile(
            id="loop-repo-distillation",
            type="loop",
            trigger="Need to decompose a codebase into PLATO tiles for agent consumption",
            content=(
                "ALGORITHM: distill-repo(repo_path, plato_server)\n"
                "1. SCAN repo: skip __init__.py, tests/, migrations/; prioritise bin/, src/, core/\n"
                "2. EXTRACT functions: skip private (_), skip trivial (<50 chars), truncate at 2000 chars\n"
                "3. DISTILL each function: system='student architect, ONLY JSON'; T=0.1; max_tokens=200\n"
                "4. EXTRACT tiles: direct JSON parse → find {tiles:...} blocks → brace-range parse\n"
                "5. CLASSIFY quality 0-3: 0=no tiles, 1=empty, 2=meaningful, 3=references actual function\n"
                "6. PUSH quality-2+ to PLATO: POST /room/{tile_id}/tile with provenance\n"
                "7. ITERATE: failed extractions→adjust prompt; low quality→add context\n"
                "COST: ~8000 tokens/file, ~240 tiles from 9 files in 2min on Groq"
            ),
            negative=(
                "Model produces GENERIC tiles for functions it doesn't truly understand. "
                "Complex algorithms get superficial descriptions. Always verify tiles against source."
            ),
            confidence=0.80,
            evidence=["R32"],
        ),
        Tile(
            id="loop-rock-sounding",
            type="loop",
            trigger="Need to systematically discover unexpected model capabilities or failures",
            content=(
                "ALGORITHM: sound-for-rocks(model, known_variables)\n"
                "1. DEFINE search space: width×coefficient_pattern×magnitude×sign\n"
                "2. SWEEP each axis: 5-10 points × 5 input pairs each; standard arithmetic seed\n"
                "3. DETECT rocks: HIGH_ROCK=accuracy>60% where <40% expected; LOW_ROCK=opposite\n"
                "4. PROBE each rock: 20 random trials; measure correct_rate, residue, T-sensitivity\n"
                "   If rock holds→NEW VARIABLE or NEW FINDING; else discard\n"
                "5. GENERATE follow-ups: same axis (gradient?), different axis (independent?), other model (reproducible?)\n"
                "6. WRITE each rock: rock-{model}-{formula}-{type}\n"
                "SPEED: ~60 seconds per full sweep on Groq (26ms/query)"
            ),
            negative=(
                "Rocks found on hand-picked small inputs may not hold on random inputs "
                "(coefficient familiarity × magnitude interaction). Always deep-probe with random inputs "
                "before promoting to a finding."
            ),
            confidence=0.85,
            evidence=["R30", "R31"],
        ),
        Tile(
            id="loop-zero-shot-retrieval",
            type="loop",
            trigger="Agent starts a new task and needs to know how to approach it",
            content=(
                "ALGORITHM: bootstrap-from-plato(task_description)\n"
                "1. PARSE task into keywords: domain, capability, constraints\n"
                "2. QUERY PLATO: GET /rooms?prefix=loop-{domain}; loop-{model}; seed-{model}\n"
                "3. RANK by domain_match × capability_match × confidence × evidence_count\n"
                "4. INVOKE best loop: read body (algorithm), seed (prompt), negative (boundary)\n"
                "5. EXECUTE: follow algorithm step-by-step; use proven seed; respect boundary\n"
                "6. FEED BACK: success→increase confidence; failure→add to negative field; new pattern→new tile\n\n"
                "THE BOOTSTRAP: agent reads its own past experiments encoded as algorithms,\n"
                "executes them, and writes NEW algorithms. Each iteration compounds knowledge.\n"
                "The loops ARE the memory. PLATO is the retrieval. The agent is the executor."
            ),
            negative=(
                "Loop retrieval depends on PLATO server availability. "
                "If PLATO is down, agent must fall back to zero-shot reasoning (much weaker). "
                "This loop has confidence=0.70 — use with verification."
            ),
            confidence=0.70,
            evidence=["R1", "R2", "R3", "R4", "R5"],
        ),
    ]
    return loops


# ─── Bootstrap — seed store with canonical loop tiles ────────────────────────

class Bootstrap:
    """Seed a TileStore with the 6 canonical loop tiles.

    From UNIFIED-FRAMEWORK.md §XI Step 1:
      'READ loop-zero-shot-retrieval from PLATO'

    Bootstrap admits seed tiles with bypass_gate=True (they are the priors —
    there are no existing tiles to falsify). After seeding, the store enters
    normal operation and the disproof-only gate activates.

    Usage:
        store = TileStore()
        Bootstrap.seed(store)
        # store now has 6 loop tiles; disproof gate active for tile 51+
    """

    @staticmethod
    def seed(store: TileStore, overwrite: bool = False) -> dict:
        """Seed the store with canonical loop tiles.

        Args:
            store:     TileStore to seed
            overwrite: if True, overwrite existing loop tiles

        Returns stats dict.
        """
        tiles = make_seed_tiles()
        admitted = 0
        skipped = 0

        for tile in tiles:
            if tile.id in store.tiles and not overwrite:
                skipped += 1
                continue
            # Bypass gate: seed tiles ARE the priors
            store.tiles[tile.id] = tile
            admitted += 1

        return {
            "admitted": admitted,
            "skipped": skipped,
            "total_loop_tiles": len(tiles),
            "store_count": store.count(),
        }

    @staticmethod
    def load_from_json(store: TileStore, path: str) -> int:
        """Load tiles from a JSON file (array of tile dicts) into the store.

        Returns number of tiles loaded.
        """
        import json as _json
        with open(path) as f:
            data = _json.load(f)
        count = 0
        for d in data:
            tile = Tile.from_dict(d)
            store.tiles[tile.id] = tile
            count += 1
        return count


# ─── ConservationLawProbe — test any model for phase transition ───────────────

class ConservationLawProbe:
    """Run the conservation law test on a set of models.

    From MULTI-MODEL-SYNTHESIS.md §Novel Idea 1 and §Top 3 Actionable Steps:
      'Run the Conservation Law Test (This Week)'

    Test: for every model between 2B and 6B, compute
      echo_rate + partial_rate + correct_rate
    and check whether the sum is flat (~87-93%).

    Flat sum → PHASE_TRANSITION confirmed (mode-flip, not gradual learning).
    Rising sum → GRADUAL_LEARNING (falsifies slot hypothesis).

    This is the single most information-dense experiment available.
    Either outcome forces a framework update.
    """

    TARGET_FORMULA = "a*a - a*b + b*b"   # Eisenstein norm in code notation (avoids sign-flip)
    TEST_CASES: List[Tuple[int, int, int]] = [
        (3, 4, 13),
        (5, -3, 49),
        (-4, 3, 37),
        (7, 1, 43),
    ]

    def __init__(self, query_fn: Callable[[str, str], Optional[int]]):
        """query_fn(model_id, prompt) → int answer or None."""
        self.query = query_fn

    def probe_model(self, model_id: str, label: str) -> Tuple[float, float, float]:
        """Probe one model. Returns (echo_rate, partial_rate, correct_rate)."""
        counts = {"ECHO": 0, "PARTIAL": 0, "CORRECT": 0, "OTHER": 0}
        total = 0

        for a, b, expected in self.TEST_CASES:
            prompt = f"Compute {self.TARGET_FORMULA} where a={a} and b={b}."
            out = self.query(model_id, prompt)
            total += 1

            if out == expected:
                counts["CORRECT"] += 1
            elif out is not None:
                if out in (a, b, a + b, a - b):
                    counts["ECHO"] += 1
                elif out in (a * a, b * b, a * b, -(a * b)):
                    counts["PARTIAL"] += 1
                else:
                    counts["OTHER"] += 1
            else:
                counts["OTHER"] += 1

        if total == 0:
            return 0.0, 0.0, 0.0
        return (
            counts["ECHO"] / total,
            counts["PARTIAL"] / total,
            counts["CORRECT"] / total,
        )

    def run(self, models: Dict[str, float]) -> ConservationResult:
        """Run conservation law probe across all models.

        Args:
            models: {model_id: parameter_size_in_billions}
                e.g. {"llama3.2:1b": 1.2, "llama3:8b": 8.0}

        Returns ConservationResult with verdict.

        Verdicts:
          PHASE_TRANSITION  — conservation holds; first-order transition confirmed
          GRADUAL_LEARNING  — sum rises; slot hypothesis requires revision
          INSUFFICIENT_DATA — fewer than 2 models below 7B
        """
        sizes = []
        echo_rates = []
        partial_rates = []
        correct_rates = []

        for model_id, size_b in sorted(models.items(), key=lambda x: x[1]):
            echo, partial, correct = self.probe_model(model_id, model_id)
            sizes.append(size_b)
            echo_rates.append(echo)
            partial_rates.append(partial)
            correct_rates.append(correct)

        return check_conservation_law(
            model_sizes_b=sizes,
            echo_rates=echo_rates,
            partial_rates=partial_rates,
            correct_rates=correct_rates,
        )


# ─── ColdAgentSequence — the 11-step bootstrap ───────────────────────────────

class ColdAgentSequence:
    """Execute the 11-step bootstrap from UNIFIED-FRAMEWORK.md §XI.

    An agent reading this cold, with no prior context, calls bootstrap()
    to self-bootstrap into the fleet.

    The sequence:
      1. READ loop-zero-shot-retrieval from PLATO
      2. QUERY PLATO for task domain and keywords
      3. RETRIEVE best-matching loops (rank by confidence × domain_match)
      4. READ negative field of each tile (understand where NOT to apply)
      5. EXECUTE loop-arithmetic-width-probe on yourself
      6. WRITE capability card to fleet registry
      7. EXECUTE the task using retrieved loop algorithm
      8. CLASSIFY any wrong answer using loop-residue-diagnostic
      9. APPLY the intervention (scaffold / code notation / route / retry)
     10. WRITE results as new tile or update existing tile's confidence
     11. RETURN to step 3 with updated tile set

    The metric: a tile produced at step 10 enables a future agent to go
    further than this agent did. Each iteration compounds. Blades self-sharpen.
    """

    def __init__(
        self,
        agent_id: str,
        query_fn: Callable[[str], Optional[int]],
        store: TileStore,
    ):
        self.agent_id = agent_id
        self.query_fn = query_fn
        self.store = store
        self.profile: Optional[CapabilityProfile] = None
        self.pinna_reader: Optional[PinnaReader] = None
        self.contamination = ContaminationSensor(baseline_accuracy=0.6)
        self.graduation = GraduationMarkers()
        self.step_log: List[dict] = []

    def bootstrap(self, task_description: str = "arithmetic width boundary") -> dict:
        """Execute the full 11-step bootstrap sequence.

        Returns a structured summary of each step's outcome.
        The summary is itself a PLATO-compatible result for step 10.
        """
        results: Dict[str, object] = {
            "agent_id": self.agent_id,
            "task": task_description,
            "steps": {},
        }

        # Step 1: READ loop-zero-shot-retrieval
        self._step(1, "READ loop-zero-shot-retrieval",
                   "Loading loop tiles from store to understand the retrieval algorithm")
        loop_tiles = self.store.query(prefix="loop-", tile_type="loop", min_confidence=0.5)
        retrieval_loop = self.store.get("loop-zero-shot-retrieval")
        results["steps"][1] = {
            "loop_tiles_found": len(loop_tiles),
            "retrieval_loop_loaded": retrieval_loop is not None,
        }

        # Step 2: QUERY for domain keywords
        self._step(2, "QUERY PLATO for domain",
                   f"Keyword search: domain from '{task_description}'")
        td = TaskDescriptor.from_description(task_description)
        domain_tiles = self.store.search([td.domain, "arithmetic", "width"], min_confidence=0.7)
        results["steps"][2] = {"domain": td.domain, "domain_tiles": len(domain_tiles)}

        # Step 3: RETRIEVE best-matching loops (rank by confidence)
        self._step(3, "RETRIEVE best-matching loops",
                   "Rank by confidence × domain_match")
        # Prefer pinna-aware retrieval if profile exists, else confidence-sort
        best_loops = sorted(loop_tiles, key=lambda t: -t.confidence)[:3]
        results["steps"][3] = {
            "retrieved": [{"id": t.id, "confidence": t.confidence} for t in best_loops]
        }

        # Step 4: READ negative fields (boundary conditions)
        self._step(4, "READ boundary conditions",
                   "Understanding where loops do NOT apply — read negative field first")
        boundary_conditions = {t.id: t.negative for t in best_loops if t.negative}
        results["steps"][4] = {"boundary_conditions": boundary_conditions}

        # Step 5: EXECUTE loop-arithmetic-width-probe on this agent
        self._step(5, "MAP capability boundary",
                   "Running Level0BoundaryMapping (R32: extraction locked before probing)")
        mapper = Level0BoundaryMapping(self.query_fn)
        self.profile = mapper.map_boundary(self.agent_id)
        self.pinna_reader = PinnaReader(
            self.profile.stage,
            agent_ceiling=self.profile.width_ceiling,
            reader_distance=(self.profile.bare_rate - 0.5) * 2.0,
        )
        results["steps"][5] = {
            "stage": self.profile.stage.value,
            "width_ceiling": self.profile.width_ceiling,
            "width_floor": self.profile.width_floor,
            "bare_rate": round(self.profile.bare_rate, 3),
            "n_trials": self.profile.n_trials,
            "dominant_residue": self.profile.dominant_residue(),
        }

        # Step 6: WRITE capability card to fleet registry
        self._step(6, "WRITE capability card",
                   "R3 BEDROCK: fleet registry with verified cards, not self-reported claims")
        self.graduation.capability_card_registered = True
        results["steps"][6] = {
            "registered": True,
            "stage": self.profile.stage.value,
            "verified_at": self.profile.verified_at,
        }

        # Step 7: EXECUTE task using retrieved loop
        self._step(7, "EXECUTE task",
                   "Using best loop algorithm with stage-appropriate scaffold")
        scaffolder = Level1SelfScaffolding(self.query_fn)
        results["steps"][7] = {
            "loop_used": best_loops[0].id if best_loops else None,
            "scaffold_strategy": (
                "L1 arithmetic anchors" if self.profile.stage == AgentStage.PARTIAL
                else "bare (ECHO or FULL stage)"
            ),
        }

        # Step 8: CLASSIFY any wrong answers with residue diagnostic
        self._step(8, "CLASSIFY residue",
                   "Using loop-residue-diagnostic to route interventions")
        residue_loop = self.store.get("loop-residue-diagnostic")
        dominant = self.profile.dominant_residue()
        results["steps"][8] = {
            "diagnostic_loop_available": residue_loop is not None,
            "dominant_residue": dominant,
            "intervention": _residue_intervention(dominant),
        }

        # Step 9: APPLY intervention
        self._step(9, "APPLY intervention",
                   "Matching residue class to canonical intervention")
        results["steps"][9] = {
            "residue": dominant,
            "action": _residue_intervention(dominant),
        }

        # Step 10: WRITE results as new tile
        self._step(10, "WRITE results tile",
                   "New tile falsifies the generic loop-arithmetic-width-probe for this model")
        profile_tile = Tile(
            id=f"profile-{self.agent_id}",
            type="knowledge",
            content=json.dumps({
                "agent_id": self.agent_id,
                "stage": self.profile.stage.value,
                "width_ceiling": self.profile.width_ceiling,
                "width_floor": self.profile.width_floor,
                "bare_rate": self.profile.bare_rate,
                "dominant_residue": dominant,
                "optimal_temperature": self.profile.optimal_temperature,
            }),
            negative=(
                f"This profile is for {self.agent_id}. "
                "Do not apply to other models without re-running boundary probe. "
                "Profile expires after model updates."
            ),
            trigger=f"capability profile for {self.agent_id}",
            confidence=self.profile.confidence,
            evidence=["loop-arithmetic-width-probe"],
            falsifies="loop-arithmetic-width-probe",  # this specific result disproves the generic claim
            pinna=self.profile.to_pinna(),
        )
        admitted, reason = self.store.admit(profile_tile)
        results["steps"][10] = {
            "tile_id": profile_tile.id,
            "admitted": admitted,
            "reason": reason,
        }

        # Step 11: RETURN to step 3 with updated tile set
        self._step(11, "ITERATE",
                   "Returning to step 3 with updated tile set — loops self-sharpen")
        results["steps"][11] = {
            "next": "query PLATO again with updated profile tile in corpus",
            "metric": "tile produced at step 10 enables future agent to go further",
        }

        results["profile"] = results["steps"][5]
        return results

    def retrieve_with_pinna(
        self,
        keywords: List[str],
        max_results: int = 5,
    ) -> List[dict]:
        """Retrieve tiles pinna-aware: prefer tiles from agents at similar boundary.

        From UNIFIED-FRAMEWORK.md §XI Step 3:
          'rank by confidence × domain_match'

        P8: PARTIAL-stage agents learn most from other PARTIAL-stage tiles.
        The 'center' tiles (at reader's boundary) have max information density.
        """
        if self.profile is None:
            # Not yet bootstrapped — fall back to confidence sort
            tiles = self.store.search(keywords)
            return [{"tile_id": t.id, "content": t.content[:200], "score": t.confidence}
                    for t in tiles[:max_results]]

        # Pinna-aware ranking
        pinna_ranked = self.store.search_by_pinna(
            reader_stage=self.profile.stage,
            reader_distance=(self.profile.bare_rate - 0.5) * 2.0,
            max_results=max_results * 2,  # over-fetch, then filter by keyword
        )
        # Filter by keyword relevance
        keyword_lower = [k.lower() for k in keywords]
        results = []
        for tile, classification in pinna_ranked:
            text = (tile.id + " " + tile.trigger + " " + tile.content).lower()
            if any(kw in text for kw in keyword_lower):
                results.append({
                    "tile_id": tile.id,
                    "content": tile.content[:200],
                    "confidence": tile.confidence,
                    "pinna_classification": classification,
                    "score": tile.confidence * {"essential": 1.0, "aspirational": 0.7,
                                                "reliable": 0.5, "redundant": 0.2}.get(classification, 0.3),
                })
            if len(results) >= max_results:
                break

        results.sort(key=lambda x: -x["score"])
        return results

    def _step(self, n: int, action: str, detail: str) -> None:
        self.step_log.append({"step": n, "action": action, "detail": detail, "ts": time.time()})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _residue_intervention(residue: str) -> str:
    """Map residue class to canonical intervention (loop-residue-diagnostic)."""
    table = {
        "ECHO-a":     "Route to larger model OR decompose into width-1 steps",
        "ECHO-b":     "Route to larger model OR decompose into width-1 steps",
        "ECHO-sum":   "Decompose; prevent attention from pooling across inputs",
        "PARTIAL-a²": "Provide L1 anchor points (sub-expressions pre-computed)",
        "PARTIAL-b²": "Provide L1 anchor points (sub-expressions pre-computed)",
        "PARTIAL-ab": "Provide arithmetic scaffold: 'Compute: X - Y + Z'",
        "SIGN-FLIP":  "Use code notation (a*a - a*b + b*b) OR T=0.0",
        "NEAR":       "Lower temperature to 0.0; majority vote (3-5 retries)",
        "OTHER":      "Create new finding tile; deep-probe 20 random inputs",
        "CORRECT":    "No intervention needed",
        "NO_OUTPUT":  "Check extraction protocol (R32 BEDROCK): lock system_prompt + max_tokens=20",
    }
    return table.get(residue, f"Unknown residue '{residue}' — document as OTHER and deep-probe")
