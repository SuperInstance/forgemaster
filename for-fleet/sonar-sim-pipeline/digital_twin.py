#!/usr/bin/env python3
"""SonarVision Digital Twin — full marine environment model.

Combines FLUX physics, ray tracing, fleet simulation, and neural
surrogate into a unified MarineDigitalTwin object. Tracks state
over time, supports what-if queries, and exports to JSON.

Usage:
  python3 digital_twin.py              # Run quick demo
  python3 digital_twin.py --profile    # Full dive profile
  python3 digital_twin.py --fleet 5    # Fleet simulation
  python3 digital_twin.py --twin       # Full digital twin demo
"""

import math, json, sys, os, time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sim_pipeline'))
sys.path.insert(0, os.path.dirname(__file__))

try:
    from sim_pipeline import (
        FluxPhysics, SonarRayTracer, MissionPlanner, SonarDisplay,
        AUVFleetSimulator, FLUXCTBridge, ConstraintSnapper,
        compute_physics, dive_profile
    )
    from sim_pipeline.fleet_sim import Formation
except ImportError:
    FluxPhysics = None


class MarineDigitalTwin:
    """Full marine environment digital twin.

    Tracks oceanographic state across time and depth. Supports
    what-if queries for survey planning, acoustic propagation,
    and multi-agent fleet coordination.
    """

    def __init__(self, max_depth: float = 200.0, chl: float = 5.0,
                 season: str = "summer", sediment: str = "sand",
                 lat: float = 59.5, lon: float = -151.4):
        self.max_depth = max_depth
        self.chl = chl
        self.season = season
        self.sediment = sediment
        self.lat = lat
        self.lon = lon
        self.created_at = datetime.utcnow()

        self.physics = FluxPhysics()
        self.twin = []          # time-series state snapshots
        self.fleet = None
        self.active_mission = None
        self.ray_tracer = SonarRayTracer(max_depth=max_depth, chl=chl,
                                          season=season, sediment=sediment)
        self._cache = {}

    def snapshot(self, depth: float, t: Optional[float] = None) -> Dict:
        """Take a single snapshot of the environment at depth."""
        t = t or time.time()
        env = self.physics.compute(depth, self.chl, self.season, self.sediment)
        env["timestamp"] = t
        env["latitude"] = self.lat
        env["longitude"] = self.lon
        return env

    def profile(self, start: float = 0, end: Optional[float] = None,
                step: float = 5) -> List[Dict]:
        """Full dive profile from start to end."""
        end = end or self.max_depth
        prof = []
        d = start
        while d <= end:
            prof.append(self.snapshot(d))
            d += step
        self._cache["profile"] = prof
        return prof

    def profile_to_csv(self, prof: List[Dict]) -> str:
        """Convert profile to CSV string."""
        if not prof:
            return "# No profile data"
        keys = ["depth", "temperature", "sound_speed", "absorption",
                "scattering", "attenuation", "visibility",
                "seabed_reflectivity", "water_type_name", "sediment"]
        lines = [",".join(keys)]
        for p in prof:
            lines.append(",".join(str(p.get(k, "")) for k in keys))
        return "\n".join(lines)

    def trace_acoustic(self, source_depth: float, target_depth: float,
                       range_m: float, fan: bool = False) -> Dict:
        """Trace acoustic ray from source to target."""
        key = f"ray:{source_depth}:{target_depth}:{range_m}:{fan}"
        if key in self._cache:
            return self._cache[key]
        result = self.ray_tracer.compute_return(source_depth, target_depth, range_m)
        if fan:
            result["fan_scan"] = self.ray_tracer.fan_scan(sd=source_depth, rng=range_m)
        self._cache[key] = result
        return result

    def optimal_depth_range(self) -> Dict:
        """Find optimal survey depth range using constraint snapping."""
        snapper = ConstraintSnapper(self.physics)
        snap = snapper.optimal_survey_depth(max_d=int(self.max_depth))
        return snap

    def plan_mission(self, pattern: str = "lawnmower", width: float = 500,
                     height: float = 200, depth: float = 25, spacing: float = 50) -> Dict:
        """Plan an autonomous survey mission."""
        planner = MissionPlanner(self.physics)
        patterns = {
            "lawnmower": lambda: planner.lawnmover("twin", width, height, depth, spacing),
            "spiral": lambda: planner.spiral("twin", max(width, height)/2, depth),
            "star": lambda: planner.star("twin", max(width, height)/2, depth),
            "perimeter": lambda: planner.perimeter("twin", width, height, depth),
        }
        mission = patterns.get(pattern, patterns["lawnmower"])()
        self.active_mission = mission

        # Simulate pings at each waypoint
        pings = []
        for wp in mission.waypoints:
            p = self.snapshot(wp.depth)
            p["position"] = {"x": wp.x, "y": wp.y}
            pings.append(p)

        return {
            "name": mission.name,
            "pattern": mission.pattern,
            "waypoint_count": len(mission.waypoints),
            "total_distance_m": mission.total_distance(),
            "estimated_duration_s": mission.estimated_duration(),
            "area_width": mission.area_width,
            "area_height": mission.area_height,
            "waterfall": SonarDisplay.waterfall(pings),
            "summary_table": SonarDisplay.ping_table(pings),
        }

    def spawn_fleet(self, count: int = 5, depth: float = 20,
                    spread: float = 100, formation: str = "v") -> Dict:
        """Spawn and simulate AUV fleet."""
        self.fleet = AUVFleetSimulator(self.physics)
        ids = self.fleet.spawn_fleet(count, depth=depth, spread=spread)
        fm = {"line": Formation.LINE, "v": Formation.V,
              "diamond": Formation.DIAMOND, "grid": Formation.GRID,
              "random": Formation.RANDOM}.get(formation, Formation.V)
        self.fleet.formation(fm, spacing=40)
        return {"auvs": ids, "count": len(ids), "formation": formation}

    def run_fleet(self, seconds: int = 60) -> Dict:
        """Run fleet simulation for N seconds."""
        if not self.fleet:
            return {"error": "No fleet spawned"}
        ticks = self.fleet.run_for(seconds)
        summary = self.fleet.fleet_summary()
        summary["ticks"] = ticks
        return summary

    def find_thermocline(self, prof: Optional[List[Dict]] = None) -> Dict:
        """Find the thermocline from a dive profile."""
        prof = prof or self._cache.get("profile", self.profile())
        max_grad = 0
        thermocline = {"depth": 20, "dTdz": 0, "top": 10, "bottom": 30}

        for i in range(1, len(prof)):
            dT = prof[i]["temperature"] - prof[i-1]["temperature"]
            dz = prof[i]["depth"] - prof[i-1]["depth"]
            if dz <= 0: continue
            grad = abs(dT / dz)
            if grad > max_grad:
                max_grad = grad
                thermocline = {
                    "depth": prof[i]["depth"],
                    "dTdz": round(grad, 4),
                    "temperature": prof[i]["temperature"],
                    "sound_speed": prof[i]["sound_speed"],
                    "top": prof[i-1]["depth"],
                    "bottom": prof[i]["depth"],
                }
        thermocline["status"] = "distinct" if max_grad > 0.05 else "weak/mixed"
        return thermocline

    def what_if(self, chl: Optional[float] = None, season: Optional[str] = None,
                sediment: Optional[str] = None) -> Dict:
        """What-if query: change parameters and see effects."""
        old_chl, old_season, old_sed = self.chl, self.season, self.sediment
        self.chl = chl if chl is not None else self.chl
        self.season = season if season is not None else self.season
        self.sediment = sediment if sediment is not None else self.sediment

        prof = self.profile(0, 50, 10)
        optimal = self.optimal_depth_range()
        ray = self.trace_acoustic(10, 50, 100)
        thermocline = self.find_thermocline(prof)

        # Restore
        self.chl, self.season, self.sediment = old_chl, old_season, old_sed
        self.ray_tracer = SonarRayTracer(max_depth=self.max_depth,
                                          chl=self.chl, season=self.season,
                                          sediment=self.sediment)

        return {
            "parameters": {"chl": self.chl, "season": self.season, "sediment": self.sediment},
            "scenario": {"chl": chl, "season": season, "sediment": sediment},
            "optimal_depth_m": optimal.get("depth"),
            "travel_time_s": ray.get("total_travel_time_s"),
            "total_loss_db": ray.get("total_loss_db"),
            "thermocline_depth_m": thermocline.get("depth"),
            "thermocline_dTdz": thermocline.get("dTdz"),
        }

    def to_json(self) -> str:
        """Export full twin state as JSON."""
        prof = self._cache.get("profile", self.profile(0, 50, 10))
        return json.dumps({
            "twin_id": "sonar-vision-twin",
            "version": "1.4.0",
            "created_at": self.created_at.isoformat(),
            "location": {"lat": self.lat, "lon": self.lon},
            "parameters": {
                "max_depth": self.max_depth, "chl": self.chl,
                "season": self.season, "sediment": self.sediment,
            },
            "thermocline": self.find_thermocline(prof),
            "optimal_survey_depth": self.optimal_depth_range(),
            "profile_len": len(prof),
        }, indent=2, default=str)

    def summary(self) -> str:
        """Human-readable summary."""
        prof = self._cache.get("profile", self.profile(0, 50, 10))
        tc = self.find_thermocline(prof)
        opt = self.optimal_depth_range()

        lines = [
            "=" * 50,
            " SonarVision Digital Twin",
            f" Location: {self.lat:.1f}N, {self.lon:.1f}W",
            f" Max Depth: {self.max_depth}m  |  Chl: {self.chl}  |  {self.season} / {self.sediment}",
            f" Profile: {len(prof)} depths (0-{self.max_depth}m)",
            f" Thermocline: {tc['depth']}m ({tc['dTdz']:.3f} C/m) — {tc['status']}",
            f" Optimal Survey: {opt['depth']}m (vis={opt.get('visibility','?')}m)",
            f" Fleet: {'Not spawned' if not self.fleet else f'{len(self.fleet.auvs)} AUVs'}",
            f" Mission: {self.active_mission.name if self.active_mission else 'None'}",
            "=" * 50,
        ]
        return "\n".join(lines)


def demo():
    """Full digital twin demo."""
    twin = MarineDigitalTwin(max_depth=100, chl=4.0, season="summer", sediment="sand")
    print(twin.summary())

    # Profile
    print("\nDive profile (0-50m @10m):")
    prof = twin.profile(0, 50, 10)
    for p in prof:
        print(f"  {p['depth']:6.0f}m | {p['temperature']:6.1f}C | {p['sound_speed']:6.0f}m/s | {p['visibility']:5.1f}m")

    # What-if: fall vs summer
    print("\nWhat-if: Summer → Fall (chl=18, sediment=seagrass):")
    wi = twin.what_if(chl=18, season="summer", sediment="seagrass")
    for k, v in wi["scenario"].items():
        print(f"  {k}: {v}")
    print(f"  Optimal: {wi['optimal_depth_m']}m, Travel: {wi['travel_time_s']}s")

    # Ray trace
    print("\nRay trace (10m → 50m @ 100m range):")
    ray = twin.trace_acoustic(10, 50, 100, fan=True)
    print(f"  Travel: {ray['total_travel_time_s']:.4f}s, Loss: {ray['total_loss_db']:.1f}dB")

    # Fleet
    print("\nFleet (5 AUVs, 30s):")
    twin.spawn_fleet(5, formation="v")
    result = twin.run_fleet(30)
    print(f"  {result['count']} AUVs, {result['avg_battery']:.1f}% avg battery")

    # Mission
    print("\nMission (spiral):")
    mission = twin.plan_mission("spiral", width=200, height=200, depth=15)
    print(f"  Pattern: {mission['pattern']}, {mission['waypoint_count']} wp, {mission['total_distance_m']:.0f}m")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SonarVision Digital Twin")
    parser.add_argument("--demo", action="store_true", default=True)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--fleet", type=int, help="Fleet count to simulate")
    parser.add_argument("--json", action="store_true", help="Export as JSON")
    args = parser.parse_args()

    demo()
