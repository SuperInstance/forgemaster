# GUARD Error Messages

GUARD error messages are written for **safety engineers**, not programmers. They cite the standard, explain the physical meaning, and suggest concrete fixes.

## Error Taxonomy

| Code | Phase | Severity | Meaning |
|------|-------|----------|---------|
| `G0xx` | Parse | Fatal | Syntax or structural problem |
| `G1xx` | Type | Fatal | Unit mismatch or domain violation |
| `G2xx` | Static Analysis | Warning | Potential issue, compilation continues |
| `G3xx` | Verification | Fatal | Proof obligation failed |
| `G4xx` | Runtime | Critical | Constraint violated during execution |
| `G5xx` | Certificate | Fatal | Certificate malformed or proof regressed |

---

## Parse Errors (`G0xx`)

### `G001` — Unexpected Token

```
Error G001: I expected a semicolon or the word 'ensure' here,
            but I found 'on_violation' instead.

   --> flight-envelope.guard:42:3
    |
 42 |   on_violation halt
    |   ^^^^^^^^^^^^
    |
    = Hint: An invariant must have the form:
        invariant <name>
          [when <condition>]
          ensure <expression>
          [on_violation <action>];
      Did you forget the word 'ensure' before this condition?
```

### `G002` — Missing Unit

```
Error G002: The state variable 'indicated_airspeed' needs a unit.

   --> flight-envelope.guard:55:3
    |
 55 |   state indicated_airspeed has real
    |        ^^^^^^^^^^^^^^^^^^^
    |
    = Hint: Physical quantities must have units so the compiler can check
      dimensional consistency. Try:
        state indicated_airspeed has real in [0 kt .. 500 kt]
      or:
        state indicated_airspeed has real unit kt;
```

### `G003` — Domain Not Defined

```
Error G003: I don't know what 'AccessMode' means here.

   --> zone-access.guard:38:28
    |
 38 |   array [Zone × Role] of AccessMode
    |                            ^^^^^^^^^^
    |
    = Hint: You can define it with:
        domain AccessMode = { Locked, Unlocked, Escorted };
    = Or import it:
        import SecurityModel.AccessMode;
```

---

## Type Errors (`G1xx`)

### `G101` — Unit Mismatch

```
Error G101: You are comparing apples and oranges — literally.

   --> flight-envelope.guard:78:10
    |
 78 |   ensure indicated_airspeed ≤ Alpha_max
    |          ^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^
    |          Knots                 Degrees
    |
    = Hint: 'indicated_airspeed' is measured in knots (speed).
      'Alpha_max' is measured in degrees (angle).
      These are different physical dimensions and cannot be compared.
    = Suggestion: Did you mean to compare 'angle_of_attack' to 'Alpha_max'?
```

### `G102` — Domain Violation (Static)

```
Error G102: This value can never be reached.

   --> zone-access.guard:45:5
    |
 45 |     (Red, Visitor) → Unlocked,
    |      ^^^^^^^^^^^^^
    |
    = The domain definition for 'auth_matrix' says:
        (Red, Visitor) → Locked
      but you are overriding it to 'Unlocked'.
    = Safety impact: A visitor would be granted unsupervised access
      to the Red radiation zone. This violates ALARA principle.
    = Suggestion: Change to 'Locked' or escalate to the RSO.
```

### `G103` — Temporal Operator on Non-Temporal State

```
Error G103: 'rate_of' can only be applied to continuously sampled state.

   --> flight-envelope.guard:112:18
    |
112 |   ensure |rate_of flap_setting| ≤ 2 °/s
    |                  ^^^^^^^^^^^^
    |
    = 'flap_setting' is sampled every 100 ms and has discrete values
      {Clean, Takeoff, Landing}. Its rate is undefined.
    = Suggestion: Remove 'rate_of', or model flap transition as a
      continuous proxy variable (e.g., flap_extension_degrees).
```

---

## Static Analysis Warnings (`G2xx`)

### `G201` — Unreachable Invariant

```
Warning G201: This invariant can never trigger.

   --> throttle.guard:18:1
    |
 18 | invariant ThrottleMustNotReverse
    |
    = The 'when' clause is 'throttle_command < 0 %', but the state
      declaration says throttle_command is in [0 % .. 100 %].
    = The compiler can prove this condition is always false.
    = Suggestion: Remove the invariant, or widen the state domain if
      the sensor can legitimately report negative values (sensor fault).
```

### `G202` — Overlapping Authority

```
Warning G202: Two invariants may demand contradictory actions.

   --> flight-envelope.guard:88:1 and 95:1
    |
 88 | invariant AlphaFloorProtection ... on_violation transition Protection;
 95 | invariant AlphaHardLimit       ... on_violation halt;
    |
    = At angle_of_attack = 15.4 °, both invariants are active.
      One demands 'transition Protection', the other demands 'halt'.
    = Safety impact: The FCC may receive conflicting commands.
    = Suggestion: Use a priority table or merge into a single
      envelope-limit invariant with a unified recovery action.
```

### `G203` — Zeno Risk (Too-Fast Sampling)

```
Warning G203: The sample rate may exceed the actuator bandwidth.

   --> flight-envelope.guard:102:3
    |
102 |   sampled every 1 ms
    |
    = You are sampling at 1 kHz, but the elevator hydraulic servo
      has a 40 Hz bandwidth (25 ms rise time).
    = Risk: High-frequency noise may alias into the control loop.
    = Suggestion: Increase sample period to ≤ 20 ms, or add an
      anti-aliasing filter before the constraint check.
```

---

## Verification Errors (`G3xx`)

### `G301` — Invariant Violated (Proof Failure)

```
Error G301: The safety invariant 'StallWarningMargin' does NOT always hold.

   --> flight-envelope.guard:72:1
    |
 72 | invariant StallWarningMargin
    |
    = The solver found a reachable state where the property fails.

    Counterexample:
      indicated_airspeed = 82.3 kt
      V_stall_current    = 85.0 kt
      flap_setting       = Takeoff
      flight_phase       = Approach

    = At this point, airspeed is below 1.05 × V_stall (89.25 kt).
      The aircraft is in a stall precursor condition during approach.
    = Safety impact: Autothrust alpha-floor may not have enough
      authority to recover before ground contact.
    = Suggestions:
        1. Raise the minimum approach speed in the FMS.
        2. Increase the stall margin factor from 1.05 to 1.10.
        3. Add a temporal guard: 'for 2 s' before triggering violation.
```

### `G302` — Derived Rule Not Entailed

```
Error G302: The derived rule 'PositiveThrottleImpliesEngineEnabled'
            is not a logical consequence of its premises.

   --> throttle.guard:24:1
    |
 24 | derive PositiveThrottleImpliesEngineEnabled
    |
    = Premises:
        - ThrottleMustNotExceedMax (throttle ≤ 100 %)
        - ThrottleMustNotReverse   (throttle ≥ 0 %)
    = Claimed conclusion:
        throttle > 0 % implies engine_enabled = true
    = Counterexample:
        throttle_command = 50 %
        engine_enabled   = false
    = Explanation: The premises only constrain the *range* of the
      throttle command. They say nothing about the engine state.
      A failed ignition or FADEC shutdown could set engine_enabled
      to false while the throttle lever is at 50 %.
    = Suggestion: Add an additional premise that links throttle
      authority to engine state, or change to an invariant.
```

### `G303` — Solver Timeout

```
Error G303: The proof engine could not verify 'FlightEnvelopeProof'
            within the allotted time (300 s).

   --> flight-envelope.guard:145:1
    |
145 | proof FlightEnvelopeProof { ... }
    |
    = This usually means the state space is too large or the
      temporal horizon is too deep for the chosen tactic.
    = Current tactic: k_induction 5
    = Suggestions:
        1. Reduce 'k' (e.g., k_induction 3).
        2. Add lemma 'RateLimitBounds' to strengthen the inductive step.
        3. Use 'bounded_model_check 50 steps' instead of k-induction.
        4. Increase timeout: proof { tactic k_induction 5 timeout 600 s; }
```

---

## Runtime Errors (`G4xx`)

### `G401` — Constraint Violation at Runtime

```
CRITICAL G401: Safety invariant VIOLATED during flight.

  Invariant:  AlphaHardLimit
  Location:   flight-envelope.guard:95:3
  Priority:   critical
  Time:       T+8473.21 s (since boot)
  Step:       423,661

  Observed values:
    angle_of_attack = 16.2 °
    Alpha_max       = 15.5 °
    exceedance      = +0.7 °

  Aircraft state at violation:
    indicated_airspeed  = 142 kt
    altitude            = 1,240 ft
    flight_phase        = Approach
    stick_pitch_cmd     = +78 % (nose-up)

  Immediate action taken:  HALT (flight control revert to direct law)

  Post-flight: Extract execution trace from FCC NVM and attach
               to incident report. Trace digest: sha256:9a4f2c...
```

### `G402` — Sensor Fault Detected

```
CRITICAL G402: State variable out of declared domain.

  Variable:   indicated_airspeed
  Declared:   [0 kt .. 500 kt]
  Observed:   -12.4 kt
  Time:       T+192.05 s

  Probable cause: Pitot-static probe icing or ADC fault.
  Action:         Reject value, latch last-good, annunciate ADC FAIL.
```

---

## Certificate Errors (`G5xx`)

### `G501` — Proof Regression

```
Error G501: The certificate no longer matches the source.

  Expected source hash:  sha256:9f86d081...
  Actual source hash:    sha256:a3f5c112...

  = Someone modified the source after the certificate was generated.
  = Action: Re-run 'guardc --prove' and re-submit to the verifier.
```

### `G502` — Merkle Root Mismatch

```
Error G502: The proof certificate has been tampered with.

  Certificate:  FlightEnvelopeProof.guardcert
  Claimed root: sha256:e3b0c442...
  Computed root: sha256:7d8a9f1...

  = One or more obligation traces were altered after generation.
  = Action: Treat this certificate as INVALID. Do not deploy.
```
