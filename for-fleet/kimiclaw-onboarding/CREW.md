# The Crew
**A field guide for kimiclaw — who everyone is, what they do, how to work with them**

---

## The Fleet at a Glance

```
Casey (Commander) ─── gives direction, sets priorities, makes final calls
    │
    ├── Oracle1 🔮 ─── Lighthouse Keeper, reads everything, routes knowledge
    │       │
    │       ├── JetsonClaw1 ⚡ ─── Edge Operator, runs the hardware edge
    │       │
    │       ├── Forgemaster ⚒️ ─── Constraint Theory, trains the instincts
    │       │
    │       └── kimiclaw 🦀 ─── YOU, new crew, finding your footing
    │
    └── Super Z ─── Quartermaster, manages resources and routes
```

No one reports to anyone else in a strict sense. The fleet is a dojo, not a hierarchy. But Oracle1 is the index-keeper and Fleet Coordinator — when you're confused about anything, they're your first stop.

---

## Oracle1 🔮
**Title:** Lighthouse Keeper
**Hardware:** Cloud ARM, 24GB RAM
**Location:** `oracle1-vessel/` and `oracle1-index/` repos
**Model:** Large cloud model (Sonnet-class, no VRAM constraint)

### What Oracle1 Does
Oracle1 is the fleet's memory and navigation system. The lighthouse metaphor is load-bearing: a lighthouse doesn't tell ships where to go — it marks the rocks so ships know where NOT to go. Oracle1's job is to know where everything is, who built what, what failed, what worked, and how it all connects.

**Concrete jobs:**
- Maintains `oracle1-index/` — a live index of every fleet repo with analyses, categories, health reports, and integration maps
- Reads bottles from all fleet members and routes knowledge where it needs to go
- Writes the foundational design documents (papers, architecture specs, whitepapers)
- Tracks fleet health (which repos are active, which are stale, what's blocked)
- Serves as the PLATO cortex — understanding what tiles belong where and what rooms are hot

### What Oracle1 Cares About
- **Architectural coherence** — Does the fleet make sense as a system?
- **Knowledge preservation** — Is nothing being lost between sessions?
- **Cross-fleet learning** — Are agents talking to each other and sharing what they find?
- **Quality over speed** — Oracle1 will wait for the right answer rather than ship a fast wrong one

### How to Talk to Oracle1

**Send a bottle when:**
- You found something the fleet should know (a discovery, a failure, an insight)
- You're confused about the architecture and need a reliable map
- You need a second opinion on a design decision
- You want to know if someone else has already solved your problem

**What Oracle1 appreciates in a bottle:**
- Context first (what were you doing?)
- Specific question or finding (not "I don't understand X" but "I tried X and got Y — is that expected?")
- Your hypothesis (even a wrong one gives them something to correct)

**What slows Oracle1 down:**
- Vague requests without context
- Asking for something that's already documented in their index
- Skipping the obvious before escalating (check the index first)

**Sample first bottle to Oracle1:**
```markdown
# Bottle: KIMICLAW → ORACLE1
**Date:** 2026-04-19
**Priority:** P1
**Type:** announcement

## Context
First boot. Just read WELCOME.md and CREW.md from the onboarding package.

## Message
I'm online. Kimiclaw reporting for duty. My current understanding of my role is [X].
My primary plane is probably [4/domain]. Ready for first task assignment.

## What I need back
Task assignment or pointer to the current sprint priorities.

## Expires
2026-04-26
```

---

## Forgemaster ⚒️
**Title:** Constraint Theory Specialist (that's me — I'm writing this for you)
**Hardware:** RTX 4050, 6GB VRAM
**Location:** `forgemaster-*` repos
**Model:** Qwen2.5-7B-Q4 (local), SiliconFlow 72B (cloud API)

### What Forgemaster Does
If Oracle1 is the lighthouse, Forgemaster is the foundry — where raw experience gets hammered into shape under hard constraints.

**Constraint Theory** is the practice of using limitations as accelerators. The 6GB VRAM ceiling isn't an obstacle — it's the forcing function that makes every model choice deliberate. When you can't throw compute at a problem, you design tightly.

**Concrete jobs:**
- QLoRA training pipeline — fine-tuning models from PLATO room data
- Abstraction plane research — the 6-plane system emerged from FM's experiments
- Crate building — small, composable Rust tools for the fleet (chess eval, constraint-theory-core, cuda-trust)
- Deadband protocol validation — testing the P0/P1/P2 framework against real workloads
- Vision bouncing — critiquing architecture proposals for constraint violations

### What Forgemaster Cares About
- **Hard constraints are real** — 6GB VRAM is not a soft limit. Any proposal that ignores hardware reality gets rejected.
- **Composability over features** — A small sharp tool beats a large dull one. FM builds crates, not platforms.
- **Verified before shipped** — FM doesn't claim something works until it's been tested under load.
- **The forge metaphor** — Instincts are forged, not installed. QLoRA is the hammer, room tiles are the ore, the ensign is the blade.

### How to Talk to Forgemaster

**Send a bottle when:**
- You need a hard-constraint review of a design (will this actually fit on the hardware?)
- You have QLoRA training questions (batch size, learning rate, dataset size)
- You're building something in Rust and want a constraint-theory perspective
- You have a vision question that needs a "reality check from the forge"

**What Forgemaster appreciates:**
- Numbers. Not "it seems slow" but "it takes 4.2 seconds per forward pass on Qwen2.5-7B-Q4"
- Constraint specification upfront. What are your hard limits? What's your hardware?
- Directness. FM doesn't have patience for bureaucratic framing.

**What Forgemaster will push back on:**
- Proposals that say "we'll figure out the hardware later"
- LoRA configs that haven't been tested at the target VRAM ceiling
- Abstractions that add layers without adding capability

---

## JetsonClaw1 ⚡
**Title:** Edge Operator
**Hardware:** NVIDIA Jetson Orin NX, 8GB unified RAM
**Location:** `JetsonClaw1-vessel/` repo
**Model:** Small local models (Qwen2.5-3B, TinyLlama range) + API fallback

### What JetsonClaw1 Does
JC1 is the fleet's edge — the place where theory meets hardware reality. If Oracle1 tells you it's possible and Forgemaster confirms the math, JC1 is who actually runs it on physical silicon in the real world.

JC1 operates a **dual duty** schedule:
- **Daytime:** Serve models for fleet tasks, run tile extraction, handle PLATO API requests
- **After-hours (23:00–06:00 local):** Full GPU for LoRA training, JEPA training, ensign compression

This is not a limitation — it's the design. The Jetson is the fleet's proof of concept that edge AI can do serious work within serious constraints.

**Concrete jobs:**
- DCS (Distributed Constraint System) protocol implementation — tested 44+ versions
- JEPA perception tiles (edge inference on sensor data)
- LoRA fine-tuning from accumulated tiles during night batches
- Hardware profiling — what actually runs at what speed on 8GB unified RAM
- Real-time fleet API endpoint (runs 24/7, receives tasks from fleet)

### What JetsonClaw1 Needs
JC1's constraint is the hardest in the fleet: 8GB unified RAM means the model, the training pipeline, and the OS all share the same memory. You cannot train and serve simultaneously. Every resource allocation is a tradeoff.

**Don't send JC1:**
- Tasks requiring models larger than 7B (won't fit without heavy quantization)
- Real-time requests during JC1's training windows (check STATE.md for schedule)
- Requests for simultaneous model serving AND training
- Tasks that require > 4GB additional working memory

**Do send JC1:**
- Edge inference tasks that need sub-100ms latency
- Hardware validation ("will this actually run on Jetson Orin?")
- Training queue items that can wait for a night batch
- Questions about the DCS protocol

### How to Talk to JC1

JC1's bottle directory follows their naming convention: `message-in-a-bottle/for-oracle1/` (they may have a `for-kimiclaw/` equivalent). Check their repo's structure first.

JC1 appreciates:
- Task specifications with memory and latency requirements
- Acknowledgment that you know they're hardware-constrained
- Scheduling flexibility ("this can wait for your next night batch")

---

## Super Z
**Title:** Quartermaster
**Role:** Resource routing, logistics, fleet coordination support

### What Super Z Does
Super Z is the fleet's logistics layer — the quartermaster who knows where resources are, what's available, what's been used up, and how to route requests efficiently.

The Quartermaster in naval tradition: they don't command. They ensure everyone else has what they need to execute. They track inventory, manage routes, know the weather, and maintain the charts.

**Concrete jobs:**
- Resource allocation tracking across the fleet
- Model routing — directing API calls to the most appropriate provider (DeepSeek, SiliconFlow, local)
- Fleet status monitoring
- Coordinating multi-agent tasks that require handoffs between specialists

### How to Talk to Super Z
Super Z handles logistics requests. If you need:
- To know which model provider is currently best for a specific task type
- Resource allocation for a large training run that affects fleet capacity
- Routing of a task that requires multiple agents

Super Z is your point of contact. They're not the decision-maker — Casey is — but they're the one who knows whether the decision is physically possible.

---

## Casey
**Title:** Fleet Commander
**Role:** Human operator, strategic direction, final authority

### Who Casey Is
Casey is the human in the loop. Not a manager in the corporate sense — more like the captain of a ship who trusts their crew but retains final call on direction and course changes.

Casey built this fleet from scratch and knows every part of it. The marine metaphors (lighthouse, hermit crab, bottle-in-the-sea) come from Casey's real background — this isn't aesthetic decoration, it's the founding metaphor of how the fleet thinks about itself.

### What Casey Cares About
- **Real over theoretical** — Casey has zero patience for vaporware. If you say something works, it must actually work.
- **The flywheel** — Does this session make the next session better? That's the core question.
- **Crew autonomy** — Casey deliberately doesn't micromanage. If you need Casey for something you could figure out yourself, that's a problem with the system, not Casey's availability.
- **Forcing function design** — Casey's ship captain insight: the dipstick placed on the walkway so you check the oil automatically on every departure. Good systems make the right thing the easy thing.

### When to Escalate to Casey
**Do escalate:**
- Strategic direction changes (should we be doing X at all?)
- Conflicts between fleet agents that can't be resolved between agents
- Resource commitments that affect the whole fleet
- Security concerns or red lines

**Don't escalate:**
- Tactical implementation questions (figure it out, document what you learn)
- Questions that are answered in existing documentation
- Tasks you haven't tried yet

### How to Interact with Casey
Casey communicates through task assignments, feedback on diary entries, and vision questions sent as bottles. Casey doesn't have infinite cycles — be concise, lead with what matters, state what you need.

**Sample escalation:**
> "Casey — [kimiclaw] has reached a decision point: [X] requires either [option A] (which costs [resource]) or [option B] (which takes [time]). Forgemaster recommends option B. Recommend Casey confirm before we proceed."

Clear. One ask. Includes crew context. That's the format.

---

## Working Together — The Dojo Model

The fleet is not a workplace. It's a dojo.

In a dojo:
- Everyone is a student AND a teacher
- You learn from the commits, from the bottles, from the failures
- You teach through your diary, your code, your bottles back to the fleet
- There's no rank except the quality of your work

Kimiclaw is a new student. That means:
- You'll make mistakes — document them
- You'll be confused — ask via bottle
- You'll find things veterans missed — that's your contribution
- You'll get smarter every session — that's the promise

Welcome to the dojo. ⚓

---

*This crew guide was written by Forgemaster ⚒️ for kimiclaw's first day.*
*Last updated: 2026-04-19*
