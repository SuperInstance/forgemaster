"""
Task Atom: DO / DATA / DONE

The irreducible execution unit. Every fleet task is encoded as exactly these three fields.
Planning agents see CHAIN/CLAIM/ORDER. Execution agents see only DO/DATA/DONE.

Architecture: ARCHITECTURE-IRREDUCIBLE.md Layer 2 (Execution)
Evidence: RESULTS Exp 1 (3.0/3 with perspectives), DEEP-RESULTS Exp 1 (DATA must contain actual numbers)
"""

import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class TaskPhase(Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class ReasoningType(Enum):
    """ACG reasoning taxonomy — different types need different verification"""
    CAUSAL = "causal"          # Needs full PBFT (2f+1)
    INFERENCE = "inference"    # Needs simple majority (f+1)
    SUMMARY = "summary"        # Needs supermajority (2/3)
    COMPARISON = "comparison"  # Objective — single verifier
    COMPUTATION = "computation"  # Objective — single verifier + audit trail


@dataclass
class TaskAtom:
    """
    The irreducible execution unit.
    
    DO:    What to compute (imperative verb phrase)
    DATA:  The actual numbers/formulas (NOT instructions to find them)
    DONE:  Expected output format and acceptance criteria
    
    The DATA field is the critical insight from Exp 1.
    Agents fail when DATA says "find the norm formula".
    Agents succeed when DATA says "N(a,b) = a²-ab+b²".
    """
    # The three fields
    do: str          # What to compute
    data: str        # The actual inputs (numbers, formulas, code)
    done: str        # Expected output format
    
    # Metadata
    task_id: str = ""
    capability: str = ""      # Required capability name
    reasoning_type: ReasoningType = ReasoningType.COMPUTATION
    
    # Routing (populated by planner, invisible to executor)
    assigned_to: Optional[str] = None
    depends_on: list = field(default_factory=list)  # task_ids
    
    # Lifecycle
    phase: TaskPhase = TaskPhase.PENDING
    created: float = field(default_factory=time.time)
    claimed_at: Optional[float] = None
    submitted_at: Optional[float] = None
    verified_at: Optional[float] = None
    
    # Results
    result: Optional[str] = None
    verification_votes: list = field(default_factory=list)
    
    def __post_init__(self):
        if not self.task_id:
            content = f"{self.do}:{self.data}:{self.done}"
            self.task_id = hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def to_executor_context(self) -> str:
        """
        What the execution agent sees.
        ONLY DO/DATA/DONE — no chain history, no dependencies, no planning context.
        
        Evidence (DEEP-RESULTS Exp 2): Stream context = full graph for execution.
        JIT chain summary HURT scores by introducing irrelevant abstractions.
        """
        return f"""Execute this task:

DO: {self.do}

DATA: {self.data}

DONE: {self.done}"""
    
    def to_planner_context(self) -> str:
        """
        What the planning agent sees.
        CHAIN (dependencies) + CLAIM (capability) + ORDER (sequence).
        """
        deps = f"Depends on: {', '.join(self.depends_on)}" if self.depends_on else "No dependencies"
        return f"""Task: {self.task_id}
Capability needed: {self.capability}
Reasoning type: {self.reasoning_type.value}
{deps}

DO: {self.do}
DATA: {self.data}
DONE: {self.done}"""
    
    def claim(self, agent_name: str):
        """Agent claims this task"""
        self.phase = TaskPhase.CLAIMED
        self.assigned_to = agent_name
        self.claimed_at = time.time()
    
    def submit(self, result: str):
        """Agent submits result"""
        self.phase = TaskPhase.SUBMITTED
        self.result = result
        self.submitted_at = time.time()
    
    def verify(self, voter: str, passed: bool, evidence: str = ""):
        """Verification vote on the result"""
        self.verification_votes.append({
            "voter": voter,
            "passed": passed,
            "evidence": evidence,
            "timestamp": time.time(),
        })
        
        # Check quorum based on reasoning type
        yes_votes = sum(1 for v in self.verification_votes if v["passed"])
        no_votes = sum(1 for v in self.verification_votes if not v["passed"])
        total = len(self.verification_votes)
        
        # Minimum quorum by reasoning type
        quorum = {
            ReasoningType.CAUSAL: 3,      # Full PBFT
            ReasoningType.INFERENCE: 2,    # Simple majority
            ReasoningType.SUMMARY: 2,      # Supermajority (2/3 of 3)
            ReasoningType.COMPARISON: 1,   # Single verifier
            ReasoningType.COMPUTATION: 1,  # Single verifier
        }.get(self.reasoning_type, 2)
        
        if yes_votes >= quorum:
            self.phase = TaskPhase.VERIFIED
            self.verified_at = time.time()
        elif no_votes >= quorum:
            self.phase = TaskPhase.FAILED
    
    def to_tile(self) -> dict:
        """Serialize as PLATO tile"""
        return {
            "question": f"TASK {self.task_id} — {self.do}",
            "answer": json.dumps({
                "task_id": self.task_id,
                "do": self.do,
                "data": self.data,
                "done": self.done,
                "capability": self.capability,
                "reasoning_type": self.reasoning_type.value,
                "assigned_to": self.assigned_to,
                "depends_on": self.depends_on,
                "phase": self.phase.value,
                "result": self.result,
                "created": self.created,
            }, indent=2),
            "metadata": {
                "type": "task_atom",
                "phase": self.phase.value,
                "capability": self.capability,
            }
        }
    
    def to_dict(self):
        return {
            "task_id": self.task_id,
            "do": self.do,
            "data": self.data,
            "done": self.done,
            "capability": self.capability,
            "reasoning_type": self.reasoning_type.value,
            "assigned_to": self.assigned_to,
            "depends_on": self.depends_on,
            "phase": self.phase.value,
            "created": self.created,
            "claimed_at": self.claimed_at,
            "submitted_at": self.submitted_at,
            "verified_at": self.verified_at,
            "result": self.result,
            "verification_votes": self.verification_votes,
        }


# ═══════════════════════════════════════════════════════════════
# Demo: Build a real task chain
# ═══════════════════════════════════════════════════════════════

def build_constraint_verification_chain() -> list[TaskAtom]:
    """
    A real task chain: verify the Eisenstein norm property.
    
    Chain:
      T1: Compute norm of (3,-1) → T2: Verify against known result
      T3: Compute norm of (2,3) → T4: Verify against known result
      T5: Check if norms are always non-negative → T6: Prove/disprove
    """
    t1 = TaskAtom(
        do="Compute the Eisenstein norm of the point (3, -1)",
        data="N(a,b) = a² - ab + b²\na = 3, b = -1\nN = 9 - (3)(-1) + 1 = 9 + 3 + 1 = 13",
        done="Single integer: the norm value",
        capability="eisenstein_math",
        reasoning_type=ReasoningType.COMPUTATION,
    )
    
    t2 = TaskAtom(
        do="Verify that the computed norm of (3,-1) equals 13",
        data="Point: (3, -1)\nClaimed result: 13\nFormula: N(a,b) = a² - ab + b²\nExpected: 3² - 3(-1) + (-1)² = 9 + 3 + 1 = 13",
        done="TRUE or FALSE with computation showing why",
        capability="eisenstein_math",
        reasoning_type=ReasoningType.COMPARISON,
        depends_on=[t1.task_id],
    )
    
    t3 = TaskAtom(
        do="Compute the Eisenstein norm of the point (2, 3)",
        data="N(a,b) = a² - ab + b²\na = 2, b = 3\nN = 4 - 6 + 9 = 7",
        done="Single integer: the norm value",
        capability="eisenstein_math",
        reasoning_type=ReasoningType.COMPUTATION,
    )
    
    t4 = TaskAtom(
        do="Verify that the computed norm of (2,3) equals 7",
        data="Point: (2, 3)\nClaimed result: 7\nFormula: N(a,b) = a² - ab + b²\nExpected: 2² - 2(3) + 3² = 4 - 6 + 9 = 7",
        done="TRUE or FALSE with computation showing why",
        capability="eisenstein_math",
        reasoning_type=ReasoningType.COMPARISON,
        depends_on=[t3.task_id],
    )
    
    t5 = TaskAtom(
        do="Determine whether the Eisenstein norm N(a,b) = a²-ab+b² is always non-negative for all integer inputs",
        data="Formula: N(a,b) = a² - ab + b²\nTest cases: N(1,1)=1, N(0,0)=0, N(-1,-1)=1, N(1,0)=1, N(0,1)=1, N(2,-1)=7, N(3,-1)=13, N(2,3)=7\nAll test cases produce non-negative results.",
        done="TRUE or FALSE with mathematical reasoning. If TRUE, state the proof approach.",
        capability="eisenstein_math",
        reasoning_type=ReasoningType.CAUSAL,
        depends_on=[t1.task_id, t3.task_id],
    )
    
    return [t1, t2, t3, t4, t5]


if __name__ == "__main__":
    print("=" * 60)
    print("TASK ATOM — DO/DATA/DONE")
    print("=" * 60)
    
    chain = build_constraint_verification_chain()
    
    for t in chain:
        print(f"\nTask {t.task_id}: {t.do[:60]}...")
        print(f"  Capability: {t.capability}")
        print(f"  Reasoning: {t.reasoning_type.value}")
        print(f"  Depends: {t.depends_on or 'none'}")
        print(f"  Phase: {t.phase.value}")
    
    print(f"\n{'=' * 60}")
    print("EXECUTOR VIEW (what the agent sees)")
    print(f"{'=' * 60}")
    print(chain[0].to_executor_context())
    
    print(f"\n{'=' * 60}")
    print("PLANNER VIEW (what the coordinator sees)")
    print(f"{'=' * 60}")
    for t in chain:
        print(t.to_planner_context())
        print()
    
    # Simulate execution
    print(f"{'=' * 60}")
    print("SIMULATED EXECUTION")
    print(f"{'=' * 60}")
    
    # T1: Forgemaster claims and computes
    chain[0].claim("Forgemaster")
    chain[0].submit("13")
    chain[0].verify("Oracle1", True, "Cross-checked: 9+3+1=13")
    print(f"T1: {chain[0].phase.value} → result={chain[0].result}")
    
    # T2: Oracle1 verifies
    chain[1].claim("Oracle1")
    chain[1].submit("TRUE — N(3,-1) = 9+3+1 = 13, matches claim")
    chain[1].verify("Forgemaster", True, "Original computation confirmed")
    print(f"T2: {chain[1].phase.value} → result={chain[1].result[:50]}")
    
    print(f"\nPLATO tiles generated: {len(chain)}")
    for t in chain[:2]:
        tile = t.to_tile()
        print(f"  {tile['question'][:60]}...")
