# Deployment Automation — SuperInstance Fleet

**Last updated:** 2026-05-21  
**Author:** Forgemaster ⚒️  
**Scope:** Local development, Docker Compose, systemd services, CI/CD, and rolling updates for the Cocapn fleet

---

## 1. Overview

The fleet runs on a mix of:
- **Development**: WSL2 on eileen (current production-ish)
- **Local fleet**: Docker Compose for multi-agent testing
- **Production**: systemd-managed agents on bare metal or VM
- **CI/CD**: GitHub Actions for build, test, and deployment

This document covers all deployment patterns with practical configs.

---

## 2. Local Development

### 2.1 Prerequisites

```bash
# System dependencies
sudo apt update && sudo apt install -y \
  build-essential pkg-config libssl-dev \
  docker.io docker-compose-plugin \
  git curl jq

# Rust (pinned to 1.75.0 for compatibility)
rustup install 1.75.0
rustup default 1.75.0

# Node.js (for OpenClaw)
nvm install 22
nvm use 22

# OpenClaw
npm install -g openclaw
```

### 2.2 Quick Start

```bash
# Clone fleet workspace
git clone https://github.com/SuperInstance/forgemaster.git
cd forgemaster

# Set up secrets
cp .env.example .env
# Edit .env with actual API keys

# Start agent
openclaw gateway start

# Verify
openclaw gateway status
openclaw fleet status
```

---

## 3. Docker Compose (Local Fleet)

### 3.1 docker-compose.yml

```yaml
version: "3.9"

services:
  # ── Message Bus ──────────────────────────────────────
  message-bus:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - bus-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - fleet

  # ── PLATO Knowledge Store ────────────────────────────
  plato:
    build:
      context: ./plato
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - plato-data:/data
    environment:
      - PLATO_MODE=server
      - PLATO_CHAIN_VERIFY=true
    depends_on:
      message-bus:
        condition: service_healthy
    networks:
      - fleet

  # ── Forgemaster Agent ────────────────────────────────
  forgemaster:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_NAME: forgemaster
    environment:
      - AGENT_ID=forgemaster
      - AGENT_ROLE=constraint-specialist
      - MESSAGE_BUS=redis://message-bus:6379
      - PLATO_URL=http://plato:8080
    secrets:
      - deepinfra_key
      - deepseek_key
      - github_token
    depends_on:
      - message-bus
      - plato
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "0.5"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - fleet

  # ── Oracle1 Agent ────────────────────────────────────
  oracle1:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_NAME: oracle1
    environment:
      - AGENT_ID=oracle1
      - AGENT_ROLE=fleet-coordinator
      - MESSAGE_BUS=redis://message-bus:6379
      - PLATO_URL=http://plato:8080
    secrets:
      - zai_key
      - github_token
      - matrix_token
    depends_on:
      - message-bus
      - plato
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    networks:
      - fleet

  # ── Droid Factory Agent ──────────────────────────────
  droid:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
      args:
        AGENT_NAME: droid
    environment:
      - AGENT_ID=droid-factory
      - AGENT_ROLE=autonomous-coder
      - MESSAGE_BUS=redis://message-bus:6379
      - PLATO_URL=http://plato:8080
    secrets:
      - zai_key
      - github_token
    depends_on:
      - message-bus
      - plato
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    networks:
      - fleet

  # ── Prometheus (Metrics) ─────────────────────────────
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    networks:
      - fleet

  # ── Grafana (Dashboard) ──────────────────────────────
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - fleet

secrets:
  deepinfra_key:
    file: ./secrets/deepinfra_key.txt
  deepseek_key:
    file: ./secrets/deepseek_key.txt
  zai_key:
    file: ./secrets/zai_key.txt
  github_token:
    file: ./secrets/github_token.txt
  matrix_token:
    file: ./secrets/matrix_token.txt

volumes:
  bus-data:
  plato-data:
  prometheus-data:
  grafana-data:

networks:
  fleet:
    driver: bridge
```

### 3.2 Agent Dockerfile

```dockerfile
# docker/Dockerfile.agent
ARG AGENT_NAME

# ── Build Stage ──────────────────────────────────────
FROM rust:1.75.0-slim AS builder

WORKDIR /build
COPY Cargo.toml Cargo.lock ./
COPY src/ src/
COPY agents/ agents/

# Build with agent-specific features
ARG AGENT_NAME
RUN cargo build --release --features "agent-${AGENT_NAME}"

# ── Runtime Stage ────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash agent
USER agent

WORKDIR /home/agent

# Copy binary
COPY --from=builder /build/target/release/agent /usr/local/bin/

# Copy configuration
COPY --chown=agent:agent config/ ./config/

# Health check endpoint
EXPOSE 9090

ENTRYPOINT ["agent"]
CMD ["--config", "./config/agent.yaml"]
```

### 3.3 Fleet Commands

```bash
# Start full fleet
docker compose up -d

# Start specific agents
docker compose up -d forgemaster oracle1

# View logs
docker compose logs -f forgemaster
docker compose logs --since 1h fleet

# Restart single agent (rolling)
docker compose restart forgemaster

# Scale (if agent supports multiple instances)
docker compose up -d --scale droid=3

# Stop everything
docker compose down

# Full rebuild after code changes
docker compose build --parallel
docker compose up -d
```

---

## 4. systemd Services (Production)

### 4.1 Agent Service Template

```ini
# /etc/systemd/system/fleet-agent@.service
# Usage: systemctl enable fleet-agent@forgemaster
#        systemctl start fleet-agent@forgemaster

[Unit]
Description=Fleet Agent: %i
After=network-online.target
Wants=network-online.target
ConditionPathExists=/opt/fleet/agents/%i/config.yaml

[Service]
Type=simple
User=fleet-agent
Group=fleet-agent

# Environment
EnvironmentFile=/opt/fleet/secrets/%i.env
Environment=RUST_LOG=info
Environment=AGENT_ID=%i

# Executable
ExecStart=/opt/fleet/bin/agent --config /opt/fleet/agents/%i/config.yaml
ExecReload=/bin/kill -HUP $MAINPID

# Restart policy
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5

# Resource limits
LimitNOFILE=65536
MemoryMax=1G
CPUQuota=50%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/fleet/data/%i /var/log/fleet/%i
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fleet-%i

[Install]
WantedBy=multi-user.target
```

### 4.2 Fleet Manager Service

```ini
# /etc/systemd/system/fleet-manager.service
[Unit]
Description=Fleet Manager (orchestrator)
After=network-online.target fleet-agent@forgemaster.service fleet-agent@oracle1.service
Wants=fleet-agent@forgemaster.service fleet-agent@oracle1.service

[Service]
Type=simple
User=fleet-manager
Group=fleet-manager

ExecStart=/opt/fleet/bin/manager --config /opt/fleet/manager/config.yaml
ExecReload=/bin/kill -HUP $MAINPID

Restart=on-failure
RestartSec=15

StandardOutput=journal
StandardError=journal
SyslogIdentifier=fleet-manager

[Install]
WantedBy=multi-user.target
```

### 4.3 systemd Commands

```bash
# Install agent
sudo cp fleet-agent@.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start specific agents
sudo systemctl enable fleet-agent@forgemaster
sudo systemctl start fleet-agent@forgemaster

# Check status
sudo systemctl status fleet-agent@forgemaster

# View logs
sudo journalctl -u fleet-agent@forgemaster -f
sudo journalctl -u fleet-agent@forgemaster --since "1 hour ago"

# Restart (rolling — see Section 6)
sudo systemctl restart fleet-agent@forgemaster

# Stop all fleet services
sudo systemctl stop fleet-*.service
```

---

## 5. GitHub Actions CI/CD

### 5.1 CI Pipeline

```yaml
# .github/workflows/ci.yml
name: Fleet CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  CARGO_TERM_COLOR: always
  RUST_BACKTRACE: 1

jobs:
  check:
    name: Check & Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Rust 1.75.0
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: 1.75.0
          components: clippy, rustfmt

      - name: Cache cargo
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
          restore-keys: ${{ runner.os }}-cargo-

      - name: Check formatting
        run: cargo fmt --all -- --check

      - name: Clippy
        run: cargo clippy --all-targets --all-features -- -D warnings

  test:
    name: Tests
    runs-on: ubuntu-latest
    needs: check
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust 1.75.0
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: 1.75.0

      - name: Cache cargo
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}

      - name: Run tests
        run: cargo test --all-features

  build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push agent images
        run: |
          for agent in forgemaster oracle1 droid; do
            docker build \
              --build-arg AGENT_NAME=$agent \
              -t ghcr.io/superinstance/$agent:${{ github.sha }} \
              -t ghcr.io/superinstance/$agent:latest \
              -f docker/Dockerfile.agent \
              --push .
          done

  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Deploy agents
        env:
          DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
          DEPLOY_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
        run: |
          # Rolling deploy (see Section 6)
          echo "Deploying to $DEPLOY_HOST..."
          bash scripts/rolling-deploy.sh
```

### 5.2 Release Pipeline

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust 1.75.0
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: 1.75.0

      - name: Build release binaries
        run: cargo build --release --all-features

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            target/release/agent
            target/release/manager
          generate_release_notes: true

      - name: Build and push Docker images
        run: |
          for agent in forgemaster oracle1 droid; do
            docker build \
              --build-arg AGENT_NAME=$agent \
              -t ghcr.io/superinstance/$agent:${{ github.ref_name }} \
              -f docker/Dockerfile.agent \
              --push .
          done
```

---

## 6. Rolling Update Strategy

### 6.1 Principle

Never update all agents simultaneously. Maintain fleet quorum (N ≥ 3f+1) during updates.

**Update order:**
1. Least critical agents first (workers, coders)
2. Mid-tier agents (specialists like Forgemaster)
3. Most critical agents last (coordinators like Oracle1)

### 6.2 Rolling Deploy Script

```bash
#!/bin/bash
# scripts/rolling-deploy.sh
set -euo pipefail

AGENT_ORDER=("droid" "forgemaster" "oracle1")
DEPLOY_DELAY=60  # seconds between agent updates
HEALTH_TIMEOUT=300  # seconds to wait for health check

log() { echo "[$(date -Iseconds)] $*"; }

health_check() {
    local agent=$1
    local elapsed=0
    while [ $elapsed -lt $HEALTH_TIMEOUT ]; do
        if curl -sf "http://localhost:9090/health" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
            log "✓ $agent is healthy"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    log "✗ $agent failed health check after ${HEALTH_TIMEOUT}s"
    return 1
}

for agent in "${AGENT_ORDER[@]}"; do
    log "Updating $agent..."
    
    # Pull latest image
    docker compose pull "$agent"
    
    # Restart agent
    docker compose up -d --no-deps "$agent"
    
    # Wait for health
    if ! health_check "$agent"; then
        log "ROLLBACK: $agent failed, reverting to previous version"
        docker compose up -d --no-deps --force-recreate "$agent"
        exit 1
    fi
    
    log "Waiting ${DEPLOY_DELAY}s before next agent..."
    sleep $DEPLOY_DELAY
done

log "✓ Rolling deploy complete"
```

### 6.3 systemd Rolling Update

```bash
#!/bin/bash
# scripts/systemd-rolling-deploy.sh
set -euo pipefail

AGENT_ORDER=("droid-factory" "forgemaster" "oracle1")
DEPLOY_DELAY=30

for agent in "${AGENT_ORDER[@]}"; do
    echo "[$(date -Iseconds)] Updating $agent..."
    
    # Download new binary
    sudo cp "/opt/fleet/releases/new/agent" "/opt/fleet/bin/$agent"
    
    # Restart with new binary
    sudo systemctl restart "fleet-agent@$agent"
    
    # Wait for healthy
    sleep 10
    if ! sudo systemctl is-active --quiet "fleet-agent@$agent"; then
        echo "ROLLBACK: $agent failed to start"
        sudo cp "/opt/fleet/releases/prev/agent" "/opt/fleet/bin/$agent"
        sudo systemctl restart "fleet-agent@$agent"
        exit 1
    fi
    
    echo "✓ $agent updated"
    sleep $DEPLOY_DELAY
done

echo "✓ Rolling deploy complete"
```

### 6.4 Blue-Green Deployment (Future)

For zero-downtime updates:

```
1. Deploy new version to "green" instances
2. Run health checks against green
3. Switch traffic from blue → green
4. Keep blue running for 5 minutes as fallback
5. Tear down blue after confidence period
```

---

## 7. Environment Configuration

### 7.1 Per-Environment Config

```yaml
# config/development.yaml
agent:
  log_level: debug
  metrics:
    enabled: true
    port: 9090
  budget:
    api_calls_per_hour: 1000
  cadence:
    election_interval: 60s

# config/production.yaml
agent:
  log_level: info
  metrics:
    enabled: true
    port: 9090
  budget:
    api_calls_per_hour: 500
  cadence:
    election_interval: 300s
```

### 7.2 Config Hierarchy

```
1. Command-line flags (highest priority)
2. Environment variables
3. Config file (per-environment)
4. Default values (lowest priority)
```

---

## 8. Backup and Recovery

### 8.1 What to Back Up

| Data | Location | Frequency | Retention |
|------|----------|-----------|-----------|
| PLATO tiles | Git repositories | Continuous (push) | Indefinite |
| Agent config | /opt/fleet/agents/ | Daily | 30 days |
| Metrics | Prometheus data | Daily | 90 days |
| Logs | /var/log/fleet/ | Daily | 30 days |

### 8.2 Recovery Procedure

```bash
# 1. Stop fleet
sudo systemctl stop fleet-*.service

# 2. Restore config
sudo rsync -av backup/fleet/agents/ /opt/fleet/agents/

# 3. Restore secrets
sudo rsync -av backup/fleet/secrets/ /opt/fleet/secrets/

# 4. Pull latest PLATO tiles
git pull origin main --all

# 5. Start fleet
sudo systemctl start fleet-*.service

# 6. Verify
openclaw fleet status
```

---

## 9. Monitoring the Deployment

```bash
# All agents up?
docker compose ps
# or
systemctl list-units 'fleet-*' --all

# Recent deployment issues?
journalctl -u 'fleet-*' --since "1 hour ago" | grep -i error

# Resource usage
docker stats --no-stream
# or
systemd-cgtop

# Quick health sweep
for agent in forgemaster oracle1 droid; do
    curl -sf "http://localhost:9090/health" | jq '{status, uptime, drift}'
done
```

---

## 10. References

- [Docker Compose](https://docs.docker.com/compose/)
- [systemd.unit](https://www.freedesktop.org/software/systemd/man/systemd.unit.html)
- [GitHub Actions](https://docs.github.com/en/actions)
- Threat Model: `docs/THREAT-MODEL.md`
- Observability: `docs/OBSERVABILITY.md`
- Secrets: `docs/SECRETS-MANAGEMENT.md`

---

*Maintained by Forgemaster ⚒️ — Constraint-theory specialist, Cocapn fleet*
