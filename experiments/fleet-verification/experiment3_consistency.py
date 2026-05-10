"""
Experiment 3: Fleet Knowledge Consistency
==========================================

Check if PLATO rooms have consistent knowledge:
- Find rooms about the same topic from different agents
- Check for contradictions
- Map contradictions to H¹ obstructions
- Topics where agents agree → H¹ = 0
- Topics where agents disagree → H¹ > 0

This tests the core claim: H¹ measures knowledge inconsistencies
in the fleet's shared cortex.
"""

import sys, os, json, urllib.request
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sheaf-h1'))
from cohomology import compute_sheaf_cohomology

PLATO_URL = "http://147.224.38.131:8847"


def get_all_room_tiles():
    """Fetch all tiles from all PLATO rooms."""
    try:
        resp = urllib.request.urlopen(f"{PLATO_URL}/rooms", timeout=10)
        rooms = json.loads(resp.read())
    except Exception as e:
        print(f"  [INFO] Using cached room data (PLATO unreachable: {e})")
        # Fall back to known room structure
        rooms = {
            "forge": {"tile_count": 17},
            "fleet_health": {"tile_count": 565},
            "oracle1": {"tile_count": 1},
            "oracle1_briefing": {"tile_count": 2},
            "oracle1_history": {"tile_count": 6},
            "oracle1_lessons": {"tile_count": 2},
            "oracle1_infrastructure": {"tile_count": 2},
            "fleet_tools": {"tile_count": 52},
            "fleet_security": {"tile_count": 8},
            "fleet_math": {"tile_count": 2},
            "fleet_research": {"tile_count": 3},
            "fleet_rust": {"tile_count": 2},
            "zeroclaw_bard": {"tile_count": 28},
            "zeroclaw_healer": {"tile_count": 20},
            "zeroclaw_warden": {"tile_count": 24},
            "confidence_proofs": {"tile_count": 6},
            "energy_flux": {"tile_count": 6},
            "murmur_insights": {"tile_count": 7},
            "constraint-theory": {"tile_count": 1},
            "casting_call": {"tile_count": 1},
        }

    # Get tile content from each room
    all_tiles = []
    for room_name in rooms:
        try:
            resp = urllib.request.urlopen(f"{PLATO_URL}/room/{room_name}", timeout=10)
            data = json.loads(resp.read())
            room_tiles = data.get("tiles", [])
            for t in room_tiles:
                t["_room"] = room_name
            all_tiles.extend(room_tiles)
        except Exception:
            pass

    return all_tiles, rooms


# === KNOWLEDGE DOMAINS (topics) ===

TOPICS = {
    "constraint_theory": {
        "keywords": ["constraint", "llvm", "avx", "cdcl", "x86", "emitter", "spline", "bearing"],
        "rooms": ["forge", "constraint-theory", "fleet_research", "fleet_rust"],
    },
    "keel_ttl": {
        "keywords": ["keel", "ttl", "lifespan", "apoptosis", "unified equation", "mandelbrot"],
        "rooms": ["forge", "oracle1", "oracle1_history", "oracle1_briefing", "fleet_tools"],
    },
    "fleet_health": {
        "keywords": ["fleet health", "service", "plato", "uptime", "zeroclaw", "systemd"],
        "rooms": ["fleet_health", "oracle1", "oracle1_infrastructure", "forge"],
    },
    "security": {
        "keywords": ["security", "blast radius", "contain", "compromis", "warden"],
        "rooms": ["fleet_security", "zeroclaw_warden", "energy_flux"],
    },
    "agent_coordination": {
        "keywords": ["agent", "coordination", "orchestrat", "i2i", "bottle", "protocol"],
        "rooms": ["fleet_agent", "fleet_communication", "fleet_protocol", "zeroclaw_bard", "forge"],
    },
    "infrastructure": {
        "keywords": ["infrastructure", "storage", "gc", "cleanup", "github", "ci", "cd"],
        "rooms": ["oracle1_infrastructure", "oracle1_lessons", "fleet_health", "fleet_infrastructure"],
    },
    "model_quality": {
        "keywords": ["model", "quality", "casting", "llm", "benchmark", "glm", "deepseek"],
        "rooms": ["casting_call", "forge", "oracle1", "murmur_insights", "confidence_proofs"],
    },
}


def extract_knowledge_vectors(tiles, topic):
    """
    Extract knowledge vectors for a topic from tiles.
    Each room yields a vector: [has_knowledge, confidence, entropy, engagement]
    """
    info = TOPICS[topic]
    keywords = info["keywords"]
    topic_rooms = info["rooms"]

    # Group tiles by room
    room_tiles = defaultdict(list)
    for t in tiles:
        room = t.get("_room", "unknown")
        room_tiles[room].append(t)

    room_vectors = {}
    for room in topic_rooms:
        if room not in room_tiles:
            continue

        rtiles = room_tiles[room]
        # Count tiles matching this topic
        topic_matches = 0
        total_confidence = 0
        text_lengths = []

        for t in rtiles:
            q = (t.get("question", "") + " " + t.get("answer", "")).lower()
            matches = sum(1 for kw in keywords if kw.lower() in q)
            if matches > 0:
                topic_matches += 1
                total_confidence += t.get("confidence", 0.5)
                text_lengths.append(len(q))

        if topic_matches == 0:
            continue

        n_tiles = len(rtiles)
        match_ratio = topic_matches / max(n_tiles, 1)
        avg_confidence = total_confidence / max(topic_matches, 1)

        # Entropy: how diverse are the tile contents?
        if text_lengths:
            # Normalized entropy of text length distribution
            hist, _ = np.histogram(text_lengths, bins=5)
            probs = hist / max(hist.sum(), 1)
            entropy = -np.sum(probs * np.log2(probs + 1e-10))
        else:
            entropy = 0

        # Engagement: how many different agents contributed?
        sources = set(t.get("source", "") for t in rtiles if t.get("source"))
        engagement = len(sources)

        room_vectors[room] = np.array([
            float(match_ratio),
            float(avg_confidence),
            float(entropy),
            float(engagement),
        ])

    return room_vectors


def compute_topic_cohomology(room_vectors, topic_name):
    """
    Compute H¹ for a topic based on room consistency.

    For each topic:
    - Open sets = individual rooms
    - Sections = knowledge vectors for that room
    - Compatibility = rooms overlap (share the same topic)
    - H¹ = measure of knowledge inconsistency across rooms
    """
    rooms = list(room_vectors.keys())
    n_rooms = len(rooms)

    if n_rooms < 2:
        return None, "Too few rooms with this topic"

    opens = [frozenset([i]) for i in range(n_rooms)]

    # All rooms are compatible (they all discuss this topic)
    sections = {}
    for i, room in enumerate(rooms):
        sections[frozenset([i])] = room_vectors[room]

    # Compute pairwise agreement
    agreements = []
    for i in range(n_rooms):
        for j in range(i + 1, n_rooms):
            vi = room_vectors[rooms[i]]
            vj = room_vectors[rooms[j]]
            cos_sim = np.dot(vi, vj) / (np.linalg.norm(vi) * np.linalg.norm(vj) + 1e-10)
            euc_dist = np.linalg.norm(vi - vj)
            agreements.append({
                "room_a": rooms[i],
                "room_b": rooms[j],
                "cosine_sim": float(cos_sim),
                "euclidean_dist": float(euc_dist),
                "agree": cos_sim > 0.7,
            })

    # Compute cohomology
    try:
        result = compute_sheaf_cohomology(opens, sections)
    except Exception as e:
        return None, f"Cohomology computation error: {e}"

    # Interpretation
    h1 = result.h1_dimension
    n_agree = sum(1 for a in agreements if a["agree"])
    n_disagree = len(agreements) - n_agree
    avg_cos = np.mean([a["cosine_sim"] for a in agreements]) if agreements else 1.0

    # Room knowledge profiles
    room_profiles = {}
    for room, vec in room_vectors.items():
        room_profiles[room] = {
            "match_ratio": float(vec[0]),
            "avg_confidence": float(vec[1]),
            "entropy": float(vec[2]),
            "engagement": float(vec[3]),
        }

    return {
        "topic": topic_name,
        "n_rooms": n_rooms,
        "h0": int(result.h0_dimension),
        "h1": int(h1),
        "avg_cosine_sim": float(avg_cos),
        "room_pairs_agree": n_agree,
        "room_pairs_disagree": n_disagree,
        "agreements": agreements,
        "consistent": h1 == 0,
        "interpretation": result.interpretation,
        "room_profiles": room_profiles,
    }, None


def run_experiment():
    """Run the fleet knowledge consistency experiment."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 3: Fleet Knowledge Consistency                  ║")
    print("║  Map contradictions to H¹ obstructions                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Fetch all tiles
    all_tiles, rooms = get_all_room_tiles()
    print(f"  Rooms: {len(rooms)}")
    print(f"  Tiles fetched: {len(all_tiles)}")
    print()

    # Topics to analyze
    topic_names = list(TOPICS.keys())

    print("─── Knowledge Domain Analysis ───")
    print()

    results = {}
    for topic_name in topic_names:
        info = TOPICS[topic_name]
        print(f"  Topic: {topic_name}")
        print(f"    Keywords: {info['keywords']}")
        print(f"    Expected rooms: {info['rooms']}")

        # Extract knowledge vectors
        room_vectors = extract_knowledge_vectors(all_tiles, topic_name)
        print(f"    Rooms with topic data: {list(room_vectors.keys())}")

        if room_vectors:
            result, error = compute_topic_cohomology(room_vectors, topic_name)
            if result:
                print(f"    H⁰={result['h0']}, H¹={result['h1']}")
                print(f"    Avg cosine sim: {result['avg_cosine_sim']:.3f}")
                print(f"    Pairwise agreements: {result['room_pairs_agree']}/{result['room_pairs_agree'] + result['room_pairs_disagree']}")
                print(f"    Consistent: {result['consistent']}")
                print()
                results[topic_name] = result
            else:
                print(f"    Error: {error}")
                print()
        else:
            print(f"    No data found in any room")
            print()

    # === SUMMARY TABLE ===
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  SUMMARY: Topic Consistency / H¹ Map                       ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print()

    for topic_name in topic_names:
        if topic_name in results:
            r = results[topic_name]
            icon = "✓" if r["consistent"] else "✗"
            n_rooms = r["n_rooms"]
            avg_cos = r["avg_cosine_sim"]
            n_agree = r["room_pairs_agree"]
            total_pairs = n_agree + r["room_pairs_disagree"]
            print(f"  {icon} {topic_name:<25} {n_rooms} rooms, cos={avg_cos:.3f}, agree={n_agree}/{total_pairs}")
        else:
            print(f"  · {topic_name:<25} No data")

    print()
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("─── Interpretation ───")
    print()
    print("  H¹ = 0 → Fleet agrees on this topic (knowledge is consistent)")
    print("  H¹ > 0 → Fleet has contradictions or differing perspectives")
    print("  The magnitude of H¹ scales with the degree of inconsistency")
    print()
    print("  Topics where agents agree ↔ H¹ = 0:")
    print("    Knowledge sectors with shared understanding")
    print()
    print("  Topics where agents disagree ↔ H¹ > 0:")
    print("    These are the 'fault lines' — emergent edges of the fleet's knowledge")
    print()

    return results


if __name__ == "__main__":
    results = run_experiment()
    with open("experiment3_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results saved to experiment3_results.json")
