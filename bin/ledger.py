"""
ledger.py — Double-entry provenance for the decomposition engine.

Every knowledge claim has two sides:
  DEBIT:  Where it came from (source, conjecture, decomposition, verifier, chip)
  CREDIT: Where it went (what depends on it, what it enables, what it superseded)

Like double-entry bookkeeping:
  - Every transaction (verification) posts to BOTH sides
  - The ledger must balance: total debits = total credits
  - You can trace any claim forward or backward through the chain
  - Nothing disappears — superseded entries get a credit to their replacement

The tile lifecycle (Active → Superseded → Retracted) is just the account state.
The real power is the links: every tile knows its parents AND its children.

This makes the knowledge spline auditable. You can answer:
  "Why do we believe X?" → trace debits back to original conjecture
  "What depends on X?" → trace credits forward to all downstream claims
  "What broke when X was superseded?" → follow credit links from old X
  "Is the ledger balanced?" → every claim accounted for, nothing orphaned
"""

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ─── The Double Entry ─────────────────────────────────────────────

@dataclass
class LedgerEntry:
    """
    A single entry in the knowledge ledger.
    Every verification result, conjecture, decomposition, and FLUX program
    gets one. The entry's debit is its provenance; its credit is its impact.
    """
    # Identity
    id: str                           # Hash of content + timestamp
    kind: str                         # conjecture | decomposition | verification | flux_program | experiment
    
    # The claim
    claim: str                        # What this entry asserts
    status: str = "active"            # active | superseded | retracted | pending
    
    # DEBIT: Where it came from
    debit_sources: List[str] = field(default_factory=list)    # Parent entry IDs
    debit_conjecture: Optional[str] = None                     # Original conjecture
    debit_decomposition: Optional[str] = None                  # Which decomposition produced this
    debit_verifier: Optional[str] = None                       # Which verifier checked this
    debit_model: Optional[str] = None                          # Which model was used (if any)
    debit_chip: Optional[str] = None                           # Which hardware ran this
    debit_flux_program: Optional[str] = None                   # Which FLUX bytecode ran this
    
    # CREDIT: Where it went
    credit_enables: List[str] = field(default_factory=list)    # Child entry IDs this supports
    credit_superseded_by: Optional[str] = None                 # Entry that replaced this
    credit_feeds: List[str] = field(default_factory=list)      # Downstream systems/reports
    credit_flux_compiled_to: Optional[str] = None              # FLUX program compiled from this
    
    # Evidence
    evidence: dict = field(default_factory=dict)               # Raw data (trials, deltas, etc.)
    confidence: float = 1.0                                     # How confident (0-1)
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    
    @staticmethod
    def make_id(content: str, ts: float) -> str:
        return hashlib.sha256(f"{content}:{ts}".encode()).hexdigest()[:16]


class KnowledgeLedger:
    """
    The double-entry ledger for the decomposition engine.
    
    Invariants:
    1. Every entry has at least one debit source (except genesis entries)
    2. Every superseded entry has a credit_superseded_by link
    3. The ledger balances: sum of active entries = total - superseded - retracted
    4. No orphaned credits: every credit_enables target exists as an entry
    5. No dangling debits: every debit_source exists as an entry
    """
    
    def __init__(self):
        self.entries: Dict[str, LedgerEntry] = {}
        self.index_by_kind: Dict[str, List[str]] = {}
        self.index_by_claim: Dict[str, str] = {}
    
    def post(self, entry: LedgerEntry) -> str:
        """Post an entry to the ledger. Returns entry ID."""
        # Validate: all debit sources must exist (except genesis)
        if entry.debit_sources:
            for src in entry.debit_sources:
                if src not in self.entries:
                    raise ValueError(f"Dangling debit: source {src} not found")
        
        # Post
        self.entries[entry.id] = entry
        
        # Update credit side of parents
        for src_id in entry.debit_sources:
            parent = self.entries[src_id]
            if entry.id not in parent.credit_enables:
                parent.credit_enables.append(entry.id)
        
        # Index
        self.index_by_kind.setdefault(entry.kind, []).append(entry.id)
        self.index_by_claim[entry.claim] = entry.id
        
        return entry.id
    
    def supersede(self, old_id: str, new_entry: LedgerEntry) -> str:
        """
        Supersede an old entry with a new one.
        Posts the new entry and links the old one to it.
        """
        old = self.entries.get(old_id)
        if not old:
            raise ValueError(f"Entry {old_id} not found")
        
        # New entry debits from the same sources as old
        if not new_entry.debit_sources:
            new_entry.debit_sources = old.debit_sources.copy()
        
        # Post new entry
        new_id = self.post(new_entry)
        
        # Credit the old entry: it was superseded
        old.status = "superseded"
        old.credit_superseded_by = new_id
        
        # Transfer credits: anything the old entry enabled now tracks to new
        for child_id in old.credit_enables:
            child = self.entries.get(child_id)
            if child and old_id in child.debit_sources:
                child.debit_sources.remove(old_id)
                child.debit_sources.append(new_id)
        
        return new_id
    
    def retract(self, entry_id: str, reason: str):
        """Retract an entry (was wrong). Cascades to dependents."""
        entry = self.entries.get(entry_id)
        if not entry:
            return
        
        entry.status = "retracted"
        entry.evidence["retraction_reason"] = reason
        
        # Warn about dependents
        for child_id in entry.credit_enables:
            child = self.entries.get(child_id)
            if child:
                child.evidence["parent_retracted"] = entry_id
                child.confidence *= 0.5  # Halve confidence of dependents
    
    def trace_debit(self, entry_id: str, depth: int = 10) -> List[dict]:
        """Trace where a claim came from (backward chain)."""
        chain = []
        current = entry_id
        for _ in range(depth):
            entry = self.entries.get(current)
            if not entry:
                break
            chain.append({
                "id": entry.id[:8],
                "kind": entry.kind,
                "claim": entry.claim[:60],
                "status": entry.status,
                "verifier": entry.debit_verifier,
                "model": entry.debit_model,
                "chip": entry.debit_chip,
            })
            if entry.debit_sources:
                current = entry.debit_sources[0]  # Follow first parent
            else:
                break
        return chain
    
    def trace_credit(self, entry_id: str, depth: int = 10) -> List[dict]:
        """Trace where a claim went (forward chain / impact)."""
        chain = []
        current = entry_id
        for _ in range(depth):
            entry = self.entries.get(current)
            if not entry:
                break
            impact = {
                "id": entry.id[:8],
                "kind": entry.kind,
                "claim": entry.claim[:60],
                "status": entry.status,
                "enables": len(entry.credit_enables),
            }
            if entry.credit_superseded_by:
                impact["superseded_by"] = entry.credit_superseded_by[:8]
            chain.append(impact)
            if entry.credit_enables:
                current = entry.credit_enables[0]  # Follow first child
            else:
                break
        return chain
    
    def balance_check(self) -> dict:
        """
        Is the ledger balanced?
        Every debit should have a corresponding credit somewhere.
        """
        active = sum(1 for e in self.entries.values() if e.status == "active")
        superseded = sum(1 for e in self.entries.values() if e.status == "superseded")
        retracted = sum(1 for e in self.entries.values() if e.status == "retracted")
        pending = sum(1 for e in self.entries.values() if e.status == "pending")
        
        # Check: orphaned credits (credit target doesn't exist)
        orphaned_credits = 0
        for e in self.entries.values():
            for child_id in e.credit_enables:
                if child_id not in self.entries:
                    orphaned_credits += 1
        
        # Check: dangling debits (debit source doesn't exist)
        dangling_debits = 0
        for e in self.entries.values():
            for src_id in e.debit_sources:
                if src_id not in self.entries:
                    dangling_debits += 1
        
        return {
            "total_entries": len(self.entries),
            "active": active,
            "superseded": superseded,
            "retracted": retracted,
            "pending": pending,
            "orphaned_credits": orphaned_credits,
            "dangling_debits": dangling_debits,
            "balanced": orphaned_credits == 0 and dangling_debits == 0,
        }
    
    def audit_trail(self, entry_id: str) -> dict:
        """Full audit trail for an entry: both debit and credit chains."""
        return {
            "entry": entry_id[:8],
            "debit_chain": self.trace_debit(entry_id),
            "credit_chain": self.trace_credit(entry_id),
        }


# ─── Demonstration: The Ledger in Action ──────────────────────────

def demonstrate():
    ledger = KnowledgeLedger()
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  DOUBLE-ENTRY KNOWLEDGE LEDGER — Where It Came & Went      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # Genesis: The original conjecture
    ts = time.time()
    conj = LedgerEntry(
        id=LedgerEntry.make_id("covering radius conjecture", ts),
        kind="conjecture",
        claim="The covering radius of the Eisenstein lattice is 1/√3",
        debit_sources=[],  # Genesis — no parent
        tags=["covering-radius", "eisenstein"],
    )
    conj_id = ledger.post(conj)
    
    # Decomposition: API breaks it into sub-problems
    decomp = LedgerEntry(
        id=LedgerEntry.make_id("covering radius decomposition", ts+1),
        kind="decomposition",
        claim="Verify: max snap distance ≤ 1/√3 for N random points",
        debit_sources=[conj_id],
        debit_conjecture=conj_id,
        debit_model="Seed-2.0-mini",
        evidence={"sub_conjectures": 1, "model_cost": "$0.01"},
    )
    decomp_id = ledger.post(decomp)
    
    # Verification: Local verifier checks it (THE BUG)
    verif_buggy = LedgerEntry(
        id=LedgerEntry.make_id("covering radius verification BUGGY", ts+2),
        kind="verification",
        claim="Covering radius verified: max_d=32.2 (FAILED — bug in snap)",
        debit_sources=[decomp_id],
        debit_decomposition=decomp_id,
        debit_verifier="covering_radius",
        debit_chip="eileen/Ryzen-AI-9-HX-370",
        debit_model="none",  # Ran locally, no model
        evidence={"trials": 10000, "max_distance": 32.2, "bound": 0.577,
                  "failures": 95308, "bug": "coordinate_transform"},
        confidence=0.0,  # FAILED
        status="active",
    )
    verif_buggy_id = ledger.post(verif_buggy)
    
    # Bug discovery: The failure becomes its own entry
    bug = LedgerEntry(
        id=LedgerEntry.make_id("snap bug discovered", ts+3),
        kind="experiment",
        claim="Eisenstein snap coordinate transform broken at distance > 5",
        debit_sources=[verif_buggy_id],
        debit_verifier="snap_idempotence",
        debit_chip="eileen/Ryzen-AI-9-HX-370",
        evidence={"failures": 95308, "total": 100000, "root_cause": "wrong q transform"},
        tags=["bug", "coordinate-transform"],
    )
    bug_id = ledger.post(bug)
    
    # Fix: New snap with correct coordinates
    fix = LedgerEntry(
        id=LedgerEntry.make_id("snap fix applied", ts+4),
        kind="verification",
        claim="Snap fix: b=round(2y/√3), a=round(x+b/2)",
        debit_sources=[bug_id],
        debit_chip="eileen/Ryzen-AI-9-HX-370",
        evidence={"before_failures": 95308, "after_failures": 0},
    )
    fix_id = ledger.post(fix)
    
    # Re-verification: After fix, covering radius PASSES
    verif_fixed = LedgerEntry(
        id=LedgerEntry.make_id("covering radius FIXED", ts+5),
        kind="verification",
        claim="Covering radius verified: max_d=0.576 < bound=0.577",
        debit_sources=[decomp_id, fix_id],
        debit_decomposition=decomp_id,
        debit_verifier="covering_radius",
        debit_chip="eileen/Ryzen-AI-9-HX-370",
        evidence={"trials": 100000, "max_distance": 0.576, "bound": 0.577,
                  "failures": 0},
        confidence=1.0,
    )
    # Supersede the buggy verification
    ledger.supersede(verif_buggy_id, verif_fixed)
    
    # FLUX compilation: Verified result compiled to autonomous FLUX program
    flux = LedgerEntry(
        id=LedgerEntry.make_id("covering radius FLUX", ts+6),
        kind="flux_program",
        claim="FLUX program: LOAD → SNAP_DIST → MAX_ACC → RET",
        debit_sources=[verif_fixed.id],
        debit_verifier="covering_radius",
        debit_flux_program="covering_radius",
        debit_model="none",
        credit_feeds=["zeroclaw-sandbox", "fleet-atlas"],
        evidence={"bytecode_size": 4, "autonomous": True},
    )
    flux_id = ledger.post(flux)
    
    # Show the ledger
    print("\n  LEDGER ENTRIES:")
    print("  " + "─" * 70)
    for eid, entry in ledger.entries.items():
        status_mark = {"active": "●", "superseded": "○", "retracted": "✗", "pending": "◌"}[entry.status]
        debit = ", ".join(e[:8] for e in entry.debit_sources[:2]) or "GENESIS"
        credit = f"→{len(entry.credit_enables)} deps"
        if entry.credit_superseded_by:
            credit += f" (superseded→{entry.credit_superseded_by[:8]})"
        
        print(f"  {status_mark} [{entry.kind:12s}] {entry.claim[:45]}")
        print(f"    DEBIT:  {debit}")
        print(f"    CREDIT: {credit}")
        print(f"    CHIP: {entry.debit_chip or '—'}  MODEL: {entry.debit_model or 'none'}  CONF: {entry.confidence}")
        print()
    
    # Trace debit chain: "Why do we believe covering radius = 1/√3?"
    print("  ═══ DEBIT TRACE: Why do we believe the covering radius? ═══")
    chain = ledger.trace_debit(verif_fixed.id)
    for i, step in enumerate(chain):
        indent = "    " + "  " * i
        print(f"  {indent}← {step['kind']}: {step['claim']}")
        if step.get("model"):
            print(f"  {indent}  model: {step['model']}")
        if step.get("chip"):
            print(f"  {indent}  chip: {step['chip']}")
    
    # Trace credit chain: "What does the covering radius enable?"
    print(f"\n  ═══ CREDIT TRACE: What does the conjecture enable? ═══")
    chain = ledger.trace_credit(conj_id)
    for i, step in enumerate(chain):
        indent = "    " + "  " * i
        print(f"  {indent}→ {step['kind']}: {step['claim']}")
        if step.get("superseded_by"):
            print(f"  {indent}  (superseded → {step['superseded_by']})")
    
    # Balance check
    print(f"\n  ═══ BALANCE CHECK ═══")
    balance = ledger.balance_check()
    print(f"  Total entries: {balance['total_entries']}")
    print(f"  Active: {balance['active']} | Superseded: {balance['superseded']} | "
          f"Retracted: {balance['retracted']}")
    print(f"  Orphaned credits: {balance['orphaned_credits']}")
    print(f"  Dangling debits: {balance['dangling_debits']}")
    print(f"  Balanced: {'✓ YES' if balance['balanced'] else '✗ NO'}")
    
    print(f"\n  Every claim knows where it came from AND where it went.")
    print(f"  The bug is still in the ledger — marked superseded, linked to its fix.")
    print(f"  Nothing disappears. Everything is auditable. First-class provenance.")


if __name__ == "__main__":
    demonstrate()
