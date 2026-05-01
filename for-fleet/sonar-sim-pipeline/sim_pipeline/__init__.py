"""Sonar Simulation Pipeline.

A production-quality Python package for autonomous AUV sonar simulation
integrating mission planning, FLUX physics, ray tracing, and display/export.

Modules:
    physics       - FLUX physics engine (Mackenzie, Francois-Garrison, Snell, Jerlov)
    ray_tracer    - Deterministic 2D ray tracer with multi-beam support
    mission_planner - Lawnmower, spiral, and adaptive survey generators
    display       - ASCII waterfall plots and JSON/CSV exporters
    pipeline      - End-to-end orchestration class
    cli           - Command-line interface

Example::

    from sim_pipeline import Pipeline, SurveyType, JerlovWaterType

    pipe = Pipeline(
        survey_type=SurveyType.LAWNMOWER,
        width=500, height=500, depth=50,
        water_type=JerlovWaterType.IA,
    )
    result = pipe.run()
    print(result.ascii_plot)
"""

__version__ = "1.0.0"

from .physics import FluxPhysics, JerlovWaterType, get_physics_backend, PhysicsBackend
from .ray_tracer import SonarRayTracer, PingResult, RayPoint, get_ray_tracer_backend
from .mission_planner import MissionPlanner, Mission, Waypoint, SurveyType
from .display import SonarDisplay, DisplayPing
from .pipeline import Pipeline, PipelineResult

__all__ = [
    "FluxPhysics",
    "JerlovWaterType",
    "get_physics_backend",
    "PhysicsBackend",
    "SonarRayTracer",
    "PingResult",
    "RayPoint",
    "get_ray_tracer_backend",
    "MissionPlanner",
    "Mission",
    "Waypoint",
    "SurveyType",
    "SonarDisplay",
    "DisplayPing",
    "Pipeline",
    "PipelineResult",
]
