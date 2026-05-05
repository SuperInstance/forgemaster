# Cocapn AI Agent Fleet Runbook
Version: 1.3 (2024-06-05)
Last Updated: [Current Date]
Audience: Fleet SREs, On-Call Engineers, Cocapn Core Team
Scope: 9 containerized AI agents, 1,427 managed repos across 3 GitHub Orgs (`cocapn-core` (412), `cocapn-extensions` (289), `cocapn-community` (726))

---

## 1. Fleet Overview
### Core Agent Breakdown (9 Total)
All agents run on AWS ECS Fargate in `us-east-1`, with cross-region backup in `us-west-2`:
| Agent Name | ECS Service Name | Primary Workload |
|------------|------------------|------------------|
| Agent Alpha | `cocapn-agent-alpha` | New repo onboarding to Cocapn scanner |
| Agent Beta | `cocapn-agent-beta` | SAST/DAST code security scans |
| Agent Gamma | `cocapn-agent-gamma` | Automated PR review & security checks |
| Agent Delta | `cocapn-agent-delta` | Security incident triage & escalation |
| Agent Epsilon | `cocapn-agent-epsilon` | Sync fleet docs/runbooks with repo changes |
| Agent Zeta | `cocapn-agent-zeta` | Dependency vulnerability scanning (pip/npm/go.mod) |
| Agent Eta | `cocapn-agent-eta` | Validate new Cocapn service deploy health |
| Agent Theta | `cocapn-agent-theta` | GitHub repo access & agent audit logging |
| Agent Iota | `cocapn-agent-iota` | Sync internal KB with community repo docs |

### Critical Infrastructure Dependencies
- **Fleet Manager (FM)**: Primary orchestrator (2 instances: `fm-primary`/`fm-backup`)
- **Oracle1**: Global state oracle (single source of truth for repo inventory/workload assignments, backed up to S3 every 15min)
- **Monitoring**: Grafana dashboard at `grafana.cocapn.dev/fleet`, Slack alerts routed to `#cocapn-fleet-alerts`

---

## 2. Coordination Cadence
Follows strict scheduled syncs per your requirements:
### Oracle1 Schedule (UTC Top/Half Hour)
| Time | Action |
|------|--------|
| `:00` | Publish full 1,427-repo inventory snapshot to all agents + FM |
| `:30` | Publish updated workload assignment map (based on agent capacity and repo priority) |

### Fleet Manager (FM) Schedule (UTC 15/45 Past Hour)
| Time | Action |
|------|--------|
| `:15` | Run L1 health check aggregation across all 9 agents, publish health report to `PLATO-GLOBAL-FLEET`, trigger alerts for failed checks |
| `:45` | Validate completion of all workloads from the prior 30min, clear finished tasks from Oracle1 state, publish workload metrics |

#### Failover Rule: FM will automatically hand off to `fm-backup` if `fm-primary` fails 3 consecutive `:15` health checks.

---

## 3. I2I Bottle Protocol
### Definition
**I2I = Inter-Agent Intent**: Standardized secure communication between agents, FM, and Oracle1. A **Bottle** is the fixed-format data packet for all I2I traffic.
### Standard Bottle Schema (JSON)
```json
{
  "bottle_id": "uuid-v4",
  "sender_agent": "AGENT_GAMMA",
  "recipient_agent": "FLEET_MANAGER",
  "timestamp": "ISO 8601",
  "workload_metadata": {
    "workload_id": "WRK-78901",
    "repo_scope": ["cocapn-core/agent-gamma"],
    "priority": "MEDIUM",
    "deadline": "2024-06-05T14:30:00Z"
  },
  "health_data": {
    "agent_health_score": 97,
    "cpu_usage": 41,
    "memory_usage": 39
  },
  "expiration_seconds": 300,
  "signature": "hmac-sha256 of bottle_id+timestamp+sender_agent (signed with fleet HMAC key from SSM)"
}
```
### Routing & Retry Rules
1. **Priority Bottles (SEVERE/CRITICAL)**: Bypass standard queues, routed directly to FM + Oracle1
2. **Standard Bottles**: Routed via FM's workload queue
3. **Retry Logic**: Max 3 retries with backoff (10s → 30s → 60s). After 3 failed retries, bottle is sent to `PLATO-QUARANTINE` for manual review
4. **Quarantine**: On-call engineer must review quarantined bottles within 1 hour to re-route or discard.

---

## 4. PLATO Room Naming Convention
PLATO = **Pod-Level Agent Task Operations**: Standardized naming for all fleet communication and task tracking rooms (Slack Connect + Linear tickets):
1. **Global Fleet Rooms**:
   - `PLATO-GLOBAL-FLEET`: Primary fleet alerts, announcements, coordination
   - `PLATO-ORACLE-MONITOR`: Oracle1 state, backup, sync alerts
   - `PLATO-QUARANTINE`: Review failed I2I bottles/corrupted workloads
   - `PLATO-INCIDENT-RESPONSE`: Central hub for incident tracking
2. **Agent-Specific Rooms** (no duplicate abbreviations):
   - `PLATO-A-ONBOARD` (Alpha)
   - `PLATO-B-SCAN` (Beta)
   - `PLATO-G-PR` (Gamma)
   - `PLATO-D-TRIAGE` (Delta)
   - `PLATO-EPS-DOCSYNC` (Epsilon)
   - `PLATO-Z-DEP-SCAN` (Zeta)
   - `PLATO-ET-DEPLOY` (Eta)
   - `PLATO-TH-AUDIT` (Theta)
   - `PLATO-I-KBSYNC` (Iota)
3. **Workload-Specific Rooms**: `PLATO-WORKLOAD-[ORG]-[TYPE]` (e.g. `PLATO-WORKLOAD-COMMUNITY-ONBOARD`)
4. **Incident Rooms**: `PLATO-INCIDENT-[SEVERITY]-[YYYYMMDD-HHMM]` (e.g. `PLATO-INCIDENT-P1-20240605-1430`)

---

## 5. Health Checks
Split into automated, manual, and emergency checks:
### L1 Automated Health Checks (Every 5min, FM-Triggered)
| Check | Target | Threshold | Alert Channel |
|-------|--------|-----------|---------------|
| Agent Heartbeat | All 9 agents | Last heartbeat <2min ago | `PLATO-GLOBAL-FLEET`, PagerDuty (3 consecutive failures) |
| Resource Utilization | All ECS tasks | CPU/memory <70% | `PLATO-GLOBAL-FLEET` |
| Repo Sync Staleness | All agents | No repo sync >1hr | `PLATO-GLOBAL-FLEET` |
| I2I Bottle Success Rate | FM/Oracle1 | >99% | `PLATO-GLOBAL-FLEET` |
| Oracle1 Backup Validity | Oracle1 | S3 backup exists for last 15min | `PLATO-ORACLE-MONITOR` |

### L2 Manual Health Checks (Hourly, On-Call Engineer)
1. Validate all 9 agents passed L1 checks via Grafana
2. Confirm workload queue depth <100 items per agent
3. Verify scan coverage >99% across all 1,427 repos
4. Run credential validation script: `./scripts/verify-creds.sh`
5. Confirm Oracle1 repo count matches 1,427: `curl https://oracle1.cocapn.dev/api/list-repos | jq '. | length'`

### L3 Emergency Health Checks (On-Demand)
1. Restart unresponsive agent: `aws ecs update-service --cluster cocapn-fleet --service [SERVICE_NAME] --force-new-deployment`
2. Re-sync Oracle1 state from S3 backup:
   ```bash
   aws s3 cp s3://cocapn-oracle-backups/latest/state.json /opt/oracle1/state.json
   systemctl restart oracle1
   ```

---

## 6. Emergency Procedures
Split by severity:
### Severity 1 (Critical): >50% Agents Down, >700 Unmanaged Repos
1. Acknowledge PagerDuty alert immediately, create `PLATO-INCIDENT-P1-[TIMESTAMP]`
2. Trigger FM failover: SSH to `fm-backup` and run `./scripts/failover-fm.sh`
3. Pause all non-critical workloads: `curl -X POST https://fm-backup.cocapn.dev/api/pause-workloads`
4. Restart agents in low-impact batches first: Iota → Epsilon → Zeta → Beta → Eta → Gamma → Theta → Alpha → Delta
5. Restore Oracle1 state from latest S3 backup if corrupted
6. Re-enable non-critical workloads once all agents are healthy
7. Conduct post-mortem within 24hrs and update runbook

### Severity 2 (High): <50% Agents Down, Critical Workload Backlog
1. Alert on-call engineer in `#cocapn-fleet-alerts`
2. Restart affected agents one at a time, wait for L1 health checks to pass
3. Re-route backlogged workloads: `curl -X POST https://fm-primary.cocapn.dev/api/reroute-workload --data '{"workload_id": "WRK-12345", "recipient": "AGENT_BETA"}'`
4. Monitor for 1hr and post status updates to `PLATO-GLOBAL-FLEET`

### Severity 3 (Medium): Single Agent Outage, Minor Backlog
1. Notify the relevant agent-specific PLATO room
2. Restart the agent via AWS ECS console or CLI
3. Validate health check passes and clear backlog
4. Document incident in the fleet runbook log

---

## 7. Credential Rotation
### Scheduled Rotation (30 Day API Keys, 90 Day IAM Roles)
1. **Pre-Notification**: Post to `PLATO-GLOBAL-FLEET` 24hrs prior, announce maintenance window (00:00-02:00 UTC)
2. **Generate New Credentials**:
   - GitHub API keys: GitHub Org Settings > Developer Settings
   - Slack/ AWS IAM keys: 1Password > Cocapn Fleet > Active Credentials
3. **Update SSM Parameter Store**:
   ```bash
   aws ssm put-parameter --name /cocapn/fleet/github-api-key --value "NEW_KEY" --type SecureString --overwrite
   aws ssm put-parameter --name /cocapn/fleet/i2i-hmac-key --value "NEW_HMAC_KEY" --type SecureString --overwrite
   ```
4. **Rolling Restart**: Restart one agent at a time, wait for 5 consecutive L1 health checks before moving to the next
5. **Validate**: Run `./scripts/verify-creds.sh` to confirm all agents can access repos/APIs
6. **Archive Old Credentials**: Move expired keys to 1Password > Archived Credentials, mark 7-day expiration
7. **Log Rotation**: Document date, credentials used, and engineer name in the runbook

### Emergency Rotation (Compromised Key)
1. Immediately pause all workloads via Oracle1 API
2. Run the emergency rotation script: `aws s3 cp s3://cocapn-scripts/emergency-cred-rotate.sh ./ && chmod +x ./emergency-cred-rotate.sh && ./emergency-cred-rotate.sh`
3. Validate credentials work with `./scripts/verify-creds.sh`
4. Revoke compromised keys via their respective dashboards
5. Notify all relevant teams in `PLATO-GLOBAL-FLEET`

---

## 8. Deploy Checklist (For 1,427+ Repos)
### Pre-Deploy Checklist (24hrs Prior)
1. Run full test suite across all 9 agent repos: `pytest`/`npm test` confirm 100% pass rate
2. Validate I2I bottle schema compatibility: `./scripts/validate-bottle-schema.sh`
3. Update Oracle1 workload assignment map, confirm repo count = 1,427
4. Post deploy announcement to `PLATO-GLOBAL-FLEET`, set maintenance window
5. Pause non-critical workloads: `curl -X POST https://fm-primary.cocapn.dev/api/pause-workloads`
