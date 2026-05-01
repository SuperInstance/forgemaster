"""ASCII visualization and data export for sonar survey data."""
import json


class SonarDisplay:
    """Static display methods: waterfall, ping_table, export_json, survey_summary."""

    NL = "\n"

    @staticmethod
    def waterfall(pings, width=60, height=20):
        if not pings:
            return "[No ping data]"
        vs = [p.get("visibility", p.get("depth", p.get("intensity", 0))) for p in pings]
        vmin, vmax = min(vs), max(vs)
        vr = max(vmax - vmin, 0.001)
        ch = " .:-=+*#%@"
        dv = vs[-width:] if len(vs) > width else vs
        lines = []
        for y in range(height - 1, -1, -1):
            thr = vmin + vr * y / max(height - 1, 1)
            line = ""
            for v in dv:
                if v >= thr:
                    idx = min(int((v - vmin) / vr * (len(ch) - 1)), len(ch) - 1)
                    line += ch[idx]
                else:
                    line += " "
            lines.append(line)
        fmt = "{:.1f}".format(vmax)
        pad = width - len("{:.1f}".format(vmin)) - len(fmt)
        lines.append("{:.1f}{:>{}}{}".format(vmin, "", pad, fmt))
        lines.append("{:^{}}".format("<-- Time -->", width))
        return SonarDisplay.NL.join(lines)

    @staticmethod
    def ping_table(pings, max_rows=20):
        if not pings:
            return "[No ping data]"
        h = "Ping | Depth(m) | Temp(C) | SS(m/s) | Vis(m) | Att(dB)"
        s = "-" * len(h)
        lines = [h, s]
        for i, p in enumerate(pings[:max_rows]):
            lines.append("{:>4} | {:>8.1f} | {:>6.2f} | {:>6.0f} | {:>5.1f} | {:>6.3f}".format(
                i, p.get("depth", 0), p.get("temperature", 0),
                p.get("sound_speed", 0), p.get("visibility", 0),
                p.get("attenuation", 0)))
        if len(pings) > max_rows:
            lines.append("... and {} more".format(len(pings) - max_rows))
        return SonarDisplay.NL.join(lines)

    @staticmethod
    def export_json(data, indent=2):
        return json.dumps(data, indent=indent, default=str)

    @staticmethod
    def survey_summary(mission, pings):
        md = mission.to_dict() if hasattr(mission, "to_dict") else {}
        l = ["Survey: {}".format(md.get("name", "?")),
             "  Waypoints: {}".format(md.get("waypoint_count", len(pings)))]
        if md.get("total_distance_m"):
            l.append("  Distance: {:.0f}m".format(md["total_distance_m"]))
        if pings:
            ts = [p.get("temperature", 0) for p in pings if "temperature" in p]
            vs = [p.get("visibility", 0) for p in pings if "visibility" in p]
            if ts:
                l.append("  Avg Temp: {:.1f}C".format(sum(ts) / len(ts)))
            if vs:
                l.append("  Avg Vis:  {:.1f}m".format(sum(vs) / len(vs)))
        return SonarDisplay.NL.join(l)
