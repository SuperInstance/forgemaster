# Great Writing Analysis: Three Master Classes

*Analyzed 2026-05-17 for the Signal Chain page rewrite*

---

## 1. Paul Graham — "How to Do Great Work"

### Opening Sentence
> "If you collected lists of techniques for doing great work in a lot of different fields, what would the intersection look like?"

**Type:** Hypothetical question that reframes a familiar concept. Not "here's how to do great work" but "what would the common pattern even look like?" — this makes the reader lean in.

### Paragraphs Before First Insight
**2 paragraphs.** The first sets up the hypothetical. The second delivers the thesis. Then paragraph 3 hits the first real insight: "it does have a definite shape; it's not just a point labelled 'work hard.'" The reader already feels rewarded.

### Thesis (One Sentence)
The techniques for doing great work share a common shape across all fields: cultivate excessive curiosity, work on your own projects, find the frontiers, and notice what others overlook.

### How He Handles Technical Detail
Graham uses **zero code, zero tables, zero diagrams.** Every technical concept is rendered in plain prose. When he explains the "four steps" of great work, he writes: "choose a field, learn enough to get to the frontier, notice gaps, explore promising ones." That's a 300-page research methodology compressed into 16 words.

**His technique:** Replace technical detail with *metaphor*. "Knowledge expands fractally." "Work has a sort of activation energy." "The big prize is to discover a new fractal bud." Each metaphor does the work of a chapter of explanation.

**When he'd need code, he doesn't show it — he describes the feeling of using it:** "When I'm reluctant to start work in the morning, I often trick myself by saying 'I'll just read over what I've got so far.' Five minutes later I've found something that seems mistaken or incomplete, and I'm off."

### Structure Ratio
- **Narrative paragraphs:** ~80+
- **Code blocks:** 0
- **Tables:** 0
- **Footnotes:** ~12 (for nuance, not structure)

This essay is *pure* narrative. It works because every paragraph contains either an insight, a counterintuitive observation, or a vivid metaphor.

### What Makes It Compelling

1. **Calibrated vulnerability.** "I often trick myself by saying..." — he admits the same struggles everyone has. This is not a guru on a mountain. This is someone saying "here's what I've noticed, including about myself."

2. **Every paragraph earns its keep.** No filler. No "it's important to note that..." No throat-clearing. Each paragraph either advances the argument or adds a memorable image.

3. **He argues with himself.** "That sounds straightforward, but it's often quite difficult." He poses the objection before you can. This creates trust — you feel like he's already thought of your pushback.

4. **Conversational yet precise.** "The empirical evidence is on the scale of the evidence for mortality" — that's a joke that also happens to be the most precise way to say it.

5. **Section-to-section compounding.** Each section builds on the last without saying "building on what we discussed." He talks about finding a field → getting to the frontier → noticing gaps → exploring them → the nature of the work itself. It's a single ascending arc.

---

## 2. Simon Willison — "Building Python Tools with a One-Shot Prompt"

### Opening Sentence
> "I've written a lot about how I've been using Claude to build one-shot HTML+JavaScript applications via Claude Artifacts."

**Type:** Personal context-setting. "Here's what I've been doing, and here's the new thing." It works because it signals: this is a field report from someone actually doing the thing, not a theoretical overview.

### Paragraphs Before First Insight
**2 paragraphs** of setup, then the insight lands: he defines what "one-shot" means (and acknowledges the confusing dual meaning — this honesty builds trust immediately). By paragraph 3, he's showing the S3 debugging example.

### Thesis (One Sentence)
You can reliably build complete, dependency-managed Python tools from a single prompt by combining Claude Projects (with custom instructions) with `uv run`'s inline dependency declarations.

### How He Handles Technical Detail
**This is where Willison is a master.** He does something specific:

1. **He starts with the PROBLEM, not the tool.** "I had another round of battle with Amazon S3 today trying to figure out why a file in one of my buckets couldn't be accessed via a public URL." You feel his frustration. Now you care about the solution.

2. **He shows the prompt BEFORE the code.** You see his exact words: *"Write me a Python CLI tool using Click and boto3 which takes a URL of that form and then uses EVERY single boto3 trick in the book to try and debug why the file is returning a 404."* This teaches you HOW to prompt, not just what the tool does.

3. **Code appears only after you understand WHY.** The inline dependency comment block (`# /// script`) is shown AFTER you've already seen it work in the example command.

4. **He shows the RUN command, not just the code.** `uv run debug_s3_access.py https://...` — you can literally copy-paste. The writing IS the documentation.

5. **He links to full transcripts** rather than embedding everything. Trust the reader to go deeper if they want.

### Structure Ratio
- **Narrative paragraphs:** ~12
- **Code blocks:** ~6 (prompt examples, code snippets, run commands)
- **Tables:** 0

The code-to-prose ratio is about 1:2 — enough code to be concrete, enough prose to keep you oriented.

### What Makes It Compelling

1. **It's a war story with a tool.** He's not selling you on a framework. He's saying "here's a thing that annoyed me and here's how I solved it." The S3 story is relatable — everyone has fought S3 permissions.

2. **Progressive disclosure.** He shows you the trick (uv run), then the mechanism (inline dependencies), then the meta-pattern (Claude Projects with custom instructions), then the broader implication (custom instructions can teach LLMs new patterns). Each layer makes the previous one more valuable.

3. **He names the pattern.** "One-shot Python tools" — giving something a name makes it cognitively real. You can now think about it, talk about it, build on it.

4. **Zero hype.** No "revolutionary" or "game-changing." Just "this seems to work really well."

5. **He shows the custom instructions verbatim.** This is the most valuable part of the post, and he doesn't gatekeep it. You get the exact prompt that makes the pattern work.

### Section-to-Section Compounding
Problem (S3 access) → Tool (debug script) → Mechanism (inline deps) → Pattern (Claude Project) → Generalization (custom instructions for new patterns) → Broader implication (tools.simonwillison.net). Each section makes the previous one retroactively more useful.

---

## 3. Dan Luu — "In Defense of Simple Architectures"

### Opening Sentence
> "Wave is a $1.7B company with 70 engineers whose product is a CRUD app that adds and subtracts numbers."

**Type:** A mic-drop opening that inverts expectations. A $1.7B company... is a CRUD app? The reader immediately wants to know how that's possible. This is one of the best opening sentences in tech writing.

### Paragraphs Before First Insight
**1 paragraph.** The insight IS the opening: simplicity at scale works. By paragraph 2, he's already citing Stackoverflow scaling a monolith to top-100 traffic. The reader is already learning.

### Thesis (One Sentence)
Simple architectures (monoliths on boring databases) are unreasonably effective even at massive scale, and the tech industry's obsession with complex architectures is driven by conference culture and hype rather than engineering necessity.

### How He Handles Technical Detail
Dan Luu uses a **confessional, post-mortem style.** He doesn't explain what a monolith is — he describes what his monolith does, what went wrong, and what they'd change.

1. **He lists mistakes first.** "A mistake we made in the first few months..." — this is disarming. He earns credibility by being honest about failures before claiming successes.

2. **Technical choices appear as trade-off lists, not tutorials.** The GraphQL section has explicit Pros and Cons. He doesn't say "use GraphQL" — he says "here's why it worked for us, and here's where the libraries sucked."

3. **He quantifies the boring.** "Only handling billions of requests a month (for now)" — the parenthetical is doing enormous rhetorical work. He's saying "yes, we know this is small, but we're growing, and we chose boring anyway."

4. **No code at all.** This is an architecture post with zero architecture diagrams and zero code. The writing IS the architecture document. "Our architecture is so simple I'm not even going to bother with an architectural diagram."

### Structure Ratio
- **Narrative paragraphs:** ~15 (it's a shorter post)
- **Code blocks:** 0
- **Lists:** 2 (GraphQL pros/cons, things they'd change)

The ratio is overwhelmingly narrative. The lists break up the prose and serve as scannable reference points.

### What Makes It Compelling

1. **The $1.7B opening creates massive cognitive dissonance.** "A CRUD app that adds and subtracts numbers." You can't stop reading. He's challenging your entire mental model of what "serious engineering" looks like.

2. **He argues against the industry consensus without being contrarian.** He's not saying "microservices are bad." He's saying "here's a $1.7B company that didn't need them." The evidence does the arguing.

3. **Honest about trade-offs.** "Using synchronous Python is expensive... but the cost of our engineering team completely dominates the cost of the systems we operate." He's not pretending there are no costs — he's showing the costs are irrelevant.

4. **Specific about alternatives they rejected AND why.** "Users of [async frameworks] at scale often also report significant fallout." He's not cherry-picking — he acknowledges others have tried this path.

5. **The confessional structure.** Listing what they'd do differently (RabbitMQ → Redis, Celery → something simpler) builds enormous trust. You believe him about what works because he's honest about what doesn't.

### Section-to-Section Compounding
Opening (CRUD app = $1.7B) → Evidence (Stackoverflow) → Why simple works (engineers > compute) → What they do (boring Python) → What went wrong (transaction boundaries) → What they'd change → What they kept even though it sounds complex (GraphQL, K8s) → Where complexity is unavoidable (telecom integrations) → Conclusion (spend complexity budget where it matters).

---

## Cross-Patterns: What All Three Do

| Pattern | Graham | Willison | Luu |
|---------|--------|----------|-----|
| Open with a reframe, not a statement | ✅ Hypothetical question | ✅ Context + new direction | ✅✅ Cognitive dissonance |
| Thesis in first 3 paragraphs | ✅ | ✅ | ✅ |
| No filler paragraphs | ✅ | ✅ | ✅ |
| Show the problem before the solution | ✅ | ✅✅ | ✅ |
| Earn credibility through honesty about failures | ✅ (self-tricks) | ✅ (S3 frustration) | ✅✅ (explicit mistakes list) |
| Code only after WHY is established | N/A (no code) | ✅✅ | N/A (no code) |
| Name the pattern | ✅ ("staying upwind") | ✅ ("one-shot tools") | ✅ ("simple architectures") |
| Each section compounds on the last | ✅✅ | ✅✅ | ✅✅ |
| Conversational tone, no hype | ✅ | ✅ | ✅ |
| End with the reader wanting to act | ✅ | ✅ | ✅ |

---

## Template: How to Rewrite the Signal Chain Page

### Structural Blueprint

```
OPENING (1-2 paragraphs)
  └── An observation that reframes how the reader thinks about AI pipelines
      (NOT "AI pipelines are important" — something that makes them go "huh")

INSIGHT 1 (2-3 paragraphs)
  └── The first compounding insight — built directly on the opening observation
  └── Why this matters in plain language

INSIGHT 2 (2-3 paragraphs)
  └── Reframes the problem — the reader now sees it differently than before
  └── A specific, concrete example (not abstract)

INSIGHT 3 (2-3 paragraphs)  ← THIS IS WHERE TECHNICAL DETAIL FIRST APPEARS
  └── The "ah-ha" moment — now show the code/table that makes it real
  └── Technical detail earns its place because the reader already wants it

INSIGHT 4 (2-3 paragraphs)
  └── Compounds — shows how the previous insight leads somewhere unexpected
  └── More technical detail, now the reader is fluent

INSIGHT 5 (2-3 paragraphs)
  └── The payoff — the reader sees the full picture
  └── "I need to try this" feeling

CLOSING (1-2 paragraphs)
  └── Name the pattern
  └── End on action, not summary
```

### Opening Move: The Reframe

Don't open with "Signal Chain is a framework for..." Open with an observation that makes the reader's current mental model feel incomplete.

**Example openers in the style of these writers:**

- **Graham style:** "If you watch what actually happens inside a production AI pipeline — not what the diagram says, but what the code does — you'll notice something odd: most of the code isn't doing AI. It's doing plumbing. And most of the failures aren't AI failures. They're plumbing failures."

- **Willison style:** "I spent three hours last Tuesday debugging why an LLM call was returning stale results. The model was fine. The prompt was fine. The cache header on a middleware proxy had been set to 300 seconds by someone who didn't know the pipeline existed. That's when I realized: the hard part of AI pipelines isn't the AI."

- **Luu style:** "The most reliable AI pipeline I've ever seen has 40 lines of code. The least reliable has 40,000. The 40-line one processes 10M requests a month. The 40,000-line one has a dedicated on-call team."

### Rules for Technical Detail

1. **NO code before Insight 3.** The reader must understand WHY before seeing HOW.
2. **Every code block must answer a question the reader already has.** Not "here's the code" but "here's the code that solves the problem we just described."
3. **Tables appear AFTER the narrative.** Show the insight in prose, then give the table as a reference the reader can come back to.
4. **Maximum 1 code block per insight section.** More than that and you're writing documentation, not an essay.

### The Compounding Insight Pattern

Each insight should follow this shape:

```
What you probably think → Why that's incomplete → What's actually happening → Why that's interesting
```

Example:
- "You probably think the bottleneck in AI pipelines is model latency."
- "It's not. In production, the bottleneck is almost always data transformation between stages."
- "What's actually happening: each stage reshapes data in ways the next stage doesn't expect, and the glue code between them grows without anyone noticing."
- "Why that's interesting: this means the most impactful optimization isn't a faster model — it's a better contract between stages."

### Ending: The Action Impulse

Don't end with "In conclusion..." End with something that makes the reader open a terminal.

**Bad ending:** "Signal Chain provides a robust framework for building AI pipelines with type safety, caching, and observability built in."

**Good ending (Graham style):** "The best AI pipelines aren't the ones with the most sophisticated models. They're the ones where the plumbing disappears — where each stage just works because the contract between stages makes failure impossible. That's not a framework. That's a discipline. And you can start practicing it today."

**Good ending (Willison style):** "Here's the entire signal chain for a production pipeline. One file. Copy it, run it, break it. You'll learn more in ten minutes than you would from a hundred architecture diagrams."

**Good ending (Luu style):** "Our pipeline is simple enough that I can explain it in a sentence: data comes in, gets validated, gets transformed, gets scored, gets sent out. The simplicity isn't a limitation — it's the feature that lets us sleep at night."

### Tone Calibration

- **Direct, not academic.** "Use this" not "It is recommended to utilize this."
- **Honest about limitations.** Include at least one "here's where this approach doesn't work."
- **Name things.** Give the pattern a name. Named patterns are remembered.
- **No filler transitions.** Never write "Now let's look at..." Just look at it.
- **Personal voice.** "I spent..." / "We found..." / "The mistake was..." — not "It has been observed that..."

### Target Ratios

- Narrative paragraphs: ~60-70% of total content
- Code blocks: 3-5 total (each one earned by prior narrative)
- Tables: 1-2 (reference material, placed after the insight they support)
- Lists: Use sparingly — only when the reader needs a scannable reference (GraphQL pros/cons style)

---

## Summary: The One Rule

**All three writers follow the same rule: never show the reader something before they want it.**

Graham doesn't explain "activation energy" until you've felt the resistance of starting work. Willison doesn't show inline dependencies until you've felt the pain of installing dependencies. Luu doesn't justify the monolith until you've felt the weight of the $1.7B number.

**For the Signal Chain page:** Don't show the pipeline until the reader has felt the pain of pipelines without contracts. Don't show the code until the reader has understood the constraint it solves. Don't show the architecture until the reader has realized their current architecture is the problem.

The writing teaches by creating desire, then satisfying it. Every paragraph is either creating desire or satisfying it. Never neither.
