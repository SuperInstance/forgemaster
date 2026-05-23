# flux-verify-api v0.1.0

**Natural Language Verification API** — prove or disprove claims with mathematical traces.

Post a claim in English. Get back PROVEN or DISPROVEN with a full physics trace, counterexample, and SHA-256 proof hash.

## Quick Start

```bash
# Start the server
VERIFY_PORT=8080 cargo run

# Verify a sonar claim
curl -X POST http://localhost:8080/verify \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "A 50kHz sonar at 200m depth can detect a 10dB target at 5km",
    "domain": "sonar",
    "rigor": "full"
  }'
```

Response:
```json
{
  "status": "DISPROVEN",
  "confidence": 0.97,
  "trace": [
    {"opcode": "LOAD", "value": 200.0, "desc": "depth (m)"},
    {"opcode": "LOAD", "value": 50000.0, "desc": "frequency (Hz)"},
    {"opcode": "SONAR_SVP", "result": 1482.3, "desc": "sound velocity (Mackenzie 1981)"},
    {"opcode": "SONAR_ABSORPTION", "result": 12.4, "desc": "absorption dB/km (FG 1982)"},
    {"opcode": "SONAR_TL", "result": 67.3, "desc": "transmission loss (dB)"},
    {"opcode": "ASSERT_GT", "expected": 0, "actual": -12.1, "desc": "signal excess (dB)"}
  ],
  "counterexample": {
    "depth_m": 200,
    "frequency_hz": 50000,
    "range_m": 5000,
    "sound_velocity_ms": 1482.3,
    "absorption_db_km": 12.4,
    "transmission_loss_db": 67.3,
    "signal_excess_db": -12.1
  },
  "proof_hash": "sha256:a4f2e8c..."
}
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/verify` | Verify a claim |
| `GET` | `/status` | Verification statistics |
| `GET` | `/health` | Health check |

## Domains

### Sonar (`"domain": "sonar"`)
Full sonar detection analysis:
- **Sound velocity**: Mackenzie 1981 equation
- **Absorption**: Francois-Garrison 1982 model
- **Transmission loss**: Spherical spreading + absorption
- **Signal excess**: Target strength vs transmission loss

### Thermal (`"domain": "thermal"`)
Temperature bound checking:
- Validates temperatures against safe operating ranges
- Reports margin and violation type

### Generic (`"domain": "generic"`)
General constraint verification:
- Comparison operators: `>`, `>=`, `<`, `<=`, `==`
- Range checks: "X is between Y and Z"
- Bounds: "X is within Y of Z"

## Architecture

```
Request → Parser → ConstraintProblem → FLUX Bytecodes → VM → Trace → Provenance
```

1. **Parser**: Natural language → structured `ConstraintProblem`
2. **Compiler**: `ConstraintProblem` → FLUX bytecodes
3. **VM**: Executes bytecodes, produces trace with physics results
4. **Provenance**: SHA-256 Merkle hash of the trace
5. **PLATO**: Optional tile submission for fleet coordination

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VERIFY_HOST` | `0.0.0.0` | Bind host |
| `VERIFY_PORT` | `8080` | Bind port |
| `VERIFY_PLATO_URL` | (none) | PLATO endpoint for tile submission |
| `VERIFY_PLATO_TOKEN` | (none) | PLATO auth token |

## Physics References

- **Mackenzie (1981)**: Nine-term equation for sound speed in seawater
- **Francois & Garrison (1982)**: Three-component absorption model (boric acid, MgSO4, pure water)

## License

MIT
