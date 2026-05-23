#!/usr/bin/env python3
"""SonarVision CLI — full pipeline runner.

Usage:
  python cli_runner.py survey --type lawnmower --width 500 --height 200 --depth 25
  python cli_runner.py fleet --count 5 --seconds 60
  python cli_runner.py neural --train --epochs 10
  python cli_runner.py neural --predict --depth 25 --chl 5 --season summer
  python cli_runner.py physics --depth 0:100:5
  python cli_runner.py ray --source-depth 10 --angle 15 --range 100
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) if '__file__' in dir() else '.')

from sim_pipeline import (
    MissionPlanner, SonarDisplay, FluxPhysics, SonarRayTracer,
    compute_physics, dive_profile, AUVFleetSimulator, AUV, Formation,
    ConstraintSnapper, FLUXCTBridge, CSPTranslator,
)


def cmd_physics(args):
    depths = list(range(args.start, args.end + 1, args.step))
    prof = dive_profile(args.start, args.end, args.step, args.chl, args.season, args.sediment)
    print("depth,temperature,sound_speed,absorption,visibility,attenuation,seabed_reflectivity")
    for p in prof:
        print("{},{},{},{},{},{},{}".format(
            p["depth"], p["temperature"], p["sound_speed"], p["absorption"],
            p["visibility"], p["attenuation"], p["seabed_reflectivity"]))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(prof, f, indent=2)
            print("Wrote {}".format(args.json))


def cmd_ray(args):
    tracer = SonarRayTracer(chl=args.chl, season=args.season)
    ret = tracer.compute_return(args.source_depth, args.target_depth, args.target_range)
    print(json.dumps(ret, indent=2))

    if args.fan:
        scan = tracer.fan_scan(source_depth=args.source_depth, target_range=args.target_range)
        print("\nFan scan ({} rays):".format(len(scan)))
        for s in scan:
            print("  {:.0f} deg -> z={:.1f}m @ {:.0f}m  {:.0f}dB".format(
                s["angle_deg"], s["terminal_depth_m"],
                s["terminal_range_m"], s["terminal_intensity_db"]))


def cmd_survey(args):
    import time
    planner = MissionPlanner()
    types = {
        "lawnmower": lambda: planner.lawnmover(args.name, args.width, args.height, args.depth, args.spacing),
        "spiral": lambda: planner.spiral(args.name, max(args.width, args.height) / 2, args.depth),
        "star": lambda: planner.star(args.name, max(args.width, args.height) / 2, args.depth),
        "perimeter": lambda: planner.perimeter(args.name, args.width, args.height, args.depth),
    }
    mission = types.get(args.type, types["lawnmower"])()
    print("Mission: {} ({})".format(mission.name, mission.pattern))
    print("  Waypoints: {}".format(len(mission.waypoints)))
    print("  Distance:  {:.0f}m".format(mission.total_distance()))
    print("  Duration:  {:.0f}s".format(mission.estimated_duration()))

    # Show waypoints
    if args.verbose:
        for wp in mission.waypoints:
            print("  wp-{:02d}: ({:.0f}, {:.0f}) @ {:.0f}m s={:.1f}".format(
                wp.index, wp.x, wp.y, wp.depth, wp.speed))

    # Simulate pings at each waypoint
    if args.simulate:
        pings = []
        for wp in mission.waypoints:
            p = compute_physics(wp.depth, args.chl, args.season, args.sediment)
            p["position"] = {"x": wp.x, "y": wp.y}
            pings.append(p)
        print("\nSimulated {} pings".format(len(pings)))
        print(SonarDisplay.ping_table(pings))
        print("\nWaterfall:")
        print(SonarDisplay.waterfall(pings))


def cmd_fleet(args):
    sim = AUVFleetSimulator(FluxPhysics())
    sim.spawn_fleet(args.count, spread=args.spread, depth=args.depth)
    formations = {
        "line": Formation.LINE, "v": Formation.V,
        "diamond": Formation.DIAMOND, "grid": Formation.GRID,
    }
    sim.formation(formations.get(args.formation, Formation.V), spacing=args.spacing)
    print("Fleet: {} AUVs in {} formation".format(args.count, args.formation))
    print("Running {} seconds...".format(args.seconds))
    sim.run_for(args.seconds)
    summary = sim.fleet_summary()
    print("\nResults:")
    print("  Time:      {:.0f}s".format(summary["time"]))
    print("  Battery:   {:.1f}% avg".format(summary["avg_battery"]))
    print("  Collisions: {}".format(summary["collisions"]))
    for a in summary["fleet"]:
        print("  {}: pos=({:.0f},{:.0f},{:.0f}) bat={:.0f}% state={}".format(
            a["id"], a["position"]["x"], a["position"]["y"],
            a["position"]["z"], a["battery"], a["state"]))


def cmd_neural(args):
    try:
        from neural_physics import (
            PhysicsSurrogate, create_synthetic_data, train,
            benchmark, predict_profile, ModelConfig, TrainConfig,
        )
    except ImportError:
        print("Install torch: pip install torch")
        return

    cfg = ModelConfig()
    tc = TrainConfig(epochs=args.epochs, device="cpu")

    if args.train:
        print("Training neural surrogate for {} epochs...".format(args.epochs))
        model = PhysicsSurrogate(cfg)
        loaders = create_synthetic_data(n_samples=args.samples, batch_size=256)
        hist = train(model, loaders, tc)
        print("Done. Final loss: {:.4f}".format(hist["val_loss"][-1]))
        bm = benchmark(model, n_queries=200)
        print("Speed: {:.0f} q/s".format(bm["queries_per_sec"]))
        for name in cfg.output_dim:
            pass
        for name in ["temperature", "sound_speed", "visibility"]:
            print("  {} MAE: {:.4f}".format(name, bm["mae"].get(name, 0)))

    if args.predict:
        model = PhysicsSurrogate(cfg)
        season = 0 if args.season == "summer" else 1
        sed = {"mud": 0, "sand": 1, "gravel": 2, "rock": 3, "seagrass": 4}.get(args.sediment, 1)
        prof = predict_profile(model, args.start, args.end, args.step, args.chl, season, sed)
        print("Surrogate profile (0-epoch model, untrained):")
        for i, d in enumerate(prof["depths"]):
            s = prof["surrogate"][i]
            g = prof["ground_truth"][i]
            print("  {:4.0f}m  pred_T={:5.1f}C  gt_T={:5.1f}C  pred_c={:6.0f}  gt_c={:6.0f}".format(
                d, s["temperature"], g["temperature"], s["sound_speed"], g["sound_speed"]))


def main():
    parser = argparse.ArgumentParser(description="SonarVision Pipeline CLI")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("physics", help="Compute FLUX physics profile")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=100)
    p.add_argument("--step", type=int, default=5)
    p.add_argument("--chl", type=float, default=5.0)
    p.add_argument("--season", default="summer")
    p.add_argument("--sediment", default="sand")
    p.add_argument("--json", help="Output file")

    p = sub.add_parser("ray", help="Trace acoustic ray")
    p.add_argument("--source-depth", type=float, default=10.0)
    p.add_argument("--target-depth", type=float, default=50.0)
    p.add_argument("--target-range", type=float, default=100.0)
    p.add_argument("--chl", type=float, default=5.0)
    p.add_argument("--season", default="summer")
    p.add_argument("--fan", action="store_true")

    p = sub.add_parser("survey", help="Plan and simulate survey")
    p.add_argument("--type", choices=["lawnmower", "spiral", "star", "perimeter"], default="lawnmower")
    p.add_argument("--name", default="survey")
    p.add_argument("--width", type=float, default=500.0)
    p.add_argument("--height", type=float, default=200.0)
    p.add_argument("--depth", type=float, default=25.0)
    p.add_argument("--spacing", type=float, default=50.0)
    p.add_argument("--chl", type=float, default=5.0)
    p.add_argument("--season", default="summer")
    p.add_argument("--sediment", default="sand")
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--verbose", action="store_true")

    p = sub.add_parser("fleet", help="Run fleet simulation")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--seconds", type=int, default=60)
    p.add_argument("--depth", type=float, default=20.0)
    p.add_argument("--spread", type=float, default=100.0)
    p.add_argument("--spacing", type=float, default=40.0)
    p.add_argument("--formation", choices=["line", "v", "diamond", "grid"], default="v")

    p = sub.add_parser("neural", help="Train/predict with neural surrogate")
    p.add_argument("--train", action="store_true")
    p.add_argument("--predict", action="store_true")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--samples", type=int, default=10000)
    p.add_argument("--depth", type=float, default=25.0)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=50)
    p.add_argument("--step", type=int, default=5)
    p.add_argument("--chl", type=float, default=5.0)
    p.add_argument("--season", default="summer")
    p.add_argument("--sediment", default="sand")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmds = {
        "physics": cmd_physics,
        "ray": cmd_ray,
        "survey": cmd_survey,
        "fleet": cmd_fleet,
        "neural": cmd_neural,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
