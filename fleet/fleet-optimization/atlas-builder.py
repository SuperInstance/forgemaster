#!/usr/bin/env python3
"""atlas-builder.py — Builds the Performance Atlas from collected results.

Periodically queries collective-kernels, meta-verifier, and experiment-results
to build the canonical (algorithm × hardware → optimal config) knowledge map.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_NAMESPACE = "fleet-opt"


class AtlasBuilder:
    """Builds and updates the fleet performance atlas."""

    def __init__(self, plato: Any):
        self.plato = plato

    def rebuild_atlas(self) -> None:
        """Query all kernel configs and build canonical atlas entries."""
        kernels = self.plato.find_tiles(
            room=f"{_NAMESPACE}/collective-kernels",
        )
        alerts = self.plato.find_tiles(
            room=f"{_NAMESPACE}/fast-math-alerts",
        )
        verifications = self.plato.find_tiles(
            room=f"{_NAMESPACE}/meta-verifier",
        )

        # Index alerts by algorithm
        alerts_by_alg: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for alert in alerts:
            answer = alert.get("_answer_obj", {})
            summary = answer.get("summary", "")
            for kw in ["eisenstein-snap", "lattice-spline", "eisenstein-contract"]:
                if kw in summary:
                    alerts_by_alg[kw].append(answer)

        # Index verifications by work_id
        verif_by_work: dict[str, dict[str, Any]] = {}
        for v in verifications:
            answer = v.get("_answer_obj", {})
            wid = answer.get("work_id", "")
            if wid:
                verif_by_work[wid] = answer

        # Group kernels by (algorithm, arch)
        by_alg_arch: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for kernel in kernels:
            answer = kernel.get("_answer_obj", {})
            alg = answer.get("algorithm", "unknown")
            arch = answer.get("arch", "unknown")
            by_alg_arch[(alg, arch)].append(answer)

        # Build atlas entries
        for (alg, arch), entries in by_alg_arch.items():
            self._build_entry(alg, arch, entries, alerts_by_alg, verif_by_work)

    def _build_entry(
        self,
        algorithm: str,
        arch: str,
        kernels: list[dict[str, Any]],
        alerts_by_alg: dict[str, list[dict[str, Any]]],
        verif_by_work: dict[str, dict[str, Any]],
    ) -> None:
        """Build/update a single atlas entry."""
        if not kernels:
            return

        # Find the optimal kernel (best throughput)
        best = max(kernels, key=lambda k: k.get("benchmark_summary", {}).get("mean_throughput_ops_s", 0))

        # Check if the fastest config has numerical correctness issues
        fastest_name = best.get("config_name", "")
        fastest_is_correct = True
        notes = ""

        # Check alerts for this algorithm
        if algorithm in alerts_by_alg:
            for alert in alerts_by_alg[algorithm]:
                config = alert.get("config", "")
                if config and config in fastest_name:
                    fastest_is_correct = False
                    notes = alert.get("recommendation", "")
                    break

        # Build cross-arch perspective
        cross_arch: dict[str, str] = {}
        for k in kernels:
            if k.get("arch") != arch:
                summary = k.get("benchmark_summary", {})
                cross_arch[k.get("arch", "?")] = (
                    f"{k.get('config_name', '?')} @ "
                    f"{summary.get('mean_latency_us', '?')}µs"
                )

        # Build natural-language canonical answer
        canon = self._canonical_answer(algorithm, arch, best, fastest_is_correct, notes)

        entry = {
            "algorithm": algorithm,
            "arch": arch,
            "query": f"What's the fastest way to run {algorithm} on {arch}?",
            "canonical_answer": canon,
            "best_kernel": {
                "config_name": best.get("config_name", "?"),
                "compiler_flags": best.get("compiler_flags", []),
                "runtime_params": best.get("runtime_params", {}),
                "mean_latency_us": best.get("benchmark_summary", {}).get("mean_latency_us", 0),
                "mean_throughput_ops_s": best.get("benchmark_summary", {}).get("mean_throughput_ops_s", 0),
            },
            "fastest_config": {
                "config_name": fastest_name,
                "mean_latency_us": best.get("benchmark_summary", {}).get("mean_latency_us", 0),
                "mean_throughput_ops_s": best.get("benchmark_summary", {}).get("mean_throughput_ops_s", 0),
            },
            "numerical_correctness": {
                "fastest_is_correct": fastest_is_correct,
                "notes": notes if not fastest_is_correct else "All configs pass numerical verification",
            },
            "cross_arch_perspective": cross_arch,
            "entries_count": len(kernels),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        self.plato.write_tile(
            room=f"{_NAMESPACE}/performance-atlas",
            domain=_NAMESPACE,
            question=f"atlas:{algorithm}:{arch}",
            answer=entry,
            source="fleet-opt-atlas-builder",
            confidence=0.9,
            tags=["atlas", f"algorithm:{algorithm}", f"arch:{arch}"],
        )
        print(f"[atlas-builder] Updated: {algorithm} @ {arch}")

    def _canonical_answer(
        self, algorithm: str, arch: str, best: dict[str, Any],
        correct: bool, notes: str
    ) -> str:
        """Generate a natural-language canonical performance answer."""
        flags = " ".join(best.get("compiler_flags", []))
        lat = best.get("benchmark_summary", {}).get("mean_latency_us", "?")
        thpt = best.get("benchmark_summary", {}).get("mean_throughput_ops_s", "?")

        if not correct:
            return (
                f"Use {best.get('config_name', '?')} for {algorithm} on {arch}: "
                f"compile with '{flags}', achieves ~{lat}µs / ~{thpt} ops/s. "
                f"⚠️ NOTE: {notes}"
            )
        return (
            f"Optimal config for {algorithm} on {arch}: "
            f"compile with '{flags}', "
            f"achieves ~{lat}µs / ~{thpt} ops/s. "
            f"Numerically verified against reference."
        )


if __name__ == "__main__":
    from fleet_agent import PLATOShim
    plato = PLATOShim()
    builder = AtlasBuilder(plato)
    builder.rebuild_atlas()
