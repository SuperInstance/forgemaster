"""Multi-agent AUV fleet simulator with FLUX physics."""
import math
import random
from dataclasses import dataclass, field
from enum import Enum


class AUVState(Enum):
    IDLE = "idle"
    TRANSIT = "transit"
    SURVEY = "survey"
    RETURN = "return"
    EMERGENCY = "emergency"


class Formation(Enum):
    LINE = "line"
    V = "v"
    DIAMOND = "diamond"
    GRID = "grid"
    RANDOM = "random"


@dataclass
class AUV:
    id: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    heading: float = 0.0
    speed: float = 1.5
    battery: float = 100.0
    state: AUVState = AUVState.IDLE
    path: list = field(default_factory=list)
    comms_range: float = 300.0
    acoustic_channel: int = 0

    def to_dict(self):
        return dict(id=self.id,
                    position=dict(x=round(self.x, 1), y=round(self.y, 1), z=round(self.z, 1)),
                    heading=round(self.heading, 1), speed=round(self.speed, 2),
                    battery=round(self.battery, 1), state=self.state.value)


class AUVFleetSimulator:
    def __init__(self, physics):
        self.physics = physics
        self.auvs = {}
        self.time = 0.0
        self.collisions = 0

    def spawn_fleet(self, count=5, cx=0, cy=0, spread=100, depth=20):
        ids = []
        for i in range(count):
            a = 2 * math.pi * i / count
            auv = AUV("auv_{}".format(i),
                      cx + spread * math.cos(a),
                      cy + spread * math.sin(a),
                      depth + random.uniform(-5, 5),
                      math.degrees(a),
                      1.5 + random.uniform(-0.3, 0.3),
                      95 + random.uniform(-5, 5),
                      AUVState.SURVEY,
                      acoustic_channel=i % 3)
            self.auvs[auv.id] = auv
            ids.append(auv.id)
        return ids

    def tick(self):
        self.time += 1.0
        for a in self.auvs.values():
            if a.state == AUVState.EMERGENCY:
                continue
            env = self.physics.compute(a.z, chl=4.0, season=0, sediment=1)
            a.battery -= 0.005 + env.get("attenuation", 0.05) * 0.1
            if a.battery < 10:
                a.state = AUVState.EMERGENCY
        return dict(time=self.time, auv_count=len(self.auvs))

    def formation(self, ftype, cx=0, cy=0, spacing=30):
        alist = list(self.auvs.values())
        n = len(alist)
        if ftype == Formation.LINE:
            offs = [(i*spacing, 0, 0) for i in range(n)]
        elif ftype == Formation.V:
            offs = [(i*spacing*0.5, (i%2-0.5)*spacing*(i//2+1), 0) for i in range(n)]
        elif ftype == Formation.DIAMOND:
            offs = [(spacing*(1-0.5*(i%2))*math.cos(2*math.pi*i/n),
                     spacing*(1-0.5*(i%2))*math.sin(2*math.pi*i/n), 0) for i in range(n)]
        elif ftype == Formation.GRID:
            cols = max(2, int(math.sqrt(n)))
            offs = [(i%cols*spacing, i//cols*spacing, 0) for i in range(n)]
        else:
            offs = [(random.uniform(-spacing, spacing),
                     random.uniform(-spacing, spacing), 0) for _ in range(n)]
        for i, a in enumerate(alist):
            a.path = [(cx+offs[i][0], cy+offs[i][1], a.z+offs[i][2])]

    def fleet_summary(self):
        avg_bat = sum(a.battery for a in self.auvs.values()) / max(len(self.auvs), 1)
        return dict(time=round(self.time, 1), count=len(self.auvs),
                    collisions=self.collisions, avg_battery=round(avg_bat, 1))

    def run_for(self, seconds):
        return [self.tick() for _ in range(int(seconds))]
