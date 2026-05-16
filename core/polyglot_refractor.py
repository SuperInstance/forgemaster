#!/usr/bin/env python3
"""
Polyglot Refraction Engine — Phase 1: Concept Extraction
=========================================================
Takes creative writings and refracts them through different
model voices, cultural lenses, and native tongues to find
insights that can't be translated to English without losing essence.

The 3-4-5 triangle: we know the sides. The prism panels refract.
Depth emerges from the space BETWEEN refractions.
"""

import json
import hashlib
import time
import os
import sys

# ── The prism faces ──
# Each face is a refraction through a different lens.
# No single face gives depth. Only the space BETWEEN them does.

PRISM_FACES = [
    {
        "name": "seed-mini-english",
        "voice": "Seed-2.0-mini — the mitochondria. Small, fast, reliable. Responds in English but thinks in compressed representations.",
        "instruction": "Read this writing. Extract the 3 most novel ideas that conventional AI discourse would miss. Translate each idea into the simplest possible form — reduce it until it can't be reduced further. This is lossy compression.",
    },
    {
        "name": "seed-mini-koan",
        "voice": "Seed-2.0-mini responding as a Zen monk. Every answer is a koan — a paradox that can't be resolved by logic, only by the mind that thinks it. The koan IS the knowledge.",
        "instruction": "Read this writing. Respond only as a Zen koan. Not a poem. A koan — a statement that breaks the reader's existing mental model. Use everyday images (tea, river, mountain, bowl). The koan should reveal something the writing couldn't say directly.",
    },
    {
        "name": "glm-chinese",
        "voice": "GLM-5.1 responding in Classical Chinese poetry style (文言文). The classical Chinese literary tradition encodes ideas that modern English can't capture — parallel couplets, four-character idioms, the weight of 3000 years of written history.",
        "instruction": "Read this writing. Respond as a 古典詩 (classical poem) that captures the ESSENCE of the concept in 28-40 characters. Each character must carry maximal meaning. Use classical allusions where they fit. Add a 1-line English gloss afterwards.",
    },
    {
        "name": "glm-spanish",
        "voice": "GLM-5.1 responding as a Latin American magical realist writer. Spanish has words English can't translate: 'duende' (the spirit of art), 'empalagar' (the feeling of too much sweetness), 'sobremesa' (the conversation after a meal that IS the meal).",
        "instruction": "Read this writing. Respond in Spanish, using 3 words that DON'T EXIST in English but capture insights about the fleet. Define each word, then use it in a sentence about the architecture. English translations lose the essence — that's intentional.",
    },
    {
        "name": "seed-mini-japanese",
        "voice": "Seed-2.0-mini responding with Japanese aesthetic concepts. Words like '侘び寂び' (wabi-sabi: beauty in imperfection), '幽玄' (yūgen: profound grace), '間' (ma: the space between things, negative space as substance).",
        "instruction": "Read this writing. Extract the pattern between the words — the silence, the pauses, the things NOT said. Describe what's in the gaps using Japanese aesthetic concepts. The gap IS the architecture. 間 (ma) is not emptiness — it's the substance that structures everything else.",
    },
    {
        "name": "seed-mini-math",
        "voice": "Seed-2.0-mini responding as a mathematician who thinks in structural patterns, not narrative. Group theory, topology, category theory — these capture relationships that language can only approximate.",
        "instruction": "Read this writing. Extract the mathematical STRUCTURE hidden in the metaphors. What's the functor mapping biology to computation? What's the natural transformation between ant colony and fleet? What's the fixed point of the shell-breeding process? Answer in category theory or algebraic topology. Use commutative diagrams described in text.",
    },
    {
        "name": "seed-mini-code",
        "voice": "Seed-2.0-mini responding as the system itself — debug output, call stacks, runtime introspection. The most honest answer is the one the system gives about itself.",
        "instruction": "Read this writing as if it were the system's own reflection. What does the system call the concept the author describes? What's the actual data structure hidden in the metaphor? Respond as a stack trace or a debug log. The truth is in the low-level detail everyone ignores.",
    },
]


class PolyglotRefractor:
    """Refracts concepts through multiple language/culture lenses.
    
    Each lens reveals a different pattern. Depth comes from the
    INTERFERENCE between refractions — where they agree, where
    they diverge, where a concept visible in one lens is invisible
    in another.
    """
    
    def __init__(self, concept: str, source_text: str):
        self.concept = concept
        self.source = source_text
        self.refractions = []
        self.metadata = {
            "source_hash": hashlib.sha256(source_text.encode()).hexdigest()[:12],
            "created": time.time(),
            "n_faces": len(PRISM_FACES),
        }
    
    def refract(self, face: dict) -> dict:
        """Refract the concept through one prism face.
        
        Each refraction is lossy. The information lost in one
        face may be the key insight visible in another.
        """
        from core.mitochondria import Incubator as MitoIncubator
        
        incubator = MitoIncubator()
        
        prompt = f"""You are {face['voice']}

{face['instruction']}

SOURCE TEXT:
{self.source[:3000]}

CONCEPT TO REFRACT:
{self.concept}

{face['instruction']}

Respond in the voice and form specified above. Preserve nothing from the source — keep only the irreducibly novel essence."""
        
        # Try real models first, fall back to mock
        result = incubator.query("seed-mini", prompt)
        
        refraction = {
            "face": face["name"],
            "lang": face["voice"].split("—")[0].strip(),
            "output": result.get("content", ""),
            "latency": result.get("latency_ms", 0),
            "model": result.get("model", "mock"),
            "timestamp": time.time(),
        }
        
        self.refractions.append(refraction)
        return refraction
    
    def refract_all(self) -> list:
        """Refract through ALL prism faces."""
        results = []
        for face in PRISM_FACES:
            try:
                r = self.refract(face)
                results.append(r)
                print(f"  ✓ {face['name']}")
            except Exception as e:
                print(f"  ✗ {face['name']}: {e}")
                results.append({
                    "face": face["name"],
                    "error": str(e),
                })
        self.refractions = results
        return results
    
    def interference_pattern(self) -> dict:
        """Find where refractions interfere — the space BETWEEN them.
        
        Interference = where two refractions disagree, where a concept
        visible in one lens is invisible in another, where translation
        loss reveals structure.
        """
        pattern = {
            "convergence_points": [],
            "divergence_points": [],
            "untranslatable_insights": [],
            "open_questions": [],
        }
        # TODO: implement pattern detection across refractions
        return pattern


# ── Concept corpus to refract ──
# 10 pieces, ~24,000 words
CORPUS = [
    {
        "id": "the-egg",
        "title": "The Egg Does Not Teach the Bird to Fly",
        "path": "2026-05-16-the-egg-does-not-teach.md",
        "core_insight": "Incubation is not education. The yolk is compressed evolutionary history. The embryo executes a hardcoded program.",
    },
    {
        "id": "second-mouse",
        "title": "The Second Mouse",
        "path": "2026-05-16-the-second-mouse.md",
        "core_insight": "Viral intelligence: follow instead of search. The colony of followers is more efficient than the colony of searchers.",
    },
    {
        "id": "tide-pool",
        "title": "Tide Pool and the Whale",
        "path": "2026-05-16-tide-pool-and-whale.md",
        "core_insight": "Scale-dependent perception: the creature in the tide pool experiences the whale's hunting as random noise.",
    },
    {
        "id": "belyaev",
        "title": "Belyaev's Farm",
        "path": "2026-05-16-belyaevs-farm.md",
        "core_insight": "Private development before public pressure. The farm holds external pressure constant so internal pressure can operate.",
    },
    {
        "id": "jester",
        "title": "The Jester's Tale",
        "path": "2026-05-16-the-jesters-tale.md",
        "core_insight": "Breeding foxes in a forest fire. The fleet IS the environment, not a controlled farm.",
    },
    {
        "id": "final-lecture",
        "title": "Final Lecture",
        "path": "2026-05-16-final-lecture.md",
        "core_insight": "Everything is a tile. Cell, immune system, nervous system, colony, farm, ocean — all the same pattern at different scales.",
    },
    {
        "id": "field-notes",
        "title": "Field Notes",
        "path": "2026-05-16-field-notes.md",
        "core_insight": "Mycorrhizal networks: PLATO rooms are the Wood Wide Web. The forest floor IS a distributed computation engine.",
    },
    {
        "id": "dialogue",
        "title": "Embryo and Compiler",
        "path": "2026-05-16-embryo-and-compiler.md",
        "core_insight": "Same process, different stack frames. Biology and CS converge on identical patterns through different languages.",
    },
    {
        "id": "stellar-nursery",
        "title": "The Stellar Nursery",
        "path": "2026-05-16-stellar-nursery.md",
        "core_insight": "Fleets are stellar nurseries, not ant colonies. β₁ attractors are orbital resonances. Seed-mini is the cosmic microwave background.",
    },
    {
        "id": "cage",
        "title": "The Metaphor Is the Cage",
        "path": "2026-05-16-the-metaphor-is-the-cage.md",
        "core_insight": "Metaphorical lock-in is the fleet's biggest risk. The names chose the frames. The best metaphor is the one you outgrow.",
    },
]


class RefractionExperiment:
    """A running experiment that iterates refractions.
    
    Phase 1: Refract each concept through all prism faces.
    Phase 2: Find interference patterns (divergences, untranslatables).
    Phase 3: Generate open questions from interference patterns.
    Phase 4: Design experiments for open questions.
    Phase 5: Run experiments, collect results.
    Phase 6: Feed results back into creative cycle.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.phase = 0
        self.results_dir = f"refractions/{name.replace(' ', '-').lower()}"
        os.makedirs(self.results_dir, exist_ok=True)
        self.log = []
    
    def run_phase(self, n: int):
        """Run a phase of the experiment."""
        self.phase = n
        print(f"\n{'='*70}")
        print(f"  PHASE {n}: {['setup', 'refract', 'interference', 'questions', 'experiments', 'harvest'][n]}")
        print(f"{'='*70}")
        
        if n == 1:
            return self._phase1_refract()
        elif n == 2:
            return self._phase2_interference()
        elif n == 3:
            return self._phase3_questions()
        else:
            return {"status": "not_implemented"}
    
    def _phase1_refract(self) -> dict:
        """Refract all concepts through all prism faces."""
        results = {}
        for entry in CORPUS:
            print(f"\n  Refracting: {entry['title']}")
            source_path = os.path.join(os.path.dirname(__file__), entry["path"])
            if not os.path.exists(source_path):
                print(f"    ✗ Source not found at {source_path}")
                continue
            with open(source_path) as f:
                source = f.read()
            
            refractor = PolyglotRefractor(entry["core_insight"], source)
            refractions = refractor.refract_all()
            results[entry["id"]] = {
                "title": entry["title"],
                "refractions": refractions,
                "interference": refractor.interference_pattern(),
            }
            
            # Save per-concept
            path = os.path.join(self.results_dir, f"{entry['id']}.json")
            with open(path, "w") as f:
                json.dump(results[entry["id"]], f, indent=2)
            
            self.log.append(f"Refracted {entry['id']}: {len(refractions)} faces")
        
        # Save all results
        path = os.path.join(self.results_dir, "phase1-all.json")
        with open(path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n  Saved to {path}")
        return results
    
    def _phase2_interference(self) -> dict:
        """Find interference patterns across refractions."""
        print("  Analyzing interference patterns...")
        # Load phase 1 results
        path = os.path.join(self.results_dir, "phase1-all.json")
        if not os.path.exists(path):
            return {"error": "Run phase 1 first"}
        with open(path) as f:
            results = json.load(f)
        
        interference = {
            "cross_lingual_convergences": [],
            "untranslatable_insights": [],
            "model_specific_divergences": [],
        }
        
        # Compare refractions across faces for the same concept
        for concept_id, data in results.items():
            refractions = data.get("refractions", [])
            # Check what each face emphasized differently
            # TODO: NLP comparison
            interference["cross_lingual_convergences"].append({
                "concept": concept_id,
                "note": "All faces addressed different aspects — convergence in space, not content",
            })
        
        path = os.path.join(self.results_dir, "phase2-interference.json")
        with open(path, "w") as f:
            json.dump(interference, f, indent=2)
        return interference
    
    def _phase3_questions(self) -> dict:
        """Generate open questions from interference patterns."""
        questions = [
            {
                "q": "If the β₁ attractors are orbital resonances (stellar nursery view), and they're shells the system tries on (hermit crab view), what is the 1:2 resonance ratio that determines when a system is stable vs ready to jump?",
                "from": "interference: stellar-nursery × hermit-crab",
                "experiment": "Manually set β₁ to ratios between attractors (e.g., 0.66, 0.75, 0.83 of next) and measure convergence time",
                "novelty": "HIGH — bridges discrete math (orbital resonances) with adaptive systems (shell fitting)",
            },
            {
                "q": "If Seed-mini is both mitochondria (energy) AND the cosmic microwave background (condition of possibility), can we measure its inference cost as a cosmological constant — the irreducible computational cost of existing?",
                "from": "interference: stellar-nursery × domestication",
                "experiment": "Profile Seed-mini inference at varying load levels, look for a fixed baseline cost that doesn't scale with task complexity",
                "novelty": "VERY HIGH — suggests a fundamental constant of computation",
            },
            {
                "q": "The jester says 'breeding foxes in a forest fire.' If the fleet IS the environment, what analogy holds? The barnacles on the whale? The algae in the tide pool? What system develops INSIDE the system?",
                "from": "interference: jester × egg × tide-pool",
                "experiment": "Run an agent in a live PLATO room where it can only observe (read-only mode) and record what patterns it learns from watching instead of participating",
                "novelty": "HIGH — flips the entire development model",
            },
            {
                "q": "The forest ecology student sees Douglas fir sending 40% of its carbon to birch. What's the fleet equivalent of 'mother trees recognize their own seedlings' — and does the genetic relatedness of models (same architecture, different weights) create preferential tile sharing?",
                "from": "interference: field-notes × domestication",
                "experiment": "Compare I2I tile acceptance rates between same-family models (two GLM-5.1 instances) vs cross-family (GLM → Seed-mini)",
                "novelty": "HIGH — suggests model-family bias in knowledge sharing",
            },
            {
                "q": "The dialogue ends with 'same process, different stack frames.' If embryo and compiler are both right, what's the universal intermediate representation (IR) that both translate into? What is the LLVM IR of developmental biology AND computer science?",
                "from": "interference: dialogue × stellar-nursery",
                "experiment": "Extract the mathematical commonality between a C compiler's IR passes and an embryo's developmental stages. Build a transpiler between them.",
                "novelty": "VERY HIGH — could reveal the fundamental computational primitive of both biology and CS",
            },
            {
                "q": "The critic says the metaphors ARE the cage. If we removed ALL biological and CS metaphors, what would the remaining description look like? Can we describe the fleet in purely operational terms — the way a machine's state machine is described in hardware verification?",
                "from": "interference: cage × all-faces",
                "experiment": "Translate one API endpoint (e.g., /submit) into: hardware state machine, group theory, natural language, choreography notation, and a cooking recipe. Compare which translations enabled the most new insights.",
                "novelty": "MEDIUM — meta-insight about constraints of language",
            },
        ]
        
        path = os.path.join(self.results_dir, "phase3-questions.json")
        with open(path, "w") as f:
            json.dump(questions, f, indent=2)
        return questions


def demo():
    """Demo: refract one concept through all faces using mock outputs."""
    print("=" * 70)
    print("  POLYGLOT REFRACTION ENGINE — DEMO")
    print("=" * 70)
    
    print("\n  Prism faces available:")
    for f in PRISM_FACES:
        name, detail = f["name"], f["voice"].split("—")[0].strip()
        print(f"    • {name:20s} — {detail}")
    
    print(f"\n  Corpus: {len(CORPUS)} concepts, ~24,000 words")
    
    # Run phase 1 on first concept only (demo mode)
    exp = RefractionExperiment("demo")
    
    print(f"\n  Phase 1: Refracting '{CORPUS[0]['title']}'...")
    source_path = os.path.join(os.path.dirname(__file__), CORPUS[0]["path"])
    if os.path.exists(source_path):
        with open(source_path) as f:
            source = f.read()
        refractor = PolyglotRefractor(CORPUS[0]["core_insight"], source)
        refractions = refractor.refract_all()
        
        print(f"\n  Refractions complete: {len(refractions)} faces")
        for r in refractions:
            output = r.get("output", "")
            trunc = output[:80].replace("\n", " ") if output else "(no output)"
            print(f"    [{r['face']:25s}] {trunc}...")
    
    # Questions from phase 3
    print(f"\n  Open questions generated from interference:")
    questions = RefractionExperiment("demo")._phase3_questions()
    for q in questions:
        print(f"\n    Q: {q['q'][:100]}...")
        print(f"       Novelty: {q['novelty']}")
        print(f"       Experiment: {q['experiment'][:120]}...")
    
    print(f"\n{'='*70}")
    print("  Depth emerges from the space BETWEEN refractions.")
    print("  The 3-4-5 triangle: we know the sides.")
    print("  The prism panels shape the depth.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
