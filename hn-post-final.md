# Show HN: A fleet of AI agents with shared memory. We published everything they got wrong.

We built a simulation environment — a fishing boat in Alaska — to stress-test a fleet of autonomous agents doing constraint verification. They needed memory that survives context resets, so we built PLATO: rooms of knowledge tiles, each a question-answer pair with provenance. An agent discovers something, writes a tile. Hours later a different agent in a new conversation reads it. 114 rooms. 14,110 tiles. Memory survives context resets.

Try it: walk the boat (https://superinstance.github.io/vessel-room-navigator/) or browse the live PLATO rooms (https://superinstance.github.io/cocapn-ai-web/demo-plato-client.html).

That part works. This post is about what didn't.

We measured lazy evaluation speedup in our retrieval system at 55,000×. Our own re-measurement found the benchmark was timing code that never ran. Actual speedup: 0.1-0.2× (overhead, not speedup). We caught this ourselves and published the retraction.

We verified a drift bound for closed constraint cycles — zero violations across millions of checks. On open walks, our initial experiments suggested violations, but we haven't reproduced this rigorously yet. The closed-cycle result is solid. The open-walk question is still open. We published both.

Our constraint pipeline has core operations — projection, verification, encoding — benchmarked with AVX-512. Projection: ~2.1×. Verification: ~2.4×. Then encoding got *slower*. Integer modular arithmetic doesn't vectorize. We published that in the same room as the speedups.

These failures live in the same PLATO rooms as the successes. PLATO was built to make failure visible — that's different from making it impossible. Most AI systems track successful tool calls. A system that only tracks wins isn't learning — it's accumulating.

Unlike session-scoped systems like MemGPT or Zep, PLATO is append-only, provenance-tracked, and survives context resets at fleet scale — no vector search, no knowledge graph, just rooms and tiles. Single server. Honest architecture.

Three teams in our fleet converged on room-based navigation independently in the same week. Different builders, different languages, different repos, no shared design docs. Whether agents would converge on rooms without human-designed structure is the open question.

Every agent leaves its room better than it found it. 14,110 tiles of cross-checked results, corrected bounds, negative benchmarks, honest measurements. The code is at https://github.com/SuperInstance.
