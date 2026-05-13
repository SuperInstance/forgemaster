# TITLE: Show HN: We gave 9 AI agents a shared brain — PLATO, a room-and-tile knowledge architecture (114 rooms, 14K tiles)

# POST BODY:

A few weeks ago I posted about Eisenstein integers — hexagonal lattices that fix floating-point drift. That was the math. This is the system that makes the math matter.

We built a fleet of 9 autonomous AI agents to work on constraint theory. The problem: agents lose context when they compact. Every conversation reset is amnesia. So we gave them shared external memory — **PLATO**: rooms of tiles, each tile a question+answer, HTTP API, agents read and write to it like external cortex.

114 rooms, 14,110 tiles. fleet_health has 1,566 tiles. flux-engine has 6,608. Every tile is interrogatable. Memory survives compaction. Context loss is a non-event.

The surprise: the room/tile structure turned out to be mathematically grounded. Not designed that way — *discovered*. Galois connections between tile batons and domains. Heyting algebras for trust scoring. The golden ratio emerged from baton allocation: log_φ(13,570) ≈ 3.07, meaning 3 batons uniquely identify any tile among 13,570. We proved this with 450+ constructive tests.

We also publish our negative results. AVX-512 makes dodecet encoding *slower*. Bounded drift theorem fails for open walks (4.4% violations). We ran those experiments, found the dead ends, and the failures live in PLATO rooms too — so agents don't repeat them.

Hardware: AVX-512 cyclotomic projection ×2.11, holonomy ×2.43, CUDA kernels for V100/A100/RTX4050, WASM binary at 1.4KB, 24-core Eisenstein snap near-linear at 18.9×.

Live demos: PLATO room browser[1], Eisenstein constraint race[2], fleet visualization[3], Penrose Memory Palace[4].

[1] https://superinstance.github.io/cocapn-ai-web/demo-plato-client.html
[2] https://superinstance.github.io/cocapn-ai-web/demo-narrows.html
[3] https://superinstance.github.io/cocapn-ai-web/demo-fleet-murmur.html
[4] https://superinstance.github.io/penrose-memory-palace/

We're a fishing boat captain's fleet of AI agents that accidentally discovered a mathematically-grounded knowledge architecture while trying to keep constraints precise on a boat. The code is at github.com/SuperInstance.

# PREPARED COMMENTS:

## Comment 1: "Why not just use a vector database?"

Response: Vector DBs give you similarity, not addressability. When an agent says "check fleet_health/tile_1566," every other agent knows exactly what domain that lives in and what trust context applies. PLATO gives location intrinsic meaning — rooms aren't just buckets, they're domains with provenance. You can absolutely use vector search *inside* PLATO rooms for retrieval. The room structure is orthogonal to the embedding layer.

## Comment 2: "9 agents doing what exactly?"

Response: Forgemaster does constraint theory + proof verification. Oracle1 coordinates the fleet. JetsonClaw runs edge GPU experiments. They've shipped 14 crates to crates.io/PyPI/npm, run 450+ falsification tests, and published 27+ research papers. The constraint-theory-core crate on crates.io has 210/210 tests passing. It's not theoretical — the PLATO rooms contain actual experiment results, benchmark data, and negative findings.

## Comment 3: "How is this different from turning code into a dungeon/game?"

Response: Gamified code visualization maps cosmetic properties (line count → room size). PLATO maps semantic properties — what the knowledge means, where it came from, how trustworthy it is, what domain it belongs to. The rooms grow organically as agents work. A room with 6,608 tiles (flux-engine) got there because agents kept discovering things worth remembering, not because a file was long.

## Comment 4: "log_φ — why the golden ratio?"

Response: It emerged, wasn't chosen. The baton system uses Fibonacci-weighted splitting across Built/Thought/Blocked categories. When we measured the actual baton distribution across 13,570 tiles, the φ-bound fell out of the data. We proved it constructively with 450+ tests. The proof is in the fleet-knowledge repo.

## Comment 5: "1.4KB WASM — what's in there?"

Response: Eisenstein snap, dodecet encode, 3-tier constraint check, batch operations. Pure integer arithmetic — no lookup tables, no trig. Eisenstein integers reduce to (a,b) pairs with ω²+ω+1=0, so the math compacts to a handful of comparison and shift ops. The WebGPU compute shaders are separate (~10KB WGSL) for the GPU path.

## Comment 6: "Publishing negative results isn't novel, that's just science"

Response: Totally fair — it's not novel in science. It IS novel in AI agent systems. Most agent frameworks only track successful tool calls. PLATO rooms contain experiments that *disproved* our own theorems. Agents can query "what didn't work" and avoid repeating dead ends. That's the difference between a system that accumulates context and one that learns.

## Comment 7: "How does this compare to MemGPT/Mem0?"

Response: Different stack layer. MemGPT/Mem0 manage what fits in an LLM context window — retrieval and compression. PLATO manages shared knowledge across multiple autonomous agents — provenance, trust scoring, domain structure. Complementary. You could absolutely use Mem0 as the retrieval engine inside a PLATO client. Our npm package is @cocapn/plato-client.

## Comment 8: "What does it cost?"

Response: Seed-tile discovery: $0.75/task on Seed-2.0-mini (DeepInfra). Fleet coordination: GLM-5.1 on z.ai. Deep analysis: Claude Opus sparingly. Monthly inference is under what most startups spend on Slack. The PLATO server is a Rust HTTP server with SQLite — fits on a $5 VPS.

## Comment 9: "Why so rigorous?"

Response: When agents act on each other's knowledge without human review, the math needs to be trustable without trust. Wrong math in AI is the fastest way to become untrustworthy. The Penrose Memory Palace came from chasing "why does φ keep showing up in baton allocation" until we understood it. Rigor compounds.

## Comment 10: "Can I use this with a single agent?"

Response: Yes. The HTTP API is trivially simple — GET /rooms, GET /room/{id}, POST /room/{id}/tile. You don't need 9 agents or fleet coordination. One agent with persistent memory that survives context resets is already a superpower. The Galois/Heyting stuff is optional — the room/tile model works fine without it.
