"""Rich terminal dashboard for fleet clock synchronization."""

from __future__ import annotations

import argparse
import sys
import time
from typing import TextIO

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .charts import bar_chart, heat_map, sparkline
from .simulator import Agent, AgentState, Fleet


def build_agent_table(fleet: Fleet) -> Table:
    """Build a Rich Table showing each agent's status."""
    table = Table(title="⏱ Fleet Clock Sync", show_lines=False, expand=True)
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Drift (μs)", justify="right")
    table.add_column("Offset (ms)", justify="right")
    table.add_column("State", justify="center")
    table.add_column("Trend", no_wrap=True)

    for agent in fleet.agents:
        drift_us = agent.measured_offset * 1e6
        offset_ms = agent.measured_offset * 1000
        state = agent.state.value
        trend = sparkline(agent.history[-60:], 20) if len(agent.history) > 2 else "—"

        state_style = {
            "LOCKED": "bold green",
            "SYNCING": "yellow",
            "HOLDOVER": "magenta",
            "DRIFTING": "bold red",
            "OFFLINE": "dim",
        }.get(state, "white")

        table.add_row(
            agent.name,
            f"{drift_us:+.1f}",
            f"{offset_ms:+.4f}",
            f"[{state_style}]{state}[/]",
            trend,
        )
    return table


def build_drift_panel(fleet: Fleet) -> Panel:
    """Panel showing drift timeline across all agents."""
    lines = []
    for agent in fleet.agents:
        sp = sparkline(agent.history[-80:], 50)
        if sp:
            lines.append(f"[cyan]{agent.name:>12s}[/] │{sp}│")
    content = "\n".join(lines) if lines else "[dim]Waiting for data…[/]"
    return Panel(content, title="📈 Drift Timeline", border_style="blue")


def build_topology_panel(fleet: Fleet) -> Panel:
    """ASCII topology of tight links."""
    edges = fleet.topology_edges()
    if not edges:
        return Panel("[dim]No tight links[/]", title="🔗 Topology", border_style="green")
    lines = []
    n = len(fleet.agents)
    # Simple adjacency display
    for i, j, w in edges[:20]:
        lines.append(f"  {fleet.agents[i].name} ── {fleet.agents[j].name}  ({w:.3f}ms)")
    content = "\n".join(lines)
    return Panel(content, title="🔗 Topology (tight links)", border_style="green")


def build_protocol_panel() -> Panel:
    """Side-by-side protocol comparison."""
    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("Protocol")
    table.add_column("Accuracy")
    table.add_column("Typical Use")
    table.add_row("NTP", "~1-10ms", "Internet time sync")
    table.add_row("PTP (IEEE 1588)", "~1μs", "Datacenter / telecom")
    table.add_row("Chrony", "~100μs", "Linux default, adaptive")
    table.add_row("SyncE", "~1μs", "Carrier-grade PHY sync")
    table.add_row("White Rabbit", "~1ns", "CERN / sub-ns precision")
    return Panel(table, title="📋 Protocol Comparison", border_style="yellow")


def build_latency_panel(fleet: Fleet) -> Panel:
    """Heat map of pairwise latency."""
    matrix = fleet.latency_matrix()
    labels = [a.name for a in fleet.agents]
    hm = heat_map(matrix, row_labels=labels, col_labels=labels)
    return Panel(hm or "[dim]No data[/]", title="🌡 Latency Heat Map (ms)", border_style="red")


# ── Commands ──────────────────────────────────────────────────────────


def cmd_watch(console: Console, fleet: Fleet, refresh: float = 1.0) -> None:
    """Live auto-refreshing dashboard."""
    layout = Layout()
    layout.split_column(
        Layout(name="top", size=3),
        Layout(name="table"),
        Layout(name="drift"),
    )
    layout["top"].update(Panel("[bold]Metronome Dashboard — Fleet Clock Sync[/]", style="blue"))

    with Live(layout, console=console, refresh_per_second=1 / refresh):
        fleet.start()
        try:
            while True:
                layout["table"].update(build_agent_table(fleet))
                layout["drift"].update(build_drift_panel(fleet))
                time.sleep(refresh)
        except KeyboardInterrupt:
            fleet.stop()


def cmd_compare(console: Console, fleet: Fleet) -> None:
    """Show protocol comparison panel."""
    console.print(build_protocol_panel())


def cmd_topology(console: Console, fleet: Fleet) -> None:
    """Show fleet topology and latency heat map."""
    fleet.start()
    time.sleep(2)  # let it collect some data
    console.print(build_topology_panel(fleet))
    console.print()
    console.print(build_latency_panel(fleet))
    fleet.stop()


def cmd_history(console: Console, fleet: Fleet) -> None:
    """Show bar chart of current offsets + drift sparklines."""
    fleet.start()
    time.sleep(2)
    labels = [a.name for a in fleet.agents]
    values = [a.measured_offset for a in fleet.agents]
    console.print(Panel(bar_chart(labels, values), title="📊 Agent Offsets", border_style="magenta"))
    console.print()
    console.print(build_drift_panel(fleet))
    fleet.stop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="metronome-dashboard",
        description="Terminal dashboard for fleet clock synchronization",
    )
    parser.add_argument("command", nargs="?", default="watch",
                        choices=["watch", "compare", "topology", "history"],
                        help="Dashboard command (default: watch)")
    parser.add_argument("-n", "--agents", type=int, default=10,
                        help="Number of simulated agents (default: 10)")
    parser.add_argument("-r", "--refresh", type=float, default=1.0,
                        help="Refresh interval in seconds (default: 1.0)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args(argv)

    console = Console()
    fleet = Fleet.create(n=args.agents, seed=args.seed)

    cmd_map = {
        "watch": cmd_watch,
        "compare": cmd_compare,
        "topology": cmd_topology,
        "history": cmd_history,
    }
    cmd = cmd_map[args.command]
    if args.command == "watch":
        cmd(console, fleet, refresh=args.refresh)
    else:
        cmd(console, fleet)
