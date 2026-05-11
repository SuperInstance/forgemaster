#!/usr/bin/env python3
"""
Simulator 5: Delta-to-Script Learning Cycle

Full learning loop: experience → pattern → script → automation → delta monitoring → script update.
Agent starts blank, creates scripts from repeated delta patterns, shows phase transitions.
"""

import json
import random
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

# ─── Situation Generator ─────────────────────────────────────────────

SITUATION_TYPES = [
    'combat', 'navigation', 'social', 'resource', 'crafting',
    'puzzle', 'stealth', 'trade', 'healing', 'defense',
]

# Each situation has features that determine its "shape"
@dataclass
class Situation:
    type: str
    features: Dict[str, float]  # feature values 0-1
    
    def signature(self) -> str:
        """Discretized signature for pattern matching."""
        return self.type + ':' + ','.join(
            f"{k}={round(v * 4) / 4:.1f}" for k, v in sorted(self.features.items())
        )
    
    def distance_to(self, other: 'Situation') -> float:
        """Euclidean distance between feature vectors."""
        all_keys = set(self.features.keys()) | set(other.features.keys())
        dist = 0
        for k in all_keys:
            diff = self.features.get(k, 0.5) - other.features.get(k, 0.5)
            dist += diff * diff
        return math.sqrt(dist)


def generate_situation(rng: random.Random = random) -> Situation:
    """Generate a random situation."""
    sit_type = rng.choice(SITUATION_TYPES)
    features = {}
    
    # Each type has different feature distributions
    if sit_type == 'combat':
        features = {
            'threat_level': rng.uniform(0, 1),
            'ally_count': rng.uniform(0, 0.6),
            'terrain_advantage': rng.choice([0.0, 0.3, 0.7, 1.0]),
            'equipment': rng.uniform(0.3, 1.0),
            'surprise': rng.choice([0.0, 1.0]),
        }
    elif sit_type == 'navigation':
        features = {
            'complexity': rng.uniform(0, 1),
            'familiarity': rng.choice([0.0, 0.3, 0.6, 1.0]),
            'landmarks': rng.uniform(0, 1),
            'time_pressure': rng.choice([0.0, 0.5, 1.0]),
        }
    elif sit_type == 'social':
        features = {
            'ally_count': rng.uniform(0, 1),
            'trust_level': rng.uniform(0, 1),
            'formality': rng.choice([0.0, 0.5, 1.0]),
            'stakes': rng.uniform(0, 1),
        }
    elif sit_type == 'resource':
        features = {
            'scarcity': rng.uniform(0, 1),
            'competition': rng.uniform(0, 1),
            'renewability': rng.choice([0.0, 0.5, 1.0]),
            'value': rng.uniform(0, 1),
        }
    elif sit_type == 'crafting':
        features = {
            'complexity': rng.uniform(0, 1),
            'material_quality': rng.uniform(0, 1),
            'tool_quality': rng.uniform(0, 1),
            'recipe_known': rng.choice([0.0, 1.0]),
        }
    elif sit_type == 'puzzle':
        features = {
            'difficulty': rng.choice([0.2, 0.4, 0.6, 0.8, 1.0]),
            'hint_available': rng.choice([0.0, 1.0]),
            'time_pressure': rng.uniform(0, 1),
            'pattern_known': rng.choice([0.0, 1.0]),
        }
    elif sit_type == 'stealth':
        features = {
            'visibility': rng.uniform(0, 1),
            'guard_density': rng.uniform(0, 1),
            'distraction_available': rng.choice([0.0, 1.0]),
            'escape_routes': rng.uniform(0, 1),
        }
    elif sit_type == 'trade':
        features = {
            'market_volatility': rng.uniform(0, 1),
            'information_asymmetry': rng.uniform(0, 1),
            'urgency': rng.choice([0.0, 0.5, 1.0]),
            'relationship': rng.uniform(0, 1),
        }
    elif sit_type == 'healing':
        features = {
            'severity': rng.uniform(0, 1),
            'resources_available': rng.uniform(0, 1),
            'time_pressure': rng.uniform(0, 1),
            'expertise': rng.choice([0.0, 0.5, 1.0]),
        }
    elif sit_type == 'defense':
        features = {
            'threat_level': rng.uniform(0, 1),
            'fortification': rng.uniform(0, 1),
            'warning_time': rng.uniform(0, 1),
            'ally_count': rng.uniform(0, 1),
        }
    
    return Situation(type=sit_type, features=features)


# ─── Action / Response ───────────────────────────────────────────────

def optimal_response(situation: Situation) -> str:
    """Ground truth optimal action for a situation."""
    f = situation.features
    if situation.type == 'combat':
        if f.get('threat_level', 0.5) > 0.7 and f.get('ally_count', 0) < 0.3:
            return 'retreat'
        elif f.get('surprise', 0) > 0.5:
            return 'ambush'
        else:
            return 'attack'
    elif situation.type == 'navigation':
        if f.get('familiarity', 0) > 0.5:
            return 'auto_navigate'
        elif f.get('landmarks', 0) > 0.5:
            return 'landmark_navigate'
        else:
            return 'explore'
    elif situation.type == 'social':
        if f.get('trust_level', 0) < 0.3:
            return 'cautious'
        elif f.get('stakes', 0) > 0.7:
            return 'formal'
        else:
            return 'casual'
    elif situation.type == 'resource':
        if f.get('scarcity', 0) > 0.7 and f.get('competition', 0) > 0.5:
            return 'compete'
        elif f.get('renewability', 0) > 0.5:
            return 'gather'
        else:
            return 'conserve'
    elif situation.type == 'crafting':
        if f.get('recipe_known', 0) > 0.5:
            return 'follow_recipe'
        else:
            return 'experiment'
    elif situation.type == 'puzzle':
        if f.get('pattern_known', 0) > 0.5:
            return 'apply_pattern'
        elif f.get('hint_available', 0) > 0.5:
            return 'use_hint'
        else:
            return 'brute_force'
    elif situation.type == 'stealth':
        if f.get('visibility', 0) > 0.6:
            return 'distraction'
        elif f.get('escape_routes', 0) > 0.5:
            return 'sneak'
        else:
            return 'wait'
    elif situation.type == 'trade':
        if f.get('information_asymmetry', 0) > 0.6:
            return 'leverage_info'
        elif f.get('relationship', 0) > 0.5:
            return 'fair_deal'
        else:
            return 'cautious_offer'
    elif situation.type == 'healing':
        if f.get('severity', 0) > 0.7 and f.get('expertise', 0) < 0.5:
            return 'call_expert'
        elif f.get('time_pressure', 0) > 0.7:
            return 'triage'
        else:
            return 'standard_treatment'
    elif situation.type == 'defense':
        if f.get('warning_time', 0) > 0.5:
            return 'prepare'
        elif f.get('fortification', 0) > 0.5:
            return 'fortify'
        else:
            return 'evacuate'
    return 'default_action'


def action_quality(action: str, situation: Situation) -> float:
    """How good is this action? 1.0 = optimal, 0.0 = terrible."""
    optimal = optimal_response(situation)
    if action == optimal:
        return 1.0
    # Partial credit for reasonable alternatives
    alternatives = get_reasonable_alternatives(situation)
    if action in alternatives:
        return 0.5
    return 0.1  # bad choice


def get_reasonable_alternatives(situation: Situation) -> List[str]:
    """Get sub-optimal but reasonable actions."""
    f = situation.features
    if situation.type == 'combat':
        if f.get('threat_level', 0.5) < 0.5:
            return ['attack', 'negotiate']
        return ['defend', 'negotiate']
    elif situation.type == 'navigation':
        return ['explore', 'ask_directions']
    elif situation.type == 'social':
        return ['listen', 'observe']
    elif situation.type == 'resource':
        return ['share', 'scout']
    elif situation.type == 'crafting':
        return ['follow_recipe', 'ask_help']
    elif situation.type == 'puzzle':
        return ['take_break', 'ask_hint']
    elif situation.type == 'stealth':
        return ['wait', 'observe']
    elif situation.type == 'trade':
        return ['observe', 'ask_questions']
    elif situation.type == 'healing':
        return ['stabilize', 'call_help']
    elif situation.type == 'defense':
        return ['watch', 'communicate']
    return ['default_action']


# ─── Script ──────────────────────────────────────────────────────────

@dataclass
class Script:
    name: str
    pattern_signature: str  # what situation pattern this script handles
    action: str             # what action to take
    creation_time: int      # when was this script created
    use_count: int = 0
    success_count: int = 0
    last_used: int = 0
    snap_tolerance: float = 0.2  # how close a situation must be to match
    
    def snap_match(self, situation: Situation, distance: float) -> bool:
        """Does this situation snap to this script's pattern?"""
        return distance <= self.snap_tolerance
    
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 0.5
        return self.success_count / self.use_count


# ─── Learning Agent ──────────────────────────────────────────────────

class LearningAgent:
    def __init__(self):
        self.scripts: List[Script] = []
        self.delta_buffer: List[Tuple[Situation, str, float, int]] = []  # (situation, action, quality, time)
        self.pattern_counts: Dict[str, int] = defaultdict(int)
        self.total_experiences = 0
        self.total_scripts_created = 0
        
        # Metrics tracking
        self.metrics = {
            'scripts_over_time': [],
            'script_hit_rate_over_time': [],
            'cognitive_load_over_time': [],
            'performance_over_time': [],
            'new_scripts_per_window': [],
        }
    
    def choose_action(self, situation: Situation, t: int) -> Tuple[str, bool]:
        """Choose an action. Returns (action, was_scripted)."""
        # Try to snap to existing script
        best_script = None
        best_dist = float('inf')
        
        for script in self.scripts:
            # Create a template situation from script signature
            # Simple distance: check type match + feature proximity
            if not situation.type in script.pattern_signature:
                continue
            
            # Compute distance based on how well features match
            # (simplified: use signature matching)
            sig = situation.signature()
            if sig == script.pattern_signature:
                best_script = script
                best_dist = 0
                break
            
            # Partial match on type
            if best_dist > 0.5:
                best_script = script
                best_dist = 0.5
        
        if best_script and best_dist <= best_script.snap_tolerance:
            best_script.use_count += 1
            best_script.last_used = t
            return best_script.action, True
        
        # No script match — this is a delta. Need to think.
        # Random action (novice decision)
        all_actions = ['attack', 'retreat', 'ambush', 'explore', 'negotiate',
                       'gather', 'conserve', 'follow_recipe', 'experiment',
                       'use_hint', 'brute_force', 'sneak', 'wait', 'cautious',
                       'formal', 'casual', 'default_action', 'compete',
                       'distraction', 'fair_deal', 'triage', 'prepare',
                       'fortify', 'evacuate', 'auto_navigate', 'landmark_navigate',
                       'observe', 'listen', 'share', 'scout', 'ask_help',
                       'call_expert', 'standard_treatment', 'leverage_info',
                       'cautious_offer', 'stabilize', 'call_help', 'watch',
                       'communicate', 'take_break', 'ask_hint', 'ask_directions',
                       'apply_pattern', 'defend']
        
        # Semi-smart: prefer actions relevant to situation type
        relevant = get_reasonable_alternatives(situation) + [optimal_response(situation)]
        if random.random() < 0.3:
            action = random.choice(relevant)
        else:
            action = random.choice(all_actions)
        
        return action, False
    
    def learn(self, situation: Situation, action: str, quality: float, t: int):
        """Learn from this experience."""
        self.total_experiences += 1
        
        # Record delta (unscripted experience)
        self.delta_buffer.append((situation, action, quality, t))
        
        # Count pattern occurrences
        sig = situation.signature()
        self.pattern_counts[sig] += 1
        
        # If pattern seen 3+ times and quality is decent, create a script
        if self.pattern_counts[sig] >= 3:
            # Check if we already have a script for this
            existing = [s for s in self.scripts if s.pattern_signature == sig]
            if not existing:
                # Create script with the best action seen for this pattern
                pattern_experiences = [(s, a, q) for s, a, q, _ in self.delta_buffer 
                                      if s.signature() == sig]
                if pattern_experiences:
                    # Pick action with highest average quality
                    action_scores = defaultdict(list)
                    for s, a, q in pattern_experiences:
                        action_scores[a].append(q)
                    best_action = max(action_scores.items(), 
                                    key=lambda x: sum(x[1])/len(x[1]))[0]
                    
                    script = Script(
                        name=f"script_{self.total_scripts_created}",
                        pattern_signature=sig,
                        action=best_action,
                        creation_time=t,
                        snap_tolerance=0.3,
                    )
                    self.scripts.append(script)
                    self.total_scripts_created += 1
            else:
                # Update existing script if we found a better action
                script = existing[0]
                if quality > 0.7:
                    script.success_count += 1
    
    def record_metrics(self, t: int, window: int = 1000):
        """Record metrics at this timestep."""
        if t % window == 0 and t > 0:
            # Scripts over time
            self.metrics['scripts_over_time'].append((t, len(self.scripts)))
            
            # Script hit rate (last window)
            recent = [(s, a, q, time) for s, a, q, time in self.delta_buffer 
                      if t - time < window]
            scripted = sum(1 for _, _, q, _ in recent if q >= 0.8)
            hit_rate = scripted / max(len(recent), 1)
            self.metrics['script_hit_rate_over_time'].append((t, round(hit_rate, 3)))
            
            # Cognitive load (unscripted decisions)
            unscripted = sum(1 for _, _, q, _ in recent if q < 0.8)
            self.metrics['cognitive_load_over_time'].append((t, unscripted))
            
            # Performance (average quality)
            avg_quality = sum(q for _, _, q, _ in recent) / max(len(recent), 1)
            self.metrics['performance_over_time'].append((t, round(avg_quality, 3)))
            
            # New scripts in window
            new_scripts = sum(1 for s in self.scripts 
                            if s.creation_time > t - window)
            self.metrics['new_scripts_per_window'].append((t, new_scripts))


def run_simulation(num_experiences: int = 100000) -> dict:
    """Run the full learning cycle simulation."""
    agent = LearningAgent()
    rng = random.Random(42)
    
    performance_window = []
    cognitive_load_window = []
    script_hits_window = []
    
    # Detailed tracking
    phase_transitions = []
    prev_script_count = 0
    prev_phase = 'learning'
    
    for t in range(num_experiences):
        situation = generate_situation(rng)
        action, was_scripted = agent.choose_action(situation, t)
        quality = action_quality(action, situation)
        
        if was_scripted:
            quality = min(quality + 0.1, 1.0)  # scripted actions get slight bonus
        
        agent.learn(situation, action, quality, t)
        agent.record_metrics(t)
        
        performance_window.append(quality)
        cognitive_load_window.append(0 if was_scripted else 1)
        script_hits_window.append(1 if was_scripted else 0)
        
        # Detect phase transitions
        if t % 1000 == 0 and t > 0:
            current_count = len(agent.scripts)
            new_phase = 'learning' if current_count > prev_script_count else 'smooth'
            if new_phase != prev_phase:
                phase_transitions.append({
                    'time': t,
                    'from_phase': prev_phase,
                    'to_phase': new_phase,
                    'scripts': current_count,
                })
            prev_phase = new_phase
            prev_script_count = current_count
    
    # Compute final results
    window = 1000
    
    def window_avg(data, start, end):
        chunk = data[start:end]
        return sum(chunk) / len(chunk) if chunk else 0
    
    # Split into 10 epochs
    num_epochs = 10
    epoch_size = num_experiences // num_epochs
    
    epoch_data = []
    for epoch in range(num_epochs):
        start = epoch * epoch_size
        end = start + epoch_size
        epoch_data.append({
            'epoch': epoch + 1,
            'range': f"{start}-{end}",
            'avg_performance': round(window_avg(performance_window, start, end), 4),
            'cognitive_load': round(window_avg(cognitive_load_window, start, end), 4),
            'script_hit_rate': round(window_avg(script_hits_window, start, end), 4),
        })
    
    return {
        'total_experiences': num_experiences,
        'final_scripts': len(agent.scripts),
        'total_scripts_created': agent.total_scripts_created,
        'epochs': epoch_data,
        'phase_transitions': phase_transitions[:20],
        'sample_scripts': [
            {
                'name': s.name,
                'pattern': s.pattern_signature[:60],
                'action': s.action,
                'uses': s.use_count,
                'success_rate': round(s.success_rate(), 3),
                'created_at': s.creation_time,
            }
            for s in agent.scripts[:20]
        ],
        'insight': (
            "The agent should show phase transitions: early epochs have high cognitive load "
            "and low performance (many deltas, no scripts). Middle epochs show rapid script creation "
            "(learning burst). Later epochs show smooth execution — most situations snap to scripts, "
            "cognitive load drops, performance stabilizes high. The snap function automates what was "
            "once novel, freeing cognition for truly new situations."
        ),
    }


if __name__ == '__main__':
    print("🧠 Delta-to-Script Learning Cycle — Running 100,000 experiences...")
    results = run_simulation(100000)
    
    with open('results_learning_cycle.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to results_learning_cycle.json")
    print(f"\n📊 Final scripts: {results['final_scripts']}")
    print(f"\n📈 Epoch performance:")
    for epoch in results['epochs']:
        print(f"  Epoch {epoch['epoch']:2d} ({epoch['range']:>12s}): "
              f"perf={epoch['avg_performance']:.3f}, "
              f"load={epoch['cognitive_load']:.3f}, "
              f"hit_rate={epoch['script_hit_rate']:.3f}")
    print(f"\n🔄 Phase transitions: {len(results['phase_transitions'])}")
