# GUARD DSL — Complete Design Document

**Version:** 1.0.0
**Date:** 2026-05-03
**Status:** Specification Complete — Ready for Compiler Implementation
**Compliance Targets:** DO-178C / DO-333, IEC 61508, ISO 26262, IEC 62304
**Target Runtime:** FLUX 43-opcode Stack VM → FPGA Hard Enforcement

---

## Table of Contents

1. [Language Philosophy](#1-language-philosophy)
2. [Complete Grammar (EBNF)](#2-complete-grammar-ebnf)
3. [Three Examples of Increasing Complexity](#3-three-examples-of-increasing-complexity)
4. [Type System](#4-type-system)
5. [Compilation to FLUX Bytecode](#5-compilation-to-flux-bytecode)
6. [Error Messages for Safety Engineers](#6-error-messages-for-safety-engineers)
7. [Comparison to Related Work](#7-comparison-to-related-work)
8. [Proof Certificates](#8-proof-certificates)

---

## 1. Language Philosophy

### Who Writes GUARD

GUARD is written by **safety engineers** — the people who read fault-tree analyses, write hazard severity assessments, and sign off on system-level requirements. They understand:

- What a stall speed is and why it depends on flap configuration.
- Why a visitor cannot enter a radiation zone unescorted.
- Why a throttle command must never go negative.

They do not necessarily understand:
- Monadic temporal logic in Coq.
- SMT solver option tuning.
- Fixed-point arithmetic overflow in C.

GUARD is designed so that the *first group* can write it and the *second group* can verify it, without requiring the same person to be both.

### The Core Tension GUARD Resolves

Safety constraints live in three places today, and they drift apart:

1. **The Word document** — what the engineer wrote.
2. **The Simulink model** — what the control engineer implemented.
3. **The C code** — what the compiler actually runs on hardware.

When these three disagree, someone dies. GUARD collapses all three into **one artifact**: a `.guard` file that *is* the requirement, *compiles* to bytecode, and *ships* with a machine-checkable proof that the bytecode satisfies the requirement.

### Design Principles

**P1 — Readability over terseness.**
A safety engineer should read a GUARD file without training. Compare:

```guard
// GUARD (readable)
invariant ThrottleMustNotExceedMax
  critical
  ensure throttle_command ≤ 100 %
  on_violation halt;
```

```lustre
// Lustre (opaque to non-engineers)
node throttle_check(cmd: real) returns (ok: bool);
let ok = cmd <= 1.0 tel;
```

GUARD's names, units, and violation actions are self-documenting.

**P2 — Units are semantic, not cosmetic.**
`100` is ambiguous. `100 %` is a throttle limit. `100 kt` is an airspeed. `100 ft` is an altitude. These cannot be compared — and the compiler enforces that. The Mars Climate Orbiter was lost to a unit mismatch in 1999. GUARD prevents it at compile time.

**P3 — Temporal logic is explicit.**
Safety requirements routinely involve time: "for 3 seconds after rotation", "must respond within 500 ms", "rate must not exceed 1.5 g per second". GUARD makes these first-class operators, not library calls or comment annotations.

**P4 — One source of truth.**
The `.guard` file is the requirement. The bytecode is derived from it. The proof certificate attests that the derivation is correct. There is no separate document that the compiler doesn't know about.

**P5 — Trust the proof, not the compiler.**
The compiler can have bugs. The proof certificate cannot lie — it is checked by an independent verifier with a Trusted Computing Base of under 1,000 lines of Rust. A safety auditor can verify every obligation without trusting the compiler.

**P6 — Graceful degradation under verification limits.**
Not every property can be fully verified automatically. GUARD distinguishes:
- **Proved** — the SMT solver found a complete proof.
- **Bounded** — bounded model checking found no counterexample up to N steps.
- **Runtime** — no static proof is possible; the bytecode enforces the constraint at runtime and will halt on violation.

This distinction appears explicitly in the proof certificate so auditors know exactly what was and was not verified statically.

**P7 — Safety impact before fix suggestion.**
Error messages explain *why* something matters before suggesting how to fix it. An engineer who understands the safety implication can make a better judgment than one who just copies the compiler's suggestion.

---

## 2. Complete Grammar (EBNF)

This is the normative grammar. The compiler's PEG parser is derived directly from this specification.

```ebnf
(* ======================================================================== *)
(*  GUARD DSL — Formal Grammar (Extended BNF)                               *)
(*  Version: 1.0.0                                                          *)
(* ======================================================================== *)

(* --- Lexical ------------------------------------------------------------ *)

letter        ::= "a"..."z" | "A"..."Z" ;
digit         ::= "0"..."9" ;
underscore    ::= "_" ;
prime         ::= "'" ;

identifier    ::= letter { letter | digit | underscore } [ prime ] ;
qualified_id  ::= identifier { "." identifier } ;

(* Numbers with mandatory units for physical quantities. *)
decimal       ::= digit { digit } [ "." digit { digit } ] ;
scientific    ::= decimal ( "e" | "E" ) [ "+" | "-" ] digit { digit } ;
number        ::= decimal | scientific ;

(* Units are not comments. They are semantic tokens. *)
unit          ::= identifier | "%" | "°" | "°C" | "°F" | "°/s" ;
quantity      ::= number unit ;

string        ::= '"' { character } '"' ;
comment       ::= "//" { character } newline
                | "/*" { character } "*/" ;

(* --- Document Structure ------------------------------------------------- *)

module        ::= header import* unit_decl* domain_decl* state_decl*
                  invariant_decl* derive_decl* proof_decl* ;

header        ::= "module" identifier [ version ] [ "for" system_desc ] ";" ;
version       ::= "version" string ;
system_desc   ::= string ;

import        ::= "import" qualified_id [ "as" identifier ] ";" ;

(* --- Unit Declarations -------------------------------------------------- *)

unit_decl     ::= "dimension" identifier "is" unit_expr [ unit_range ] ";" ;
unit_expr     ::= identifier
                | unit_expr "*" unit_expr
                | unit_expr "/" unit_expr ;
unit_range    ::= "from" quantity "to" quantity ;

(* --- Domain Declarations ------------------------------------------------ *)
(*  A domain is a named set of values: enums, intervals, or products.      *)

domain_decl   ::= "domain" identifier "=" domain_body ";" ;
domain_body   ::= enum_domain | interval_domain | product_domain ;
enum_domain   ::= "{" identifier { "," identifier } "}" ;
interval_domain
              ::= "[" quantity ".." quantity "]" ;
product_domain
              ::= "(" domain_body { "×" domain_body } ")" ;

(* --- State Declarations ------------------------------------------------- *)
(*  Variables observable in the system. Each has a type, unit, and domain. *)

state_decl    ::= "state" identifier "has" type_desc
                  [ "in" domain_ref ]
                  [ "initially" expr ]
                  [ "sampled" "every" quantity ]
                  ";" ;
type_desc     ::= scalar_type | array_type | record_type ;
scalar_type   ::= "real" | "integer" | "boolean" | "enum" domain_ref ;
array_type    ::= "array" "[" quantity ".." quantity "]" "of" type_desc ;
record_type   ::= "record" "{" field { "," field } "}" ;
field         ::= identifier "has" type_desc [ "in" domain_ref ] ;
domain_ref    ::= qualified_id | interval_domain | enum_domain ;

(* --- Expressions -------------------------------------------------------- *)

expr          ::= logical_expr ;
logical_expr  ::= temporal_expr
                | logical_expr "implies" temporal_expr
                | logical_expr "iff"     temporal_expr
                | logical_expr "and"     temporal_expr
                | logical_expr "or"      temporal_expr
                | "not" temporal_expr ;

temporal_expr ::= comparison_expr
                | "always"     comparison_expr
                | "eventually" comparison_expr
                | "next"       comparison_expr
                | comparison_expr "until" comparison_expr
                | comparison_expr "since" comparison_expr
                | "for"   quantity comparison_expr
                | "after" quantity comparison_expr ;

comparison_expr
              ::= additive_expr
                | additive_expr "="  additive_expr
                | additive_expr "≠"  additive_expr
                | additive_expr "<"  additive_expr
                | additive_expr ">"  additive_expr
                | additive_expr "≤"  additive_expr
                | additive_expr "≥"  additive_expr
                | additive_expr "in" domain_ref ;

additive_expr ::= multiplicative_expr
                | additive_expr "+" multiplicative_expr
                | additive_expr "-" multiplicative_expr ;

multiplicative_expr
              ::= unary_expr
                | multiplicative_expr "*"   unary_expr
                | multiplicative_expr "/"   unary_expr
                | multiplicative_expr "mod" unary_expr ;

unary_expr    ::= primary
                | "-" unary_expr
                | "|" unary_expr "|"      (* absolute value *)
                | "old"     unary_expr    (* previous time-step value *)
                | "rate_of" unary_expr    (* derivative, per sample period *)
                | "delta"   unary_expr ;  (* x - old x *)

primary       ::= identifier
                | qualified_id
                | quantity
                | "true" | "false"
                | "(" expr ")"
                | identifier "(" expr { "," expr } ")"   (* function call *)
                | identifier "[" expr "]"                (* array access *)
                | identifier "." identifier              (* field access *)
                | "if" expr "then" expr "else" expr ;    (* conditional *)

(* --- Invariant Declarations --------------------------------------------- *)
(*  Core constraints that must hold. Each is a named safety requirement.   *)

invariant_decl
              ::= "invariant" identifier [ priority ] [ "when" expr ]
                  "ensure"      expr
                  [ "on_violation" violation_action ]
                  ";" ;

priority      ::= "critical" | "major" | "minor" ;
violation_action
              ::= "halt"
                | "warn"
                | "log"
                | "transition" identifier ;

(* --- Derive Declarations ------------------------------------------------ *)
(*  Derived rules: consequences that follow from invariants and state.     *)

derive_decl   ::= "derive" identifier "from" premise_list
                  [ "when" expr ]
                  "conclude" expr
                  [ "proof_obligation" expr ]
                  ";" ;

premise_list  ::= premise { "," premise } ;
premise       ::= identifier | expr ;

(* --- Proof Declarations ------------------------------------------------- *)
(*  Explicit proof hints, abstractions, and certificate tuning.            *)

proof_decl    ::= "proof" identifier "{" proof_body "}" ;
proof_body    ::= { proof_step } ;
proof_step    ::= "tactic"      identifier ";"
                | "lemma"       identifier "=" expr ";"
                | "reduce"      "to" identifier ";"
                | "certificate" "{" cert_config "}" ;

cert_config   ::= "format"               "=" ( "smt2" | "lfsc" | "native" ) ";"
                | "include_trace"        "=" boolean ";"
                | "include_counterexample" "=" boolean ";"
                | "hash"                 "=" ( "sha256" | "blake3" ) ";" ;

boolean       ::= "true" | "false" ;

(* --- N-ary Constraint Sugar --------------------------------------------- *)
(*  These are syntactic sugar; they desugar during lowering.               *)

all_distinct  ::= "all_distinct" "(" expr { "," expr } ")" ;
all_equal     ::= "all_equal"    "(" expr { "," expr } ")" ;
monotone      ::= "monotone"     "(" expr [ "ascending" | "descending" ] ")" ;
table_constraint
              ::= "table" identifier "[" expr "]" "must_be" expr ;
```

### Operator Precedence (tightest to loosest)

| Level | Operators |
|-------|-----------|
| 1 (tightest) | `old`, `rate_of`, `delta`, unary `-`, `\|…\|` |
| 2 | `*`, `/`, `mod` |
| 3 | `+`, `-` |
| 4 | `=`, `≠`, `<`, `>`, `≤`, `≥`, `in` |
| 5 | `always`, `eventually`, `next`, `for`, `after` |
| 6 | `until`, `since` |
| 7 | `not` |
| 8 | `and` |
| 9 | `or` |
| 10 (loosest) | `implies`, `iff` |

---

## 3. Three Examples of Increasing Complexity

### 3a. Simple — Throttle Limit

**Context:** An Engine Control Unit (ECU) must enforce that a throttle command stays within physical bounds. If it ever exceeds 100 % or goes below 0 %, the ECU halts.

```guard
// ========================================================================
//  Example (a) — Simple Throttle Limit
//  System: Engine Control Unit (ECU)
//  Standard: DO-178C Level A
// ========================================================================

module ThrottleLimit
  version "1.0.0"
  for "ECU-320 Throttle Body Authority"
;

// Physical dimensions used in this module
dimension Percent is real % from 0 % to 100 %;

// The only observable we care about
state throttle_command has real in [0 % .. 100 %]
  sampled every 10 ms;

// Hard limits — on violation, halt immediately
invariant ThrottleMustNotExceedMax
  critical
  ensure throttle_command ≤ 100 %
  on_violation halt;

invariant ThrottleMustNotReverse
  critical
  ensure throttle_command ≥ 0 %
  on_violation halt;

// Derived: any positive command implies the engine is enabled.
// This is a proof obligation, not a runtime check.
derive PositiveThrottleImpliesEngineEnabled
  from ThrottleMustNotExceedMax, ThrottleMustNotReverse
  when throttle_command > 0 %
  conclude engine_enabled = true;

// Proof configuration
proof ThrottleSafetyProof {
  tactic interval_arithmetic;
  tactic bit_blast;
  certificate {
    format = native;
    include_trace = true;
    hash = sha256;
  }
}
```

**What this demonstrates:**
- `dimension` declaration for physical units.
- `state` with a sampled variable and declared domain.
- Two `invariant` declarations with `critical` priority and `halt` action.
- A `derive` rule that creates a proof obligation without runtime overhead.
- A `proof` block selecting tactics and certificate format.

---

### 3b. Medium — Zone Access Control with Authorization Matrix

**Context:** A radiation therapy bunker has four access zones (Red = highest dose, Green = public). Personnel have roles. The authorization matrix specifies who may enter each zone unescorted, escorted, or not at all. This must be enforced in real time against badge scans.

```guard
// ========================================================================
//  Example (b) — Zone Access Control
//  System: Radiation Bunker Personnel Safety Interlock
//  Standard: IEC 62304 Class C / IEC 61508 SIL 3
// ========================================================================

module ZoneAccessControl
  version "2.1.0"
  for "Radiation Bunker Personnel Safety Interlock"
;

import PersonnelDatabase.Person as Person;
import PersonnelDatabase.Role   as Role;

// Discrete domains
domain Zone       = { Red, Orange, Yellow, Green };
domain AccessMode = { Locked, Unlocked, Escorted };
domain Role       = { Physician, Physicist, Therapist, Technician, Visitor, None };
domain DoorState  = { Open, Closed, Ajar };

// Authorization matrix: (Zone, Role) → AccessMode
// This is the single source of truth for access policy.
state auth_matrix has
  array [Zone × Role] of AccessMode
  initially {
    (Red,    Physician)  → Unlocked,
    (Red,    Physicist)  → Unlocked,
    (Red,    Therapist)  → Escorted,
    (Red,    Technician) → Locked,
    (Red,    Visitor)    → Locked,
    (Orange, Physician)  → Unlocked,
    (Orange, Physicist)  → Unlocked,
    (Orange, Therapist)  → Unlocked,
    (Orange, Technician) → Escorted,
    (Orange, Visitor)    → Locked,
    (Yellow, Physician)  → Unlocked,
    (Yellow, Physicist)  → Unlocked,
    (Yellow, Therapist)  → Unlocked,
    (Yellow, Technician) → Unlocked,
    (Yellow, Visitor)    → Escorted,
    (Green,  _)          → Unlocked    // wildcard: Green is public
  };

// Dynamic state
state current_zone     has Zone      sampled every 100 ms;
state badge_role       has Role      sampled every 100 ms;
state door_front       has DoorState sampled every 50 ms;
state door_rear        has DoorState sampled every 50 ms;
state beam_armed       has boolean   initially false;
state persons_inside   has
  array [1 .. 20] of record {
    id   has integer,
    role has Role
  }
  initially {};

// --- Invariants ---

// Persons present in Red zone must be physician or physicist.
invariant RedZoneRequiresPhysicistOrPhysician
  critical
  when current_zone = Red
  ensure
    forall p in persons_inside :
      p.role = Physician or p.role = Physicist
  on_violation halt;

// Door must be locked when badge is insufficient for the zone.
invariant DoorLockedWhenUnauthorized
  major
  when auth_matrix[current_zone, badge_role] = Locked
  ensure door_front = Closed and door_rear = Closed
  on_violation halt;

// Escorted access requires a supervisor to be present.
invariant EscortRequiresAuthorizedSupervisor
  major
  when auth_matrix[current_zone, badge_role] = Escorted
  ensure
    exists p in persons_inside :
      auth_matrix[current_zone, p.role] = Unlocked
  on_violation warn;

// Beam cannot be armed unless both doors are fully closed.
invariant BeamArmedRequiresDoorsClosed
  critical
  when beam_armed = true
  ensure door_front = Closed and door_rear = Closed
  on_violation halt;

// --- Derived rules ---

// If beam is armed, we must be in a treatment zone.
derive BeamArmedImpliesTreatmentZone
  from BeamArmedRequiresDoorsClosed
  when beam_armed = true
  conclude current_zone = Orange or current_zone = Red;

// An empty room cannot have the beam armed.
derive EmptyRoomImpliesBeamDisarmed
  from RedZoneRequiresPhysicistOrPhysician
  when |persons_inside| = 0
  conclude beam_armed = false;

proof ZoneAccessProof {
  tactic enumerate_finite_domain;
  tactic bounded_model_check 20 steps;
  certificate {
    format = native;
    include_trace = true;
    include_counterexample = true;
    hash = sha256;
  }
}
```

**What this demonstrates over (a):**
- `domain` enumerations and product domains `[Zone × Role]`.
- 2D array state with record elements.
- Authorization matrix as a typed lookup table with wildcard entries.
- `forall` and `exists` quantification over arrays.
- `when` guard conditions that activate invariants only in relevant states.
- Multiple violation actions (`halt`, `warn`) with appropriate escalation.
- `derive` rules that use the matrix to establish higher-level consequences.

---

### 3c. Complex — Flight Envelope Protection

**Context:** A fly-by-wire flight control computer must protect the aircraft from exceeding its structural and aerodynamic envelope across four dimensions simultaneously: airspeed (both IAS and Mach), angle of attack, normal load factor (g-load), and pitch rate — the last two with temporal rate limits. At high g and high AoA simultaneously, the pitch authority is reduced.

```guard
// ========================================================================
//  Example (c) — Flight Envelope Protection
//  System: Fly-by-Wire Flight Control Computer (FCC)
//  Standard: DO-178C Level A / ARP 4754A
// ========================================================================

module FlightEnvelopeProtection
  version "3.0.2"
  for "FCC Pitch and Airspeed Authority Limits"
;

import AtmosphereModel.density as rho;

// --- Physical dimensions ---
dimension Knots     is real from 0 kt to 500 kt;
dimension Feet      is real from -1000 ft to 55000 ft;
dimension Degrees   is real from -90 ° to 90 °;
dimension DegPerSec is real from -20 °/s to 20 °/s;
dimension GUnits    is real from -3.0 g to 4.5 g;
dimension Kg        is real from 20000 kg to 90000 kg;
dimension Percent   is real % from 0 % to 100 %;

// --- Domains ---
domain FlapSetting    = { Clean, Takeoff, Landing };
domain FlightPhase    = { Ground, TakeoffRoll, Climb, Cruise, Descent, Approach, LandingRoll };
domain EnvelopeRegion = { Normal, Advisory, Caution, Warning, Protection };

// --- Aircraft configuration constants ---
state V_stall_clean   has real in [80 kt .. 120 kt]       initially 102 kt;
state V_stall_takeoff has real in [70 kt .. 110 kt]       initially 85 kt;
state V_stall_landing has real in [65 kt .. 105 kt]       initially 78 kt;
state V_mo            has real in [300 kt .. 400 kt]      initially 340 kt;
state M_mo            has real in [0.70 .. 0.90]          initially 0.82;
state Alt_max         has real in [35000 ft .. 45000 ft]  initially 41000 ft;
state Alpha_max       has real in [12 ° .. 20 °]          initially 15.5 °;
state N_z_max         has real in [2.0 g .. 3.0 g]        initially 2.5 g;
state N_z_min         has real in [-1.5 g .. -0.5 g]      initially -1.0 g;

// --- Dynamic state (sensor inputs) ---
state indicated_airspeed  has real in [0 kt .. 500 kt]      sampled every 20 ms;
state altitude            has real in [-1000 ft .. 55000 ft] sampled every 20 ms;
state angle_of_attack     has real in [-5 ° .. 25 °]         sampled every 10 ms;
state normal_load_factor  has real in [-4.0 g .. 5.0 g]      sampled every 10 ms;
state pitch_rate          has real in [-20 °/s .. 20 °/s]    sampled every 10 ms;
state gross_weight        has real in [20000 kg .. 90000 kg] sampled every 500 ms;
state flap_setting        has FlapSetting                     sampled every 100 ms;
state flight_phase        has FlightPhase                     sampled every 100 ms;
state stick_pitch_cmd     has real in [-100 % .. 100 %]       sampled every 10 ms;
state elevator_deflection has real in [-30 ° .. 20 °]         sampled every 10 ms;

// --- Derived computed values (updated by FCC each cycle) ---
state V_alpha_prot has real in [0 kt .. 500 kt];
state V_alpha_max  has real in [0 kt .. 500 kt];
state V_stall_warn has real in [0 kt .. 500 kt];

// ========================================================================
//  Airspeed Limits
// ========================================================================

// Never exceed Mach number at altitude (Mach trim: 661 kt ≈ speed of sound at FL280).
invariant MachNeverExceed
  critical
  when altitude ≥ 28000 ft
  ensure indicated_airspeed ≤ M_mo * 661 kt
  on_violation transition Protection;

// Never exceed maximum operating indicated airspeed.
invariant VmoNeverExceed
  critical
  ensure indicated_airspeed ≤ V_mo
  on_violation transition Protection;

// Stall warning margin: must stay above 1.05 × V_stall.
invariant StallWarningMargin
  major
  ensure indicated_airspeed ≥ 1.05 * V_stall_current
  on_violation transition Advisory;

// V_stall_current is configuration-dependent.
derive VStallCurrentFromFlaps
  from StallWarningMargin
  conclude V_stall_current =
    if flap_setting = Clean   then V_stall_clean
    else if flap_setting = Takeoff then V_stall_takeoff
    else V_stall_landing;

// ========================================================================
//  Angle of Attack Limits
// ========================================================================

// Alpha floor protection: autothrust must go to TOGA as alpha approaches limit.
invariant AlphaFloorProtection
  critical
  when angle_of_attack ≥ Alpha_max - 1.5 °
  ensure autothrust_mode = TOGA
  on_violation transition Protection;

// Hard alpha limit: structural and aerodynamic absolute maximum.
invariant AlphaHardLimit
  critical
  ensure angle_of_attack ≤ Alpha_max
  on_violation halt;

// ========================================================================
//  Normal Load Factor (g-load) Limits
// ========================================================================

// Positive g-limit (structural).
invariant PositiveGLimit
  critical
  when flight_phase = Climb or flight_phase = Cruise or flight_phase = TakeoffRoll
  ensure normal_load_factor ≤ N_z_max
  on_violation transition Caution;

// Negative g-limit (structural + comfort).
invariant NegativeGLimit
  critical
  ensure normal_load_factor ≥ N_z_min
  on_violation transition Caution;

// ========================================================================
//  Temporal Rate Limits
// ========================================================================

// Pitch rate must not exceed 8 °/s below 1000 ft AGL.
invariant PitchRateLimitLowAltitude
  major
  when altitude ≤ 1000 ft and (flight_phase = Approach or flight_phase = LandingRoll)
  ensure |pitch_rate| ≤ 8 °/s
  on_violation transition Advisory;

// Pitch rate must not exceed 5 °/s for the first 3 seconds after takeoff rotation.
// "for 3 s" means this must hold continuously for 3 whole seconds after the
// takeoff phase begins — not just instantaneously.
invariant PitchRateLimitTakeoff
  critical
  when flight_phase = TakeoffRoll
  ensure
    for 3 s ( |pitch_rate| ≤ 5 °/s )
  on_violation transition Caution;

// Airspeed must not decay faster than 5 kt per second in approach.
invariant AirspeedDecayLimitApproach
  major
  when flight_phase = Approach
  ensure
    always ( delta indicated_airspeed ≥ -5 kt per s )
  on_violation warn;

// Normal load factor rate of change must not exceed 1.5 g per second.
// This limits structural shock loads and passenger injury risk.
invariant GLimitRate
  major
  ensure
    always ( |rate_of normal_load_factor| ≤ 1.5 g per s )
  on_violation transition Advisory;

// ========================================================================
//  Authority Cross-Check (combined-limit protection)
// ========================================================================

// When both g-load and angle of attack are near their limits simultaneously,
// reduce pitch authority to prevent simultaneous hard limit breach.
invariant AuthorityReductionWhenMultipleLimits
  major
  when normal_load_factor ≥ 0.9 * N_z_max and angle_of_attack ≥ 0.9 * Alpha_max
  ensure |stick_pitch_cmd| ≤ 50 %
  on_violation transition Caution;

// ========================================================================
//  Proof
// ========================================================================
proof FlightEnvelopeProof {
  tactic differential_invariants;
  tactic k_induction 5;
  tactic interval_arithmetic;
  // Key lemma: rate limiting on g-load bounds the change per sample step.
  // This is the inductive step for GLimitRate.
  lemma RateLimitBounds =
    forall t . |rate_of normal_load_factor| ≤ 1.5 g per s
      implies
    next (normal_load_factor ≤ old normal_load_factor + 0.015 g);
  certificate {
    format = native;
    include_trace = true;
    include_counterexample = true;
    hash = sha256;
  }
}
```

**What this demonstrates over (b):**
- Seven named physical dimensions with explicit ranges.
- Two domain types: enum and phase enum.
- Aircraft-specific constants as bounded state variables (vary by gross weight computation).
- Mixed sampling rates (10 ms for pitch-sensitive, 500 ms for gross weight).
- Mach-speed cross-dimension arithmetic (`M_mo * 661 kt`).
- Configuration-dependent derived computation (`V_stall_current`).
- Temporal modalities: `for 3 s` (continuous window), `always`, `delta`, `rate_of`.
- Combined-limit logic: `AuthorityReductionWhenMultipleLimits` is a real-world cross-axis protection used in Airbus normal law.
- Multi-tactic proof with a hand-written lemma that assists the inductive step.

---

## 4. Type System

### 4.1 Overview

GUARD has a **two-level type system**:

1. **Structural types** — what kind of thing a value is (scalar, array, record, enum).
2. **Physical types** — what physical dimension a value represents (knots, degrees, g, %).

Both levels are checked at compile time. A structural mismatch is a programming error; a physical mismatch is a **safety error** that carries the risk of a Mars Climate Orbiter incident.

### 4.2 Domains

A **domain** constrains the legal values of a variable. There are three domain forms:

| Form | Syntax | Example | Meaning |
|------|--------|---------|---------|
| Enumeration | `{ A, B, C }` | `{ Red, Orange, Yellow }` | Exactly these discrete values. |
| Interval | `[lo .. hi]` | `[0 kt .. 500 kt]` | Any value in this closed range. |
| Product | `(D₁ × D₂)` | `[Zone × Role]` | Pairs from each component domain. |

Domains compose: `array [Zone × Role] of AccessMode` declares a 2D lookup table.

### 4.3 Physical Unit Types (Dimensional Analysis)

Every `quantity` expression carries a **unit signature** — a rational power-product of the seven SI base dimensions (length, mass, time, temperature, angle, current, amount). The compiler maintains this signature through every operation:

| Operation | Unit Rule |
|-----------|-----------|
| `a + b` | Signatures must be equal. |
| `a - b` | Signatures must be equal. |
| `a * b` | Signatures multiply (exponents add). |
| `a / b` | Signatures divide (exponents subtract). |
| `a ≤ b` | Signatures must be equal. |
| `rate_of a` | Signature of `a` divided by time (`a / s`). |
| `delta a` | Same signature as `a`. |

All quantities are normalized to SI base units before bytecode emission, scaled to `f64` or fixed-point as configured. The FLUX VM computes in normalized units; display conversion is a tool-level concern.

**Example — unit error:**
```guard
ensure indicated_airspeed ≤ Alpha_max
//     ^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^
//     Knots (length/time)   Degrees (angle)
// ERROR G101: unit mismatch — comparing knots to degrees.
```

### 4.4 Constraints (Invariants)

An `invariant` is a named safety requirement with four components:

| Component | Required | Meaning |
|-----------|----------|---------|
| `priority` | No (default: `minor`) | `critical`, `major`, or `minor` — maps to severity in the fault tree. |
| `when expr` | No | Guard: constraint is only checked when this condition is true. |
| `ensure expr` | Yes | The property that must hold. |
| `on_violation action` | No (default: `log`) | What happens if the property fails at runtime. |

Violation actions in escalating severity:
- `log` — record the event, continue execution.
- `warn` — annunciate to operator, continue execution.
- `transition <state>` — transition the system mode, continue with restricted authority.
- `halt` — stop all outputs immediately (fail-safe).

### 4.5 Derived Rules

A `derive` rule states a **proof obligation**: if these premises hold, then this conclusion holds. Unlike invariants, derived rules do not add runtime checks — they add entries to the proof certificate that the compiler must discharge.

```guard
derive PositiveThrottleImpliesEngineEnabled
  from ThrottleMustNotExceedMax, ThrottleMustNotReverse
  when throttle_command > 0 %
  conclude engine_enabled = true;
```

If the compiler cannot prove this entailment, it emits `G302` (derived rule not entailed) with a counterexample.

### 4.6 Temporal Modalities

GUARD uses **discrete-time linear temporal logic (LTL)** with bounded-duration operators. The semantics are defined over traces `σ₀, σ₁, σ₂, …` where each `σᵢ` is a full system state snapshot.

| Operator | Formal Semantics | Safety Pattern |
|----------|-----------------|----------------|
| `always P` | ∀k ≥ 0 . P(σₖ) | Limit never exceeded |
| `eventually P` | ∃k ≥ 0 . P(σₖ) | Alarm must eventually sound |
| `next P` | P(σ₁) | One-step lookahead |
| `P until Q` | ∃k ≥ 0 . Q(σₖ) ∧ ∀j < k . P(σⱼ) | Armed until fired |
| `P since Q` | Q held at some past step; P held in every step since | Monitoring since fault |
| `for T P` | ∀k ∈ [t, t+n] . P(σₖ) (n = T / sample_period) | Cooldown window |
| `after T P` | P(σₜ₊ₙ) (n = T / sample_period) | Startup delay |
| `old x` | σₜ₋₁(x) | Previous cycle value |
| `rate_of x` | (σₜ(x) − σₜ₋₁(x)) / Δt | Per-cycle rate of change |
| `delta x` | σₜ(x) − σₜ₋₁(x) | Absolute per-cycle change |

**Temporal type rule:** `rate_of` and `delta` may only be applied to state variables declared with `sampled every`. Applying them to enum state or event flags is an error (G103).

### 4.7 Verification Conditions

For each `invariant I`, the compiler generates:

1. **Initiation**: `InitialState ⇒ I(σ₀)` — the invariant holds at power-on.
2. **Preservation**: `I(σₜ) ∧ Transition(σₜ, σₜ₊₁) ⇒ I(σₜ₊₁)` — if it held last cycle, it holds this cycle.

If both are proved (by SMT solver), the invariant is **inductive** and holds in all reachable states.

Temporal properties use:
- **K-induction** for `always` properties (unfolds k steps, checks the inductive step).
- **Bounded model checking (BMC)** for `eventually` and finite-horizon properties.
- **Differential invariants** for `rate_of` constraints involving continuous physics.

---

## 5. Compilation to FLUX Bytecode

### 5.1 Pipeline

```
GUARD Source (.guard)
      │
      ▼
 ┌──────────┐
 │  Parser  │   PEG-based, error-recovering. Produces annotated AST.
 └──────────┘
      │
      ▼
 ┌──────────────┐
 │  Typechecker │   Unit normalization, domain membership, temporal type rules.
 └──────────────┘
      │
      ▼
 ┌──────────────────┐
 │  Lowering Passes │   Desugar temporal ops → history buffer ops.
 │                  │   Expand quantifiers → FLUX loop primitives.
 │                  │   Allocate memory slots (256-slot address space).
 └──────────────────┘
      │
      ▼
 ┌────────┐
 │ Prover │   Emit SMT-LIB VCs. Invoke Z3 / cvc5 / Bitwuzla.
 └────────┘
      │
      ▼
 ┌─────────┐
 │ Emitter │   Emit FLUX bytecode (.flux) + proof certificate (.guardcert).
 └─────────┘
```

### 5.2 FLUX VM Memory Model

The FLUX VM has 256 memory slots (indexed 0–255):

| Slot Range | Purpose |
|------------|---------|
| 0–31 | Constants (pre-loaded at boot) |
| 32–127 | State variables (updated by host every cycle) |
| 128–223 | Temporal history buffers (circular queues for `old`, `for T`) |
| 224–255 | Scratch / intermediate computation |

### 5.3 Compiling Example (a) — Throttle Limit

Source:

```guard
module ThrottleLimit version "1.0.0" for "ECU-320 Throttle Body Authority";
dimension Percent is real % from 0 % to 100 %;
state throttle_command has real in [0 % .. 100 %] sampled every 10 ms;
invariant ThrottleMustNotExceedMax critical ensure throttle_command ≤ 100 % on_violation halt;
invariant ThrottleMustNotReverse   critical ensure throttle_command ≥ 0 %   on_violation halt;
```

**Compilation steps:**

1. **Unit lowering:** `100 %` → normalized scalar `1.0`. `0 %` → `0.0`. `throttle_command` mapped to slot 2.
2. **Constant allocation:** Upper bound `1.0` → slot 0. Lower bound `0.0` → slot 1.
3. **Bytecode emission:** Single-step check loop (no temporal history needed).

**Bytecode table:**

| Offset | Opcode | Operands | Source Location | Semantic Description |
|--------|--------|----------|-----------------|----------------------|
| 0 | `Nop` | — | 1:1 | Module header alignment |
| 1 | `Push` | `1.0` | 13:33 | Load constant 100 % (normalized) |
| 2 | `Store` | slot 0 | 10:1 | Initialize upper bound register |
| 3 | `Push` | `0.0` | 18:33 | Load constant 0 % (normalized) |
| 4 | `Store` | slot 1 | 10:1 | Initialize lower bound register |
| 5 | `Push` | `0.0` | 10:1 | Default throttle value at cold-start |
| 6 | `Store` | slot 2 | 10:1 | Store to `throttle_command` slot |
| 7 | `Trace` | — | 1:1 | Begin constraint check loop; record Merkle trace point |
| 8 | `Load` | slot 2 | 13:10 | Push current `throttle_command` |
| 9 | `Load` | slot 0 | 13:33 | Push upper bound (1.0) |
| 10 | `Le` | — | 13:26 | Compare: throttle ≤ 1.0 |
| 11 | `Assert` | id=1 | 13:3 | **Hard constraint** ThrottleMustNotExceedMax |
| 12 | `Load` | slot 2 | 18:10 | Push current `throttle_command` |
| 13 | `Load` | slot 1 | 18:33 | Push lower bound (0.0) |
| 14 | `Ge` | — | 18:26 | Compare: throttle ≥ 0.0 |
| 15 | `Assert` | id=2 | 18:3 | **Hard constraint** ThrottleMustNotReverse |
| 16 | `Nop` | — | 1:1 | Yield / wait for next 10 ms sample |
| 17 | `Jump` | offset 8 | 1:1 | Loop back to Trace |

**Hex dump:**
```
0000  70 32 01 3F F0 00 00 00 00 00 00 00 51 00 32 01
0010  00 00 00 00 00 00 00 00 51 01 32 01 00 00 00 00
0020  00 00 00 00 51 02 72 50 02 50 00 34 60 01 50 02
0030  50 01 35 60 02 70 40 08
```

**Byte encoding key:**
- `70` = `Nop`
- `32 01 3FF0...` = `Push` with IEEE 754 double operand (3FF0… = 1.0)
- `51 xx` = `Store` to slot `xx`
- `50 xx` = `Load` from slot `xx`
- `34` = `Le` (less-than-or-equal comparison)
- `35` = `Ge` (greater-than-or-equal comparison)
- `60 xx` = `Assert` with constraint ID `xx` (triggers halt on false)
- `72` = `Trace` (records execution point for Merkle trace)
- `40 08` = `Jump` to offset 8

**Runtime behavior:**
1. On power-up: VM initializes constants into slots 0–1, sets slot 2 to 0.0.
2. Host writes new sensor reading to slot 2 every 10 ms.
3. VM executes offsets 8–17: two comparisons, two asserts, one yield, one jump.
4. If either `Assert` fails: `FluxError::ConstraintViolation` fires, halts all outputs, records source location, constraint name, and observed value.
5. The `Trace` opcode captures a Merkle-compatible execution record for the proof certificate's runtime trace.

### 5.4 Temporal Expansion

For temporal invariants such as `for 3 s ( |pitch_rate| ≤ 5 °/s )` at a 10 ms sample rate, the lowering pass:

1. Allocates a **300-entry circular history buffer** in slots 128–427.
2. Emits a **sub-loop** before the constraint expression that iterates over all 300 history entries and asserts the constraint on each.
3. The host fills the history buffer entry for slot `t mod 300` each cycle.

This turns the temporal operator into a space/time trade-off that fits in the FLUX VM's deterministic execution model: no dynamic allocation, bounded execution time.

### 5.5 FPGA Enforcement

The FLUX VM is designed to map directly to **FPGA lookup tables**. The 43-opcode ISA was chosen so that each opcode synthesizes to a single LUT chain at 50 MHz. The constraint loop executes in < 1 µs per cycle, providing hard real-time enforcement independent of any operating system. The GUARD toolchain produces both the FLUX bytecode (for simulation and soft-core deployment) and a synthesizable Verilog netlist (for FPGA hard enforcement).

---

## 6. Error Messages for Safety Engineers

Every GUARD error message follows this structure:

1. **What went wrong** — in plain English, not compiler jargon.
2. **Where** — source file, line, column, with a source snippet.
3. **The safety impact** — why this matters physically.
4. **Concrete suggestions** — what to change.

### Parse Errors (G0xx)

**G001 — Missing structural keyword:**
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

**G002 — Missing unit on physical state:**
```
Error G002: The state variable 'indicated_airspeed' needs a unit.

   --> flight-envelope.guard:55:3
    |
 55 |   state indicated_airspeed has real
    |         ^^^^^^^^^^^^^^^^^^^
    |
    = Hint: Physical quantities must have units so the compiler
      can check dimensional consistency. Try:
        state indicated_airspeed has real in [0 kt .. 500 kt]
```

**G003 — Undefined domain:**
```
Error G003: I don't know what 'AccessMode' means here.

   --> zone-access.guard:38:28
    |
 38 |   array [Zone × Role] of AccessMode
    |                            ^^^^^^^^^^
    |
    = Hint: Define it with:
        domain AccessMode = { Locked, Unlocked, Escorted };
    = Or import it:
        import SecurityModel.AccessMode;
```

### Type Errors (G1xx)

**G101 — Unit mismatch (the "Mars Climate Orbiter" error):**
```
Error G101: You are comparing apples and oranges — literally.

   --> flight-envelope.guard:78:10
    |
 78 |   ensure indicated_airspeed ≤ Alpha_max
    |          ^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^
    |          Knots (speed)         Degrees (angle)
    |
    = 'indicated_airspeed' is measured in knots.
      'Alpha_max' is measured in degrees.
      These are different physical dimensions and cannot be compared.
    = Did you mean to compare 'angle_of_attack' to 'Alpha_max'?
```

**G102 — Authorization matrix conflict:**
```
Error G102: This entry contradicts the domain definition.

   --> zone-access.guard:45:5
    |
 45 |     (Red, Visitor) → Unlocked,
    |      ^^^^^^^^^^^^^
    |
    = Safety impact: A visitor would be granted unsupervised access
      to the Red radiation zone. This violates the ALARA principle
      (As Low As Reasonably Achievable).
    = Suggestion: Change to 'Locked' or escalate to the RSO.
```

**G103 — Rate operator on non-continuous state:**
```
Error G103: 'rate_of' can only be applied to continuously sampled state.

   --> flight-envelope.guard:112:18
    |
112 |   ensure |rate_of flap_setting| ≤ 2 °/s
    |                   ^^^^^^^^^^^^
    |
    = 'flap_setting' is an enum (Clean, Takeoff, Landing).
      Rates of change are undefined for discrete values.
    = Suggestion: Remove 'rate_of', or model the transition as a
      continuous proxy variable (e.g., flap_extension_degrees).
```

### Static Analysis Warnings (G2xx)

**G201 — Unreachable invariant:**
```
Warning G201: This invariant can never trigger.

   --> throttle.guard:18:1
    |
 18 | invariant ThrottleMustNotReverse
    |
    = The 'when' clause requires 'throttle_command < 0 %', but
      the state declaration says the domain is [0 % .. 100 %].
    = The compiler can prove this condition is always false.
    = Suggestion: Remove the invariant, or widen the state domain
      if the sensor can report negative values (sensor fault mode).
```

**G202 — Conflicting violation actions:**
```
Warning G202: Two invariants may demand contradictory actions.

   --> flight-envelope.guard:88:1 and 95:1
    |
 88 | invariant AlphaFloorProtection ... on_violation transition Protection;
 95 | invariant AlphaHardLimit       ... on_violation halt;
    |
    = At angle_of_attack = 15.4 °, both invariants are active.
      One demands 'transition Protection'; the other demands 'halt'.
    = Safety impact: The FCC may receive conflicting commands.
    = Suggestion: Merge into a single envelope invariant with a
      priority table, or use 'critical' > 'major' ordering.
```

### Verification Failures (G3xx)

**G301 — Property does not hold (with counterexample):**
```
Error G301: The safety invariant 'StallWarningMargin' does NOT always hold.

   --> flight-envelope.guard:72:1
    |
 72 | invariant StallWarningMargin
    |
    = The solver found a reachable state where the property fails.

    Counterexample:
      indicated_airspeed = 82.3 kt
      V_stall_current    = 85.0 kt   (Landing flaps)
      flap_setting       = Landing
      flight_phase       = Approach

    = At this state, IAS (82.3 kt) < 1.05 × V_stall (89.25 kt).
      The aircraft is in a stall precursor condition on approach.
    = Safety impact: Alpha-floor may lack authority to recover
      before ground contact.
    = Suggestions:
        1. Raise the minimum approach speed in the FMS.
        2. Increase the stall margin factor from 1.05 to 1.10.
        3. Restrict the domain of flap_setting during approach.
```

**G303 — Solver timeout:**
```
Error G303: The proof engine could not verify 'FlightEnvelopeProof'
            within the allotted time (300 s).

   --> flight-envelope.guard:145:1
    |
145 | proof FlightEnvelopeProof { tactic k_induction 5; ... }
    |
    = Current tactic: k_induction 5 (unfolds 5 time steps)
    = Suggestions:
        1. Reduce k: 'tactic k_induction 3;'
        2. Add the RateLimitBounds lemma to strengthen the inductive step.
        3. Switch to bounded model checking: 'tactic bounded_model_check 50 steps;'
        4. Increase timeout: 'tactic k_induction 5 timeout 600 s;'
```

### Runtime Critical (G4xx)

**G401 — Constraint violated during flight:**
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

  Aircraft state:
    indicated_airspeed  = 142 kt
    altitude            = 1,240 ft
    flight_phase        = Approach
    stick_pitch_cmd     = +78 % (nose-up)

  Immediate action:  HALT (revert to direct law)

  Post-flight: Attach NVM execution trace to incident report.
               Trace digest: sha256:9a4f2c...
```

---

## 7. Comparison to Related Work

GUARD occupies a specific niche: a **requirements-language-first** safety specification tool that compiles to a lightweight enforcement VM and produces independently verifiable proof artifacts.

| Dimension | GUARD | SCADE/Lustre | Alloy | Datalog |
|-----------|-------|--------------|-------|---------|
| **Primary user** | Safety engineer | Control engineer | Software architect | Database engineer |
| **Syntax feel** | Requirements doc | Dataflow equations | Relational logic | Logic rules |
| **Execution model** | Constraint loop on FLUX VM | Synchronous dataflow | SAT solver (offline) | Fixpoint evaluation |
| **Temporal logic** | Explicit (`always`, `for T`, `rate_of`) | Implicit (`pre`, `->`, clocks) | Via dynamic predicates | Stratified negation |
| **Physical units** | **Mandatory, checked** | Optional | None | None |
| **Proof style** | SMT + inductive invariants + certificates | Tool qualification (KCG) | Bounded SAT | Query satisfiability |
| **Certificates** | **Merkle-ized, independent** | DO-178C tool qualification | None | None |
| **Target runtime** | FLUX VM / FPGA | C or Ada (certified) | Java (Alloy Analyzer) | Datalog engine |
| **Hard real-time** | Yes (< 1 µs constraint loop) | Yes (deterministic) | No (offline only) | Soft |

### GUARD vs. SCADE/Lustre

**SCADE's strengths:** Qualified code generator (KCG) is the industry gold standard for DO-178C. Synchronous dataflow is intuitive for control engineers. Excellent traceability.

**Where GUARD differs:**
- *Audience*: SCADE requires training in synchronous programming. GUARD reads like a requirements document.
- *Units*: SCADE has optional unit annotations. GUARD enforces dimensional consistency at compile time.
- *Proof model*: SCADE relies on *tool qualification* (trust the code generator). GUARD relies on *proof certificates* (trust a small independent verifier, not the compiler).
- *Temporal expressiveness*: Lustre's `pre` and `->` are powerful but subtle; `for 3 s` is not idiomatic. GUARD's operators map directly to natural-language requirements text.
- *Runtime footprint*: SCADE-generated C requires an OS thread and libc. FLUX bytecode runs in 8 KB of flash with no heap allocation.

**Use SCADE when:** You need DO-178C certification with a qualified toolchain, you have control engineers on staff, and you can afford the Esterel toolchain cost.
**Use GUARD when:** Safety engineers own the specification, you want proofs that survive compiler upgrades, or your target is bare-metal or FPGA.

### GUARD vs. Alloy

**Alloy's strengths:** Relational modeling is unmatched for structural constraints (authorization policies, ownership graphs). Bounded verification finds subtle design-level bugs. Lightweight and open-source.

**Where GUARD differs:**
- *Execution*: Alloy is a model finder, not a runtime. It answers "is there a counterexample within bound k?" GUARD generates executable bytecode that enforces constraints at 100 Hz.
- *Physical units*: Alloy has no concept of knots, feet, or g-loads.
- *Temporal logic*: Alloy 6 added LTL operators, but they are translated to SAT and verified only within a bounded horizon. GUARD uses k-induction for unbounded proofs.
- *Error messages*: Alloy counterexamples are raw relational tuples. GUARD counterexamples cite aircraft state and suggest physical fixes.
- *Interoperability*: Use Alloy to verify the structural correctness of GUARD domain definitions (e.g., "is the auth_matrix total?"), then use GUARD to enforce those domains at runtime.

**Use Alloy when:** You are designing a protocol, file-system structure, or authorization policy and want to explore structural what-if scenarios before building.
**Use GUARD when:** You need to continuously enforce safety limits on a physical system.

### GUARD vs. Datalog

**Datalog's strengths:** Rule-based reasoning is declarative and composable. Semi-naive evaluation handles large fact bases efficiently. Excellent for static analysis and authorization.

**Where GUARD differs:**
- *Time*: Standard Datalog is atemporal. Temporal extensions (DatalogMTL) are research tools, not shipping products.
- *Physical semantics*: Datalog reasons about discrete facts. GUARD reasons about continuous quantities with derivatives.
- *Proof certificates*: Datalog derivations can track provenance, but there is no standard for tamper-evident certificates. GUARD produces Merkle-ized SMT proofs.
- *Determinism*: Datalog evaluation order can affect performance. GUARD's FLUX VM is cycle-accurate and memory-bounded.

**Use Datalog when:** You are building a compiler, dependency analyzer, or authorization engine with millions of facts.
**Use GUARD when:** A missed deadline means a crashed aircraft.

---

## 8. Proof Certificates

### 8.1 Purpose

The **proof certificate** (`.guardcert`) is the cornerstone of GUARD's trust model. It allows a safety auditor — or a regulatory authority — to verify that the compiled bytecode correctly implements the source requirements, without trusting the GUARD compiler.

The certificate is checked by an **independent verifier** with a Trusted Computing Base (TCB) of under 1,000 lines of Rust. The compiler is not in the TCB.

### 8.2 Certificate Contents

```json
{
  "certificate_format": "guard-native-v1",
  "module": "ThrottleLimit",
  "version": "1.0.0",
  "compiler": {
    "name": "guardc",
    "version": "1.0.0-ship",
    "target": "flux-isa-43"
  },
  "source_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "bytecode_hash": "sha256:a3c5f1e...",
  "proofs": [
    {
      "proof_id": "ThrottleSafetyProof",
      "tactics": ["interval_arithmetic", "bit_blast"],
      "status": "verified",
      "verification_time_ms": 47,
      "obligations": [
        {
          "obligation_id": "inv-01",
          "kind": "invariant_preservation",
          "name": "ThrottleMustNotExceedMax",
          "source_span": "throttle.guard:13:3-15:19",
          "vc": {
            "logic": "QF_LRA",
            "formula": "(assert (<= throttle_command 1.0))",
            "status": "sat"
          },
          "trace_digest": "sha256:bb12a9...",
          "counterexample": null
        }
      ],
      "merkle_root": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "metadata": {
    "generated_at": "2026-05-03T08:35:51Z",
    "host_os": "linux-x86_64",
    "deterministic": true
  }
}
```

### 8.3 What Every Field Means

| Field | Meaning |
|-------|---------|
| `source_hash` | SHA-256 of the canonicalized source text. If the source changes after certification, this hash changes and the certificate is invalid. |
| `bytecode_hash` | SHA-256 of the emitted FLUX bytecode. Ties the certificate to exactly one compiled binary. |
| `proofs` | One entry per `proof { ... }` block in the source. |
| `obligations` | Individual verification conditions. Each `invariant` generates at least two (initiation + preservation); each `derive` generates one (entailment). |
| `vc.logic` | SMT-LIB logic used: `QF_LRA` = quantifier-free linear real arithmetic; `QF_BV` = bit-vectors; `QF_NRA` = nonlinear real arithmetic. |
| `vc.status` | `sat` = no counterexample (property holds); `unsat` = counterexample found (property fails); `unknown` = solver timeout. |
| `trace_digest` | Hash of the symbolic execution trace. Used for incremental re-verification (only recheck obligations whose traces changed). |
| `counterexample` | Concrete assignment of variable values that violates the property. Null if the property holds. |
| `merkle_root` | Merkle root over all `trace_digest` values. A single-hash comparison detects any tampering with any obligation. |

### 8.4 Obligation Kinds

| Kind | Description |
|------|-------------|
| `invariant_initiation` | Does the invariant hold at power-on (initial state)? |
| `invariant_preservation` | Does the invariant hold in all reachable states? |
| `derived_rule_sanity` | Is the derived rule logically entailed by its premises? |
| `temporal_safety` | Does an `always` property hold for all time? |
| `temporal_liveness` | Does an `eventually` property eventually occur? |
| `unit_consistency` | Are all operations dimensionally consistent? |
| `domain_membership` | Can any variable leave its declared domain at runtime? |

### 8.5 Merkle Tree Construction

The Merkle root is a tamper-evident seal over the entire proof:

```
leaf_i = SHA-256( obligation_id ‖ trace_digest )
parent = SHA-256( left ‖ right )
root   = reduce(leaves, parent_fn)
```

If any obligation is recomputed with a different solver or different bounds, its `trace_digest` changes, and the `merkle_root` changes. An auditor can confirm the entire proof with one hash comparison.

### 8.6 Counterexample Format

When a property fails, the certificate includes a concrete counterexample:

```json
"counterexample": {
  "model": {
    "indicated_airspeed": 82.3,
    "V_stall_current": 85.0,
    "flap_setting": "Landing"
  },
  "time_step": 0,
  "violated_invariant": "StallWarningMargin",
  "explanation": "At time step 0, IAS (82.3 kt) < 1.05 × V_stall (89.25 kt). The aircraft is below its stall warning margin in Landing configuration."
}
```

The `explanation` field is generated in plain English, using the physical variable names and units from the source — not the normalized SMT variable names.

### 8.7 Trusted Computing Base

The certificate verifier requires only:

1. **SHA-256** (or Blake3) for hash verification — ≈ 200 lines.
2. **SMT solver** (Z3, cvc5, or Bitwuzla) for re-checking VCs — external, standard.
3. **FLUX VM** for executing the bytecode trace — ≈ 300 lines.
4. **Source parser** for confirming source-to-bytecode span mapping — ≈ 200 lines.

Total: ≈ 700 lines + an external SMT solver. The compiler itself is **not** in the TCB.

### 8.8 Certificate Lifecycle

```
 GUARD Source ──► guardc (compiler) ──► FLUX Bytecode
                        │
                        ▼
                  SMT Prover (Z3 / cvc5)
                        │
                        ▼
               Certificate (.guardcert)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
         Safety Audit          CI Gate
         (regulatory)       (blocks deploy if
                             regression detected)
```

On every build, the CI gate re-runs the independent verifier. If the `merkle_root` in the certificate does not match what the verifier computes from the source and bytecode, the build fails. A safety auditor at certification time runs the same verifier and arrives at the same conclusion without trusting any intermediate artifact.

---

## Appendix A — Module Sections Summary

| Section | Purpose | Required |
|---------|---------|----------|
| `module` | Identity, version, target system description | Yes |
| `import` | Reuse types and constants from other modules | No |
| `dimension` | Define named physical units with legal ranges | No |
| `domain` | Define discrete/enumerable value sets | No |
| `state` | Observable system variables with types and domains | Yes |
| `invariant` | Hard constraints that must hold (runtime + proof) | Yes |
| `derive` | Logical consequences (proof obligation only, no runtime cost) | No |
| `proof` | Verification tactics and certificate configuration | Recommended |

## Appendix B — File Layout

```
guard-dsl/
├── SPEC.md              # Complete language specification
├── GRAMMAR.ebnf         # Normative EBNF grammar
├── BYTECODE.md          # GUARD → FLUX bytecode mapping guide
├── CERTIFICATES.md      # Proof certificate format and verification
├── ERRORS.md            # Human-centered error catalog (all G-codes)
├── COMPARISON.md        # Detailed comparison whitepaper
└── examples/
    ├── throttle.guard        # (a) Simple: throttle limit
    ├── zone-access.guard     # (b) Medium: radiation bunker interlock
    └── flight-envelope.guard # (c) Complex: fly-by-wire envelope protection
```
