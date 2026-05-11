#!/usr/bin/env python3
"""
Simulator 4: Multi-Flavor Attention Budget

Agent with finite attention budget across multiple information streams.
Each stream has different randomness flavor. Snap compresses within-tolerance.
Three strategies: uniform, reactive, smart (actionability-weighted).
"""

import json
import random
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from collections import defaultdict

# ─── Randomness Flavors ─────────────────────────────────────────────

def coin_stream(n: int) -> List[float]:
    return [random.choice([0.0, 1.0]) for _ in range(n)]

def d6_stream(n: int) -> List[float]:
    return [random.randint(1, 6) / 6.0 for _ in range(n)]

def d20_stream(n: int) -> List[float]:
    return [random.randint(1, 20) / 20.0 for _ in range(n)]

def bell_stream(n: int) -> List[float]:
    return [(random.randint(1,6) + random.randint(1,6)) / 12.0 for _ in range(n)]

def gaussian_stream(n: int) -> List[float]:
    return [max(0, min(1, random.gauss(0.5, 0.15))) for _ in range(n)]

def spike_stream(n: int) -> List[float]:
    """Rare spikes — mostly 0, occasional 1."""
    return [1.0 if random.random() < 0.05 else 0.0 for _ in range(n)]

def sine_stream(n: int) -> List[float]:
    """Predictable sine wave — low entropy."""
    return [0.5 + 0.4 * math.sin(2 * math.pi * i / 20) for i in range(n)]

def drift_stream(n: int) -> List[float]:
    """Slow drift with noise."""
    val = 0.5
    result = []
    for _ in range(n):
        val += random.gauss(0, 0.02)
        val = max(0, min(1, val))
        result.append(val)
    return result

def categorical_stream(n: int) -> List[float]:
    return [random.choice([0.0, 0.25, 0.5, 0.75, 1.0]) for _ in range(n)]

def burst_stream(n: int) -> List[float]:
    """Bursty — long quiet periods, then clusters of activity."""
    result = []
    for _ in range(n):
        if random.random() < 0.1:
            result.extend([random.uniform(0.7, 1.0)] * random.randint(1, 3))
        else:
            result.append(random.uniform(0.0, 0.3))
    return result[:n]


STREAM_GENERATORS = {
    'coin': coin_stream,
    'd6': d6_stream,
    'd20': d20_stream,
    'bell': bell_stream,
    'gaussian': gaussian_stream,
    'spike': spike_stream,
    'sine': sine_stream,
    'drift': drift_stream,
    'categorical': categorical_stream,
    'burst': burst_stream,
}

# ─── Information Stream ─────────────────────────────────────────────

@dataclass
class InfoStream:
    name: str
    flavor: str
    data: List[float]
    actionability: float  # 0-1, how much thinking can affect outcome
    true_anomaly_rate: float  # rate of genuine anomalies (ground truth)
    
    # Snap function
    tolerance: float = 0.15
    baseline: float = 0.5
    
    def __post_init__(self):
        self.baseline = self.data[0] if self.data else 0.5
    
    def snap(self, value: float) -> Tuple[bool, float]:
        delta = abs(value - self.baseline)
        if delta <= self.tolerance:
            self.baseline = 0.9 * self.baseline + 0.1 * value
            return True, delta
        return False, delta
    
    def is_true_anomaly(self, value: float, t: int) -> bool:
        """Ground truth: is this actually anomalous?"""
        # Use a moving window approach
        window = 20
        start = max(0, t - window)
        window_data = self.data[start:t]
        if not window_data:
            return False
        mean = sum(window_data) / len(window_data)
        std = (sum((x - mean)**2 for x in window_data) / len(window_data)) ** 0.5
        return abs(value - mean) > max(std * 1.5, 0.1)


# ─── Attention Strategies ───────────────────────────────────────────

def allocate_uniform(streams: List[InfoStream], deltas: List[Tuple[int, float]], 
                     budget: int) -> List[int]:
    """Equal attention to all streams with deltas."""
    if not deltas:
        return []
    random.shuffle(deltas)
    return [d[0] for d in deltas[:budget]]


def allocate_reactive(streams: List[InfoStream], deltas: List[Tuple[int, float]], 
                      budget: int) -> List[int]:
    """Attend to biggest deltas regardless of stream."""
    sorted_deltas = sorted(deltas, key=lambda x: x[1], reverse=True)
    return [d[0] for d in sorted_deltas[:budget]]


def allocate_smart(streams: List[InfoStream], deltas: List[Tuple[int, float]], 
                   budget: int) -> List[int]:
    """Attend to deltas weighted by actionability."""
    scored = [(idx, delta * streams[idx].actionability) for idx, delta in deltas]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:budget]]


STRATEGIES = {
    'uniform': allocate_uniform,
    'reactive': allocate_reactive,
    'smart': allocate_smart,
}


def run_simulation(num_timesteps: int = 100000, budget: int = 3) -> dict:
    """Run the multi-stream attention budget simulation."""
    
    num_streams = 10
    timesteps = num_timesteps
    
    # Create streams with different properties
    stream_configs = [
        ('coin', 0.3, 0.02),       # low actionability, low anomaly rate
        ('d6', 0.5, 0.05),
        ('d20', 0.6, 0.04),
        ('bell', 0.7, 0.03),
        ('gaussian', 0.8, 0.06),
        ('spike', 0.9, 0.05),      # high actionability, spikes ARE the anomalies
        ('sine', 0.2, 0.01),       # low actionability, very predictable
        ('drift', 0.6, 0.04),
        ('categorical', 0.4, 0.05),
        ('burst', 0.85, 0.05),     # high actionability
    ]
    
    # Generate data
    stream_data = {}
    for name, actionability, anomaly_rate in stream_configs:
        gen = STREAM_GENERATORS[name]
        data = gen(timesteps)
        # Inject true anomalies
        for i in range(timesteps):
            if random.random() < anomaly_rate:
                # Create a real anomaly
                data[i] = 1.0 - data[i]  # flip
        stream_data[name] = (data, actionability, anomaly_rate)
    
    results = {}
    
    for strategy_name, strategy_fn in STRATEGIES.items():
        streams = []
        for name, (data, actionability, anomaly_rate) in stream_data.items():
            streams.append(InfoStream(
                name=name, flavor=name, data=data,
                actionability=actionability, true_anomaly_rate=anomaly_rate,
                tolerance=0.15, baseline=data[0] if data else 0.5,
            ))
        
        total_utility = 0
        missed_opportunities = 0
        attention_waste = 0
        total_deltas = 0
        correct_attend = 0
        false_attend = 0
        true_anomalies_missed = 0
        
        for t in range(timesteps):
            # Detect deltas across all streams
            deltas = []
            for idx, stream in enumerate(streams):
                value = stream.data[t]
                snapped, delta = stream.snap(value)
                if not snapped:
                    deltas.append((idx, delta))
                    total_deltas += 1
            
            # Allocate attention
            attended = strategy_fn(streams, deltas, budget)
            
            # Score the allocation
            for idx in attended:
                stream = streams[idx]
                value = stream.data[t]
                is_anomaly = stream.is_true_anomaly(value, t)
                
                if is_anomaly:
                    total_utility += stream.actionability  # high-value catch
                    correct_attend += 1
                else:
                    attention_waste += 0.1  # wasted attention on non-anomaly
                    false_attend += 1
            
            # Count missed true anomalies
            for idx in range(len(streams)):
                if idx not in attended:
                    stream = streams[idx]
                    value = stream.data[t]
                    is_anomaly = stream.is_true_anomaly(value, t)
                    if is_anomaly and any(d[0] == idx for d in deltas):
                        missed_opportunities += 1
                        true_anomalies_missed += 1
        
        results[strategy_name] = {
            'total_utility': round(total_utility, 2),
            'missed_opportunities': missed_opportunities,
            'attention_waste': round(attention_waste, 2),
            'total_deltas_detected': total_deltas,
            'correct_attends': correct_attend,
            'false_attends': false_attend,
            'true_anomalies_missed': true_anomalies_missed,
            'precision': round(correct_attend / max(correct_attend + false_attend, 1), 4),
            'net_value': round(total_utility - attention_waste, 2),
        }
    
    return {
        'timesteps': timesteps,
        'budget': budget,
        'num_streams': num_streams,
        'strategies': results,
        'insight': (
            "Smart strategy (actionability-weighted) should outperform because it directs attention "
            "to deltas where thinking can actually change outcomes. Reactive wastes attention on "
            "large deltas from low-actionability streams. Uniform wastes attention randomly."
        ),
    }


if __name__ == '__main__':
    print("📡 Multi-Flavor Attention Budget — Running 100,000 timesteps...")
    results = run_simulation(100000)
    
    with open('results_attention_budget.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to results_attention_budget.json")
    for name, data in results['strategies'].items():
        print(f"\n  {name}:")
        print(f"    Utility: {data['total_utility']}")
        print(f"    Net value: {data['net_value']}")
        print(f"    Missed opportunities: {data['missed_opportunities']}")
        print(f"    Attention waste: {data['attention_waste']}")
        print(f"    Precision: {data['precision']}")
