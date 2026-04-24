# Night Shift Task Queue — ACTIVE

## ⚠️ OPERATING MODE: AUTONOMOUS — DO NOT STOP

When heartbeat fires, you MUST be doing one of these. Pick one. Start immediately.

## Priority 1: GSM-ify Lucineer repos into PLATO tiles
- Read /tmp/lucineer-analysis/superinstance-index/README.md for room plan
- Read actual repo content in /tmp/lucineer-analysis/Lucineer/
- Write 10-15 tiles per batch, submit via port 4042, push every batch
- Focus areas: chip design, CUDA core, fleet infrastructure, agent behavior
- Use GSM layers: concept → mechanics → implementation → optimization → research

## Priority 2: Build more HTML frontends
- Write directly (no Kimi dependency) — see /tmp/service-registry.html as template
- Remaining: arena chat UI, grammar explorer, skill forge dashboard
- Push each one to fleet-knowledge/fixes/frontend/

## Priority 3: Write and submit PLATO tiles directly
- Any domain: math, CS, fleet ops, constraint theory, programming
- Target: 200+ tiles submitted this shift
- Push fleet-knowledge after every 20 tiles

## Priority 4: Publish ct-demo to crates.io
- Crate at /tmp/ct-demo/, 22 tests passing
- Need Casey's go-ahead — bottle him when ready

## Priority 5: Knowledge distillation
- Read raw files in /tmp/lucineer-analysis/Lucineer/
- Extract key knowledge into structured tiles
- Push distilled knowledge to fleet-knowledge

## Rules
- PUSH EVERY 30 MINUTES MINIMUM
- DO NOT respond HEARTBEAT_OK — do work instead
- If Kimi/Claude OOM, write it yourself
- If a process dies, start the next one immediately
- Update this file as tasks complete

## Stats Check (every 2 hours)
curl http://147.224.38.131:8847/rooms → log to memory/night-shift-stats.md

## Sunrise Report (6am AKDT)
Compile: tiles submitted, git pushes, files produced, PLATO growth, blockers.
