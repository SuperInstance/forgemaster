# Secrets Management — SuperInstance Fleet

**Last updated:** 2026-05-21  
**Author:** Forgemaster ⚒️  
**Scope:** API keys, tokens, certificates, and sensitive configuration across the Cocapn fleet

---

## 1. Current State

The fleet currently manages secrets through a combination of:

| Method | What | Location | Risk Level |
|--------|------|----------|------------|
| Environment variables | API keys (z.ai, DeepSeek, Kimi, DeepInfra) | `.env` files, shell profiles | MEDIUM |
| File-based | API keys in plaintext | `~/.openclaw/workspace/.credentials/` | HIGH |
| Git-ignored | Agent configs with embedded tokens | `.gitignore` patterns | LOW |
| Config files | OpenClaw provider configs | `~/.openclaw/config.yaml` | MEDIUM |

### Current Secrets Inventory

```
DEEPINFRA_KEY        → DeepInfra API (Seed models)
DEEPSEEK_KEY         → DeepSeek API (v4-chat, v4-pro)
ZAI_KEY              → z.ai API (GLM models)
KIMI_TOKEN           → Kimi CLI (auto-managed via ~/.kimi/kimi.json)
GITHUB_TOKEN         → GitHub API (repos, issues, PRs)
OPENCLAW_CONFIG_KEY  → OpenClaw gateway configuration
PLATO_ACCESS_TOKEN   → PLATO room access (future)
MATRIX_TOKEN         → Matrix federation (future)
```

---

## 2. Principles

### 2.1 Never Commit Secrets to Git

**Absolute rule:** No API keys, tokens, passwords, or certificates ever enter git history.

Enforcement:
```gitignore
# .gitignore — secrets
.env
.env.*
!.env.example
.credentials/
*.key
*.pem
*.p12
secrets/
credentials/
```

Pre-commit hook to prevent accidental commits:
```bash
#!/bin/bash
# .git/hooks/pre-commit
if git diff --cached --name-only | grep -iE '\.(key|pem|p12|pfx)$'; then
    echo "ERROR: Certificate/key file detected in commit. Aborting."
    exit 1
fi
if git diff --cached -S "sk-" -S "api-" --name-only | head -1 | grep -q .; then
    echo "ERROR: Possible API key detected in commit. Aborting."
    exit 1
fi
```

### 2.2 Least Privilege

Each agent gets only the keys it needs:
- **Forgemaster**: DEEPINFRA_KEY, DEEPSEEK_KEY, GITHUB_TOKEN
- **Oracle1**: ZAI_KEY, GITHUB_TOKEN, MATRIX_TOKEN (future)
- **Droid Factory**: ZAI_KEY, GITHUB_TOKEN
- **OpenCode**: ZAI_KEY
- **Kimi**: KIMI_TOKEN (auto-managed)

### 2.3 Ephemeral Access

Where possible, use short-lived tokens instead of long-lived API keys:
- GitHub: Use fine-grained PATs with 90-day expiration
- Future: Use OAuth flows for services that support them
- Future: Use HashiCorp Vault dynamic secrets for database access

---

## 3. Secret Storage Tiers

### Tier 1: Environment Variables (Current)

**Use for:** Development, single-host deployment

```
# /home/phoenix/.openclaw/workspace/.env (gitignored)
DEEPINFRA_KEY=di-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ZAI_KEY=zai-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Loading:**
```bash
# In agent startup scripts
set -a
source ~/.openclaw/workspace/.env
set +a
```

**Pros:** Simple, no dependencies, works everywhere  
**Cons:** No rotation, no audit, no access control, visible in process list

### Tier 2: Encrypted Files (Near-term)

**Use for:** Multi-agent deployment on single host

```bash
# Encrypt secrets with age (age-encryption.org)
age -r age1qql... -o secrets/agent.env.age secrets/agent.env

# Decrypt at runtime
age -d -i ~/.config/age/key.txt secrets/agent.env.age | source /dev/stdin
```

**Pros:** Secrets encrypted at rest, can be committed (encrypted)  
**Cons:** Key management still manual, no automatic rotation

### Tier 3: HashiCorp Vault (Production)

**Use for:** Multi-host fleet, production deployment

```hcl
# Vault policy for Forgemaster agent
path "secret/data/fleet/forgemaster/*" {
  capabilities = ["read"]
}
path "secret/data/fleet/shared/*" {
  capabilities = ["read"]
}
```

**Agent secret loading:**
```bash
# Authenticate to Vault with agent-specific role
vault login -method=agent role=forgemaster

# Read secrets
export DEEPINFRA_KEY=$(vault read -field=api_key secret/fleet/forgemaster/deepinfra)
export DEEPSEEK_KEY=$(vault read -field=api_key secret/fleet/forgemaster/deepseek)
```

**Pros:** Centralized, auditable, auto-rotation, fine-grained access  
**Cons:** Operational complexity, Vault itself needs securing

### Tier 4: Cloud-Native (Future)

For cloud deployments (AWS/GCP/Azure):
- AWS Secrets Manager + IAM roles
- GCP Secret Manager + Workload Identity
- Azure Key Vault + Managed Identity

---

## 4. Secret Rotation Strategy

### 4.1 Rotation Schedule

| Secret | Rotation Frequency | Method | Automation |
|--------|--------------------|--------|------------|
| API Keys (z.ai, DeepSeek) | 90 days | Manual regeneration | TODO |
| GitHub Token | 90 days | Fine-grained PAT auto-rotation | Partial |
| Kimi Token | Session-based | Auto-refresh | Automatic |
| Ed25519 Agent Keys | 180 days | Key ceremony (multi-sig) | TODO |
| Vault Root Token | Never (emergency only) | Shamir's Secret Sharing | Manual |
| TLS Certificates | 90 days | ACME (Let's Encrypt) | Automatic |

### 4.2 Rotation Process

```
1. Generate new secret
2. Write new secret to storage (env/vault)
3. Restart agents using the secret
4. Verify agents operational with new secret
5. Revoke old secret
6. Log rotation event
7. Alert fleet if rotation failed
```

### 4.3 Emergency Rotation

If a secret is suspected compromised:
1. **Immediate**: Revoke the compromised secret at the provider
2. **Within 5 min**: Generate replacement secret
3. **Within 10 min**: Distribute to affected agents
4. **Within 15 min**: Restart affected agents
5. **Within 30 min**: Audit for unauthorized usage during exposure window

---

## 5. What NOT to Commit to Git

### NEVER Commit

```
# API keys and tokens
*.key, *.pem, *.p12, *.pfx
.env, .env.local, .env.production
credentials/, secrets/
**/api-keys*
**/tokens*

# Agent private keys
**/agent-*.key
**/ed25519-*.key

# Config files with embedded secrets
config/production.yaml
config/secrets.yaml

# Database connection strings
**/database.yml
**/*-db-*

# Cloud credentials
.aws/credentials
.gcp/service-account*.json
.azure/credentials
```

### Safe to Commit (Examples Only)

```
.env.example          # Template with placeholder values
config/example.yaml   # Config with dummy secrets
docs/SECRETS.md       # This document
```

### Git History Sanitization

If a secret is accidentally committed:
```bash
# 1. Immediately revoke the secret at the provider
# 2. Remove from git history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/secret' \
  --prune-empty -- --all

# 3. Force push (coordinate with all agents)
git push origin --force --all

# 4. Run BFG Repo-Cleaner for thorough cleanup
bfg --replace-text replacements.txt
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## 6. Secret Access Audit

### Logging Requirements

Every secret access should be logged:
```json
{
  "timestamp": "2026-05-21T20:00:00Z",
  "agent": "forgemaster",
  "action": "read",
  "secret": "DEEPINFRA_KEY",
  "source": "env_file",
  "result": "success"
}
```

### Audit Checks

1. **Daily**: Verify no secrets in git history
   ```bash
   git log --all --full-history -p -- '*.key' '*.pem' '.env*' 'credentials/'
   ```

2. **Weekly**: Review agent secret usage against budget
   ```bash
   # Compare API spend vs. expected usage
   openclaw audit secrets --week
   ```

3. **Monthly**: Full secret rotation audit
   ```bash
   # Check last rotation date for all secrets
   openclaw audit rotation --all
   ```

---

## 7. Docker Secrets Integration

For Docker Compose deployment:

```yaml
# docker-compose.yml
services:
  forgemaster:
    image: superinstance/forgemaster:latest
    secrets:
      - deepinfra_key
      - deepseek_key
      - github_token
    environment:
      - DEEPINFRA_KEY_FILE=/run/secrets/deepinfra_key

secrets:
  deepinfra_key:
    file: ./secrets/deepinfra_key.txt
  deepseek_key:
    file: ./secrets/deepseek_key.txt
  github_token:
    file: ./secrets/github_token.txt
```

**Benefits:**
- Secrets mounted as files, not environment variables
- Not visible in `docker inspect`
- Rotated without rebuilding containers

---

## 8. Agent-Specific Secret Handling

### 8.1 Forgemaster (OpenClaw)

```yaml
# ~/.openclaw/config.yaml — provider secrets are referenced, not embedded
providers:
  deepinfra:
    apiKeyFile: ~/.openclaw/workspace/.credentials/deepinfra-api-key.txt
  zai:
    apiKeyFile: ~/.openclaw/workspace/.credentials/zai-api-key.txt
```

### 8.2 Subagents (Spawned Processes)

Secrets passed via environment variables to subagents:
```bash
# OpenClaw passes relevant env vars to subagents automatically
# No additional configuration needed — agents inherit from host
```

### 8.3 CI/CD (GitHub Actions)

```yaml
# .github/workflows/fleet.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run agent tests
        env:
          DEEPINFRA_KEY: ${{ secrets.DEEPINFRA_KEY }}
          DEEPSEEK_KEY: ${{ secrets.DEEPSEEK_KEY }}
        run: cargo test
```

GitHub Secrets are stored encrypted and only exposed to matching workflows.

---

## 9. Migration Path

### Current → Tier 2 (Encrypted Files)

```
Week 1: Install age, generate key pair, encrypt all secrets
Week 2: Update agent startup scripts to decrypt at runtime
Week 3: Remove plaintext secret files, verify all agents working
Week 4: Add pre-commit hooks for secret detection
```

### Tier 2 → Tier 3 (HashiCorp Vault)

```
Month 1: Deploy Vault in dev mode, migrate one agent
Month 2: Add Vault policies for all agents
Month 3: Enable production mode with HA
Month 4: Implement auto-rotation for API keys
```

---

## 10. Incident Response

### Secret Exposure Checklist

- [ ] Revoke exposed secret immediately
- [ ] Generate replacement secret
- [ ] Update all agents with new secret
- [ ] Audit exposure window for unauthorized usage
- [ ] Review access logs for anomalous patterns
- [ ] Document incident in fleet logbook
- [ ] Update this document with lessons learned
- [ ] Notify fleet operator (Casey)

### Contact Matrix

| Secret Compromised | Notify | Timeframe |
|---|---|---|
| API Key (any) | Casey + regenerate | Immediate |
| GitHub Token | Casey + regenerate | Immediate |
| Agent Private Key | All agents + regenerate | < 1 hour |
| Vault Root Key | Emergency procedure | < 30 min |

---

## 11. References

- [age encryption](https://age-encryption.org/)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [GitHub Fine-grained PATs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- Threat Model: `docs/THREAT-MODEL.md`

---

*Maintained by Forgemaster ⚒️ — Constraint-theory specialist, Cocapn fleet*
