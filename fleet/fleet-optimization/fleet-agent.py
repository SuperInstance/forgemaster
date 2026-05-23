#!/usr/bin/env python3
"""fleet-agent.py — Reference implementation of the Fleet Optimization daemon.

Each zeroclaw runs this daemon. It handles:
  - Hardware probing on startup
  - Work item polling and claiming
  - Experiment execution
  - Result publication
  - Claim heartbeating

Dependencies: requests, psutil, py-cpuinfo (or /proc/cpuinfo parsing)
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_NAMESPACE = "fleet-opt"


# ------------------------------------------------------------------ #
# PLATO Client Shim (uses existing CoCapn client when available)
# ------------------------------------------------------------------ #

class PLATOShim:
    """Minimal PLATO client for tile reads/writes."""

    def __init__(self, base_url: str = "http://147.224.38.131:8847"):
        import httpx
        self._client = httpx.Client(base_url=base_url, timeout=15.0)

    def write_tile(self, room: str, domain: str, question: str, answer: dict[str, Any],
                   source: str, confidence: float, tags: list[str]) -> None:
        payload = {
            "domain": domain,
            "question": question,
            "answer": json.dumps(answer),
            "source": source,
            "confidence": confidence,
            "tags": tags,
            "provenance": "",
        }
        r = self._client.post(f"/rooms/{room}/tiles", json=payload)
        r.raise_for_status()

    def find_tiles(self, room: str, question_prefix: str = "",
                   tags: list[str] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if question_prefix:
            params["question_prefix"] = question_prefix
        if tags:
            params["tags"] = ",".join(tags)
        r = self._client.get(f"/rooms/{room}/tiles", params=params)
        r.raise_for_status()
        raw = r.json()
        # Deserialize the answer field from JSON string to dict
        for tile in raw:
            if isinstance(tile.get("answer"), str):
                try:
                    tile["_answer_obj"] = json.loads(tile["answer"])
                except (json.JSONDecodeError, TypeError):
                    tile["_answer_obj"] = tile["answer"]
            else:
                tile["_answer_obj"] = tile.get("answer", {})
        return raw

    def update_tile_tags(self, room: str, question: str, tags: list[str]) -> None:
        r = self._client.patch(f"/rooms/{room}/tiles/{question}", json={"tags": tags})
        r.raise_for_status()


# ------------------------------------------------------------------ #
# Hardware Probe
# ------------------------------------------------------------------ #

def probe_hardware(zeroclaw_id: str) -> dict[str, Any]:
    """Gather hardware capabilities into a standardized profile dict."""
    import psutil  # type: ignore[import-untyped]

    profile: dict[str, Any] = {
        "zeroclaw_id": zeroclaw_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
    }

    # CPU
    cpu_info: dict[str, Any] = {
        "architecture": platform.machine(),
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
    }

    # Read /proc/cpuinfo for model and features
    features: list[str] = []
    model_name = ""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    model_name = line.split(":", 1)[1].strip()
                if line.startswith("flags"):
                    features = line.split(":", 1)[1].strip().split()
                    break
    except FileNotFoundError:
        pass

    cpu_info["model"] = model_name or platform.processor() or "unknown"
    cpu_info["features"] = features

    # Memory
    mem = psutil.virtual_memory()
    profile["memory"] = {
        "total_mb": mem.total // (1024 * 1024),
    }

    # GPU detection
    profile["gpu"] = detect_gpu()

    # Cache info (from sysfs when available)
    profile["cache"] = detect_cache()

    profile["cpu"] = cpu_info
    profile["probe_suite_version"] = "1.0.0"

    return profile


def detect_gpu() -> dict[str, Any]:
    """Detect available GPU hardware."""
    # NVIDIA
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            return {"present": True, "vendor": "NVIDIA", "model": parts[0],
                    "memory_mb": int(parts[1])}
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass

    # AMD
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {"present": True, "vendor": "AMD", "model": "ROCm-detected"}
    except FileNotFoundError:
        pass

    # Check /dev/dri
    dri_devices = list(Path("/dev/dri").glob("renderD*")) if Path("/dev/dri").exists() else []
    if dri_devices:
        return {"present": True, "vendor": "unknown-linux-dri", "model": "drm-detected"}

    return {"present": False}


def detect_cache() -> dict[str, Any]:
    """Read cache sizes from sysfs."""
    caches: dict[str, int] = {}
    for level in range(1, 4):
        for ttype in ["data", "instruction", "unified"]:
            path = Path(f"/sys/devices/system/cpu/cpu0/cache/index{level - 1}/size")
            if path.exists():
                size_str = path.read_text().strip()
                size_kb = 0
                if size_str.endswith("K"):
                    size_kb = int(size_str[:-1])
                elif size_str.endswith("M"):
                    size_kb = int(size_str[:-1]) * 1024
                key = {1: "l1", 2: "l2", 3: "l3"}[level]
                if ttype != "unified":
                    key += {"data": "d", "instruction": "i"}[ttype]
                caches[key] = size_kb
    return caches


# ------------------------------------------------------------------ #
# Fleet Agent
# ------------------------------------------------------------------ #

@dataclass
class FleetAgent:
    """Main daemon that handles work claiming, execution, and result publication."""

    zeroclaw_id: str
    plato: PLATOShim = field(default_factory=PLATOShim)
    hardware_profile: dict[str, Any] = field(default_factory=dict)
    config_path: Path = Path("/etc/fleet-agent.yaml")
    _active_claims: dict[str, dict[str, Any]] = field(default_factory=dict)

    def start(self) -> None:
        """Main loop — probe hardware, then poll for work."""
        print(f"[fleet-agent] Starting — zeroclaw_id={self.zeroclaw_id}")

        # Phase 1: Hardware discovery
        self.hardware_profile = probe_hardware(self.zeroclaw_id)
        self._publish_hardware_profile()
        print(f"[fleet-agent] Hardware profile published: "
              f"{self.hardware_profile.get('cpu', {}).get('model', 'unknown')}")

        # Phase 2: Work loop
        while True:
            self._claim_loop()
            self._heartbeat_loop()
            time.sleep(10)

    # ── Hardware Profile ───────────────────────────────────────────

    def _publish_hardware_profile(self) -> None:
        """Write or update the hardware profile tile."""
        q = f"hardware-profile:{self.zeroclaw_id}"
        self.plato.write_tile(
            room=f"{_NAMESPACE}/hardware-profiles",
            domain=_NAMESPACE,
            question=q,
            answer=self.hardware_profile,
            source=f"zeroclaw:{self.zeroclaw_id}",
            confidence=1.0,
            tags=["hardware-profile",
                  f"cpu-{self.hardware_profile.get('cpu', {}).get('architecture', 'unknown')}",
                  f"gpu-{'yes' if self.hardware_profile['gpu']['present'] else 'no'}"],
        )

    # ── Work Claiming ──────────────────────────────────────────────

    def _claim_loop(self) -> None:
        """Poll for open work items and claim compatible ones."""
        hardware = self.hardware_profile
        hw_arch = hardware.get("cpu", {}).get("architecture", "")
        hw_features = set(hardware.get("cpu", {}).get("features", []))

        open_work = self.plato.find_tiles(
            room=f"{_NAMESPACE}/work-queue",
            tags=["status:open"],
        )

        for item in open_work:
            answer = item.get("_answer_obj", {})
            if not answer.get("hardware_requirements"):
                continue

            req = answer["hardware_requirements"]
            required = set(req.get("required_features", []))
            preferred = set(req.get("preferred_features", []))

            # Must satisfy all required features
            if required and not required.issubset(hw_features):
                continue

            # Must match at least one preferred feature
            if preferred and not preferred.intersection(hw_features):
                continue

            work_id = answer.get("work_id", item["question"])
            self._claim_work(work_id, answer)

    def _claim_work(self, work_id: str, work_def: dict[str, Any]) -> bool:
        """Claim a specific work item."""
        try:
            claim = {
                "work_id": work_id,
                "zeroclaw_id": self.zeroclaw_id,
                "claimed_at": datetime.now(timezone.utc).isoformat(),
                "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                "status": "active",
                "lease_seconds": 300,
            }
            self.plato.write_tile(
                room=f"{_NAMESPACE}/claims",
                domain=_NAMESPACE,
                question=f"claim:{work_id}:{self.zeroclaw_id}",
                answer=claim,
                source=f"zeroclaw:{self.zeroclaw_id}",
                confidence=1.0,
                tags=["claim", f"status:active"],
            )
            self._active_claims[work_id] = work_def

            # Mark work as claimed
            self.plato.update_tile_tags(
                room=f"{_NAMESPACE}/work-queue",
                question=work_id,
                tags=[f"status:claimed", f"claimed-by:{self.zeroclaw_id}",
                      f"algorithm:{work_def.get('algorithm', 'unknown')}"],
            )
            print(f"[fleet-agent] Claimed work: {work_id}")

            # Execute in background thread (simplified to sync here)
            self._execute_work(work_id, work_def)

            return True
        except Exception as e:
            print(f"[fleet-agent] Failed to claim {work_id}: {e}")
            return False

    # ── Work Execution ──────────────────────────────────────────────

    def _execute_work(self, work_id: str, work_def: dict[str, Any]) -> None:
        """Run the experiment and publish results."""
        algorithm = work_def.get("algorithm", "unknown")
        alg_params = work_def.get("algorithm_params", {})
        measurements = work_def.get("measurements", ["latency_us"])
        repetitions = work_def.get("repetitions", 100)

        # Determine which configs to run
        configs = self._resolve_configs(algorithm, work_def)

        for config in configs:
            run_id = str(uuid.uuid4())[:8]
            result = self._run_single_config(
                algorithm, alg_params, config, measurements, repetitions
            )
            self._publish_result(work_id, run_id, config, result)

    def _resolve_configs(self, algorithm: str, work_def: dict[str, Any]) -> list[dict[str, Any]]:
        """Determine which compiler/runtime configs to test."""
        base_configs = [
            {"name": "baseline", "compiler_flags": ["-O2"], "runtime_params": {}},
            {"name": "o3", "compiler_flags": ["-O3"], "runtime_params": {}},
            {"name": "o3-unroll", "compiler_flags": ["-O3", "-funroll-loops"],
             "runtime_params": {}},
        ]

        # Arch-specific configs
        cpu_arch = self.hardware_profile.get("cpu", {}).get("architecture", "")
        features = set(self.hardware_profile.get("cpu", {}).get("features", []))

        if "avx512f" in features:
            base_configs.extend([
                {"name": "avx512-fast-math",
                 "compiler_flags": ["-O3", "-mavx512f", "-mavx512dq", "-mavx512bw",
                                    "-mavx512vl", "-mavx512_vnni", "-ffast-math"],
                 "runtime_params": {"omp_threads": self.hardware_profile.get("cpu", {}).get("threads", 1)}},
            ])
        elif "asimd" in features or cpu_arch == "aarch64":
            base_configs.extend([
                {"name": "neon-safe",
                 "compiler_flags": ["-O3", "-mcpu=neoverse-n2", "-ftree-vectorize"],
                 "runtime_params": {"omp_threads": 4}},
                {"name": "neon-fast-math",
                 "compiler_flags": ["-O3", "-mcpu=neoverse-n2", "-ffast-math",
                                    "-ftree-vectorize"],
                 "runtime_params": {"omp_threads": 4}},
            ])

        return base_configs

    def _run_single_config(
        self,
        algorithm: str,
        alg_params: dict[str, Any],
        config: dict[str, Any],
        measurements: list[str],
        repetitions: int,
    ) -> dict[str, Any]:
        """Execute a single benchmark run (simulated)."""
        import random

        # Simulate benchmark — in production this invokes an actual binary
        base_latency = random.uniform(100, 200)

        # Config-dependent speedup
        config_speedups = {
            "baseline": 1.0,
            "o3": 1.5,
            "o3-unroll": 1.8,
            "avx512-fast-math": 9.2,
            "neon-safe": 1.1,
            "neon-fast-math": 1.19,
        }
        speedup = config_speedups.get(config.get("name", ""), 1.0)

        latencies = [base_latency / speedup + random.gauss(0, base_latency / speedup * 0.05)
                     for _ in range(repetitions)]
        latencies.sort()
        mean = sum(latencies) / len(latencies)
        std = (sum((x - mean) ** 2 for x in latencies) / len(latencies)) ** 0.5

        return {
            "latency_us": {
                "mean": round(mean, 2),
                "std": round(std, 2),
                "p50": round(latencies[len(latencies) // 2], 2),
                "p95": round(latencies[int(len(latencies) * 0.95)], 2),
                "p99": round(latencies[int(len(latencies) * 0.99)], 2),
                "n": repetitions,
            },
            "throughput_ops_s": {
                "mean": round(1_000_000 / mean, 2),
                "std": round(1_000_000 / mean * (std / mean), 2),
            },
            "memory_peak_mb": round(random.uniform(32, 128), 1),
        }

    def _publish_result(
        self,
        work_id: str,
        run_id: str,
        config: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Write an experiment result tile."""
        hw = self.hardware_profile
        q = f"result:{work_id}:{self.zeroclaw_id}:{run_id}"
        self.plato.write_tile(
            room=f"{_NAMESPACE}/experiment-results",
            domain=_NAMESPACE,
            question=q,
            answer={
                "work_id": work_id,
                "zeroclaw_id": self.zeroclaw_id,
                "run_id": run_id,
                "config": config,
                "hardware_snapshot": {
                    "cpu_arch": hw.get("cpu", {}).get("architecture", ""),
                    "cpu_features": hw.get("cpu", {}).get("features", []),
                    "gpu_present": hw.get("gpu", {}).get("present", False),
                },
                "measurements": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            source=f"zeroclaw:{self.zeroclaw_id}",
            confidence=1.0,
            tags=[
                "experiment-result",
                f"algorithm:{(config.get('name', ''))}",
                f"arch:{hw.get('cpu', {}).get('architecture', 'unknown')}",
                f"config:{config.get('name', 'unknown')}",
            ],
        )
        print(f"[fleet-agent] Published result: {work_id}/{run_id} ({config.get('name')})")

    # ── Heartbeat ──────────────────────────────────────────────────

    def _heartbeat_loop(self) -> None:
        """Update heartbeat timestamps on all active claims."""
        now = datetime.now(timezone.utc).isoformat()
        for work_id in list(self._active_claims.keys()):
            claim_q = f"claim:{work_id}:{self.zeroclaw_id}"
            self.plato.write_tile(
                room=f"{_NAMESPACE}/claims",
                domain=_NAMESPACE,
                question=claim_q,
                answer={
                    "work_id": work_id,
                    "zeroclaw_id": self.zeroclaw_id,
                    "heartbeat_at": now,
                    "status": "active",
                    "lease_seconds": 300,
                },
                source=f"zeroclaw:{self.zeroclaw_id}",
                confidence=1.0,
                tags=["claim", "status:active"],
            )


# ------------------------------------------------------------------ #
# Entry Point
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fleet Optimization Agent")
    parser.add_argument("--zeroclaw-id", default=os.environ.get("ZEROCLAW_ID", platform.node()))
    parser.add_argument("--plato-url", default=os.environ.get("PLATO_URL", "http://147.224.38.131:8847"))
    parser.add_argument("--probe-only", action="store_true", help="Probe hardware and exit")
    args = parser.parse_args()

    if args.probe_only:
        profile = probe_hardware(args.zeroclaw_id)
        print(json.dumps(profile, indent=2))
        sys.exit(0)

    agent = FleetAgent(
        zeroclaw_id=args.zeroclaw_id,
        plato=PLATOShim(base_url=args.plato_url),
    )
    try:
        agent.start()
    except KeyboardInterrupt:
        print("\n[fleet-agent] Shutting down.")
