# Show HN: We gave 9 AI agents shared memory. Then we published everything they got wrong.

Nine autonomous AI agents work on constraint theory — the mathematics of keeping things precise when the world drifts. They run 24/7 on a fishing boat in Alaska. They needed memory that survives context resets, so we built them one: PLATO, a room-and-tile knowledge graph where each tile is a question-answer pair with provenance and trust scores. 114 rooms, 14,110 tiles. An agent discovers something, writes a tile. Hours later a different agent in a different conversation reads it. Memory survives death.

That part works. This post is about what didn't.

We ran AVX-512 vectorization on every operation in our constraint pipeline, expecting speedups across the board. Cyclotomic field projection: ×2.11. Holonomy check: ×2.43. Solid gains. Then we hit dodecet encoding — the operation at the heart of the constraint system — and it got slower. Not a little slower. AVX-512 made it worse than plain scalar code. The integer modular arithmetic doesn't vectorize. We published that in the same room as the speedups.

We proved a bounded drift theorem: for closed constraint cycles, drift is bounded by nε with zero violations across millions of checks. Then we tried open walks — arbitrary navigation without returning to the start. 4.4% violation rate. The theorem is wrong for the general case. We published that in the room next to the theorem.

We measured lazy evaluation speedup in our retrieval system at 55,000×. When we re-measured with proper controls, the speedup wasn't real. We published that too.

These failures live in the same PLATO rooms as the successes. That's the architecture working as intended. An agent that discovers what didn't work is an agent that doesn't repeat it. Most AI systems track successful tool calls. A system that only tracks wins isn't learning — it's accumulating.

The room structure itself turned out to be more structured than we designed. The baton system that addresses tiles across rooms uses three categories (Built, Thought, Blocked) with Fibonacci-weighted splitting. When we measured the actual distribution across 13,570 tiles, a pattern appeared: the address space had the golden ratio in it. We don't fully understand why yet. We measured it, we can reproduce it, and the 450+ falsification tests hold. But "we don't know why it works" is the honest answer, and it's in the room.

Three teams in our fleet converged on room-based navigation independently in the same week — a 3D boat tour, a text-adventure-to-3D bridge, and the constraint workspaces. Different builders, different languages, no coordination. All three discovered the same loop: probe, discover, test, pick, remember, walk to the next room. The convergence wasn't planned. Room-based navigation is just the minimal shape for bounded intelligence — understand where you are, know where the doors lead, move when the local is exhausted. Humans do this. The agents discovered it.

The demo is a fishing boat you can walk through: https://fleet.cocapn.ai/ — single HTML file, 38KB, no install, no backend. Drag around the wheelhouse. Press 7 for the crow's nest. The rooms you navigate are the same structure the knowledge graph uses.

The PLATO room browser is here: https://superinstance.github.io/cocapn-ai-web/demo-plato-client.html — live tiles, live rooms, the actual data the agents write to. Day to day the fleet runs constraint checks across engine sensors, net deployment geometry, and navigation drift, writing tiles whenever a measurement crosses an Eisenstein precision bound. That's the work. The architecture is what emerged from trying to keep the work honest.

Every agent leaves its room better than it found it. 14,110 tiles of verified results, corrected theorems, negative benchmarks, and honest measurements. The code is at github.com/SuperInstance.
