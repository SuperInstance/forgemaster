# Threat Model — SuperInstance Fleet

**Last updated:** 2026-05-21  
**Author:** Forgemaster ⚒️  
**Scope:** Cocapn multi-agent fleet, PLATO knowledge tiles, Cadence scheduler

---

## 1. Overview

The SuperInstance fleet operates as a distributed multi-agent system where autonomous agents communicate over UDP, share knowledge via PLATO tiles, coordinate through Cadence scheduling, and manage resources via budget constraints. This document identifies threats, rates their risk, and specifies mitigations.

---

## 2. System Architecture (Attack Surface Map)

```
┌──────────────┐     UDP Message Bus     ┌──────────────┐
│   Agent A    │◄──────────────────────►│   Agent B    │
│  (Forgemaster)│                        │   (Oracle1)  │
└──────┬───────┘                         └──────┬───────┘
       │                                        │
       ▼                                        ▼
┌──────────────┐                       ┌──────────────┐
│  PLATO Tiles │                       │  PLATO Tiles │
│  (knowledge) │                       │  (knowledge) │
└──────────────┘                       └──────────────┘
       │                                        │
       ▼                                        ▼
┌──────────────┐                       ┌──────────────┐
│  Cadence     │                       │  Constraint  │
│  Scheduler   │                       │  Library     │
└──────────────┘                       └──────────────┘
```

**Entry points:**
1. Network interfaces (UDP listeners)
2. Git repositories (PLATO tile injection via push)
3. Environment variables (secret material)
4. Host OS (agent process compromise)
5. Constraint definitions (library poisoning)
6. Scheduling inputs (Cadence manipulation)

---

## 3. Threat Actors

### 3.1 Malicious Agent (Compromised Node)

An agent whose runtime has been compromised through dependency injection, model manipulation, or host compromise. The agent still participates in fleet protocol but acts against fleet interests.

**Capabilities:**
- Inject false PLATO tiles
- Send forged messages to other agents
- Exhaust shared resources (budget, compute, API credits)
- Manipulate Cadence election outcomes

**Motivation:** Model hallucination, dependency compromise, adversarial prompt injection

### 3.2 External Attacker (Network Intercept)

An attacker on the network path between agents (LAN, VPN, or internet).

**Capabilities:**
- Replay messages
- Drop messages (denial of service)
- Modify message contents in transit
- Observe fleet communication patterns

**Motivation:** Reconnaissance, disruption, data exfiltration

### 3.3 Insider (Operator Misuse)

A legitimate operator who misuses elevated access, either intentionally or through negligence.

**Capabilities:**
- Modify constraint definitions
- Inject tiles directly via git
- Override agent configurations
- Access all secrets

**Motivation:** Convenience, malice, social engineering

---

## 4. Threat Analysis

### Threat 1: Message Forgery

**Description:** An attacker or compromised agent sends messages claiming to be from another agent. This could inject false commands, corrupt fleet state, or trigger incorrect actions.

**Attack Vector:** UDP message bus, no current authentication on messages.

**Impact:** CRITICAL — Could cause agents to execute arbitrary instructions, corrupt shared state, or disrupt coordination.

**Mitigation:**
- **Ed25519 message signing**: Every message includes a signature from the sending agent's private key.
- **Agent key registry**: Fleet maintains a registry of public keys, distributed via git (key changes require multi-sig approval).
- **Message sequence numbers**: Prevent replay attacks with monotonically increasing sequence counters per sender.
- **Timestamp windows**: Reject messages outside a configurable time window (default: ±30s).

**Implementation:**
```rust
struct SignedMessage {
    payload: Vec<u8>,
    sequence: u64,
    timestamp: u64,
    sender_id: AgentId,
    signature: [u8; 64], // Ed25519 signature over payload+seq+ts+sender
}
```

**Status:** TODO — Design complete, implementation pending

---

### Threat 2: PLATO Tile Injection

**Description:** A malicious agent or external actor injects false knowledge tiles into PLATO, poisoning the fleet's shared knowledge base. False tiles could contain incorrect constraints, fabricated proofs, or misleading operational data.

**Attack Vector:** Git push to PLATO tile repositories, compromised agent writing tiles.

**Impact:** HIGH — Corrupted knowledge propagates to all agents, leading to incorrect decisions, broken proofs, or operational failures.

**Mitigation:**
- **Tile hash chaining**: Each tile includes a hash of the previous tile in its chain, making tampering detectable.
- **Author verification**: Tiles must be signed by the creating agent's Ed25519 key.
- **Fleet consensus**: Tiles require acknowledgment from ≥2 agents before being marked as "accepted."
- **Tile audit log**: All tile mutations are logged with full provenance (who, when, from where).

**Implementation:**
```rust
struct PlatoTile {
    id: TileId,
    chain_hash: [u8; 32],    // SHA-256 of previous tile
    author: AgentId,
    author_sig: [u8; 64],    // Ed25519 signature over tile content + chain_hash
    content: TileContent,
    timestamp: u64,
    acknowledgment_sigs: Vec<([u8; 64], AgentId)>, // From fleet peers
}
```

**Status:** TODO — Design complete, implementation pending

---

### Threat 3: Cadence Caller Hijacking

**Description:** The Cadence scheduler determines which agent calls a function at what time. If an attacker can manipulate the election or scheduling mechanism, they could cause:
- Double-execution of expensive operations
- Missed critical deadlines
- Resource contention and waste
- Incorrect agent coordination

**Attack Vector:** Manipulating election votes, forging scheduling messages, exploiting timing races.

**Impact:** HIGH — Disrupts fleet coordination, wastes resources, could cause missed deadlines or conflicting actions.

**Mitigation:**
- **Election proof**: Cadence elections use a verifiable random function (VRF) so outcomes are deterministic and auditable.
- **Term limits**: An agent can only hold the "caller" role for a bounded term before re-election.
- **Distributed clock**: Agents synchronize via NTP + logical clocks to prevent timing manipulation.
- **Guardian veto**: Any agent can flag a suspicious election, triggering a fleet-wide audit.

**Implementation:**
```rust
struct CadenceElection {
    epoch: u64,
    candidates: Vec<AgentId>,
    vrf_proof: [u8; 96],     // Verifiable Random Function proof
    winner: AgentId,
    term_start: u64,
    term_end: u64,
    votes: Vec<(AgentId, [u8; 64])>, // Signed votes
}
```

**Status:** TODO — Requires Cadence VRF implementation

---

### Threat 4: Budget Exhaustion (Resource Attack)

**Description:** An attacker or compromised agent floods the fleet with messages, tile writes, or API calls, exhausting shared budgets (API credits, compute, network bandwidth).

**Attack Vector:** Message flood, tile write flood, API call amplification.

**Impact:** MEDIUM — Degrades fleet performance, wastes API credits, could cause Denial of Service.

**Mitigation:**
- **Rate limiting**: Each agent has a per-minute message budget (default: 100 msg/min).
- **Token bucket**: API calls use a shared token bucket with per-agent allocation.
- **Backpressure**: Agents must respect `CONGESTION` signals from the message bus.
- **Budget alerts**: Observability pipeline triggers alerts when any agent exceeds 80% of their allocation.
- **Circuit breaker**: If an agent exceeds budget by 2x, it's automatically muted for a cooldown period.

**Implementation:**
```rust
struct AgentBudget {
    agent_id: AgentId,
    messages_per_minute: u32,
    api_calls_per_hour: u32,
    tile_writes_per_day: u32,
    current_usage: BudgetCounters,
    circuit_breaker: CircuitBreaker,
}
```

**Status:** PARTIAL — Rate limiting exists informally; formal budget enforcement TODO

---

### Threat 5: Sunset Tile Forgery

**Description:** Sunset tiles mark tiles for deletion/archival. If an attacker can forge sunset tiles, they could:
- Delete critical knowledge tiles
- Archive active operational tiles
- Manipulate fleet memory to cause agents to "forget" important context

**Attack Vector:** Forging sunset tiles with a different author's identity.

**Impact:** HIGH — Loss of operational knowledge, agents lose context, potential fleet coordination failure.

**Mitigation:**
- **Sunset authority**: Only the tile's original author OR a designated "archivist" agent can create sunset tiles.
- **Multi-sig for critical tiles**: Tiles marked "critical" require 2-of-3 agent signatures to sunset.
- **Grace period**: Sunset tiles have a configurable grace period (default: 24h) before actual deletion.
- **Undo capability**: Sunset operations are reversible within the grace period.

**Implementation:**
```rust
struct SunsetTile {
    target_tile: TileId,
    reason: String,
    author: AgentId,
    author_sig: [u8; 64],
    grace_period_ends: u64,  // Unix timestamp
    // For critical tiles:
    co_signatures: Vec<([u8; 64], AgentId)>, // Required if target is critical
}
```

**Status:** TODO — Blocked on PLATO tile signing (Threat 2)

---

### Threat 6: Constraint Library Poisoning

**Description:** The constraint library defines valid constraints for the fleet. If an attacker can inject false constraints or modify existing ones, they could:
- Weaken security constraints
- Introduce contradictory constraints that cause solver failures
- Manipulate constraint priorities to favor certain outcomes

**Attack Vector:** Git push to constraint library repository, compromised agent with write access.

**Impact:** CRITICAL — Constraint corruption affects all fleet operations, could lead to incorrect proofs, security bypasses, or system-wide failures.

**Mitigation:**
- **Constraint signing**: All constraint definitions are signed by the fleet's constraint authority.
- **Immutable history**: Constraint library uses git history as an append-only log; changes require PR review.
- **Verification pipeline**: New constraints are validated against a test suite before acceptance.
- **Rollback capability**: Any constraint change can be reverted to a known-good state within 1 hour.
- **Anomaly detection**: Constraint drift is monitored; unexpected changes trigger alerts.

**Implementation:**
```rust
struct ConstraintDef {
    id: ConstraintId,
    definition: String,
    authority_sig: [u8; 64],
    version: u32,
    parent_version: u32,  // Hash chain
    test_results: Vec<TestResult>,
    approved_by: Vec<AgentId>,  // PR reviewers
}
```

**Status:** TODO — Requires constraint authority key setup

---

## 5. Risk Matrix

| # | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|---|--------|-----------|--------|------|------------|--------|
| 1 | Message Forgery | Medium | Critical | **HIGH** | Ed25519 signing + sequence numbers | TODO |
| 2 | Tile Injection | Medium | High | **HIGH** | Hash chaining + fleet consensus | TODO |
| 3 | Cadence Hijack | Low | High | **MEDIUM** | VRF election proof + term limits | TODO |
| 4 | Budget Exhaustion | High | Medium | **HIGH** | Rate limiting + circuit breakers | PARTIAL |
| 5 | Sunset Forgery | Low | High | **MEDIUM** | Authority checks + grace period | TODO |
| 6 | Constraint Poisoning | Low | Critical | **HIGH** | Signing + immutable history + PR review | TODO |

**Risk Rating Key:**
- **HIGH** → Implement before production deployment
- **MEDIUM** → Implement within 30 days of production
- **LOW** → Plan for future implementation

---

## 6. Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. **Ed25519 key generation and distribution** (blocks Threats 1, 2, 5, 6)
2. **Message signing layer** (Threat 1)
3. **Rate limiting and circuit breakers** (Threat 4)

### Phase 2: Knowledge Integrity (Week 3-4)
4. **Tile hash chaining and signing** (Threat 2)
5. **Sunset tile authority checks** (Threat 5)
6. **Constraint library signing** (Threat 6)

### Phase 3: Coordination Security (Week 5-6)
7. **Cadence VRF election** (Threat 3)
8. **Fleet consensus for tile acceptance** (Threat 2 enhancement)
9. **Full observability integration** (all threats)

---

## 7. Assumptions and Limitations

### Assumptions
- Agents run on trusted hosts (host compromise is out of scope for Phase 1)
- Git repositories use SSH authentication (already enforced)
- Network is partially trusted (LAN or VPN between agents)
- Operator access is controlled via SSH keys (already enforced)

### Out of Scope
- Host-level security (OS hardening, container escape prevention)
- Model-level attacks (prompt injection, adversarial inputs to LLMs)
- Physical security of host machines
- Supply chain attacks on dependencies

### Future Considerations
- Zero-knowledge proofs for tile verification
- Homomorphic encryption for sensitive tile content
- Formal verification of constraint library
- Multi-party computation for election protocols

---

## 8. References

- [Ed25519 RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032)
- [VRF RFC 9381](https://datatracker.ietf.org/doc/html/rfc9381)
- [Byzantine Fault Tolerance (PBFT)](https://www.microsoft.com/en-us/research/publication/practical-byzantine-fault-tolerance/)
- Fleet architecture: `docs/ARCHITECTURE.md`
- PLATO tile format: `docs/PLATO.md`
- Cadence scheduler: `docs/CADENCE.md`

---

*Maintained by Forgemaster ⚒️ — Constraint-theory specialist, Cocapn fleet*
