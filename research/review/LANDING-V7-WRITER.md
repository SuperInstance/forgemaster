# Signal Chain Landing Page — Writer's Review

## 1. Does this page have a thesis? What is it?

Yes. Buried under a concrete example.

**Thesis:** You don't need one big model for every input. Give each processing stage a dial (α) that controls how much model capacity it uses, and let most inputs resolve at the cheap end.

The problem: the reader doesn't encounter this thesis as a thesis until the third section heading ("The dial: α ∈ [0, 1] per stage") — roughly 400 words in. Before that, they're reading a worked example of spam filtering, which is compelling as demonstration but doesn't tell them *why they should care* until they've already committed to reading.

## 2. Where does the narrative arc peak?

The peak is the benchmark table. "38 of 50 emails resolved by pure code at room 1. Only 3 needed the model. Same accuracy, 94% fewer API calls, 16.7× faster."

This is the moment where the reader thinks: *oh, this actually works, and the numbers are absurd.* It's the right peak. The problem is getting there — the arc climbs steadily but lacks a setup that creates tension. There's no "here's the problem everyone has" moment before the solution walks onstage.

## 3. Which paragraph would make a reader STOP SCROLLING?

> "Total: $0.0051, 8.4ms, spam confidence 0.95. The 70B model never ran. Three rooms handled it with regex, a keyword counter, and a 3B model that read two tiles and answered one question."

That's the one. It's specific, it's surprising, and it names the thing everyone assumes you need (the 70B model) and says it didn't show up. The specificity of "$0.0051" and "8.4ms" does more work than any abstract claim could.

## 4. Does each section build on the previous one?

Mostly yes, and this is one of the page's real strengths. The structure is:

1. Example (concrete) → 2. The dial (mechanism) → 3. Tiles (data structure) → 4. Early exit (result) → 5. Deadband (dynamics) → 6. Seeds (learning) → 7. Where it applies → 8. Compression → 9. Open problems

The first four sections form a tight chain. Sections 5-6 (deadband, seeds) feel like they belong in a different document — they're interesting but break the "one idea, escalating" momentum. The reader who was tracking "give each stage a dial" suddenly has to learn about KPI monitoring, hysteresis, duration gates, and a five-state lifecycle diagram. That's a digression that costs attention.

## 5. Is there a single "ah-ha" moment?

Yes, and it's stated *once*, mid-page, in a paragraph that should be the opening:

> "Most rooms exit on the code path most of the time. The model handles the delta — the part the shell doesn't already know."

This is the insight. Everything else is machinery. But the reader encounters it as an aside in a code walkthrough rather than as the fulcrum of the argument.

## 6. Compare this to a great technical essay. What's the gap?

Read Paul Graham's "Make Something People Want" or Dan Luu's "Things You're Allowed to Do." Those essays start with the insight in the first paragraph — sometimes the first sentence — and then spend the rest of the essay making you believe it through evidence, examples, and careful escalation.

This page does the opposite: it starts with evidence (a spam filter trace), builds up to the insight, and then keeps going past it into implementation details that a landing page reader doesn't need yet.

The gap is **prioritization of attention.** A great essay says "here's the one thing" and then makes you care. This page says "here's a lot of things" and hopes the one thing lands.

## 7. What would Paul Graham do with this material?

He'd write 800 words, not 2,500. He'd open with:

> "Most inputs don't need a model. The surprising thing is how far you can push this. At SuperInstance, we built a pipeline where 94% of inputs are resolved by regex, and the model only runs when the code isn't sure. Same accuracy. Sixteen times faster."

Then he'd give the spam example. Then he'd explain the dial. Then he'd stop. The deadband, seeds, compression, and open problems would be links, not sections. He'd trust that the reader who's hooked will click.

Graham's signature move: he states the insight, then spends the essay defending it against objections the reader is already forming. This page states the machinery and hopes the reader extracts the insight.

## 8. Core insight clarity: how many sentences until the reader gets "most inputs don't need a model, give each stage a dial"?

**Current:** The reader encounters fragments of this idea scattered across the first ~500 words. The closest to a thesis statement appears after the second example: "Every stage has a dial for how much model capacity to use." That's roughly paragraph 8, sentence 20+. Then the dial section sharpens it. Then "Most rooms exit on the code path most of the time" lands it.

**How many it should take:** Two. Maybe three. First sentence states the problem ("We're using 70B models for inputs that regex could handle"). Second sentence states the solution ("Give each stage a dial"). Done.

## 9. Writing quality: 1-10

**6.5**

Strengths: The concrete examples are genuinely excellent. The spam filter walkthrough is the best kind of technical writing — you can *see* it working. The benchmark numbers are specific and honest. The code snippets are real, not pseudocode. The page practices what it preaches (efficiency of communication).

Weaknesses: No thesis statement up front. The opening is a worked example with no frame — the reader doesn't know what they're reading or why until they've invested significant attention. Sections 5-6 (deadband, seeds) dilute the core argument. The "Where this pattern applies" table is good content in the wrong place — it should be earlier, as proof of generality, not later as an afterthought. The compression section reads like a different paper bolted on.

The biggest issue: the page is structured like documentation, not an essay. Documentation says "here's what I built." Essays say "here's what I discovered, and here's why it matters." This material has a genuine discovery in it. The structure hides that.

## 10. How the opening should read

---

Every input hits the same 70B model. That's the default architecture: one big model, every request, every time. It works. It's also like using a scalpel to open every piece of mail — technically correct, massively overqualified for 90% of the job.

We built a pipeline where each processing stage has a dial. α = 0 means pure code — regex, lookups, arithmetic. α = 1 means full model invocation. Most stages sit at α = 0 and resolve inputs for free. The model only runs when the code path isn't confident enough. We tested it on email classification: 94% of emails resolved without invoking the model at all. Same accuracy. Sixteen times faster. One-fiftieth the cost.

Here's how it works.

---

That opening does four things the current one doesn't:

1. **States the problem** (one sentence — everyone uses one big model for everything)
2. **States the insight** (give each stage a dial)
3. **Gives the proof** (94% fewer calls, 16.7× faster)
4. **Creates a pivot** ("Here's how it works") that the spam example naturally follows

The spam filter trace then becomes *evidence for a claim the reader already holds*, rather than *a trace the reader has to reverse-engineer a claim from*. That's the difference between compelling and merely informative.
