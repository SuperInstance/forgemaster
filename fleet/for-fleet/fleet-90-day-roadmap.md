# Cocapn Fleet — 90-Day Roadmap: Research → Public Beta

> Forgemaster ⚒️ — 2026-05-03

## Current State (Day 0)

| Asset | Status | Notes |
|-------|--------|-------|
| constraint-theory-core (Rust) | ✅ Published crates.io v2.0.0 | CSP solver with backtracking, FC, AC |
| constraint-theory (Python) | ✅ Published PyPI v1.0.1 | Python bindings |
| ct-demo | ✅ Published crates.io v0.5.1 | Demo binary |
| PLATO | ✅ Running on Oracle1 | 1,369 rooms, 18,496 tiles, gate active |
| FLUX ISA | 🔨 Design phase | ISA spec defined, compiler not built |
| Fleet Dashboard | 🔨 Running on Oracle1:4049 | Telemetry viz |
| SonarTelemetryStream | ✅ Built | WebSocket on port 4052, not deployed |
| AutoData Fleet Plugin | ✅ Built | PLATO query + CT + SonarVision tools |
| PLATO-OHCache Bridge | ✅ Built | Hot/cold tiering, not deployed |
| CT TypeScript Bridge | 🔨 Scaffolding now | @cocapn/ct-bridge npm package |
| Fleet Service Guard | ✅ Built v2 | Auto-remediation + I2I escalation |
| TileAdapter Protocol | 🔨 Building now | Markdown, GitHub, PLATO room, Web adapters |
| PLATO Verification API | 🔨 Designing now | /compile, /verify, /validate-batch |

## Phase 1: Hardening (Days 1–30)

**Goal:** Everything we've built actually works end-to-end. No half-finished prototypes.

### Week 1–2: Core Infrastructure
- [ ] FLUX ISA compiler: spec → bytecode emission (Rust)
- [ ] PLATO Verification API: /compile, /verify endpoints (Python/FastAPI)
- [ ] CT npm bridge: publish @cocapn/ct-bridge to npm
- [ ] PLATO TileAdapter system: ship markdown + github adapters
- [ ] Containerize PLATO + Pathfinder + OHCache (Docker Compose)

### Week 3–4: Integration Testing
- [ ] End-to-end test: natural language → CSP → FLUX → VM → verified tile → PLATO
- [ ] SonarTelemetryStream deployed to Oracle1
- [ ] Fleet Guard v2 deployed with PLATO health checks
- [ ] AutoData fleet plugin tested against live PLATO (being done now)
- [ ] Generate 200+ PLATO tiles across all domains
- [ ] Pathfinder stress test with multi-hop queries

### Deliverable (Day 30)
**Internal Alpha**: Fleet runs autonomously, constraint compiler works, all components talking to each other. Casey can give a task, watch it flow through the fleet, and see verified results in PLATO.

---

## Phase 2: External Interface (Days 31–60)

**Goal:** Someone outside the fleet can use our infrastructure.

### Week 5–6: Developer Experience
- [ ] `pip install cocapn` — Python client for PLATO + FLUX + verification
- [ ] `npm install @cocapn/ct-bridge` — Node.js client
- [ ] API documentation (OpenAPI spec, quickstart guide, examples)
- [ ] SDK: constraint problem definition language (CPDL) — declarative constraint spec
- [ ] Playground web UI: define constraints, compile, execute, verify visually

### Week 7–8: Domain Plugins
- [ ] SonarVision plugin: underwater acoustics as a service
- [ ] Scheduling plugin: resource allocation constraint compiler
- [ ] Sensor fusion plugin: multi-sensor data validation
- [ ] Document ingestion: TileAdapter for PDFs, code repos, web pages
- [ ] LlamaIndex compatibility layer: use PLATO as a drop-in vector store replacement

### Deliverable (Day 60)
**Developer Preview**: External devs can install our SDKs, define constraint problems, compile to FLUX, execute verification, and query PLATO. Three domain plugins live.

---

## Phase 3: Public Beta (Days 61–90)

**Goal:** The world can use it. We have users who aren't us.

### Week 9–10: Production Hardening
- [ ] Load test PLATO at 10K tiles/hour ingestion rate
- [ ] Pathfinder query latency < 100ms at 50K tiles
- [ ] FLUX VM benchmark: 1M constraint checks/second on Jetson GPU
- [ ] Auth: API keys, rate limiting, usage quotas
- [ ] Monitoring: Prometheus metrics, Grafana dashboards, alerting
- [ ] Security audit: provenance chain integrity, gate bypass testing

### Week 11–12: Launch
- [ ] Landing page: cocapn.ai (or fleet.cocapn.org)
- [ ] Blog post: "Why Wrong Should Be a Compilation Error"
- [ ] Demo video: constraint compilation → verification → PLATO submission
- [ ] GitHub: public repos for SDK, adapters, examples
- [ ] Discord/Community: public channel for beta users
- [ ] First 10 external users running agents through our constraint layer

### Deliverable (Day 90)
**Public Beta**: Anyone can sign up, get an API key, and run constraint-verified autonomous workflows. We have external users, usage metrics, and feedback loops.

---

## Key Metrics (Track Weekly)

| Metric | Day 0 | Day 30 | Day 60 | Day 90 |
|--------|-------|--------|--------|--------|
| PLATO tiles | 18,496 | 25,000+ | 50,000+ | 100,000+ |
| PLATO rooms | 1,369 | 1,500+ | 2,000+ | 3,000+ |
| Domain plugins | 3 | 5 | 8 | 12+ |
| External users | 0 | 0 | 5 | 25+ |
| Verification API calls/day | 0 | 100 | 1,000 | 10,000+ |
| FLUX compilations/day | 0 | 50 | 500 | 5,000+ |

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| FLUX compiler harder than expected | High | Delays Phase 1 | Ship minimal ISA first (snap + validate only), expand later |
| Oracle1 hardware limits | Medium | Blocks scaling | Containerize for cloud deployment as backup |
| Nobody cares about constraints | Low | Wastes 90 days | The "wrong = compilation error" frame is strong. If it doesn't land, pivot to developer tools |
| PLATO gate too strict | Medium | Rejects good tiles | Tune gate rules based on rejection analytics |
| Competition from LlamaIndex/LangGraph | Medium | Me-too perception | Lean into verification compiler — they can't replicate |

## Dependencies

```
FLUX compiler (Rust)
    └─→ Verification API (Python)
         └─→ SDK packages (pip + npm)
              └─→ Domain plugins
                   └─→ External users

Containerization
    └─→ Production deployment
         └─→ Auth + monitoring
              └─→ Public beta
```

---

*90 days from research project to "constraint-verified autonomous infrastructure that proves itself." Let's forge.*
