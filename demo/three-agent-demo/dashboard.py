"""Terminal dashboard showing fleet state."""

import sys
from typing import Dict, Any


class Dashboard:
    """Print-based fleet dashboard (no curses dependency)."""

    def __init__(self):
        self.history: list[dict] = []

    def render(
        self,
        tick: int,
        agents: dict,
        cadence_caller: str,
        violations: list[str],
        max_drift: float,
        holonomy: dict,
    ):
        """Render dashboard frame to terminal."""
        # Store snapshot
        snapshot = {
            "tick": tick,
            "cadence_caller": cadence_caller,
            "max_drift": max_drift,
            "violations": len(violations),
            "holonomy": holonomy,
        }
        self.history.append(snapshot)

        # Only print every 10 ticks for readability
        if tick % 10 != 0 and tick > 0:
            return

        caller_str = cadence_caller
        drift_str = f"{max_drift:.6f}"
        viol_str = f"{len(violations)} violations" if violations else "clean"

        parts = [f"[TICK {tick:04d}]"]
        parts.append(f"Caller: {caller_str}")
        parts.append(f"Max drift: {drift_str}")
        parts.append(f"| {viol_str}")

        if holonomy:
            h_ok = "✓" if holonomy.get("holonomy_ok") else "✗"
            l_ok = "✓" if holonomy.get("laman_ok") else "✗"
            parts.append(f"| Holonomy:{h_ok} Laman:{l_ok}")

        line = " ".join(parts)
        print(line)

        # Show individual agent drift
        for agent_id, agent in agents.items():
            if hasattr(agent, "metronome"):
                drift = agent.metronome.clock.drift_float
                tick_count = agent.metronome.tick_count
                print(f"  {agent_id:15s} | drift: {drift:+.6f} | tick: {tick_count}")

        # Show violations
        for v in violations[:3]:
            print(f"  ⚠ VIOLATION: {v}")
        if len(violations) > 3:
            print(f"  ... and {len(violations) - 3} more")

    def summary(self):
        """Print final summary."""
        if not self.history:
            print("No history recorded.")
            return

        max_drift = max(h["max_drift"] for h in self.history)
        total_violations = sum(h["violations"] for h in self.history)
        ticks = len(self.history)

        print(f"\n{'='*60}")
        print(f"DASHBOARD SUMMARY")
        print(f"{'='*60}")
        print(f"Ticks simulated:    {ticks}")
        print(f"Max drift ever:     {max_drift:.6f}")
        print(f"Total violations:   {total_violations}")
        print(f"{'='*60}")
