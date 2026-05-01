"""FLUX to constraint-theory bridge."""
from .physics import FluxPhysics

class ConstraintSnapper:
    def __init__(self, physics): self.physics = physics
    def optimal_survey_depth(self, min_d=0, max_d=50, chl=5.0, season=0):
        best = (None, float("inf"))
        for d in range(min_d, max_d+1):
            p = self.physics.compute(float(d), chl, season, 1)
            sc = -p["visibility"] + p["absorption"]*100
            if sc < best[1]: best = (d, sc)
        p = self.physics.compute(float(best[0]), chl, season, 1)
        return {"depth":best[0],"visibility":p["visibility"],"absorption":p["absorption"]}

class FLUXCTBridge:
    def __init__(self, physics): self.physics = physics
    def snap_profile(self, depth, chl=5.0, season=0, sediment=1):
        p = self.physics.compute(depth, chl, season, sediment)
        return {"flux_opcode":"PHY_ABSORB",
                "execution":{"depth":p["depth"],"temperature_C":p["temperature"],
                             "sound_speed_ms":p["sound_speed"],"absorption":p["absorption"],
                             "attenuation":p["attenuation"]},
                "constraint_variables":{"x":round(depth*0.1,2),"y":round(p["sound_speed"]*0.001,3),
                                        "z":round(p["temperature"]*0.05,3)}}

class CSPTranslator:
    def __init__(self, physics): self.physics = physics
    def sonar_path_planning(self, depths, chl=5.0, season=0):
        profs = {}; vars_ = []
        for d in depths:
            p = self.physics.compute(d, chl, season, 1); profs[d] = p
            vars_.append({"var":"d{}".format(d),"depth":d,"temp":p["temperature"]})
        for i in range(1, len(vars_)):
            vars_[i-1]["dtdz"] = round(abs(vars_[i]["temp"]-vars_[i-1]["temp"])/max(abs(vars_[i]["depth"]-vars_[i-1]["depth"]),1),3)
        trans = [{"from":vars_[i-1]["var"],"to":vars_[i]["var"],
                  "dtdz":round(abs(vars_[i]["temp"]-vars_[i-1]["temp"])/max(abs(vars_[i]["depth"]-vars_[i-1]["depth"]),1),3)}
                 for i in range(1, len(vars_))]
        return {"variables":vars_,"transitions":trans,
                "valid_paths":sum(1 for t in trans if t["dtdz"]<2),"total":len(trans)}
