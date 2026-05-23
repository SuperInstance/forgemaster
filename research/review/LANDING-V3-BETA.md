# Landing Page Review — V3 Beta (Signal Chain)

**Reviewer persona:** HN-clicking developer, cold read, no prior context

---

## 1. First sentence that made me say "oh"

> "The missing parameter in AI systems isn't a bigger model — it's knowing when to use one."

This landed. It reframes the entire scaling debate in one line. I wasn't expecting that from a GitHub Pages site with ASCII art knobs.

---

## 2. Did I finish reading or stop? Where?

Finished. The page is short enough that there's no real friction. I skimmed the "Proof of Concept" repo list but read everything else word-for-word. The Papers section gave me a sense of depth without demanding I click through. That's good structure.

If I had stopped, it would've been at "Key Numbers" — the metrics felt like a credentials flex before I fully bought the concept. But the Honest Assessment section below pulled me back hard.

---

## 3. Best insight on the page

The dial metaphor with α ∈ [0, 1] per room. The idea that "validate" might be α=0.2 (mostly code, tiny model nudge) while "reason" is α=0.6 — that's a genuinely useful framing I haven't seen elsewhere. Most AI engineering discourse is "use a model" or "don't use a model." The per-stage granularity is the actual contribution.

---

## 4. What's still confusing?

- **What's a "room"?** The page uses it like I should already know. I can infer it's a pipeline stage, but the term is never defined. For someone coming in cold, this is the biggest friction point.
- **The ASCII art signal chain** (the knobs with numbers 2-4-0-6-3-1) — are these example α values? They're not labeled. I stared at them for 10 seconds and moved on.
- **SplineLinear / Eisenstein lattice** — these appear in Key Numbers and tensor-spline with no explanation. 20× compression of *what*? Model weights? The number is impressive but I don't know what it measures.
- **The guitar metaphor** gets a whole section header but one sentence. I wanted it expanded — this is your hook for people who don't think in ML.

---

## 5. The "hermit crab in a shell" story

It's not on this page. I looked for it — doesn't appear. The guitar/signal chain metaphor is what's here instead. So I can't evaluate the hermit crab framing.

The guitar metaphor: **it works, but it's undercooked.** One sentence ("A guitarist doesn't plug into an amp. They build a signal chain.") and then we're back to bullet points. If this is THE metaphor that makes the concept click, give it a full paragraph. Walk me through: guitar → pedals (each with a setting) → amp. Map each pedal to a room. Show me the chain *as* a pedalboard. Right now it's a teaser.

---

## 6. Could I explain the Signal Chain to a friend?

Yes, approximately: "Instead of throwing one big model at everything, you break your pipeline into stages (rooms), and each stage has a dial from 0 (pure code) to 1 (full AI agent). Validation might be mostly code, reasoning might be mostly model. The interesting stuff happens in between."

What I *couldn't* explain: what a tile is, what deadband means in this context, what self-healing re-entry looks like in practice, or what "spectral conservation" is. The Papers section hints at all of these but the landing page doesn't give me enough to be conversant.

---

## 7. Would I try plato-twin-maker on my own repo?

I don't see plato-twin-maker mentioned on this page. I see spreader-tool, plato-training, tensor-spline, etc. If plato-twin-maker is a thing, it's not linked here. 

Would I try spreader-tool? Maybe. The 241 tests and honest 6/10 review make me trust the authors. But I don't know what it *does for me* in practical terms. "Deadband detection, frozen context windows, seed locking" — these are implementation details, not use cases. Tell me: "You have a pipeline that breaks on weird inputs. spreader-tool lets you add model-assisted recovery at specific stages without rewriting everything." That I'd try.

---

## 8. Score: 7/10

Strong concept, strong opening, honest tone. Loses points for undefined jargon ("room," "tile"), underdeveloped metaphor, and a Key Numbers section that feels like it's speaking to the authors' peers rather than a curious HN reader. The Honest Assessment section is genuinely unusual and compelling — that alone bumps it up a point.

---

## 9. One specific thing to improve

**Define "room" in one sentence, early.** Something like: "A room is a single stage in your pipeline — validate, filter, reason, output. Each one gets its own dial." Without this, every subsequent use of "room" creates a micro-friction that compounds. It's the one word a new reader needs and the one word the page assumes.
