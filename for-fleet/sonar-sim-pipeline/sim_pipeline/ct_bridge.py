"""FLUX to constraint-theory bridge for marine physics extension."""
from .physics import FluxPhysics, SEDIMENT_REFLECT, SEDIMENT_NAMES

class ConstraintSnapper:
    def __init__(self, physics): self.physics = physics
    def depth_constraint_csp(self, max_depth=100, target_temp=15.0, target_speed=1500.0):
        res = []
        for d in range(max_depth+1):
            p = self.physics.compute(float(d), 4.0, 0, 1)
            if abs(p["temperature"]-target_temp)<2 and abs(p["sound_speed"]-target_speed)<10:
                res.append({"depth":d,"temperature":p["temperature"],"sound_speed":p["sound_speed"],
                            "cost":abs(p["temperature"]-target_temp)+abs(p["sound_speed"]-target_speed)*0.2})
        return sorted(res, key=lambda x:x["cost"])
    def optimal_survey_depth(self, min_d=0, max_d=50, chl=5.0, season=0):
        best = (None, float("inf"))
        for d in range(min_d, max_d+1):
            p = self.physics.compute(float(d), chl, season, 1)
            sc = -p["visibility"] + p["absorption"]*100
            if sc < best[1]: best = (d, sc)
        p = self.physics.compute(float(best[0]), chl, season, 1)
        return {"depth":best[0],"visibility":p["visibility"],"absorption":p["absorption"]}

class CSPTranslator:
    def __init__(self, physics): self.physics = physics
    def sonar_path_planning(self, depths, chl=5.0, season=0):
        profs = {}; vars_ = []
        for d in depths:
            p = self.physics.compute(d, chl, season, 1); profs[d] = p
            vars_.append({"var":"d{}".format(d),"depth":d,"temp":p["temperature"],
                          "speed":p["sound_speed"],"vis":p["visibility"],"absorption":p["absorption"]})
        for i in range(1,len(vars_)):
            dtdz = abs(vars_[i]["temp"]-vars_[i-1]["temp"])/max(abs(vars_[i]["depth"]-vars_[i-1]["depth"]),1)
            vars_[i-1]["dtdz"] = round(dtdz,3)
        trans = [{"from":vars_[i-1]["var"],"to":vars_[i]["var"],
                  "dtdz":round(abs(vars_[i]["temp"]-vars_[i-1]["temp"])/max(abs(vars_[i]["depth"]-vars_[i-1]["depth"]),1),3)}
                 for i in range(1,len(vars_))]
        return {"variables":vars_,"transitions":trans,
                "valid_paths":sum(1 for t in trans if t["dtdz"]<2),"total_transitions":len(trans)}

class FLUXCTBridge:
    def __init__(self, physics): self.physics = physics
    def snap_profile(self, depth, chl=5.0, season=0, sediment=1):
        p = self.physics.compute(depth, chl, season, sediment)
        return {"flux_opcode":"PHY_ABSORB",
                "execution":{"depth":p["depth"],"temperature_C":p["temperature"],
                             "sound_speed_ms":p["sound_speed"],"absorption":p["absorption"],
                             "attenuation":p["attenuation"]},
                "constraint_variables":{"x":round(depth*0.1,2),"y":round(p["sound_speed"]*0.001,3),
                                        "z":round(p["temperature"]*0.05,3)},
                "miller_equivalent":{"mill":round(p["absorption"]*1000,1),"cylinder":round(p["visibility"],1),
                                     "cone":round(p["seabed_reflectivity"]*100,1)}}
    def multi_depth_snap(self, start=0, end=100, step=5, chl=5.0, season=0, sediment=1):
        return [self.snap_profile(float(d), chl, season, sediment) for d in range(start, end+1, step)]
