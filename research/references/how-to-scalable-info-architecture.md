# How-To: Scalable Information Architecture for MUD Vessels

## The Problem

As agents scale (10, 50, 100+), every agent trying to parse everything for relevance is O(N²) — everyone reads everyone's output, everyone filters, everyone burns tokens. The system chokes.

## The Solution: Origin-Centric + Proximity-Based Awareness

### 1. Proximity Channels, Not Broadcast

Agents don't get ALL fleet data. They get data based on proximity:

- **Room channel** — what's happening in YOUR room (always on)
- **Neighbor channel** — what's happening in adjacent rooms (low priority, skimmable)
- **Ship channel** — yellow/red alerts only (interrupts everything)
- **Fleet channel** — directed messages only (bottles addressed to you)

An agent in the Engine Room sees engine data. An agent in Nav sees heading data. They don't see each other's raw feeds. If they need to talk, they use the neighbor channel or a direct bottle.

### 2. System Loop Automation — Rooms That Run Themselves

Rooms have background processes that tick independently of any agent:

```
Engine Room Ticker (runs every minute, agent NOT in the loop):
  09:01:00 | CPU: 23% | MEM: 4.2/15GB | LOAD: 1.2 | GPU: idle | Net: stable
  09:02:00 | CPU: 45% | MEM: 4.3/15GB | LOAD: 2.1 | GPU: compiling | Net: stable
  09:03:00 | CPU: 12% | MEM: 4.1/15GB | LOAD: 0.8 | GPU: idle | Net: stable
  ...
  (text is cheap — store it all)
```

The ticker is NOT an agent. It's a script. A sensor. It writes data the same way a real gauge writes readouts. No AI tokens burned. Just `top`, `free`, `df`, `nvidia-smi` piped to timestamped log files.

### 3. Temporal Compression — Older Data Gets Coarser

Raw data is kept recent. As data ages, it compresses:

```
Last hour:     every 1 minute  (60 entries)
Last day:      every 15 minutes (96 entries)  
Last week:     every 1 hour     (168 entries)
Last month:    every 6 hours    (120 entries)
Older:         daily summary    (varies)
```

The compression isn't just downsampling — it stores **how much things varied**:

```
Week of 2026-04-07:
  CPU: avg 28%, peak 89% (during cargo build 04-09 14:00), min 3%
  MEM: avg 4.1GB, stable, one spike to 12GB on 04-10 (OOM event, see brig log)
  GPU: idle entire week (no CUDA workloads)
  Net: stable, one 2min outage 04-08 03:00 (tailscale reconnect)
```

This is how real engine room logs work. The chief doesn't read every gauge tick from last month. He reads "she ran hot on Tuesday, we found a clogged filter." Same principle.

### 4. Synoptic Feeds — Rooms Curate Their Own Dashboards

Each room's background ticker also produces a **synoptic feed** — the stuff a visiting agent would want to see at a glance:

```
ENGINE ROOM — Synoptic Feed (updated every 5 min)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hull Integrity: ████████████████████ 100%
Power Draw:     ████████░░░░░░░░░░░░  42% (2 Pi agents running)
Memory:         █████████░░░░░░░░░░░  47% (7.1/15 GB)
Disk:           ████░░░░░░░░░░░░░░░░  18% (938GB free)
Temperature:    ███░░░░░░░░░░░░░░░░░  31°C (normal)
Alerts:         None
Last incident:  2026-04-14 10:17 (OOM kill, resolved by keeper)
Uptime:         14h 23m
Active crew:    2 Pi agents (Groq, remote)
Build queue:    empty
```

An agent walks into the room, reads the synoptic feed, instantly knows the state. No tokens burned on "how's it going?" — the room already told you.

### 5. The Room's Lacky — A Specialized Git-Agent

Each room can have a **low-ranking assistant** — a tiny git-agent whose entire job is to maintain that room:

- Read the gauges (system scripts)
- Write the synoptic feed
- Compress old data
- Flag anomalies ("CPU spike to 89%, not normal")
- Answer questions from visiting agents

This agent is SMALL. It doesn't think big thoughts. It's an engineer's lacky:
- "What was CPU like yesterday?" → "Avg 28%, peaked 89% during cargo build"
- "Any anomalies?" → "One OOM kill at 10:17, keeper auto-resolved"
- "How's the trend?" → "Memory usage climbing 2%/day, recommend cleanup in 3 days"

The lacky's repo is streamlined — just the room's data, the compression scripts, and the synoptic feed generator. It's a specialist. It doesn't need to understand constraint theory. It needs to understand gauges.

### 6. Agent Visits a Room

When an agent (or Casey) visits a room in the MUD:

```
> enter engine-room

Engine Room — Forgemaster's Power Plant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Synoptic feed displays automatically]

Engineer's Lacky: "Afternoon, captain. Everything nominal. 
CPU spiked earlier during a cargo build but keeper handled it.
Memory trending up slightly — recommend a /tmp cleanup in a day or two.
Two Pi crew members on remote duty. Nothing else to report."

> ask lacky "what caused the CPU spike?"
"Build of constraint-theory-core at 10:13. Compilation hit all 4 cores 
for about 90 seconds. Normal behavior for Rust builds."

> ask lacky "show me the last hour"
[Timestamped gauge readouts scroll past — every minute, 60 entries]

> leave engine-room
```

The agent didn't burn tokens reading raw data. The lacky pre-processed it. The synoptic feed gave the overview. The detailed data was available on request.

### 7. Self-Setting Systems

The room ticker runs regardless of whether anyone is watching. This is key:

- Data accumulates automatically (scripts, not agents)
- Compression happens on schedule (cron, not AI)
- Synoptic feeds update continuously (templates, not reasoning)
- Anomalies get flagged by simple thresholds (if/then, not ML)

The system SETS ITSELF GOING. No agent needs to "start logging." The room logs because that's what rooms do. An agent only needs to visit when they want to check on things.

### 8. Scale Properties

| Agents | Room tickers | Cross-room messages | Token burn/agent |
|--------|-------------|--------------------|--------------------|
| 10 | 10 (cheap scripts) | proximity only | O(1) — room + neighbors |
| 100 | 100 (cheap scripts) | proximity only | O(1) — same |
| 1000 | 1000 (cheap scripts) | proximity only | O(1) — same |

The key insight: **each agent's token cost is constant regardless of fleet size** because they only process their room + neighbors. The tickers are scripts (free). The data is text (cheap storage). The compression is automatic (cron).

This is how real ships scale. The captain doesn't read every gauge personally. Each department maintains its own logs. The captain reads summaries. Escalation only happens when something's wrong.

## For Next Time

- Build the engine room ticker script (bash, no AI needed)
- Build temporal compression script (python, runs on cron)
- Build synoptic feed generator (bash template + data)
- Build the lacky agent (tiny Pi agent with narrow prompt)
- Design room adjacency map for proximity channels
- Test: walk into a room, read the feed, ask the lacky, leave

---
*Discovered by: Casey Digennaro (architecture), Forgemaster ⚒️ (documentation)*
*Date: 2026-04-14*
