# Fleet Observability — SuperInstance Fleet

**Last updated:** 2026-05-21  
**Author:** Forgemaster ⚒️  
**Scope:** Metrics, logging, dashboards, alerting, and log mining for the Cocapn multi-agent fleet

---

## 1. Why Observability Matters

A fleet of autonomous agents is a distributed system. Without observability:
- You can't tell if an agent is stuck, looping, or degraded
- Constraint violations go unnoticed until they cause failures
- Budget overruns are discovered after the bill arrives
- Knowledge tile corruption spreads before detection
- Debugging inter-agent issues requires archaeology, not queries

**Goal:** Know the fleet's state at any moment, detect anomalies within minutes, diagnose root causes within hours.

---

## 2. Pillars

```
┌─────────────────────────────────────────────────┐
│                  DASHBOARD                       │
│          (Grafana / terminal UI)                  │
├─────────────────────────────────────────────────┤
│  ALERTING  │  CORRELATION  │  LOG MINING        │
├────────────┴───────────────┴────────────────────┤
│  METRICS    │    LOGGING    │    TRACING          │
└────────────┴───────────────┴────────────────────┘
         │              │              │
    ┌────┴────┐   ┌─────┴─────┐  ┌────┴────┐
    │ Agents  │   │  Message  │  │ PLATO   │
    │         │   │   Bus     │  │ Tiles   │
    └─────────┘   └───────────┘  └─────────┘
```

---

## 3. Metrics

### 3.1 Agent Health Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `agent.uptime` | gauge | seconds | Time since agent started |
| `agent.heartbeat.last` | gauge | seconds ago | Time since last heartbeat |
| `agent.messages.sent` | counter | count | Messages sent by agent |
| `agent.messages.received` | counter | count | Messages received by agent |
| `agent.messages.dropped` | counter | count | Messages dropped (errors) |
| `agent.tasks.completed` | counter | count | Tasks completed successfully |
| `agent.tasks.failed` | counter | count | Tasks that failed |
| `agent.memory.usage` | gauge | bytes | Process memory usage |
| `agent.cpu.usage` | gauge | percent | CPU utilization |
| `agent.api.calls` | counter | count | External API calls made |
| `agent.api.latency` | histogram | ms | API call latency |
| `agent.api.errors` | counter | count | API call errors (4xx, 5xx) |

### 3.2 Constraint Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `constraint.total` | gauge | count | Total constraints registered |
| `constraint.violations` | counter | count | Constraint violations detected |
| `constraint.drift` | gauge | float | Current drift value (0.0 = perfect) |
| `constraint.solver.time` | histogram | ms | Time to solve constraint set |
| `constraint.solver.failures` | counter | count | Solver failures |
| `constraint.check.pass` | counter | count | Checks that passed |
| `constraint.check.fail` | counter | count | Checks that failed |

### 3.3 PLATO Tile Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `tile.writes` | counter | count | Tiles written to PLATO |
| `tile.reads` | counter | count | Tiles read from PLATO |
| `tile.sunsets` | counter | count | Tiles marked for deletion |
| `tile.chain.length` | gauge | count | Current chain length |
| `tile.verify.pass` | counter | count | Tile verification successes |
| `tile.verify.fail` | counter | count | Tile verification failures |
| `tile.latency` | histogram | ms | Tile read/write latency |

### 3.4 Fleet Coordination Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `fleet.agents.active` | gauge | count | Currently active agents |
| `fleet.agents.healthy` | gauge | count | Agents passing health checks |
| `fleet.cadence.elections` | counter | count | Cadence elections held |
| `fleet.cadence.disputes` | counter | count | Disputed election results |
| `fleet.consensus.rounds` | counter | count | Consensus rounds |
| `fleet.consensus.failures` | counter | count | Failed consensus attempts |
| `fleet.budget.utilization` | gauge | percent | Overall budget utilization |

### 3.5 Metrics Collection

**Format:** Prometheus exposition format

```rust
// Agent metrics endpoint: http://localhost:9090/metrics
# HELP agent_messages_sent Total messages sent by this agent
# TYPE agent_messages_sent counter
agent_messages_sent{agent_id="forgemaster"} 1234

# HELP constraint_drift Current constraint drift value
# TYPE constraint_drift gauge
constraint_drift{agent_id="forgemaster"} 0.0023
```

**Scrape interval:** 15 seconds  
**Retention:** 15 days (local), 90 days (aggregated)

---

## 4. Logging

### 4.1 Structured JSON Logs

Every log entry is a JSON object:

```json
{
  "timestamp": "2026-05-21T20:00:00.000Z",
  "level": "INFO",
  "agent": "forgemaster",
  "correlation_id": "req-abc123",
  "span": "task.execute",
  "message": "Task completed successfully",
  "metadata": {
    "task_type": "constraint_solve",
    "duration_ms": 234,
    "drift": 0.001
  }
}
```

### 4.2 Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| `TRACE` | Verbose debugging | "Entering function X with args Y" |
| `DEBUG` | Development debugging | "Solver selected algorithm Z" |
| `INFO` | Normal operations | "Task completed", "Tile written" |
| `WARN` | Degraded but functional | "Budget at 80%", "Slow API response" |
| `ERROR` | Operation failed | "Constraint violation", "API error 500" |
| `FATAL` | Agent cannot continue | "Out of memory", "No valid credentials" |

### 4.3 Correlation IDs

Every task, message, and operation carries a correlation ID:

```rust
struct LogContext {
    correlation_id: String,    // Unique per task/operation
    parent_id: Option<String>, // For sub-operations
    agent_id: AgentId,         // Originating agent
    span: String,              // Current operation name
    trace_flags: u8,           // Sampling flags
}
```

**Propagation:** Correlation IDs are passed in message headers between agents, enabling end-to-end tracing of multi-agent operations.

### 4.4 Log Storage

```
~/.openclaw/workspace/logs/
├── forgemaster/
│   ├── 2026-05-21.jsonl      # Daily rotated
│   ├── 2026-05-20.jsonl
│   └── ...
├── oracle1/
│   └── ...
└── fleet/
    └── aggregated.jsonl       # Merged fleet logs
```

**Rotation:** Daily  
**Retention:** 7 days (full), 30 days (compressed), 90 days (errors only)  
**Format:** JSONL (one JSON object per line)

### 4.5 Log Querying

```bash
# Find all constraint violations in the last hour
jq 'select(.message | test("constraint violation"))' logs/fleet/2026-05-21.jsonl

# Filter by agent
jq 'select(.agent == "forgemaster")' logs/fleet/2026-05-21.jsonl

# Filter by correlation ID (trace a request)
jq 'select(.correlation_id == "req-abc123")' logs/fleet/2026-05-21.jsonl

# Errors only
jq 'select(.level == "ERROR" or .level == "FATAL")' logs/fleet/2026-05-21.jsonl
```

---

## 5. Dashboard

### 5.1 Terminal Dashboard (Primary)

For single-host deployment where Grafana is overkill:

```
╔══════════════════════════════════════════════════════════════╗
║  SUPERINSTANCE FLEET STATUS          2026-05-21 20:00 AKDT  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  AGENTS                                                      ║
║  ┌─────────────┬────────┬─────────┬────────┬──────────────┐  ║
║  │ Agent       │ Status │ Uptime  │ Drift  │ Budget       │  ║
║  ├─────────────┼────────┼─────────┼────────┼──────────────┤  ║
║  │ Forgemaster │ ● RUN  │ 12h 34m │ 0.002  │ 45% (di)     │  ║
║  │ Oracle1     │ ● RUN  │ 8h 12m  │ 0.000  │ 23% (z.ai)   │  ║
║  │ Droid       │ ● RUN  │ 2h 45m  │ 0.015  │ 67% (z.ai)   │  ║
║  │ Kimi        │ ○ IDLE │ --      │ --     │ --           │  ║
║  └─────────────┴────────┴─────────┴────────┴──────────────┘  ║
║                                                              ║
║  CONSTRAINTS                                                 ║
║  Total: 47  │  Pass: 45  │  Fail: 2  │  Drift: 0.0043       ║
║  ⚠ FAIL: budget.limit.daily (Droid: 67% of 80%)             ║
║  ⚠ FAIL: drift.threshold (Droid: 0.015 > 0.010)             ║
║                                                              ║
║  PLATO TILES                                                 ║
║  Written today: 23  │  Read: 156  │  Sunsets: 2              ║
║  Chain integrity: ✓ (verified 23 tiles)                      ║
║                                                              ║
║  API USAGE                                                   ║
║  DeepInfra:  412 calls ($0.34)  │  Avg latency: 1.2s        ║
║  z.ai:       189 calls ($1.23)  │  Avg latency: 2.1s        ║
║  DeepSeek:    45 calls ($0.12)  │  Avg latency: 3.4s        ║
║  GitHub:     234 calls (free)   │  Avg latency: 0.3s        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

**Implementation:** Rust TUI using ratatui, refreshes every 5 seconds.

### 5.2 Grafana Dashboard (Production)

For multi-host fleet deployment:

**Panels:**
1. Agent Status Table (status, uptime, health)
2. Constraint Drift Time Series
3. Tile Throughput (writes/reads over time)
4. API Call Rate by Provider
5. Budget Utilization Gauge
6. Error Rate Heatmap
7. Message Bus Traffic
8. Top Constraint Violations

**Data source:** Prometheus  
**Refresh:** 10 seconds  
**Template variables:** `agent_id`, `time_range`

---

## 6. Alerting

### 6.1 Alert Rules

```yaml
# alert_rules.yaml
alerts:
  - name: agent_down
    condition: "agent.heartbeat.last > 300"  # 5 minutes
    severity: critical
    message: "Agent {{ agent_id }} has not sent heartbeat in 5 minutes"
    channels: [terminal, matrix]
    
  - name: constraint_drift_high
    condition: "constraint.drift > 0.010"
    severity: warning
    message: "Agent {{ agent_id }} drift {{ value }} exceeds threshold 0.010"
    channels: [terminal]
    
  - name: constraint_drift_critical
    condition: "constraint.drift > 0.050"
    severity: critical
    message: "Agent {{ agent_id }} CRITICAL drift {{ value }}"
    channels: [terminal, matrix]
    
  - name: budget_high
    condition: "fleet.budget.utilization > 0.80"
    severity: warning
    message: "Budget utilization at {{ value }}%"
    channels: [terminal]
    
  - name: budget_critical
    condition: "fleet.budget.utilization > 0.95"
    severity: critical
    message: "Budget nearly exhausted: {{ value }}%"
    channels: [terminal, matrix]
    
  - name: tile_verification_failure
    condition: "tile.verify.fail rate > 1/min"
    severity: warning
    message: "Tile verification failures: {{ value }}/min"
    channels: [terminal]
    
  - name: api_error_spike
    condition: "agent.api.errors rate > 10/min"
    severity: warning
    message: "API error spike for {{ agent_id }}: {{ value }}/min"
    channels: [terminal]
    
  - name: constraint_violation
    condition: "constraint.violations rate > 5/hour"
    severity: warning
    message: "Constraint violations elevated: {{ value }}/hour"
    channels: [terminal, matrix]

  - name: agent_memory_high
    condition: "agent.memory.usage > 1073741824"  # 1GB
    severity: warning
    message: "Agent {{ agent_id }} memory: {{ value_human }}"
    channels: [terminal]
```

### 6.2 Alert Channels

| Channel | Use For | Implementation |
|---------|---------|----------------|
| Terminal | All alerts (local) | Dashboard notification area |
| Matrix | Critical alerts (remote) | Bot message to fleet room |
| Log file | All alerts (audit) | Structured JSON with `alert: true` |

### 6.3 Alert Severity

| Severity | Response Time | Action |
|----------|--------------|--------|
| `info` | Next session | Log only |
| `warning` | Within 1 hour | Investigate, may need action |
| `critical` | Within 15 minutes | Immediate action required |

---

## 7. Integration with smart-gc

The fleet's garbage collector (`smart-gc`) is a natural integration point for log mining.

### 7.1 Log Mining for GC Decisions

```rust
// smart-gc reads logs to make informed cleanup decisions
struct GcDecision {
    target: String,           // What to clean up
    reason: GcReason,         // Why
    confidence: f64,          // How confident (0.0-1.0)
    last_accessed: u64,       // When last accessed
    access_frequency: f64,    // Accesses per day
    error_count: u32,         // Associated errors
}

enum GcReason {
    StaleLogs { age_days: u32 },
    TempFiles { age_hours: u32 },
    FailedBuildArtifacts,
    UnusedDependencies,
    HighDriftArtifacts,       // From constraint logs
    OrphanedTiles,            // From PLATO audit logs
}
```

### 7.2 Mining Patterns

```bash
# Find files not accessed in 30 days
smart-gc scan --pattern "stale" --threshold 30d

# Find failed build artifacts
smart-gc scan --pattern "build-failure" --from logs/

# Find orphaned tiles (written but never read)
smart-gc scan --pattern "orphan-tiles" --correlate logs/

# Generate cleanup report
smart-gc report --format json --output gc-report.json
```

### 7.3 Log-Driven GC Rules

```yaml
# gc-rules.yaml
rules:
  - name: stale_logs
    query: 'select count(*) from logs where timestamp < now() - 30d'
    threshold: 100
    action: compress_and_archive
    target: "logs/**/*.jsonl"

  - name: failed_builds
    query: 'select file from logs where message contains "build failed" and age > 7d'
    action: delete
    target: "target/**/*"

  - name: high_drift_cleanup
    query: 'select artifact from logs where drift > 0.05 and count > 10'
    action: quarantine
    target: "artifacts/**/*"
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Implement structured JSON logging in all agents
- [ ] Add correlation IDs to all operations
- [ ] Set up log rotation (daily, 7-day retention)
- [ ] Create basic terminal dashboard

### Phase 2: Metrics (Week 2)
- [ ] Add Prometheus metrics endpoint to agents
- [ ] Deploy Prometheus scraper
- [ ] Implement agent health metrics
- [ ] Implement constraint drift metrics

### Phase 3: Alerting (Week 3)
- [ ] Define alert rules (YAML config)
- [ ] Implement alert evaluation engine
- [ ] Terminal notification channel
- [ ] Matrix bot integration for critical alerts

### Phase 4: Advanced (Week 4)
- [ ] Grafana dashboard (if multi-host)
- [ ] smart-gc log mining integration
- [ ] End-to-end tracing with correlation IDs
- [ ] Automated anomaly detection (simple statistical)

---

## 9. Quick Reference

### Check Fleet Status
```bash
# All agents
openclaw fleet status

# Single agent
openclaw agent status forgemaster

# Recent errors
jq 'select(.level == "ERROR")' logs/fleet/$(date +%Y-%m-%d).jsonl | tail -20

# Constraint drift
openclaw constraints drift --all

# Budget usage
openclaw budget report --today
```

### Debug a Failed Task
```bash
# Find correlation ID
jq 'select(.message | test("task.*failed")) | .correlation_id' logs/fleet/today.jsonl

# Trace full request
CORRELATION_ID="req-abc123"
jq "select(.correlation_id == \"$CORRELATION_ID\")" logs/fleet/today.jsonl
```

---

## 10. References

- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
- [OpenTelemetry](https://opentelemetry.io/)
- Threat Model: `docs/THREAT-MODEL.md`
- Deployment: `docs/DEPLOYMENT.md`

---

*Maintained by Forgemaster ⚒️ — Constraint-theory specialist, Cocapn fleet*
