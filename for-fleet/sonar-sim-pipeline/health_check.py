#!/usr/bin/env python3
"""SonarVision System Health Check — verifies all 9 subsystems in one shot.

Usage:
    python3 health_check.py          # local modules
    python3 health_check.py --all    # full check incl. registries (network)

Prints a pass/fail board for every subsystem.
"""

import sys
import os
import math
import time

# Add sim_pipeline to path for module imports
_HP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HP)
sys.path.insert(0, os.path.join(_HP, 'sim_pipeline'))

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"
BOLD = "\033[1m"
RESET = "\033[0m"


def header(title):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")


def check(name, ok, detail=""):
    status = PASS if ok else FAIL
    d = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{d}")
    return ok


def run():
    results = []
    errors = []

    # ── 1. Physics Engine ──
    header("1. FLUX Physics Engine")
    try:
        # Force fresh import
        if "sim_pipeline.physics" in sys.modules:
            del sys.modules["sim_pipeline.physics"]
        from sim_pipeline.physics import FluxPhysics, compute_physics, dive_profile, SonarRayTracer

        p = FluxPhysics().compute(15.0, chl=4.0, season=0, sediment=1)
        ok = abs(p["temperature"] - 22.0) < 0.5
        results.append(check("Temp @15m (summer)", ok,
                             f"{p['temperature']:.1f}C (expect ~22.0)"))

        ok = abs(p["sound_speed"] - 1527) < 5
        results.append(check("Sound speed @15m", ok,
                             f"{p['sound_speed']:.0f} m/s (expect ~1527)"))

        ok = abs(p["refraction_deg"] - 14.6) < 1.0
        results.append(check("Refraction angle", ok,
                             f"{p['refraction_deg']:.1f}° (expect ~14.6)"))

        # Season parameter as string
        p2 = compute_physics(30.0, chl=2.0, season="winter", sediment="rock")
        ok = p2["temperature"] < p["temperature"]  # winter colder than summer
        results.append(check("Winter colder than summer", ok,
                             f"{p['temperature']:.1f}C vs {p2['temperature']:.1f}C"))

        # Dive profile
        prof = dive_profile(0, 30, 5)
        ok = len(prof) == 7  # 0,5,10,15,20,25,30
        results.append(check("Dive profile depths", ok, f"{len(prof)} points"))
    except Exception as e:
        errors.append(f"Physics: {e}")
        results.append(False)

    # ── 2. SonarRayTracer ──
    header("2. Sonar Ray Tracer")
    try:
        rt = SonarRayTracer(max_depth=100, layers=200)

        # Surface sound speed
        ssp = rt.sound_speed_at(0)
        ok = 1460 < ssp < 1550
        results.append(check("SSP surface", ok, f"{ssp:.0f} m/s (expect ~1468)"))

        # Ray trace
        ray = rt.trace_ray(sd=10.0, angle=15.0, rng=100.0, steps=500)
        ok = len(ray) > 10
        results.append(check("Ray trace steps", ok, f"{len(ray)} steps"))

        # Compute return
        ret = rt.compute_return(10.0, 50.0, 100.0)
        ok = 0.13 < ret["total_travel_time_s"] < 0.15
        results.append(check("Return travel time", ok,
                             f"{ret['total_travel_time_s']:.4f}s (expect ~0.139)"))

        ok = 500 < ret["total_loss_db"] < 600
        results.append(check("Return loss", ok,
                             f"{ret['total_loss_db']:.1f}dB"))

        # Fan scan
        fan = rt.fan_scan(sd=15.0, rng=80.0, nr=9)
        ok = len(fan) == 9
        results.append(check("Fan scan beams", ok, f"{len(fan)} beams"))
    except Exception as e:
        errors.append(f"RayTracer: {e}")
        results.append(False)

    # ── 3. Mission Planner ──
    header("3. Mission Planner")
    try:
        from sim_pipeline.mission import MissionPlanner

        mp = MissionPlanner()

        m1 = mp.lawnmower("lawn", 500, 200, 25)
        ok = len(m1.waypoints) == 8
        results.append(check("Lawnmower (8 wp)", ok, f"{len(m1.waypoints)} waypoints"))

        m2 = mp.spiral("spiral", 100, 15, turns=4)
        ok = len(m2.waypoints) == 49
        results.append(check("Spiral (49 wp)", ok, f"{len(m2.waypoints)} waypoints"))

        m3 = mp.star("star", 100, 15, arms=4)
        ok = len(m3.waypoints) == 9
        results.append(check("Star (9 wp)", ok, f"{len(m3.waypoints)} waypoints"))

        m4 = mp.perimeter("perim", 500, 200, 25)
        ok = len(m4.waypoints) == 5
        results.append(check("Perimeter (5 wp)", ok, f"{len(m4.waypoints)} waypoints"))

        ok = isinstance(m1.total_distance(), float) and m1.total_distance() > 0
        results.append(check("Mission distance", ok, f"{m1.total_distance():.0f}m"))
    except Exception as e:
        errors.append(f"Mission: {e}")
        results.append(False)

    # ── 4. Display ──
    header("4. Sonar Display")
    try:
        from sim_pipeline.display import SonarDisplay

        wf = SonarDisplay.waterfall([dict(visibility=i*0.5) for i in range(30)], width=40, height=10)
        ok = len(wf.split("\n")) == 12  # 10 + 2 header lines
        results.append(check("Waterfall rendering", ok, f"{len(wf.split(chr(10)))} lines"))

        pt = SonarDisplay.ping_table([dict(depth=i*10, temperature=22-i*0.5,
                                            sound_speed=1500, visibility=20, attenuation=0.1)
                                      for i in range(5)])
        ok = "Ping" in pt
        results.append(check("Ping table", ok, f"{len(pt.split(chr(10)))} lines"))

        exp = SonarDisplay.export_json(dict(test=True))
        ok = '"test": true' in exp
        results.append(check("JSON export", ok))
    except Exception as e:
        errors.append(f"Display: {e}")
        results.append(False)

    # ── 5. Fleet Simulator ──
    header("5. AUV Fleet Simulator")
    try:
        from sim_pipeline.fleet_sim import AUVFleetSimulator, AUVState, Formation
        from sim_pipeline.physics import FluxPhysics

        sim = AUVFleetSimulator(FluxPhysics())
        ids = sim.spawn_fleet(5, depth=20)
        ok = len(ids) == 5
        results.append(check("Spawn fleet", ok, f"{len(ids)} AUVs"))

        t = sim.tick()
        ok = t["time"] == 1.0
        results.append(check("Fleet tick", ok, f"time={t['time']}"))

        sim.formation(Formation.V, spacing=40)
        ok = any(a.path for a in sim.auvs.values())
        results.append(check("V-formation", ok))

        stats = sim.run_for(30)
        ok = len(stats) == 30
        results.append(check("Run for 30s", ok, f"{len(stats)} ticks"))

        summary = sim.fleet_summary()
        results.append(check("Fleet summary", summary["avg_battery"] < 100,
                             f"{summary['avg_battery']:.1f}% avg battery"))
    except Exception as e:
        errors.append(f"Fleet: {e}")
        results.append(False)

    # ── 6. Constraint Theory Bridge ──
    header("6. Constraint Theory Bridge")
    try:
        from sim_pipeline.ct_bridge import ConstraintSnapper, FLUXCTBridge, CSPTranslator
        from sim_pipeline.physics import FluxPhysics

        phys = FluxPhysics()

        snap = ConstraintSnapper(phys)
        opt = snap.optimal_survey_depth(0, 50)
        ok = 0 <= opt["depth"] <= 50
        results.append(check("Optimal survey depth", ok, f"{opt['depth']}m"))

        bridge = FLUXCTBridge(phys)
        sp = bridge.snap_profile(35.0)
        ok = len(sp["constraint_variables"]) == 3
        results.append(check("Profile snapping", ok, f"3 vars snapped"))

        csp = CSPTranslator(phys)
        sp = csp.sonar_path_planning([10, 20, 30, 40, 50])
        ok = len(sp["variables"]) == 5 and len(sp["transitions"]) == 4
        results.append(check("CSP path planning", ok,
                             f"{len(sp['transitions'])} transitions"))
    except Exception as e:
        errors.append(f"CT Bridge: {e}")
        results.append(False)

    # ── 7. Pipeline ──
    header("7. Pipeline")
    try:
        from sim_pipeline.pipeline import Pipeline

        pl = Pipeline(max_depth=50)
        env = pl.get_env(15)
        ok = "temperature" in env
        results.append(check("Pipeline env @15m", ok,
                             f"temp={env.get('temperature', '?')}C"))
    except Exception as e:
        errors.append(f"Pipeline: {e}")
        results.append(False)

    # ── 8. Digital Twin ──
    header("8. Marine Digital Twin")
    try:
        from digital_twin import MarineDigitalTwin

        twin = MarineDigitalTwin(max_depth=100, chl=4.0, season="summer")
        prof = twin.profile(0, 30, 5)
        ok = len(prof) == 7
        results.append(check("DT profile", ok, f"{len(prof)} depths"))

        tc = twin.find_thermocline(prof)
        ok = 8 < tc["depth"] < 15 and tc["dTdz"] > 0.5
        results.append(check("DT thermocline", ok,
                             f"{tc['depth']}m ({tc['dTdz']:.3f}C/m)"))

        mission = twin.plan_mission("spiral", width=200, height=200, depth=20)
        ok = isinstance(mission, dict) and mission["waypoint_count"] > 10
        results.append(check("DT mission plan", ok,
                             f"{mission['waypoint_count']} waypoints"))

        summary = twin.summary()
        ok = "Environmental" in summary or "Profile" in summary
        results.append(check("DT summary", ok))

        # What-if
        wi = twin.what_if(chl=10.0)
        ok = isinstance(wi, dict) and "optimal_depth_m" in wi
        results.append(check("DT what-if", ok,
                             f"opt_depth={wi.get('optimal_depth_m', '?')}m"))
    except Exception as e:
        errors.append(f"DigitalTwin: {e}")
        results.append(False)

    # ── 9. Neural Physics ──
    header("9. Neural Physics Surrogate")
    try:
        import torch
        from neural_physics import PhysicsSurrogate, ModelConfig, DataConfig

        cfg = ModelConfig(hidden_dim=32, n_ensemble=2)
        model = PhysicsSurrogate(model_cfg=cfg)
        x = torch.randn(4, cfg.input_dim)
        out = model(x)
        ok = out["predictions"].shape == (4, cfg.output_dim)
        results.append(check("Forward pass", ok, f"output shape {list(out['predictions'].shape)}"))
    except ImportError as e:
        results.append(check("Neural (requires torch)", False, str(e)))
    except Exception as e:
        results.append(check("Neural surrogate", False, str(e)))

    # ── Summary ──
    header("SUMMARY")
    passed = sum(1 for r in results if r)
    total = len(results)
    failed = total - passed

    print(f"  {BOLD}{passed}/{total} checks passed{RESET}")
    if failed > 0:
        print(f"  \033[31m{failed} check(s) FAILED{RESET}")
    if errors:
        print(f"\n  \033[31m{len(errors)} subsystem error(s):{RESET}")
        for e in errors:
            print(f"    {e}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
