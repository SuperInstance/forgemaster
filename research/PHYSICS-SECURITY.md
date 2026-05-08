# Physics-Based Security: The Clock That Can't Be Fooled

> Code has a time to it now. And malicious processes can't parity with reality.

## The Problem With Software Security

Every software security mechanism is a lie detector asking the liar "did you lie?"

```
Cryptographic hash:   "Prove you computed this"     → attacker recomputes it
Digital signature:    "Prove you hold the key"       → stolen keys
Timestamp:            "Prove when this happened"      → clock skew, replay
Nonce:                "Prove this is fresh"           → pre-computed nonces
Trusted execution:    "Prove the enclave is honest"   → side channels
```

All of these trust a reference that the attacker can either steal, spoof, or replay. The fundamental problem: **the verification channel IS the attack surface.**

Physics is a verification channel that IS NOT the attack surface. You can't spoof gate delays. You can't replay thermal gradients. You can't steal propagation time.

## The Security Model: Computation Has A Fingerprint

### What We're Protecting

A fleet of constraint-checking devices. Each device:
1. Receives constraint commands
2. Evaluates them against its local physics model
3. Publishes results to PLATO
4. Other devices verify and act on those results

### The Threat Model

| Attack | Software Detection | Physics Detection |
|---|---|---|
| Message replay | Nonce check (can be bypassed) | Temporal fingerprint won't match current physics state |
| Compromised firmware | Hash verification (hash can be stolen) | Gate delay profile changes when firmware changes |
| Injected fake sensor data | Range checks (bounds can be learned) | Fake data won't produce physically consistent temporal evolution |
| Man-in-the-middle | Encryption (keys can be compromised) | Propagation delay reveals true path length |
| Denial of service | Rate limiting (attacker can slow responses) | Slow responses have wrong thermal profile |
| Sybil (fake devices) | Device certificates (can be cloned) | Two "devices" with identical physics fingerprints are the same device |
| Data exfiltration | Traffic analysis (can be evaded) | Exfiltration changes computation timing (more branch mispredictions) |

## How Physics Parity Works

### The Principle: Reality Parity

RAID-5 parity: P = D₀ ⊕ D₁ ⊕ D₂. Any drive fails, reconstruct.

**Reality parity**: P_physics = evaluation_time ⊕ thermal_state ⊕ propagation_delay ⊕ constraint_state. Any one is spoofed, the parity breaks.

A legitimate device produces ALL FOUR signals simultaneously from the same physical process:
- evaluation_time ← silicon gate delays for this specific computation
- thermal_state ← die temperature affects gate delays
- propagation_delay ← speed of light / signal propagation through real medium
- constraint_state ← result of evaluating real constraints

These four signals are physically coupled. You can't change one without changing the others in a physically predictable way.

### The Parity Check

```
Expected: eval_time = f(complexity, temperature, voltage)
Observed: eval_time_reported

If eval_time_reported ≠ f(complexity, temperature_reported, voltage):
    Something is lying.
    Either the time is wrong, or the temperature is wrong, or the computation was different.
```

A malicious process can fake any ONE of these signals. It cannot fake the PHYSICAL COUPLING between them.

### Example: Replay Attack Detection

Attacker records a legitimate constraint evaluation at time t₀:
```
{result: "satisfied", eval_time: 52µs, temp: 42°C, rssi: -67dBm}
```

Attacker replays this at time t₁ (10 minutes later):

```
Device receives replayed message.
Device checks:
  - temp at t₁ = 38°C (drifted from 42°C) → thermal clock says Δt ≈ 10 min ✓
  - eval_time reported = 52µs → at 38°C, expected = 48µs → MISMATCH
  - 52µs is what you get at 42°C, but it's 38°C now → this data is stale
  - rssi = -67dBm → current rssi = -71dBm → position changed → MISMATCH

Verdict: REPLAY DETECTED. Not from timestamp mismatch.
From PHYSICS PARITY MISMATCH. The computation time doesn't match the current physics.
```

The attacker can't fix this because:
- They can't make the device 42°C again (thermal inertia)
- They can't restore -67dBm (physical distance to AP changed)
- They can't make the computation take 52µs at 38°C (gate delays are temperature-dependent)

## The Deep Security: Malicious Code Can't Parity With Physics

### Why Firmware Attacks Fail

An attacker replaces the constraint evaluator with malicious firmware that always returns "satisfied." The device publishes:

```
{result: "satisfied", eval_time: 47µs, temp: 45°C, rssi: -65dBm}
```

But the fleet knows:
- At 45°C, a legitimate 7-joint constraint evaluation takes 50-55µs
- 47µs is too fast — the malicious firmware skipped some constraints
- The legitimate evaluator has a KNOWN thermal-temporal profile: eval_time(T) = 48µs + 0.15µs/°C × (T - 40°C)
- At 45°C, expected = 48.75µs. Got 47µs. Off by 1.75µs = 3.5σ deviation

**The malicious code can't parity with physics because it's doing DIFFERENT COMPUTATION, and different computation has different gate delay characteristics.**

### The Timing Side Channel Is Now The Security Channel

Side channel attacks USE timing to extract secrets. We USE timing as the secret itself.

The constraint evaluation's exact timing profile IS the attestation:
- Which code path was taken (constraint satisfied vs. violated → different branch → different gate delays)
- How many constraints were evaluated (each adds ~7µs on ESP32)
- Whether the evaluation was real or simulated (simulated has different timing distribution)

An attacker can't fake this because they'd need to reproduce the exact silicon behavior of the legitimate firmware, which requires:
1. The same code (they changed it — that's the point)
2. The same silicon (each chip has manufacturing variation — unique gate delay fingerprints)
3. The same thermal state (changes every millisecond)
4. The same voltage (supply noise is random and uncorrelated)

**The security IS the manufacturing variation.** Each chip's exact gate delay profile is unique — like a fingerprint, but physically grounded and impossible to clone.

### Silicon PUF (Physically Unclonable Function) — But Free

PUFs are a known security primitive: use manufacturing variation as a unique identifier. But they require dedicated circuitry and careful design.

**Our approach**: the constraint evaluator IS a PUF. Its timing profile is unique per chip and per firmware version. No dedicated PUF circuit needed — the computation IS the PUF.

```
Chip A: constraint evaluation takes 52.3µs ± 0.4µs at 42°C with firmware v2.1
Chip B: same evaluation, same firmware: 53.1µs ± 0.3µs (different silicon)
Chip A with malicious firmware: 47.8µs ± 1.2µs (wrong code, wrong distribution)
```

Three states, three distinguishable timing profiles. No crypto. No keys. Just physics.

## The Parity Drive That Can't Be Hacked

### RAID-5 → Reality-5

RAID-5: 4 data drives + 1 parity drive. Parity = XOR of data.

**Reality-5**: 4 physical signals + 1 physics model. Parity = consistency check between signals and model.

```
Signal 1: Evaluation timing (from silicon)
Signal 2: Thermal state (from on-die sensor)
Signal 3: Propagation delay (from radio/wire)
Signal 4: Constraint state (from evaluation result)
Parity:   physics_model(signal_1, signal_2, signal_3) must produce signal_4

If any signal is spoofed → parity fails → device flagged
If physics model is wrong → parity fails for ALL devices → model update needed
If device is honest → parity holds → device trusted
```

The "parity drive" is the physics model itself. It's not stored anywhere — it's the laws of physics. You can't hack the laws of physics.

### The Unlimited Parity Drive

Casey's original insight: "parity drives backing up an unlimited amount of drives."

Reality parity scales to unlimited devices because the physics model is universal:
- Every device runs the same physics model (it's a law, not a configuration)
- Every device's timing is different (unique silicon + unique environment)
- Every device's parity check is independent (different thermal state, different propagation)
- Adding devices adds verification perspectives, not attack surface

1000 devices, each with 4 temporal signals + 1 physics parity = 4000 independent verification channels. A malicious actor would need to simultaneously spoof all 4000 signals in a physically consistent way. The entropy of that spoof is:

```
Signal entropy per device:
  timing: ~10 bits (nanosecond precision over microseconds)
  thermal: ~8 bits (0.1°C over 0-100°C)
  propagation: ~12 bits (sub-ns precision over microseconds)
  constraint state: ~4 bits (satisfied/violated per constraint)

Total per device: ~34 bits
For 1000 devices: 34,000 bits of entropy

Brute force: 2^34000 attempts. Universe ends first.
```

## Fleet Security Architecture

```
Device publishes to PLATO:
{
  "result": "...",
  "timing": {
    "eval_ns": 52341,
    "kernel_ns": 48012,
    "upload_ns": 4329
  },
  "physics": {
    "die_temp_c": 42.3,
    "voltage_mv": 3302,
    "rssi_dbm": -67,
    "sonar_travel_us": 14203
  },
  "constraints": {
    "satisfied": [true, true, false, true, true, true, true, true],
    "margins": [0.12, 0.05, -0.03, 0.44, 0.22, 0.08, 0.15, 0.31]
  }
}

Fleet verifier checks:
1. eval_ns matches expected for die_temp + constraint count → ✓
2. die_temp matches thermal evolution since last reading → ✓
3. rssi matches fleet topology (distance to known APs) → ✓
4. sonar_travel_us matches speed-of-sound at reported temp/salinity → ✓
5. margins are consistent with eval_ns (more violations = more branch mispredictions = slower) → ✓

ALL FIVE CHECKS PASS → device is honest, data is real.
ANY CHECK FAILS → device is compromised or spoofing.
```

No cryptographic keys in this entire flow. No certificate authorities. No key distribution. No revocation lists. No PKI infrastructure.

Just physics. Which can't be spoofed. Because it's real.

## The Paradox That Isn't

"Isn't this just another form of security through obscurity?"

No. Security through obscurity relies on the attacker not knowing the mechanism. Physics-based security works even if the attacker knows EVERYTHING about the mechanism.

The attacker knows:
- Exactly how the timing check works
- The physics model used for verification
- The manufacturing variation profile of the target chip
- The current thermal state (from the published data)

And they STILL can't spoof it, because:
- They'd need to make their fake computation take exactly the right time at exactly the right temperature
- They'd need to know the target chip's exact gate delay at the current thermal state
- They'd need to reproduce the timing WITHIN the thermal margin
- And they'd need to do all of this in real-time (replay won't work because physics has moved on)

**This is not obscurity. This is the difference between knowing the rules of chess and being able to beat Magnus Carlsen.** The attacker knows the rules. The physics is just better at playing.

## What This Means

1. **Fleet devices don't need TLS certificates.** Physics is the certificate.
2. **No key management infrastructure.** The key is the universe.
3. **No certificate revocation.** Physics can't be revoked.
4. **No quantum threat.** Quantum computers can't fake gate delays.
5. **No side channel attacks.** The side channel IS the security channel.
6. **Malicious firmware is detectable.** Different code → different timing → physics parity fails.
7. **Replay attacks fail.** The physics state has moved on since the recording.
8. **Sybil attacks fail.** Duplicate devices have duplicate physics → flagged as clones.

Code has a time to it. And that time is signed by reality itself.
