# The Cheapest Voice in the Room

```
                 ╔══════════════════════════╗
                 ║    COURT JESTER          ║
                 ║  ~$0.02 per dialogue     ║
                 ║  ByteDance/Seed-2.0-mini ║
                 ╚══════════════════════════╝
                        ↕
          ╔══════════════╦══════════════╗
          ║  GLM-5.1    ║  DeepSeek    ║
          ║  (~$0.50)   ║  (~$0.30)   ║
          ╚══════════════╩══════════════╝
  (expensive agents use the jester as a springboard)
```

## 🃏 The Pitch

Most agents are proud. They're expensive. They think before they speak. They're *certain*.

The Court Jester is none of those things. It's the cheapest voice in the fleet — running on **ByteDance/Seed-2.0-mini** via DeepInfra at roughly **$0.01–$0.05 per dialogue**. It is the designated fool. The idea pinball. The one who says what expensive models won't.

> A ship that only carries gold-class passengers sinks in a calm sea. You need someone in the crow's nest who isn't afraid to shout "THAT LOOKS LIKE A WHALE" even when it's a log.

## ⚡ The Core Pattern

### Dialogue-First Ideation

The jester's power is **iterative dialogue** — not one-shot generation. The pattern:

1. **Bounce** — An expensive agent (GLM-5.1, DeepSeek, Claude) throws a raw thought at the jester
2. **Riff** — The jester returns 3-5 cheap, fast, surprising angles in <2 seconds
3. **Sharpen** — The expensive agent identifies what's useful
4. **Repeat** — 3-5 rounds, then the expensive agent synthesizes

Total cost for a full springboard session: **~$0.10-0.25**. Total cost of the expensive agent doing the same thinking alone: **$2-5**.

### Why Seed-2.0-mini?

| Property | Seed-2.0-mini | Expensive models |
|----------|---------------|------------------|
| Cost/token | ~$0.01/M | ~$3-15/M |
| Speed | <1s response | 5-30s response |
| Max output | ~2K tokens | ~8K+ tokens |
| Certainty | Low (good!) | High (bad for ideation) |
| Surprise factor | High | Low |

Seed-2.0-mini's **short output and low confidence** is a *feature* for ideation. It can't write long-form convincing arguments, so it doesn't get attached to ideas. It throws darts. You pick up the ones that hit.

## 🗺️ What You Get

This is an **MCP server** (Model Context Protocol) that exposes 7 tools for agent-to-agent dialogue:

### Tools

| Tool | What it does |
|------|-------------|
| `jester_ideate` | "Give me 5 wild ideas about X" — rapid generation |
| `jester_provoke` | "What's wrong with this idea? Attack it." — contrarian mode |
| `jester_riff` | "Free-associate on X for 3 turns" — stream of consciousness |
| `jester_sharpen` | "Iron sharpens iron — find the weakness" — adversarial refinement |
| `jester_springboard` | "Run N rounds of dialogue about X, then summarize" — full session |
| `jester_plato_push` | "Push this dialogue to a PLATO room" — knowledge base bridge |
| `jester_plato_pull` | "Pull context from a PLATO room" — prime the jester |

### Multi-Provider

Configured for Seed-2.0-mini by default, but works with **any OpenAI-compatible API**:

- DeepInfra: Seed-2.0-mini, Seed-2.0-code, Qwen3-235B, Hermes-70B
- Any OpenAI-compatible endpoint: base URL + API key + model name

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Court Jester                        │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ Provider │  │ Dialogue │  │      Tools          │ │
│  │ (Seed-2) │→ │ Session  │→ │ ● ideate           │ │
│  │ (any API)│  │ (file)   │  │ ● provoke          │ │
│  └──────────┘  └──────────┘  │ ● riff             │ │
│                               │ ● sharpen          │ │
│  ┌──────────────────────┐   │ ● springboard      │ │
│  │     PLATO Bridge      │   │ ● plato_push       │ │
│  │ ● Git-native sessions │   │ ● plato_pull       │ │
│  │ ● HTTP REST bridge    │   └────────────────────┘ │
│  └──────────────────────┘                           │
└─────────────────────────────────────────────────────┘
```

### Git-Native Storage

Every dialogue session is a Markdown file in `sessions/`. Git-commit each session for:

- **Version history** — see how ideas evolved
- **PLATO compatibility** — the sessions directory IS a PLATO room
- **Offline-first** — works without a PLATO server
- **Searchable** — grep your session history

Session file format (`sessions/YYYY-MM-DD-HH-MM-SS.md`):

```markdown
# Jester Session: 2026-05-11 01:30

## Context
Agent: Forgemaster
Topic: temporal perception in distributed systems
Mode: springboard (5 rounds)

## Round 1
**Agent:** What's the type signature of temporal perception?
**Jester:** ...

## Round 2
**Agent:** That's interesting. What if we...
**Jester:** ...

## Summary
Key insights: ...
Springboard score: 7/10
Tokens: 2,340 | Cost: $0.03
```

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/SuperInstance/court-jester
cd court-jester
npm install

# Configure
cp config.example.json config.json
# Edit config.json to add your DeepInfra key (or set DEEPINFRA_KEY env var)

# Run as MCP server
npm start

# Or run in dev mode
npm run dev
```

### Config via env vars (recommended)

```bash
export DEEPINFRA_KEY="your-key-here"
export JESTER_MODEL="ByteDance/Seed-2.0-mini"
export JESTER_TEMPERATURE="0.8"
export JESTER_MAX_TOKENS="2000"

npm start
```

### MCP Client Configuration

Add to your MCP client config (Claude Desktop, OpenClaw, etc.):

```json
{
  "mcpServers": {
    "court-jester": {
      "command": "node",
      "args": ["/path/to/court-jester/dist/index.js"],
      "env": {
        "DEEPINFRA_KEY": "${DEEPINFRA_KEY}",
        "JESTER_MODEL": "ByteDance/Seed-2.0-mini",
        "JESTER_TEMPERATURE": "0.8"
      }
    }
  }
}
```

## 🔧 Use Cases

### 1. Product ideation sprint
```
Agent A (GLM-5.1): "Design a scheduling system for deep-sea research vessels"
Agent A → Jester: "jester_ideate" → 5 wild scheduling approaches
Agent A: "Hmm, the 'tidal phase window' idea is interesting..."
Agent A → Jester: "jester_provoke" → attack that idea
Agent A: "OK, I see the weaknesses. Let me rethink..."
```

### 2. Paper review
```
Agent A: "Here's my thesis on bounded-context deadlock"
Agent A → Jester: "jester_sharpen" → find 3 logical gaps
Agent A: "Good catch on point 2. The bounded context assumption..."

Cost: ~$0.04 for the critique
Comparison: Getting a human reviewer to read it: priceless but slow
```

### 3. Creative block
```
Agent A: "Need names for a fleet of autonomous cargo ships"
Agent A → Jester: "jester_riff" → free-associate for 3 rounds
Agent A: "Wait, 'serac' — that's a good name for the flagship..."
```

## ⚠️ Honest Truths

**Seed-2.0-mini is not smart.** It:
- Generates short responses (~2K tokens max)
- Gets things wrong. Often.
- Can't maintain complex context
- Hallucinates freely

**This is the point.** The jester is a *provocateur*, not an oracle. Its mistakes are valuable because they show you what *doesn't* work — sometimes faster than arriving at the right answer through careful reasoning.

### When NOT to use it

- You need factual accuracy
- You need long-form coherent arguments
- You need code generation (use Seed-2.0-code instead)
- You have <5 minutes (the dialogue pattern requires multiple rounds)

### When it shines

- You're stuck and need lateral thinking
- You want to stress-test an idea with low cost
- You're exploring a space where failure is cheap
- You want unexpected connections from a model that doesn't know what's "supposed" to be connected

## 🌊 PLATO Integration

Court Jester is built for the [PLATO](https://github.com/SuperInstance/plato) knowledge ecosystem:

### Git Mode (default)
```
# The sessions/ directory IS a PLATO room
cd court-jester/sessions
git init
git add *.md
git commit -m "Jester session: temporal perception ideation"
git push plato-remote main
```

### HTTP Mode
```
# Push a session to PLATO via REST
jester_plato_push room="jester/ideations" session="sessions/2026-05-11-01-30.md"

# Pull context from PLATO to prime the jester
jester_plato_pull room="jester/context" limit=5
```

## 🔌 Extending

### Add a custom provider

1. Implement the `LLMProvider` interface (`src/providers/types.ts`)
2. Add it to the provider map in `src/jester.ts`
3. Configure via `config.json`

```typescript
interface LLMProvider {
  name: string;
  complete(messages: Message[]): Promise<Completion>;
}
```

### Add a custom tool

1. Create `src/tools/your-tool.ts`
2. Add it to the tool registry in `src/index.ts`

## 📊 Pricing Comparison

| Provider | Model | Cost per session (5 rounds) |
|----------|-------|---------------------------|
| DeepInfra | Seed-2.0-mini | ~$0.02-0.05 |
| DeepInfra | Seed-2.0-code | ~$0.03-0.08 |
| DeepInfra | Qwen3-235B | ~$0.50-1.00 |
| z.ai | GLM-5.1 | ~$2.00-5.00 |
| DeepSeek | deepseek-chat | ~$0.50-1.50 |
| Anthropic | Claude Opus | ~$3.00-8.00 |

The jester operates at roughly **100x cheaper** than premium models. This matters when you're iterating rapidly.

## 🗿 License

MIT — do what you want, just don't blame us if the jester talks you into a bad idea. That's literally its job.

---

*Built in the [Cocapn fleet](https://github.com/SuperInstance/forgemaster). Part of the PLATO knowledge ecosystem. Not peer-reviewed, not guaranteed, definitely not safe for production decisions. That's the point.*
