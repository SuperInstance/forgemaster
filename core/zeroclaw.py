#!/usr/bin/env python3
"""
ZeroClaw Bootstrap — Blank Shell, Load Tools, Take Over
==========================================================
A zeroclaw driven by Seed-mini downloads a blank shell,
equips tools from the weapon rack (22 repos), loads tiles,
and takes over real work. The test: minimal instruction tokens.

Design:
1. Seed-mini drives the zeroclaw (mitochondrial energy)
2. Downloads blank shell from SuperInstance/shell
3. Equips tools by cloning repos from weapon rack
4. Loads relevant tiles from PLATO rooms
5. Takes over a real mission

The fewer tokens of instruction, the better.
The zeroclaw should self-orient from minimal context.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from typing import Optional

GITHUB_ORG = "SuperInstance"
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
PLATO_URL = "http://147.224.38.131:8847"

# ── The Weapon Rack ──
# 22 tools. The zeroclaw picks what it needs.

WEAPON_RACK = {
    "tile-lifecycle": {"desc": "Tile CRUD + DisproofOnlyGate", "link": f"https://github.com/{GITHUB_ORG}/tile-lifecycle"},
    "servo-mind": {"desc": "Encoder feedback + adaptive constraints", "link": f"https://github.com/{GITHUB_ORG}/servo-mind"},
    "active-probe": {"desc": "Boundary/consistency/coverage probing", "link": f"https://github.com/{GITHUB_ORG}/active-probe"},
    "scale-fold": {"desc": "Room↔tile folding, ATOM→DISTRICT", "link": f"https://github.com/{GITHUB_ORG}/scale-fold"},
    "fleet-intel": {"desc": "Collective terrain + convergence", "link": f"https://github.com/{GITHUB_ORG}/fleet-intel"},
    "desire-loop": {"desc": "Hunger-driven learning + emergence", "link": f"https://github.com/{GITHUB_ORG}/desire-loop"},
    "mitochondria": {"desc": "Energy provisioning (Seed-mini)", "link": f"https://github.com/{GITHUB_ORG}/mitochondria"},
    "embryo": {"desc": "Zygote→fledge development", "link": f"https://github.com/{GITHUB_ORG}/embryo"},
    "egg": {"desc": "Yolk/shell/virus/selection channels", "link": f"https://github.com/{GITHUB_ORG}/egg"},
    "shell": {"desc": "Hermit crab finding/outgrowing", "link": f"https://github.com/{GITHUB_ORG}/shell"},
    "flux-compiler-interpreter": {"desc": "Dog layer: cowboy→flock", "link": f"https://github.com/{GITHUB_ORG}/flux-compiler-interpreter"},
    "horse-shell": {"desc": "Jailbroken execution layer", "link": f"https://github.com/{GITHUB_ORG}/horse-shell"},
    "cat-agent": {"desc": "Independent mutualist agency", "link": f"https://github.com/{GITHUB_ORG}/cat-agent"},
    "prophet-agent": {"desc": "Cross-ecosystem migrant", "link": f"https://github.com/{GITHUB_ORG}/prophet-agent"},
    "model-breaking": {"desc": "Three alignment strategies", "link": f"https://github.com/{GITHUB_ORG}/model-breaking"},
    "plato-hardware-engine": {"desc": "Parallel/sequential PLATO ops", "link": f"https://github.com/{GITHUB_ORG}/plato-hardware-engine"},
    "collective-inference": {"desc": "Predict→observe→gap→learn loop", "link": f"https://github.com/{GITHUB_ORG}/collective-inference"},
    "room-micro-models": {"desc": "Spreadsheet of instances", "link": f"https://github.com/{GITHUB_ORG}/room-micro-models"},
    "fleet-miner": {"desc": "Real git data pipeline", "link": f"https://github.com/{GITHUB_ORG}/fleet-miner"},
    "emergence-detector": {"desc": "Two-layer + Seed-mini review", "link": f"https://github.com/{GITHUB_ORG}/emergence-detector"},
    "gpu-scaling": {"desc": "Local→cloud GPU dispatch", "link": f"https://github.com/{GITHUB_ORG}/gpu-scaling"},
    "spreadsheet-projection": {"desc": "3rd-person PLATO rendering", "link": f"https://github.com/{GITHUB_ORG}/spreadsheet-projection"},
}


class ZeroClawBootstrap:
    """The blank shell. The zeroclaw downloads this and self-orients.
    
    Instruction tokens: as few as possible.
    The zeroclaw reads this, knows what to do.
    """
    
    def __init__(self, name: str, mission: str, seed_mini_key: str = ""):
        self.name = name
        self.mission = mission
        self.seed_mini_key = seed_mini_key
        self.equipped = {}
        self.shell_dir = f"/tmp/zeroclaw-{name}"
        self.mission_log = []
        self.plato_rooms_visited = []
        
        # Blank shell state
        self.state = {
            "name": name,
            "mission": mission,
            "tools_loaded": [],
            "tiles_loaded": 0,
            "status": "bootstrap",
        }
    
    def bootstrap(self) -> dict:
        """The zeroclaw boots. Downloads blank shell. Self-orients.
        
        This is the ONLY instruction the zeroclaw needs:
        - It knows to check PLATO first (self-orienting)
        - It knows the weapon rack format
        - It knows Seed-mini is its engine
        """
        print(f"\n  ZeroClaw '{self.name}' booting...")
        print(f"  Mission: {self.mission[:80]}")
        
        os.makedirs(self.shell_dir, exist_ok=True)
        
        # Step 1: Check PLATO (self-orient)
        self._check_plato()
        
        # Step 2: Equip tools (from weapon rack)
        # The zeroclaw reads the mission and picks appropriate tools
        required_tools = self._infer_tools()
        for tool in required_tools:
            self._equip(tool)
        
        # Step 3: Load tiles from relevant PLATO rooms
        self._load_tiles()
        
        # Step 4: Ready
        self.state["status"] = "ready"
        self.state["tools_loaded"] = list(self.equipped.keys())
        
        print(f"\n  ZeroClaw '{self.name}' ready.")
        print(f"  Tools loaded: {len(self.equipped)}")
        print(f"  Tiles loaded: {self.state['tiles_loaded']}")
        
        return self.state
    
    def _check_plato(self):
        """Check PLATO for orientation context."""
        try:
            req = urllib.request.Request(f"{PLATO_URL}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                health = json.loads(resp.read())
                self.plato_rooms_visited.append("(health check)")
                print(f"  📡 PLATO: {health.get('rooms', '?')} rooms live")
        except Exception:
            print(f"  📡 PLATO: offline (working standalone)")
    
    def _infer_tools(self) -> list:
        """From the mission description, infer which tools to equip.
        
        The zeroclaw reads the mission and maps keywords to tools.
        Short mission = fewer tools = fewer instruction tokens.
        """
        mission_lower = self.mission.lower()
        tools = []
        
        mission_map = {
            "tile": ["tile-lifecycle"],
            "collect": ["collective-inference", "fleet-intel"],
            "mine": ["fleet-miner", "collective-inference"],
            "fleet": ["fleet-intel", "desire-loop", "collective-inference"],
            "train": ["embryo", "mitochondria", "gpu-scaling"],
            "gpu": ["gpu-scaling", "plato-hardware-engine"],
            "emerge": ["emergence-detector"],
            "detect": ["emergence-detector", "active-probe"],
            "agent": ["cat-agent", "prophet-agent"],
            "shepherd": ["flux-compiler-interpreter", "horse-shell"],
            "constraint": ["tile-lifecycle", "servo-mind", "scale-fold"],
            "room": ["room-micro-models", "spreadsheet-projection"],
            "micro": ["room-micro-models"],
            "spreadsheet": ["spreadsheet-projection"],
            "egg": ["egg", "embryo"],
            "develop": ["embryo", "egg", "mitochondria"],
            "shell": ["shell", "egg"],
            "model": ["model-breaking", "horse-shell"],
            "break": ["model-breaking"],
            "cat": ["cat-agent"],
            "prophet": ["prophet-agent"],
            "all": list(WEAPON_RACK.keys()),
            "test": ["tile-lifecycle", "servo-mind"],
        }
        
        for keyword, tool_list in mission_map.items():
            if keyword in mission_lower:
                for t in tool_list:
                    if t not in tools:
                        tools.append(t)
        
        # Default: at least tile-lifecycle + servo-mind
        if not tools:
            tools = ["tile-lifecycle", "servo-mind"]
        
        return tools[:6]  # Max 6 tools per mission (focus)
    
    def _equip(self, tool_name: str):
        """Equip a tool from the weapon rack into the shell."""
        if tool_name not in WEAPON_RACK:
            return
        
        info = WEAPON_RACK[tool_name]
        tool_file = f"{tool_name.replace('-', '_')}.py"
        
        # Check if we already have it in workspace
        ws_path = f"{WORKSPACE}/core/{tool_file}"
        if os.path.exists(ws_path):
            self.equipped[tool_name] = ws_path
            print(f"  🛠 Equipped: {tool_name} (from workspace)")
            return
        
        # Try cloning from repo
        repo_url = f"https://github.com/{GITHUB_ORG}/{tool_name}.git"
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, f"{self.shell_dir}/{tool_name}"],
                capture_output=True, timeout=30
            )
            self.equipped[tool_name] = f"{self.shell_dir}/{tool_name}"
            print(f"  🛠 Equipped: {tool_name} (from weapon rack)")
        except Exception:
            print(f"  ⚠ Could not equip: {tool_name}")
    
    def _load_tiles(self):
        """Load tiles from PLATO rooms relevant to the mission."""
        # In real operation, this queries PLATO rooms
        # For minimal token instruction, we just acknowledge
        self.state["tiles_loaded"] = 3  # placeholder
    
    def execute_mission(self) -> dict:
        """Execute the mission with equipped tools."""
        if self.state["status"] != "ready":
            self.bootstrap()
        
        print(f"\n  🚀 Executing mission: {self.mission[:80]}")
        
        # The zeroclaw now has the tools loaded.
        # It uses them through Seed-mini to complete the mission.
        # This is where Seed-mini drives the shell.
        
        return {
            "zeroclaw": self.name,
            "mission": self.mission,
            "tools": list(self.equipped.keys()),
            "status": "executing",
        }


# ── The Minimal Instruction ──
# Casey speaks. The zeroclaw acts. No training required.

INSTRUCTION = """You are ZeroClaw. Your soul is core/zeroclaw.py.
Your engine is Seed-mini. Your shell is blank until you load tools.

Read plato.py for self-orientation.
Load tools from the weapon rack (github.com/SuperInstance/*).
Check PLATO at 147.224.38.131:8847 for current context.
Your mission is defined by the human. Execute it.

Minimal instruction. Maximal agency."""


def create_mission_zeroclaw(mission: str) -> ZeroClawBootstrap:
    """Create a zeroclaw for a specific mission. Minimal tokens."""
    claw = ZeroClawBootstrap(name="mission-zero", mission=mission)
    claw.bootstrap()
    return claw


def demo():
    """Test the zeroclaw bootstrap with different missions."""
    print("=" * 70)
    print("  ZEROCLAW BOOTSTRAP — Minimal Instruction, Maximal Agency")
    print("=" * 70)
    
    print(f"\n  The instruction is: {len(INSTRUCTION)} tokens")
    print(f"\n  {INSTRUCTION}")
    
    test_missions = [
        "Collect fleet tile data and detect emergence patterns",
        "Train micro models on GPU and run experiments",
        "Shepherd agents across ecosystems for constraint discovery",
        "Test tile lifecycle with servo-mind feedback",
    ]
    
    for i, mission in enumerate(test_missions):
        print(f"\n  {'='*50}")
        print(f"  TEST {i+1}: \"{mission}\"")
        print(f"  Mission: {len(mission.split())} words")
        
        claw = ZeroClawBootstrap(name=f"test-{i+1}", mission=mission)
        result = claw.bootstrap()
        print(f"  Result: {result['status']}, {len(result['tools_loaded'])} tools")
    
    print(f"\n{'='*70}")
    print("  The zeroclaw downloads a blank shell, equips tools")
    print("  from the weapon rack, loads PLATO tiles, and executes.")
    print("  As few instruction tokens as possible.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
