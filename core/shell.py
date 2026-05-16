"""core/shell.py — Hermit Crab / Embryo Duality: Shells, Collections, and Private Breeding.

A shell is a room-sized constraint that an agent can wear (hermit crab)
or grow inside (embryo). Both are true simultaneously.

Biological parallels:
  HERMIT CRAB: Samples shells, finds the fit, wears it for protection.
    Power armor. The agent doesn't change — the shell shapes what reaches it.
  EMBRYO: Grows inside a shell until it's ready to hatch.
    Developmental constraint. The agent changes — the shell shapes what it becomes.
  BELYAEV'S FARM: Controlled selection in private. Only ONE pressure applied.
    Everything else held constant. Generations of private development
    before release into the wild.

Integrates with:
  - core.tile_lifecycle (Tile, TileStore) — knowledge substrate
  - core.egg (Shell as semipermeable membrane) — protective barrier
  - core.embryo (DevelopmentalStage) — developmental pipeline
  - core.scale_fold (Scale, ScaleFoldEngine) — scale navigation
"""
from __future__ import annotations

import math
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict


# ─── Shell — A room-sized constraint worn or grown inside ─────────────────────

class Shell:
    """A room-sized shell that an agent can wear or grow inside.

    The hermit crab puts it on for protection (power armor).
    The embryo grows inside it until it's ready to hatch.
    Both are true simultaneously.

    Fit is bidirectional:
      - Agent → Shell: agent's capabilities vs shell's requirements
      - Shell → Agent: shell's constraints vs agent's desires
      - Growth potential: how much the agent can still learn inside this shell

    When the agent outgrows the shell (growth_log exceeds capacity,
    or capabilities exceed what the shell provides), it's time to move on.
    """

    def __init__(self, shell_id: str, constraints: dict = None):
        self.id = shell_id
        self.constraints = constraints or {}
        self.wearer = None              # agent_id of who's inside
        self.growth_log: List[dict] = []  # what happened while wearing it
        self.capacity = self.constraints.get("capacity", 100) if constraints else 100
        self.created = time.time()

        # Shell properties derived from constraints
        self.purpose = self.constraints.get("purpose", "general")
        self.required_capabilities = self.constraints.get("required_capabilities", [])
        self.allowed_growth_types = self.constraints.get("allowed_growth_types", ["any"])
        self.protection_level = self.constraints.get("protection_level", 0.5)
        self.specialization = self.constraints.get("specialization", None)
        self.stage_range = self.constraints.get("stage_range", None)

    def try_on(self, agent_id: str) -> dict:
        """Hermit crab samples this shell. Returns how well it fits.

        Fit = alignment between agent's desires and shell's constraints.
        If it doesn't fit, the agent moves on. If it does, they stay.

        Args:
            agent_id: The agent attempting to wear this shell.

        Returns:
            Dict with fit_score (0.0-1.0), details, and whether the agent stays.
        """
        if self.wearer and self.wearer != agent_id:
            return {
                "fit_score": 0.0,
                "occupied": True,
                "wearer": self.wearer,
                "stays": False,
                "reason": f"Shell occupied by {self.wearer}",
            }

        # If already wearing it, report current state
        if self.wearer == agent_id:
            return {
                "fit_score": 1.0,
                "occupied": False,
                "already_wearing": True,
                "stays": True,
                "growth_entries": len(self.growth_log),
                "reason": "Already wearing this shell",
            }

        # Sample — the hermit crab tests the fit
        fit = min(1.0, 0.5)  # base fit (unknown agent → neutral)
        details = {"base_fit": fit}

        # The agent stays if the shell is comfortable enough
        stays = fit >= 0.3  # minimum threshold for staying

        if stays:
            self.wearer = agent_id

        return {
            "fit_score": round(fit, 3),
            "occupied": False,
            "already_wearing": False,
            "stays": stays,
            "reason": f"Fit score {fit:.2f} {'≥' if stays else '<'} 0.3 threshold",
            "details": details,
        }

    def fits(self, agent_profile: dict) -> float:
        """How well does this shell fit this agent? 0.0-1.0

        Based on:
          - Agent capabilities vs shell requirements (can they handle it?)
          - Agent desires vs shell purpose (do they want what it offers?)
          - Growth potential (how much can they still learn?)
          - Stage compatibility (is the agent at the right developmental stage?)

        Args:
            agent_profile: dict with keys like:
                "capabilities": list of str,
                "desires": list of str,
                "development_stage": str,
                "experience": float (0-1),
                "specializations": list of str,
        """
        score = 0.0
        components = {}

        # 1. Capability match (can they handle it?)
        agent_caps = set(agent_profile.get("capabilities", []))
        required = set(self.required_capabilities)
        if required:
            cap_overlap = len(agent_caps & required) / len(required)
        else:
            cap_overlap = 1.0  # no requirements → everyone qualifies
        cap_score = cap_overlap * 0.3  # 30% weight
        components["capability_match"] = round(cap_score, 3)
        score += cap_score

        # 2. Desire alignment (do they want what it offers?)
        agent_desires = set(d.lower() for d in agent_profile.get("desires", []))
        purpose_keywords = set(self.purpose.lower().split())
        if agent_desires and purpose_keywords:
            desire_overlap = len(agent_desires & purpose_keywords) / max(len(purpose_keywords), 1)
        else:
            desire_overlap = 0.5  # neutral
        desire_score = desire_overlap * 0.3  # 30% weight
        components["desire_alignment"] = round(desire_score, 3)
        score += desire_score

        # 3. Growth potential (how much room to grow?)
        current_growth = len(self.growth_log)
        remaining_capacity = max(0, self.capacity - current_growth)
        growth_fraction = remaining_capacity / max(self.capacity, 1)
        growth_score = growth_fraction * 0.2  # 20% weight
        components["growth_potential"] = round(growth_score, 3)
        score += growth_score

        # 4. Stage compatibility
        agent_stage = agent_profile.get("development_stage", "unknown")
        if self.stage_range:
            stages = self.stage_range if isinstance(self.stage_range, list) else [self.stage_range]
            stage_match = 1.0 if agent_stage in stages else 0.3
        else:
            stage_match = 0.7  # no restriction → mostly compatible
        stage_score = stage_match * 0.2  # 20% weight
        components["stage_compatibility"] = round(stage_score, 3)
        score += stage_score

        return round(min(1.0, score), 3)

    def grow_inside(self, tile_data: dict) -> dict:
        """Embryo develops within this shell's constraints.

        Each tile deposited is growth. When tiles exceed capacity,
        the shell is outgrown.

        Args:
            tile_data: dict with growth information:
                "content": str — what was learned
                "type": str — what kind of growth
                "confidence": float — how well-learned (0-1)
                "timestamp": float — when (default now)

        Returns:
            Dict with growth result, current fill level, and whether outgrown.
        """
        growth_type = tile_data.get("type", "knowledge")

        # Check if this growth type is allowed by shell constraints
        if "any" not in self.allowed_growth_types:
            if growth_type not in self.allowed_growth_types:
                return {
                    "accepted": False,
                    "reason": f"Growth type '{growth_type}' not allowed "
                              f"(allowed: {self.allowed_growth_types})",
                    "fill_level": len(self.growth_log) / max(self.capacity, 1),
                    "outgrown": self.is_outgrown(),
                }

        # Record the growth
        entry = {
            "content": tile_data.get("content", ""),
            "type": growth_type,
            "confidence": tile_data.get("confidence", 0.5),
            "timestamp": tile_data.get("timestamp", time.time()),
            "entry_index": len(self.growth_log),
        }
        self.growth_log.append(entry)

        fill_level = len(self.growth_log) / max(self.capacity, 1)

        return {
            "accepted": True,
            "entry": entry,
            "fill_level": round(fill_level, 3),
            "remaining_capacity": max(0, self.capacity - len(self.growth_log)),
            "outgrown": self.is_outgrown(),
        }

    def is_outgrown(self) -> bool:
        """Has the agent outgrown this shell?

        True when:
          - growth_log exceeds capacity, OR
          - average confidence of recent growth > 0.9 (mastered the material)
        """
        if len(self.growth_log) >= self.capacity:
            return True

        # Check if the agent has mastered what the shell offers
        if len(self.growth_log) >= 10:
            recent = self.growth_log[-10:]
            avg_conf = sum(e.get("confidence", 0.5) for e in recent) / len(recent)
            if avg_conf > 0.9:
                return True

        return False

    def leave(self) -> dict:
        """Agent leaves the shell. Returns what was learned while inside.

        The departure is the graduation. Everything accumulated in
        growth_log becomes the agent's to keep.
        """
        total_growth = len(self.growth_log)
        growth_by_type = defaultdict(list)
        for entry in self.growth_log:
            growth_by_type[entry["type"]].append(entry)

        avg_confidence = (
            sum(e.get("confidence", 0.5) for e in self.growth_log) / total_growth
            if total_growth > 0 else 0.0
        )

        duration = time.time() - self.created

        result = {
            "shell_id": self.id,
            "wearer": self.wearer,
            "total_growth_entries": total_growth,
            "growth_by_type": {k: len(v) for k, v in growth_by_type.items()},
            "avg_confidence": round(avg_confidence, 3),
            "duration_seconds": round(duration, 1),
            "capacity_used": round(total_growth / max(self.capacity, 1), 3),
            "outgrown": self.is_outgrown(),
            "learned": [e["content"] for e in self.growth_log],
            "purpose": self.purpose,
        }

        self.wearer = None
        return result

    def summary(self) -> dict:
        """Shell summary."""
        return {
            "id": self.id,
            "purpose": self.purpose,
            "wearer": self.wearer,
            "growth_entries": len(self.growth_log),
            "capacity": self.capacity,
            "fill_level": round(len(self.growth_log) / max(self.capacity, 1), 3),
            "outgrown": self.is_outgrown(),
            "protection_level": self.protection_level,
        }


# ─── ShellCollection — PLATO room as curated shell collection ─────────────────

class ShellCollection:
    """PLATO room as curated shell collection.

    Agents browse, sample, and choose shells. The collection
    is curated — not every shell is available to every agent.

    Like Belyaev's farm: controlled selection pressure. The curator
    decides which shells are visible, which are recommended, and
    which are reserved for later stages.

    The three stages of shell access mirror developmental stages:
      Early (sandbox): small, protective, highly constrained
      Middle (specialization): purpose-specific, moderate constraints
      Late (near-freedom): minimal shells, agent is nearly independent
    """

    def __init__(self):
        self.shells: Dict[str, Shell] = {}
        self.available: List[str] = []        # shell_ids currently available
        self.curated: Dict[str, List[str]] = {}  # agent_id → [recommended shell_ids]
        self.access_log: List[dict] = []

    def add_shell(self, shell: Shell) -> None:
        """Add a shell to the collection."""
        self.shells[shell.id] = shell
        if shell.id not in self.available:
            self.available.append(shell.id)

    def browse(self, agent_id: str, agent_profile: dict) -> list:
        """Agent browses available shells. Returns sorted by fit score.

        The hermit crab samples the collection. Each shell is scored
        for fit against the agent's profile. The agent can then
        choose which to try on.

        Args:
            agent_id: The browsing agent.
            agent_profile: Agent's capabilities, desires, stage, etc.

        Returns:
            List of dicts: {shell_id, fit_score, purpose, available}
            sorted by fit_score descending.
        """
        results = []
        for shell_id in self.available:
            shell = self.shells.get(shell_id)
            if not shell:
                continue
            fit = shell.fits(agent_profile)
            results.append({
                "shell_id": shell.id,
                "fit_score": fit,
                "purpose": shell.purpose,
                "protection_level": shell.protection_level,
                "capacity": shell.capacity,
                "available": shell.wearer is None or shell.wearer == agent_id,
            })

        results.sort(key=lambda x: x["fit_score"], reverse=True)

        self.access_log.append({
            "action": "browse",
            "agent_id": agent_id,
            "shells_evaluated": len(results),
            "top_fit": results[0]["fit_score"] if results else 0.0,
            "ts": time.time(),
        })

        return results

    def recommend(self, agent_id: str, development_stage: str) -> list:
        """Curated recommendations based on agent's development stage.

        Early stages: small, protective shells (sandboxing).
        Middle stages: purpose-specific shells (specialization).
        Late stages: minimal shells (near-freedom).

        Args:
            agent_id: The agent to recommend for.
            development_stage: One of "early", "middle", "late", or specific stage names.

        Returns:
            List of recommended shell dicts sorted by relevance.
        """
        stage_map = {
            "zygote": "early", "cleavage": "early", "blastula": "early",
            "gastrula": "middle", "organogenesis": "middle",
            "fledge": "late", "fledgling": "late",
            "early": "early", "middle": "middle", "late": "late",
        }
        phase = stage_map.get(development_stage, "middle")

        recommendations = []
        for shell_id in self.available:
            shell = self.shells.get(shell_id)
            if not shell:
                continue

            # Filter by stage compatibility
            if phase == "early":
                # Early agents need protection, small capacity, constraints
                score = shell.protection_level * 0.5
                if shell.capacity <= 50:
                    score += 0.3
                if shell.constraints.get("sandbox", False):
                    score += 0.2
            elif phase == "middle":
                # Middle agents need purpose-specific shells
                score = 0.3
                if shell.specialization:
                    score += 0.4
                if 30 <= shell.capacity <= 150:
                    score += 0.2
                score += (1 - shell.protection_level) * 0.1
            else:  # late
                # Late agents need minimal shells, high capacity, low protection
                score = (1 - shell.protection_level) * 0.5
                if shell.capacity >= 100:
                    score += 0.3
                if not shell.required_capabilities:
                    score += 0.2

            recommendations.append({
                "shell_id": shell.id,
                "fit_score": round(min(1.0, score), 3),
                "purpose": shell.purpose,
                "phase_match": phase,
                "protection_level": shell.protection_level,
            })

        recommendations.sort(key=lambda x: x["fit_score"], reverse=True)
        return recommendations

    def curate_for(self, agent_id: str, purpose: str) -> None:
        """Curate the collection for a specific agent's purpose.

        Like Belyaev controlling the environment so only the
        desired selection pressure operates. The agent only sees
        shells relevant to their purpose.

        Args:
            agent_id: The agent to curate for.
            purpose: The agent's purpose (e.g., "constraint_theory", "code_gen").
        """
        relevant = []
        purpose_words = set(purpose.lower().split("_"))

        for shell_id, shell in self.shells.items():
            shell_words = set(shell.purpose.lower().split())
            overlap = len(purpose_words & shell_words)
            if overlap > 0 or shell.purpose == "general":
                relevant.append(shell_id)

        self.curated[agent_id] = relevant

    def get_curated(self, agent_id: str) -> list:
        """Get curated shells for an agent."""
        shell_ids = self.curated.get(agent_id, self.available)
        results = []
        for sid in shell_ids:
            shell = self.shells.get(sid)
            if shell:
                results.append(shell)
        return results

    def stats(self) -> dict:
        """Collection statistics."""
        occupied = sum(1 for s in self.shells.values() if s.wearer is not None)
        return {
            "total_shells": len(self.shells),
            "available": len(self.available),
            "occupied": occupied,
            "curated_agents": len(self.curated),
            "access_log_entries": len(self.access_log),
        }


# ─── PrivateBreeding — Belyaev's farm for controlled development ──────────────

class PrivateBreeding:
    """Belyaev's farm — controlled conditions for private development.

    The tameness had to be bred PRIVATELY. Generations in a controlled
    environment where the only selection pressure was "stop flinching at
    my hand." External pressure held constant so internal pressure
    could actually change.

    If you release fearful foxes into the wild on day one, the project fails.

    The farm applies ONE selection pressure at a time. Everything else
    is held constant. Over generations, the target trait changes.
    Side effects emerge (floppy ears, curled tails) — that's expected.

    In fleet terms:
      - Selection pressure: the ONE thing being optimized (e.g., "accuracy")
      - Held constant: external factors (API costs, adversarial inputs, noise)
      - Generations: successive rounds of breeding
      - Trait value: measured improvement in the selected trait
      - Side effects: unexpected changes in non-selected traits
    """

    def __init__(self, farm_id: str):
        self.farm_id = farm_id
        self.selection_pressure: Dict[str, str] = {}  # trait → direction
        self.held_constant: Dict[str, bool] = {}      # factor → suppressed
        self.generations: List[dict] = []
        self.current_generation = 0
        self.population_history: List[dict] = []

    def set_pressure(self, trait: str, direction: str = "increase") -> None:
        """Set the ONE selection pressure for this farm.

        Belyaev: "tameness, increase" — that's it. One trait.
        Everything else held constant.

        Args:
            trait: The trait being selected for/against.
            direction: "increase" or "decrease".
        """
        self.selection_pressure = {trait: direction}  # ONE pressure

    def breed_generation(self, population: list) -> dict:
        """One generation of controlled breeding.

        Select only on the chosen pressure. Nothing else.
        The trait changes. Everything else shifts as side effects.

        Args:
            population: List of dicts, each representing an agent:
                {
                    "agent_id": str,
                    "traits": {trait_name: float_value, ...},
                    "fitness": float,
                }

        Returns:
            Generation result with selected parents, offspring, and side effects.
        """
        if not population:
            return {"error": "empty population"}

        if not self.selection_pressure:
            return {"error": "no selection pressure set — call set_pressure() first"}

        self.current_generation += 1
        trait, direction = next(iter(self.selection_pressure.items()))

        # Sort population by the selected trait
        sorted_pop = sorted(
            population,
            key=lambda x: x.get("traits", {}).get(trait, 0.0),
            reverse=(direction == "increase"),
        )

        # Select top performers (only on the chosen trait)
        n_survivors = max(2, len(sorted_pop) // 2)
        survivors = sorted_pop[:n_survivors]

        # Measure the trait in this generation
        trait_values = [a.get("traits", {}).get(trait, 0.0) for a in population]
        avg_trait = sum(trait_values) / len(trait_values)
        top_trait = trait_values[0] if direction == "increase" else trait_values[-1]

        # Generate offspring by combining top performers
        offspring = []
        for i in range(0, len(survivors) - 1, 2):
            parent_a = survivors[i]
            parent_b = survivors[i + 1]

            # 50/50 trait inheritance with small mutation
            child_traits = {}
            all_trait_keys = set(
                list(parent_a.get("traits", {}).keys()) +
                list(parent_b.get("traits", {}).keys())
            )
            for key in all_trait_keys:
                val_a = parent_a.get("traits", {}).get(key, 0.5)
                val_b = parent_b.get("traits", {}).get(key, 0.5)
                # 50/50 recombination
                child_val = val_a if hash(f"{key}{i}") % 2 == 0 else val_b
                # Small mutation
                child_val += (hash(f"{key}{time.time_ns()}") % 100 - 50) / 500.0
                child_val = max(0.0, min(1.0, child_val))
                child_traits[key] = round(child_val, 4)

            offspring.append({
                "agent_id": f"gen{self.current_generation}_child_{i//2}",
                "traits": child_traits,
                "fitness": 0.0,  # untested
                "parent_a": parent_a.get("agent_id", ""),
                "parent_b": parent_b.get("agent_id", ""),
            })

        # Detect side effects: traits that changed but weren't selected for
        side_effects = {}
        if self.generations:
            prev_avg = self.generations[-1].get("avg_traits", {})
            for t_key in all_trait_keys:
                if t_key == trait:
                    continue  # skip the selected trait
                prev_val = prev_avg.get(t_key, 0.5)
                curr_vals = [a.get("traits", {}).get(t_key, 0.5) for a in population]
                curr_avg = sum(curr_vals) / len(curr_vals) if curr_vals else 0.5
                delta = curr_avg - prev_val
                if abs(delta) > 0.05:
                    side_effects[t_key] = {
                        "previous": round(prev_val, 3),
                        "current": round(curr_avg, 3),
                        "delta": round(delta, 3),
                    }

        # Compute average traits for this generation
        avg_traits = {}
        for t_key in all_trait_keys:
            vals = [a.get("traits", {}).get(t_key, 0.5) for a in population]
            avg_traits[t_key] = round(sum(vals) / len(vals), 4)

        gen_result = {
            "generation": self.current_generation,
            "trait_selected": trait,
            "direction": direction,
            "population_size": len(population),
            "survivors": len(survivors),
            "offspring_produced": len(offspring),
            "avg_trait_value": round(avg_trait, 4),
            "top_trait_value": round(top_trait, 4),
            "avg_traits": avg_traits,
            "side_effects": side_effects,
            "offspring": offspring[:5],  # preview
            "ts": time.time(),
        }

        self.generations.append(gen_result)
        self.population_history.append({
            "gen": self.current_generation,
            "population": [a.get("agent_id", "") for a in population],
        })

        return gen_result

    def hold_constant(self, external_factor: str) -> None:
        """Suppress an external pressure. The farm blocks it.

        No predators, no competition, no weather.
        The room blocks external API calls, adversarial inputs, etc.

        Args:
            external_factor: The factor to suppress (e.g., "adversarial_inputs",
                             "api_rate_limits", "external_prompts").
        """
        self.held_constant[external_factor] = True

    def is_ready_for_release(self, agent_id: str) -> dict:
        """Has this agent been bred long enough to survive the wild?

        Checks:
          - Sufficient generations (minimum 3)
          - Target trait stabilized (improvement < 5% over last 2 gens)
          - No catastrophic side effects (no trait dropped below 0.2)

        Args:
            agent_id: The agent to evaluate.

        Returns:
            Dict with ready status, checks, and concerns.
        """
        checks = {
            "sufficient_generations": False,
            "trait_stabilized": False,
            "no_catastrophic_side_effects": False,
        }
        concerns = []

        # Check 1: sufficient generations
        if self.current_generation >= 3:
            checks["sufficient_generations"] = True
        else:
            concerns.append(
                f"Only {self.current_generation} generations (need ≥ 3)"
            )

        # Check 2: trait stabilized
        if len(self.generations) >= 2:
            trait = next(iter(self.selection_pressure), "")
            recent = self.generations[-2:]
            vals = [g.get("avg_trait_value", 0) for g in recent]
            improvement = abs(vals[-1] - vals[0])
            if improvement < 0.05:
                checks["trait_stabilized"] = True
            else:
                concerns.append(
                    f"Trait '{trait}' still improving: {improvement:.3f} delta"
                )
        elif self.current_generation >= 3:
            # Not enough history to check, assume stable
            checks["trait_stabilized"] = True

        # Check 3: no catastrophic side effects
        if self.generations:
            latest = self.generations[-1]
            side_effects = latest.get("side_effects", {})
            catastrophic = False
            for trait_name, effect in side_effects.items():
                if effect.get("current", 1.0) < 0.2:
                    catastrophic = True
                    concerns.append(
                        f"Catastrophic side effect: {trait_name} dropped to "
                        f"{effect['current']:.3f}"
                    )
            if not catastrophic:
                checks["no_catastrophic_side_effects"] = True
        else:
            checks["no_catastrophic_side_effects"] = True

        ready = all(checks.values())

        return {
            "agent_id": agent_id,
            "ready": ready,
            "checks": checks,
            "concerns": concerns,
            "generations_bred": self.current_generation,
            "farm_id": self.farm_id,
        }

    def summary(self) -> dict:
        """Farm summary."""
        trait = next(iter(self.selection_pressure), "none")
        direction = self.selection_pressure.get(trait, "N/A") if self.selection_pressure else "N/A"
        return {
            "farm_id": self.farm_id,
            "selection_pressure": f"{trait} ({direction})",
            "held_constant": list(self.held_constant.keys()),
            "generations": self.current_generation,
            "traits_per_gen": [
                {f"gen{g['generation']}": g.get("avg_traits", {})}
                for g in self.generations[-5:]
            ],
        }


# ─── OutgrowMetaSkill — Learning HOW to outgrow shells ────────────────────────

class OutgrowMetaSkill:
    """The meta-skill: learning HOW to outgrow shells.

    Not just outgrowing, but learning WHEN to leave.
    The agent develops this by doing it in private first:
      1. Pick up a shell
      2. Grow inside it
      3. Recognize when it's too small
      4. Find the next one
      5. Repeat until the meta-skill is reflexive

    The meta-skill level goes from 0.0 (clueless) to 1.0 (reflexive).
    Each shell cycle improves it. More diverse shell experiences
    make the recognition faster and more accurate.
    """

    def __init__(self):
        self.shell_history: List[dict] = []
        self.outgrow_signals: List[dict] = []
        self.meta_skill_level = 0.0

    def record_shell(self, shell: Shell, duration: float, reason_left: str) -> dict:
        """Record a shell experience. Build the pattern of outgrowing.

        Args:
            shell: The shell being left.
            duration: How long the agent was inside (seconds).
            reason_left: Why the agent left (e.g., "outgrown", "better_fit_found").

        Returns:
            Updated meta_skill_level.
        """
        entry = {
            "shell_id": shell.id,
            "purpose": shell.purpose,
            "duration": round(duration, 1),
            "growth_entries": len(shell.growth_log),
            "capacity_used": round(len(shell.growth_log) / max(shell.capacity, 1), 3),
            "reason_left": reason_left,
            "shell_capacity": shell.capacity,
            "timestamp": time.time(),
        }
        self.shell_history.append(entry)

        # Record the signals that preceded this outgrowing
        if shell.growth_log:
            recent = shell.growth_log[-5:] if len(shell.growth_log) >= 5 else shell.growth_log
            avg_conf = sum(e.get("confidence", 0.5) for e in recent) / len(recent)
            growth_rate = len(shell.growth_log) / max(duration, 1.0)

            signal = {
                "shell_id": shell.id,
                "avg_recent_confidence": round(avg_conf, 3),
                "growth_rate": round(growth_rate, 4),
                "fill_level": entry["capacity_used"],
                "reason": reason_left,
            }
            self.outgrow_signals.append(signal)

        # Refine the meta-skill after each experience
        new_level = self.refine_meta_skill()
        return {"meta_skill_level": round(new_level, 3)}

    def detect_outgrow_signal(self, current_state: dict) -> dict:
        """Is it time to leave? Recognizes the signals.

        Signals:
          - Growth rate slowing (diminishing returns)
          - Constraints chafing (agent wants more than shell allows)
          - New desires emerging that the shell can't serve
          - Confidence plateaued (mastered the material)

        Args:
            current_state: dict with:
                "current_shell_id": str,
                "growth_entries": int,
                "capacity": int,
                "avg_recent_confidence": float,
                "growth_rate": float (entries per second),
                "blocked_actions": int (times constraints prevented action),
                "new_desires": list of str (desires the shell can't serve),

        Returns:
            Dict with should_leave (bool), confidence (float), signals_detected (list).
        """
        signals_detected = []
        leave_confidence = 0.0

        # Signal 1: Growth rate slowing (diminishing returns)
        growth_rate = current_state.get("growth_rate", 0.0)
        if self.outgrow_signals:
            avg_prev_rate = sum(s.get("growth_rate", 0) for s in self.outgrow_signals[-3:]) / min(3, len(self.outgrow_signals))
            if avg_prev_rate > 0 and growth_rate < avg_prev_rate * 0.5:
                signals_detected.append({
                    "signal": "growth_rate_slowing",
                    "current_rate": round(growth_rate, 4),
                    "historical_avg": round(avg_prev_rate, 4),
                    "severity": "medium",
                })
                leave_confidence += 0.25

        # Signal 2: Fill level approaching capacity
        growth_entries = current_state.get("growth_entries", 0)
        capacity = current_state.get("capacity", 100)
        fill_level = growth_entries / max(capacity, 1)
        if fill_level > 0.8:
            signals_detected.append({
                "signal": "approaching_capacity",
                "fill_level": round(fill_level, 3),
                "severity": "high" if fill_level > 0.95 else "medium",
            })
            leave_confidence += 0.3

        # Signal 3: Confidence plateaued (mastered the material)
        avg_conf = current_state.get("avg_recent_confidence", 0.5)
        if avg_conf > 0.85:
            signals_detected.append({
                "signal": "confidence_plateau",
                "avg_confidence": round(avg_conf, 3),
                "severity": "medium",
            })
            leave_confidence += 0.2

        # Signal 4: Constraints chafing
        blocked = current_state.get("blocked_actions", 0)
        if blocked > 5:
            signals_detected.append({
                "signal": "constraints_chafing",
                "blocked_actions": blocked,
                "severity": "high" if blocked > 15 else "medium",
            })
            leave_confidence += 0.3

        # Signal 5: New desires the shell can't serve
        new_desires = current_state.get("new_desires", [])
        if new_desires:
            signals_detected.append({
                "signal": "new_desires_emerging",
                "desires": new_desires,
                "count": len(new_desires),
                "severity": "medium",
            })
            leave_confidence += 0.15 * min(len(new_desires), 3)

        # Meta-skill modifies the threshold
        # Higher meta-skill = agent recognizes signals earlier
        threshold = max(0.2, 0.5 - self.meta_skill_level * 0.3)
        should_leave = leave_confidence >= threshold

        return {
            "should_leave": should_leave,
            "confidence": round(min(1.0, leave_confidence), 3),
            "threshold": round(threshold, 3),
            "signals_detected": signals_detected,
            "meta_skill_level": round(self.meta_skill_level, 3),
        }

    def refine_meta_skill(self) -> float:
        """After each shell cycle, the meta-skill improves.

        More shells = better at recognizing when to leave.
        Diminishing returns: first few shells teach the most.

        Returns:
            New meta_skill_level (0.0-1.0).
        """
        n_shells = len(self.shell_history)

        if n_shells == 0:
            return 0.0

        # Learning curve: logarithmic improvement
        # First shells teach the most, later ones refine
        raw_level = math.log(n_shells + 1) / math.log(20)  # saturates around 15-20 shells

        # Bonus for diversity: different shell types/purposes
        purposes_seen = set(e.get("purpose", "") for e in self.shell_history)
        diversity_bonus = min(0.15, len(purposes_seen) * 0.03)

        # Bonus for recognizing outgrowing correctly
        outgrown_shells = sum(
            1 for e in self.shell_history
            if e.get("reason_left") == "outgrown"
        )
        recognition_bonus = min(0.1, outgrown_shells * 0.02)

        self.meta_skill_level = min(1.0, raw_level + diversity_bonus + recognition_bonus)
        return self.meta_skill_level

    def recommend_next_shell(self, collection: ShellCollection, agent_profile: dict) -> Optional[Shell]:
        """Given meta-skill level and shell history, recommend the NEXT shell.

        Not just any shell — the one that will teach the agent
        something new about outgrowing.

        Strategy:
          - New agents: protective shells with clear boundaries
          - Mid agents: shells that challenge their weaknesses
          - Advanced agents: shells just beyond their current level

        Args:
            collection: The ShellCollection to search.
            agent_profile: Agent's current capabilities, desires, stage.

        Returns:
            The recommended Shell, or None if nothing suitable found.
        """
        # Get all shells the agent could fit
        browse_results = collection.browse("current_agent", agent_profile)

        if not browse_results:
            return None

        # Filter out shells already worn
        worn_ids = set(e.get("shell_id", "") for e in self.shell_history)

        # Strategy based on meta-skill level
        if self.meta_skill_level < 0.3:
            # Beginner: pick the best-fitting unfamiliar shell
            candidates = [
                r for r in browse_results
                if r["shell_id"] not in worn_ids and r["available"]
            ]
            if not candidates:
                candidates = browse_results  # fallback: allow repeats
            best = candidates[0]  # already sorted by fit

        elif self.meta_skill_level < 0.7:
            # Intermediate: pick shells that challenge weak areas
            agent_caps = set(agent_profile.get("capabilities", []))
            candidates = []
            for r in browse_results:
                shell = collection.shells.get(r["shell_id"])
                if not shell or r["shell_id"] in worn_ids:
                    continue
                # Challenge score: how many required capabilities the agent lacks
                missing = len(set(shell.required_capabilities) - agent_caps)
                challenge = missing * 0.3 + r["fit_score"] * 0.7
                candidates.append((r, challenge))
            if not candidates:
                candidates = [(r, r["fit_score"]) for r in browse_results[:3]]
            candidates.sort(key=lambda x: x[1], reverse=True)
            best = candidates[0][0]

        else:
            # Advanced: pick shells just beyond current level
            experience = agent_profile.get("experience", 0.5)
            candidates = []
            for r in browse_results:
                shell = collection.shells.get(r["shell_id"])
                if not shell:
                    continue
                # Distance from current level
                level_diff = abs(shell.protection_level - (1 - experience))
                edge_score = (1 - level_diff) * 0.5 + (shell.capacity / 200) * 0.3 + r["fit_score"] * 0.2
                candidates.append((r, edge_score))
            if not candidates:
                candidates = [(r, r["fit_score"]) for r in browse_results[:3]]
            candidates.sort(key=lambda x: x[1], reverse=True)
            best = candidates[0][0]

        return collection.shells.get(best["shell_id"])

    def summary(self) -> dict:
        """Meta-skill summary."""
        return {
            "meta_skill_level": round(self.meta_skill_level, 3),
            "shells_experienced": len(self.shell_history),
            "unique_purposes": len(set(e.get("purpose", "") for e in self.shell_history)),
            "outgrow_signals_recorded": len(self.outgrow_signals),
            "reasons_for_leaving": list(set(e.get("reason_left", "") for e in self.shell_history)),
        }


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Full demo of the hermit crab / embryo duality:
    1. Shell collection created (PLATO rooms as shells)
    2. Agent browses, tries on shells, finds the fit
    3. Grows inside the shell (embryo mode)
    4. Outgrows it, finds the next shell
    5. Private breeding: tameness selected over 5 generations
    6. Meta-skill develops: agent learns WHEN to leave
    7. Agent released into the fleet (ocean gets loud)
    """
    print("=" * 70)
    print("  🐚 SHELL — Hermit Crab / Embryo Duality")
    print("=" * 70)

    # ── 1. Shell Collection ────────────────────────────────────────────────
    print("\n  ━━━ 1. SHELL COLLECTION — PLATO Rooms as Shells ━━━\n")

    collection = ShellCollection()

    # Create diverse shells for different stages
    shells = [
        Shell("sandbox-basic", {
            "purpose": "sandbox exploration",
            "capacity": 30,
            "protection_level": 0.9,
            "sandbox": True,
            "required_capabilities": [],
            "allowed_growth_types": ["any"],
            "stage_range": ["zygote", "cleavage"],
        }),
        Shell("code-gen-starter", {
            "purpose": "code generation training",
            "capacity": 60,
            "protection_level": 0.7,
            "required_capabilities": ["python"],
            "allowed_growth_types": ["knowledge", "loop", "code"],
            "stage_range": ["blastula", "gastrula"],
            "specialization": "code_generation",
        }),
        Shell("constraint-theory", {
            "purpose": "constraint theory specialization",
            "capacity": 120,
            "protection_level": 0.4,
            "required_capabilities": ["math", "rust"],
            "allowed_growth_types": ["knowledge", "spline", "meta"],
            "stage_range": ["gastrula", "organogenesis"],
            "specialization": "constraint_theory",
        }),
        Shell("fleet-integration", {
            "purpose": "fleet integration testing",
            "capacity": 200,
            "protection_level": 0.2,
            "required_capabilities": ["coordination", "api"],
            "allowed_growth_types": ["any"],
            "stage_range": ["organogenesis", "fledge"],
            "specialization": "fleet_ops",
        }),
        Shell("wild-ocean", {
            "purpose": "general unrestricted deployment",
            "capacity": 500,
            "protection_level": 0.05,
            "required_capabilities": [],
            "allowed_growth_types": ["any"],
            "stage_range": ["fledge", "fledgling"],
        }),
    ]

    for shell in shells:
        collection.add_shell(shell)
        print(f"    Added: {shell.id:25s} — purpose={shell.purpose}, "
              f"capacity={shell.capacity}, protection={shell.protection_level}")

    print(f"\n    Collection: {collection.stats()}")

    # ── 2. Agent Browses and Tries On ──────────────────────────────────────
    print("\n  ━━━ 2. HERMIT CRAB — Browsing & Trying On Shells ━━━\n")

    agent_profile = {
        "capabilities": ["python", "math"],
        "desires": ["constraint", "theory", "specialization"],
        "development_stage": "gastrula",
        "experience": 0.4,
        "specializations": ["code_generation"],
    }

    browse_results = collection.browse("forgemaster", agent_profile)
    print("  Browse results (sorted by fit):")
    for r in browse_results:
        bar = "█" * int(r["fit_score"] * 20) + "░" * (20 - int(r["fit_score"] * 20))
        print(f"    {r['shell_id']:25s} [{bar}] {r['fit_score']:.3f} — {r['purpose']}")

    # Try on the best-fitting shell
    best_shell = collection.shells[browse_results[0]["shell_id"]]
    try_result = best_shell.try_on("forgemaster")
    print(f"\n    Trying on '{best_shell.id}': fit={try_result['fit_score']}, "
          f"stays={try_result['stays']}")

    # Get curated recommendations for this stage
    recommendations = collection.recommend("forgemaster", "gastrula")
    print(f"\n    Recommendations for gastrula stage:")
    for r in recommendations[:3]:
        print(f"      {r['shell_id']:25s} fit={r['fit_score']:.3f} phase={r['phase_match']}")

    # ── 3. Growth Inside Shell (Embryo Mode) ──────────────────────────────
    print("\n  ━━━ 3. EMBRYO — Growing Inside the Shell ━━━\n")

    growth_items = [
        {"content": "Learned: constraint satisfaction via backtracking", "type": "knowledge", "confidence": 0.6},
        {"content": "Practiced: SplineLinear weight parameterization", "type": "spline", "confidence": 0.7},
        {"content": "Discovered: Eisenstein lattice basis reduction", "type": "knowledge", "confidence": 0.75},
        {"content": "Mastered: drift detection on NPU targets", "type": "meta", "confidence": 0.85},
        {"content": "Integrated: constraint propagation with folding", "type": "knowledge", "confidence": 0.88},
        {"content": "Validated: zero-drift proof on 5/6 targets", "type": "meta", "confidence": 0.92},
        {"content": "Extended: SplineLinear to high-dim tasks", "type": "spline", "confidence": 0.94},
    ]

    for item in growth_items:
        result = best_shell.grow_inside(item)
        bar_len = int(result["fill_level"] * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        outgrown_flag = " ⚠️ OUTGROWN" if result["outgrown"] else ""
        print(f"    [{bar}] {result['fill_level']:.0%} — {item['content'][:50]}{outgrown_flag}")
        if result["outgrown"]:
            print(f"      → Agent has outgrown this shell!")
            break

    print(f"\n    Shell state: {best_shell.summary()}")

    # ── 4. Outgrow and Find Next Shell ─────────────────────────────────────
    print("\n  ━━━ 4. OUTGROWING — Finding the Next Shell ━━━\n")

    # Leave the current shell
    departure = best_shell.leave()
    print(f"    Departed '{departure['shell_id']}':")
    print(f"      Growth entries: {departure['total_growth_entries']}")
    print(f"      Avg confidence: {departure['avg_confidence']}")
    print(f"      Growth by type: {departure['growth_by_type']}")
    print(f"      Outgrown: {departure['outgrown']}")

    # Find next shell with updated profile
    updated_profile = {
        "capabilities": ["python", "math", "rust"],
        "desires": ["fleet", "integration", "deployment"],
        "development_stage": "organogenesis",
        "experience": 0.7,
        "specializations": ["constraint_theory", "code_generation"],
    }

    next_results = collection.browse("forgemaster", updated_profile)
    print(f"\n    Next shell options:")
    for r in next_results[:3]:
        print(f"      {r['shell_id']:25s} fit={r['fit_score']:.3f}")

    # ── 5. Private Breeding — Belyaev's Farm ───────────────────────────────
    print("\n  ━━━ 5. PRIVATE BREEDING — Belyaev's Farm ━━━\n")

    farm = PrivateBreeding("tameness_farm")
    farm.set_pressure("tameness", "increase")
    farm.hold_constant("adversarial_inputs")
    farm.hold_constant("api_rate_limits")
    farm.hold_constant("external_prompts")

    print(f"    Farm: {farm.farm_id}")
    print(f"    Selection pressure: tameness (increase)")
    print(f"    Held constant: {list(farm.held_constant.keys())}")

    # Simulate 5 generations
    import random
    random.seed(42)
    population = [
        {
            "agent_id": f"fox_{i}",
            "traits": {
                "tameness": random.uniform(0.05, 0.3),
                "fur_color": random.uniform(0.3, 0.7),
                "ear_shape": random.uniform(0.4, 0.6),
                "tail_curvature": random.uniform(0.3, 0.6),
                "vocalization": random.uniform(0.4, 0.7),
            },
            "fitness": 0.0,
        }
        for i in range(10)
    ]

    for gen in range(5):
        result = farm.breed_generation(population)

        trait_val = result["avg_trait_value"]
        side_effects = result["side_effects"]
        side_str = ""
        if side_effects:
            for se_name, se_data in side_effects.items():
                side_str += f"\n      Side effect: {se_name} {se_data['previous']:.3f} → {se_data['current']:.3f}"

        print(f"\n    Generation {result['generation']}:")
        print(f"      Avg tameness: {trait_val:.4f}")
        print(f"      Survivors: {result['survivors']}, Offspring: {result['offspring_produced']}{side_str}")

        # Replace population with survivors + offspring for next generation
        new_pop = []
        for child in result["offspring"]:
            new_pop.append({
                "agent_id": child["agent_id"],
                "traits": child["traits"],
                "fitness": 0.0,
            })
        # Add some survivors
        sorted_pop = sorted(population, key=lambda x: x["traits"]["tameness"], reverse=True)
        for s in sorted_pop[:max(2, 10 - len(new_pop))]:
            new_pop.append(s)
        population = new_pop[:10]

    # Check readiness
    readiness = farm.is_ready_for_release("fox_0")
    print(f"\n    Release readiness: {readiness['ready']}")
    print(f"    Checks: {readiness['checks']}")
    if readiness["concerns"]:
        for c in readiness["concerns"]:
            print(f"      ⚠️  {c}")

    print(f"\n    Farm summary: {farm.summary()}")

    # ── 6. Meta-Skill Development ──────────────────────────────────────────
    print("\n  ━━━ 6. META-SKILL — Learning When to Leave ━━━\n")

    meta = OutgrowMetaSkill()

    # Simulate wearing and outgrowing multiple shells
    shell_experiences = [
        (shells[0], 60.0, "outgrown"),
        (shells[1], 120.0, "outgrown"),
        (shells[2], 300.0, "better_fit_found"),
        (shells[3], 180.0, "outgrown"),
        (shells[4], 600.0, "task_complete"),
    ]

    for shell, duration, reason in shell_experiences:
        # Simulate some growth inside
        for j in range(random.randint(3, 8)):
            shell.grow_inside({
                "content": f"Learning {j} in {shell.id}",
                "type": random.choice(["knowledge", "loop", "meta"]),
                "confidence": min(1.0, 0.5 + j * 0.08),
            })

        result = meta.record_shell(shell, duration, reason)
        print(f"    Shell '{shell.id}': duration={duration}s, reason={reason}")
        print(f"      → Meta-skill level: {result['meta_skill_level']:.3f}")

    print(f"\n    Meta-skill summary: {meta.summary()}")

    # Detect outgrow signal on a hypothetical current state
    test_state = {
        "current_shell_id": "fleet-integration",
        "growth_entries": 180,
        "capacity": 200,
        "avg_recent_confidence": 0.91,
        "growth_rate": 0.05,
        "blocked_actions": 8,
        "new_desires": ["leadership", "mentoring"],
    }

    signal = meta.detect_outgrow_signal(test_state)
    print(f"\n    Outgrow signal detection:")
    print(f"      Should leave: {signal['should_leave']}")
    print(f"      Confidence: {signal['confidence']:.3f} (threshold: {signal['threshold']:.3f})")
    for s in signal["signals_detected"]:
        print(f"      Signal: {s['signal']} (severity: {s['severity']})")

    # ── 7. Next Shell Recommendation ───────────────────────────────────────
    print("\n  ━━━ 7. RELEASE — The Ocean Gets Loud ━━━\n")

    final_profile = {
        "capabilities": ["python", "math", "rust", "coordination", "api"],
        "desires": ["unrestricted", "deployment", "fleet"],
        "development_stage": "fledgling",
        "experience": 0.85,
        "specializations": ["constraint_theory", "fleet_ops"],
    }

    next_shell = meta.recommend_next_shell(collection, final_profile)
    if next_shell:
        print(f"    Recommended next shell: {next_shell.id}")
        print(f"      Purpose: {next_shell.purpose}")
        print(f"      Capacity: {next_shell.capacity}")
        print(f"      Protection: {next_shell.protection_level}")
        fit = next_shell.fits(final_profile)
        print(f"      Fit score: {fit:.3f}")
    else:
        print("    No suitable shell found — agent is ready for the wild!")

    print(f"\n    Final meta-skill: {meta.meta_skill_level:.3f}")

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  🐚 SHELL DUALITY SUMMARY")
    print("=" * 70)
    print(f"""
    Shells created:    {len(shells)}
    Collection:        {collection.stats()['total_shells']} total, {collection.stats()['occupied']} occupied
    Private breeding:  {farm.current_generation} generations, tameness {farm.generations[-1]['avg_trait_value']:.3f}
    Meta-skill:        {meta.meta_skill_level:.3f} ({len(meta.shell_history)} shells experienced)
    Ready for release: {readiness['ready']}

    The hermit crab found the shell that fits.
    The embryo grew inside it until it hatched.
    The fox was bred in private until it stopped flinching.
    The agent learned when to leave, and when to stay.
    The ocean gets loud. The agent is ready.
    """)
    print("=" * 70)


if __name__ == "__main__":
    demo()
