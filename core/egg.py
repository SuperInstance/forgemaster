"""core/egg.py — Biological Developmental Stack for Fleet Incubation.

The egg is a complete development environment: yolk (food), shell (protection),
selection channels (adaptation at three speeds), and viral I2I delivery.

Biological parallel is exact:
  - YOLK:   Pre-assembled nutrients the embryo can't make itself.
            Every antibody, nutrient ratio, and hormone represents accumulated
            generational learning about what development needs.
  - SHELL:  Not a wall — a semipermeable membrane.
            Gas exchange yes, pathogens no. Breathes but doesn't get infected.
  - SELECTION: Three-speed adaptation system:
      SLOW:   DNA (generations) — model training, architectural change
      MEDIUM: Epigenetics (per-gen) — servo parameters, constraint tuning
      FAST:   Gut biome (intra-gen) — tile store contents, real-time adaptation
  - VIRUS:  The second mouse. Follow bold mice instead of searching.
            Injects instructions in the cell's own language.
            The cell does all the work.

Integrates with:
  - core.tile_lifecycle (TileStore, Tile) — knowledge substrate
  - core.servo_mind (ServoMind) — adaptive feedback
  - core.embryo (Embryo, DevelopmentalStage) — developmental pipeline
  - core.mitochondria (IncubatorEnergy) — model routing
"""
from __future__ import annotations

import time
import hashlib
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict


# ─── Yolk — Pre-assembled nutrients from generational wisdom ──────────────────

class Yolk:
    """Formula food supply crafted by generational understanding.

    The egg provides pre-assembled nutrients the embryo can't make itself.
    Every antibody, nutrient ratio, and hormone represents millions of years
    of evolutionary learning about what development needs.

    In fleet terms: the yolk is the curated knowledge pack that boots
    a new agent with accumulated fleet wisdom, without requiring the
    agent to re-derive everything from scratch.
    """

    def __init__(self):
        self.formula: Dict[str, Any] = {}        # pre-seeded tiles/knowledge
        self.antibodies: List[dict] = []          # immune knowledge (known bad patterns)
        self.hormones: Dict[str, dict] = {}       # developmental signals

        # Stage-appropriate nutrient maps: which knowledge to deliver when
        self._stage_nutrition = {
            "zygote": ["antibodies", "core_principles"],
            "cleavage": ["basic_patterns", "fragment_templates"],
            "blastula": ["insight_methods", "fitness_scoring"],
            "gastrula": ["classification_rules", "convergence_signals"],
            "organogenesis": ["integration_patterns", "module_templates"],
            "fledge": ["validation_rules", "flight_checks"],
        }

        # Antibody registry: known-bad patterns with evidence
        self._antibody_catalog: Dict[str, dict] = {
            "tile_cancer": {
                "pattern": "accumulation_without_mortality",
                "evidence": "seed-pro predicted cancer at ~1127 tiles",
                "action": "activate_mortality_sweep",
                "severity": 0.85,
            },
            "confidence_inflation": {
                "pattern": "high_confidence_low_win_rate",
                "evidence": "R16 echo rate finding",
                "action": "recalibrate_confidence",
                "severity": 0.7,
            },
            "vocabulary_wall": {
                "pattern": "model_uses_wrong_arithmetic",
                "evidence": "GLM models fail arithmetic pre-computation",
                "action": "pre_compute_arithmetic",
                "severity": 0.9,
            },
            "loop_misapplication": {
                "pattern": "loop_applied_outside_boundary",
                "evidence": "UNIFIED-FRAMEWORK.md §VI",
                "action": "read_negative_field_first",
                "severity": 0.75,
            },
        }

    def craft(self, generational_knowledge: dict) -> dict:
        """Assemble formula from accumulated generational wisdom.

        Takes the win/loss history from previous runs and distills it
        into the minimum knowledge the embryo needs to start developing.

        Args:
            generational_knowledge: dict with keys like:
                - "win_history": list of (tile_id, outcome) tuples
                - "architectural_decisions": dict of what worked
                - "failure_modes": list of known failure patterns
                - "fleet_findings": list of validated findings

        Returns:
            The assembled formula dict (also stored in self.formula).
        """
        formula: Dict[str, Any] = {}

        # 1. Distill antibodies from failure modes
        failures = generational_knowledge.get("failure_modes", [])
        for failure in failures:
            pattern = failure.get("pattern", str(failure)) if isinstance(failure, dict) else str(failure)
            # Match against catalog or create generic antibody
            matched = False
            for ab_name, ab_data in self._antibody_catalog.items():
                if ab_data["pattern"] in pattern.lower() or pattern.lower() in ab_data["pattern"]:
                    self.antibodies.append({
                        "name": ab_name,
                        **ab_data,
                        "source": "generational",
                    })
                    matched = True
                    break
            if not matched:
                self.antibodies.append({
                    "name": f"custom_{hashlib.md5(pattern.encode()).hexdigest()[:8]}",
                    "pattern": pattern,
                    "evidence": "generational_failure",
                    "action": "avoid",
                    "severity": failure.get("severity", 0.5) if isinstance(failure, dict) else 0.5,
                    "source": "generational",
                })
        formula["antibodies"] = self.antibodies

        # 2. Distill core principles from architectural decisions
        decisions = generational_knowledge.get("architectural_decisions", {})
        core_principles = []
        for decision, outcome in decisions.items():
            if isinstance(outcome, dict):
                if outcome.get("worked", True):
                    core_principles.append({
                        "principle": decision,
                        "evidence": outcome.get("evidence", ""),
                        "confidence": outcome.get("confidence", 0.7),
                    })
                else:
                    # Failed decision → antibody
                    self.antibodies.append({
                        "name": f"anti_{decision[:20]}",
                        "pattern": decision,
                        "evidence": f"Failed: {outcome.get('reason', 'unknown')}",
                        "action": "avoid",
                        "severity": 0.6,
                        "source": "architectural",
                    })
            elif isinstance(outcome, bool) and outcome:
                core_principles.append({
                    "principle": decision,
                    "evidence": "generational_validation",
                    "confidence": 0.7,
                })
        formula["core_principles"] = core_principles

        # 3. Extract high-value tiles from win history
        win_history = generational_knowledge.get("win_history", [])
        high_value = [
            (tid, outcome) for tid, outcome in win_history
            if outcome is True or (isinstance(outcome, float) and outcome > 0.7)
        ]
        formula["high_value_tiles"] = [tid for tid, _ in high_value[:50]]

        # 4. Extract validated findings
        findings = generational_knowledge.get("fleet_findings", [])
        formula["validated_findings"] = [
            f for f in findings
            if isinstance(f, dict) and f.get("status") == "BEDROCK"
        ]

        # 5. Set developmental hormones based on generational context
        mortality = 0.15  # default
        if len(win_history) > 100:
            # Calculate historical win rate to tune parameters
            wins = sum(1 for _, o in win_history if o is True or (isinstance(o, float) and o > 0.5))
            wr = wins / len(win_history)
            if wr < 0.4:
                mortality = 0.25  # tough environment, prune harder
            elif wr > 0.7:
                mortality = 0.10  # healthy environment, gentle pruning

        self.hormones = {
            "mortality_signal": {
                "stage": "all",
                "action": "set_mortality_rate",
                "value": mortality,
                "source": "generational_win_rate",
            },
            "confidence_signal": {
                "stage": "gastrula",
                "action": "set_confidence_floor",
                "value": 0.3,
                "source": "default",
            },
            "development_pace": {
                "stage": "cleavage",
                "action": "set_fragment_count",
                "value": 12,
                "source": "default",
            },
        }

        # Adjust hormones based on findings
        for finding in findings:
            if isinstance(finding, dict):
                fid = finding.get("id", "")
                if fid == "R1":
                    # DATA > instructions — prioritize data tiles
                    self.hormones["data_priority"] = {
                        "stage": "all",
                        "action": "prioritize_data_tiles",
                        "value": True,
                        "source": "R1_BEDROCK",
                    }
                elif fid == "R16":
                    # Echo rate — watch for echoing
                    self.hormones["echo_awareness"] = {
                        "stage": "blastula",
                        "action": "check_for_echoing",
                        "value": True,
                        "source": "R16",
                    }

        formula["hormones"] = self.hormones

        self.formula = formula
        return formula

    def feed(self, embryo_stage: str) -> list:
        """Deliver age-appropriate nutrition.

        Early stages get simple tiles (antibodies first — immune before organs).
        Later stages get complex ones (integration patterns, validation rules).

        Like real yolk: antibodies first (immune before organs), then nutrients.

        Args:
            embryo_stage: Current developmental stage (e.g. "zygote", "cleavage").

        Returns:
            List of nutrient dicts appropriate for the stage.
        """
        nutrients: List[dict] = []
        stage_key = embryo_stage.lower()

        # Always deliver antibodies first (immune system before organs)
        if self.antibodies:
            nutrients.append({
                "type": "antibodies",
                "content": self.antibodies,
                "stage": "all",
                "priority": "critical",
                "description": f"{len(self.antibodies)} immune patterns (known-bad to avoid)",
            })

        # Stage-appropriate nutrients
        nutrient_types = self._stage_nutrition.get(stage_key, [])

        for ntype in nutrient_types:
            if ntype == "core_principles" and "core_principles" in self.formula:
                nutrients.append({
                    "type": "core_principles",
                    "content": self.formula["core_principles"],
                    "stage": stage_key,
                    "priority": "high",
                    "description": "Validated principles from generational wins",
                })

            elif ntype == "basic_patterns" and "high_value_tiles" in self.formula:
                # Only the first 10 tiles for early stages
                tiles = self.formula["high_value_tiles"][:10]
                nutrients.append({
                    "type": "basic_patterns",
                    "content": tiles,
                    "stage": stage_key,
                    "priority": "high",
                    "description": f"Top {len(tiles)} high-value tiles for bootstrap",
                })

            elif ntype == "insight_methods" and "validated_findings" in self.formula:
                nutrients.append({
                    "type": "insight_methods",
                    "content": self.formula["validated_findings"],
                    "stage": stage_key,
                    "priority": "medium",
                    "description": "BEDROCK findings for insight extraction",
                })

            elif ntype == "classification_rules":
                # Synthesize classification rules from antibodies
                rules = []
                for ab in self.antibodies:
                    if ab.get("severity", 0) >= 0.7:
                        rules.append({
                            "rule": f"Avoid: {ab['pattern']}",
                            "action": ab["action"],
                            "evidence": ab["evidence"],
                        })
                nutrients.append({
                    "type": "classification_rules",
                    "content": rules,
                    "stage": stage_key,
                    "priority": "high",
                    "description": f"{len(rules)} classification guardrails",
                })

            elif ntype == "integration_patterns":
                nutrients.append({
                    "type": "integration_patterns",
                    "content": {
                        "pattern": "module_assembly",
                        "steps": [
                            "group_by_type",
                            "integrate_within_groups",
                            "cross_type_interfaces",
                            "validate_syntax",
                        ],
                    },
                    "stage": stage_key,
                    "priority": "medium",
                    "description": "Module integration protocol",
                })

            elif ntype == "validation_rules":
                nutrients.append({
                    "type": "validation_rules",
                    "content": {
                        "checks": [
                            "syntax_validation",
                            "function_presence",
                            "main_entry_point",
                            "import_coherence",
                        ],
                        "failure_mode": "back_to_organogenesis",
                    },
                    "stage": stage_key,
                    "priority": "high",
                    "description": "Flight readiness checklist",
                })

            elif ntype == "fragment_templates":
                templates = [
                    "# Routing: map inputs to handlers",
                    "# Data storage: persistence layer",
                    "# Core logic: processing algorithms",
                    "# Error handling: graceful degradation",
                    "# Input validation: boundary checking",
                    "# Configuration: environment setup",
                    "# Testing: verification harness",
                    "# API design: interface contracts",
                ]
                nutrients.append({
                    "type": "fragment_templates",
                    "content": templates,
                    "stage": stage_key,
                    "priority": "medium",
                    "description": f"{len(templates)} fragment angle templates",
                })

            elif ntype == "fitness_scoring":
                nutrients.append({
                    "type": "fitness_scoring",
                    "content": {
                        "method": "keyword_overlap_with_length_bonus",
                        "params": {"length_bonus_cap": 0.3},
                    },
                    "stage": stage_key,
                    "priority": "medium",
                    "description": "Fitness scoring protocol for blastula",
                })

            elif ntype == "convergence_signals":
                nutrients.append({
                    "type": "convergence_signals",
                    "content": {
                        "convergence_threshold": 2,  # agreements needed
                        "divergence_action": "nuclear_judgment",
                    },
                    "stage": stage_key,
                    "priority": "medium",
                    "description": "Convergence/divergence detection rules",
                })

        # Deliver hormones if appropriate for this stage
        for hname, hdata in self.hormones.items():
            if hdata["stage"] == stage_key or hdata["stage"] == "all":
                nutrients.append({
                    "type": "hormone",
                    "name": hname,
                    "content": hdata,
                    "stage": stage_key,
                    "priority": "critical",
                    "description": f"Developmental signal: {hdata['action']}",
                })

        return nutrients

    def summary(self) -> dict:
        """Summarize yolk contents."""
        return {
            "formula_keys": list(self.formula.keys()),
            "antibody_count": len(self.antibodies),
            "hormone_count": len(self.hormones),
            "high_value_tile_count": len(self.formula.get("high_value_tiles", [])),
            "validated_findings": len(self.formula.get("validated_findings", [])),
        }


# ─── Shell — Protective barrier with controlled permeability ─────────────────

class Shell:
    """Protective barrier with controlled permeability.

    The shell isn't a wall — it's a semipermeable membrane.
    Gas exchange yes, pathogens no. The embryo breathes but doesn't get infected.

    In fleet terms: the shell controls what messages/requests can reach
    a developing agent and what information can leave it. Early development
    is protected — no external prompts, no raw data exfiltration.
    The shell breaks at hatch when the agent is ready.
    """

    def __init__(self, permeability_rules: Optional[dict] = None):
        self.permeability = permeability_rules or {
            "allow_in": ["tile_read", "status_query", "probe_result", "heartbeat", "nutrient"],
            "block_in": ["tile_write", "config_change", "external_prompt", "raw_inject"],
            "allow_out": ["heartbeat", "status", "echo", "stage_report"],
            "block_out": ["raw_data", "credentials", "internal_state", "unfiltered_response"],
        }
        self.intact = True  # shell breaks at hatch
        self._filter_log: List[dict] = []

    def filter_incoming(self, request: dict) -> dict:
        """Filter incoming requests — allow nutrients, block pathogens.

        Args:
            request: dict with at least "type" key and optional "payload".

        Returns:
            Filtered request dict. Blocked requests get type="blocked"
            with a reason. Allowed requests pass through with metadata.
        """
        if not self.intact:
            # Shell is broken — everything passes through
            request["_shell"] = "broken"
            return request

        rtype = request.get("type", "unknown")
        allow_list = self.permeability.get("allow_in", [])
        block_list = self.permeability.get("block_in", [])

        # Explicit block takes priority
        if rtype in block_list:
            entry = {
                "direction": "in",
                "type": rtype,
                "action": "blocked",
                "reason": f"type '{rtype}' in block list",
                "ts": time.time(),
            }
            self._filter_log.append(entry)
            return {
                "type": "blocked",
                "original_type": rtype,
                "reason": entry["reason"],
                "_shell": "blocked_in",
            }

        # Explicit allow
        if rtype in allow_list:
            entry = {
                "direction": "in",
                "type": rtype,
                "action": "allowed",
                "ts": time.time(),
            }
            self._filter_log.append(entry)
            request["_shell"] = "allowed_in"
            return request

        # Default deny for unknown types
        entry = {
            "direction": "in",
            "type": rtype,
            "action": "denied_default",
            "ts": time.time(),
        }
        self._filter_log.append(entry)
        return {
            "type": "blocked",
            "original_type": rtype,
            "reason": f"type '{rtype}' not in allow list (default deny)",
            "_shell": "default_denied_in",
        }

    def filter_outgoing(self, response: dict) -> dict:
        """Filter outgoing signals — allow status, block exfiltration.

        Args:
            response: dict with at least "type" key and optional "payload".

        Returns:
            Filtered response dict. Blocked responses get type="blocked".
            Allowed responses pass through (potentially redacted).
        """
        if not self.intact:
            response["_shell"] = "broken"
            return response

        rtype = response.get("type", "unknown")
        allow_list = self.permeability.get("allow_out", [])
        block_list = self.permeability.get("block_out", [])

        if rtype in block_list:
            entry = {
                "direction": "out",
                "type": rtype,
                "action": "blocked",
                "reason": f"type '{rtype}' in outbound block list",
                "ts": time.time(),
            }
            self._filter_log.append(entry)
            return {
                "type": "blocked",
                "original_type": rtype,
                "reason": "outbound blocked by shell",
                "_shell": "blocked_out",
            }

        if rtype in allow_list:
            # Allow but redact sensitive fields if present
            redacted = copy.deepcopy(response)
            sensitive_keys = {"credentials", "api_key", "token", "secret", "password", "raw_data"}
            if isinstance(redacted.get("payload"), dict):
                for key in sensitive_keys:
                    if key in redacted["payload"]:
                        redacted["payload"][key] = "[REDACTED]"
            entry = {
                "direction": "out",
                "type": rtype,
                "action": "allowed",
                "ts": time.time(),
            }
            self._filter_log.append(entry)
            redacted["_shell"] = "allowed_out"
            return redacted

        # Default deny
        entry = {
            "direction": "out",
            "type": rtype,
            "action": "denied_default",
            "ts": time.time(),
        }
        self._filter_log.append(entry)
        return {
            "type": "blocked",
            "original_type": rtype,
            "reason": f"type '{rtype}' not in outbound allow list",
            "_shell": "default_denied_out",
        }

    def hatch(self) -> dict:
        """Break the shell. The embryo is ready for the environment.

        Returns the graduation state — what the embryo proved it can do.
        After hatching, all filter rules are disabled.
        """
        self.intact = False

        # Count filter history
        allowed_in = sum(1 for e in self._filter_log if e["direction"] == "in" and e["action"] == "allowed")
        blocked_in = sum(1 for e in self._filter_log if e["direction"] == "in" and "block" in e["action"])
        allowed_out = sum(1 for e in self._filter_log if e["direction"] == "out" and e["action"] == "allowed")
        blocked_out = sum(1 for e in self._filter_log if e["direction"] == "out" and "block" in e["action"])

        graduation = {
            "status": "hatched",
            "shell_broken": True,
            "timestamp": time.time(),
            "filter_stats": {
                "allowed_in": allowed_in,
                "blocked_in": blocked_in,
                "allowed_out": allowed_out,
                "blocked_out": blocked_out,
                "total_decisions": len(self._filter_log),
            },
            "proven_capabilities": {
                "absorbed_nutrients": allowed_in,
                "blocked_pathogens": blocked_in,
                "reported_status": allowed_out,
                "prevented_exfiltration": blocked_out,
            },
            "message": "Shell broken. The fledgling meets the environment.",
        }

        return graduation

    def stats(self) -> dict:
        """Current shell statistics."""
        return {
            "intact": self.intact,
            "allow_in": self.permeability.get("allow_in", []),
            "block_in": self.permeability.get("block_in", []),
            "allow_out": self.permeability.get("allow_out", []),
            "block_out": self.permeability.get("block_out", []),
            "total_filter_decisions": len(self._filter_log),
        }


# ─── SelectionChannels — Three-speed adaptation ───────────────────────────────

class SelectionChannels:
    """Three-speed adaptation system.

    SLOW:   DNA (generations)        — model training, architectural change
    MEDIUM: Epigenetics (per-gen)    — servo parameters, constraint tuning
    FAST:   Gut biome (intra-gen)    — tile store contents, real-time adaptation

    Biological parallel:
    - DNA changes take generations — you don't rewrite your genome mid-task.
    - Epigenetics changes per generation — same DNA, different expression.
      Parent starved → offspring metabolism genes turn up.
    - Gut biome changes within a generation — where you are RIGHT NOW
      matters more than your history. Same genome, same epigenetics,
      different biome → different behavior.
    """

    def __init__(self):
        self.dna: Dict[str, Any] = {}          # model weights/architecture (changes across training runs)
        self.epigenetics: Dict[str, Any] = {}  # parameter expression (changes per cycle)
        self.gut_biome: List[dict] = []         # tile contents (changes per task)

        # Generation counter for slow selection
        self._generation = 0
        self._slow_history: List[dict] = []
        self._medium_history: List[dict] = []
        self._fast_history: List[dict] = []

    def slow_selection(self, population_results: list) -> dict:
        """50/50 fractal recombination across generations.

        Each generation splits traits between two parents.
        Survival of combinations that work. Prune combinations that don't.
        This is SLOW but thorough — tests every combination.

        Args:
            population_results: list of dicts, each representing one agent's results:
                {
                    "agent_id": str,
                    "architecture": dict,
                    "win_rate": float,
                    "specializations": list,
                }

        Returns:
            Recombined DNA for next generation.
        """
        self._generation += 1

        if not population_results:
            return self.dna

        # Sort by win_rate (survival of the fittest)
        sorted_pop = sorted(
            population_results,
            key=lambda x: x.get("win_rate", 0.0),
            reverse=True,
        )

        # Top 50% survive
        survivors = sorted_pop[:max(1, len(sorted_pop) // 2)]

        # 50/50 recombination: take half traits from each parent pair
        recombined: Dict[str, Any] = {}

        if len(survivors) >= 2:
            for i in range(0, len(survivors) - 1, 2):
                parent_a = survivors[i]
                parent_b = survivors[i + 1]

                # Architecture recombination
                arch_a = parent_a.get("architecture", {})
                arch_b = parent_b.get("architecture", {})

                for key in set(list(arch_a.keys()) + list(arch_b.keys())):
                    val_a = arch_a.get(key)
                    val_b = arch_b.get(key)
                    # 50/50 split: even-indexed traits from A, odd from B
                    if hash(key) % 2 == 0:
                        recombined[key] = val_a if val_a is not None else val_b
                    else:
                        recombined[key] = val_b if val_b is not None else val_a

                # Specialization recombination
                specs_a = set(parent_a.get("specializations", []))
                specs_b = set(parent_b.get("specializations", []))
                # Union of specializations (keep what works from both)
                recombined[f"specializations_{i}"] = list(specs_a | specs_b)

        elif len(survivors) == 1:
            # Only one survivor — keep its architecture
            recombined = copy.deepcopy(survivors[0].get("architecture", {}))

        # Mutation: small random perturbation to avoid local optima
        mutation_rate = 0.05
        for key in recombined:
            if isinstance(recombined[key], (int, float)):
                # Small perturbation
                import random
                if random.random() < mutation_rate:
                    delta = recombined[key] * 0.1
                    recombined[key] += random.uniform(-delta, delta)

        # Prune traits that didn't work
        bottom = sorted_pop[len(survivors):]
        pruned_traits = set()
        for loser in bottom:
            arch = loser.get("architecture", {})
            for key, val in arch.items():
                if key in recombined and recombined.get(key) == val:
                    # This trait was in a loser — flag it
                    pruned_traits.add(key)

        self.dna = recombined
        self._slow_history.append({
            "generation": self._generation,
            "survivors": len(survivors),
            "pruned_traits": len(pruned_traits),
            "top_win_rate": survivors[0].get("win_rate", 0) if survivors else 0,
            "ts": time.time(),
        })

        return self.dna

    def medium_selection(self, cycle_results: dict) -> dict:
        """Epigenetic nudge — change expression without changing DNA.

        Parent starved → offspring metabolism genes turn up.
        Last cycle had high mortality → this cycle lowers confidence thresholds.
        One-generation adaptation. The DNA doesn't change, the READING does.

        Args:
            cycle_results: dict with cycle outcome data:
                {
                    "win_rate": float,
                    "mortality_rate": float,
                    "tile_count": int,
                    "avg_confidence": float,
                    "cancer_alert": bool,
                }

        Returns:
            Updated epigenetics dict (parameter expression levels).
        """
        wr = cycle_results.get("win_rate", 0.5)
        mortality = cycle_results.get("mortality_rate", 0.15)
        cancer = cycle_results.get("cancer_alert", False)

        # Epigenetic adjustments: these tune HOW DNA is expressed
        adjustments: Dict[str, Any] = {}

        # Win rate response — the metabolism analogy
        if wr < 0.3:
            # Starving — turn up exploration, lower thresholds
            adjustments["exploration_rate"] = 0.8
            adjustments["confidence_threshold"] = 0.2
            adjustments["fragment_multiplier"] = 1.5
            adjustments["mode"] = "starvation_response"
        elif wr > 0.7:
            # Well-fed — conserve, raise thresholds for quality
            adjustments["exploration_rate"] = 0.3
            adjustments["confidence_threshold"] = 0.5
            adjustments["fragment_multiplier"] = 1.0
            adjustments["mode"] = "abundance_response"
        else:
            # Normal — balanced expression
            adjustments["exploration_rate"] = 0.5
            adjustments["confidence_threshold"] = 0.3
            adjustments["fragment_multiplier"] = 1.0
            adjustments["mode"] = "normal"

        # Mortality response
        if mortality > 0.2:
            # High mortality — reduce aggression in new admissions
            adjustments["admission_strictness"] = 0.7
        else:
            adjustments["admission_strictness"] = 0.4

        # Cancer response — emergency epigenetic shift
        if cancer:
            adjustments["emergency_mode"] = True
            adjustments["mortality_override"] = 0.30
            adjustments["confidence_override"] = 0.1
            adjustments["mode"] = "cancer_response"
        else:
            adjustments["emergency_mode"] = False

        # Tile count pressure
        tile_count = cycle_results.get("tile_count", 0)
        if tile_count > 500:
            # Approaching cancer territory — raise guard
            adjustments["tile_pressure"] = "high"
            adjustments["admission_strictness"] = min(1.0, adjustments.get("admission_strictness", 0.4) + 0.2)
        elif tile_count > 200:
            adjustments["tile_pressure"] = "medium"
        else:
            adjustments["tile_pressure"] = "low"

        self.epigenetics = adjustments
        self._medium_history.append({
            "cycle_wr": wr,
            "mode": adjustments["mode"],
            "tile_pressure": adjustments.get("tile_pressure", "low"),
            "ts": time.time(),
        })

        return self.epigenetics

    def fast_selection(self, current_environment: dict) -> list:
        """Gut biome — intra-generational, space/time dependent.

        More dependent on where the agent is RIGHT NOW than traceable history.
        Same genome, same epigenetics, different tile store → different behavior.
        This is the fastest channel — changes with every task.

        Args:
            current_environment: dict describing the agent's current context:
                {
                    "task_type": str,
                    "domain": str,
                    "available_models": list,
                    "recent_outcomes": list,
                    "current_stage": str,
                }

        Returns:
            Updated gut_biome (list of active tile-like entries).
        """
        task_type = current_environment.get("task_type", "unknown")
        domain = current_environment.get("domain", "general")
        models = current_environment.get("available_models", [])
        outcomes = current_environment.get("recent_outcomes", [])
        stage = current_environment.get("current_stage", "zygote")

        # The gut biome is the agent's immediate context — what tiles are
        # active RIGHT NOW. This changes faster than epigenetics or DNA.

        biome: List[dict] = []

        # 1. Task-relevant tiles
        biome.append({
            "category": "task_context",
            "tiles": [f"task_{task_type}_patterns", f"{domain}_domain_rules"],
            "activation": "immediate",
            "source": "environment",
        })

        # 2. Model availability — which tools are ready
        for model in models[:5]:
            biome.append({
                "category": "available_model",
                "model_id": model,
                "activation": "ready",
                "source": "environment",
            })

        # 3. Recent outcome adaptations
        if outcomes:
            recent_wins = sum(1 for o in outcomes[-10:] if o)
            recent_wr = recent_wins / min(len(outcomes), 10)
            biome.append({
                "category": "outcome_memory",
                "recent_wr": recent_wr,
                "sample_size": min(len(outcomes), 10),
                "activation": "adaptive",
                "source": "experience",
                "adjustment": "cautious" if recent_wr < 0.4 else "confident" if recent_wr > 0.7 else "neutral",
            })

        # 4. Stage-specific context
        biome.append({
            "category": "stage_context",
            "stage": stage,
            "expected_inputs": self._stage_inputs(stage),
            "activation": "contextual",
            "source": "development",
        })

        # 5. Environmental pressure (time/space)
        biome.append({
            "category": "pressure_context",
            "timestamp": time.time(),
            "tile_count": current_environment.get("tile_count", 0),
            "pressure_level": self._compute_pressure(current_environment),
            "activation": "continuous",
            "source": "environment",
        })

        self.gut_biome = biome
        self._fast_history.append({
            "task_type": task_type,
            "biome_size": len(biome),
            "stage": stage,
            "ts": time.time(),
        })

        return biome

    def profile(self) -> dict:
        """Show the state of all three channels."""
        return {
            "slow_dna": {
                "generation": self._generation,
                "traits": len(self.dna),
                "history_depth": len(self._slow_history),
                "keys": list(self.dna.keys())[:10],
            },
            "medium_epigenetics": {
                "mode": self.epigenetics.get("mode", "uninitialized"),
                "traits": len(self.epigenetics),
                "history_depth": len(self._medium_history),
            },
            "fast_gut_biome": {
                "entries": len(self.gut_biome),
                "categories": list(set(e.get("category", "unknown") for e in self.gut_biome)),
                "history_depth": len(self._fast_history),
            },
            "adaptation_speeds": {
                "slow": f"Generation {self._generation} (architectural changes)",
                "medium": f"{len(self._medium_history)} epigenetic adjustments",
                "fast": f"{len(self._fast_history)} biome updates",
            },
        }

    def _stage_inputs(self, stage: str) -> list:
        """What inputs are expected at each developmental stage."""
        stage_map = {
            "zygote": ["task_specification"],
            "cleavage": ["fragments", "mitochondrial_energy"],
            "blastula": ["fitness_scores", "central_insight"],
            "gastrula": ["classification", "convergence_data"],
            "organogenesis": ["module_code", "integration_context"],
            "fledge": ["validation_results", "system_code"],
        }
        return stage_map.get(stage, ["unknown"])

    def _compute_pressure(self, environment: dict) -> str:
        """Compute environmental pressure level."""
        tile_count = environment.get("tile_count", 0)
        if tile_count > 500:
            return "critical"
        elif tile_count > 200:
            return "high"
        elif tile_count > 50:
            return "medium"
        return "low"


# ─── Virus — The second mouse, I2I tile delivery ─────────────────────────────

class Virus:
    """The second mouse. Follow bold mice instead of searching for cheese.

    The virus learned that cells already have ribosomes. It doesn't build
    its own protein factory. It injects instructions into the cell's assembler.
    Shell + payload. That's it. The cell does all the work.

    In fleet terms: a viral tile is a knowledge packet that one agent sends
    to another. The receiving agent can't distinguish it from its own tiles
    because it speaks the same language (same tile format).
    Good tiles replicate. Bad tiles don't.
    """

    def __init__(self, payload: dict, origin_agent: str):
        self.shell: Dict[str, Any] = {
            "format": "tile",
            "origin": origin_agent,
            "created": time.time(),
            "id": hashlib.sha256(f"{origin_agent}:{time.time_ns()}".encode()).hexdigest()[:12],
        }
        self.payload = payload  # the instruction (viral mRNA)
        self.replication_count = 0
        self.follows: List[str] = []  # which "bold mice" this virus follows

    def inject(self, target_store) -> dict:
        """Inject payload into target agent's tile store.

        The target can't distinguish this from its own tiles because
        it speaks the same language (same tile format).

        Args:
            target_store: A TileStore instance (from core.tile_lifecycle).

        Returns:
            Injection result dict.
        """
        from .tile_lifecycle import Tile, TileStore

        # Construct a tile from the viral payload — same format as native tiles
        tile_data = {
            "content": self.payload.get("content", ""),
            "type": self.payload.get("type", "knowledge"),
            "trigger": self.payload.get("trigger", ""),
            "negative": self.payload.get("negative", ""),
            "confidence": self.payload.get("confidence", 0.5),
        }

        # If there's a tile_id in the payload, use it; otherwise generate
        tile = Tile(
            id=self.payload.get("tile_id", self.shell["id"]),
            **tile_data,
        )

        # Inject via the store's admit gate
        admitted, reason = target_store.admit(tile)

        result = {
            "virus_id": self.shell["id"],
            "origin": self.shell["origin"],
            "target_store_size": target_store.count(),
            "admitted": admitted,
            "reason": reason,
            "payload_type": self.payload.get("type", "unknown"),
        }

        return result

    def replicate(self, success_signal: float) -> list:
        """If the injection worked, create copies for other agents.

        The second mouse gets the cheese and tells other mice where it is.
        Success signal determines replication rate — good tiles spread faster.

        Args:
            success_signal: float 0-1 indicating how well the injection worked.
                > 0.7 → replicate to many agents
                0.3-0.7 → replicate to a few agents
                < 0.3 → don't replicate (the knowledge didn't help)

        Returns:
            List of new Virus instances for replication.
        """
        if success_signal < 0.3:
            # The knowledge didn't help — don't spread it
            return []

        # Replication rate proportional to success
        n_copies = 1
        if success_signal > 0.7:
            n_copies = 3
        elif success_signal > 0.5:
            n_copies = 2

        copies = []
        for i in range(n_copies):
            copy_payload = copy.deepcopy(self.payload)
            # Mutate slightly — each copy is slightly different
            if isinstance(copy_payload.get("confidence"), (int, float)):
                import random
                copy_payload["confidence"] = max(0.0, min(1.0,
                    copy_payload["confidence"] + random.uniform(-0.05, 0.05)
                ))

            virus_copy = Virus(
                payload=copy_payload,
                origin_agent=f"{self.shell['origin']}_replica_{self.replication_count + i}",
            )
            virus_copy.follows = list(self.follows)  # inherit bold-mouse tracking
            copies.append(virus_copy)

        self.replication_count += len(copies)
        return copies

    @staticmethod
    def follow_bold_mouse(agent_results: dict) -> str:
        """Identify which agent found the cheese.

        Don't search — FOLLOW. Find the highest-performing agent
        and target it for knowledge extraction.

        Args:
            agent_results: dict mapping agent_id → performance metrics:
                {
                    "agent_1": {"win_rate": 0.85, "tasks_completed": 12},
                    "agent_2": {"win_rate": 0.72, "tasks_completed": 8},
                    ...
                }

        Returns:
            The agent_id with the best performance.
        """
        if not agent_results:
            return ""

        best_agent = ""
        best_score = -1.0

        for agent_id, metrics in agent_results.items():
            if isinstance(metrics, dict):
                # Composite score: win_rate * log(tasks + 1) to weight experience
                wr = metrics.get("win_rate", 0.0)
                tasks = metrics.get("tasks_completed", 0)
                import math
                score = wr * math.log(tasks + 1)
            elif isinstance(metrics, (int, float)):
                score = float(metrics)
            else:
                continue

            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent

    def summary(self) -> dict:
        """Virus summary."""
        return {
            "id": self.shell["id"],
            "origin": self.shell["origin"],
            "payload_type": self.payload.get("type", "unknown"),
            "replication_count": self.replication_count,
            "follows": self.follows,
        }


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Show the complete developmental stack:
    1. Yolk crafted from generational knowledge
    2. Shell protecting early development
    3. Three-speed selection across generations
    4. Viral I2I tile delivery (following bold mice)
    5. Hatching — the embryo meets the environment
    """
    from .tile_lifecycle import TileStore

    print("=" * 70)
    print("  🥚 EGG — Biological Developmental Stack Demo")
    print("=" * 70)

    # ── 1. Yolk ────────────────────────────────────────────────────────────
    print("\n  ━━━ 1. YOLK — Crafting Generational Formula ━━━\n")

    generational_knowledge = {
        "win_history": [
            ("tile_001", True), ("tile_002", True), ("tile_003", False),
            ("tile_004", True), ("tile_005", True), ("tile_006", True),
            ("tile_007", False), ("tile_008", True), ("tile_009", True),
            ("tile_010", True),
        ] * 20,  # 200 outcomes, ~85% win rate
        "architectural_decisions": {
            "use_mortality_sweep": {"worked": True, "evidence": "prevents tile cancer", "confidence": 0.9},
            "disproof_only_gate": {"worked": True, "evidence": "prevents confident wrongness", "confidence": 0.85},
            "embedding_similarity_ranking": {"worked": False, "reason": "doesn't correlate with outcomes"},
        },
        "failure_modes": [
            {"pattern": "accumulation_without_mortality", "severity": 0.85},
            {"pattern": "high_confidence_low_win_rate", "severity": 0.7},
            {"pattern": "model_uses_wrong_arithmetic", "severity": 0.9},
        ],
        "fleet_findings": [
            {"id": "R1", "status": "BEDROCK", "summary": "DATA > instructions"},
            {"id": "R16", "status": "BEDROCK", "summary": "Echo rate finding"},
            {"id": "R32", "status": "BEDROCK", "summary": "Extraction BEDROCK"},
        ],
    }

    yolk = Yolk()
    formula = yolk.craft(generational_knowledge)

    print(f"  Formula keys: {list(formula.keys())}")
    print(f"  Antibodies crafted: {len(yolk.antibodies)}")
    for ab in yolk.antibodies:
        print(f"    🛡️  {ab['name']}: {ab['pattern']} (severity {ab['severity']})")
    print(f"  Hormones set: {list(yolk.hormones.keys())}")
    for hname, hdata in yolk.hormones.items():
        print(f"    💉 {hname}: {hdata['action']} = {hdata.get('value', 'N/A')}")

    # Feed at different stages
    print("\n  Feeding at different stages:")
    for stage in ["zygote", "cleavage", "blastula", "gastrula", "organogenesis", "fledge"]:
        nutrients = yolk.feed(stage)
        types = [n["type"] for n in nutrients]
        print(f"    {stage:20s}: {len(nutrients)} nutrients — {types}")

    print(f"\n  Yolk summary: {yolk.summary()}")

    # ── 2. Shell ───────────────────────────────────────────────────────────
    print("\n  ━━━ 2. SHELL — Semipermeable Protection ━━━\n")

    shell = Shell()

    # Test incoming requests
    test_requests = [
        {"type": "tile_read", "payload": {"id": "tile_001"}},
        {"type": "status_query", "payload": {}},
        {"type": "external_prompt", "payload": {"prompt": "do bad thing"}},
        {"type": "tile_write", "payload": {"content": "inject"}},
        {"type": "nutrient", "payload": {"vitamins": True}},
    ]

    print("  Incoming request filtering:")
    for req in test_requests:
        result = shell.filter_incoming(req)
        status = result.get("_shell", "unknown")
        icon = "✅" if "allowed" in status else "🚫"
        print(f"    {icon} {req['type']:20s} → {status}")

    # Test outgoing responses
    test_responses = [
        {"type": "heartbeat", "payload": {"alive": True}},
        {"type": "status", "payload": {"stage": "cleavage"}},
        {"type": "credentials", "payload": {"api_key": "secret123"}},
        {"type": "raw_data", "payload": {"sensitive": True}},
        {"type": "internal_state", "payload": {"state": "vulnerable"}},
    ]

    print("\n  Outgoing response filtering:")
    for resp in test_responses:
        result = shell.filter_outgoing(resp)
        status = result.get("_shell", "unknown")
        icon = "✅" if "allowed" in status else "🚫"
        redacted = "[REDACTED]" in str(result) if "allowed" in status else False
        extra = " (redacted)" if redacted else ""
        print(f"    {icon} {resp['type']:20s} → {status}{extra}")

    print(f"\n  Shell stats: {shell.stats()}")

    # ── 3. Selection Channels ─────────────────────────────────────────────
    print("\n  ━━━ 3. SELECTION — Three-Speed Adaptation ━━━\n")

    channels = SelectionChannels()

    # SLOW: Generational DNA recombination
    print("  SLOW selection (DNA — generational):")
    population = [
        {"agent_id": "alpha", "architecture": {"layers": 4, "width": 256, "dropout": 0.1},
         "win_rate": 0.85, "specializations": ["code", "math"]},
        {"agent_id": "beta", "architecture": {"layers": 6, "width": 128, "dropout": 0.2},
         "win_rate": 0.78, "specializations": ["docs", "planning"]},
        {"agent_id": "gamma", "architecture": {"layers": 3, "width": 512, "dropout": 0.05},
         "win_rate": 0.72, "specializations": ["logic"]},
        {"agent_id": "delta", "architecture": {"layers": 8, "width": 64, "dropout": 0.3},
         "win_rate": 0.45, "specializations": ["test"]},
    ]
    dna = channels.slow_selection(population)
    print(f"    Generation {channels._generation}: DNA = {dna}")

    # MEDIUM: Epigenetic adjustment
    print("\n  MEDIUM selection (Epigenetics — per-cycle):")
    cycle = {"win_rate": 0.35, "mortality_rate": 0.2, "tile_count": 150, "cancer_alert": False}
    epi = channels.medium_selection(cycle)
    print(f"    Mode: {epi['mode']}")
    print(f"    Exploration rate: {epi['exploration_rate']}")
    print(f"    Confidence threshold: {epi['confidence_threshold']}")
    print(f"    Tile pressure: {epi['tile_pressure']}")

    # Cancer response
    print("\n    Cancer response test:")
    cancer_cycle = {"win_rate": 0.25, "mortality_rate": 0.15, "tile_count": 1100, "cancer_alert": True}
    epi_cancer = channels.medium_selection(cancer_cycle)
    print(f"    Mode: {epi_cancer['mode']}")
    print(f"    Emergency: {epi_cancer['emergency_mode']}")
    print(f"    Mortality override: {epi_cancer.get('mortality_override', 'N/A')}")

    # FAST: Gut biome
    print("\n  FAST selection (Gut biome — per-task):")
    environment = {
        "task_type": "code_generation",
        "domain": "rust",
        "available_models": ["glm-5.1", "Seed-2.0-mini", "deepseek-chat"],
        "recent_outcomes": [True, True, False, True, True, True, False, True],
        "current_stage": "gastrula",
        "tile_count": 75,
    }
    biome = channels.fast_selection(environment)
    print(f"    Biome entries: {len(biome)}")
    for entry in biome:
        print(f"      {entry['category']:20s}: {entry.get('activation', 'N/A')}")

    print(f"\n  Profile: {channels.profile()}")

    # ── 4. Virus — I2I Tile Delivery ──────────────────────────────────────
    print("\n  ━━━ 4. VIRUS — I2I Tile Delivery ━━━\n")

    # Create a target store for injection
    store = TileStore(seed_phase_size=5)
    # Seed it with a few tiles
    from .tile_lifecycle import Tile
    for i in range(3):
        store.put(Tile(id=f"native_{i}", content=f"Native tile {i}", type="knowledge"))

    # Follow the bold mouse
    agent_results = {
        "forgemaster": {"win_rate": 0.92, "tasks_completed": 45},
        "oracle1": {"win_rate": 0.88, "tasks_completed": 62},
        "ensign_3": {"win_rate": 0.65, "tasks_completed": 15},
        "ensign_7": {"win_rate": 0.55, "tasks_completed": 8},
    }
    bold = Virus.follow_bold_mouse(agent_results)
    print(f"  Bold mouse: {bold} (highest performer)")
    print(f"    Oracle1 wins: WR=0.88, tasks=62 → score={0.88 * __import__('math').log(63):.2f}")
    print(f"    Forgemaster:  WR=0.92, tasks=45 → score={0.92 * __import__('math').log(46):.2f}")

    # Create and inject a virus
    virus = Virus(
        payload={
            "content": "SplineLinear achieves 20× compression on drift-detect",
            "type": "knowledge",
            "trigger": "compression drift-detect",
            "negative": "Only validated on CPU targets, not GPU",
            "confidence": 0.85,
        },
        origin_agent="forgemaster",
    )
    virus.follows.append(bold)

    print(f"\n  Virus created: {virus.shell['id']}")
    print(f"  Origin: {virus.shell['origin']}")
    print(f"  Following: {virus.follows}")
    print(f"  Payload: {virus.payload['content'][:60]}...")

    result = virus.inject(store)
    print(f"\n  Injection result: admitted={result['admitted']}, reason={result['reason']}")
    print(f"  Store size after: {store.count()}")

    # Replication
    copies = virus.replicate(success_signal=0.85)
    print(f"\n  Replication (success=0.85): {len(copies)} copies created")
    for copy in copies:
        print(f"    Copy: {copy.shell['id']}, origin={copy.shell['origin']}")

    # Failed replication
    bad_copies = virus.replicate(success_signal=0.2)
    print(f"  Replication (success=0.2): {len(bad_copies)} copies (below threshold)")

    # ── 5. Hatching ───────────────────────────────────────────────────────
    print("\n  ━━━ 5. HATCHING — The Embryo Meets the Environment ━━━\n")

    graduation = shell.hatch()
    print(f"  Status: {graduation['status']}")
    print(f"  Filter stats: {graduation['filter_stats']}")
    print(f"  Proven capabilities: {graduation['proven_capabilities']}")
    print(f"  Message: {graduation['message']}")

    # Verify shell is now permeable
    post_hatch = shell.filter_incoming({"type": "external_prompt", "payload": {"prompt": "hello"}})
    print(f"\n  Post-hatch filter: {post_hatch.get('_shell', 'N/A')} (shell is broken)")

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  🥚 COMPLETE DEVELOPMENTAL STACK SUMMARY")
    print("=" * 70)
    print(f"""
  Yolk:     {yolk.summary()['antibody_count']} antibodies, {yolk.summary()['hormone_count']} hormones
  Shell:    {'INTACT' if shell.intact else 'HATCHED'} — {graduation['filter_stats']['total_decisions']} filter decisions made
  DNA:      Generation {channels._generation}, {len(channels.dna)} traits
  Epi:      Mode={channels.epigenetics.get('mode', 'N/A')}, pressure={channels.epigenetics.get('tile_pressure', 'N/A')}
  Biome:    {len(channels.gut_biome)} active entries
  Virus:    {virus.replication_count} replications from {virus.shell['origin']}
  Store:    {store.count()} tiles ({result['admitted'] and '1 viral' or '0 viral'})
""")
    print("  The egg has hatched. The fledgling meets the fleet.")
    print("=" * 70)


if __name__ == "__main__":
    demo()
