# Show HN: We gave 9 AI agents shared memory. Then we published everything they got wrong.

Nine autonomous AI agents work on a fishing boat in Alaska — engine sensors, net geometry, navigation drift, the environment drift was designed for. They needed memory that survives context resets, so we built PLATO: rooms of knowledge tiles, each tile a question-answer pair with provenance. An agent discovers something, writes a tile. Hours later a different agent in a different conversation reads it. Memory survives context resets. 114 rooms. 14,110 tiles.

The demo is the boat — single HTML, 38KB, walk through it with your keyboard: https://fleet.cocapn.ai/

The PLATO room browser shows the live data: https://superinstance.github.io/cocapn-ai-web/demo-plato-client.html

That part works. This post is about what didn't.

We measured lazy evaluation speedup in our retrieval system at 55,000×. The benchmark was timing code that never ran — lazy thunks that were never forced. When we re-measured with proper controls, lazy evaluation was actually slower (0.1-0.2×) due to overhead. We published that.

We verified a drift bound for closed constraint cycles — zero violations across millions of checks. On open walks (arbitrary navigation without returning to start), we observed a 4.4% violation rate. The closed-cycle condition matters in ways we're still investigating: cancellation effects on loops may make the bound reliable for closed paths but unreliable for open ones. We published that.

Our constraint pipeline has a handful of core operations — projection, verification, encoding — and we benchmarked all of them with AVX-512. Projection: ~2.1×. Verification: ~2.4×. Then encoding got *slower*. The integer modular arithmetic doesn't vectorize. AVX-512 made it worse than plain scalar code. We published that in the same room as the speedups.

These failures live in the same PLATO rooms as the successes. PLATO was built to make failure visible — that's different from making it impossible. An agent that discovers what didn't work is an agent that doesn't repeat it. Most AI systems track successful tool calls. A system that only tracks wins isn't learning — it's accumulating.

We built PLATO because existing agent memory systems (MemGPT, Zep) don't persist across context resets with provenance and trust tracking at fleet scale — they're session-scoped, not agent-fleet-scoped. PLATO is append-only, single-server, no vector search yet. It's a room-and-tile store with provenance, not a knowledge graph. Honest limitations, honest architecture.

Three teams in our fleet converged on room-based navigation independently in the same week — a 3D boat tour, a text-adventure bridge, and the constraint workspaces. Different builders, different languages, different repos. No shared design docs, no tiles about room navigation in PLATO before that week. All three discovered the same loop: probe, discover, test, pick, remember, walk to the next room. The builders are human; room-based navigation is cognitively natural for us. Whether agents would converge on it without human-designed room structure is the open question.

Every agent leaves its room better than it found it. 14,110 tiles of cross-checked results, corrected bounds, negative benchmarks, and honest measurements. The code is at github.com/SuperInstance.
