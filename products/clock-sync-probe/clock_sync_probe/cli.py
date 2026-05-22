"""Click CLI for clock-sync-probe."""

from __future__ import annotations

import json
import sys
import time

import click

from . import __version__
from .probe import Peer, ProbeConfig, run_probe, benchmark_strategies, rank_results
from .visualize import ascii_timeline, quick_summary


@click.group()
@click.version_option(__version__, prog_name="clock-sync-probe")
def main():
    """Test your network's clock synchronization capability in 30 seconds."""
    pass


@main.command()
@click.option("--peers", "-p", default="", help="Comma-separated host:port pairs")
@click.option("--duration", "-d", default=30.0, type=float, help="Probe duration in seconds")
@click.option("--strategy", "-s", "strategies", default="naive,cristian,ptp,exponential",
              help="Comma-separated strategies to test")
@click.option("--json-out", "-j", default=None, help="Write results to JSON file")
def test(peers: str, duration: float, strategies: str, json_out: str | None):
    """Run a clock sync probe against simulated or real peers."""
    click.echo(f"⏱  Clock Sync Probe — {duration}s test")
    click.echo()

    peer_list = []
    if peers:
        peer_list = [Peer.from_str(p.strip()) for p in peers.split(",") if p.strip()]

    strat_names = [s.strip() for s in strategies.split(",") if s.strip()]

    config = ProbeConfig(
        peers=peer_list,
        duration_s=duration,
        strategies=strat_names,
    )

    click.echo(f"  Peers: {len(peer_list) or 'default (2 simulated)'}")
    click.echo(f"  Strategies: {', '.join(strat_names)}")
    click.echo()

    with click.progressbar(length=100, label="Probing") as bar:
        results = run_probe(config)
        bar.update(100)

    click.echo()
    click.echo(ascii_timeline(results))
    click.echo()

    # Recommendation
    ranked = rank_results(results)
    best = ranked[0]
    click.echo(f"✅ Recommended strategy: {best.strategy}")
    click.echo(f"   Recommended δ (uncertainty): ±{best.delta_ms:.2f}ms")
    click.echo(f"   Estimated convergence: {best.convergence_ticks} ticks")

    if json_out:
        data = []
        for r in results:
            data.append({
                "strategy": r.strategy,
                "residual_offset_ms": r.residual_offset_ms,
                "jitter_ms": r.jitter_ms,
                "delta_ms": r.delta_ms,
                "convergence_ticks": r.convergence_ticks,
                "score": r.score,
                "offsets_sample": r.offsets[:100],
            })
        with open(json_out, "w") as f:
            json.dump(data, f, indent=2)
        click.echo(f"\n📄 Results written to {json_out}")


@main.command()
@click.option("--strategies", "-s", default="naive,cristian,ptp,exponential",
              help="Comma-separated strategies")
@click.option("--ticks", "-t", default=1000, type=int, help="Number of simulation ticks")
def benchmark(strategies: str, ticks: int):
    """Benchmark sync strategies with simulated fleet."""
    click.echo(f"🔬 Benchmark — {ticks} ticks, comparing strategies")
    click.echo()

    strat_names = [s.strip() for s in strategies.split(",") if s.strip()]
    results = benchmark_strategies(strat_names, ticks)

    click.echo(ascii_timeline(results))
    click.echo()

    ranked = rank_results(results)
    click.echo("Results:")
    for i, r in enumerate(ranked, 1):
        click.echo(f"  {i}. {quick_summary(r)}")


@main.command()
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True),
              help="JSON results file from a previous test")
def report(input_file: str):
    """Generate a report from saved test results."""
    with open(input_file) as f:
        data = json.load(f)

    click.echo("📊 Clock Sync Probe Report")
    click.echo("=" * 50)
    click.echo(f"  Source: {input_file}")
    click.echo(f"  Strategies tested: {len(data)}")
    click.echo()

    # Reconstruct SyncResults for display
    from .probe import SyncResult
    results = []
    for d in data:
        results.append(SyncResult(
            strategy=d["strategy"],
            offsets=d.get("offsets_sample", []),
            residual_offset_ms=d["residual_offset_ms"],
            jitter_ms=d["jitter_ms"],
            delta_ms=d["delta_ms"],
            convergence_ticks=d["convergence_ticks"],
        ))

    click.echo(ascii_timeline(results))


if __name__ == "__main__":
    main()
