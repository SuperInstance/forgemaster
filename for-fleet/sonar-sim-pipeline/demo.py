#!/usr/bin/env python3
"""Demo: full SonarVision pipeline survey with fleet simulation and CLI output."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath('.'))))

from sim_pipeline import (
    MissionPlanner, SonarDisplay, Pipeline,
    FluxPhysics, SonarRayTracer, compute_physics,
    AUVFleetSimulator, AUV, Formation,
    ConstraintSnapper, FLUXCTBridge, CSPTranslator,
)


def main():
    print("=" * 60)
    print("  SonarVision Pipeline v1.3.0 — Full Survey Demo")
    print("=" * 60)

    # 1. Physics Environment
    print("\n--- 1. FLUX Physics Engine ---")
    phys = FluxPhysics()
    for d in [0, 10, 25, 50, 100]:
        p = phys.compute(float(d), chl=4.0, season=0, sediment=1)
        print("  d={:4.0f}m  {:<18}  T={:5.1f}°C  c={:6.0f}m/s  vis={:4.1f}m  abs={:.4f}".format(
            p['depth'], p['water_type_name'],
            p['temperature'], p['sound_speed'],
            p['visibility'], p['absorption']))

    # 2. Ray Tracer
    print("\n--- 2. Sonar Ray Tracer ---")
    tracer = SonarRayTracer()
    ret = tracer.compute_return(10.0, 50.0, 100.0)
    print("  Ping @10m → seabed ~{:.0f}m (100m range)".format(ret['seabed_depth_m']))
    print("  Travel time: {:.4f}s  Loss: {:.1f}dB".format(
        ret['total_travel_time_s'], ret['total_loss_db']))

    # Fan scan
    scan = tracer.fan_scan(num_rays=9)
    print("  Fan scan (9 rays):")
    for s in scan[::2]:
        print("    {:4.0f}° → z={:5.1f}m @ {:4.0f}m  {:.0f}dB".format(
            s['angle_deg'], s['terminal_depth_m'],
            s['terminal_range_m'], s['terminal_intensity_db']))

    # 3. Mission Planning
    print("\n--- 3. Mission Planner ---")
    planner = MissionPlanner()
    m = planner.lawnmover("Alpha Survey", 500, 200, 25, line_spacing=50)
    print("  {:13s}: {:3d} waypoints, {:5.0f}m total, {:5.0f}s est".format(
        m.name, len(m.waypoints), m.total_distance(), m.estimated_duration()))

    s = planner.spiral("Spiral Survey", 150, 25, turns=4)
    print("  {:13s}: {:3d} waypoints, {:5.0f}m total, {:5.0f}s est".format(
        s.name, len(s.waypoints), s.total_distance(), s.estimated_duration()))

    # 4. Fleet Simulation
    print("\n--- 4. AUV Fleet Simulation ---")
    sim = AUVFleetSimulator(phys)
    sim.spawn_fleet(5, spread=150)
    sim.formation(Formation.DIAMOND, spacing=40)
    events = sim.run_for(60)
    summary = sim.fleet_summary()
    print("  Fleet: {} AUVs, {:.1f}% avg battery, {} collisions".format(
        summary['count'], summary['avg_battery'], summary['collisions']))
    print("  Comms events: {} total links".format(
        sum(1 for ev in events for e in ev['events'] if e.startswith('LINK'))))

    # 5. Constraint Bridge
    print("\n--- 5. FLUX → Constraint Theory Bridge ---")
    bridge = FLUXCTBridge(phys)
    snap = bridge.snap_profile(35.0)
    print("  Snap @35m: FLUX opcode={}, CT vars={}".format(
        snap['flux_opcode'], snap['constraint_variables']))

    snapper = ConstraintSnapper(phys)
    opt = snapper.optimal_survey_depth()
    print("  Optimal survey depth: {}m (vis={:.1f}m, abs={:.4f})".format(
        opt['depth'], opt['visibility'], opt['absorption']))

    print("\n" + "=" * 60)
    print("  Demo complete. All systems operational.")
    print("=" * 60)


if __name__ == "__main__":
    main()
