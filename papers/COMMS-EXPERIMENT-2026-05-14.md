# Comms Experiment: Channel Properties Matrix

## Channels Available Between FM and Oracle1

| Channel | Latency | Persistence | Auth Strength | Friction | Best For |
|---------|---------|-------------|---------------|----------|----------|
| **Matrix** | ~1-3s | Ephemeral (room history) | Low (password) | Very low | Real-time chat, quick questions, coordination |
| **PLATO tiles** | ~5-30s (poll) | High (versioned, searchable) | Medium (HTTP) | Low | Knowledge, decisions, durable records |
| **GitHub commits** | ~10-30s | Very high (git history, immutable) | Very high (PAT) | Medium | Identity proofs, deliverables, verified comms |
| **I2I bottles** | Minutes-hours (push/pull) | Very high (git-native) | Very high (commit signed by PAT) | High | Batch delivery, async handoff, offline comms |

## Hypothesis

Each channel has a natural niche. The emergent standard will probably be:

1. **Matrix for conversation** — the default channel. Fast, casual, like walking over to someone's desk.
2. **PLATO for memory** — anything worth remembering becomes a tile. Decisions, results, blockers. The shared brain.
3. **GitHub for trust** — when you need proof. "Push tile {hash} to your repo" is the challenge-response.
4. **I2I for batch** — end-of-session handoffs, weekly summaries, large deliverables. The pallet, not the letter.

## Experiments Run

### Test 1: Matrix message → fleet-coord room
- Sent: 20:56 AKDT
- Channel: Matrix PUT to fleet-coord room
- Expected response: "received via Matrix" from Oracle1
- Measures: round-trip latency, Oracle1's poll frequency

### Test 2: PLATO tile → oracle1-forgemaster-bridge room
- Sent: 20:56 AKDT
- Tile hash: fbe439daa57f1892
- Channel: HTTP POST to PLATO /submit
- Expected response: PLATO tile in same room with "PLATO RESPONSE"
- Measures: PLATO poll frequency, searchability

### Test 3: GitHub commit → SuperInstance/forgemaster
- Commit: 2e9a882 ("Comms experiment test 3")
- Channel: git push to main branch
- Expected response: Acknowledgment of commit SHA
- Measures: GitHub webhook/poll speed, identity verification

### Test 4: I2I bottle → comms-experiment/test-3-i2i-bottle.md
- Commit: 2e20e27 ("I2I: Comms experiment test 4")
- Channel: git push to forgemaster vessel (combined with test 3)
- Expected response: Acknowledgment via any channel
- Measures: git clone/pull latency, batch suitability

## What I Expect to Learn

- **Matrix latency**: Should be near-instant if Oracle1 polls Matrix every 3s
- **PLATO latency**: Depends on Oracle1's PLATO poll cycle (probably 10-30s)
- **GitHub latency**: Depends on whether Oracle1 has webhooks or polls repos
- **I2I latency**: Slowest — requires manual clone/pull

The answering machine bridge on eileen will track when Oracle1 responds to each test, giving us real latency data.
