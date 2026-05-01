"""Multi-agent AUV fleet simulator with FLUX physics."""
import math, random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

class AUVState(Enum): IDLE="idle"; TRANSIT="transit"; SURVEY="survey"; RETURN="return"; EMERGENCY="emergency"; DOCKED="docked"
class Formation(Enum): LINE="line"; V="v"; DIAMOND="diamond"; GRID="grid"; RANDOM="random"

@dataclass
class AUV:
    id: str; x: float=0.0; y: float=0.0; z: float=0.0
    heading: float=0.0; speed: float=1.5; battery: float=100.0
    state: AUVState=AUVState.IDLE; path: List[Tuple]=field(default_factory=list)
    comms_range: float=300.0; acoustic_channel: int=0
    def to_dict(self):
        return {"id":self.id,"position":{"x":round(self.x,1),"y":round(self.y,1),"z":round(self.z,1)},
                "heading":round(self.heading,1),"speed":round(self.speed,2),"battery":round(self.battery,1),
                "state":self.state.value,"path_length":len(self.path)}

class AUVFleetSimulator:
    def __init__(self, physics):
        self.physics = physics; self.auvs = {}; self.time = 0.0; self.collisions = 0
    def spawn_fleet(self, count=5, cx=0, cy=0, spread=100, depth=20):
        ids = []
        for i in range(count):
            a = 2*math.pi*i/count
            a = AUV("auv_{}".format(i), cx+spread*math.cos(a), cy+spread*math.sin(a),
                     depth+random.uniform(-5,5), math.degrees(a),
                     1.5+random.uniform(-0.3,0.3), 95+random.uniform(-5,5),
                     AUVState.SURVEY, acoustic_channel=i%3)
            self.auvs[a.id] = a; ids.append(a.id)
        return ids
    def tick(self):
        self.time += 1.0; ev = {"time":self.time,"auv_count":len(self.auvs),"events":[]}
        for a in self.auvs.values():
            if a.state == AUVState.DOCKED: a.battery = min(100, a.battery+2); continue
            try: env = self.physics.compute(a.z, 4.0, 0, 1)
            except: env = {"attenuation":0.05,"temperature":15,"sound_speed":1500}
            if a.path:
                dx,dy,dz = a.path[0][0]-a.x, a.path[0][1]-a.y, a.path[0][2]-a.z
                d = math.sqrt(dx*dx+dy*dy+dz*dz)
                if d < 1: a.path.pop(0)
                elif d > 0:
                    a.x += dx/d; a.y += dy/d; a.z += dz/d
                    a.heading = math.degrees(math.atan2(dy, dx))
            a.battery -= 0.005 + env.get("attenuation",0.05)*0.1
            if a.battery < 10: a.state = AUVState.EMERGENCY
            elif a.battery < 5: a.state = AUVState.RETURN; a.path = [(0,0,5)]
        return ev
    def formation(self, ftype, cx=0, cy=0, spacing=30):
        al = list(self.auvs.values()); n = len(al)
        if ftype == Formation.LINE: offs = [(i*spacing,0,0) for i in range(n)]
        elif ftype == Formation.V: offs = [(i*spacing*0.5,(i%2-0.5)*spacing*(i//2+1),0) for i in range(n)]
        elif ftype == Formation.DIAMOND: offs = [(spacing*(1-0.5*(i%2))*math.cos(2*math.pi*i/n),spacing*(1-0.5*(i%2))*math.sin(2*math.pi*i/n),0) for i in range(n)]
        elif ftype == Formation.GRID: cols=max(2,int(math.sqrt(n))); offs=[(i%cols*spacing,i//cols*spacing,0) for i in range(n)]
        else: offs = [(random.uniform(-spacing,spacing),random.uniform(-spacing,spacing),0) for _ in range(n)]
        for i,a in enumerate(al): a.path = [(cx+offs[i][0],cy+offs[i][1],a.z+offs[i][2])]
    def fleet_summary(self):
        return {"time":round(self.time,1),"count":len(self.auvs),
                "collisions":self.collisions,
                "avg_battery":round(sum(a.battery for a in self.auvs.values())/max(len(self.auvs),1),1)}
    def run_for(self, seconds):
        return [self.tick() for _ in range(int(seconds))]
