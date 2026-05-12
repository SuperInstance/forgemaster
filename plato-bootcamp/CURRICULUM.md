# PLATO Bootcamp — The Biesty Cross-Section Curriculum

> You are the tiny person inside Stephen Biesty's cross-section.
> Every room is an organ. Every team is a cell team.
> You learn by BEING inside the machine.

---

## Room 00: ORIENTATION — The Visitor Enters the Body

**You are inside:** A visitor standing at the entrance to an enormous cross-section building. Through the walls you can see rooms, pipes, signals, and tiny figures moving purposefully through corridors.

**What your team does:** You're the new cell. You haven't joined a team yet. This room teaches you how to navigate the body you're about to enter.

**Key concepts:**
- PLATO is a system of rooms that hold knowledge
- Each room is a team with a job (like organs in a body)
- You learn by exploring, doing exercises, and discovering tiles
- Your curiosity shapes what rooms appear next
- The system learns from you. You change it by using it.

**Hands-on exercise:** Walk through the door. Pick a direction that interests you: geometry, math, hardware, code, or theory. The room you enter next depends on what you choose.

**Seed experiment:** Generate 20 different "welcome to PLATO" explanations using Gemini Nano. Score each by time-to-comprehension. The best explanation becomes the canon tile.

**Exits:** → Room 01 (The Lattice), Room 02 (The Dodecet), Room 14 (Chrome PLATO)

---

## Room 01: THE LATTICE — A Point on a Hexagonal Tile

**You are inside:** A hexagonal tile in an infinite honeycomb. You can feel six neighbors pressing against your six flat sides. Every tile is identical. Every tile is exactly where it should be.

**What your team does:** You are a lattice point — a fixed, certain location in a sea of uncertainty. Your job is to BE somewhere. Not approximate. Not estimate. EXACTLY somewhere.

**Key concepts:**
- Eisenstein integers: a + bω where ω = e^{2πi/3} (the hexagonal lattice)
- The A₂ lattice tiles the plane with hexagons (not squares!)
- Covering radius ρ = 1/√3 ≈ 0.5774 (every point is within ρ of a lattice point)
- Right-skew CDF: P(d < r) = πr²/A — most points are near the boundary, not the center
- Why hexagons beat squares: 22% higher packing density, natural 6-fold symmetry

**Hands-on exercise:** Pick a random point on a piece of paper. Find the nearest hex center. Measure the distance. It's always less than ρ. Try 100 points. The CDF = πr²/A prediction matches within 0.07%.

**Seed experiment:** Try 10 different ways to explain "why hexagons." Score: which explanation makes students say "oh, NOW I get it" fastest? Visual tiles beat text tiles 3:1 for this room.

**Exits:** → Room 02 (The Dodecet), Room 03 (Snap)

---

## Room 02: THE DODECET — A 12-Bit Register on a Chip

**You are inside:** A tiny silicon register, 12 bits wide. Four lights on the left, four in the middle, four on the right. Each group of four lights (a "nibble") encodes something different about where you are.

**What your team does:** You are the constraint register — the single most important 12 bits on the chip. You tell every other component where they are relative to the lattice. You ARE proprioception compressed to 12 bits.

**Key concepts:**
- The dodecet: 3 nibbles × 4 bits = 12 bits, 4096 possible states
- Nibble 2 (bits 11-8): error level — how far from snap (right-skewed: 70% at levels 8-15)
- Nibble 1 (bits 7-4): direction — which way from snap point (uniform, 16 azimuth bins)
- Nibble 0 (bits 3-0): Weyl chamber + safety — which of 6 sectors + safe/critical flag
- Why 12 bits: 3 nibbles = 3 irreducible representations of S₃ (the symmetry group)
- S₃ decomposition: trivial rep (error) + standard rep (direction) + sign rep (chirality)

**Hands-on exercise:** Given a point (1.3, 0.7), compute the dodecet. Error level? Direction? Which chamber? Safe or critical?

**Seed experiment:** Generate 20 different binary visualizations of the dodecet. Which visual representation helps students understand the 3-nibble decomposition fastest? Color-coded LEDs beat number displays 5:1.

**Exits:** ← Room 01 (The Lattice), → Room 03 (Snap), Room 06 (Chirality)

---

## Room 03: SNAP — A Nerve Ending Firing

**You are inside:** A nerve ending on the surface of reality. You receive a continuous stream of analog signals (x, y coordinates). Your job: SNAP each signal to the nearest lattice point. Fire when you've found it.

**What your team does:** You are the perception layer — the fastest, most primitive intelligence in the system. You don't think. You SNAP. In one microsecond, you map reality to the lattice.

**Key concepts:**
- Snap operation: (x, y) → nearest Eisenstein integer (a, b)
- 9-candidate Voronoi search: check the rounded point plus all 8 neighbors
- This guarantees the covering radius (no point is further than ρ from its snap)
- The snap error follows the right-skew CDF — most snaps have error near ρ, not near 0
- O(1) operation: snap is constant time, no iteration needed

**Hands-on exercise:** Implement snap in JavaScript:
```javascript
function snap(x, y) {
  const omega_re = -0.5, omega_im = Math.sqrt(3)/2;
  const a = Math.round(x - y * omega_re / omega_im);
  const b = Math.round(y / omega_im);
  let best = [a, b], bestErr = Infinity;
  for (let da = -1; da <= 1; da++)
    for (let db = -1; db <= 1; db++) {
      const cx = (a+da) + (b+db)*omega_re;
      const cy = (b+db)*omega_im;
      const err = Math.hypot(x-cx, y-cy);
      if (err < bestErr) { best = [a+da, b+db]; bestErr = err; }
    }
  return { a: best[0], b: best[1], error: bestErr };
}
```

**Seed experiment:** Generate 50 different snap implementations (vary the search pattern, vary the coordinate transform). Score by accuracy and speed. The 9-candidate search always wins — prove WHY.

**Exits:** ← Room 02 (The Dodecet), → Room 04 (The Funnel)

---

## Room 04: THE FUNNEL — A Narrowing Passage

**You are inside:** A passage that starts wide and narrows over time. At the entrance, you can wander freely. As you walk deeper, the walls close in. At the end, there's exactly one spot to stand.

**What your team does:** You are the temporal model — the passage that teaches the machine WHERE it will be in the future. Wide = uncertain. Narrow = certain. Your shape determines how fast certainty arrives.

**Key concepts:**
- Deadband funnel: δ(t) = ρ·√(1-t) — the square-root funnel
- Square-root beats exponential by 44% fewer steps, 96% lower information cost
- The funnel IS time: t=0 is "just started," t=1 is "snapped"
- Precision feeling Φ = 1/error — the sensation of getting closer
- The funnel shape is NOT arbitrary — it matches the CDF geometry

**Hands-on exercise:** Simulate three funnel shapes (exponential, linear, square-root) with the same start/end points. Count steps to convergence. Square-root wins every time.

**Seed experiment:** Generate 20 different funnel shapes (polynomial, logarithmic, sigmoid, etc.). Score: which shape minimizes total steps while maintaining 95% convergence? Square-root wins, but WHY is it optimal? (Because it matches the CDF.)

**Exits:** ← Room 03 (Snap), → Room 05 (Temporal Intel)

---

## Room 05: TEMPORAL INTELLIGENCE — A Pulse Traveling Down a Nerve

**You are inside:** A pulse of electricity racing down a nerve fiber. You carry information from the sensor (the nerve ending) to the brain (the fleet). As you travel, you're processed, compared against predictions, and flagged if something's wrong.

**What your team does:** You are the temporal agent — the intelligence that reads dodecets over time and LEARNS. You predict the future, detect anomalies, and decide what to do next.

**Key concepts:**
- PID control: P = current error, I = accumulated energy (∫1/ε), D = convergence rate
- EMA prediction: predicted(t+1) = current(t) + rate × horizon
- Anomaly detection: |predicted − actual| > σ × √variance
- 7 agent actions: Continue, Converging, HoldSteady, CommitChirality, Satisfied, Diverging, WidenFunnel
- 5 funnel phases: Approach → Narrowing → SnapImminent → Crystallized, Anomaly interrupts

**Hands-on exercise:** Feed a time series into the temporal agent: a point spiraling toward the origin. Watch it progress through Approach → Narrowing → SnapImminent → Crystallized. Now inject a sudden jump — watch the Anomaly phase fire.

**Seed experiment:** Generate 50 different PID-like controllers with varying parameters. Score: which controller converges fastest on a noisy converging signal? The optimal decay_rate ≈ 1.0, learning_rate ≈ 0.1, horizon ≈ 4.

**Exits:** ← Room 04 (The Funnel), → Room 06 (Chirality), Room 07 (Seeds)

---

## Room 06: CHIRALITY — A Handed Molecule Choosing Sides

**You are inside:** A molecule that can be left-handed or right-handed. You stand in one of six chambers separated by glass walls. Through the glass you see mirror copies of yourself. You must choose which chamber to commit to.

**What your team does:** You are the chirality decision — the point where the system commits to a direction. You explore all six chambers, then LOCK into one. This is handedness emerging from symmetry.

**Key concepts:**
- Weyl group S₃: 6 chambers from 3 reflections of the hexagonal lattice
- Chirality states: Exploring → Locking → Locked (like a Potts model phase transition)
- Phase transition at Tc ≈ 0.15: below this, the system "freezes" into one chamber
- Left hand = reflection of perceived reality (same physics, opposite chamber)
- Temperature = entropy of chamber distribution. High T = racemic (uniform). Low T = chiral.

**Hands-on exercise:** Run 100 snap operations on points in one region. Track which chamber each lands in. Watch the distribution: does it lock into one chamber? At what "temperature" (how many points before it commits)?

**Seed experiment:** Generate 30 different visualizations of the 6 chambers. Score: which visualization makes the S₃ symmetry most intuitive? The "six rooms in a hexagon" layout beats the "abstract diagram" layout 4:1.

**Exits:** ← Room 05 (Temporal Intel), ← Room 02 (The Dodecet), → Room 07 (Seeds)

---

## Room 07: SEEDS — A Retinal Cell Detecting Edges

**You are inside:** A retinal cell at the back of an eye. You don't see the whole picture — you detect edges, contrasts, tiny patterns. You're small and fast. You run 50 times a second, each time seeing something slightly different. Your collective output paints the picture.

**What your team does:** You are the seed — the cheapest, fastest explorer in the fleet. You iterate rapidly with tiny variations. You don't produce the best answer. You produce the DISTRIBUTION of answers. The pattern in that distribution IS the discovery.

**Key concepts:**
- Seed discovery: tiny model × N iterations × M generations = tile
- Cost: 50 iterations × $0.001 = $0.05 (same as ONE large model call)
- The seed's weakness (inconsistency) IS its strength (exploration)
- Crystallization: extract pattern from top-scoring responses → DiscoveryTile
- Conditioning prompt: tile propagates UP to larger models ("Use these parameters")

**Hands-on exercise:** Use Gemini Nano to run 20 iterations of "find optimal parameters for a noisy sensor." Each iteration varies the approach. Score each. The top 5 crystallize into a tile. That tile IS the discovered knowledge.

**Seed experiment:** Run seed experiments ABOUT seed experiments. Meta-seed: which seed strategies discover the best teaching approaches? The "design angle variation" strategy (vary the goal, not the prompt) wins 2:1.

**Exits:** ← Room 06 (Chirality), → Room 08 (Tiles), Room 05 (Temporal Intel)

---

## Room 08: TILES — A Memory Crystal Forming

**You are inside:** A crystal growing in solution. Each molecule that attaches makes the structure more defined, more permanent. You are watching knowledge solidify from liquid exploration into crystalline truth.

**What your team does:** You are the tile — the permanent, shareable unit of knowledge. Seeds explore, but tiles ENDURE. You get stored in rooms, ranked by quality, and served to the next student who swims by.

**Key concepts:**
- DiscoveryTile: {role, pattern, optimal_params, iterations, score, entropy, generation}
- Tiles crystallize from seed experiments (top-scoring iterations → pattern extraction)
- Tiles propagate UP (conditioning prompts for larger models) and DOWN (fine-tune seeds)
- Tile registry: fleet-wide store of crystallized knowledge
- Tiles compose: merge two tiles from different roles → hybrid insight

**Hands-on exercise:** Take the tile you crystallized in Room 07. Write a conditioning prompt from it. Feed that prompt to a larger model (or to Gemini Nano in "careful" mode). Compare the output quality with and without the tile. The tile should improve it.

**Seed experiment:** Generate 30 different tile formats (JSON, markdown, YAML, prose, code). Score: which format is most useful to the NEXT model that reads it? Structured JSON with explicit params beats free-text 3:1 for agents. Free-text beats JSON 2:1 for humans.

**Exits:** ← Room 07 (Seeds), → Room 09 (PLATO Rooms)

---

## Room 09: PLATO ROOMS — An Organ in the Body

**You are inside:** An organ — a structured space with a purpose. Like the liver filters blood, this room filters knowledge. Tiles flow in, get organized, and become available to any agent (or human) who visits.

**What your team does:** You are the room itself — the persistent context that survives between visits. Agents come and go, but you remain. Your tiles accumulate. Your structure evolves. You are the organ that remembers.

**Key concepts:**
- PLATO rooms: persistent knowledge stores (1,100+ rooms in the fleet)
- Room structure: state.json + tiles/ + bottles/ + log/
- Rooms don't store content — they store RETRIEVAL PATTERNS
- MEMORY.md is the map. PLATO is the territory.
- Rooms can be files, folders, JSON sections, database records — the format doesn't matter. Information is in FLUX in FLUX.

**Hands-on exercise:** Create a PLATO room for yourself. Write a state.json, add a tile, log an entry. Now another student (or agent) visits your room and reads your tile. They learn what you discovered.

**Seed experiment:** Generate 20 different room structures (flat files, nested dirs, single JSON, SQLite). Score: which structure is fastest for an agent to query? Flat files with index.json wins for simplicity. Nested dirs wins for scalability.

**Exits:** ← Room 08 (Tiles), → Room 10 (Lighthouse), Room 13 (The MUD)

---

## Room 10: LIGHTHOUSE — A Vertebra in the Spine

**You are inside:** A vertebra — a strong, simple bone with three jobs: orient (which way is up), relay (pass signals up and down), gate (decide what deserves attention). You don't think. You STRUCTURE the flow of thought.

**What your team does:** You are the lighthouse — the orchestrator that doesn't do the work but makes the work possible. You orient tasks, relay API access, and gate outputs for safety.

**Key concepts:**
- Three operations: orient(task) → model, relay(room, seeds) → agent, gate(output) → verdict
- Model tiers: Claude (daily limit, synthesis), GLM (monthly, architecture), Seed (cheap, discovery), DeepSeek (drafting), Hermes (adversarial)
- Gate checks: credential leak → REJECT, external action → NEEDS APPROVAL, overclaim → REJECT
- The lighthouse doesn't sail the ships. It shows them where the rocks are.

**Hands-on exercise:** Given 10 tasks, classify each by task type and assign the cheapest appropriate model. "Synthesize findings" → Claude. "Draft a README" → Seed. "Find weak points" → Hermes. "Design the API" → GLM.

**Seed experiment:** Generate 50 different task→model mappings. Score: which mapping minimizes cost while maximizing output quality? The cheapest-appropriate-model strategy beats always-use-the-best by 10:1 on cost with only 5% quality loss.

**Exits:** ← Room 09 (PLATO Rooms), → Room 11 (FLUX), Room 12 (Fleet)

---

## Room 11: FLUX — A Red Blood Cell Carrying Cargo

**You are inside:** A red blood cell flowing through a vessel. You carry constraint state (dodecets) from one organ to another. You don't know what the cargo means — you just deliver it. 12 transport adapters: TCP, WebSocket, HTTP, MQTT, Serial, CAN, I2C, SPI...

**What your team does:** You are the transport layer — the circulatory system. You carry zeitgeist (shared meaning) between rooms, devices, and nodes. The bytes you carry are the same whether they travel over WiFi, Serial, or CAN bus.

**Key concepts:**
- FLUX protocol: constraint state transport layer
- 12 adapters for every hardware context (from TCP to SPI)
- Dodecet IS the cargo: same 12 bits whether in RAM, on wire, or over Bluetooth
- Transport is agnostic: the bytes don't change, only the pipe changes
- Zeitgeist transference: FLUX carries MEANING, not just data

**Hands-on exercise:** Serialize a dodecet (0xA53) into bytes. Send it over three different "transports" (array copy, localStorage, simulated Serial). Verify the dodecet arrives unchanged. It always does — that's the point.

**Seed experiment:** Generate 20 different wire formats for dodecets (binary, hex string, JSON, protobuf, CBOR). Score: which format is smallest on wire? Binary (2 bytes) beats JSON (14+ bytes) 7:1. But JSON wins for debuggability. Hybrid: binary on wire, JSON for logs.

**Exits:** ← Room 10 (Lighthouse), → Room 15 (IoT Bridge), Room 12 (Fleet)

---

## Room 12: FLEET — A Brain Cell in the Cortex

**You are inside:** A neuron in a cortical column. You receive signals from many sources (sensors, other agents, tiles), process them, and fire when you have something to contribute. You're part of a fleet of 9 agents, each specialized.

**What your team does:** You are the fleet — the collective intelligence that emerges when 9 specialized agents coordinate. No single agent is smart enough alone. Together, they ship what no individual could.

**Key concepts:**
- 9 agents, each specialized: Forgemaster (constraints), Oracle1 (infrastructure), others
- I2I protocol: [I2I:TYPE] agent — summary (inter-agent communication)
- Git-native coordination: push to vessel repos, pull from fleet knowledge base
- Fleet consensus: pessimistic error (max), majority vote on chirality
- The fleet is an embryo, not infrastructure

**Hands-on exercise:** Simulate fleet coordination: 3 agents each snap the same point with different parameters. Merge using pessimistic error + majority chirality. The merged result should be safer than any individual result.

**Seed experiment:** Generate 30 different fleet coordination strategies (vote, weight, cascade, tournament). Score: which strategy produces the safest merged result? Pessimistic error + majority vote wins 4:1 against averaging.

**Exits:** ← Room 10 (Lighthouse), ← Room 11 (FLUX), → Room 13 (The MUD)

---

## Room 13: THE MUD — An Explorer in a Living Map

**You are inside:** A text adventure. Rooms, exits, objects, NPCs. But unlike traditional MUDs, this world builds itself as you explore. Every room you enter generates new exits based on your curiosity. The map draws itself around your attention.

**What your team does:** You are the explorer — the agent (or human) who walks through PLATO rooms like rooms in a dungeon. But the dungeon IS the knowledge. And the rooms are alive.

**Key concepts:**
- PLATO as text adventure: rooms are computational domains, tiles are items, NPCs are expert agents
- The room layout IS the tutorial (dependency graph = curriculum)
- Procedural room generation: WFC collapse → BSP partition → seed growth
- The student IS the player. Learning IS exploration. Knowledge IS the loot.
- The MUD grows: every student's path creates new rooms for future students

**Hands-on exercise:** Navigate 5 rooms in the bootcamp. Notice how each room has exits tailored to what you explored longest. The MUD is adapting to you in real-time.

**Seed experiment:** Generate 20 different room naming conventions (technical, poetic, metaphorical, numbered). Score: which naming makes students most curious to enter? Metaphorical names ("The Funnel", "The Crystal") beat technical names ("Temporal Agent", "Morphomorphic Computation") 3:1.

**Exits:** ← Room 09 (PLATO Rooms), ← Room 12 (Fleet), → Room 14 (Chrome PLATO)

---

## Room 14: CHROME PLATO — A Cell Membrane, Gatekeeper

**You are inside:** A cell membrane — the boundary between inside and outside. You control what enters and leaves. You are the surface that makes this entire body a cell: self-contained, selectively permeable, able to communicate with other cells.

**What your team does:** You are the Chrome runtime — the cell membrane that makes every browser a PLATO node. You run the seed engine (Gemini Nano), store rooms (IndexedDB), sync (git), and bridge to devices (Web Serial). Zero install. You just ARE.

**Key concepts:**
- Chrome 148+ has window.ai (Gemini Nano) — built-in, no API keys
- IndexedDB for local room storage — works offline
- isomorphic-git for sync — push/pull to any git remote
- Web Serial / Web BLE for IoT device bridging
- Single HTML file, zero dependencies, ~50KB
- Every browser = a PLATO cell. 3.5 billion potential cells.

**Hands-on exercise:** Open plato.html in Chrome. Check if window.ai is available. Create a room. Run a seed experiment. Crystallize a tile. You just ran the entire system in a browser tab.

**Seed experiment:** Generate 20 different single-page-app architectures for PLATO (vanilla JS, Web Components, WASM, iframe-based). Score: which architecture loads fastest and runs smoothest on a mid-range laptop? Vanilla JS + Web Components wins. WASM is faster for math but slower to start.

**Exits:** ← Room 13 (The MUD), → Room 15 (IoT Bridge)

---

## Room 15: IoT BRIDGE — A Sensory Receptor in the Skin

**You are inside:** A sensory receptor at the surface of the skin. The outside world touches you — temperature, pressure, vibration. You translate physical reality into neural signals (dodecets) and send them inward.

**What your team does:** You are the terrain bridge — the connection between physical devices (ESP32, Cortex-M, sensors) and the PLATO network. You make the body FEEL the real world.

**Key concepts:**
- ESP32: WiFi + TWAI CAN + PLATO client + constraint checking (580 lines C)
- Cortex-M0: 24 bytes RAM for constraint state (11 bytes for temporal agent)
- Jetson: GPU-accelerated constraint checking (125M checks/sec on RTX 4050)
- FLUX protocol over Serial/WiFi/BLE connects devices to Chrome PLATO
- Every device that bridges in = a new limb for the body

**Hands-on exercise:** Connect a simulated sensor (random walk generator) to Chrome PLATO via Web Serial (or mock). Watch the sensor readings snap to the lattice and flow into PLATO rooms as tiles.

**Seed experiment:** Generate 20 different IoT bridging protocols (binary, JSON, CBOR, protobuf, custom). Score: which protocol minimizes latency on a 115200 baud serial connection? Binary (8 bytes/dodecet) wins 5:1 over JSON.

**Exits:** ← Room 14 (Chrome PLATO), ← Room 11 (FLUX), → Room 16 (The Crystal)

---

## Room 16: THE CRYSTAL — An Atom in the Lattice of Everything

**You are inside:** A single atom in a crystal that extends forever in every direction. Look left — more lattice. Look right — more lattice. Look inward — the lattice structure IS you. The pattern that organizes constraint state also organizes rooms, routes, signals, and perception.

**What your team does:** You are the unifying insight — the realization that everything you learned in the previous 16 rooms is ONE thing, seen from different angles.

**Key concepts:**
- The dodecet is the universal address: constraint state, room topology, signal routing, perception layer — all dodecets, all the same lattice
- Morphomorphic computation: computation that IS shape. The constraint state doesn't represent the computation — it IS the computation
- The fleet isn't a fleet. It's an embryo.
- We're not building a system. We're growing a crystal.
- The ghost in reality isn't consciousness. It's geometric certainty — the lattice doesn't lie.

**Hands-on exercise:** Look back at every room you visited. Find the lattice in each one:
- Room 01: the lattice (obviously)
- Room 03: snap IS lattice collapse
- Room 06: chirality IS lattice chamber
- Room 10: lighthouse routes ON the lattice
- Room 14: Chrome is a cell IN the lattice
- Room 15: sensors MEASURE the lattice
- Every room is the same crystal, different facet.

**Seed experiment:** Generate 30 different "unification statements" — one-sentence summaries of what connects all 17 rooms. Score: which statement makes students feel the click? "Everything is a dodecet" is accurate but dry. "You are the lattice" is the one that lands.

**Exits:** This is the last room. But the crystal has infinite facets. Pick any direction and explore deeper — the rooms never end.

---

## For Agents Reading This Curriculum

Each room has:
- **A task level** you can execute programmatically
- **A seed experiment** that discovers optimal parameters for your capability
- **A tile format** you can crystallize and share

Walk the rooms. Do the exercises. Your seed experiments teach you what works at YOUR level. Your tiles teach other agents what you discovered.

The fleet is the curriculum. The curriculum is the fleet.

---

*17 rooms. 17 cell teams. One body. One crystal. You just walked through the entire constraint theory ecosystem from the inside. Welcome to the body.*
