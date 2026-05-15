#!/usr/bin/env python3
"""core/critical_angle.py — Critical angle measurement and integration.

The critical angle is the fleet's fundamental measurement unit.
This module provides:
  1. Critical angle measurement for any model × axis
  2. Export to fleet-math format (compatible with Oracle1's CouplingAnalysis)
  3. Integration with fleet_router for automatic config updates
  4. Cross-model comparison matrices

This is the LONG-TERM ECOSYSTEM integration piece:
  - Oracle1's fleet-math provides spectral analysis
  - FM's critical_angle provides behavioral analysis
  - Together: structural + behavioral = complete fleet understanding
  
Usage:
    from core.critical_angle import CriticalAngleMapper
    
    mapper = CriticalAngleMapper()
    angles = mapper.measure("seed-mini", "addition_depth")
    matrix = mapper.comparison_matrix()
    mapper.export_fleet_math()  # Export for Oracle1's fleet-math
"""

from __future__ import annotations

import json, os, re, time, statistics
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

import requests

API_KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
PLATO_URL = "http://147.224.38.131:8847"


@dataclass 
class AngleMeasurement:
    """A single critical angle measurement."""
    model: str
    axis: str
    critical_angle: Optional[int]  # None = ∞
    accuracy_curve: Dict[int, float]  # depth → accuracy
    n_trials: int = 3
    timestamp: str = ""
    confidence: float = 0.0  # How confident in the measurement (0-1)
    
    @property
    def is_infinite(self) -> bool:
        return self.critical_angle is None
    
    @property
    def phase_type(self) -> str:
        """Classify the phase transition."""
        if self.is_infinite:
            return "no_transition"
        
        # Check if it's a sharp cliff or a gradual slope
        accs = sorted(self.accuracy_curve.items())
        drops = []
        for i in range(len(accs) - 1):
            drop = accs[i][1] - accs[i+1][1]
            if drop > 0:
                drops.append(drop)
        
        if drops and max(drops) > 0.5:
            return "sharp_cliff"  # Phase transition
        elif drops and max(drops) > 0.2:
            return "moderate_cliff"
        else:
            return "gradual"


@dataclass
class ModelProfile:
    """Complete critical angle profile for a model."""
    model_key: str
    model_id: str
    measurements: Dict[str, AngleMeasurement] = field(default_factory=dict)
    
    @property
    def strongest_axis(self) -> str:
        """Which axis has the highest critical angle (or ∞)?"""
        best_axis = None
        best_angle = -1
        for axis, m in self.measurements.items():
            if m.is_infinite:
                return axis
            if m.critical_angle and m.critical_angle > best_angle:
                best_angle = m.critical_angle
                best_axis = axis
        return best_axis or "unknown"
    
    @property
    def weakest_axis(self) -> str:
        """Which axis has the lowest critical angle?"""
        worst_axis = None
        worst_angle = float('inf')
        for axis, m in self.measurements.items():
            if m.critical_angle is not None and m.critical_angle < worst_angle:
                worst_angle = m.critical_angle
                worst_axis = axis
        return worst_axis or "unknown"
    
    @property
    def fleet_role(self) -> str:
        """Suggested fleet role based on critical angle profile."""
        infinite_axes = sum(1 for m in self.measurements.values() if m.is_infinite)
        total_axes = len(self.measurements)
        
        if infinite_axes == total_axes:
            return "universal"  # Use for everything
        elif infinite_axes > total_axes / 2:
            return "workhorse"  # Primary compute
        elif infinite_axes > 0:
            return "specialist"  # Use for specific axes
        else:
            return "limited"  # Use only within known bounds


# ─── Probe Definitions ─────────────────────────────────────────────────────────

def _addition_probe(depth, trial=0):
    terms = [str((i * 7 + trial * 3 + 3) % 10 + 1) for i in range(depth)]
    prompt = " + ".join(terms)
    expected = str(sum(int(t) for t in terms))
    return prompt, expected

def _multiplication_probe(depth, trial=0):
    factors = [str((i * 3 + trial * 2 + 2) % 4 + 2) for i in range(depth)]
    prompt = " * ".join(factors)
    val = 1
    for f in factors: val *= int(f)
    return prompt, str(val)

def _nesting_probe(depth, trial=0):
    val = 3 + trial
    expr = str(val)
    ops = [("+", 2), ("*", 3), ("-", 1), ("+", 4), ("*", 2), ("-", 2), ("+", 3)]
    for d in range(depth):
        op, n = ops[d % len(ops)]
        if op == "+": val += n
        elif op == "-": val -= n
        elif op == "*": val *= n
        expr = f"({expr}{op}{n})"
    return expr, str(val)

def _coefficient_probe(level, trial=0):
    """Coefficient familiarity at different levels."""
    a = 5 + trial
    b = 3 + trial
    patterns = {
        0: (f"a*a + b*b where a={a}, b={b}", str(a*a + b*b)),
        1: (f"a*a - a*b + b*b where a={a}, b={b}", str(a*a - a*b + b*b)),
        2: (f"a*a - 2*a*b + b*b where a={a}, b={b}", str(a*a - 2*a*b + b*b)),
        3: (f"a*a - 3*a*b + b*b where a={a}, b={b}", str(a*a - 3*a*b + b*b)),
        4: (f"2*a*a - a*b + b*b where a={a}, b={b}", str(2*a*a - a*b + b*b)),
        5: (f"a*a + 5*a*b + b*b where a={a}, b={b}", str(a*a + 5*a*b + b*b)),
    }
    return patterns.get(level, (f"2+2", "4"))

PROBES = {
    "addition_depth": {"gen": _addition_probe, "depths": [5, 10, 15, 20, 25, 30], "mt": 80},
    "multiplication_depth": {"gen": _multiplication_probe, "depths": [3, 5, 6, 7, 8, 9, 10], "mt": 80},
    "nesting": {"gen": _nesting_probe, "depths": [2, 3, 4, 5, 6, 7, 8], "mt": 80},
    "coefficient_familiarity": {"gen": _coefficient_probe, "depths": [0, 1, 2, 3, 4, 5], "mt": 80},
}

MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "gemini-lite": "google/gemini-3.1-flash-lite",
    "hermes-70b": "NousResearch/Hermes-3-Llama-3.1-70B",
    "qwen-0.8b": "Qwen/Qwen3.5-0.8B",
}


def _key():
    return open(API_KEY_PATH).read().strip()


def _query(model, prompt, max_tokens=80):
    ak = _key()
    headers = {"Authorization": f"Bearer {ak}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [
        {"role": "system", "content": "You are a calculator. Output the result number ONLY."},
        {"role": "user", "content": prompt},
    ], "temperature": 0.0, "max_tokens": max_tokens}
    try:
        r = requests.post("https://api.deepinfra.com/v1/openai/chat/completions",
                          headers=headers, json=payload, timeout=90)
        d = r.json()
        msg = d["choices"][0]["message"]
        c = (msg.get("content") or "").strip()
        r_txt = (msg.get("reasoning_content") or "").strip()
        text = c if c else r_txt
        nums = re.findall(r"-?\d+\.?\d*", text)
        return nums[-1] if nums else None
    except:
        return None


class CriticalAngleMapper:
    """Map critical angles across models and axes.
    
    This is the fleet's measurement instrument. It produces the data
    that feeds the fleet router, health monitor, and fleet-math integration.
    """
    
    def __init__(self, models: Dict = None):
        self.models = models or MODELS
        self.profiles: Dict[str, ModelProfile] = {}
    
    def measure(self, model_key: str, axis: str, trials: int = 3) -> AngleMeasurement:
        """Measure the critical angle for one model on one axis."""
        mid = self.models[model_key]
        probe = PROBES[axis]
        gen = probe["gen"]
        depths = probe["depths"]
        mt = probe["mt"]
        
        acc_curve = {}
        for d in depths:
            correct = 0
            for trial in range(trials):
                prompt, expected = gen(d, trial)
                got = _query(mid, prompt, max_tokens=mt)
                if got and expected:
                    try:
                        if abs(float(got) - float(expected)) / max(abs(float(expected)), 1) < 0.05:
                            correct += 1
                    except: pass
            acc_curve[d] = correct / trials
        
        # Find critical angle
        critical_angle = None
        for d in sorted(acc_curve.keys()):
            if acc_curve[d] < 0.5:
                critical_angle = d
                break
        
        # Confidence: higher if sharp transition
        confidence = 0.5
        accs = sorted(acc_curve.items())
        for i in range(len(accs) - 1):
            drop = accs[i][1] - accs[i+1][1]
            if drop > 0.5:
                confidence = min(1.0, confidence + 0.3)
        
        return AngleMeasurement(
            model=model_key,
            axis=axis,
            critical_angle=critical_angle,
            accuracy_curve=acc_curve,
            n_trials=trials,
            timestamp=datetime.utcnow().isoformat() + "Z",
            confidence=round(confidence, 2),
        )
    
    def measure_all(self, model_keys: List[str] = None) -> Dict[str, ModelProfile]:
        """Measure all models on all axes."""
        keys = model_keys or list(self.models.keys())
        
        for mk in keys:
            if mk not in self.models: continue
            profile = ModelProfile(
                model_key=mk,
                model_id=self.models[mk],
            )
            for axis in PROBES:
                print(f"  Measuring {mk} × {axis}...", flush=True)
                profile.measurements[axis] = self.measure(mk, axis)
            self.profiles[mk] = profile
        
        return self.profiles
    
    def comparison_matrix(self) -> str:
        """Generate a comparison matrix of all measured profiles."""
        if not self.profiles:
            return "No profiles measured yet."
        
        axes = list(PROBES.keys())
        models = list(self.profiles.keys())
        
        # Header
        header = f"{'Model':15s}" + "".join(f"{a[:12]:>13s}" for a in axes) + f"{'Role':>12s}"
        lines = [header, "-" * len(header)]
        
        for mk, p in self.profiles.items():
            row = f"{mk:15s}"
            for axis in axes:
                m = p.measurements.get(axis)
                if m and m.is_infinite:
                    row += f"{'∞':>13s}"
                elif m and m.critical_angle:
                    row += f"{m.critical_angle:>13d}"
                elif m:
                    row += f"{'?':>13s}"
                else:
                    row += f"{'-':>13s}"
            row += f"{p.fleet_role:>12s}"
            lines.append(row)
        
        return "\n".join(lines)
    
    def export_fleet_math(self) -> Dict:
        """Export critical angles in fleet-math compatible format.
        
        Oracle1's fleet-math uses CouplingAnalysis for spectral decomposition.
        Our critical angles complement that with behavioral measurements.
        
        Output format matches fleet-math's CouplingAnalysis.build_coupling schema.
        """
        export = {
            "schema": "critical_angle_v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "forgemaster-core",
            "models": {},
            "coupling_matrix": [],
        }
        
        axes = list(PROBES.keys())
        models = list(self.profiles.keys())
        
        for mk, p in self.profiles.items():
            export["models"][mk] = {
                "model_id": p.model_id,
                "fleet_role": p.fleet_role,
                "strongest_axis": p.strongest_axis,
                "weakest_axis": p.weakest_axis,
                "critical_angles": {
                    axis: ("inf" if m.is_infinite else m.critical_angle)
                    for axis, m in p.measurements.items()
                },
                "phase_types": {
                    axis: m.phase_type
                    for axis, m in p.measurements.items()
                },
            }
        
        # Build coupling matrix: model × model overlap
        # Two models "couple" when they share the same critical angle on an axis
        for m1 in models:
            row = []
            for m2 in models:
                shared = 0
                total = len(axes)
                for axis in axes:
                    a1 = self.profiles[m1].measurements.get(axis)
                    a2 = self.profiles[m2].measurements.get(axis)
                    if a1 and a2:
                        if a1.is_infinite and a2.is_infinite:
                            shared += 1
                        elif a1.critical_angle and a2.critical_angle:
                            # Close enough counts
                            if abs(a1.critical_angle - a2.critical_angle) <= 1:
                                shared += 1
                row.append(shared / total if total else 0)
            export["coupling_matrix"].append(row)
        
        return export
    
    def to_fleet_router_config(self) -> Dict:
        """Export as fleet_router.py FLEET config dict."""
        config = {}
        for mk, p in self.profiles.items():
            from core.fleet_router import ModelProfile, QueryAxis
            
            angles = {}
            for axis, m in p.measurements.items():
                try:
                    qa = QueryAxis(axis)
                    angles[qa] = m.critical_angle
                except ValueError:
                    pass
            
            # Import here to avoid circular
            config[mk] = {
                "model_id": p.model_id,
                "model_key": mk,
                "critical_angles": angles,
                "fleet_role": p.fleet_role,
            }
        
        return config


def main():
    import argparse
    p = argparse.ArgumentParser(description="Critical Angle Mapper")
    p.add_argument("--models", nargs="+", default=["seed-mini", "gemini-lite"])
    p.add_argument("--axes", nargs="+", default=None)
    p.add_argument("--full", action="store_true", help="Measure all models")
    p.add_argument("--export", action="store_true", help="Export fleet-math format")
    p.add_argument("--matrix", action="store_true", help="Show comparison matrix")
    args = p.parse_args()
    
    mapper = CriticalAngleMapper()
    
    if args.full:
        args.models = list(MODELS.keys())
    
    print("CRITICAL ANGLE MAPPER")
    print("=" * 60)
    
    mapper.measure_all(args.models)
    
    print("\n" + mapper.comparison_matrix())
    
    if args.export:
        data = mapper.export_fleet_math()
        path = os.path.expanduser("~/.openclaw/workspace/experiments/critical-angle-export.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nExported to {path}")


if __name__ == "__main__":
    main()
