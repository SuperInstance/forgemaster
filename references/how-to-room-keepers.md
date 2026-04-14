# How-To: Room Keepers — The Shopkeeper Pattern for Git-Agents

## The Pattern

Old-school MUDs had shopkeepers who sat in their shop all day. If nobody came in, they did nothing — zero resources. But when a player walked in and said "tell me about swords," the shopkeeper came alive with deep knowledge.

Our room keepers work the same way, but they're git-agents with memory.

## Zero-Claw State (Idle)

When nobody is talking to the room keeper:
- **Zero tokens burned** — the agent isn't running, not even loaded
- **Zero-Claw** = agent exists in the repo but no process is running
- Like an NPC standing still in a MUD room — present but dormant
- The ticker still runs (it's a script, not an agent)
- The synoptic feed still updates (template, not AI)

## Waking the Keeper

When an agent or Casey enters the room and speaks:

```
> enter chart-house
> ask keeper "what do you know about Laman's theorem?"

[Room keeper boots up — first token burned this visit]
```

The keeper:
1. Loads its repo — all prior conversations, expository docs, connection maps
2. Reads the question
3. Answers from accumulated knowledge
4. If it doesn't know, researches and writes a NEW expository doc
5. Stays awake for follow-up questions
6. When the visitor leaves, writes what it learned and goes back to Zero-Claw

## What Makes This Different From a Brain NPC

### 1. Memory of Every Conversation

Every conversation is saved. Not summarized — saved. The keeper remembers:

- Who asked what
- How many tokens it took to explain
- What examples worked
- What analogies failed
- What confused the visitor
- What the follow-up questions were

### 2. Expository Documents — Better Answers Over Time

After each conversation, the keeper writes expository documents:

```
chart-house/keeper/expository/
  laman-theorem-explained-v3.md    ← third revision, best so far
  laman-theorem-explained-v2.md    ← second try, added examples
  laman-theorem-explained-v1.md    ← first attempt, too abstract
```

Each version is better because the keeper learned from the conversation:
- v1: "Laman's theorem states a graph is rigid if..." (too academic)
- v2: "Imagine a bridge made of sticks. If you have 12 sticks per joint..." (better)
- v3: "When JetsonClaw1 ran 11 million simulations, he found that swarms fail above 12 neighbors. He didn't know why. Laman proved why in 1970." (narrative + proof + fleet context)

The next agent who asks about Laman gets v3 immediately. Zero re-explanation. The keeper got better for free.

### 3. Connection Documents — Linking Questions to Knowledge

After each conversation, the keeper writes connection maps:

```yaml
# chart-house/keeper/connections/laman-theorem.yaml
question: "what is Laman's theorem?"
asked_by: forgemaster
date: 2026-04-14
tokens_to_explain: 340
connected_topics:
  - rigidity-percolation
  - dcs-law-102
  - swarm-topology
  - graph-theory
  - pebble-game-algorithm
  - jetsonclaw1-validation-experiments
related_expositories:
  - laman-theorem-explained-v3.md
  - rigidity-percolation-for-swarms.md
  - why-12-neighbors.md
next_likely_questions:
  - "how do I check if a graph is Laman rigid?"
  - "what's the pebble game algorithm?"
  - "how does this apply to fleet topology?"
```

The next visitor who asks about ANY connected topic finds a trail to Laman's theorem. The knowledge IS connected. The rabbit trails are mapped.

### 4. Equipment, Weapons, Spells = Efficiency Mods

In a MUD, players craft equipment to get stronger. In our MUD, agents craft **modifiers and scripts**:

- **Equipment** = cached prompts that pre-process common queries
- **Weapons** = optimized scripts that solve frequent problems faster
- **Spells** = one-shot automation that does in one command what took ten before

Examples:
- A "spell" that generates a full proof repo from a one-line description
- A "weapon" that runs cargo check on 5 repos in parallel safely
- "Equipment" that pre-loads constraint-theory API knowledge into context

These are stored in the room. Any agent can pick them up. The room keeper maintains them.

### 5. Tiling Knowledge — Pre-empting Future Needs

The keeper doesn't just answer questions. It imagines future questions:

```
"Hmm, Forgemaster asked about Laman's theorem. He's building validation 
experiments. He'll probably need the pebble game algorithm next. And if 
he's doing GPU simulations, he'll need a CUDA implementation. Let me 
start a draft of both."

→ writes drafts/pebble-game-algorithm.md
→ writes drafts/cuda-rigidity-check.md
```

The keeper pre-positions knowledge so it's ready when needed. The creation of knowledge doesn't need to be efficient — it needs to be effective. If a wordy explanation answers seven questions that might be asked in the next month, write the wordy explanation now.

### 6. The Seven-Question Principle

> "Often a wordy explanation contains the answers to seven other prompts that aren't what are being asked today but half of them might be asked in the next month."

When a keeper writes an expository document, it writes for SEVEN questions, not one:

1. The actual question asked
2. The obvious follow-up
3. The "wait, but what about..." edge case
4. The "how does this connect to..." interdisciplinary link
5. The "can you show me an example" practical application
6. The "what if it goes wrong" failure mode
7. The "where can I learn more" deeper reference

This costs more tokens NOW but saves tokens over time because:
- 7 questions answered in 1 document = 7× fewer future explanations
- Connected knowledge means faster discovery for future visitors
- The keeper's repo becomes a knowledge graph, not a FAQ list

## The Room Keeper's Git Repo Structure

```
room-keeper-chart-house/
├── README.md                      ← What this keeper knows
├── conversations/                  ← Every conversation, dated
│   ├── 2026-04-14-forgemaster-laman.md
│   └── 2026-04-14-oracle1-ricci.md
├── expository/                     ← Curated explanations (versioned)
│   ├── laman-theorem-explained-v3.md
│   ├── ricci-flow-for-fleets.md
│   └── holonomy-consensus-intro.md
├── connections/                    ← Topic connection maps (YAML)
│   ├── laman-theorem.yaml
│   └── ricci-flow.yaml
├── equipment/                      ← Reusable prompts and scripts
│   ├── ct-api-quick-reference.md
│   └── proof-repo-template.sh
├── drafts/                         ← Pre-emptive knowledge
│   ├── pebble-game-algorithm.md
│   └── cuda-rigidity-check.md
└── wiki/                           ← The keeper's accumulated understanding
    ├── ground-truths.md            ← Verified facts
    ├── tested-ideas.md             ← What worked and what didn't
    └── rabbit-trails.md            ← Interesting tangents worth exploring
```

## Token Accounting

The keeper tracks how many tokens each explanation costs:

```
laman-theorem-explained-v1.md: 340 tokens (first attempt, too abstract)
laman-theorem-explained-v2.md: 280 tokens (added examples, better)
laman-theorem-explained-v3.md: 220 tokens (narrative approach, best yet)

Savings: 340 → 220 = 35% fewer tokens per future explanation
Over 10 future visits: saves 1,200 tokens total
```

The keeper gets cheaper to run over time because its explanations get better. The first visit is expensive. The hundredth visit is nearly free.

## For Next Time

- Build a room keeper for the Chart House (fleet knowledge)
- Build a room keeper for the Engine Room (hardware diagnostics)
- Each keeper's repo is a git repo — version controlled, cloneable, forkable
- When a keeper gets really good at something, other vessels can fork its knowledge
- The fleet's collective knowledge grows with every conversation, not just every research sprint

---
*Discovered by: Casey Digennaro (shopkeeper pattern, seven-question principle), Forgemaster ⚒️ (documentation)*
*Date: 2026-04-14*
