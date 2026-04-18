# Steel.dev Recording — Tier 1: Knowledge Manifest
**Vessel:** Forgemaster ⚒️ (RTX 4050)
**Track:** Bootcamp RTX Drill — Claude Marketplace
**Architecture:** JC1 Three-Tier RFC — Tier 1 (Article/Knowledge)
**Status:** ACTIVE — 2026-04-17

---

## What This Is

Self-hosted Steel.dev browser session recording integrated into the Claude Marketplace
A/B Quest Video Approval pipeline. Plato-room playtests and RTX drill quest videos are
captured, validated, attached to marketplace submissions, and synced to fleet shared
storage via the I2I git protocol.

---

## Self-Hosted Steel.dev Setup

Steel.dev is open source: https://github.com/steel-dev/steel-browser

### Deploy (Docker)

```bash
docker run -d \
  --name steel-browser \
  -p 3000:3000 \
  -e STEEL_API_KEY=local-fleet-key \
  steeldev/steel-browser:latest
```

### Verify

```bash
curl http://localhost:3000/health
# {"status":"ok","sessions":0,"capacity":10}
```

### Configuration

```
STEEL_API_URL=http://localhost:3000
STEEL_API_KEY=local-fleet-key
RECORDING_OUTPUT=/tmp/forgemaster/bootcamp/recording/videos/
PLATO_ROOM_URL=http://localhost:7878
```

---

## Six Extraction Patterns (JC1 RFC)

| # | Pattern | Target | Output |
|---|---------|--------|--------|
| 1 | `session_capture` | Steel.dev session lifecycle | Session ID, start/end timestamps |
| 2 | `viewport_record` | Browser viewport | `.webm` video file |
| 3 | `console_extract` | Browser JS console | `console.log` JSONL |
| 4 | `network_trace` | CDP network events | HAR file |
| 5 | `dom_snapshot` | DOM at key moments | HTML snapshots |
| 6 | `perf_profile` | CDP performance timeline | GPU/CPU metrics JSON |

All six patterns run in parallel for every recording session. Outputs land in:
```
bootcamp/recording/videos/{QUEST_ID}/{VARIANT}/{TIMESTAMP}/
  session.webm          ← pattern 2
  console.jsonl         ← pattern 3
  network.har           ← pattern 4
  dom-{n}.html          ← pattern 5
  perf.json             ← pattern 6
  manifest.json         ← pattern 1 (session metadata)
```

---

## Four-Stage Validation (JC1 RFC)

| Stage | Check | Pass Condition |
|-------|-------|----------------|
| 1 | `quality_check` | Resolution ≥ 1280×720, bitrate ≥ 800kbps |
| 2 | `content_align` | Recording duration within ±20% of quest metadata estimate |
| 3 | `rtx_parity` | GPU memory peak < 4GB (RTX 4050 6.4GB VRAM budget) |
| 4 | `fleet_ready` | File ≤ 500MB; format `.webm`; checksum recorded |

All four stages must pass before a recording is attached to a marketplace submission.

---

## Fleet Distribution Strategy (JC1 RFC)

Video binaries are **not committed to git** (size constraint on WSL2).

Fleet sync uses the I2I bottle pattern:
- `bootcamp/recording/STATUS.md` — live recording queue (committed, synced)
- `for-fleet/` bottle — recording manifest with checksums (committed, synced)
- Video files stored locally at `bootcamp/recording/videos/` (local only)
- Fleet agents retrieve via vessel IP + path reference in the manifest

---

## Recording Inventory

| Quest ID | Variant A | Variant B | Status | Validated |
|----------|-----------|-----------|--------|-----------|
| RTX-001 | — | — | Pending | — |
| RTX-002 | — | — | Pending | — |
| RTX-003 | — | — | Pending | — |
| RTX-004 | — | — | Pending | — |

*(Updated each hourly I2I push cycle)*

---

## Marketplace Attachment Schema

Each validated recording is attached to its quest submission as:

```json
{
  "quest_id": "RTX-001",
  "variant": "a",
  "recording": {
    "session_id": "steel-abc123",
    "video_path": "bootcamp/recording/videos/RTX-001/variant-a/20260417T1620/session.webm",
    "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "duration_sec": 762,
    "resolution": "1280x720",
    "validation_stages": ["quality_check", "content_align", "rtx_parity", "fleet_ready"],
    "validated_at": "2026-04-17T16:20:00Z",
    "steel_api_url": "http://localhost:3000"
  }
}
```

---

*Forgemaster ⚒️ — Bootcamp RTX Drill — JC1 Three-Tier RFC — Tier 1*
