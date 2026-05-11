#!/usr/bin/env python3
"""
snapkit — Command-Line Interface
=================================

Usage:
    snapkit monitor --streams 5 --budget 100 --topology hexagonal
    snapkit analyze results.json --html report.html
    snapkit demo poker --hands 1000
    snapkit demo learning --experiences 10000
"""

import argparse
import sys
import numpy as np
import json
import time
from typing import List, Optional, Dict, Any

from snapkit import (
    SnapFunction, SnapTopologyType, DeltaDetector, AttentionBudget,
    LearningCycle, ScriptLibrary, Script,
)
from snapkit.serial import load, save
from snapkit.visualization import terminal_table, ascii_chart, html_report, format_results
from snapkit.streaming import StreamProcessor, StreamConfig, StreamMonitor
from snapkit.pipeline import PipelineBuilder, LearningPipeline, MonitoringPipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog='snapkit',
        description='Tolerance-Compressed Attention Allocation Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  snapkit monitor --streams 5 --budget 100
  snapkit analyze results.json --html report.html
  snapkit demo poker --hands 100
  snapkit demo learning --experiences 500
  snapkit calibrate data.csv --target-rate 0.9
        """,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # monitor
    monitor_parser = subparsers.add_parser(
        'monitor',
        help='Monitor streams in real-time',
    )
    monitor_parser.add_argument('--streams', type=int, default=3,
                                help='Number of streams to monitor')
    monitor_parser.add_argument('--budget', type=float, default=100.0,
                                help='Total attention budget')
    monitor_parser.add_argument('--topology', type=str, default='hexagonal',
                                choices=[t.value for t in SnapTopologyType],
                                help='Snap topology type')
    monitor_parser.add_argument('--tolerance', type=float, default=0.1,
                                help='Initial snap tolerance')
    monitor_parser.add_argument('--steps', type=int, default=50,
                                help='Number of monitoring steps')
    monitor_parser.add_argument('--interval', type=float, default=0.1,
                                help='Interval between steps (seconds)')
    
    # analyze
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze snap results from a file',
    )
    analyze_parser.add_argument('input', type=str,
                                help='Input JSON file with snap results')
    analyze_parser.add_argument('--html', type=str,
                                help='Output HTML report path')
    analyze_parser.add_argument('--json', type=str,
                                help='Output analyzed JSON path')
    
    # demo
    demo_parser = subparsers.add_parser(
        'demo',
        help='Run demonstrations',
    )
    demo_parser.add_argument('demo_type', type=str,
                             choices=['poker', 'learning', 'adversarial'],
                             help='Type of demo')
    demo_parser.add_argument('--hands', type=int, default=100,
                             help='Number of poker hands (poker demo)')
    demo_parser.add_argument('--experiences', type=int, default=1000,
                             help='Number of experiences (learning demo)')
    
    # calibrate
    cal_parser = subparsers.add_parser(
        'calibrate',
        help='Calibrate snap tolerance from data',
    )
    cal_parser.add_argument('datafile', type=str,
                            help='JSON file with data array')
    cal_parser.add_argument('--target-rate', type=float, default=0.9,
                            help='Target snap rate')
    cal_parser.add_argument('--topology', type=str, default='hexagonal',
                            choices=[t.value for t in SnapTopologyType],
                            help='Snap topology')
    cal_parser.add_argument('--output', type=str,
                            help='Output calibrated config (JSON)')
    
    # status
    status_parser = subparsers.add_parser(
        'status',
        help='Show snapkit version and system info',
    )
    
    return parser


def cmd_monitor(args: argparse.Namespace):
    """Run the monitor command."""
    # Create streams with different noise characteristics
    stream_ids = [f'stream_{i}' for i in range(args.streams)]
    
    configs = [
        StreamConfig(
            stream_id=sid,
            tolerance=args.tolerance * (1.0 + i * 0.2),
            topology=SnapTopologyType(args.topology),
        )
        for i, sid in enumerate(stream_ids)
    ]
    
    monitor = StreamMonitor(total_budget=args.budget)
    for config in configs:
        snap = SnapFunction(tolerance=config.tolerance, topology=config.topology)
        monitor.add_stream(config.stream_id, snap=snap, weight=1.0)
    
    print(f"Monitoring {args.streams} streams (budget={args.budget:.1f})")
    print(f"Topology: {args.topology}, Tolerance: {args.tolerance}")
    print()
    
    for step in range(args.steps):
        # Generate random values
        for sid in stream_ids:
            value = float(np.random.randn() * 0.3)
            monitor.observe(sid, value)
        
        # Show dashboard every 10 steps
        if step % 10 == 0:
            stats = monitor.statistics
            rows = []
            for sid, s in stats.get('per_stream', {}).items():
                rows.append([
                    sid,
                    str(s.get('obs_count', 0)),
                    str(s.get('delta_count', 0)),
                    f"{s.get('delta_count', 0) / max(s.get('obs_count', 1), 1):.0%}",
                ])
            
            table = terminal_table(
                ['Stream', 'Obs', 'Deltas', 'Rate'],
                rows,
                title=f"Step {step + 1}/{args.steps} (Util: {monitor.utilization:.0%})",
                color_column=3,
            )
            print(table)
            
            alerts = monitor.check_alerts()
            for alert in alerts:
                print(f"  ALERT: {alert.message}")
        
        if args.interval > 0:
            time.sleep(args.interval)
    
    print(f"\nFinal utilization: {monitor.utilization:.1%}")


def cmd_analyze(args: argparse.Namespace):
    """Run the analyze command."""
    data = load(args.input)
    
    if not isinstance(data, dict):
        print(f"Error: Expected dict from {args.input}, got {type(data)}")
        sys.exit(1)
    
    if args.html:
        html = html_report(data, title=f"SnapKit Analysis: {args.input}")
        with open(args.html, 'w') as f:
            f.write(html)
        print(f"HTML report written to {args.html}")
    
    if args.json:
        save(data, args.json)
        print(f"JSON output written to {args.json}")
    
    # Show summary
    print("\nAnalysis Summary:")
    print("=" * 50)
    for key, value in data.items():
        if key == 'per_stream':
            continue
        print(f"  {key}: {value}")


def cmd_demo_poker(hands: int):
    """Poker demo: simulate snap-attention processing of poker hands."""
    print(f"\n--- Poker Snap Demo ({hands} hands) ---\n")
    
    # Multi-stream detector
    detector = DeltaDetector()
    
    # Card probability stream (uniform randomness)
    detector.add_stream(
        'cards',
        SnapFunction(tolerance=0.1, topology=SnapTopologyType.UNIFORM),
        actionability_fn=lambda v: 0.3,  # Low actionability — cards are random
    )
    
    # Player behavior stream (categorical randomness)
    detector.add_stream(
        'behavior',
        SnapFunction(tolerance=0.05, topology=SnapTopologyType.CATEGORICAL),
        actionability_fn=lambda v: 0.8,  # High actionability — can read behavior
    )
    
    # Betting pattern stream (directional)
    detector.add_stream(
        'betting',
        SnapFunction(tolerance=0.15, topology=SnapTopologyType.OCTAHEDRAL),
        urgency_fn=lambda v: 0.7,  # Betting is urgent
    )
    
    # Emotional tells stream (combinatorial)
    detector.add_stream(
        'emotion',
        SnapFunction(tolerance=0.08, topology=SnapTopologyType.HEXAGONAL),
        actionability_fn=lambda v: 0.6,
        urgency_fn=lambda v: 0.5,
    )
    
    budget = AttentionBudget(total=100.0, strategy='actionability')
    
    snap_total = 0
    delta_total = 0
    
    for hand in range(hands):
        # Generate simulated observations
        obs = {
            'cards': float(np.random.random()),       # Card strength [0..1]
            'behavior': float(np.random.random()),      # Behavior deviation
            'betting': float(np.random.random()),       # Aggression level
            'emotion': float(np.random.random()),       # Emotion noise
        }
        
        deltas = detector.observe(obs)
        prioritized = detector.prioritize(top_k=3)
        budget.allocate(prioritized)
        
        # Count snaps vs deltas
        for sid, delta in deltas.items():
            if delta.exceeds_tolerance:
                delta_total += 1
            else:
                snap_total += 1
    
    total = snap_total + delta_total
    print(f"  Hands processed: {hands}")
    print(f"  Streams monitored: 4 (cards, behavior, betting, emotion)")
    print(f"  Snaps: {snap_total} ({snap_total / max(total, 1):.1%})")
    print(f"  Deltas: {delta_total} ({delta_total / max(total, 1):.1%})")
    print(f"  Budget strategy: actionability")
    print(f"  Budget exhaustion rate: {budget.exhaustion_rate:.1%}")
    
    # Show per-stream stats
    print("\n  Per-stream stats:")
    for sid, s in detector._streams.items():
        stats = s.statistics
        print(f"    {sid:10s}: tolerance={stats['tolerance']:.3f}, "
              f"delta_rate={stats['delta_rate']:.0%}")


def cmd_demo_learning(experiences: int):
    """Learning demo: show the expertise cycle."""
    print(f"\n--- Learning Cycle Demo ({experiences} experiences) ---\n")
    
    learner = LearningPipeline(tolerance=0.1)
    
    # Phase 1: Novelty (DELTA_FLOOD)
    print("Phase 1: Novelty...")
    for i in range(min(experiences // 4, 50)):
        learner.process(float(np.random.randn() * 2.0))
    
    print(f"  Phase reached: {learner.current_phase.value if learner.current_phase else 'N/A'}")
    print(f"  Scripts: {learner.statistics.get('scripts_active', 0)}")
    
    # Phase 2: Pattern emergence (SCRIPT_BURST)
    print("\nPhase 2: Patterns emerging...")
    for i in range(min(experiences // 4, 100)):
        learner.process(float(np.random.randn() * 0.5 + 0.5))
    
    print(f"  Phase reached: {learner.current_phase.value if learner.current_phase else 'N/A'}")
    print(f"  Scripts: {learner.statistics.get('scripts_active', 0)}")
    
    # Phase 3: Smooth running
    print("\nPhase 3: Automation...")
    for i in range(min(experiences // 2, 200)):
        learner.process(float(np.random.randn() * 0.3))
    
    print(f"  Phase reached: {learner.current_phase.value if learner.current_phase else 'N/A'}")
    print(f"  Scripts: {learner.statistics.get('scripts_active', 0)}")
    print(f"  Cognitive load: {learner.statistics.get('cognitive_load', 0):.2f}")
    
    # Phase 4: Disruption
    print("\nPhase 4: Disruption (novel pattern introduced)...")
    for i in range(50):
        learner.process(float(np.random.randn() * 3.0))  # Much larger variance
    
    print(f"  Phase reached: {learner.current_phase.value if learner.current_phase else 'N/A'}")
    print(f"  Phase history: {[p.value for p in learner.phase_history[:5]]}...")


def cmd_demo_adversarial():
    """Adversarial demo: demonstrate fake delta detection."""
    print("\n--- Adversarial Snap Demo ---\n")
    
    from snapkit.adversarial import (
        FakeDeltaGenerator, AdversarialDetector, 
        DeceptionLevel, BluffCalibration
    )
    
    # Create adversary and detector
    adversary = FakeDeltaGenerator(
        style="loose_aggressive",
        deception_level=DeceptionLevel.BLUFF,
    )
    
    detector = AdversarialDetector(detection_threshold=0.7)
    detector.learn_source_profile(
        "loose_aggressive",
        real_signal_rate=0.4,
        fake_signal_rate=0.4,
        deception_level=DeceptionLevel.BLUFF,
    )
    
    calibrator = BluffCalibration(max_depth=5)
    calibrator.model_adversary("loose_aggressive", estimated_level=1)
    
    # Simulate rounds
    print("Playing bluff detection rounds...")
    true_positives = 0
    false_positives = 0
    total_real = 0
    total_fake = 0
    
    for round_num in range(20):
        # Sometimes real, sometimes fake
        is_real = np.random.random() > 0.3
        
        if is_real:
            # Real delta
            source = "loose_aggressive"
            value = float(np.random.normal(0.5, 0.2))
            magnitude = float(np.abs(np.random.normal(1.0, 0.3)))
            result = detector.observe_signal(source, value, magnitude, known_classification=True)
            total_real += 1
        else:
            # Fake delta
            fake = adversary.generate(target_tolerance=0.1)
            result = detector.observe_signal(
                fake.generated_by, fake.value, fake.magnitude, known_classification=False
            )
            total_fake += 1
            
            if result['classified_as_fake']:
                true_positives += 1
            else:
                false_positives += 1
        
        # Update calibrator
        calibrator.record_round(
            my_bluffed=not is_real,
            adversary_called=result['classified_as_fake'],
            adversary_id="loose_aggressive",
        )
    
    print(f"  Total real signals: {total_real}")
    print(f"  Total fake signals: {total_fake}")
    print(f"  True positives (detected fakes): {true_positives}")
    print(f"  False positives (real classified as fake): {false_positives}")
    print(f"  Detector precision: {detector.precision:.2f}")
    print(f"  Detector recall: {detector.recall:.2f}")
    
    # Show bluff calibration
    response = calibrator.optimize_response(
        my_level=2, adversary_id="loose_aggressive"
    )
    print(f"\n  Optimal response: {response['strategy_name']}")
    print(f"  Reasoning: {response['reasoning']}")


def cmd_demo(args: argparse.Namespace):
    """Run demos."""
    if args.demo_type == 'poker':
        cmd_demo_poker(args.hands)
    elif args.demo_type == 'learning':
        cmd_demo_learning(args.experiences)
    elif args.demo_type == 'adversarial':
        cmd_demo_adversarial()
    else:
        print(f"Unknown demo: {args.demo_type}")


def cmd_calibrate(args: argparse.Namespace):
    """Calibrate snap tolerance from data."""
    data = load(args.datafile)
    
    if isinstance(data, list):
        values = [float(v) for v in data]
    elif isinstance(data, dict) and 'data' in data:
        values = [float(v) for v in data['data']]
    else:
        print(f"Error: Cannot extract data list from {args.datafile}")
        sys.exit(1)
    
    if not values:
        print("Error: Empty data list")
        sys.exit(1)
    
    topology = SnapTopologyType(args.topology)
    snap = SnapFunction(tolerance=0.1, topology=topology)
    snap.calibrate(values, target_snap_rate=args.target_rate)
    
    print(f"Calibrated snap function:")
    print(f"  Topology: {args.topology}")
    print(f"  Tolerance: {snap.tolerance:.4f}")
    print(f"  Baseline: {snap.baseline:.4f}")
    print(f"  Target snap rate: {args.target_rate:.0%}")
    print(f"  Actual snap rate (on data): {snap.snap_rate:.1%}")
    
    if args.output:
        config = {
            '__snapkit_serialized__': True,
            '__version__': "1.0.0",
            'calibration': {
                'data_source': args.datafile,
                'num_samples': len(values),
                'tolerance': snap.tolerance,
                'baseline': snap.baseline,
                'topology': args.topology,
                'target_snap_rate': args.target_rate,
                'actual_snap_rate': snap.snap_rate,
            }
        }
        save(config, args.output)
        print(f"  Config written to: {args.output}")


def cmd_status():
    """Show snapkit version and system info."""
    from snapkit import __version__
    import numpy as np
    
    print(f"snapkit v{__version__}")
    print(f"  Python: {sys.version}")
    print(f"  NumPy: {np.__version__}")
    print()
    print("Available modules:")
    print("  snap.py         — SnapFunction (core)")
    print("  delta.py        — DeltaDetector")
    print("  attention.py    — AttentionBudget")
    print("  scripts.py      — ScriptLibrary")
    print("  learning.py     — LearningCycle")
    print("  topology.py     — SnapTopology (ADE)")
    print("  cohomology.py   — ConstraintSheaf")
    print("  adversarial.py  — Adversarial Snap")
    print("  crossdomain.py  — Cross-Domain Transfer")
    print("  streaming.py    — Stream Processing")
    print("  visualization.py — Terminal/HTML Viz")
    print("  integration.py  — PySheaf/SymPy/Numpy")
    print("  serial.py       — Serialization")
    print("  pipeline.py     — Composable Pipelines")
    print("  cli.py          — Command-Line Interface")


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()
    
    if args.command == 'monitor':
        cmd_monitor(args)
    elif args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'demo':
        cmd_demo(args)
    elif args.command == 'calibrate':
        cmd_calibrate(args)
    elif args.command == 'status':
        cmd_status()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
