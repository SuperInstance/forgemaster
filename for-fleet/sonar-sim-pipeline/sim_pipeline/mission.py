"""Mission planner for autonomous sonar surveys."""
import math
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple
from enum import Enum
from datetime import datetime


class SurveyPattern(Enum):
    LAWNMOWER = "lawnmower"
    SPIRAL = "spiral"
    ADAPTIVE = "adaptive"
    STAR = "star"
    PERIMETER = "perimeter"


@dataclass
class Waypoint:
    x: float
    y: float
    depth: float
    speed: float = 1.5
    ping_rate: float = 1.0
    index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Mission:
    name: str
    pattern: str
    waypoints: List[Waypoint]
    area_width: float
    area_height: float
    max_depth: float
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "area_width": self.area_width,
            "area_height": self.area_height,
            "max_depth": self.max_depth,
            "waypoints": [wp.to_dict() for wp in self.waypoints],
            "waypoint_count": len(self.waypoints),
            "created_at": self.created_at,
        }

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def total_distance(self) -> float:
        total = 0.0
        for i in range(1, len(self.waypoints)):
            dx = self.waypoints[i].x - self.waypoints[i-1].x
            dy = self.waypoints[i].y - self.waypoints[i-1].y
            dz = self.waypoints[i].depth - self.waypoints[i-1].depth
            total += math.sqrt(dx*dx + dy*dy + dz*dz)
        return round(total, 1)

    def estimated_duration(self) -> float:
        dist = self.total_distance()
        avg_speed = self.waypoints[0].speed if self.waypoints else 1.5
        return round(dist / avg_speed, 1)


class MissionPlanner:
    """Generate survey missions with configurable patterns."""

    def __init__(self, physics=None):
        self.physics = physics
        self._wp_counter = 0

    def _next_index(self) -> int:
        self._wp_counter += 1
        return self._wp_counter

    def lawnmover(self, name: str, width: float, height: float,
                  depth: float, line_spacing: float = 50.0,
                  speed: float = 1.5, ping_rate: float = 1.0) -> Mission:
        waypoints = []
        lines = max(2, int(height / line_spacing))
        for i in range(lines):
            y = i * line_spacing
            if i % 2 == 0:
                waypoints.append(Waypoint(0, y, depth, speed, ping_rate, self._next_index()))
                waypoints.append(Waypoint(width, y, depth, speed, ping_rate, self._next_index()))
            else:
                waypoints.append(Waypoint(width, y, depth, speed, ping_rate, self._next_index()))
                waypoints.append(Waypoint(0, y, depth, speed, ping_rate, self._next_index()))
        return Mission(name, "lawnmower", waypoints, width, height, depth)

    def spiral(self, name: str, max_radius: float,
               depth: float, turns: int = 5,
               speed: float = 1.5, ping_rate: float = 1.0) -> Mission:
        waypoints = []
        points_per_turn = 12
        for t in range(turns * points_per_turn + 1):
            angle = 2 * math.pi * t / points_per_turn
            radius = max_radius * (1 - t / (turns * points_per_turn))
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            waypoints.append(Waypoint(x, y, depth, speed, ping_rate, self._next_index()))
        return Mission(name, "spiral", waypoints, max_radius * 2, max_radius * 2, depth)

    def star(self, name: str, radius: float,
             depth: float, arms: int = 4,
             speed: float = 1.5, ping_rate: float = 1.0) -> Mission:
        waypoints = []
        waypoints.append(Waypoint(0, 0, depth, speed, ping_rate, self._next_index()))
        for i in range(arms):
            angle = 2 * math.pi * i / arms
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            waypoints.append(Waypoint(x, y, depth, speed, ping_rate, self._next_index()))
            waypoints.append(Waypoint(0, 0, depth, speed, ping_rate, self._next_index()))
        return Mission(name, "star", waypoints, radius * 2, radius * 2, depth)

    def perimeter(self, name: str, width: float, height: float,
                  depth: float, speed: float = 1.5,
                  ping_rate: float = 1.0) -> Mission:
        waypoints = [
            Waypoint(0, 0, depth, speed, ping_rate, self._next_index()),
            Waypoint(width, 0, depth, speed, ping_rate, self._next_index()),
            Waypoint(width, height, depth, speed, ping_rate, self._next_index()),
            Waypoint(0, height, depth, speed, ping_rate, self._next_index()),
            Waypoint(0, 0, depth, speed, ping_rate, self._next_index()),
        ]
        return Mission(name, "perimeter", waypoints, width, height, depth)
