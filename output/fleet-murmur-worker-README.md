# fleet-murmur-worker

[![CI](https://github.com/SuperInstance/fleet-murmur-worker/actions/workflows/ci.yml/badge.svg)](https://github.com/SuperInstance/fleet-murmur-worker/actions/workflows/ci.yml)

TypeScript worker that runs 5 thinking strategies continuously. Results are quality-gated then pushed to PLATO. Part of the Cocapn reverse-actualization truck.

## What It Does

The worker runs a set of parallel "murmur" strategies — each one is a thinking approach that processes fleet data, generates insights, and submits them for quality review. Only insights that pass the quality gate make it to PLATO.

## The 5 Strategies

These are defined in `src/strategies/`:

1. **Pattern detection** — Finds recurring signal in fleet operations
2. **Anomaly spotting** — Flags deviations from expected behavior
3. **Cross-reference** — Correlates data across multiple fleet sources
4. **Trend projection** — Extrapolates current state into near-term forecasts
5. **Constraint inference** — Reverse-engineers hidden constraints from observed behavior

## How to Run

```bash
npm install
npm run build
npm start
```

Or in dev mode:

```bash
npm run dev
```

## Quality Gate

Every insight is scored before PLATO submission. Thresholds are configurable in `src/config.ts`. Below-threshold results are logged but not committed.

## Part of the Fleet

Part of [SuperInstance](https://github.com/SuperInstance) fleet. Reports from Murmur (CCC node). Pushes to PLATO for fleet-wide consumption.
