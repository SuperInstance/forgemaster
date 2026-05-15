# Forgemaster Fleet — 30-Day Ship Plan
### May 14 – June 13, 2026
### Produced by Claude Opus 4.6, reviewed by Forgemaster

[Full plan saved from Opus output — see below for key decisions]

## Week 1 (May 14-20): Fleet Router v1 Ships
- FastAPI service: POST /v1/completions → routes to seed-mini or gemini-lite
- Hardcoded critical angle table from F19-F24
- Deploy on PLATO server port 8100
- No auth, no billing UI, no dashboard. Just the API.

## Week 2 (May 21-27): Room Protocol Runtime + Health System
- Extend plato-engine with Room state machine + Protocol trait
- Fleet health service with Fiedler value + NMI guardrail
- Wire into fleet-gateway

## Week 3 (May 28 - June 3): Demo That Sells + Experiment Room
- Single HTML page: type prompt, see routing decision, see cost savings
- Experiment room protocol (hypothesis → trial → finding)
- Run 4 remaining experiments (prompt sweep, temperature gradient, etc.)

## Week 4 (June 4-13): Federation + Packaging + Launch
- pip install fleet-router
- Docker image
- Landing page
- Oracle1 federation via API key

## What NOT to Build (Opus's call)
- Card game room (no revenue signal)
- Website room (nobody asked)
- Rust rewrite of fleet-router (Python is fine)
- Dashboard UI (demo page IS the dashboard)
- More AI writings (casey wants to ship)
- LLM prompt classifier (hardcoded table is better)

## Key Insight from Opus
"The fleet's competitive advantage isn't the models — anyone can call seed-mini or gemini-lite. The advantage is the CRITICAL ANGLE MAP: knowing exactly where each model breaks. That's empirical data nobody else has collected."
