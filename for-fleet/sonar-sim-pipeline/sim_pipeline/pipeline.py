"""Pipeline orchestrator — ties physics, ray tracing, missions, and display."""
import json
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

from .physics import FluxPhysics
from .display import SonarDisplay


class Pipeline:
    """Full sonar simulation pipeline: mission -> physics -> ray trace -> display."""

    def __init__(self, max_depth: float = 100.0, chl: float = 5.0,
                 season: str = 'summer', sediment: str = 'sand'):
        self.max_depth = max_depth
        self.chl = chl
        self.season = 0 if season == 'summer' else 1
        self.season_name = season
        self.sediment = sediment
        self.sed_idx = {'mud': 0, 'sand': 1, 'gravel': 2, 'rock': 3,
                        'seagrass': 4}.get(sediment, 1)
        self.physics = FluxPhysics()
        self.display = SonarDisplay()
        self.environment = self._compute_env()

    def _compute_env(self) -> Dict:
        env = {}
        step = 5
        for d in range(0, int(self.max_depth) + 1, step):
            p = self.physics.compute(float(d), chl=self.chl,
                                     season=self.season,
                                     sediment=self.sed_idx)
            env['d{}'.format(d)] = {
                'temperature': p['temperature'],
                'sound_speed': p['sound_speed'],
                'visibility': p['visibility'],
                'absorption': p['absorption'],
            }
        return env

    def survey_summary(self, results: Dict, mission_name: str = "Survey") -> str:
        pings = results.get('pings', [])
        if not pings:
            return "=== {} ===\n  No data collected.\n".format(mission_name)
        depths = [p.get('depth', p.get('position', {}).get('depth', 0)) for p in pings]
        temps = [p.get('temperature', p.get('environment', {}).get('temperature', 0)) for p in pings]
        speeds = [p.get('sound_speed', p.get('environment', {}).get('sound_speed', 0)) for p in pings]
        lines = ["=== {} ===".format(mission_name)]
        lines.append('  Pings:      {}'.format(len(pings)))
        lines.append('  Depth:      {:.0f} - {:.0f}m'.format(min(depths), max(depths)))
        if temps:
            lines.append('  Temp:       {:.1f} - {:.1f}C'.format(min(temps), max(temps)))
        if speeds:
            lines.append('  Sound:      {:.0f} - {:.0f} m/s'.format(min(speeds), max(speeds)))
        return '\n'.join(lines)

    def export(self, results: Dict, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Exported to %s", filepath)
        return filepath
