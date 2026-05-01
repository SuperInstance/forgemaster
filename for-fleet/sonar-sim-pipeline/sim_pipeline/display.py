"""ASCII visualization and data export for sonar survey data."""
import math
import json
from typing import List, Dict, Optional
from datetime import datetime


class SonarDisplay:
    """Generate visualizations and exports from sonar ping data."""

    @staticmethod
    def waterfall(pings: List[Dict], width: int = 60, height: int = 20) -> str:
        if not pings:
            return "[No ping data]"
        values = []
        for p in pings:
            val = p.get('intensity', p.get('visibility', p.get('depth', 0)))
            if isinstance(val, (int, float)):
                values.append(val)
        if not values:
            return "[No numeric data]"
        vmin = min(values)
        vmax = max(values)
        vrange = max(vmax - vmin, 0.001)
        chars = ' .:-=+*#%@'
        display_vals = values[-width:] if len(values) > width else values
        lines = []
        for y in range(height - 1, -1, -1):
            row = []
            threshold = vmin + (vrange * y / max(height - 1, 1))
            for v in display_vals:
                if v >= threshold:
                    idx = int((v - vmin) / vrange * (len(chars) - 1))
                    row.append(chars[min(idx, len(chars) - 1)])
                else:
                    row.append(' ')
            lines.append(''.join(row))
        scale_l = '{:.1f}'.format(vmin)
        scale_r = '{:.1f}'.format(vmax)
        scale = scale_l + ' ' * (width - len(scale_l) - len(scale_r)) + scale_r
        lines.append(scale)
        lines.append('{:^{width}}'.format('<-- Time -->', width=width))
        return chr(10).join(lines)

    @staticmethod
    def depth_profile(pings: List[Dict], width: int = 40, height: int = 12) -> str:
        if not pings:
            return "[No ping data]"
        depths = [p.get('depth', 0) for p in pings]
        temps = [p.get('temperature', p.get('sound_speed', 0)) for p in pings]
        if not temps or not depths:
            return "[No depth/temp data]"
        tmin, tmax = min(temps), max(temps)
        trange = max(tmax - tmin, 0.001)
        depth_bins = {}
        for d, t in zip(depths, temps):
            bk = round(d, 0)
            if bk not in depth_bins:
                depth_bins[bk] = []
            depth_bins[bk].append(t)
        depth_avg = {d: sum(vs)/len(vs) for d, vs in depth_bins.items()}
        sorted_depths = sorted(depth_avg.keys())
        chars = ' _~+=*#%@'
        lines = []
        for d in sorted_depths[:height]:
            t = depth_avg[d]
            idx = int((t - tmin) / trange * (len(chars) - 1))
            bar = chars[min(idx, len(chars) - 1)] * min(width, 20)
            lines.append('{:5.0f}m |{} {:.1f}'.format(d, bar, t))
        return chr(10).join(lines)

    @staticmethod
    def ping_table(pings: List[Dict], max_rows: int = 20) -> str:
        if not pings:
            return "[No ping data]"
        keys = ['depth', 'temperature', 'sound_speed', 'visibility',
                'absorption', 'seabed_reflectivity']
        sep = '-' * 60
        lines = [sep]
        lines.append('{:>6} {:>6} {:>7} {:>6} {:>7} {:>7}'.format(
            'Depth', 'Temp', 'Sound', 'Vis', 'Abs', 'Seabed'))
        lines.append(sep)
        for ping in pings[:max_rows]:
            vals = []
            for k in keys:
                v = ping.get(k, 0)
                vals.append(v)
            lines.append('{:6.1f}m {:6.1f}C {:7.0f}m/s {:6.1f}m {:7.4f} {:7.3f}'.format(*vals))
        if len(pings) > max_rows:
            lines.append('  ... and {} more rows'.format(len(pings) - max_rows))
        lines.append(sep)
        lines.append('  Total: {} pings'.format(len(pings)))
        return chr(10).join(lines)

    @staticmethod
    def export_json(pings: List[Dict], filepath: str,
                    metadata: Optional[Dict] = None):
        export = {
            'exported_at': datetime.utcnow().isoformat(),
            'ping_count': len(pings),
        }
        if metadata:
            export['mission'] = metadata
        export['pings'] = pings
        with open(filepath, 'w') as f:
            json.dump(export, f, indent=2)
        return filepath

    @staticmethod
    def survey_summary(pings: List[Dict], mission_name: str = "Survey") -> str:
        if not pings:
            return "=== {} ===\n  No data collected.\n".format(mission_name)
        depths = [p.get('depth', 0) for p in pings]
        temps = [p.get('temperature', 0) for p in pings]
        speeds = [p.get('sound_speed', 0) for p in pings]
        lines = ["=== {} ===".format(mission_name)]
        lines.append('  Pings:      {}'.format(len(pings)))
        lines.append('  Depth:      {:.0f} - {:.0f}m'.format(min(depths), max(depths)))
        if temps:
            lines.append('  Temp:       {:.1f} - {:.1f}C'.format(min(temps), max(temps)))
        if speeds:
            lines.append('  Sound:      {:.0f} - {:.0f} m/s'.format(min(speeds), max(speeds)))
        return chr(10).join(lines)
