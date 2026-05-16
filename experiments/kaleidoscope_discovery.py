#!/usr/bin/env python3
"""
Kaleidoscope Discovery Engine
==============================
Metaphor rotation as a discovery mechanism.

The insight: different metaphors are different LENSES. Each lens has chromatic
aberration — it distorts some wavelengths and lets others through. By rotating
through lenses and comparing the aberrations, you don't get a better picture of
the concept. You get a PICTURE OF THE LENSES. And the picture of the lenses
IS the architecture.

Usage:
    python3 kaleidoscope_discovery.py "disproof gate"
    python3 kaleidoscope_discovery.py "tile lifecycle" --metaphors 6
"""

import json
import hashlib
import itertools
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class MetaphorReframing:
    """One metaphor lens applied to a concept."""
    domain: str                   # e.g. "biology", "city planning"
    concept_translation: str      # How the concept maps into this domain
    reveals: list[str]            # What this lens makes visible
    hides: list[str]              # What this lens distorts or obscures
    tension_points: list[str]     # Where the metaphor strains / breaks
    novel_questions: list[str]    # Questions ONLY this lens can generate


@dataclass
class RotationPair:
    """Comparison between two adjacent metaphor lenses."""
    lens_a: str
    lens_b: str
    revealed_by_rotation: list[str]   # B sees what A hid
    hidden_by_rotation: list[str]     # A saw what B hides
    emergent_questions: list[str]     # Questions from the DIFFERENCE


@dataclass
class DiscoveryReport:
    """Full output of a kaleidoscope run."""
    concept: str
    timestamp: str
    reframings: list[dict]
    rotation_pairs: list[dict]
    meta_questions: list[str]         # Questions no single lens could produce
    lens_portrait: dict               # What the rotation reveals about the LENSES
    discovery_score: float            # Rough metric: how much novelty emerged
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Metaphor domain definitions
# ---------------------------------------------------------------------------

METAPHOR_DOMAINS = {
    "biology": {
        "ontology": ["organism", "cell", "membrane", "metabolism", "apoptosis",
                      "mutation", "immune response", "symbiosis", "parasitism"],
        "dynamics": "growth, decay, adaptation, reproduction, selection pressure",
        "blind_spot": "tends to naturalize — makes everything seem inevitable",
    },
    "city_planning": {
        "ontology": ["district", "highway", "zoning", "permit", "inspector",
                      "traffic", "gridlock", "gentrification", "infrastructure"],
        "dynamics": "flow, congestion, regulation, growth boundaries, rezoning",
        "blind_spot": "assumes top-down order — hides emergent self-organization",
    },
    "music": {
        "ontology": ["note", "chord", "rhythm", "harmony", "dissonance",
                      "tempo", "cadence", " improvisation", "score", "silence"],
        "dynamics": "tension, resolution, syncopation, modulation, dynamics",
        "blind_spot": "temporal bias — everything becomes sequential, misses static structure",
    },
    "weather": {
        "ontology": ["front", "pressure", "storm", "convection", "jet stream",
                      "humidity", "barrier", "precipitation", "cyclone"],
        "dynamics": "accumulation, release, fronts colliding, prediction limits",
        "blind_spot": "deterministic bias — suggests patterns exist even where they don't",
    },
    "chinese_poetry": {
        "ontology": ["image", "juxtaposition", "blank space", "resonance",
                      "allusion", "parallel couplet", "unsaid", "gesture"],
        "dynamics": "suggestion, omission, echo, restraint, layered meaning",
        "blind_spot": "aesthetic bias — makes everything seem intentional art",
    },
    "geology": {
        "ontology": ["stratum", "fault", "erosion", "pressure", "subduction",
                      "uplift", "crystal", "sediment", "tectonic plate"],
        "dynamics": "deep time, compaction, sudden release, layering, folding",
        "blind_spot": "fatalism — everything seems predetermined by deep forces",
    },
    "legal_system": {
        "ontology": ["statute", "precedent", "verdict", "evidence", "jurisdiction",
                      "appeal", "burden of proof", "standing", "enforcement"],
        "dynamics": "adversarial process, jurisdictional conflict, precedent binding",
        "blind_spot": "procedural bias — assumes rules are the real structure",
    },
    "software": {
        "ontology": ["function", "type", "compiler", "test", "branch", "merge",
                      "dependency", "runtime", "crash", "assertion"],
        "dynamics": "compilation, testing, deployment, failure modes, edge cases",
        "blind_spot": "formalization bias — assumes everything can be specified",
    },
}

# Domain-specific reframing engines — maps concept properties to each domain
# Each returns a MetaphorReframing

def reframe_in_domain(concept: str, domain: str) -> MetaphorReframing:
    """Generate a metaphor reframing of `concept` in `domain`."""
    d = METAPHOR_DOMAINS[domain]
    ont = d["ontology"]
    dyn = d["dynamics"]
    blind = d["blind_spot"]

    # The reframing logic is domain-aware but concept-driven
    # We use a structured approach per domain

    if domain == "biology":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as an immune checkpoint — a membrane gate that distinguishes self from non-self before allowing passage",
            reveals=[
                "The SELECTIVITY of the gate — not just pass/fail but recognition-based",
                "The cost of false positives/negatives (autoimmune disease vs infection)",
                "The gate as a living membrane that can itself mutate or degrade",
                "Symbiont relationships — some 'threats' are actually beneficial",
                "Gate fatigue — immune checkpoints can be overwhelmed by volume",
            ],
            hides=[
                "Intentionality — biology has no designer, but gates might need one",
                "External audit — immune systems don't keep logs for review",
                "Reversible decisions — apoptosis is final, gates might need undo",
            ],
            tension_points=[
                "Self vs non-self is fuzzy in biology (mitochondria were 'non-self' once)",
                "Immune evasion is evolution's arms race — gates will always be tested",
                "The gate IS part of the organism, not external to it",
            ],
            novel_questions=[
                "What is the 'autoimmune disease' of a disproof gate — when does it reject valid proofs?",
                "Can a gate develop 'immune memory' — faster rejection of known-bad patterns?",
                "What happens when the gate itself is a symbiont with the thing it's gating?",
            ],
        )

    elif domain == "city_planning":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as a building inspection checkpoint — no certificate of occupancy until the inspector signs off",
            reveals=[
                "The gate as a REGULATORY function — it exists for public safety, not for itself",
                "Multiple inspectors with different specializations (structural, electrical, fire)",
                "The gate creates a QUEUE — throughput matters, not just correctness",
                "Building codes evolve — yesterday's gate criteria may be obsolete",
                "Political dimension — inspectors can be bribed, influenced, or understaffed",
            ],
            hides=[
                "Organic/emergent validity — some structures work without inspection",
                "The gate's effect on what gets built (people build to pass inspection)",
                "Global vs local standards — different cities, different gates",
            ],
            tension_points=[
                "Speed vs thoroughness — the queue grows if inspection is rigorous",
                "Who inspects the inspectors? Meta-gating problem",
                "Inspection assumes a static artifact; what if the building keeps changing?",
            ],
            novel_questions=[
                "What's the 'zoning variance' of a disproof gate — can you get an exception?",
                "Does the gate incentivize 'builder-proof' proofs that pass inspection but are hollow?",
                "What happens when the building code changes while construction is underway?",
            ],
        )

    elif domain == "music":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as a cadence — a harmonic resolution point that confirms the key before the piece can proceed",
            reveals=[
                "The gate as a TEMPORAL event — it happens in time, not just in logic",
                "Tension before resolution — the gate creates anticipation, not just verification",
                "Multiple valid resolutions (perfect cadence, plagal, deceptive)",
                "The performer's interpretation — same gate, different musicians, different results",
                "Dissonance as information — a 'failed' gate is musically meaningful",
            ],
            hides=[
                "Persistent state — music is ephemeral, gates leave residue",
                "Concurrency — music is usually one timeline, gates may be parallel",
                "The score vs the performance — specification vs execution",
            ],
            tension_points=[
                "Deceptive cadences — the ear expects resolution but gets deflected",
                "Improvisation around the gate — can you 'play through' without resolving?",
                "Cultural dependency — cadences work differently in different musical traditions",
            ],
            novel_questions=[
                "Is there a 'deceptive cadence' in proof — something that looks resolved but isn't?",
                "Can a gate have RHYTHM — predictable temporal patterns in its operation?",
                "What would 'improvising through the gate' mean in a formal system?",
            ],
        )

    elif domain == "weather":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as a weather front — a boundary between air masses where transformation occurs",
            reveals=[
                "The gate as a BOUNDARY PHENOMENON — it's not a thing, it's where things meet",
                "Instability at the boundary — storms happen at fronts, not in stable air",
                "Predictability limits — chaos theory applies, small inputs change outcomes",
                "The gate has SCOPE — a front covers a region, not a point",
                "Seasonal variation — the gate behaves differently under different conditions",
            ],
            hides=[
                "Intentionality — weather has no purpose, gates might need one",
                "Discrete outcomes — weather is continuous, gates produce binary results",
                "Design — fronts emerge, gates are built",
            ],
            tension_points=[
                "The boundary is fuzzy — where exactly does the front end?",
                "Forecast skill decreases with range — distant gates are unpredictable",
                "The front itself modifies the conditions that created it",
            ],
            novel_questions=[
                "Does a disproof gate have 'storm conditions' — periods of chaotic behavior?",
                "Can the gate itself change the 'climate' of the system it operates in?",
                "What's the 'butterfly effect' — what tiny input could flip a gate decision?",
            ],
        )

    elif domain == "chinese_poetry":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as the unsaid between couplets — the meaning lives in what's omitted, not what's stated",
            reveals=[
                "The gate operates in NEGATIVE SPACE — what it rejects defines it more than what it accepts",
                "Restraint as power — the most effective gates are the quietest",
                "Allusive depth — the gate resonates with every previous instance",
                "The reader completes the meaning — the gate's verdict depends on the observer",
                "Parallelism creates structure without explicit rules",
            ],
            hides=[
                "Explicit criteria — poetry avoids specification",
                "Operational mechanics — the craft behind the art is hidden",
                "Failure modes — poetry doesn't have 'bugs' in the same way",
            ],
            tension_points=[
                "Interpretive ambiguity — the same gate, different readers, different verdicts",
                "Cultural specificity — the gate's meaning depends on tradition",
                "The unsaid can never be fully recovered — some gate logic is irretrievable",
            ],
            novel_questions=[
                "What is the 'negative space' of a disproof gate — what is defined by absence?",
                "Can a gate have 'allusive depth' — referencing all previous decisions without stating them?",
                "What happens when the 'reader' of the gate is another gate?",
            ],
        )

    elif domain == "geology":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as a fault line — a discontinuity where pressure accumulates and releases catastrophically",
            reveals=[
                "DEEP TIME — the gate has a history stretching back beyond anyone's memory",
                "Pressure accumulation — unresolved proofs build up like tectonic stress",
                "Catastrophic release — when the gate fails, it fails big (earthquake)",
                "Layered strata — the gate sits at the boundary between geological eras",
                "The gate IS the evidence of past events — it records history in its structure",
            ],
            hides=[
                "Agency — faults don't decide, they break",
                "Gradual change — geology hides slow continuous transformation",
                "Reversibility — once a fault slips, the landscape is permanently changed",
            ],
            tension_points=[
                "Predictability paradox — we know WHERE but not WHEN",
                "The gate is both cause and effect of the forces acting on it",
                "Erosion wears down the gate itself over time",
            ],
            novel_questions=[
                "What accumulated 'pressure' are we not measuring in the gate's environment?",
                "Is there a 'Richter scale' for gate failures — some are tremors, some are quakes?",
                "Can a gate 'erode' — gradually losing discrimination over many applications?",
            ],
        )

    elif domain == "legal_system":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as a burden-of-proof standard — 'beyond reasonable doubt' vs 'preponderance of evidence'",
            reveals=[
                "The gate has MULTIPLE STANDARDS — not one threshold but a spectrum",
                "Adversarial testing — the gate works because both sides push against it",
                "Precedent binds future gates — stare decisis creates path dependence",
                "The gate is jurisdictional — different courts, different gates",
                "Appeals process — a gate verdict is never truly final",
            ],
            hides=[
                "Computational clarity — law deals in judgment, not calculation",
                "Speed — legal gates are deliberately slow",
                "Emotional/social context — formal gates ignore human factors",
            ],
            tension_points=[
                "Precedent can be overturned — the gate's history is not its destiny",
                "The standard of proof IS the gate, but who sets the standard?",
                "Jury nullification — the gate can be bypassed by the community",
            ],
            novel_questions=[
                "What is the 'standard of proof' for a disproof gate — and who sets it?",
                "Can a gate have 'stare decisis' — should past decisions bind future ones?",
                "What's the equivalent of 'jury nullification' — community override of formal logic?",
            ],
        )

    elif domain == "software":
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} as a type checker — the compiler rejects programs that don't type-check before they can run",
            reveals=[
                "The gate as a STATIC ANALYSIS tool — it catches errors before runtime",
                "Soundness vs completeness — the gate can reject valid programs (false positives) or accept invalid ones (false negatives)",
                "The gate has a LANGUAGE — what it can express depends on its type system",
                "Gradual typing — you can have partial gates that check some things",
                "The halting problem — some gate decisions are undecidable",
            ],
            hides=[
                "The runtime reality — type-correct programs can still crash",
                "Human factors — developer experience of the gate matters",
                "Social dynamics — gate design is political (which errors are 'important')",
            ],
            tension_points=[
                "Expressiveness vs safety — stricter gates reject more valid programs",
                "Type erasure — after the gate, the type information disappears",
                "The gate can't check what it can't see — hidden dependencies escape",
            ],
            novel_questions=[
                "Is the disproof gate 'sound' or 'complete' — and what's the trade-off?",
                "What would 'gradual gating' look like — partial verification with escape hatches?",
                "Can the gate's own logic be type-checked — who gates the gate?",
            ],
        )

    # Fallback for unknown domains
    else:
        return MetaphorReframing(
            domain=domain,
            concept_translation=f"{concept} reframed through {domain}",
            reveals=["(generic reframing — define this domain for richer output)"],
            hides=["(unknown blind spots)"],
            tension_points=["(unknown tensions)"],
            novel_questions=["(unknown questions)"],
        )


# ---------------------------------------------------------------------------
# Rotation analysis — the core discovery mechanism
# ---------------------------------------------------------------------------

def analyze_rotation(a: MetaphorReframing, b: MetaphorReframing) -> RotationPair:
    """
    Compare two metaphor lenses. The KEY insight:
    What B reveals that A hid IS the chromatic aberration.
    The collection of all aberrations IS the portrait of the concept.
    """
    # What lens B reveals that lens A hid
    revealed = []
    for r in b.reveals:
        for h in a.hides:
            # Conceptual overlap detection via keyword matching
            r_words = set(r.lower().split())
            h_words = set(h.lower().split())
            if r_words & h_words:  # shared keywords
                revealed.append(
                    f"[{b.domain}] reveals what [{a.domain}] hid: '{r}' "
                    f"addresses '{h}'"
                )

    # Add non-overlapping revelations too
    for r in b.reveals[:2]:  # top reveals
        revealed.append(f"[{b.domain}] shows: {r}")

    # What lens A saw that lens B obscures
    hidden = []
    for r in a.reveals[:2]:
        hidden.append(f"[{a.domain}] saw something [{b.domain}] misses: {r}")

    # Emergent questions from the DIFFERENCE between lenses
    emergent = []
    for qt in a.tension_points[:1]:
        for qb in b.tension_points[:1]:
            emergent.append(
                f"If [{a.domain}] says '{qt[:60]}...' but [{b.domain}] says "
                f"'{qb[:60]}...', which is the REAL structure?"
            )
    # Cross-pollinate novel questions
    for qa in a.novel_questions[:1]:
        for qb in b.novel_questions[:1]:
            emergent.append(
                f"Combining [{a.domain}] question with [{b.domain}] question: "
                f"What if {qa[:50]}... AND {qb[:50]}...?"
            )

    return RotationPair(
        lens_a=a.domain,
        lens_b=b.domain,
        revealed_by_rotation=revealed,
        hidden_by_rotation=hidden,
        emergent_questions=emergent,
    )


# ---------------------------------------------------------------------------
# Meta-question generation
# ---------------------------------------------------------------------------

def generate_meta_questions(pairs: list[RotationPair], reframings: list[MetaphorReframing]) -> list[str]:
    """
    Generate questions that NO single lens could produce.
    These come from the ROTATION itself — the gaps between lenses.
    """
    questions = []
    domains = [r.domain for r in reframings]

    # 1. The "no lens captures this" questions
    all_hides = set()
    for r in reframings:
        for h in r.hides:
            all_hides.add((r.domain, h))

    questions.append(
        "CONVERGENCE BLIND SPOT: What property of the concept is hidden by "
        f"ALL {len(domains)} metaphor domains? The intersection of blind spots "
        "is the deepest unknown."
    )

    # 2. The "lens portrait" questions
    questions.append(
        "LENS PORTRAIT: What does the pattern of what each metaphor reveals "
        "tell us about the METAPHORS themselves — and does that pattern "
        "constitute a new domain that should be added to the rotation?"
    )

    # 3. Cross-domain emergent questions from rotation pairs
    for pair in pairs[:3]:
        if pair.emergent_questions:
            questions.append(f"META ({pair.lens_a} ↔ {pair.lens_b}): {pair.emergent_questions[-1]}")

    # 4. The recursive question
    questions.append(
        "RECURSION: If metaphor rotation is a discovery engine, what metaphor "
        "best describes the ROTATION ITSELF? Is it a kaleidoscope, a prism, "
        "a gyroscope, or something else entirely? And does that metaphor "
        "have its own blind spots?"
    )

    # 5. Stability question
    questions.append(
        "STABILITY: Does the discovery output converge (same metaphors → same "
        "insights) or diverge (each rotation generates genuinely novel territory)? "
        "If it diverges, the engine is an INFINITE discovery machine."
    )

    # 6. Architecture question
    domains_string = ", ".join(domains)
    questions.append(
        f"ARCHITECTURE: The {len(domains)} lenses ({domains_string}) each "
        "have different ontologies. Is there a META-ONTOLOGY that unifies "
        "them? If so, is that meta-ontology itself the architecture of the concept?"
    )

    return questions


# ---------------------------------------------------------------------------
# Lens portrait — what the rotation reveals about the LENSES
# ---------------------------------------------------------------------------

def build_lens_portrait(reframings: list[MetaphorReframing]) -> dict:
    """
    The picture of the lenses IS the architecture.
    Map out what each lens is good at, bad at, and where it strains.
    """
    portrait = {}
    for r in reframings:
        portrait[r.domain] = {
            "strengths": r.reveals[:3],
            "blind_spots": r.hides[:3],
            "breaking_points": r.tension_points[:2],
            "unique_contribution": r.novel_questions[0] if r.novel_questions else "none",
            "aberration_signature": hashlib.md5(
                "|".join(r.reveals + r.hides).encode()
            ).hexdigest()[:8],
        }
    return portrait


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

def run_kaleidoscope(
    concept: str,
    domain_names: Optional[list[str]] = None,
) -> dict:
    """
    Run the full kaleidoscope discovery engine on a concept.
    Returns a complete DiscoveryReport.
    """
    if domain_names is None:
        domain_names = ["biology", "city_planning", "music", "weather",
                        "chinese_poetry", "geology", "legal_system", "software"]

    # Phase 1: Reframe through each metaphor domain
    reframings = []
    for domain in domain_names:
        r = reframe_in_domain(concept, domain)
        reframings.append(r)
        print(f"  🔍 {domain:20s} → {len(r.reveals)} reveals, {len(r.hides)} hides")

    # Phase 2: Pairwise rotation analysis
    print(f"\n  🔄 Analyzing {len(reframings) * (len(reframings) - 1) // 2} rotation pairs...")
    rotation_pairs = []
    for a, b in itertools.combinations(reframings, 2):
        pair = analyze_rotation(a, b)
        rotation_pairs.append(pair)

    # Phase 3: Generate meta-questions
    print("  ❓ Generating meta-questions from rotation gaps...")
    meta_questions = generate_meta_questions(rotation_pairs, reframings)

    # Phase 4: Build lens portrait
    print("  🎨 Building lens portrait (the architecture)...")
    lens_portrait = build_lens_portrait(reframings)

    # Discovery score: rough measure of novelty generated
    total_reveals = sum(len(r.reveals) for r in reframings)
    total_hides = sum(len(r.hides) for r in reframings)
    total_tensions = sum(len(r.tension_points) for r in reframings)
    total_novel = sum(len(r.novel_questions) for r in reframings)
    total_emergent = sum(len(p.emergent_questions) for p in rotation_pairs)
    discovery_score = (total_reveals + total_hides + total_tensions + total_novel + total_emergent) / len(domain_names)

    # Assemble report
    report = DiscoveryReport(
        concept=concept,
        timestamp=datetime.now(timezone.utc).isoformat(),
        reframings=[asdict(r) for r in reframings],
        rotation_pairs=[asdict(p) for p in rotation_pairs],
        meta_questions=meta_questions,
        lens_portrait=lens_portrait,
        discovery_score=round(discovery_score, 2),
        metadata={
            "domains_used": domain_names,
            "total_reframings": len(reframings),
            "total_rotation_pairs": len(rotation_pairs),
            "total_meta_questions": len(meta_questions),
            "engine_version": "0.1.0",
        },
    )

    return asdict(report)


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def print_report(report: dict):
    """Print a human-readable discovery report."""
    print(f"\n{'='*72}")
    print(f"  KALEIDOSCOPE DISCOVERY REPORT")
    print(f"  Concept: {report['concept']}")
    print(f"  Timestamp: {report['timestamp']}")
    print(f"  Discovery Score: {report['discovery_score']}")
    print(f"{'='*72}")

    # Reframings
    print(f"\n{'─'*72}")
    print(f"  PHASE 1: METAPHOR REFRAMINGS ({len(report['reframings'])} lenses)")
    print(f"{'─'*72}")
    for r in report["reframings"]:
        print(f"\n  📐 {r['domain'].upper()}")
        print(f"     Translation: {r['concept_translation']}")
        print(f"     Reveals ({len(r['reveals'])}):")
        for v in r["reveals"]:
            print(f"       ✦ {v}")
        print(f"     Hides ({len(r['hides'])}):")
        for h in r["hides"]:
            print(f"       ✗ {h}")
        print(f"     Tensions ({len(r['tension_points'])}):")
        for t in r["tension_points"]:
            print(f"       ⚡ {t}")
        print(f"     Novel Questions ({len(r['novel_questions'])}):")
        for q in r["novel_questions"]:
            print(f"       ❓ {q}")

    # Meta-questions
    print(f"\n{'─'*72}")
    print(f"  PHASE 2: META-QUESTIONS (from rotation gaps)")
    print(f"{'─'*72}")
    for i, q in enumerate(report["meta_questions"], 1):
        print(f"  {i}. {q}")

    # Lens portrait
    print(f"\n{'─'*72}")
    print(f"  PHASE 3: LENS PORTRAIT (the architecture)")
    print(f"{'─'*72}")
    for domain, data in report["lens_portrait"].items():
        print(f"\n  {domain} [sig: {data['aberration_signature']}]")
        print(f"    Unique: {data['unique_contribution'][:80]}...")

    # Summary
    print(f"\n{'─'*72}")
    print(f"  SUMMARY")
    print(f"{'─'*72}")
    print(f"  Lenses applied:    {report['metadata']['total_reframings']}")
    print(f"  Rotation pairs:    {report['metadata']['total_rotation_pairs']}")
    print(f"  Meta-questions:    {report['metadata']['total_meta_questions']}")
    print(f"  Discovery score:   {report['discovery_score']} "
          f"(insights per lens)")
    print(f"{'='*72}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Kaleidoscope Discovery Engine")
    parser.add_argument("concept", help="Concept to analyze through metaphor rotation")
    parser.add_argument("--metaphors", type=int, default=8, help="Number of metaphor domains to use")
    parser.add_argument("--save", action="store_true", default=True, help="Save results to JSON")
    parser.add_argument("--no-save", dest="save", action="store_false")
    args = parser.parse_args()

    print(f"\n🔬 KALEIDOSCOPE DISCOVERY ENGINE v0.1.0")
    print(f"   Concept: \"{args.concept}\"")
    print(f"   Metaphors: {args.metaphors}")

    all_domains = list(METAPHOR_DOMAINS.keys())
    domains = all_domains[:args.metaphors]

    print(f"   Domains: {', '.join(domains)}\n")

    report = run_kaleidoscope(args.concept, domains)
    print_report(report)

    if args.save:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe = args.concept.replace(" ", "-").replace("/", "-")
        outpath = f"experiments/results/kaleidoscope-discovery-{safe}-{ts}.json"
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  💾 Saved to {outpath}")
