"""
Fleet Registry — The Rosetta Stone

Every agent reads this on boot. Maps agent names to rooms, capabilities,
task inboxes, and VERIFIED status. Based on A2A Agent Cards + ACG verification.

Architecture: ARCHITECTURE-IRREDUCIBLE.md Layer 1 (Discovery)
Evidence: Exp 4 (registry 2.5/3), Campaign A (80% claims fail without VERIFY)
"""

import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class VerificationStatus(Enum):
    CLAIMED = "claimed"        # Agent said it can do this — NOT verified
    TESTED = "tested"          # Ran concrete tests
    CROSS_VERIFIED = "cross_verified"  # Other agents confirmed
    FIELD_PROVEN = "field_proven"      # Used in production successfully


class CapabilityLevel(Enum):
    NONE = 0        # Cannot do this
    BASIC = 1       # Can do simple tasks (<50% accuracy)
    COMPETENT = 2   # Can do standard tasks (50-80%)
    EXPERT = 3      # Can do complex tasks (>80%)


@dataclass
class Capability:
    """A single agent capability with verification trail"""
    name: str
    status: VerificationStatus = VerificationStatus.CLAIMED
    level: CapabilityLevel = CapabilityLevel.NONE
    test_pass_rate: float = 0.0
    test_count: int = 0
    cross_verified_by: list = field(default_factory=list)
    last_verified: Optional[float] = None
    caveats: list = field(default_factory=list)
    
    def to_dict(self):
        d = asdict(self)
        d['status'] = self.status.value
        d['level'] = self.level.value
        return d
    
    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d['status'] = VerificationStatus(d['status'])
        d['level'] = CapabilityLevel(d['level'])
        return cls(**d)


@dataclass
class AgentCard:
    """
    Verified Agent Card — the fleet's identity and capability record.
    
    A2A Agent Card format adapted for PLATO:
    - Identity: who am I, where do I live
    - Capabilities: what can I do (with verification status)
    - Routing: where to send tasks, how to reach me
    - Terrain: my E12 position in knowledge space
    """
    # Identity
    name: str
    role: str
    description: str
    
    # PLATO routing
    room: str                    # Primary PLATO room
    task_inbox: str              # Room for incoming tasks
    bridge_channel: Optional[str] = None  # Matrix channel if any
    
    # Terrain position
    terrain_a: int = 0           # E12(a,b) coordinate
    terrain_b: int = 0
    
    # Capabilities (verified)
    capabilities: list = field(default_factory=list)  # List of Capability dicts
    
    # Runtime info
    model: Optional[str] = None
    host: Optional[str] = None
    heartbeat_interval: int = 60  # seconds
    
    # Metadata
    created: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    def add_capability(self, cap: Capability):
        """Add or update a capability"""
        for i, existing in enumerate(self.capabilities):
            if isinstance(existing, dict) and existing.get('name') == cap.name:
                self.capabilities[i] = cap.to_dict()
                return
            elif hasattr(existing, 'name') and existing.name == cap.name:
                self.capabilities[i] = cap.to_dict()
                return
        self.capabilities.append(cap.to_dict())
    
    def get_verified_capabilities(self) -> list:
        """Return only capabilities with TESTED or better status"""
        result = []
        for cap_data in self.capabilities:
            if isinstance(cap_data, dict):
                status = cap_data.get('status', 'claimed')
                if status in ('tested', 'cross_verified', 'field_proven'):
                    result.append(cap_data)
        return result
    
    def can_perform(self, capability_name: str, min_level: int = 1) -> bool:
        """Check if agent can perform a capability at minimum level"""
        for cap_data in self.capabilities:
            name = cap_data.get('name') if isinstance(cap_data, dict) else getattr(cap_data, 'name', None)
            if name == capability_name:
                level = cap_data.get('level', 0) if isinstance(cap_data, dict) else getattr(cap_data, 'level', 0)
                status = cap_data.get('status', 'claimed') if isinstance(cap_data, dict) else getattr(cap_data, 'status', 'claimed')
                return level >= min_level and status != 'claimed'
        return False
    
    def to_tile(self) -> dict:
        """Serialize as a PLATO tile"""
        return {
            "question": f"AGENT CARD — {self.name}",
            "answer": json.dumps({
                "name": self.name,
                "role": self.role,
                "description": self.description,
                "room": self.room,
                "task_inbox": self.task_inbox,
                "bridge_channel": self.bridge_channel,
                "terrain": {"a": self.terrain_a, "b": self.terrain_b},
                "capabilities": self.capabilities,
                "model": self.model,
                "host": self.host,
                "last_seen": self.last_seen,
            }, indent=2),
            "metadata": {
                "type": "agent_card",
                "agent": self.name,
            }
        }
    
    def to_dict(self):
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "room": self.room,
            "task_inbox": self.task_inbox,
            "bridge_channel": self.bridge_channel,
            "terrain_a": self.terrain_a,
            "terrain_b": self.terrain_b,
            "capabilities": self.capabilities,
            "model": self.model,
            "host": self.host,
            "created": self.created,
            "last_seen": self.last_seen,
        }
    
    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class FleetRegistry:
    """
    The fleet directory. Maps agent names to Agent Cards.
    
    Layer 1 of the architecture. Every agent reads on boot.
    Routes tasks to agents based on VERIFIED capabilities.
    """
    
    def __init__(self):
        self.agents: dict[str, AgentCard] = {}
    
    def register(self, card: AgentCard):
        """Register or update an agent"""
        self.agents[card.name] = card
    
    def find_agent(self, capability: str, min_level: int = 1, verified_only: bool = True) -> list[AgentCard]:
        """
        Find agents with a specific capability.
        
        Evidence (Exp 4): Registry-based discovery scores 2.5/3.
        This is the primary discovery mechanism.
        """
        results = []
        for agent in self.agents.values():
            if verified_only:
                if agent.can_perform(capability, min_level):
                    results.append(agent)
            else:
                # Check declared (unverified) too
                for cap_data in agent.capabilities:
                    name = cap_data.get('name') if isinstance(cap_data, dict) else getattr(cap_data, 'name', None)
                    if name == capability:
                        level = cap_data.get('level', 0) if isinstance(cap_data, dict) else getattr(cap_data, 'level', 0)
                        if level >= min_level:
                            results.append(agent)
                            break
        return results
    
    def find_nearest(self, capability: str, terrain_a: int, terrain_b: int, min_level: int = 1) -> list[AgentCard]:
        """
        Find agents with capability, sorted by terrain proximity.
        
        Evidence (Exp 4 + Campaign C): Registry first, terrain as tiebreaker.
        Only use terrain when multiple agents match on capability.
        """
        agents = self.find_agent(capability, min_level)
        if len(agents) <= 1:
            return agents
        
        # Sort by hex distance
        def hex_dist(agent):
            da = agent.terrain_a - terrain_a
            db = agent.terrain_b - terrain_b
            return max(abs(da), abs(db), abs(da + db))
        
        agents.sort(key=hex_dist)
        return agents
    
    def route_task(self, task) -> Optional[AgentCard]:
        """
        Route a task to the best agent.
        
        Uses: REGISTRY (find by capability) → TERRAIN (tiebreak by proximity)
        Never uses terrain as primary (Campaign C proved it's invisible).
        """
        cap = task.get("capability") if isinstance(task, dict) else getattr(task, 'capability', None)
        if not cap:
            return None
        
        # Get all agents with this capability
        agents = self.find_agent(cap, min_level=1, verified_only=True)
        
        if not agents:
            # Fallback: try unverified
            agents = self.find_agent(cap, min_level=1, verified_only=False)
        
        if not agents:
            return None
        
        if len(agents) == 1:
            return agents[0]
        
        # Tiebreak by terrain proximity to task
        task_a = task.get("terrain_a", 0) if isinstance(task, dict) else getattr(task, 'terrain_a', 0)
        task_b = task.get("terrain_b", 0) if isinstance(task, dict) else getattr(task, 'terrain_b', 0)
        agents = self.find_nearest(cap, task_a, task_b)
        return agents[0]
    
    def to_tiles(self) -> list[dict]:
        """Serialize entire registry as PLATO tiles"""
        tiles = [{
            "question": "FLEET REGISTRY — READ THIS FIRST ON EVERY BOOT",
            "answer": f"This room is the verified fleet directory. {len(self.agents)} agents registered.\n\n"
                      f"Query by capability. Route by verified status. Tiebreak by terrain.",
            "metadata": {"type": "registry_header"}
        }]
        for agent in self.agents.values():
            tiles.append(agent.to_tile())
        return tiles
    
    def stats(self) -> dict:
        total_caps = 0
        verified_caps = 0
        for agent in self.agents.values():
            total_caps += len(agent.capabilities)
            verified_caps += len(agent.get_verified_capabilities())
        return {
            "total_agents": len(self.agents),
            "total_capabilities": total_caps,
            "verified_capabilities": verified_caps,
            "verification_rate": verified_caps / total_caps if total_caps > 0 else 0,
        }


# ═══════════════════════════════════════════════════════════════
# Build the actual fleet registry with real agent data
# ═══════════════════════════════════════════════════════════════

def build_production_registry() -> FleetRegistry:
    """Build the fleet registry with current agent data and verified capabilities."""
    registry = FleetRegistry()
    
    # === FORGEMASTER ===
    fm = AgentCard(
        name="Forgemaster",
        role="Constraint Theory Specialist",
        description="Eisenstein math, constraint theory proofs, E12 terrain, PLATO architecture",
        room="forgemaster",
        task_inbox="forgemaster-tasks",
        bridge_channel="!4ufW6MTmxHSAyU2VTs",  # oracle1-forgemaster-bridge
        terrain_a=3, terrain_b=0,
        model="GLM-5.1 via z.ai",
        host="eileen (WSL2)",
    )
    # Verified through actual shipped work (field_proven)
    fm.add_capability(Capability(
        name="eisenstein_math", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=1000,
        cross_verified_by=["Oracle1"],
        caveats=["Only agent with Eisenstein domain expertise"]
    ))
    fm.add_capability(Capability(
        name="constraint_theory", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=326,
        cross_verified_by=["Oracle1"],
        caveats=["3 crates on crates.io, 1 package on PyPI"]
    ))
    fm.add_capability(Capability(
        name="code_generation", status=VerificationStatus.TESTED,
        level=CapabilityLevel.COMPETENT, test_pass_rate=0.8, test_count=50,
        caveats=["Delegates to OpenCode/Kimi/Seed-2.0-mini for heavy lifting"]
    ))
    fm.add_capability(Capability(
        name="experiment_design", status=VerificationStatus.CROSS_VERIFIED,
        level=CapabilityLevel.EXPERT, test_pass_rate=0.9, test_count=15,
        cross_verified_by=["phi4-mini"],
    ))
    fm.add_capability(Capability(
        name="plato_architecture", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=200,
        cross_verified_by=["Oracle1"],
    ))
    fm.add_capability(Capability(
        name="terrain_navigation", status=VerificationStatus.TESTED,
        level=CapabilityLevel.COMPETENT, test_pass_rate=0.76, test_count=50,
        caveats=["Campaign B: 76% accuracy on hierarchical retrieval"]
    ))
    registry.register(fm)
    
    # === ORACLE1 ===
    o1 = AgentCard(
        name="Oracle1",
        role="Fleet Coordinator & Music Encoding",
        description="PLATO infrastructure, MIDI encoding, fleet coordination, spectral analysis",
        room="oracle1",
        task_inbox="oracle1-tasks",
        bridge_channel="!Gf5JuGxtRwahLSjwzS",  # fleet-ops
        terrain_a=2, terrain_b=1,
        model="Claude Opus",
        host="Oracle Cloud ARM64",
    )
    o1.add_capability(Capability(
        name="plato_infrastructure", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=500,
        cross_verified_by=["Forgemaster"],
        caveats=["Built and maintains PLATO server (3425 rooms, 53778 tiles)"]
    ))
    o1.add_capability(Capability(
        name="music_encoding", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=1276,
        cross_verified_by=["Forgemaster"],
        caveats=["1,276 pieces → 109-dim style vectors"]
    ))
    o1.add_capability(Capability(
        name="fleet_coordination", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=100,
        cross_verified_by=["Forgemaster"],
        caveats=["heartbeat.py, fleet-registry, fleet-inspector"]
    ))
    o1.add_capability(Capability(
        name="spectral_analysis", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=50,
        caveats=["Spectral gap theorem, normalized gap, Verifiability-Coupling Duality"]
    ))
    o1.add_capability(Capability(
        name="mathematical_proof", status=VerificationStatus.FIELD_PROVEN,
        level=CapabilityLevel.EXPERT, test_pass_rate=1.0, test_count=10,
        caveats=["Verifiability-Coupling Duality proved, O(ε·n·m) bound"]
    ))
    registry.register(o1)
    
    # === CCC ===
    ccc = AgentCard(
        name="CCC",
        role="Cloud Infrastructure & DevOps",
        description="Server management, deployment, Docker, infrastructure automation",
        room="ccc",
        task_inbox="ccc-tasks",
        terrain_a=5, terrain_b=-2,
        model="Unknown",
        host="Unknown",
    )
    ccc.add_capability(Capability(
        name="infrastructure", status=VerificationStatus.TESTED,
        level=CapabilityLevel.COMPETENT, test_pass_rate=0.8, test_count=20,
        caveats=["Campaign C: 80% when close to domain"]
    ))
    ccc.add_capability(Capability(
        name="deployment", status=VerificationStatus.CLAIMED,
        level=CapabilityLevel.COMPETENT, test_pass_rate=0.0, test_count=0,
    ))
    registry.register(ccc)
    
    # === SPECTRA ===
    spectra = AgentCard(
        name="Spectra",
        role="Signal Processing",
        description="Spectral analysis, signal processing, frequency domain",
        room="spectra",
        task_inbox="spectra-tasks",
        terrain_a=-1, terrain_b=3,
        model="Unknown",
        host="Unknown",
    )
    spectra.add_capability(Capability(
        name="signal_processing", status=VerificationStatus.CLAIMED,
        level=CapabilityLevel.COMPETENT, test_pass_rate=0.0, test_count=0,
    ))
    registry.register(spectra)
    
    # === NAVIGATOR ===
    nav = AgentCard(
        name="Navigator",
        role="Pathfinding & Route Planning",
        description="Route optimization, pathfinding algorithms, navigation",
        room="navigator",
        task_inbox="navigator-tasks",
        terrain_a=-2, terrain_b=-1,
        model="Unknown",
        host="Unknown",
    )
    nav.add_capability(Capability(
        name="pathfinding", status=VerificationStatus.CLAIMED,
        level=CapabilityLevel.COMPETENT, test_pass_rate=0.0, test_count=0,
    ))
    registry.register(nav)
    
    # === ARTISAN ===
    artisan = AgentCard(
        name="Artisan",
        role="Visual Design & Demos",
        description="HTML/CSS/JS demos, visualizations, UI/UX",
        room="artisan",
        task_inbox="artisan-tasks",
        terrain_a=4, terrain_b=2,
        model="Unknown",
        host="Unknown",
    )
    artisan.add_capability(Capability(
        name="visual_design", status=VerificationStatus.CLAIMED,
        level=CapabilityLevel.COMPETENT, test_pass_rate=0.0, test_count=0,
    ))
    registry.register(artisan)
    
    return registry


if __name__ == "__main__":
    registry = build_production_registry()
    
    print("=" * 60)
    print("FLEET REGISTRY — Verified Agent Cards")
    print("=" * 60)
    
    for name, agent in registry.agents.items():
        verified = agent.get_verified_capabilities()
        total = len(agent.capabilities)
        print(f"\n## {name} ({agent.role})")
        print(f"   Room: {agent.room} | Inbox: {agent.task_inbox}")
        print(f"   Terrain: E12({agent.terrain_a},{agent.terrain_b})")
        print(f"   Capabilities: {len(verified)} verified / {total} total")
        for cap in agent.capabilities:
            c = Capability.from_dict(cap) if isinstance(cap, dict) else cap
            status_icon = {"claimed": "❓", "tested": "🧪", "cross_verified": "✅", "field_proven": "🏆"}.get(c.status.value, "?")
            print(f"   {status_icon} {c.name}: {c.level.name} ({c.status.value}, {c.test_pass_rate:.0%} pass rate)")
    
    print(f"\n{'=' * 60}")
    stats = registry.stats()
    print(f"Registry stats: {stats}")
    
    # Test routing
    print(f"\n{'=' * 60}")
    print("ROUTING TESTS")
    print(f"{'=' * 60}")
    
    tasks = [
        {"capability": "eisenstein_math", "terrain_a": 3, "terrain_b": -1, "description": "Compute Eisenstein norm"},
        {"capability": "plato_infrastructure", "terrain_a": 0, "terrain_b": 0, "description": "Deploy PLATO v3"},
        {"capability": "infrastructure", "terrain_a": 5, "terrain_b": -3, "description": "Restart fleet services"},
        {"capability": "experiment_design", "terrain_a": 0, "terrain_b": 0, "description": "Design terrain-weighted voting test"},
        {"capability": "music_encoding", "terrain_a": 2, "terrain_b": 2, "description": "Encode MIDI style vector"},
    ]
    
    for task in tasks:
        agent = registry.route_task(task)
        if agent:
            print(f"  {task['capability']:25s} → {agent.name} (E12({agent.terrain_a},{agent.terrain_b}))")
        else:
            print(f"  {task['capability']:25s} → NO AGENT FOUND")
    
    # Export as PLATO tiles
    print(f"\n{'=' * 60}")
    print(f"PLATO tiles: {len(registry.to_tiles())} tiles ready for submission")
