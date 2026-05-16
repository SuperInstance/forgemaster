"""FLUX to constraint-theory bridge for marine physics planning."""


class ConstraintSnapper:
    def __init__(self, physics):
        self.physics = physics

    def optimal_survey_depth(self, min_d=0, max_d=50, chl=5.0, season=0):
        best = (None, float("inf"))
        for d in range(min_d, max_d + 1):
            p = self.physics.compute(float(d), chl, season, 1)
            score = -p["visibility"] + p["absorption"] * 100
            if score < best[1]:
                best = (d, score)
        p = self.physics.compute(float(best[0]), chl, season, 1)
        return dict(depth=best[0], visibility=p["visibility"],
                    absorption=p["absorption"])


class FLUXCTBridge:
    def __init__(self, physics):
        self.physics = physics

    def snap_profile(self, depth, chl=5.0, season=0, sediment=1):
        p = self.physics.compute(depth, chl, season, sediment)
        return dict(flux_opcode="PHY_ABSORB",
                    execution=dict(depth=p["depth"],
                                   temperature_C=p["temperature"],
                                   sound_speed_ms=p["sound_speed"],
                                   absorption=p["absorption"]),
                    constraint_variables=dict(
                        x=round(depth*0.1, 2),
                        y=round(p["sound_speed"]*0.001, 3),
                        z=round(p["temperature"]*0.05, 3)))


class CSPTranslator:
    def __init__(self, physics):
        self.physics = physics

    def sonar_path_planning(self, depths, chl=5.0, season=0):
        vars_ = []
        for d in depths:
            p = self.physics.compute(d, chl, season, 1)
            vars_.append(dict(var="d{}".format(d), depth=d,
                              temp=p["temperature"]))
        trans = []
        for i in range(1, len(vars_)):
            dz = vars_[i]["depth"] - vars_[i-1]["depth"]
            dt = vars_[i]["temp"] - vars_[i-1]["temp"]
            trans.append(dict(from_=vars_[i-1]["var"], to=vars_[i]["var"],
                              dtdz=round(abs(dt)/max(abs(dz), 1), 3)))
        return dict(variables=vars_, transitions=trans,
                    valid_paths=sum(1 for t in trans if t["dtdz"] < 2),
                    total=len(trans))
