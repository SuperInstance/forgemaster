"""ASCII visualization and data export for sonar survey data."""
import json
from datetime import datetime
from typing import Dict, List, Optional

class SonarDisplay:
    @staticmethod
    def waterfall(pings, width=60, height=20):
        if not pings: return "[No ping data]"
        values = [p.get("intensity",p.get("visibility",p.get("depth",0))) for p in pings]
        vmin,vmax=min(values),max(values); vr=max(vmax-vmin,0.001)
        chars=" .:-=+*#%@"
        dvals=values[-width:] if len(values)>width else values
        lines=[]
        for y in range(height-1,-1,-1):
            thr=vmin+(vr*y/max(height-1,1))
            lines.append("".join(
                chars[min(int((v-vmin)/vr*(len(chars)-1)),len(chars)-1)] if v>=thr else " "
                for v in dvals))
        L=len("{:.1f}".format(vmin)); R=len("{:.1f}".format(vmax))
        lines.append("{:.1f}{:>{}}{:.1f}".format(vmin,"",width-L-R,vmax))
        lines.append("{:^{}}".format("<-- Time -->",width))
        return "\n".join(lines)

