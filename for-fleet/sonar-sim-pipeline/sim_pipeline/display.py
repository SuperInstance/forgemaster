"""ASCII visualization and data export for sonar survey data."""
import json
from typing import List, Dict


class SonarDisplay:
    """Static display methods for sonar data: waterfall, depth profile, ping table, export."""

    @staticmethod
    def waterfall(pings, width=60, height=20):
        """ASCII waterfall display from ping visibility/depth/intensity data."""
        if not pings:
            return "[No ping data]"
        values = [p.get("visibility", p.get("depth", p.get("intensity", 0))) for p in pings]
        vmin, vmax = min(values), max(values)
        vr = max(vmax - vmin, 0.001)
        chars = " .:-=+*#%@"
        dvals = values[-width:] if len(values) > width else values
        lines = []
        for y in range(height - 1, -1, -1):
            thr = vmin + (vr * y / max(height - 1, 1))
            line = "".join(
                chars[min(int((v - vmin) / vr * (len(chars) - 1)), len(chars) - 1)]
                if v >= thr else " " for v in dvals
            )
            lines.append(line)
        lines.append("{:.1f}{:>{}}{:.1f}".format(
            vmin, "", width - len("{:.1f}".format(vmin)) - len("{:.1f}".format(vmax)), vmax))
        lines.append("{:^{}}".format("<-- Time -->", width))
        return "\n".join(lines)

    @staticmethod
    def depth_profile(prof, width=40, height=15):
        """ASCII depth vs temperature profile."""
        if not prof:
            return "[No profile data]"
        temps = [p["temperature"] for p in prof]
        depths = [p["depth"] for p in prof]
        tmin, tmax = min(temps), max(temps)
        tr = max(tmax - tmin, 0.001)
        chars = " .:-=+*#%@"
        lines = []
        for i in range(len(prof) - 1, -1, -1):
            bar_len = int((temps[i] - tmin) / tr * width)
            c = chars[min(int((temps[i] - tmin) / tr * (len(chars) - 1)), len(chars) - 1)]
            lines.append("{:5.0f}m | {:}{:5.1f}C".format(depths[i], c * bar_len, temps[i]))
        return "\n".join(lines)

    @staticmethod
    def ping_table(pings, max_rows=20):
        """Tabular ping data summary."""
        if not pings:
            return "[No ping data]"
        header = "{:>5} | {:>8} | {:>6} | {:>6} | {:>5} | {:>6}".format(
            "Ping", "Depth(m)", "Temp(C)", "SS(m/s)", "Vis(m)", "Att(dB)")
        sep = "-" * len(header)
        lines = [header, sep]
        for i, p in enumerate(pings[:max_rows]):
            lines.append("{:>5} | {:>8.1f} | {:>6.2f} | {:>6.0f} | {:>5.1f} | {:>6.3f}".format(
                i, p.get("depth", 0), p.get("temperature", 0),
                p.get("sound_speed", 0), p.get("visibility", 0), p.get("attenuation", 0)))
        if len(pings) > max_rows:
            lines.append("... and {} more pings".format(len(pings) - max_rows))
        return "\n".join(lines)

    @staticmethod
    def export_json(data, indent=2):
        """Export data as JSON string."""
        return json.dumps(data, indent=indent, default=str)

    @staticmethod
    def survey_summary(mission, pings):
        """Generate human-readable survey summary."""
        md = mission if isinstance(mission, dict) else {}
        if hasattr(mission, 'to_dict'):
            try: md = mission.to_dict()
            except: pass
        lines = [
            "=" * 50,
            " Survey Report: {}".format(md.get("name", "Unnamed")),
            " Waypoints: {}".format(md.get("waypoint_count", len(pings))),
        ]
        if md.get("total_distance_m"):
            lines.append(" Distance:  {:.0f}m".format(md["total_distance_m"]))
        if pings:
            temps = [p.get("temperature", 0) for p in pings if "temperature" in p]
            viss = [p.get("visibility", 0) for p in pings if "visibility" in p]
            if temps:
                lines.append(" Avg Temp:  {:.1f}C".format(sum(temps) / len(temps)))
            if viss:
                lines.append(" Avg Vis:   {:.1f}m".format(sum(viss) / len(viss)))
        lines.append("=" * 50)
        return "\n".join(lines)
