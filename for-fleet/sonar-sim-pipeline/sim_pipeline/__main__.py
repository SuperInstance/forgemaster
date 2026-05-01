"""Sonar simulation pipeline - allows module execution: python -m sim_pipeline."""

import sys

def main():
    """Run pipeline as module."""
    print("Sonar Simulation Pipeline v0.2.0")
    print("Modules: physics, mission, display, fleet, ct_bridge, pipeline")
    print("")
    print("Usage:")
    print("  from sim_pipeline import FluxPhysics, MissionPlanner, SonarRayTracer")
    print("  from sim_pipeline import compute_physics, dive_profile, SonarDisplay")
    print("  from sim_pipeline import AUVFleetSimulator, ConstraintSnapper")
    print("")
    print("Example:")
    print("  prof = dive_profile(0, 50, 5)")
    print("  print(SonarDisplay.ping_table(prof))")

if __name__ == "__main__":
    main()
