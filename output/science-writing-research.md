# Science Communication Masters: Techniques Extracted & Applied

## PART 1: Research the Masters

---

### 1. Richard Feynman

**Specific techniques:**

1. **"The dinner table test" — explain it as if talking to someone smart but non-technical at dinner.** Feynman rejected jargon not because audiences are dumb, but because jargon is what you use when you *can't* actually explain the thing. If you need the word "Hamiltonian," you haven't found the right analogy yet. His Lectures on Physics open with atoms-as-little-balls, not with formal definitions.

2. **"Show the phenomenon before the equation."** In his optics lectures, he'd show a rainbow first, describe what you actually see, and only *then* derive Snell's law. The equation answers a question the reader already has — it doesn't create the question.

3. **"The confession technique."** Feynman regularly said "I don't understand this" about things he'd already won a Nobel for. This isn't humility — it's a structural move. By admitting confusion, he gives the reader permission to be confused, which means they stay engaged instead of feeling stupid and leaving. His "Surely You're Joking" stories always start with him getting something wrong.

---

### 2. Dan McKinley (Stripe)

**Specific techniques:**

1. **"The failed alternatives catalog."** In "Choose Boring Technology," he doesn't just advocate for boring — he lists the specific alternatives people tried, how they failed, and what it cost. This works because developers trust failure data more than success claims. The structure is: "We tried X. It broke like Y. The cost was Z. Here's what we do instead."

2. **"The adversarial opening."** He writes as if the reader is already skeptical. Instead of "Here's why our approach is great," he opens with "You're probably thinking this is stupid, and here's why you're right to think that — but..." This preemptively defuses the HN commenter who was going to object.

3. **"Concrete inventory over abstract principle."** Instead of saying "use mature tools," he literally lists the tools. Instead of saying "complexity has costs," he describes the specific person-hours spent debugging the message queue. The technique: never state a principle without immediately attaching a specific instance.

---

### 3. Julia Evans

**Specific techniques:**

1. **"The zine format: one concept per page, maximum 12 panels."** The constraint forces her to find the *single essential insight* and discard everything else. The key move: she doesn't explain topics — she explains *one surprising fact* about a topic. "How DNS Works" isn't about DNS. It's about the moment you realize DNS is just a distributed database with caching. She finds the "wait, *that's* how it works?" moment and builds the whole zine around it.

2. **"Draw the system as boxes and arrows, even if it's not accurate."** Her diagrams are deliberately simplified — not because she doesn't know better, but because the simplified diagram creates the right mental model. She'll add a footnote: "Actually it's more complicated than this, but this is the 80% that matters." The technique: accuracy at the wrong level of abstraction is worse than imprecision at the right level.

3. **"The 'strace it' move."** Instead of explaining what a program does, she shows you the actual system calls. Instead of describing a concept, she shows the command that reveals it. The reader can reproduce the insight themselves. This converts passive reading into active discovery.

---

### 4. Kathy Sierra

**Specific techniques:**

1. **"Make the reader awesome, not the product."** Her technique isn't about the thing — it's about who the reader becomes by understanding the thing. She frames every concept as: "After this chapter, you will be able to do X." The reader isn't learning Java — they're becoming someone who can build web apps. The product isn't the hero; the user's future self is.

2. **"The right amount of challenge — not too easy, not a wall."** She designs learning as a series of micro-challenges that are *just barely* achievable. The technique: give the reader enough to get 70% of the way, make them sweat for the last 30%, then reveal the answer. This is the "flow state" applied to technical writing.

3. **"Emotional engagement before cognitive content."** She hooks with "Why should you care?" before "What is it?" Her Head First books literally use images, puzzles, and conversational tone to engage the emotional brain before delivering the technical payload.

---

### 5. Bret Victor

**Specific techniques:**

1. **"The reactive document."** Instead of explaining a concept, build a tool where the reader can *manipulate* the concept and see consequences in real-time. His "Ten Brighter Ideas" piece doesn't explain energy policy — it's a spreadsheet you play with. The technique: if you can make it interactive, you don't need to explain it at all.

2. **"Show the future of the thing, not the thing itself."** In "Inventing on Principle," he doesn't show a better drawing app — he shows what drawing *should feel like* if the computer actually helped you. The technique: instead of iterating on existing solutions, demonstrate the gap between what we have and what's possible. This creates desire before the reader even knows the technical details.

3. **"The instant feedback loop."** Every demo he builds has zero latency between action and visible consequence. Code changes appear as visual changes immediately. The technique isn't just about his tools — it's a writing principle: every paragraph should give the reader an immediate "ah, I see" payoff, not make them wait until the end.

---

### 6. Peter Norvig

**Specific techniques:**

1. **"The anti-shorthand."** "Teach Yourself Programming in Ten Years" works because it directly contradicts every "Learn X in 24 Hours" book on the shelf. The technique: find the thing everyone gets wrong, name it explicitly, and make your whole piece the correction. The title IS the argument.

2. **"The research-backed takedown."** He doesn't just opine — he cites the study. "The 10,000 hour rule" isn't his claim, but he wields it as evidence. The technique: when making a provocative claim, anchor it to something the reader can verify. This converts the piece from "opinion" to "something I need to reckon with."

3. **"The curated path, not the lecture."** Instead of teaching you programming in the essay, he gives you a reading list and tells you to go do it for a decade. The technique: sometimes the best explanation is "here's where to point your attention" rather than "here's the content." It respects the reader's agency.

---

### 7. Ryan Dahl (Node.js original presentation)

**Specific techniques:**

1. **"The problem demo — show the thing breaking."** He didn't start with "Here's Node.js." He showed a simple HTTP server in Apache, showed it falling over under load, showed the code that caused it (one thread per request?!), and only *then* introduced the event loop. The technique: make the reader feel the pain before offering the analgesic. The reader should be thinking "there has to be a better way" before you reveal that there is.

2. **"The minimal viable contrast."** He didn't compare Node to 15 alternatives. He compared exactly two things: the old way (blocking) vs. the new way (non-blocking). One axis. Clear binary. The technique: reduce the comparison to a single dimension where your solution obviously wins.

3. **"Live code, not slides."** He typed the server live. The audience saw it work. The technique: a working 5-line demo beats a 50-slide deck. If you can demo it, demo it.

---

### 8. Steve Yegge

**Specific techniques:**

1. **"The internal monologue as narrative."** His posts read like someone thinking out loud, not someone delivering a conclusion. He'll write "So then I thought, well, what about X? And that's when I realized..." The technique: reproduce the discovery process in real-time. The reader feels like they're discovering it with you, not being told.

2. **"The absurdly specific war story."** He doesn't say "dynamic typing has tradeoffs." He tells the story of the specific bug at Amazon that took three days to find because of a type mismatch. The technique: one vivid, specific story beats a thousand balanced comparisons.

3. **"The unapologetic length."** He writes 5,000 words when 500 would "suffice." The technique: depth IS the signal. Engineers quote his posts because he actually worked through the implications instead of hand-waving. The length says "I did the homework." (Caveat: this only works if every paragraph actually adds something.)

---

### 9. David MacKay

**Specific techniques:**

1. **"The back-of-envelope as argument."** In *Sustainable Energy — Without the Hot Air*, he doesn't argue about policy. He does the math. "If every roof had solar panels, that would give us X. We need Y. Y/X = we're screwed." The technique: let the numbers make the argument. No adjectives needed.

2. **"The normalized unit."** Instead of saying "the UK consumes 2.5 terawatt-hours," he says "that's 125 kWh per person per day." The technique: always express quantities in units the reader can *feel*. One terawatt-hour is abstract. "Your share" is visceral.

3. **"The honest accounting."** He includes ALL the costs, even the ones that help the other side. The technique: if you show your work and include unfavorable data, the reader trusts your favorable data too. Integrity is a rhetorical device.

---

### 10. 3Blue1Brown (Grant Sanderson)

**Specific techniques:**

1. **"Animate the transformation, not the result."** His videos don't show you the formula — they show you the shape *morphing* from the input to the output. The technique: the reader doesn't need to understand the math if they can *see* the operation. The visual IS the proof for 90% of viewers.

2. **"Build the intuition first, name it second."** He'll spend 5 minutes showing you what e^iπ *looks like it does* before he ever writes Euler's formula. The technique: by the time you see the equation, you already know what it says — you just didn't have the notation for it yet.

3. **"The single visual metaphor per concept."** Euler's formula = a point rotating. Dot products = projecting onto a line. Determinants = area scaling. The technique: find ONE visual that captures the core of the concept, and resist the urge to add a second one. One perfect visual > three pretty good ones.

---

## PART 2: Three Explanations of Snapping

### For Game Developers (Feynman + Evans techniques: everyday frustration → specific fix)

Your unit vectors drift. After a few thousand rotations, `(1, 0)` becomes `(0.9999998, 0.0000003)`. Run a simulation long enough and nothing points where it should. You've been normalizing to paper over it, but that's aspirin, not a cure. Snapping replaces each float with the nearest *exact rational* from a prebuilt lookup — Pythagorean triples for 2D directions, Eisenstein integers for angles, 48 discrete compass points for game logic. The result: your unit vectors are *mathematically exact* after every operation, forever. No epsilon, no drift, no "close enough."

### For Embedded Engineers (MacKay + McKinley techniques: constraint → guarantee)

You're computing trig on a chip without an FPU. Every float operation costs 50 cycles and accumulates error. After 10,000 angle additions, you're off by degrees — not because your algorithm is wrong, but because IEEE 754 is the wrong representation for this job. Snapping pre-computes a finite lattice of exact rational values (3-4KB for full coverage) and replaces every arithmetic operation with a table lookup plus integer add. Result: guaranteed zero drift, no floating point, fits in SRAM. The math is provably correct because every value on the lattice is exact — no rounding step exists to introduce error.

### For Math-Curious Developers (Sanderson + Feynman techniques: the "aha" insight)

Here's the thing nobody tells you about floating point: the error isn't random. It's *structured*. The set of numbers your CPU can represent is a grid, and every operation rounds to the nearest grid point. Snapping asks: what if the grid was *your* grid? Pythagorean triples form a natural lattice in 2D where every point is exact. Eisenstein integers (a + bω, ω = e^{2πi/3}) tile the angle space with hexagonal symmetry — 6× denser than the square grid. The "aha": you're not losing precision by discretizing. You're *choosing* a precision that's closed under the operations you actually perform. The floats were always on a lattice. You just picked a bad one.

---

## PART 3: Three Alternative HN Openings

### Opening A — Feynman Style (everyday frustration)
*"At some point, every simulation programmer discovers that a 90° rotation isn't actually 90°. It's 89.999997°. After ten thousand rotations, things that should point up are pointing sideways. We spent two years finding the mathematical structure that makes this impossible, and it fits in 3KB of SRAM."*

**Techniques applied:**
- **Feynman's "confession"** — opens with the universal experience of the bug
- **Feynman's "phenomenon before equation"** — you feel the problem before we name the solution
- **McKinley's "adversarial opening"** — "impossible" is a bold claim; the skeptic reads on to disprove it
- **MacKay's "concrete unit"** — "3KB of SRAM" makes the cost visceral

### Opening B — Julia Evans Style (specific moment of failure)
*"Last week I watched a robot drift 40° off course over 8 hours — not because of sensor error, but because it added 0.1 radians 288,000 times and IEEE 754 rounded wrong each time. The fix wasn't better sensors or tighter tolerances. It was replacing every float with the nearest exact rational from a pre-computed lattice. Zero drift. The lookup table is 4KB."*

**Techniques applied:**
- **Evans' "one surprising fact"** — the robot wasn't broken; the number system was
- **Evans' "strace it" move** — here's the exact operation (0.1 × 288,000) and the exact failure mode
- **MacKay's "honest accounting"** — we give you the exact numbers so you can verify
- **Yegge's "absurdly specific war story"** — one vivid failure beats a thousand abstractions

### Opening C — Bret Victor Style (visual/demo)
*"Take a unit vector. Rotate it 360°. It should come back to (1, 0). In IEEE 754, it comes back to (0.9999999999999998, 0.0000000000000002). Now snap every intermediate value to the nearest Pythagorean triple. Rotate 360°. You get exactly (1, 0). Rotate 3,600,000°. Still exactly (1, 0). We proved this in Coq and shipped it on a $2 ARM chip."*

**Techniques applied:**
- **Victor's "instant feedback"** — the demo is in the first sentence; the reader can verify it mentally
- **Sanderson's "single visual metaphor"** — one operation (rotate 360°) captures the entire concept
- **Dahl's "minimal viable contrast"** — exactly two outcomes: the broken way and our way
- **Victor's "show the gap"** — the reader sees the distance between what floats promise and what they deliver

---

## Cross-Reference: Technique → Application Map

| Technique | Source | Where Applied |
|-----------|--------|---------------|
| Phenomenon before equation | Feynman | All three openings; game dev explanation |
| Confession / universal bug | Feynman | Opening A; embedded explanation |
| One surprising fact | Evans | Opening B; math-curious explanation |
| Concrete unit / visceral number | MacKay | All three openings (3KB, 4KB, $2 ARM) |
| Minimal viable contrast | Dahl | Opening C; all three explanations |
| Adversarial opening | McKinley | Opening A ("impossible") |
| Absurdly specific war story | Yegge | Opening B (288,000 additions) |
| Single visual metaphor | Sanderson | Opening C (rotate 360°); math-curious |
| Honest accounting | MacKay | All openings include cost/size |
| Build intuition, name second | Sanderson | Math-curious explanation |

---

*Research complete. All techniques are specific, actionable, and cross-referenced to applications.*
