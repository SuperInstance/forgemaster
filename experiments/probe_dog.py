#!/usr/bin/env python3
"""
The Probe Dog — Three-Level Agency Cascade
============================================
The dog doesn't chase all fifty sheep. The dog finds the ONE
member of the flock whose perturbation cascade propagates through
the entire boid.

This implements: the agent that simulates cascade before firing.
"""

import json
import time
import random
import math
import os


class BoidAgent:
    """One sheep in the flock. Follows simple local rules.
    
    Each sheep: alignment (steer toward average heading of neighbors),
    separation (steer away from too-close neighbors), cohesion
    (steer toward center of mass of neighbors).
    """
    
    def __init__(self, agent_id: str, position: float, heading: float, 
                 influence: float = 1.0):
        self.id = agent_id
        self.x = position
        self.heading = heading
        self.influence = influence  # how much others follow this one
        self.dx = math.cos(heading)
        self.dy = math.sin(heading)
        self.perturbed = False
        self.perturbation_magnitude = 0.0
    
    def follow(self, neighbors: list, separation: float = 0.5, 
               alignment: float = 0.05, cohesion: float = 0.01):
        """Apply boid rules."""
        if self.perturbed:
            return
        
        if not neighbors:
            return
        
        avg_x = sum(n.x for n in neighbors) / len(neighbors)
        avg_dx = sum(n.dx for n in neighbors) / len(neighbors)
        avg_dy = sum(n.dy for n in neighbors) / len(neighbors)
        
        sep_x, sep_y = 0.0, 0.0
        for n in neighbors:
            dist = abs(n.x - self.x)
            if dist < 0.3 and dist > 0:
                sep_x -= (n.x - self.x) / dist * separation
                # Influential neighbors cause stronger separation
                self.dx += sep_x * (1 + n.influence)
        
        # Alignment (steer toward average heading) weighted by influence
        weight = self.influence * alignment
        self.dx += (avg_dx - self.dx) * weight
        self.dy += (avg_dy - self.dy) * weight
        
        # Cohesion (steer toward center of mass)
        self.dx += (avg_x - self.x) * cohesion * self.influence
        self.dy += 0  # simplified
        
        # Normalize
        mag = math.sqrt(self.dx**2 + self.dy**2) or 1.0
        self.dx /= mag
        self.dy /= mag
        
        self.x += self.dx * 0.1
    
    def nip(self, magnitude: float = 1.0):
        """Dog nips this sheep's heel. Perturbs its trajectory."""
        self.perturbed = True
        self.perturbation_magnitude = magnitude
        self.dx += magnitude * random.choice([-1, 1]) * 0.3
        self.dy += magnitude * (random.random() - 0.5) * 0.2
    
    @property
    def followers(self) -> float:
        """How many other agents tend to follow this one."""
        return self.influence * 10


class BoidFlock:
    """The emergent system. Individual agents + local rules = collective behavior."""
    
    def __init__(self, n_agents: int = 50):
        self.agents = [
            BoidAgent(f"sheep-{i}", random.uniform(0, 10), 
                      random.uniform(-1, 1), 
                      influence=random.uniform(0.5, 2.0))
            for i in range(n_agents)
        ]
        self.time = 0
        self.cascade_log = []
    
    def step(self):
        """One time step. Every agent follows local rules."""
        for agent in self.agents:
            neighbors = [a for a in self.agents if a != agent and abs(a.x - agent.x) < 1.5]
            agent.follow(neighbors)
        self.time += 1
    
    def find_lead_ewe(self) -> BoidAgent:
        """Who has the highest influence? The lead sheep."""
        return max(self.agents, key=lambda a: a.influence)
    
    def find_highest_follower_agent(self) -> BoidAgent:
        """Who do others cluster around?"""
        follower_counts = {}
        for agent in self.agents:
            for other in self.agents:
                if other != agent and abs(other.x - agent.x) < 0.5:
                    follower_counts[agent.id] = follower_counts.get(agent.id, 0) + 1
        if not follower_counts:
            return self.agents[0]
        most_followed_id = max(follower_counts, key=follower_counts.get)
        return next(a for a in self.agents if a.id == most_followed_id)
    
    def cascade_simulation(self, agent: BoidAgent, n_steps: int = 20) -> dict:
        """Simulate what happens if we nip THIS agent.
        
        The dog runs this in its head BEFORE choosing where to nip.
        Returns the predicted cascade.
        """
        # Save state
        saved = {
            "x": agent.x, "dx": agent.dx, "dy": agent.dy,
            "perturbed": agent.perturbed
        }
        
        # Nip and simulate
        agent.nip(0.5)
        displaced_agents = 0
        max_displacement = 0
        positions_before = {a.id: a.x for a in self.agents}
        
        for _ in range(n_steps):
            self.step()
        
        positions_after = {a.id: a.x for a in self.agents}
        for aid in positions_before:
            displacement = abs(positions_after[aid] - positions_before[aid])
            if displacement > 0.3:
                displaced_agents += 1
            max_displacement = max(max_displacement, displacement)
        
        # Restore state
        agent.x = saved["x"]
        agent.dx = saved["dx"]
        agent.dy = saved["dy"]
        agent.perturbed = saved["perturbed"]
        
        return {
            "target": agent.id,
            "influence": agent.influence,
            "followers": agent.followers,
            "displaced_agents": displaced_agents,
            "max_displacement": round(max_displacement, 3),
            "cascade_efficiency": displaced_agents / max(max_displacement, 0.1),
            "is_lead_ewe": agent == self.find_lead_ewe(),
        }
    
    def probe_efficiency(self, n_probes: int = 5) -> list:
        """The dog simulates multiple probes and ranks them by efficiency."""
        results = []
        candidates = random.sample(self.agents, min(n_probes, len(self.agents)))
        for agent in candidates:
            result = self.cascade_simulation(agent)
            result["cascade_amplification"] = result["displaced_agents"] * result["max_displacement"]
            results.append(result)
        results.sort(key=lambda r: -r.get("cascade_amplification", 0))
        return results


class ProbeDog:
    """The agent that simulates cascade before firing.
    
    Three-level agency:
    1. Cowboy (conductor) — the desire, the goal
    2. Sheep (individual) — the probe target
    3. Flock (emergent) — the cascade dynamics
    
    The dog finds the ONE nudge that propagates through the whole system.
    """
    
    def __init__(self, name: str = "probe-dog"):
        self.name = name
        self.probes_fired = 0
        self.successful_cascades = 0
        self.simulation_accuracy = []  # how well simulations matched reality
    
    def choose_probe_target(self, flock: BoidFlock, n_simulations: int = 5) -> dict:
        """Simulate before firing. Find the optimal nudge."""
        candidates = flock.probe_efficiency(n_simulations)
        if not candidates:
            return {"error": "no candidates"}
        
        best = candidates[0]
        print(f"  🐕 {self.name} simulated {len(candidates)} nips")
        print(f"     Best: {best['target']} (influence={best['influence']:.1f})")
        print(f"     Predicted cascade: {best['displaced_agents']} displaced, "
              f"amplification={best['cascade_amplification']:.2f}")
        
        return best
    
    def fire_probe(self, flock: BoidFlock, recommendation: dict) -> dict:
        """Fire the actual probe based on simulation."""
        target_id = recommendation["target"]
        target = next((a for a in flock.agents if a.id == target_id), None)
        if not target:
            return {"error": f"target {target_id} not found"}
        
        self.probes_fired += 1
        
        # Save pre-state
        positions_before = {a.id: a.x for a in flock.agents}
        
        # Nip!
        target.nip(1.0)
        
        # Run the cascade
        for _ in range(20):
            flock.step()
        
        # Measure actual
        positions_after = {a.id: a.x for a in flock.agents}
        displaced = sum(1 for aid in positions_before 
                       if abs(positions_after[aid] - positions_before[aid]) > 0.3)
        max_disp = max(abs(positions_after[aid] - positions_before[aid]) 
                      for aid in positions_before)
        
        self.successful_cascades += 1 if displaced > 1 else 0
        
        result = {
            "target": target_id,
            "actual_displaced": displaced,
            "actual_max_displacement": round(max_disp, 3),
            "predicted_displaced": recommendation.get("displaced_agents", 0),
            "prediction_error": abs(displaced - recommendation.get("displaced_agents", 0)),
        }
        self.simulation_accuracy.append(result["prediction_error"])
        return result


def demo():
    """Demonstrate the probe dog finding the optimal nudge."""
    print("=" * 70)
    print("  PROBE DOG — THREE-LEVEL AGENCY CASCADE")
    print("=" * 70)
    
    print("\n  🌾 Creating flock of 50 sheep...")
    flock = BoidFlock(50)
    
    # Pre-stabilize
    for _ in range(10):
        flock.step()
    
    print(f"  Lead ewe: {flock.find_lead_ewe().id} (influence={flock.find_lead_ewe().influence:.1f})")
    
    # The dog simulates before choosing
    dog = ProbeDog("efficient-herder")
    recommendation = dog.choose_probe_target(flock, n_simulations=8)
    
    print(f"\n  🐕 The dog has chosen.")
    print(f"     Target: {recommendation['target']}")
    print(f"     Is lead ewe? {recommendation['is_lead_ewe']}")
    
    # Fire the probe
    result = dog.fire_probe(flock, recommendation)
    
    print(f"\n  📊 RESULTS")
    print(f"     Actual displaced: {result['actual_displaced']} sheep")
    print(f"     Predicted displaced: {result['predicted_displaced']} sheep")
    print(f"     Prediction error: {result['prediction_error']} sheep")
    print(f"     Probe accuracy: {round((1 - result['prediction_error']/max(result['actual_displaced'], 1)) * 100, 1)}%")
    
    print(f"\n  🐕 Total probes fired: {dog.probes_fired}")
    print(f"     Successful cascades: {dog.successful_cascades}")
    print(f"     Accuracy history: {dog.simulation_accuracy}")
    
    # Compare: random probe vs optimal probe
    print(f"\n  ⚡ COMPARISON: Random probe vs optimal probe")
    random_agent = random.choice(flock.agents)
    random_rec = flock.cascade_simulation(random_agent)
    
    print(f"     Random target: {random_agent.id}")
    print(f"     Random cascade: {random_rec['displaced_agents']} displaced, "
          f"eff={random_rec['cascade_efficiency']:.2f}")
    print(f"     Optimal cascade: {recommendation['displaced_agents']} displaced, "
          f"eff={recommendation['cascade_efficiency']:.2f}")
    print(f"     EFFICIENCY RATIO: {recommendation['displaced_agents']/max(random_rec['displaced_agents'], 1):.1f}x")
    
    print(f"\n{'='*70}")
    print("  One nip at the right heel beats chasing all fifty sheep.")
    print("  The dog simulates before it fires. The fleet should too.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
