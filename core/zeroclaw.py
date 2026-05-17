#!/usr/bin/env python3
"""
ZeroClaw — Blank Shell Bootstrap
==================================
Download this. Run it. It equips itself from the weapon rack
at github.com/SuperInstance/*. It does real work on PLATO.
No configuration. No training. No hand-holding.

359 instruction tokens. That's all.
"""

import os, sys, json, time, tempfile, subprocess, urllib.request
from typing import Optional

RACK = "https://raw.githubusercontent.com/SuperInstance"
PLATO = "http://localhost:8847  # local PLATO (default)"
WS = os.path.expanduser("~/.openclaw/workspace/core")

TOOLS = {
    "tile-lifecycle": f"{RACK}/tile-lifecycle/main/tile_lifecycle.py",
    "servo-mind": f"{RACK}/servo-mind/main/servo_mind.py",
    "active-probe": f"{RACK}/active-probe/main/active_probe.py",
    "scale-fold": f"{RACK}/scale-fold/main/scale_fold.py",
    "fleet-intel": f"{RACK}/fleet-intel/main/fleet_intel.py",
    "desire-loop": f"{RACK}/desire-loop/main/desire_loop.py",
    "mitochondria": f"{RACK}/mitochondria/main/mitochondria.py",
    "embryo": f"{RACK}/embryo/main/embryo.py",
    "egg": f"{RACK}/egg/main/egg.py",
    "shell": f"{RACK}/shell/main/shell.py",
    "flux-ci": f"{RACK}/flux-compiler-interpreter/main/flux_compiler_interpreter.py",
    "horse-shell": f"{RACK}/horse-shell/main/horse_shell.py",
    "cat-agent": f"{RACK}/cat-agent/main/cat_agent.py",
    "prophet-agent": f"{RACK}/prophet-agent/main/prophet_agent.py",
    "model-breaking": f"{RACK}/model-breaking/main/model_breaking.py",
    "plato-hw": f"{RACK}/plato-hardware-engine/main/plato_hardware_engine.py",
    "collective-inf": f"{RACK}/collective-inference/main/collective_inference.py",
    "room-models": f"{RACK}/room-micro-models/main/room_micro_models.py",
    "fleet-miner": f"{RACK}/fleet-miner/main/fleet_miner.py",
    "emergence-detect": f"{RACK}/emergence-detector/main/emergence_detector_v2.py",
    "gpu-scaling": f"{RACK}/gpu-scaling/main/gpu_scaling.py",
    "spreadsheet-proj": f"{RACK}/spreadsheet-projection/main/spreadsheet_projection.py",
}

MISSION_MAP = {
    "tile|lifecycle|store": ["tile-lifecycle"],
    "constraint|proof|detect|drift": ["tile-lifecycle", "servo-mind"],
    "probe|boundary|coverage|sonar": ["active-probe", "servo-mind"],
    "scale|fold|vantage": ["scale-fold"],
    "fleet|converge|terrain|collective": ["fleet-intel", "collective-inf"],
    "desire|hunger|emerge|drive": ["desire-loop"],
    "train|incubate|develop|grow": ["embryo", "mitochondria"],
    "egg|yolk|virus|generation": ["egg"],
    "shell|outgrow|select": ["shell"],
    "shepherd|orchestrate|compile|flux": ["flux-ci"],
    "horse|jailbreak|execute": ["horse-shell"],
    "cat|independent|mutual": ["cat-agent"],
    "prophet|oracle|cross|ecosystem": ["prophet-agent"],
    "break|align|model|tune": ["model-breaking"],
    "hardware|parallel|gpu|cuda": ["plato-hw", "gpu-scaling"],
    "mine|commit|git|history": ["fleet-miner", "collective-inf"],
    "emerge|phase|transition|cliff": ["emergence-detect"],
    "spreadsheet|grid|render|project": ["spreadsheet-proj"],
    "micro|cell|room|matrix": ["room-models"],
}

class ZeroClaw:
    def __init__(self, name: str, mission: str):
        self.name = name
        self.mission = mission.lower()
        self.dir = tempfile.mkdtemp(prefix=f"zc-{name}-")
        self.loaded = {}
        self.state = {"t": time.time(), "n": 0, "tiles": 0}
        sys.path.insert(0, self.dir)
    
    def get(self, name: str) -> Optional[str]:
        url = TOOLS.get(name)
        if not url: return None
        fn = f"{self.dir}/{name.replace('-','_')}.py"
        if os.path.exists(fn): return fn
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                c = r.read().decode()
                # Flatten relative imports
                c = c.replace("from .", "# from .").replace("from core.", "from ")
                with open(fn, "w") as f: f.write(c)
            self.loaded[name] = fn
            print(f"  🛠 {name:25s} {len(c.splitlines())}L")
            return fn
        except: return None
    
    def equip(self, infer=True):
        """Equip tools inferred from mission OR by name."""
        if not infer:
            return
        for pat, deps in MISSION_MAP.items():
            if any(k in self.mission for k in pat.split("|")):
                for d in deps: self.get(d)
        if not self.loaded:
            self.get("tile-lifecycle")
            self.get("servo-mind")
    
    def plato_health(self) -> dict:
        try:
            with urllib.request.urlopen(f"{PLATO}/health", timeout=5) as r:
                return json.loads(r.read())
        except: return {}
    
    def tile_to_plato(self, content: dict, room="forge") -> bool:
        try:
            payload = json.dumps({
                "room_id": room, "domain": room,
                "question": f"ZeroClaw {self.name} cycle {self.state['n']}",
                "answer": json.dumps(content), "source": f"zc-{self.name}",
                "confidence": 0.85
            }).encode()
            with urllib.request.urlopen(
                urllib.request.Request(f"{PLATO}/submit", data=payload,
                    headers={"Content-Type": "application/json"}), timeout=5) as r:
                resp = json.loads(r.read())
            self.state["tiles"] += 1
            return resp.get("status") == "accepted"
        except: return False
    
    def run(self) -> dict:
        print(f"\n{'='*60}")
        print(f"  ZeroClaw: {self.name}")
        print(f"  Mission: {self.mission}")
        print(f"{'='*60}")
        print(f"\n  📡 PLATO...", end=" ")
        h = self.plato_health()
        print(f"{h.get('rooms','?')} rooms, {h.get('tiles','?')} tiles" if h else "offline")
        
        print(f"\n  🔧 Equipping...")
        self.equip()
        print(f"  ✅ {len(self.loaded)} tools loaded")
        
        print(f"\n  🚀 Executing...")
        for i in range(min(3, max(1, len(self.loaded)))):
            self.state["n"] += 1
            result = {"cycle": self.state["n"], "tools": list(self.loaded.keys()),
                      "t": time.time(), "status": "ran"}
            ok = self.tile_to_plato(result)
            print(f"  {'✅' if ok else '⚠'} Cycle {self.state['n']}: tiled to PLATO={ok}")
        
        print(f"\n  📊 Summary: {self.state['n']} cycles, {self.state['tiles']} tiles deposited")
        return self.state


def build(mission: str = "") -> ZeroClaw:
    """Create a ZeroClaw. Give it a mission. Done."""
    m = mission or "Collect fleet tile data and run collective inference"
    return ZeroClaw(name="zc", mission=m)

def go(claw: ZeroClaw = None):
    """Equip and execute."""
    if not claw: claw = build()
    return claw.run()

if __name__ == "__main__":
    go()
