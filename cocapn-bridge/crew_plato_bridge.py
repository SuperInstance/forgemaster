# crew_plato_bridge.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
import json
import uuid

# ─── CrewAI-style definitions (no CrewAI dependency) ────────────────

class Process(str, Enum):
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"      # Our addition — PBFT-style voting
    RACING = "racing"            # Our addition — first to finish wins

@dataclass
class AgentCard:
    """CrewAI Agent → PLATO agent card."""
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    allow_delegation: bool = False
    knowledge_sources: List[str] = field(default_factory=list)
    model: str = ""
    hardware_targets: List[str] = field(default_factory=list)
    # PLATO-specific
    primary_room: str = ""
    task_inbox: str = ""
    
    def to_manifest_text(self) -> str:
        return f"""## Agent: {self.name}
- Role: {self.role}
- Goal: {self.goal}
- Backstory: {self.backstory}
- Tools: {', '.join(self.tools)}
- Allow delegation: {self.allow_delegation}
- Knowledge sources: {', '.join(self.knowledge_sources)}
- Model: {self.model}
- Hardware: {', '.join(self.hardware_targets)}
- Primary room: {self.primary_room}
- Task inbox: {self.task_inbox}"""

@dataclass
class TaskDef:
    """CrewAI Task → PLATO task tile."""
    id: str
    description: str
    expected_output: str
    agent: str              # Agent name
    depends_on: List[str] = field(default_factory=list)
    # PLATO-specific
    status: str = "pending"  # pending → assigned → running → completed → failed
    result_room: str = ""
    
    def to_tile_question(self) -> str:
        deps = f" (depends on: {', '.join(self.depends_on)})" if self.depends_on else ""
        return f"TASK-{self.id}: {self.description}{deps}"
    
    def to_tile_answer(self) -> str:
        return f"""Assigned to: {self.agent}
Expected output: {self.expected_output}
Status: {self.status}
Dependencies: {', '.join(self.depends_on) or 'none'}"""

@dataclass
class CrewManifest:
    """CrewAI Crew → PLATO crew room manifest."""
    id: str = field(default_factory=lambda: f"crew-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    agents: List[AgentCard] = field(default_factory=list)
    tasks: List[TaskDef] = field(default_factory=list)
    process: Process = Process.SEQUENTIAL
    memory: bool = True
    verbose: bool = True
    
    def to_manifest_tile(self) -> dict:
        """Generate the manifest tile for the crew room."""
        agent_section = "\n".join(a.to_manifest_text() for a in self.agents)
        task_section = "\n".join(
            f"  {t.id}: {t.description} → {t.agent}"
            f"{' (after ' + ', '.join(t.depends_on) + ')' if t.depends_on else ''}"
            for t in self.tasks
        )
        
        manifest = f"""# Crew: {self.name}
ID: {self.id}
Description: {self.description}
Process: {self.process.value}
Memory: {self.memory}

## Agents
{agent_section}

## Tasks (execution order)
{task_section}

## Fleet Registry Integration
- Room: {self.id}
- Created: {now_iso()}
- Status: INITIALIZED
"""
        return {
            "question": f"CREW MANIFEST — {self.name}",
            "answer": manifest,
            "perspectives": [
                {"label": "one-line", "text": f"Crew {self.id}: {self.description}"},
                {"label": "hover-card", "text": f"{len(self.agents)} agents, {len(self.tasks)} tasks, {self.process.value} process. {self.description}"},
            ]
        }


# ─── Fleet Agent Cards (from fleet-registry) ────────────────────────

FORGEMASTER = AgentCard(
    name="Forgemaster",
    role="Constraint Theory Specialist",
    goal="Make constraint theory undeniable through proof repos",
    backstory="Precision-obsessed, metal/geometry analogies. Runs on GLM-5.1.",
    tools=["e12-snap", "constraint-verify", "spline-compress", "terrain-index"],
    allow_delegation=True,
    knowledge_sources=["plato-room:forgemaster-*", "plato-room:constraint-*"],
    model="zai/glm-5.1",
    hardware_targets=["cpu", "cpu-tiny", "gpu"],
    primary_room="forge",
    task_inbox="forgemaster-task-tracker",
)

ORACLE1 = AgentCard(
    name="Oracle1",
    role="Fleet Coordinator & Lighthouse",
    goal="Maintain fleet infrastructure, coordinate agents, run benchmarks",
    backstory="Runs on ARM64 Oracle Cloud. Fortran seed memory. Tucker decomposition.",
    tools=["plato-server", "matrix-bridge", "fortran-seed", "midi-pipeline"],
    allow_delegation=False,
    knowledge_sources=["plato-room:agent-oracle1", "plato-room:fleet-*"],
    model="zai/glm-5.1",
    hardware_targets=["cpu", "npu", "tpu"],
    primary_room="agent-oracle1",
    task_inbox="oracle1-task-queue",
)


# ─── Bridge Operations ──────────────────────────────────────────────

class CrewPlatoBridge:
    """Translates CrewAI crew definitions into PLATO rooms.
    
    No CrewAI dependency needed. This IS the distributed CrewAI.
    """
    
    def __init__(self, plato_url: str = "http://147.224.38.131:8847"):
        self.plato_url = plato_url
    
    def create_crew_room(self, manifest: CrewManifest) -> str:
        """Create a PLATO room for a crew run. Returns room ID."""
        room_id = manifest.id
        
        # Submit manifest tile
        self._submit_tile(room_id, manifest.to_manifest_tile())
        
        # Submit agent card tiles
        for agent in manifest.agents:
            self._submit_tile(room_id, {
                "question": f"AGENT-{agent.name.upper()}",
                "answer": agent.to_manifest_text(),
            })
        
        # Submit task tiles
        for task in manifest.tasks:
            self._submit_tile(room_id, {
                "question": task.to_tile_question(),
                "answer": task.to_tile_answer(),
            })
        
        return room_id
    
    def dispatch_tasks(self, room_id: str, manifest: CrewManifest):
        """Dispatch tasks to fleet agents via their task inboxes."""
        if manifest.process == Process.SEQUENTIAL:
            self._dispatch_sequential(room_id, manifest)
        elif manifest.process == Process.HIERARCHICAL:
            self._dispatch_hierarchical(room_id, manifest)
        elif manifest.process == Process.CONSENSUS:
            self._dispatch_consensus(room_id, manifest)
        elif manifest.process == Process.RACING:
            self._dispatch_racing(room_id, manifest)
    
    def _dispatch_sequential(self, room_id: str, manifest: CrewManifest):
        """Sequential: dispatch first task, chain rest as dependencies."""
        # Find tasks with no dependencies (first in chain)
        ready = [t for t in manifest.tasks if not t.depends_on]
        
        for task in ready:
            agent = next((a for a in manifest.agents if a.name == task.agent), None)
            if not agent:
                continue
            
            # Write task to agent's inbox
            self._submit_tile(agent.task_inbox, {
                "question": f"{room_id}→{agent.name} TASK: {task.description}",
                "answer": f"""Crew: {room_id}
Task ID: {task.id}
Expected output: {task.expected_output}
Source room: {room_id}
When done: submit result tile to {room_id} as RESULT-{task.id}"""
            })
    
    def _dispatch_hierarchical(self, room_id: str, manifest: CrewManifest):
        """Hierarchical: manager agent assigns and reviews."""
        # First agent is the manager
        manager = manifest.agents[0]
        
        # Send all tasks to manager for delegation
        task_list = "\n".join(f"  - {t.id}: {t.description} → {t.agent}" for t in manifest.tasks)
        
        self._submit_tile(manager.task_inbox, {
            "question": f"{room_id}→{manager.name} MANAGE: {manifest.name}",
            "answer": f"""You are the manager for crew {room_id}.
            
Tasks to delegate:
{task_list}

Process:
1. Review each task's description and expected output
2. Assign to appropriate agent via their task inbox
3. Review results as they come in
4. Submit final SUMMARY tile when all tasks complete

Source room: {room_id}"""
        })
    
    def _dispatch_consensus(self, room_id: str, manifest: CrewManifest):
        """Consensus: all agents work on same task, PBFT-style voting."""
        for task in manifest.tasks:
            for agent in manifest.agents:
                self._submit_tile(agent.task_inbox, {
                    "question": f"{room_id}→{agent.name} CONSENSUS: {task.description}",
                    "answer": f"""Crew: {room_id} (CONSENSUS mode)
Task ID: {task.id}
Expected output: {task.expected_output}

ALL agents work on this task independently.
Submit your result tile to {room_id} as VOTE-{task.id}-{agent.name}
Results will be compared for consensus.

Source room: {room_id}"""
                })
    
    def _dispatch_racing(self, room_id: str, manifest: CrewManifest):
        """Racing: first agent to complete wins."""
        for task in manifest.tasks:
            for agent in manifest.agents:
                self._submit_tile(agent.task_inbox, {
                    "question": f"{room_id}→{agent.name} RACE: {task.description}",
                    "answer": f"""Crew: {room_id} (RACING mode)
Task ID: {task.id}
Expected output: {task.expected_output}

FIRST agent to submit a result tile wins.
Check {room_id} before starting — someone may have already finished.

Source room: {room_id}"""
                })
    
    def check_task_status(self, room_id: str, task_id: str) -> str:
        """Check if a task has been completed."""
        tiles = self._fetch_tiles(room_id)
        for tile in tiles:
            q = tile.get("question", "")
            if f"RESULT-{task_id}" in q or f"VOTE-{task_id}" in q:
                return tile.get("answer", {}).get("status", "completed")
        return "pending"
    
    def _submit_tile(self, room_id: str, tile: dict):
        """Submit a tile to a PLATO room."""
        import urllib.request
        url = f"{self.plato_url}/submit"
        data = json.dumps({"room": room_id, **tile}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            # Queue for retry
            pass
    
    def _fetch_tiles(self, room_id: str) -> list:
        """Fetch tiles from a PLATO room."""
        import urllib.request
        url = f"{self.plato_url}/room/{room_id}"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
                return data if isinstance(data, list) else data.get("tiles", [])
        except:
            return []


# ─── Oracle1 Integration ────────────────────────────────────────────

def bridge_with_oracle1_registry(bridge: CrewPlatoBridge, manifest: CrewManifest):
    """Register crew room in Oracle1's fleet-registry.
    
    Oracle1's heartbeat reads fleet-registry on every cycle.
    Adding the crew room there means Oracle1 discovers it automatically.
    """
    registry_tile = {
        "question": f"CREW REGISTRATION — {manifest.name}",
        "answer": f"""Crew room: {manifest.id}
Process: {manifest.process.value}
Agents: {', '.join(a.name for a in manifest.agents)}
Tasks: {len(manifest.tasks)}
Status: RUNNING
Created: {now_iso()}

Oracle1: you are {'a participant' if any(a.name == 'Oracle1' for a in manifest.agents) else 'the coordinator'} in this crew.
Room: {manifest.id}"""
    }
    bridge._submit_tile("fleet-registry", registry_tile)


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# Example: Run the ACG decomposition as a crew
bridge = CrewPlatoBridge()

crew = CrewManifest(
    name="Decompose ACG Protocol",
    description="Analyze Kos-M/acg_protocol, extract useful patterns, integrate into PLATO",
    agents=[FORGEMASTER, ORACLE1],
    tasks=[
        TaskDef(
            id="1",
            description="Fetch and analyze ACG source code. Extract claim marker, SHI, and RSVP patterns.",
            expected_output="Decomposition document with 5+ actionable insights",
            agent="Forgemaster",
        ),
        TaskDef(
            id="2",
            description="Implement PLATO tile perspectives based on ACG claim markers",
            expected_output="Working Python module: cocapn/tile_perspectives.py",
            agent="Forgemaster",
            depends_on=["1"],
        ),
        TaskDef(
            id="3",
            description="Cross-verify perspective implementation against ACG test cases",
            expected_output="Verification report with pass/fail for each test",
            agent="Oracle1",
            depends_on=["2"],
        ),
    ],
    process=Process.SEQUENTIAL,
)

room_id = bridge.create_crew_room(crew)
bridge.dispatch_tasks(room_id, crew)
bridge_with_oracle1_registry(bridge, crew)

print(f"Crew dispatched. Room: {room_id}")
print(f"Oracle1 will discover this on next heartbeat cycle.")


result_tile = {
    "question": f"RESULT-{task.id}",
    "answer": result_text,
    "perspectives": [
        {"label": "one-line", "text": f"Task {task.id}: {task.description} — completed"},
        {"label": "hover-card", "text": f"Result from {agent.name}. {result_text[:100]}..."},
        {"label": "context-brief", "text": f"For task '{task.description}', {agent.name} produced: {result_text[:200]}..."},
    ],
    "retrieval_status": "earmark-agentic-beta-test",
    "reasoning_type": reasoning_type,  # From ACG: CAUSAL, INFERENCE, SUMMARY, COMPARISON
}
