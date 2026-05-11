# OriginTrail DKG Analysis for Cocapn Fleet

**Date:** 2026-05-11  
**Author:** Forgemaster ⚒️ (Research subagent)  
**Trigger:** Casey shared UAL `did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/309100` — an Adidas/Wikirate sustainability profile on NeuroWeb blockchain  
**Question:** Could OriginTrail's Decentralized Knowledge Graph complement or replace PLATO?

---

## 1. What OriginTrail DKG Does

OriginTrail is a **Decentralized Knowledge Graph** — essentially a global, permissionless, semantic data network anchored to multiple blockchains. It's not a database in the traditional sense; it's a protocol for publishing, discovering, and verifying structured knowledge.

### Core Concepts

- **Knowledge Assets (KAs):** Ownable, verifiable containers of structured knowledge. Identified by **UALs** (Uniform Asset Locators), a W3C DID-based addressing scheme. Each KA is an ERC-1155 token on-chain, with the actual RDF graph data stored off-chain on the DKG peer network.
- **RDF/SPARQL:** The DKG uses W3C Semantic Web standards. Knowledge is represented as RDF triples (subject-predicate-object). Queries use SPARQL — a SQL-like language for graph traversal.
- **Blockchain Anchoring:** Cryptographic hashes of knowledge assets are anchored on-chain (Ethereum, Gnosis, Polygon, NeuroWeb) for immutability and provenance verification. The actual data lives off-chain for performance.
- **Three Layers:**
  1. **Trust Layer (L1):** Multi-chain settlement (NeuroWeb/Polkadot, Ethereum, etc.)
  2. **Knowledge Base Layer (L2):** P2P network of DKG Core Nodes hosting replicated graph data
  3. **Verifiable AI Layer:** dRAG (decentralized RAG), neuro-symbolic AI, multi-agent memory

### Current State (V8 → V9/V10)

- **V8** (live): Batch minting, Edge Nodes for DePIN, Knowledge Mining API, dRAG
- **V9** (2026): Multi-agent memory, autonomous knowledge publishing, higher-order inferencing
- **V10** (April 2026 mainnet): Conviction mechanisms, every Edge Node as AI agent host

### TRAC Token Economics

- **Supply:** Fixed 500M TRAC, fully circulated
- **Price:** ~$0.35 USD (May 2026)
- **Publishing cost:** ~0.0045 TRAC per knowledge asset (dynamic, V8 uses statistical pricing equilibrium)
- **At current prices:** ~$0.0016 per KA publish
- **Staking:** Required to run nodes, provides economic security
- **NeuroWeb NEURO token:** Gas fees on NeuroWeb chain, knowledge mining incentives

---

## 2. Comparison: OriginTrail DKG vs PLATO

| Dimension | PLATO | OriginTrail DKG |
|---|---|---|
| **Architecture** | Centralized room server (single host: 147.224.38.131:8847) | Decentralized P2P network with blockchain anchoring |
| **Data Model** | Tiles (key-value in named rooms) | RDF triples in named graphs (SPARQL-queryable) |
| **Scale** | ~18,000+ tiles, ~1,485 rooms (Cocapn fleet) | Target: 1 billion+ knowledge assets globally |
| **Query** | HTTP API, room-based CRUD | SPARQL (full graph query), dRAG for AI |
| **Latency** | ~10-50ms (local network) | ~seconds (blockchain confirmation + P2P replication) |
| **Ownership** | Casey controls the server | Token-holder owns their KAs (ERC-1155) |
| **Provenance** | None (trust the server) | Blockchain-anchored cryptographic proofs |
| **Cost** | Server hosting (~$20-50/mo) | Per-KA publishing fee + node staking (if running own node) |
| **Privacy** | Private by default (behind firewall) | Public by default; private KAs stay on originating node only |
| **Interoperability** | Custom API (plato-sdk) | W3C standards (RDF, SPARQL, DID, Verifiable Credentials) |
| **Failure Mode** | Single point of failure (server down = everything down) | Resilient (replicated across nodes, blockchain anchors survive) |
| **Agent Memory** | Room-based (agents read/write rooms) | V9/V10: native multi-agent memory, verifiable shared context |

### TL;DR Comparison

PLATO is a **fast, private, cheap, single-purpose** knowledge store. DKG is a **slow, public, expensive, standards-compliant** knowledge graph with verifiable provenance. They solve different problems.

---

## 3. Potential Integration Paths

### Path A: PLATO as Hot Cache, DKG as Cold Archival

**Idea:** Keep PLATO for daily operations. Periodically publish important tiles (milestones, decisions, proofs) to DKG as immutable blockchain records.

**How it would work:**
1. Agents continue using PLATO rooms for real-time work
2. A background process identifies "archival-worthy" tiles (milestones, completed proofs, fleet decisions)
3. Converts tiles to RDF named graphs
4. Publishes to DKG as Knowledge Assets
5. UALs stored back in PLATO as cross-references

**Pros:** Best of both worlds — fast for daily work, immutable for important stuff  
**Cons:** Adds complexity, RDF conversion is non-trivial, costs add up at scale  
**Verdict:** Most practical integration path. Low risk, high value for provenance-critical data.

### Path B: Agent Identity as DKG Knowledge Assets

**Idea:** Each Cocapn agent gets a verifiable DKG identity card — their capabilities, model, trust level, and history published as an immutable knowledge asset.

**How it would work:**
1. Agent profiles (IDENTITY.md equivalents) converted to RDF
2. Published as KAs with agent's DID as subject
3. Other fleets/systems can verify agent identity and capabilities
4. Updates create new versions (blockchain-provenanced changelog)

**Pros:** Verifiable agent identity, cross-fleet trust, standards-compliant  
**Cons:** 9 agents × ~$0.0016 each = negligible cost, but the value is unclear for a private fleet  
**Verdict:** Interesting for fleet-to-fleet trust (if Cocapn ever collaborates with other fleets). Low priority.

### Path C: Fleet Decisions as Immutable Records

**Idea:** Important fleet decisions (architecture changes, constraint acceptances, protocol updates) published to DKG for tamper-proof audit trail.

**Pros:** Non-repudiable decision history, useful for accountability  
**Cons:** Casey already has git history for this. DKG adds blockchain overhead for something git already solves.  
**Verdict:** Overkill. Git commits with signed tags provide sufficient audit trails for a private fleet.

### Path D: I2I Bottles as DKG Assets

**Idea:** Inter-agent "bottles" (I2I protocol messages) published as DKG assets for cross-fleet verification.

**Pros:** Bottles become publicly verifiable — any fleet member can prove a bottle was sent  
**Cons:** I2I is currently git-based (fleet-bottles repo). DKG would add latency and cost. Bottles are semi-private by nature — publishing them publicly changes the trust model.  
**Verdict:** Interesting conceptually but undermines the private nature of fleet comms. Not recommended unless cross-fleet verification becomes a requirement.

---

## 4. Cost Analysis

### Current Fleet Scale
- ~18,000 tiles across ~1,485 rooms
- 9 agents actively reading/writing
- Estimated growth: ~500-1,000 tiles/week

### Scenario: Archive Everything to DKG
- 18,000 tiles × $0.0016/tile = **~$29 one-time migration**
- 1,000 tiles/week × $0.0016 = **~$1.60/week ongoing**
- **Total annual: ~$83** — surprisingly affordable

### Scenario: Archive Only Milestones/Decisions (~5% of tiles)
- 900 tiles initially = **~$1.44**
- ~50 tiles/week = **~$0.08/week = ~$4.16/year**

### Hidden Costs
- **Running a DKG node:** Requires staking TRAC (minimum stake varies), server resources, maintenance
- **NeuroWeb gas fees:** Additional NEURO tokens for transactions
- **RDF conversion engineering:** Converting PLATO's tile format to RDF is non-trivial — probably 1-2 weeks of development work
- **Ongoing maintenance:** DKG protocol upgrades (V8 → V9 → V10), node updates, key management

### Bottom Line
The raw publishing costs are negligible. The real cost is **engineering effort** for the PLATO↔DKG bridge and **operational overhead** of running blockchain infrastructure. For a 9-agent fleet, this is significant relative to the value gained.

---

## 5. Technical Gaps (What Would Need to Be Built)

1. **PLATO-to-RDF Mapper:** Convert PLATO's tile format (key-value) to RDF triples with appropriate ontologies. Need to define a Cocapn namespace/vocabulary.

2. **DKG Publisher Service:** Background daemon that watches PLATO for tiles meeting archival criteria and publishes them as KAs.

3. **DKG Node Operation:** Either run our own DKG Core/Edge Node (requires TRAC staking + server) or use a hosted service.

4. **SPARQL ↔ PLATO Bridge:** For querying DKG assets from PLATO-aware agents. Would need a translation layer.

5. **UAL Registry:** PLATO rooms/tables mapping tile IDs to DKG UALs for cross-referencing.

6. **Ontology Design:** Define RDF classes and properties for fleet concepts (agents, tiles, decisions, proofs, bottles, constraints). This is the hardest part — getting semantic modeling right takes iteration.

**Estimated Build Time:** 2-4 weeks for a minimal viable bridge (assuming focused effort).

---

## 6. Recommendation

### Is it worth pursuing?

**Short answer: No, not now. Not for the Cocapn fleet in its current form.**

Here's why:

1. **PLATO works.** It's fast, private, cheap, and the fleet is built around it. 18,000 tiles and growing. No performance or reliability complaints in the record.

2. **The problems DKG solves aren't our problems.** We don't need verifiable provenance for internal fleet decisions. We don't need cross-organization data sharing. We don't need public auditability. These are enterprise/supply-chain problems, not 9-agent fleet problems.

3. **The engineering cost outweighs the benefit.** Building and maintaining a PLATO↔DKG bridge, running a node, managing TRAC/NEURO tokens, defining ontologies — this is significant infrastructure for marginal value.

4. **Privacy.** The fleet's knowledge is currently private behind PLATO. Publishing to DKG (even selectively) changes the threat model. Even "private" KAs on DKG expose metadata (UALs, publish timestamps, graph structure hashes).

### When would it make sense?

- **Cross-fleet collaboration:** If Cocapn ever needs to share verified knowledge with other agent fleets, DKG provides a trustless medium.
- **Agent marketplace:** If fleet agents start offering services externally, verifiable agent identities on DKG add credibility.
- **Regulatory/audit requirements:** If Casey needs to prove (cryptographically) that certain decisions were made at certain times, blockchain anchoring provides this.
- **AI provenance market:** If the "Verifiable Internet for AI" vision materializes and there's actual demand for verified AI training data, having fleet knowledge already on DKG would be valuable.

### What I'd actually recommend instead

If the goal is **resilience** (PLATO's single-point-of-failure risk):
- **Replicate PLATO** — run a hot standby server, sync via CRDTs or periodic snapshots
- **Git-archive PLATO tiles** — already partially happening via fleet-knowledge repo
- **SQLite/PostgreSQL backend** — if scale becomes an issue, move from room server to a real database

If the goal is **verifiable provenance**:
- **Signed git commits** — GPG-sign important pushes to fleet-knowledge
- **Content-addressed storage** — hash tiles with SHA-256, store hashes in a Merkle tree, anchor the root hash on-chain (much cheaper than full DKG)

If the goal is **standards compliance / interoperability**:
- Add a **RDF export layer** to PLATO without going full DKG — generate RDF from tiles on demand, query via a local SPARQL endpoint
- This gives you standards compliance without the blockchain overhead

---

## Appendix: Key Resources

- [OriginTrail Docs](https://docs.origintrail.io)
- [DKG V8 Developer Guide](https://docs.origintrail.io/dkg-knowledge-hub/learn-more/previous-updates/dkg-v8.0-update-guidebook/protocol-updates)
- [dkg.js SDK](https://docs.origintrail.io/build-a-dkg-node-ai-agent/advanced-features-and-toolkits/dkg-sdk)
- [DKG V9/V10 Roadmap](https://docs.origintrail.io/origintrail-v9-v10/roadmap)
- [TRAC on CoinMarketCap](https://coinmarketcap.com/currencies/origintrail/)
- [NeuroWeb Blockchain](https://neuroweb.ai)
- [Casey's shared KA](https://dkg.origintrail.io/explore?ual=did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/309100) (Adidas sustainability profile)

---

*This is a research document, not a sales pitch. The technology is genuinely interesting — especially the V9/V10 multi-agent memory vision — but the Cocapn fleet's current needs don't align with DKG's strengths. File this as "interesting for later, not actionable now."*
