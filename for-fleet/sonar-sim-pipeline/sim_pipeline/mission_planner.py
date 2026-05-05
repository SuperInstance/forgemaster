"""Autonomous AUV mission planner.

Generates waypoints for lawnmower, spiral, and adaptive survey patterns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import logging

logger = logging.getLogger(__name__)


class SurveyType(Enum):
    """Supported survey patterns."""
    LAWNMOWER = "lawnmower"
    SPIRAL = "spiral"
    ADAPTIVE = "adaptive"


@dataclass(frozen=True, slots=True)
class Waypoint:
    """A single mission waypoint."""
    x: float
    y: float
    z: float
    speed: float = 2.0
    heading: float | None = None
    action: str = "ping"


@dataclass(frozen=True, slots=True)
class Mission:
    """A complete AUV survey mission."""
    survey_type: SurveyType
    waypoints: tuple[Waypoint, ...]
    area_m2: float
    line_spacing: float
    depth: float

    @property
    def duration_estimate_s(self) -> float:
        if not self.waypoints:
            return 0.0
        total_dist = 0.0
        for i in range(1, len(self.waypoints)):
            w0 = self.waypoints[i - 1]
            w1 = self.waypoints[i]
            total_dist += math.hypot(w1.x - w0.x, w1.y - w0.y, w1.z - w0.z)
        avg_speed = sum(w.speed for w in self.waypoints) / max(len(self.waypoints), 1)
        if avg_speed <= 0:
            return 0.0
        return total_dist / avg_speed

    def as_geojson_feature_collection(self) -> dict:
        features = []
        for i, wp in enumerate(self.waypoints):
            features.append({
                "type": "Feature",
                "properties": {
                    "index": i,
                    "speed": wp.speed,
                    "action": wp.action,
                    "heading_deg": round(math.degrees(wp.heading), 2) if wp.heading is not None else None,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(wp.x, 3), round(wp.y, 3), round(-wp.z, 3)],
                },
            })
        return {"type": "FeatureCollection", "features": features}


class MissionPlanner:
    """Generates deterministic AUV survey missions."""

    def __init__(self, default_speed: float = 2.5, default_depth: float = 50.0) -> None:
        self.default_speed = default_speed
        self.default_depth = default_depth
        logger.debug("MissionPlanner initialized: speed=%.2f m/s, depth=%.1f m", default_speed, default_depth)

    def lawnmower(self, width: float, height: float, line_spacing: float | None = None, depth: float | None = None, speed: float | None = None) -> Mission:
        d = depth if depth is not None else self.default_depth
        sp = speed if speed is not None else self.default_speed
        ls = line_spacing if line_spacing is not None else width * 0.10
        if ls <= 0:
            ls = 1.0
        waypoints: list[Waypoint] = []
        waypoints.append(Waypoint(x=0.0, y=0.0, z=0.0, speed=sp, action="dive"))
        n_lines = max(1, int(math.ceil(height / ls)))
        actual_ls = height / n_lines
        for i in range(n_lines):
            y0 = i * actual_ls
            y1 = (i + 1) * actual_ls
            if i % 2 == 0:
                waypoints.append(Waypoint(x=0.0, y=y0, z=d, speed=sp, action="ping"))
                waypoints.append(Waypoint(x=width, y=y0, z=d, speed=sp, action="ping"))
            else:
                waypoints.append(Waypoint(x=width, y=y0, z=d, speed=sp, action="ping"))
                waypoints.append(Waypoint(x=0.0, y=y0, z=d, speed=sp, action="ping"))
            if i < n_lines - 1:
                waypoints.append(Waypoint(x=waypoints[-1].x, y=y1, z=d, speed=sp, action="turn"))
        waypoints.append(Waypoint(x=waypoints[-1].x, y=waypoints[-1].y, z=0.0, speed=sp, action="surface"))
        waypoints.append(Waypoint(x=0.0, y=0.0, z=0.0, speed=sp, action="end"))
        area = width * height
        logger.info("Lawnmower mission: %d waypoints, %.0f m2, %.1f m spacing", len(waypoints), area, actual_ls)
        return Mission(survey_type=SurveyType.LAWNMOWER, waypoints=tuple(waypoints), area_m2=area, line_spacing=actual_ls, depth=d)

    def spiral(self, width: float, height: float, line_spacing: float | None = None, depth: float | None = None, speed: float | None = None, turns: int = 5) -> Mission:
        d = depth if depth is not None else self.default_depth
        sp = speed if speed is not None else self.default_speed
        ls = line_spacing if line_spacing is not None else min(width, height) / (2.0 * max(turns, 1))
        if ls <= 0:
            ls = 1.0
        waypoints: list[Waypoint] = []
        waypoints.append(Waypoint(x=0.0, y=0.0, z=0.0, speed=sp, action="dive"))
        cx, cy = width / 2.0, height / 2.0
        max_radius = math.hypot(width, height) / 2.0
        n_points = max(turns * 20, 50)
        for i in range(n_points + 1):
            t = 2.0 * math.pi * turns * i / n_points
            r = ls * t / (2.0 * math.pi)
            if r > max_radius:
                r = max_radius
            x = cx + r * math.cos(t)
            y = cy + r * math.sin(t)
            x = max(0.0, min(width, x))
            y = max(0.0, min(height, y))
            waypoints.append(Waypoint(x=x, y=y, z=d, speed=sp, action="ping"))
            if r >= max_radius:
                break
        waypoints.append(Waypoint(x=waypoints[-1].x, y=waypoints[-1].y, z=0.0, speed=sp, action="surface"))
        waypoints.append(Waypoint(x=0.0, y=0.0, z=0.0, speed=sp, action="end"))
        area = width * height
        logger.info("Spiral mission: %d waypoints, %.0f m2, %.1f m spacing", len(waypoints), area, ls)
        return Mission(survey_type=SurveyType.SPIRAL, waypoints=tuple(waypoints), area_m2=area, line_spacing=ls, depth=d)

    def adaptive(self, width: float, height: float, depth: float | None = None, speed: float | None = None, complexity: float = 0.5) -> Mission:
        d = depth if depth is not None else self.default_depth
        sp = speed if speed is not None else self.default_speed
        complexity = max(0.0, min(1.0, complexity))
        base_spacing = 5.0 + complexity * 45.0
        waypoints: list[Waypoint] = []
        waypoints.append(Waypoint(x=0.0, y=0.0, z=0.0, speed=sp, action="dive"))
        y = 0.0
        line_idx = 0
        while y < height:
            mod = 0.5 + 0.5 * math.sin(line_idx * 0.7)
            current_spacing = base_spacing * (0.7 + 0.3 * mod)
            y_next = min(y + current_spacing, height)
            if line_idx % 2 == 0:
                waypoints.append(Waypoint(x=0.0, y=y, z=d, speed=sp, action="ping"))
                waypoints.append(Waypoint(x=width, y=y, z=d, speed=sp, action="ping"))
            else:
                waypoints.append(Waypoint(x=width, y=y, z=d, speed=sp, action="ping"))
                waypoints.append(Waypoint(x=0.0, y=y, z=d, speed=sp, action="ping"))
            if y_next < height:
                waypoints.append(Waypoint(x=waypoints[-1].x, y=y_next, z=d, speed=sp, action="turn"))
            y = y_next
            line_idx += 1
        waypoints.append(Waypoint(x=waypoints[-1].x, y=waypoints[-1].y, z=0.0, speed=sp, action="surface"))
        waypoints.append(Waypoint(x=0.0, y=0.0, z=0.0, speed=sp, action="end"))
        area = width * height
        logger.info("Adaptive mission: %d waypoints, %.0f m2, complexity=%.2f", len(waypoints), area, complexity)
        return Mission(survey_type=SurveyType.ADAPTIVE, waypoints=tuple(waypoints), area_m2=area, line_spacing=base_spacing, depth=d)

    def plan(self, survey_type: SurveyType, width: float, height: float, depth: float | None = None, speed: float | None = None, line_spacing: float | None = None) -> Mission:
        if survey_type == SurveyType.LAWNMOWER:
            return self.lawnmower(width, height, line_spacing, depth, speed)
        elif survey_type == SurveyType.SPIRAL:
            return self.spiral(width, height, line_spacing, depth, speed)
        elif survey_type == SurveyType.ADAPTIVE:
            return self.adaptive(width, height, depth, speed)
        else:
            raise ValueError(f"Unknown survey type: {survey_type}")
