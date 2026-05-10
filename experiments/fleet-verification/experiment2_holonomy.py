"""
Experiment 2: I2I Communication Holonomy
=========================================

Simulate the I2I bottle protocol:
- Agent A sends a message to B (encode intent vector)
- B interprets and forwards to C
- C interprets and sends back to A
- Measure: does the message return unchanged? (holonomy)

Theory predicts:
1. Longer chains accumulate more holonomy (drift)
2. Technical messages have LESS holonomy than emotional ones
3. Holonomy is the I2I analog of H¹ — the obstruction to perfect communication

This uses our 9-channel intent encoding:
  [technical, strategic, social, emotional, creative, 
   analytical, operational, philosophical, existential]
"""

import sys, os, json, math
import numpy as np
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sheaf-h1'))
from cohomology import compute_sheaf_cohomology


# === 9-CHANNEL INTENT ENCODING ===

INTENT_CHANNELS = [
    "technical",      # Protocols, code, tooling
    "strategic",      # Planning, priorities, direction
    "social",         # Relationships, trust, coordination
    "emotional",      # Sentiment, affect, mood
    "creative",       # Novel ideas, synthesis
    "analytical",     # Analysis, breakdown
    "operational",    # Execution, tasks
    "philosophical",  # Values, principles
    "existential",    # Identity, purpose
]

@dataclass
class I2IMessage:
    """An I2I bottle message with 9-channel intent encoding."""
    sender: str
    recipient: str
    intent_vector: np.ndarray  # 9-channel encoding
    text: str
    timestamp: float = 0.0

    def encode(self) -> np.ndarray:
        """Encode the full message as vector."""
        return self.intent_vector.copy()

    def decode(self, vector: np.ndarray) -> np.ndarray:
        """Decode a received vector back into intent space."""
        return vector.copy()

    @property
    def norm(self) -> float:
        return np.linalg.norm(self.intent_vector)


# === I2I INTERPRETATION FUNCTIONS ===
# Each agent interprets the message through their expertise lens

def forgemaster_interpret(v: np.ndarray) -> np.ndarray:
    """Forgemaster: emphasis on technical+analytical, dampens emotional."""
    w = v.copy()
    w[0] *= 1.3   # technical amplified
    w[3] *= 0.5   # emotional dampened
    w[4] *= 0.8   # creative slightly dampened
    w[5] *= 1.4   # analytical amplified
    w[6] *= 1.2   # operational amplified
    # Normalize
    return w / np.linalg.norm(w) * np.linalg.norm(v)

def oracle1_interpret(v: np.ndarray) -> np.ndarray:
    """Oracle1: holistic, amplifies strategic+philosophical."""
    w = v.copy()
    w[1] *= 1.4   # strategic amplified
    w[7] *= 1.3   # philosophical amplified
    w[8] *= 1.2   # existential amplified
    w[2] *= 1.1   # social slightly amplified
    w[0] *= 0.9   # technical dampened
    return w / np.linalg.norm(w) * np.linalg.norm(v)

def bard_interpret(v: np.ndarray) -> np.ndarray:
    """Bard: creative+social, dampens analytical."""
    w = v.copy()
    w[2] *= 1.3   # social amplified
    w[4] *= 1.5   # creative amplified
    w[3] *= 1.2   # emotional amplified
    w[5] *= 0.6   # analytical dampened
    return w / np.linalg.norm(w) * np.linalg.norm(v)

def healer_interpret(v: np.ndarray) -> np.ndarray:
    """Healer: emotional+social restoration."""
    w = v.copy()
    w[2] *= 1.4   # social amplified
    w[3] *= 1.6   # emotional amplified
    w[5] *= 0.7   # analytical dampened
    w[0] *= 0.8   # technical dampened
    return w / np.linalg.norm(w) * np.linalg.norm(v)

def warden_interpret(v: np.ndarray) -> np.ndarray:
    """Warden: security+operational focus, dampens creative."""
    w = v.copy()
    w[0] *= 1.2   # technical amplified
    w[1] *= 1.1   # strategic amplified
    w[6] *= 1.5   # operational amplified
    w[4] *= 0.4   # creative heavy dampened
    w[3] *= 0.6   # emotional dampened
    return w / np.linalg.norm(w) * np.linalg.norm(v)

def fleet_gc_interpret(v: np.ndarray) -> np.ndarray:
    """fleet-gc: operational+analytical, dampens everything else."""
    w = v.copy()
    w[5] *= 1.3   # analytical amplified
    w[6] *= 1.6   # operational amplified
    w[0] *= 1.1   # technical slightly amplified
    for i in [1, 2, 3, 4, 7, 8]:
        w[i] *= 0.5
    return w / np.linalg.norm(w) * np.linalg.norm(v)


AGENT_INTERPRETERS = {
    "forgemaster": forgemaster_interpret,
    "oracle1": oracle1_interpret,
    "zeroclaw_bard": bard_interpret,
    "zeroclaw_healer": healer_interpret,
    "zeroclaw_warden": warden_interpret,
    "fleet_gc": fleet_gc_interpret,
}


def create_message(msg_type: str, sender: str, recipient: str, seed: int = 42) -> I2IMessage:
    """Create a message with a specific type profile."""
    rng = np.random.RandomState(seed)

    if msg_type == "technical":
        # High technical+analytical, low emotional+social
        v = np.array([0.9, 0.3, 0.1, 0.05, 0.3, 0.8, 0.6, 0.1, 0.1]) + 0.05 * rng.randn(9)
    elif msg_type == "strategic":
        # High strategic+philosophical
        v = np.array([0.4, 0.9, 0.3, 0.1, 0.3, 0.6, 0.5, 0.7, 0.3]) + 0.05 * rng.randn(9)
    elif msg_type == "emotional":
        # High emotional+social+existential
        v = np.array([0.1, 0.2, 0.8, 0.9, 0.4, 0.1, 0.1, 0.3, 0.7]) + 0.05 * rng.randn(9)
    elif msg_type == "creative":
        # High creative+philosophical+existential
        v = np.array([0.3, 0.4, 0.3, 0.4, 0.9, 0.4, 0.2, 0.6, 0.5]) + 0.05 * rng.randn(9)
    elif msg_type == "mixed":
        # Balanced across all channels
        v = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]) + 0.05 * rng.randn(9)
    else:
        v = np.array([0.5] * 9) + 0.05 * rng.randn(9)

    # Clamp and normalize
    v = np.clip(v, 0, 1)
    v = v / np.linalg.norm(v)

    messages = {
        "technical": "Benchmarking constraint propagation on NEON with 100M data points",
        "strategic": "Our P0 priorities should shift to the Keel integration pipeline",
        "emotional": "The fleet has been running well but I'm feeling stretched thin tonight",
        "creative": "What if we express constraints as curvature in a knowledge manifold?",
        "mixed": "Working on the compiler milestone, need input on the architecture decision",
    }

    return I2IMessage(
        sender=sender,
        recipient=recipient,
        intent_vector=v,
        text=messages.get(msg_type, "Default message"),
    )


def run_communication_chain(
    chain: List[str],
    msg_type: str,
    seed: int = 42,
) -> Dict:
    """
    Run an I2I communication chain.

    A -> B -> C -> ... -> A

    Returns the holonomy (change in message) after the chain.
    """
    n_agents = len(chain)
    if n_agents < 2:
        return {"error": "Chain must have at least 2 agents"}

    # Create initial message
    msg = create_message(msg_type, chain[0], chain[1], seed=seed)
    original = msg.encode()

    current_vector = original.copy()

    # Chain: send through interpreters
    chain_log = []
    for i in range(n_agents - 1):
        sender = chain[i]
        recipient = chain[i + 1]

        # Sender sends (no-op for now, original vector)
        sent = current_vector

        # Recipient interprets
        interpreter = AGENT_INTERPRETERS.get(recipient, oracle1_interpret)
        received = interpreter(sent)

        chain_log.append({
            "from": sender,
            "to": recipient,
            "before_norm": float(np.linalg.norm(sent)),
            "after_norm": float(np.linalg.norm(received)),
            "cosine_sim": float(np.dot(sent, received) / (np.linalg.norm(sent) * np.linalg.norm(received) + 1e-10)),
        })

        current_vector = received

    # Send back through chain in reverse to complete the loop
    reverse_log = []
    for i in range(n_agents - 2, -1, -1):
        sender = chain[i + 1]
        recipient = chain[i]

        sent = current_vector
        interpreter = AGENT_INTERPRETERS.get(recipient, oracle1_interpret)
        received = interpreter(sent)

        reverse_log.append({
            "from": sender,
            "to": recipient,
            "cosine_sim": float(np.dot(sent, received) / (np.linalg.norm(sent) * np.linalg.norm(received) + 1e-10)),
        })

        current_vector = received

    # Measure holonomy: how much did the message drift?
    final_vector = current_vector

    holonomy_cosine = float(np.dot(original, final_vector) / (np.linalg.norm(original) * np.linalg.norm(final_vector) + 1e-10))
    holonomy_euclidean = float(np.linalg.norm(original - final_vector))
    holonomy_angle = float(np.arccos(np.clip(holonomy_cosine, -1, 1)))  # radians

    # Per-channel drift
    channel_drift = {}
    for i, ch in enumerate(INTENT_CHANNELS):
        channel_drift[ch] = float(final_vector[i] - original[i])

    return {
        "msg_type": msg_type,
        "chain": chain,
        "chain_length": n_agents * 2 - 1,  # full round trip
        "original_intent": original.tolist(),
        "final_intent": final_vector.tolist(),
        "holonomy_cosine": holonomy_cosine,
        "holonomy_euclidean": holonomy_euclidean,
        "holonomy_angle_rad": holonomy_angle,
        "holonomy_angle_deg": float(math.degrees(holonomy_angle)),
        "channel_drift": channel_drift,
        "forward_log": chain_log,
        "reverse_log": reverse_log,
    }


def run_experiment():
    """Run the complete holonomy experiment."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 2: I2I Communication Holonomy                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    agents = ["forgemaster", "oracle1", "zeroclaw_bard", "zeroclaw_healer", "zeroclaw_warden", "fleet_gc"]
    msg_types = ["technical", "strategic", "emotional", "creative", "mixed"]

    print(f"  Agents: {agents}")
    print(f"  Message types: {msg_types}")
    print()

    # === TEST 1: Holonomy by message type (fixed 3-agent chain) ===
    print("─── TEST 1: Holonomy by Message Type (3-agent chain) ───")
    print()

    chain_simple = ["forgemaster", "oracle1", "forgemaster"]  # A -> B -> A
    chain_medium = ["forgemaster", "oracle1", "zeroclaw_bard", "forgemaster"]  # A -> B -> C -> A
    chain_long = ["forgemaster", "oracle1", "zeroclaw_bard", "zeroclaw_healer", "zeroclaw_warden", "forgemaster"]

    results_by_type = {}
    for msg_type in msg_types:
        print(f"  Message type: {msg_type.upper()}")

        s = create_message(msg_type, "test", "test", seed=42)
        print(f"    Profile: [{', '.join(f'{v:.2f}' for v in s.intent_vector[:5])}...]")

        for chain_name, chain in [("A→B→A", chain_simple), ("A→B→C→A", chain_medium), ("A→B→C→D→E→A", chain_long)]:
            result = run_communication_chain(chain, msg_type, seed=42)
            results_by_type.setdefault(msg_type, {})[chain_name] = result
            print(f"    {chain_name:>15}: cos_sim={result['holonomy_cosine']:.4f}, "
                  f"euc_dist={result['holonomy_euclidean']:.4f}, "
                  f"angle={result['holonomy_angle_deg']:.1f}°")

        # Find which channel drifted most
        print(f"    Drift leaders:")
        ch_drift = results_by_type[msg_type][chain_name]["channel_drift"]
        sorted_drift = sorted(ch_drift.items(), key=lambda x: -abs(x[1]))[:3]
        for ch, d in sorted_drift:
            print(f"      {ch}: {d:+.3f}")
        print()

    # === TEST 2: Holonomy vs chain length ===
    print("─── TEST 2: Holonomy vs Chain Length ───")
    print()

    # Build chains of increasing length
    # All chains start and end at forgemaster
    mid_agents = ["oracle1", "zeroclaw_bard", "zeroclaw_healer", "zeroclaw_warden"]
    length_results = []

    for chain_len in range(2, 6):  # 2, 3, 4, 5 agents in round trip
        chain = ["forgemaster"] + mid_agents[:chain_len - 1] + ["forgemaster"]
        for msg_type in ["technical", "emotional", "mixed"]:
            result = run_communication_chain(chain, msg_type, seed=42)
            length_results.append({
                "chain_length": chain_len * 2 - 1,
                "n_agents": chain_len,
                "msg_type": msg_type,
                "holonomy": result["holonomy_cosine"],
                "angle_deg": result["holonomy_angle_deg"],
                "euclidean": result["holonomy_euclidean"],
            })

            # Print
            chain_str = "→".join(chain)
            print(f"  {msg_type:>10}: {chain_str:>40} → "
                  f"cos={result['holonomy_cosine']:.3f} "
                  f"angle={result['holonomy_angle_deg']:.1f}°")

    print()
    print("─── Analysis: Does holonomy increase with chain length? ───")
    print()

    for msg_type in ["technical", "emotional", "mixed"]:
        angles = [r["angle_deg"] for r in length_results if r["msg_type"] == msg_type]
        lengths = [r["chain_length"] for r in length_results if r["msg_type"] == msg_type]
        if len(angles) >= 2:
            # Simple linear regression to detect trend
            A = np.vstack([lengths, np.ones_like(lengths)]).T
            slope, intercept = np.linalg.lstsq(A, angles, rcond=None)[0]
            print(f"  {msg_type:>10}: drift_rate={slope:.2f}°/hop, "
                  f"base_angle={intercept:.1f}°")
            print(f"    {'✓ Increasing with chain length' if slope > 2 else '~ Flat or decreasing'}")

    print()
    print("─── TEST 3: Technical vs Emotional Holonomy Comparison ───")
    print()

    # Compare technical vs emotional directly
    tech_results = [r for r in length_results if r["msg_type"] == "technical"]
    emotion_results = [r for r in length_results if r["msg_type"] == "emotional"]

    tech_avg_angle = np.mean([r["angle_deg"] for r in tech_results])
    emotion_avg_angle = np.mean([r["angle_deg"] for r in emotion_results])

    print(f"  Technical messages: avg drift angle = {tech_avg_angle:.1f}°")
    print(f"  Emotional messages: avg drift angle = {emotion_avg_angle:.1f}°")
    print(f"  Ratio (emotional/technical): {emotion_avg_angle / max(tech_avg_angle, 0.01):.2f}x")
    print()
    if emotion_avg_angle > tech_avg_angle:
        print(f"  ✓ CONFIRMED: Emotional messages have MORE holonomy than technical")
        print(f"    (theory predicts: language constraints reduce drift)")
    else:
        print(f"  × NOT confirmed: technical messages have similar or more holonomy")
        print(f"    (possible: all agents interpret technical content differently)")

    return {
        "by_type": {k: {ck: {k2: float(v2) if isinstance(v2, (int, float)) else v2 for k2, v2 in cv.items()} for ck, cv in v.items()} for k, v in results_by_type.items()},
        "length_analysis": length_results,
        "technical_vs_emotional": {
            "tech_avg_angle": tech_avg_angle,
            "emotion_avg_angle": emotion_avg_angle,
            "ratio": emotion_avg_angle / max(tech_avg_angle, 0.01),
        }
    }


if __name__ == "__main__":
    import numpy as np
    results = run_experiment()
    with open("experiment2_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results saved to experiment2_results.json")
