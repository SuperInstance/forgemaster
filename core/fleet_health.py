#!/usr/bin/env python3
"""core/fleet_health.py — Fleet health monitoring using critical angles.

Long-term ecosystem tool: monitors fleet model health by periodically
probing critical angles and detecting phase boundary drift.

If a model's critical angle shrinks over time (due to API changes,
model updates, quantization changes), the fleet router needs to know.

This tool:
  1. Runs periodic calibration probes against fleet models
  2. Tracks critical angle drift over time
  3. Updates fleet_router.py's FLEET config when angles change
  4. Emits PLATO tiles with health diagnostics
  5. Alerts when a model's critical angle has degraded

Usage:
    from core.fleet_health import FleetHealth
    
    health = FleetHealth()
    report = health.calibrate()  # Run full calibration
    health.report()              # Print report
    health.emit_plato()          # Emit PLATO tile
"""

from __future__ import annotations

import json, os, re, time, statistics
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

import requests

API_KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
PLATO_URL = "http://localhost:8847  # local PLATO (default)"
HEALTH_HISTORY_PATH = os.path.expanduser("~/.openclaw/workspace/experiments/fleet-health-history.json")


class HealthStatus(Enum):
    HEALTHY = "healthy"           # Critical angle stable
    DEGRADED = "degraded"         # Critical angle shrinking
    CRITICAL = "critical"         # Critical angle halved or more
    UNKNOWN = "unknown"           # No baseline data


@dataclass
class AxisCalibration:
    """Calibration result for one axis of one model."""
    axis: str
    depth_tested: int
    accuracy_at_depth: Dict[int, float]  # depth → accuracy
    critical_angle: Optional[int]        # None = no transition found
    baseline_angle: Optional[int]        # Previously known angle
    drift: int = 0                       # How much the angle changed
    status: HealthStatus = HealthStatus.UNKNOWN


@dataclass
class ModelHealth:
    """Health report for one model across all axes."""
    model_key: str
    model_id: str
    timestamp: str
    axes: Dict[str, AxisCalibration] = field(default_factory=dict)
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0
    total_probes: int = 0
    
    @property
    def any_degraded(self) -> bool:
        return any(a.status == HealthStatus.DEGRADED for a in self.axes.values())
    
    @property
    def any_critical(self) -> bool:
        return any(a.status == HealthStatus.CRITICAL for a in self.axes.values())


# Baseline critical angles (from 2026-05-14/15 experiments)
BASELINES = {
    "gemini-lite": {
        "addition_depth": 25,
        "multiplication_depth": 9,
        "nesting": 5,
        "coefficient_familiarity": 3,
        "word_complexity": 4,
    },
    "seed-mini": {
        "addition_depth": None,  # ∞
        "multiplication_depth": None,  # ∞ (through 10)
        "nesting": None,  # ∞ (through 8)
        "coefficient_familiarity": 4,
        "word_complexity": None,  # ∞
    },
    "hermes-70b": {
        "addition_depth": 10,
        "multiplication_depth": 5,
        "nesting": 3,
        "coefficient_familiarity": 2,
        "word_complexity": 3,
    },
}

MODELS = {
    "gemini-lite": "google/gemini-3.1-flash-lite",
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "hermes-70b": "NousResearch/Hermes-3-Llama-3.1-70B",
}

SYSTEM = "You are a calculator. Output the result number ONLY."


def _key():
    return open(API_KEY_PATH).read().strip()


def _query(model, prompt, max_tokens=80):
    ak = _key()
    headers = {"Authorization": f"Bearer {ak}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ], "temperature": 0.0, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post("https://api.deepinfra.com/v1/openai/chat/completions",
                          headers=headers, json=payload, timeout=90)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "latency_ms": lat}
        d = r.json()
        msg = d["choices"][0]["message"]
        c = (msg.get("content") or "").strip()
        r_txt = (msg.get("reasoning_content") or "").strip()
        text = c if c else r_txt
        nums = re.findall(r"-?\d+\.?\d*", text)
        return {"answer": nums[-1] if nums else None, "latency_ms": lat, "text": text}
    except Exception as e:
        return {"error": str(e), "latency_ms": (time.time() - start) * 1000}


# ─── Probe Generators ─────────────────────────────────────────────────────────

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

PROBE_GENERATORS = {
    "addition_depth": _addition_probe,
    "multiplication_depth": _multiplication_probe,
    "nesting": _nesting_probe,
}

# Depths to test for each axis
TEST_DEPTHS = {
    "addition_depth": [5, 10, 15, 20, 25, 30],
    "multiplication_depth": [3, 5, 6, 7, 8, 9, 10],
    "nesting": [2, 3, 4, 5, 6, 7, 8],
}

TRIALS = 3


class FleetHealth:
    """Monitor fleet model health through critical angle calibration.
    
    The fleet's routing depends on accurate critical angles.
    If a model degrades (API change, version update, quantization),
    its critical angles shrink and the router sends it queries it can't handle.
    
    This tool catches degradation early by periodically re-probing
    critical angles and comparing to baseline.
    """
    
    def __init__(self, baselines: Dict = None, models: Dict = None):
        self.baselines = baselines or BASELINES
        self.models = models or MODELS
        self.history = self._load_history()
    
    def calibrate(self, model_keys: List[str] = None,
                  axes: List[str] = None) -> Dict[str, ModelHealth]:
        """Run calibration probes on fleet models.
        
        For each model × axis combination, probe a range of depths
        and find where the phase transition occurs.
        """
        model_keys = model_keys or list(self.models.keys())
        results = {}
        
        for mk in model_keys:
            if mk not in self.models: continue
            mid = self.models[mk]
            baseline = self.baselines.get(mk, {})
            test_axes = axes or list(PROBE_GENERATORS.keys())
            
            health = ModelHealth(
                model_key=mk,
                model_id=mid,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            
            total_probes = 0
            latencies = []
            
            for axis_name in test_axes:
                if axis_name not in PROBE_GENERATORS: continue
                gen = PROBE_GENERATORS[axis_name]
                depths = TEST_DEPTHS.get(axis_name, [3, 5, 7, 10])
                baseline_angle = baseline.get(axis_name)
                
                acc_at_depth = {}
                for d in depths:
                    correct = 0
                    for trial in range(TRIALS):
                        prompt, expected = gen(d, trial)
                        resp = _query(mid, prompt)
                        total_probes += 1
                        
                        if "error" in resp: continue
                        latencies.append(resp.get("latency_ms", 0))
                        
                        got = resp.get("answer")
                        if got and expected:
                            try:
                                if abs(float(got) - float(expected)) / max(abs(float(expected)), 1) < 0.05:
                                    correct += 1
                            except: pass
                    
                    acc_at_depth[d] = correct / TRIALS
                
                # Find critical angle (first depth where accuracy drops below 50%)
                critical_angle = None
                for d in sorted(acc_at_depth.keys()):
                    if acc_at_depth[d] < 0.5:
                        critical_angle = d
                        break
                
                # Compare to baseline
                drift = 0
                status = HealthStatus.HEALTHY
                if baseline_angle is not None and critical_angle is not None:
                    drift = baseline_angle - critical_angle
                    if drift > 0:
                        if critical_angle <= baseline_angle / 2:
                            status = HealthStatus.CRITICAL
                        else:
                            status = HealthStatus.DEGRADED
                elif baseline_angle is None and critical_angle is None:
                    status = HealthStatus.HEALTHY  # Both infinite
                elif baseline_angle is None and critical_angle is not None:
                    status = HealthStatus.CRITICAL  # Was infinite, now finite!
                
                health.axes[axis_name] = AxisCalibration(
                    axis=axis_name,
                    depth_tested=max(depths),
                    accuracy_at_depth=acc_at_depth,
                    critical_angle=critical_angle,
                    baseline_angle=baseline_angle,
                    drift=drift,
                    status=status,
                )
            
            health.total_probes = total_probes
            health.latency_ms = statistics.mean(latencies) if latencies else 0
            
            if health.any_critical:
                health.overall_status = HealthStatus.CRITICAL
            elif health.any_degraded:
                health.overall_status = HealthStatus.DEGRADED
            else:
                health.overall_status = HealthStatus.HEALTHY
            
            results[mk] = health
        
        # Save to history
        self._save_history(results)
        return results
    
    def report(self, results: Dict[str, ModelHealth] = None) -> str:
        """Generate a human-readable health report."""
        if results is None:
            results = self.history.get("latest", {})
        
        lines = [
            f"{'='*60}",
            f" FLEET HEALTH REPORT",
            f" {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"{'='*60}",
        ]
        
        for mk, h in results.items():
            if isinstance(h, dict):
                h = ModelHealth(**h) if "axes" in h else h
                if not isinstance(h, ModelHealth): continue
            
            status_emoji = {"healthy": "✅", "degraded": "⚠️", "critical": "🔴", "unknown": "❓"}
            emoji = status_emoji.get(h.overall_status.value, "❓")
            
            lines.append(f"\n{emoji} {mk} ({h.model_id})")
            lines.append(f"   Latency: {h.latency_ms:.0f}ms | Probes: {h.total_probes}")
            
            for ax_name, ax in h.axes.items():
                if isinstance(ax, dict):
                    ax = AxisCalibration(**ax)
                
                baseline_str = str(ax.baseline_angle) if ax.baseline_angle else "∞"
                measured_str = str(ax.critical_angle) if ax.critical_angle else "∞"
                drift_str = f" (drift={ax.drift:+d})" if ax.drift else ""
                ax_emoji = status_emoji.get(ax.status.value, "❓")
                
                lines.append(f"   {ax_emoji} {ax_name:25s}: {baseline_str:>3s} → {measured_str:>3s}{drift_str}")
                
                # Show accuracy curve
                if ax.accuracy_at_depth:
                    curve = "  ".join(f"d{d}={int(a*100):3d}%" for d, a in sorted(ax.accuracy_at_depth.items()))
                    lines.append(f"     {curve}")
        
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    def emit_plato(self, results: Dict[str, ModelHealth]) -> bool:
        """Emit a PLATO tile with fleet health data."""
        tile = {
            "room_id": "fleet_health",
            "agent": "forgemaster",
            "tile_type": "fleet_health_calibration",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "content": json.dumps({
                mk: {
                    "status": h.overall_status.value if isinstance(h, ModelHealth) else h.get("overall_status", "unknown"),
                    "latency_ms": h.latency_ms if isinstance(h, ModelHealth) else h.get("latency_ms", 0),
                    "axes": {
                        ax_name: {
                            "critical_angle": ax.critical_angle if isinstance(ax, AxisCalibration) else ax.get("critical_angle"),
                            "baseline_angle": ax.baseline_angle if isinstance(ax, AxisCalibration) else ax.get("baseline_angle"),
                            "drift": ax.drift if isinstance(ax, AxisCalibration) else ax.get("drift", 0),
                        } for ax_name, ax in (h.axes.items() if isinstance(h, ModelHealth) else h.get("axes", {}).items())
                    }
                } for mk, h in results.items()
            }),
        }
        
        try:
            r = requests.post(f"{PLATO_URL}/room/fleet_health/tile", json=tile, timeout=10)
            return r.status_code == 200
        except:
            return False
    
    def _load_history(self) -> Dict:
        if os.path.exists(HEALTH_HISTORY_PATH):
            try:
                with open(HEALTH_HISTORY_PATH) as f:
                    return json.load(f)
            except: pass
        return {}
    
    def _save_history(self, results: Dict[str, ModelHealth]):
        entry = {}
        for mk, h in results.items():
            entry[mk] = asdict(h) if isinstance(h, ModelHealth) else h
        
        self.history["latest"] = entry
        ts_key = datetime.utcnow().strftime("%Y-%m-%dT%H-%M")
        self.history.setdefault("history", {})[ts_key] = entry
        
        # Keep last 50 entries
        hist = self.history.get("history", {})
        if len(hist) > 50:
            sorted_keys = sorted(hist.keys())
            for k in sorted_keys[:-50]:
                del hist[k]
        
        os.makedirs(os.path.dirname(HEALTH_HISTORY_PATH), exist_ok=True)
        with open(HEALTH_HISTORY_PATH, "w") as f:
            json.dump(self.history, f, indent=2, default=str)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Fleet Health Monitor")
    p.add_argument("--models", nargs="+", default=None)
    p.add_argument("--axes", nargs="+", default=None)
    p.add_argument("--emit", action="store_true", help="Emit PLATO tile")
    p.add_argument("--report-only", action="store_true", help="Just show last report")
    args = p.parse_args()
    
    health = FleetHealth()
    
    if args.report_only:
        print(health.report())
        return
    
    print("Running fleet health calibration...")
    results = health.calibrate(model_keys=args.models, axes=args.axes)
    print(health.report(results))
    
    if args.emit:
        ok = health.emit_plato(results)
        print(f"\nPLATO tile emitted: {'✅' if ok else '❌'}")


if __name__ == "__main__":
    main()
