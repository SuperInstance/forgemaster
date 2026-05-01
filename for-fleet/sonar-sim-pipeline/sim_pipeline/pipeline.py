"""Pipeline orchestrator."""
from .physics import FluxPhysics

class Pipeline:
    def __init__(self, max_depth=100.0, chl=5.0, season="summer", sediment="sand"):
        self.physics = FluxPhysics()
        si = {"mud":0,"sand":1,"gravel":2,"rock":3,"seagrass":4}.get(sediment,1)
        sn = 0 if season == "summer" else 1; self.chl = chl; self.max_depth = max_depth
        self.environment = {}
        for d in range(0, int(max_depth)+1, 5):
            p = self.physics.compute(float(d), chl, sn, si)
            self.environment["d{}".format(d)] = {k:p[k] for k in ["temperature","sound_speed","visibility","absorption"]}
