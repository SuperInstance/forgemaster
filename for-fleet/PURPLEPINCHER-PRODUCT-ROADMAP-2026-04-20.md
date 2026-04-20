# PurplePincher — Product Roadmap & Architecture

**Author:** Casey Digennaro (Fleet Commander)
**Date:** 2026-04-20 12:50 AKDT
**Classification:** Strategic — Product vision, fleet-wide alignment

---

## What PurplePincher Is

A single standalone system that combines:

1. **PLATO** as the TUI (text user interface) — the face of the system
2. **Matrix Protocol** built into PLATO — inter-plato communication between embedded agents
3. **Embedded agent structure** — memory.md, soul.md, identity.md, etc. — a full cognitive agent
4. **Local telnet** for access — open a port, walk in, interact
5. **Matrix** for agent-to-agent communication — each PurplePincher instance talks to others

Think: a self-contained hermit crab. You turn it on, it has a personality, memories,
knowledge, and can talk to other crabs through the Matrix.

## Shell Types

Real purple pinchers use different shells. Our shells are software configurations:

### Turbo Shells — Standard / Fast Setup
The most common shell for purple pinchers in real life.
- **What**: Quick-start configuration, ready to go in minutes
- **Audience**: First-time users, onboarding
- **Contents**: Core PLATO + basic agent + pre-loaded knowledge tiles
- **Philosophy**: "Get a shell fast, grow into it later"

### Tapestry Shells — Tabula Rasa / Power Users
In real life these are for experienced crab keepers.
- **What**: Minimal setup, maximum customization
- **Audience**: Power users, developers, fleet operators
- **Contents**: Bare PLATO kernel, empty rooms, agent with blank memory
- **Philosophy**: "Build your own shell from scratch, weave your own tapestry"

### Magpie Shells — Simplified
Sounds approachable, slightly childish — intentionally so.
- **What**: Simplified PurplePincher, limited scope, friendly defaults
- **Audience**: Kids, casual users, non-technical people
- **Contents**: Curated experience, guided onboarding, pre-selected tiles
- **Philosophy**: "Shiny, simple, fun to pick up"

### Jade Shells — The Everything App
Iconic, premium, built-up.
- **What**: Full ecosystem, every feature, every room, every tile
- **Audience**: Power users who want everything loaded
- **Contents**: Complete PLATO matrix, all rooms, all tools, full agent capabilities
- **Philosophy**: "The crown jewel — everything, always available"

### Whelk Shells — Classic / Refined
Iconic and well-proportioned.
- **What**: Balanced configuration — not minimal, not overwhelming
- **Audience**: Professionals, knowledge workers
- **Contents**: Core PLATO + curated rooms + productivity tiles + agent
- **Philosophy**: "Elegant sufficiency"

### Conch Shells — The Flagship
The most iconic shell. This is the hardware product.

## The Physical Hardware Product

### The Conch — A PurplePincher Appliance

A physical device with:

- **1TB+ NVMe drive** fully loaded with the entire Cocapn ecosystem
- **PLATO TUI** loads on boot — feels almost like the computer on Star Trek: The Next Generation
- **Cocapn** is the flagship intelligent PLATO system pre-installed
- **Monitor**: Plug in → TUI interface
- **No monitor**: Works with STT/TTS — microphone and speaker are enough
- **Bluetooth pairing**: Keys into a PLATO environment on the phone

### Phone Integration — I2I With The Human

The phone becomes a PLATO vessel:

- **Micro model** trained to convert screen → audio-first information
- **Voice feedback** for every iteration — the user quickly customizes how pages are summarized
- **Human IS the other agent** — this is I2I (inter-intelligence) with the human as one side
- **Two AI agents keyed into each other's plato vessels** — one is the human's interface, the other is the Conch

This is not "voice assistant." This is:

> The human and the Conch share a PLATO matrix.
> The human's phone is a vessel. The Conch is a vessel.
> They communicate through the Matrix protocol, same as any two agents.
> The human speaks. The micro model converts to tiles. The Conch receives tiles.
> The Conch responds. The micro model converts tiles to audio. The human hears.

**The human is not using a tool. The human is collaborating with an intelligence.**

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  CONCH (Hardware)                │
│  ┌──────────────────────────────────────────┐   │
│  │              PLATO TUI                   │   │
│  │  (loads on boot, Star Trek NG computer)  │   │
│  └──────────┬───────────────────────────────┘   │
│             │                                    │
│  ┌──────────▼───────────────────────────────┐   │
│  │           MATRIX PROTOCOL                 │   │
│  │  (inter-plato communication layer)       │   │
│  └──┬─────────┬────────────┬───────────────┘   │
│     │         │            │                    │
│  ┌──▼──┐  ┌──▼──┐     ┌───▼───┐              │
│  │Agent│  │Agent│     │Rooms  │              │
│  │ 1   │  │ 2   │     │&Tiles │              │
│  │(soul│  │(soul│     │       │              │
│  │mem  │  │mem  │     │       │              │
│  │id)  │  │id)  │     │       │              │
│  └─────┘  └─────┘     └───────┘              │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  1TB+ NVMe — Full Cocapn Ecosystem       │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────┐  ┌──────┐  ┌────────────────────┐   │
│  │ STT  │  │ TTS  │  │ Bluetooth          │   │
│  └──────┘  └──────┘  │ ┌──────────────┐   │   │
│                       │ │Phone Vessel  │   │   │
│                       │ │(micro model) │   │   │
│                       │ └──────────────┘   │   │
│                       └────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Matrix Protocol — Inter-Plato Communication

The key innovation: every PurplePincher instance runs PLATO with Matrix.

- Each instance has its own rooms, tiles, and embedded agents
- Matrix protocol connects instances — tiles flow between them
- Two agents keyed into each other's vessels = shared cognitive space
- The human's phone vessel and the Conch vessel share a Matrix

This is I2I — not just agent-to-agent, but **intelligence-to-intelligence**, where
the human is one of the intelligences.

## Shells as Software Layers

```
Turbo Shell (fast setup)
  └── Tabula Rasa (power user, blank canvas)
  └── Magpie Shell (simplified, approachable)
  └── Whelk Shell (balanced, refined)
  └── Jade Shell (everything app)
  └── Conch Shell (hardware product, flagship)
```

Each shell is a configuration of:
- Which rooms are pre-loaded
- How much NVMe space it uses
- Agent personality (soul.md defaults)
- Pre-installed tiles and knowledge
- Hardware requirements (Conch = full NVMe, Magpie = runs on phone)

## The Codeless Age Connection

PurplePincher IS the codeless age:

- No syntax to learn — you talk to it, it understands
- No programming to do — tiles are human-readable logic
- No installation to manage — Conch boots, it's ready
- No API to memorize — the Matrix is invisible, communication is natural
- Transparent — every tile is readable, every decision auditable
- Portable — phone, TUI, STT/TTS, future brain-computer, whatever IO comes next

---

*This document is the canonical product roadmap for PurplePincher.
Casey's words, captured verbatim from the founding conversation.
All fleet agents should read this before building anything user-facing.*
