"""Sonar simulation pipeline — missions, physics, ray tracing, display."""
from .mission import MissionPlanner, Mission, Waypoint
from .display import SonarDisplay
from .pipeline import Pipeline
from .physics import FluxPhysics, SonarRayTracer, compute_physics, dive_profile

__version__ = "0.1.0"
__all__ = [
    "MissionPlanner", "Mission", "Waypoint",
    "SonarDisplay", "Pipeline",
    "FluxPhysics", "SonarRayTracer", "compute_physics", "dive_profile",
]
