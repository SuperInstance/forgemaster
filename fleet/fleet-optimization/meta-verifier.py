#!/usr/bin/env python3
"""meta-verifier.py — Fleet-wide result consistency checker.

Runs as a cron/event-driven service on Oracle1.
Watches experiment-result tiles, cross-references across hardware,
and publishes verification tiles + fast-math alerts.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_NAMESPACE = "fleet-opt"


class MetaVerifier:
    """Cross-machine consistency checker for experiment results."""

    def __init__(self, plato: Any):
        self.plato = plato

    def run_once(self) -> None:
        """Scan recent results and verify cross-architecture consistency."""
        results = self._gather_unverified_results()
        by_work_config = self._group_by_work_and_config(results)

        for (work_id, config_name), group in by_work_config.items():
            if len(group) < 2:
                continue  # need at least 2 machines for cross-arch verification
            self._verify_consistency(work_id, config_name, group)

        self._check_expired_claims()

    def _gather_unverified_results(self) -> list[dict[str, Any]]:
        """Find experiment results that haven't been verified yet."""
        # In production, track last-checked-id. Simplified: check all recent.
        return self.plato.find_tiles(
            room=f"{_NAMESPACE}/experiment-results",
            tags=["experiment-result"],
        )

    def _group_by_work_and_config(
        self, results: list[dict[str, Any]]
    ) -> dict[tuple[str, str], list[dict[str, Any]]]:
        """Group results by (work_id, config_name)."""
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for tile in results:
            answer = tile.get("_answer_obj", {})
            work_id = answer.get("work_id", "unknown")
            config = answer.get("config", {})
            config_name = config.get("name", "unknown")
            groups[(work_id, config_name)].append(tile)
        return dict(groups)

    def _verify_consistency(
        self, work_id: str, config_name: str, tiles: list[dict[str, Any]]
    ) -> None:
        """Compare results across hardware and flag anomalies."""
        entries = []
        for tile in tiles:
            answer = tile.get("_answer_obj", {})
            meas = answer.get("measurements", {})
            lat = meas.get("latency_us", {})
            hw = answer.get("hardware_snapshot", {})
            arch = hw.get("cpu_arch", "unknown")
            features = ",".join(hw.get("cpu_features", []))
            entries.append({
                "zeroclaw_id": answer.get("zeroclaw_id", "?"),
                "arch": arch,
                "features": features,
                "latency_us_mean": lat.get("mean", 0),
                "throughput": meas.get("throughput_ops_s", {}).get("mean", 0),
            })

        if len(entries) < 2:
            return

        # Find baseline (first x86_64 entry, or first entry)
        baseline = next((e for e in entries if "x86" in e["arch"]), entries[0])
        tolerance_pct = 5.0

        anomalies = []
        max_dev = 0.0
        for entry in entries:
            if entry["zeroclaw_id"] == baseline["zeroclaw_id"]:
                continue
            # Simple comparison: latency
            if baseline["latency_us_mean"] > 0:
                dev = abs(entry["latency_us_mean"] - baseline["latency_us_mean"]) / \
                      baseline["latency_us_mean"] * 100
                max_dev = max(max_dev, dev)
                if dev > tolerance_pct:
                    anomalies.append({
                        "metric": "latency_us_mean",
                        "baseline_value": baseline["latency_us_mean"],
                        "actual_value": entry["latency_us_mean"],
                        "deviation_pct": round(dev, 1),
                        "baseline_arch": baseline["arch"],
                        "deviant_arch": entry["arch"],
                        "likely_cause": "Architecture-dependent optimization effect",
                    })

        status = "passed"
        if anomalies:
            status = "inconsistent"

        # Check if fast-math is involved
        is_fast_math = "fast-math" in config_name or "ffast-math" in config_name

        verification_tile = {
            "work_id": work_id,
            "config_variant": config_name,
            "num_results": len(entries),
            "hardware_entries": entries,
            "architecture_span": list(set(e["arch"] for e in entries)),
            "verification": {
                "method": "cross-architecture-latency",
                "acceptable_tolerance_pct": tolerance_pct,
                "max_deviation_pct": round(max_dev, 1),
                "status": status,
                "flagged_anomalies": anomalies,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.plato.write_tile(
            room=f"{_NAMESPACE}/meta-verifier",
            domain=_NAMESPACE,
            question=f"verify:{work_id}:{config_name}",
            answer=verification_tile,
            source="meta-verifier",
            confidence=0.95,
            tags=["meta-verification", f"status:{status}"],
        )

        # If fast-math caused inconsistency, publish an alert
        if is_fast_math and anomalies:
            self._publish_fast_math_alert(work_id, config_name, verification_tile)

    def _publish_fast_math_alert(
        self, work_id: str, config_name: str, verif: dict[str, Any]
    ) -> None:
        """Publish a fast-math alert for human review."""
        entries = verif["hardware_entries"]
        # Find x86_64 and ARM entries
        x86_entry = next((e for e in entries if "x86" in e["arch"]), entries[0])
        arm_entry = next((e for e in entries if "aarch64" in e["arch"]), None)
        if not arm_entry:
            return

        alert = {
            "work_id": work_id,
            "config": config_name,
            "severity": "critical",
            "summary": (
                f"fast-math gives {x86_entry['latency_us_mean']:.1f}µs on "
                f"{x86_entry['arch']} but {arm_entry['latency_us_mean']:.1f}µs on "
                f"{arm_entry['arch']} — disparity of "
                f"{verif['verification']['max_deviation_pct']}%"
            ),
            "x86_64_entry": x86_entry,
            "arm_entry": arm_entry,
            "recommendation": "Do NOT use -ffast-math on ARM for this algorithm. "
                              "Use architecture-specific configs.",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }

        self.plato.write_tile(
            room=f"{_NAMESPACE}/fast-math-alerts",
            domain=_NAMESPACE,
            question=f"alert:fast-math:{work_id}",
            answer=alert,
            source="meta-verifier",
            confidence=0.95,
            tags=["fast-math-alert", "severity:critical"],
        )

    def _check_expired_claims(self) -> None:
        """Reclaim work items whose claims have expired."""
        claims = self.plato.find_tiles(
            room=f"{_NAMESPACE}/claims",
            tags=["claim", "status:active"],
        )
        now = time.time()
        for claim in claims:
            answer = claim.get("_answer_obj", {})
            heartbeat_str = answer.get("heartbeat_at", "")
            heartbeat_ts = 0
            if heartbeat_str:
                try:
                    heartbeat_ts = datetime.fromisoformat(heartbeat_str).timestamp()
                except ValueError:
                    continue
            lease = answer.get("lease_seconds", 300)
            if now - heartbeat_ts > lease:
                # Expired
                zeroclaw_id = answer.get("zeroclaw_id", "?")
                work_id = answer.get("work_id", claim["question"])
                print(f"[meta-verifier] Expired claim: {work_id} by {zeroclaw_id}")
                self.plato.update_tile_tags(
                    room=f"{_NAMESPACE}/work-queue",
                    question=work_id,
                    tags=["status:open"],
                )
                self.plato.write_tile(
                    room=f"{_NAMESPACE}/claims",
                    domain=_NAMESPACE,
                    question=claim["question"],
                    answer={**answer, "status": "expired"},
                    source="meta-verifier",
                    confidence=1.0,
                    tags=["claim", "status:expired"],
                )


if __name__ == "__main__":
    # Stub — run once and exit; cron-ify for production
    from fleet_agent import PLATOShim
    plato = PLATOShim()
    verifier = MetaVerifier(plato)
    verifier.run_once()
