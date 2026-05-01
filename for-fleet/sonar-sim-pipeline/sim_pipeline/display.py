"""ASCII visualization and data export for sonar survey data."""
import json
from datetime import datetime
from typing import Dict, List, Optional

class SonarDisplay:
    @staticmethod
    def waterfall(pings: List[Dict], width: int = 60, height: int = 20) -> str:
        if not pings: return "[No ping data]"
        values = [p.get("intensity", p.get("visibility", p.get("depth", 0))) for p in pings]
        vmin, vmax = min(values), max(values); vr = max(vmax - vmin, 0.001)
        chars = " .:-=+*#%@"
        dvals = values[-width:] if len(values) > width else values
        lines = []
        for y in range(height - 1, -1, -1):
            thr = vmin + (vr * y / max(height - 1, 1))
            lines.append("".join(
                chars[min(int((v-vmin)/vr*(len(chars)-1)), len(chars)-1)] if v >= thr else " "
                for v in dvals))
        lines.append("{:.1f}{:>{}}{:.1f}".format(vmin, "", width-len("{:.1f}".format(vmin))-len("{:.1f}".format(vmax)), vmax))
        lines.append("{:^{}}".format("<-- Time -->", width))
        return chr(10).join(lines)
    @staticmethod
    def depth_profile(pings: List[Dict], height: int = 12) -> str:
        if not pings: return "[No ping data]"
        depths, temps = [p.get("depth", 0) for p in pings], [p.get("temperature", p.get("sound_speed", 0)) for p in pings]
        if not temps: return "[No data]"
        tmin, tmax = min(temps), max(temps); tr = max(tmax - tmin, 0.001)
        bins = {}
        for d, t in zip(depths, temps): bins.setdefault(round(d, 0), []).append(t)
        avgs = {d: sum(vs)/len(vs) for d, vs in bins.items()}
        chars = " _~+=*#%@"
        return chr(10).join(
            "{:5.0f}m |{} {:.1f}".format(d, chars[min(int((avgs[d]-tmin)/tr*(len(chars)-1)), len(chars)-1)]*20, avgs[d])
            for d in sorted(avgs)[:height])
    @staticmethod
    def ping_table(pings: List[Dict], max_rows: int = 20) -> str:
        if not pings: return "[No ping data]"
        keys = ["depth","temperature","sound_speed","visibility","absorption","seabed_reflectivity"]
        sep = "-" * 60
        lines = [sep, "{:>6} {:>6} {:>7} {:>6} {:>7} {:>7}".format(*keys), sep]
        for p in pings[:max_rows]:
            lines.append("{:6.1f}m {:6.1f}C {:7.0f}m/s {:6.1f}m {:7.4f} {:7.3f}".format(
                *(p.get(k,0) for k in keys)))
        if len(pings) > max_rows: lines.append("  ... and {} more rows".format(len(pings)-max_rows))
        lines.extend([sep, "  Total: {} pings".format(len(pings))])
        return chr(10).join(lines)
    @staticmethod
    def survey_summary(pings: List[Dict], name: str = "Survey") -> str:
        if not pings: return "=== {} ===\n  No data collected.\n".format(name)
        depths = [p.get("depth",0) for p in pings]
        temps = [p.get("temperature",0) for p in pings]
        speeds = [p.get("sound_speed",0) for p in pings]
        lines = ["=== {} ===".format(name), "  Pings:      {}".format(len(pings)),
                 "  Depth:      {:.0f} - {:.0f}m".format(min(depths), max(depths))]
        if temps: lines.append("  Temp:       {:.1f} - {:.1f}C".format(min(temps), max(temps)))
        if speeds: lines.append("  Sound:      {:.0f} - {:.0f} m/s".format(min(speeds), max(speeds)))
        return chr(10).join(lines)
    @staticmethod
    def to_json(pings: List[Dict], filepath: str, meta: Optional[Dict]=None) -> str:
        exp = {"exported_at": datetime.utcnow().isoformat(), "ping_count": len(pings)}
        if meta: exp["mission"] = meta
        exp["pings"] = pings
        with open(filepath, "w") as f: json.dump(exp, f, indent=2)
        return filepath
