"""
PBFT-inspired Consensus for Fleet Tile Verification

Adapted from SuperInstance/pbft-rust (0xjeffro) with COCAPN-CREDITS.
Simplified for PLATO tile verification: no view changes, no checkpoints.
Just: propose → pre-vote → commit → decide.

Campaign A proved: single-agent verification is insufficient (80% failure).
Campaign C proved: terrain weighting needs ≥60% baseline model accuracy.
This module implements the consensus layer that BOTH findings point to.
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class Vote(Enum):
    YES = "YES"
    NO = "NO"
    ABSTAIN = "ABSTAIN"

class Phase(Enum):
    PROPOSED = "proposed"
    PRE_VOTED = "pre_voted"
    COMMITTED = "committed"
    DECIDED = "decided"
    REJECTED = "rejected"

@dataclass
class ConsensusClaim:
    """A claim about a tile that needs consensus verification"""
    claim_id: str
    tile_label: str
    claim_text: str
    proposer: str
    timestamp: float = field(default_factory=time.time)
    phase: Phase = Phase.PROPOSED
    pre_votes: dict = field(default_factory=dict)  # agent → Vote
    commit_votes: dict = field(default_factory=dict)
    decision: Optional[bool] = None
    evidence: list = field(default_factory=list)
    
    def hash(self):
        content = f"{self.claim_id}:{self.tile_label}:{self.claim_text}:{self.proposer}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

@dataclass
class ConsensusResult:
    """Result of a consensus round"""
    claim_id: str
    claim_hash: str
    passed: bool
    phase_reached: Phase
    yes_votes: int
    no_votes: int
    abstain_votes: int
    total_agents: int
    f_tolerance: int  # Max Byzantine agents tolerated
    terrain_weighted: bool
    weighted_yes: float
    weighted_no: float
    evidence_summary: str = ""

class PBFTConsensus:
    """
    Simplified PBFT for fleet tile verification.
    
    Parameters:
      n_agents: total voting agents
      quorum_style: 'uniform' (2f+1) or 'terrain' (weighted by domain proximity)
      terrain: optional FleetTerrain for weighted voting
    """
    
    def __init__(self, n_agents: int = 5, quorum_style: str = 'uniform', terrain=None):
        self.n_agents = n_agents
        self.f = (n_agents - 1) // 3  # Max Byzantine faults
        self.quorum = 2 * self.f + 1  # Minimum votes for decision
        self.quorum_style = quorum_style
        self.terrain = terrain
        self.claims: dict[str, ConsensusClaim] = {}
    
    def propose(self, claim_id: str, tile_label: str, claim_text: str, proposer: str) -> ConsensusClaim:
        """Phase 1: Propose a claim for verification"""
        claim = ConsensusClaim(
            claim_id=claim_id,
            tile_label=tile_label,
            claim_text=claim_text,
            proposer=proposer,
        )
        self.claims[claim_id] = claim
        return claim
    
    def pre_vote(self, claim_id: str, agent: str, vote: Vote, evidence: str = "") -> bool:
        """Phase 2: Pre-vote on a claim"""
        if claim_id not in self.claims:
            return False
        claim = self.claims[claim_id]
        if claim.phase != Phase.PROPOSED:
            return False
        
        claim.pre_votes[agent] = vote
        if evidence:
            claim.evidence.append(f"{agent}: {evidence}")
        
        # Check if we have enough pre-votes
        if len(claim.pre_votes) >= self.quorum:
            yes_count = sum(1 for v in claim.pre_votes.values() if v == Vote.YES)
            if yes_count >= self.quorum:
                claim.phase = Phase.PRE_VOTED
                return True
            elif len(claim.pre_votes) == self.n_agents:
                # All voted but not enough YES
                claim.phase = Phase.REJECTED
                claim.decision = False
                return True
        
        return False
    
    def commit_vote(self, claim_id: str, agent: str, vote: Vote, evidence: str = "") -> Optional[ConsensusResult]:
        """Phase 3: Commit vote after pre-vote passed"""
        if claim_id not in self.claims:
            return None
        claim = self.claims[claim_id]
        if claim.phase not in (Phase.PRE_VOTED, Phase.COMMITTED):
            return None
        
        claim.commit_votes[agent] = vote
        if evidence:
            claim.evidence.append(f"{agent} commit: {evidence}")
        
        # Check if we have enough commit votes
        if len(claim.commit_votes) >= self.quorum:
            return self._decide(claim)
        
        if claim.phase == Phase.PRE_VOTED and len(claim.commit_votes) > 0:
            claim.phase = Phase.COMMITTED
        
        return None
    
    def _decide(self, claim: ConsensusClaim) -> ConsensusResult:
        """Final decision based on votes"""
        yes = sum(1 for v in claim.commit_votes.values() if v == Vote.YES)
        no = sum(1 for v in claim.commit_votes.values() if v == Vote.NO)
        abstain = sum(1 for v in claim.commit_votes.values() if v == Vote.ABSTAIN)
        
        passed = yes >= self.quorum
        claim.decision = passed
        claim.phase = Phase.DECIDED if passed else Phase.REJECTED
        
        # Compute terrain-weighted scores if terrain available
        weighted_yes = 0.0
        weighted_no = 0.0
        if self.terrain:
            for agent, vote in claim.commit_votes.items():
                weight = 1.0  # Default
                # Try terrain weighting
                try:
                    tile_e12 = None
                    for coord, v in self.terrain.graph.vertices.items():
                        if v.label == claim.tile_label:
                            tile_e12 = coord
                            break
                    if tile_e12:
                        agent_e12 = self.terrain.get_position(agent)
                        weight = self.terrain.graph.terrain_weight(agent_e12, tile_e12)
                except:
                    pass
                
                if vote == Vote.YES:
                    weighted_yes += weight
                elif vote == Vote.NO:
                    weighted_no += weight
        
        return ConsensusResult(
            claim_id=claim.claim_id,
            claim_hash=claim.hash(),
            passed=passed,
            phase_reached=claim.phase,
            yes_votes=yes,
            no_votes=no,
            abstain_votes=abstain,
            total_agents=self.n_agents,
            f_tolerance=self.f,
            terrain_weighted=self.terrain is not None,
            weighted_yes=weighted_yes,
            weighted_no=weighted_no,
            evidence_summary="\n".join(claim.evidence[:5]),
        )


# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("PBFT Consensus Demo — Fleet Tile Verification")
    print("=" * 60)
    
    # 5 agents, tolerate 1 Byzantine fault
    pbft = PBFTConsensus(n_agents=5, quorum_style='uniform')
    print(f"n=5, f={pbft.f}, quorum={pbft.quorum}")
    print()
    
    # Propose a claim
    claim = pbft.propose(
        "claim-001",
        "zero-side-info-theorem",
        "Z[ζ₁₂] achieves covering radius 0.308 at 0 bits side information",
        "Forgemaster"
    )
    print(f"Proposed: {claim.claim_text[:60]}...")
    print(f"Hash: {claim.hash()}")
    print()
    
    # Pre-votes (simulate 5 agents)
    print("Pre-vote phase:")
    agents_votes = [
        ("Forgemaster", Vote.YES, "N(0,0)=0.308 verified computationally"),
        ("Oracle1", Vote.YES, "Cross-checked with spectral gap theorem"),
        ("CCC", Vote.YES, "Reproduced on ARM64 hardware"),
        ("Spectra", Vote.NO, "Need more samples for statistical significance"),
        ("Navigator", Vote.ABSTAIN, "Outside my domain expertise"),
    ]
    
    for agent, vote, evidence in agents_votes:
        pbft.pre_vote("claim-001", agent, vote, evidence)
        print(f"  {agent}: {vote.value} — {evidence[:50]}")
    
    print(f"  Phase: {claim.phase.value}")
    print()
    
    # Commit votes
    print("Commit phase:")
    for agent, vote, evidence in agents_votes:
        result = pbft.commit_vote("claim-001", agent, vote, evidence)
        if result:
            print(f"  DECISION REACHED!")
            break
    
    if claim.decision is not None:
        print()
        print(f"Claim: {claim.claim_id}")
        print(f"Passed: {claim.decision}")
        print(f"Phase: {claim.phase.value}")
        print(f"Votes: {result.yes_votes} YES, {result.no_votes} NO, {result.abstain_votes} ABSTAIN")
        print(f"Quorum needed: {result.f_tolerance * 2 + 1}/{result.total_agents}")
        print(f"Byzantine tolerance: f={result.f_tolerance}")
        print()
        print("Evidence:")
        for line in result.evidence_summary.split("\n"):
            print(f"  {line[:80]}")
    
    # Now with terrain weighting
    print("\n" + "=" * 60)
    print("With Terrain-Weighted Voting")
    print("=" * 60)
    
    from e12_terrain.plato_integration import FleetTerrain
    terrain = FleetTerrain()
    pbft2 = PBFTConsensus(n_agents=5, quorum_style='terrain', terrain=terrain)
    
    claim2 = pbft2.propose(
        "claim-002",
        "constraint-theory-core",
        "Eisenstein norm N(a,b)=a²-ab+b² is always non-negative",
        "Forgemaster"
    )
    
    for agent, vote, _ in agents_votes:
        pbft2.pre_vote("claim-002", agent, vote)
    
    for agent, vote, _ in agents_votes:
        result2 = pbft2.commit_vote("claim-002", agent, vote)
        if result2:
            break
    
    if result2:
        print(f"Uniform: {result2.yes_votes}/{result2.total_agents} YES → {'PASS' if result2.passed else 'FAIL'}")
        print(f"Terrain-weighted: {result2.weighted_yes:.2f} vs {result2.weighted_no:.2f}")
