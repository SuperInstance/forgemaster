"""Mission planner for autonomous sonar surveys."""
import math, json
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple
from datetime import datetime

@dataclass
class Waypoint:
    x: float; y: float; depth: float
    speed: float = 1.5; ping_rate: float = 1.0; index: int = 0
    def to_dict(self) -> dict: return asdict(self)

@dataclass
class Mission:
    name: str; pattern: str; waypoints: List[Waypoint]
    area_width: float; area_height: float; max_depth: float
    created_at: str = ""
    def __post_init__(self):
        if not self.created_at: self.created_at = datetime.utcnow().isoformat()
    def to_dict(self) -> dict:
        return {"name": self.name, "pattern": self.pattern,
                "area_width": self.area_width, "area_height": self.area_height,
                "max_depth": self.max_depth,
                "waypoints": [wp.to_dict() for wp in self.waypoints],
                "waypoint_count": len(self.waypoints), "created_at": self.created_at}
    def to_json(self, indent=2) -> str: return json.dumps(self.to_dict(), indent=indent)
    def total_distance(self) -> float:
        t = 0.0
        for i in range(1, len(self.waypoints)):
            dx = self.waypoints[i].x - self.waypoints[i-1].x
            dy = self.waypoints[i].y - self.waypoints[i-1].y
            dz = self.waypoints[i].depth - self.waypoints[i-1].depth
            t += math.sqrt(dx*dx + dy*dy + dz*dz)
        return round(t, 1)
    def estimated_duration(self) -> float:
        return round(self.total_distance() / (self.waypoints[0].speed if self.waypoints else 1.5), 1)

class MissionPlanner:
    def __init__(self, physics=None): self.physics = physics; self._n = 0
    def _i(self): self._n += 1; return self._n
    def lawnmover(self, name, width, height, depth, spacing=50.0, speed=1.5, pr=1.0) -> Mission:
        wps = []
        for i in range(max(2, int(height/spacing))):
            y = i * spacing
            if i % 2 == 0:
                wps.append(Waypoint(0, y, depth, speed, pr, self._i()))
                wps.append(Waypoint(width, y, depth, speed, pr, self._i()))
            else:
                wps.append(Waypoint(width, y, depth, speed, pr, self._i()))
                wps.append(Waypoint(0, y, depth, speed, pr, self._i()))
        return Mission(name, "lawnmower", wps, width, height, depth)
    def spiral(self, name, max_radius, depth, turns=5, speed=1.5, pr=1.0) -> Mission:
        wps = []
        for t in range(turns * 12 + 1):
            angle = 2 * math.pi * t / 12
            r = max_radius * (1 - t / (turns * 12))
            wps.append(Waypoint(r*math.cos(angle), r*math.sin(angle), depth, speed, pr, self._i()))
        return Mission(name, "spiral", wps, max_radius*2, max_radius*2, depth)
    def star(self, name, radius, depth, arms=4, speed=1.5, pr=1.0) -> Mission:
        wps = [Waypoint(0, 0, depth, speed, pr, self._i())]
        for i in range(arms):
            a = 2 * math.pi * i / arms
            wps.append(Waypoint(radius*math.cos(a), radius*math.sin(a), depth, speed, pr, self._i()))
            wps.append(Waypoint(0, 0, depth, speed, pr, self._i()))
        return Mission(name, "star", wps, radius*2, radius*2, depth)
    def perimeter(self, name, width, height, depth, speed=1.5, pr=1.0) -> Mission:
        wps = [Waypoint(0, 0, depth, speed, pr, self._i()),
               Waypoint(width, 0, depth, speed, pr, self._i()),
               Waypoint(width, height, depth, speed, pr, self._i()),
               Waypoint(0, height, depth, speed, pr, self._i()),
               Waypoint(0, 0, depth, speed, pr, self._i())]
        return Mission(name, "perimeter", wps, width, height, depth)
