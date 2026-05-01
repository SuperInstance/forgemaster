"""Sonar simulation pipeline — autonomous survey, fleet simulation, FLUX physics."""
from .mission import MissionPlanner, Mission, Waypoint
from .display import SonarDisplay
from .pipeline import Pipeline
from .physics import FluxPhysics, SonarRayTracer, compute_physics, dive_profile
from .ct_bridge import ConstraintSnapper, FLUXCTBridge, CSPTranslator
from .fleet_sim import AUVFleetSimulator, AUV, AUVState, Formation

__version__ = "0.2.0"
__all__ = [
    "MissionPlanner", "Mission", "Waypoint",
    "SonarDisplay", "Pipeline",
    "FluxPhysics", "SonarRayTracer", "compute_physics", "dive_profile",
    "ConstraintSnapper", "FLUXCTBridge", "CSPTranslator",
    "AUVFleetSimulator", "AUV", "AUVState", "Formation",
]
