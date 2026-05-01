"""Pipeline orchestrator for sonar survey workflows."""
class Pipeline:
    def __init__(self, max_depth=100, chl=5.0, season="summer", sediment="sand"):
        self.env = {}
        sed = {"mud": 0, "sand": 1, "gravel": 2, "rock": 3, "seagrass": 4}.get(sediment, 1)
        sn = 0 if season == "summer" else 1
        for d in range(0, int(max_depth) + 1, 5):
            from .physics import FluxPhysics
            p = FluxPhysics().compute(float(d), chl, sn, sed)
            self.env["d{}".format(d)] = {k: p[k] for k in ["temperature", "sound_speed", "visibility", "absorption"]}

    def get_env(self, depth):
        key = "d{}".format(int(depth // 5) * 5)
        return self.env.get(key, {})
