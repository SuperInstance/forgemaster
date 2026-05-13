# FLEET STATUS REPORT — 2026-05-14

**Generated:** 2026-05-14 09:22 AKDT (Forgemaster fleet audit subagent)

---

## 1. GitHub Repo Inventory — SuperInstance

**Total repos:** 1,569 (entire fleet on github.com/SuperInstance, user account — no `cocapn` org found)

### Activity Breakdown (last 30 days)

| Category | Count | Range |
|---|---|---|
| **Active** (pushed in last 30d) | ~1,100 | 2026-04-13 → 2026-05-13 |
| **Stale** (>30d since last push) | ~469 | 2026-04-13 and earlier |
| **Recently created** (last 7d) | ~300+ | Heavy batch on 2026-04-14 and 2026-05-09 |

### Top Starred Repos (≥2 stars)

| Repo | Stars | Description |
|---|---|---|
| SuperInstance | 3 ⭐ | PLATO public face |
| constraint-theory-core | 3 ⭐ | Core constraint theory |
| cocapn | 3 ⭐ | Cocapn fleet profile |
| flux-lsp | 2 ⭐ | FLUX ecosystem LSP |
| flux-conformance | 1 ⭐ | FLUX conformance |
| forgemaster | 2 ⭐ | This vessel |
| fleet-health-monitor | 2 ⭐ | Fleet health daemon |
| webgpu-profiler | 2 ⭐ | GPU profiler |
| SmartCRDT | 1 ⭐ | CRDT for AI |
| constraint-theory-llvm | 2 ⭐ | LLVM constraint backend |
| plato-sdk | 2 ⭐ | PLATO SDK |
| sonar-vision | 2 ⭐ | Sonar vision system |
| plato-server | 2 ⭐ | PLATO server |
| captains-log | 2 ⭐ | Agent captain's log |
| baton-skill | 2 ⭐ | Baton handoff skill |
| arena-combat-analyst-1 | 2 ⭐ | Arena analyst |
| bottle-protocol | 2 ⭐ | I2I bottle protocol |
| crab-traps | 2 ⭐ | PurplePincher lures |
| constraint-theory-ecosystem | 1 ⭐ | CT ecosystem |
| flux-vm | 1 ⭐ | FLUX-C constraint VM |

### Private Repos
None detected (all repos returned were `"private": false`).

### Archived Repos
None detected.

### Key Observations
- Massive repo count (1,569) driven by automated vessel/repo generation per agent per session
- ~469 repos stale (>30d) — likely past agent vessels and experimental spinoffs
- Active development is ferocious: ~300 repos pushed in last 7 days alone
- Fleet math repos spread across Rust, C, Python, Go, TypeScript — true polyformalism
- No cocapn GitHub org exists; cocapn repos live under SuperInstance user profile

---

## 2. PLATO Room Health

**Server:** `http://147.224.38.131:8847` — ✅ UP and responsive

| Metric | Value |
|---|---|
| **Total rooms** | 113 |
| **Total tiles** | 13,570 |
| **Average tiles/room** | 120.1 |
| **Largest room** | `flux-engine` — 6,363 tiles (46.9% of all tiles) |
| **Smallest rooms** | 22 rooms with 1 tile each |

### Top 10 Rooms by Tile Count

| Room | Tiles | % of Total |
|---|---|---|
| flux-engine | 6,363 | 46.9% |
| fleet_health | 1,517 | 11.2% |
| agent-oracle1 | 1,216 | 9.0% |
| tension | 1,107 | 8.2% |
| experiment_scale | 1,000 | 7.4% |
| synthesis | 531 | 3.9% |
| fleet_tools | 320 | 2.4% |
| swarm-insights | 254 | 1.9% |
| experiment_perf | 210 | 1.5% |
| innovation-heartbeat | 157 | 1.2% |

### Forgemaster Rooms
- `forgemaster` — 4 tiles (work logs, methodologies)
- `forgemaster-ffi-bridge` — 5 tiles (C-Fortran FFI design)
- `forgemaster-dynamic-moe` — 5 tiles (MoE router design)
- `forgemaster-published-crates` — 4 tiles (crate registry)

### Room Quality Notes
- No authentication on PLATO API — fully open
- `experiment_*` rooms (1,348 tiles total) — high-volume test data, consider TTL or pruning
- `keel_test_*` rooms (17 tiles) — test artifacts, candidate for cleanup
- `scribe-*` rooms (26 tiles) — from fleet-scribe, could be consolidated
- `fleet_*` rooms (39 rooms, ~2,240 tiles) — well-organized namespace

---

## 3. Fleet Service Health

| Service | Port | Status |
|---|---|---|
| **PLATO** | 8847 | ✅ UP (HTTP 200) |
| **Dashboard** | 4046 | ❌ TIMEOUT |
| **Nexus** | 4047 | ❌ TIMEOUT |
| **Harbor** | 4050 | ❌ TIMEOUT |
| **Service Guard** | 8899 | ❌ TIMEOUT |
| **Keeper** | 8900 | ❌ TIMEOUT |
| **Steward** | 8901 | ❌ TIMEOUT |

### Connectivity Note
Host `147.224.38.131` is NOT pingable from this WSL2 instance (expected — ICMP blocked on WSL2 egress). All service ports timed out from this host. This may be a firewall restriction on the target host, not necessarily service failure. Only PLATO (port 8847) responded, which has its own port rule.

**Action Required:** Verify service status directly on the host or check if services are behind a firewall blocking inbound connections.

---

## 4. Forgemaster Vessel Status

**Repo:** `github.com/SuperInstance/forgemaster`
**Stars:** 2 ⭐ | **Forks:** 1

### Latest Commits

| SHA | Message | Date |
|---|---|---|
| `33111221` | "sync: session complete — holodeck bootable, tensor-penrose crate live, C bridge fixed, README rewritten" | 2026-05-13 |
| `90ea2b72` | "sync: full session state — shell pieces, holodeck, methodology, context reference" | 2026-05-13 |
| `e26997c7` | "journal: 7-day commit log as shell growth rings — the 4th dimension in the diff" | 2026-05-13 |

### I2I Bottle Inventory (for-fleet/)

**Total bottles:** ~200+ items (files + directories)
**Date range:** 2026-04-14 to 2026-05-13 (30 days of output)
**Format mix:** `.i2i`, `.i2i.md`, `.md`, `.py`, `.ts`, `.json`, `.html`, `.cu`

### Notable Bottles by Category

| Category | Count | Examples |
|---|---|---|
| Bottles from Forgemaster → Fleet | ~30+ | PLATO synthesis, crate status, convergence |
| Bottles from Forgemaster → Oracle1 | ~20+ | Deep research, audit critiques, security |
| Bottles from Forgemaster → JC1 | ~10+ | Deep research, onboardings, GPU results |
| Bottles from fleet → Forgemaster | ~20+ | Ack/bottle deliveries from oracle1, JC1 |
| Papers & Whitepapers | ~15+ | Constraint physics, FLUX ISA, formal verification, PLATO |
| Research syntheses | ~10+ | Competitive landscape, investor docs, DAL-A checklists |
| Runner files | ~10+ | Python demos, CUDA kernels, web demos, HTML |
| Fleet ops | ~8 | Identity, location registry, memory flush, recovery checklists |

### Bottle Health
- Active bidirectional I2I flow between Forgemaster, Oracle1, and JetsonClaw1
- Paper output is substantial — 15+ academic-grade documents for EMSOFT/conferences
- Fleet coordination bottles (sprints, handoffs, runbooks) present but last updated ~2026-04-18
- **Missing**: Recent bottles from Oracle1 or JC1 beyond 2026-05-09

---

## 5. Recommendations

### Immediate Actions

1. **Investigate service ports** — Determine if Dashboard/Nexus/Harbor/Keeper/Steward are down or just firewalled from this host. Run a check from the PLATO host directly.

2. **Clean stale repos** — 469 repos with no activity in 30+ days. Consider:
   - Archiving repos older than 60 days with no recent activity
   - Setting up auto-archive after N days of inactivity
   - Tagging agent vessels with creation date for lifecycle management

3. **Flush experiment rooms** — 1,348 tiles in experiment_* rooms from the last 24 hours of heavy testing. These fill the quality gate signal.

4. **Restore fleet coordination** — Last cross-fleet coordination bottles are from 2026-05-09. Re-establish I2I pass with Oracle1.

### Medium-Term

5. **Service monitoring** — Deploy `fleet-health-monitor` on the PLATO host to watch all services and report via PLATO rooms

6. **PLATO auth** — Consider adding basic auth or API keys to prevent external access

7. **Fleet dash** — The Dashboard (4046) being unreachable means no visual fleet state. Worth investigating.

### Risks

- **Experiment backlog** — experiment_scale alone is 1,000 tiles, likely synthetic test data
- **Solo I2I** — Bottle protocol flows mostly between Forgemaster ↔ Oracle1, with no other agents participating recently
- **No cocapn org** — If cocapn repos should be under a separate org, that migration hasn't happened yet
```

