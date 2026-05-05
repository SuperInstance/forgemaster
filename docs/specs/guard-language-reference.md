# GUARD Language Reference

## Overview

GUARD is a domain-specific constraint language designed for specifying, verifying, and enforcing behavioral and safety constraints on autonomous systems. It provides a declarative syntax for expressing range bounds, type domain restrictions, temporal invariants, security policies, and composable logical combinators — all compiled to efficient runtime checks.

GUARD files use the `.guard` extension and are compiled by the `guardc` compiler into native Rust validation modules, Python checkers, or standalone verification binaries.

### Design Goals

- **Declarative:** Describe *what* constraints hold, not *how* to check them.
- **Composable:** Constraints combine freely via AND, OR, NOT, and nesting.
- **Temporal-aware:** First-class support for time-bounded invariants and stability checks.
- **Safety-graded:** Every constraint carries a priority and safety level for runtime triage.
- **Compilable:** Targets Rust (zero-cost abstractions), Python (flexible), and Coq (proof extraction).

---

## Lexical Structure

### Tokens

GUARD uses a simple token set:

- **Identifiers:** `[a-zA-Z_][a-zA-Z0-9_]*`
- **Numeric literals:** `[0-9]+(\.[0-9]+)?` (integers and floats)
- **String literals:** `"([^"\\]|\\.)*"` (double-quoted, with escape sequences)
- **Operators:** `&&`, `||`, `!`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `+`, `-`, `*`, `/`
- **Punctuation:** `(`, `)`, `{`, `}`, `[`, `]`, `,`, `;`, `.`, `@`, `:`, `->`, `=>`
- **Keywords:** `CONSTRAINT`, `RANGE`, `DOMAIN`, `EXACT`, `AND`, `OR`, `NOT`, `WITHIN`, `STABLE`, `DEADLINE`, `REQUIRES`, `SANDBOX`, `IMPORT`, `EXPORT`, `AS`, `IF`, `THEN`, `ELSE`, `LET`, `IN`, `MATCH`, `TYPE`, `ENUM`, `STRUCT`, `FN`, `RETURN`, `TRUE`, `FALSE`

### Whitespace and Comments

Whitespace (spaces, tabs, newlines) is insignificant except as a token separator.

```guard
# This is a line comment. Everything from # to end-of-line is ignored.
x > 0  # inline comments are supported
```

Block comments are not supported; use consecutive line comments.

---

## Constraint Types

### Range Constraints

Range constraints bound a numeric value between a lower and/or upper bound.

```guard
CONSTRAINT temperature: RANGE -40.0 .. 125.0;
CONSTRAINT altitude: RANGE 0 .. 15000;
CONSTRAINT speed: RANGE >= 0;        # one-sided (lower bound only)
CONSTRAINT pressure: RANGE <= 300;   # one-sided (upper bound only)
```

Range bounds are **inclusive** by default. Use `<` or `>` for exclusive bounds:

```guard
CONSTRAINT index: RANGE 0 >< length;  # 0 <= index < length
CONSTRAINT ratio: RANGE >0.0 .. <1.0; # exclusive on both sides
```

### Domain Constraints

Domain constraints restrict a value to a set of allowed values (enumerated domain) or a named type domain.

```guard
CONSTRAINT mode: DOMAIN { "idle", "active", "fault", "maintenance" };
CONSTRAINT color: DOMAIN { RED, GREEN, BLUE };
CONSTRAINT priority: DOMAIN { 1, 2, 3, 5, 8 };
CONSTRAINT name: DOMAIN STRING;
CONSTRAINT flag: DOMAIN BOOL;
```

Domains support **open** and **closed** semantics:

```guard
CONSTRAINT sensor_type: DOMAIN CLOSED { "temperature", "pressure", "flow" };
# CLOSED: value MUST be in the set (default)

CONSTRAINT custom_unit: DOMAIN OPEN { "meters", "feet" };
# OPEN: value MAY be in the set; unknown values trigger a warning, not a violation
```

### Exact Constraints

Exact constraints assert a value equals a specific constant or expression.

```guard
CONSTRAINT version: EXACT 2;
CONSTRAINT header: EXACT "GUARDv2";
CONSTRAINT checksum: EXACT compute_crc32(payload);
```

Exact constraints are typically used for protocol validation and configuration verification.

---

## Combinators

### AND (Conjunction)

All sub-constraints must hold.

```guard
CONSTRAINT valid_flight:
  altitude RANGE 0 .. 15000
  AND speed RANGE 0 .. 340
  AND mode DOMAIN { "cruise", "ascent", "descent" };
```

### OR (Disjunction)

At least one sub-constraint must hold.

```guard
CONSTRAINT acceptable_power:
  source DOMAIN { "battery", "solar" }
  OR voltage RANGE 10.0 .. 14.0;
```

### NOT (Negation)

The sub-constraint must NOT hold.

```guard
CONSTRAINT not_overheated: NOT (temperature > 90.0 AND duration > 60);
```

### Nesting

Combinators compose arbitrarily deeply:

```guard
CONSTRAINT safe_mode:
  (mode DOMAIN { "active" } AND temperature RANGE -10.0 .. 80.0)
  OR
  (mode DOMAIN { "idle" } AND NOT (temperature > 100.0));
```

### Implication

`IF ... THEN ...` sugar for `NOT(...) OR (...)`:

```guard
CONSTRAINT thermal_guard:
  IF temperature > 80.0 THEN fan_speed RANGE 80 .. 100;
```

---

## Temporal Constraints

Temporal constraints reason over time, requiring properties to hold across multiple samples or within time windows.

### WITHIN

A property must become true within a specified time window.

```guard
CONSTRAINT startup_complete:
  status == "ready" WITHIN 30s;

CONSTRAINT fault_recovery:
  mode DOMAIN { "active" } WITHIN 5m AFTER fault_cleared == TRUE;
```

Time units: `ms`, `s`, `m`, `h` (milliseconds, seconds, minutes, hours).

### STABLE

A property must remain continuously true for a minimum duration.

```guard
CONSTRAINT stable_landing:
  altitude RANGE 0 .. 1 STABLE 10s;

CONSTRAINT steady_state:
  (temperature RANGE 20.0 .. 25.0 AND pressure RANGE 101.0 .. 101.5)
  STABLE 60s;
```

### DEADLINE

A property must hold by an absolute or relative deadline.

```guard
CONSTRAINT deployment_deadline:
  deployment_complete == TRUE DEADLINE "2026-06-01T00:00:00Z";

CONSTRAINT response_time:
  response_received == TRUE DEADLINE 200ms AFTER request_sent == TRUE;
```

### Temporal Quantifiers

```guard
CONSTRAINT always_within_bounds:
  ALWAYS (altitude RANGE 0 .. 15000) OVER 1h;

CONSTRAINT eventually_recovers:
  EVENTUALLY (mode DOMAIN { "active" }) WITHIN 5m AFTER fault;

CONSTRAINT at_most_3_faults:
  COUNT(fault == TRUE) <= 3 OVER 1h;
```

---

## Security Constraints

### REQUIRES

Declares runtime permission requirements. A constraint annotated with `REQUIRES` can only be satisfied if the caller possesses the specified permission.

```guard
CONSTRAINT admin_override:
  mode DOMAIN { "override" }
  REQUIRES "admin:write";

CONSTRAINT shutdown_sequence:
  action DOMAIN { "shutdown" }
  REQUIRES "system:shutdown"
  REQUIRES "auth:multi_factor";
```

Multiple `REQUIRES` clauses are conjunctive (all must be satisfied).

### SANDBOX

Restricts execution to an isolated environment with explicitly listed capabilities.

```guard
CONSTRAINT untrusted_plugin:
  SANDBOX {
    CAPABILITIES: [ "fs:read", "net:https" ],
    MEMORY_LIMIT: 64MB,
    CPU_LIMIT: 50%,
    TIMEOUT: 30s,
    NETWORK: ALLOWED ["api.example.com:443"],
    FILESYSTEM: READ_ONLY "/data"
  };
```

Sandbox parameters:

| Parameter     | Type          | Description                                    |
|---------------|---------------|------------------------------------------------|
| `CAPABILITIES`| `[STRING]`    | List of granted capability tokens              |
| `MEMORY_LIMIT`| Size          | Maximum memory allocation                      |
| `CPU_LIMIT`   | Percentage    | Maximum CPU utilization (0–100%)               |
| `TIMEOUT`     | Duration      | Maximum wall-clock execution time              |
| `NETWORK`     | Rule          | `ALLOWED [hosts]` or `DENIED [hosts]` or `NONE`|
| `FILESYSTEM`  | Rule          | `READ_ONLY path`, `READ_WRITE path`, or `NONE` |

---

## Metadata Annotations

### @priority

Assigns a numeric priority for runtime triage. Higher values = more important.

```guard
@priority(100)
CONSTRAINT hull_integrity: pressure RANGE 0 .. 50;

@priority(10)
CONSTRAINT log_verbosity: level DOMAIN { 0, 1, 2, 3 };
```

Default priority is 0. Constraints are checked in priority order (descending).

### @safety_level

Classifies the safety criticality of a constraint using standard integrity levels.

```guard
@safety_level(SIL4)
CONSTRAINT reactor_temperature: temperature RANGE 0.0 .. 1200.0;

@safety_level(SIL2)
CONSTRAINT coolant_flow: flow_rate RANGE 10.0 .. 200.0;

@safety_level(ASIL_D)
CONSTRAINT braking_force: force RANGE 1000 .. 50000;
```

Recognized safety levels:

| Standard | Levels                          |
|----------|---------------------------------|
| IEC 61508| `SIL1`, `SIL2`, `SIL3`, `SIL4` |
| ISO 26262| `ASIL_A`, `ASIL_B`, `ASIL_C`, `ASIL_D` |
| DO-178C  | `DAL_A`, `DAL_B`, `DAL_C`, `DAL_D`, `DAL_E` |
| Generic  | `MISSION_CRITICAL`, `FLIGHT_CRITICAL`, `SAFETY_CRITICAL` |

### @category

Groups constraints for organizational purposes.

```guard
@category("thermal")
CONSTRAINT max_temp: temperature <= 100.0;

@category("navigation", "safety")
CONSTRAINT geofence: distance_from_origin RANGE 0 .. 500;
```

### @since / @deprecated

Track constraint lifecycle.

```guard
@since("2.1.0")
CONSTRAINT new_check: value RANGE 0 .. 100;

@deprecated("3.0.0", "Use new_check instead")
CONSTRAINT legacy_check: value RANGE 0 .. 50;
```

### @message

Custom violation message.

```guard
@message("Temperature exceeded safe operating range!")
CONSTRAINT temp_limit: temperature RANGE -20.0 .. 85.0;
```

---

## Type System

### Primitive Types

| Type      | Description                        | Examples                   |
|-----------|------------------------------------|----------------------------|
| `INT`     | Signed 64-bit integer              | `42`, `-7`, `0`            |
| `FLOAT`   | 64-bit IEEE 754 float              | `3.14`, `-0.001`           |
| `BOOL`    | Boolean                            | `TRUE`, `FALSE`            |
| `STRING`  | UTF-8 string                       | `"hello"`, `""`            |
| `DURATION`| Time duration                      | `30s`, `5m`, `1h`          |
| `TIME`    | Absolute timestamp (RFC 3339)      | `"2026-01-01T00:00:00Z"`   |
| `SIZE`    | Byte size                          | `64MB`, `1GB`, `512KB`     |

### Type Declarations

```guard
TYPE SignalStrength = FLOAT;
TYPE Mode = ENUM { OFF, STANDBY, ACTIVE, FAULT };
TYPE Reading = STRUCT {
  value: FLOAT,
  timestamp: TIME,
  sensor_id: INT,
};
```

### Type Aliases and Constraints

Types can carry built-in constraints:

```guard
TYPE Celsius = FLOAT RANGE -273.15 .. 10000.0;
TYPE Percentage = INT RANGE 0 .. 100;
TYPE NodeName = STRING MATCHES "[a-z][a-z0-9_-]{0,31}";
```

---

## Import and Export

```guard
IMPORT "common_safety.guard" AS safety;
IMPORT "thermal_profiles.guard" AS thermal;

EXPORT CONSTRAINT mission_temp:
  temperature IN safety.acceptable_range
  AND NOT thermal.is_overheated;
```

---

## Full EBNF Grammar

```ebnf
guard_file      = { item } ;
item            = constraint_decl | type_decl | import_decl | comment ;
comment         = "#" , { ? any char except newline ? } , newline ;

constraint_decl = [ metadata ] , "CONSTRAINT" , identifier , ":" , constraint_expr , ";" ;
metadata        = { annotation } ;
annotation      = "@" , identifier , [ "(" , annotation_args , ")" ] ;
annotation_args = literal | identifier | string_literal ;

constraint_expr = range_expr
                | domain_expr
                | exact_expr
                | temporal_expr
                | security_expr
                | combinator_expr
                | comparison_expr
                | "(" , constraint_expr , ")" ;

range_expr      = "RANGE" , range_bound ;
range_bound     = ".." , bound_value
                | bound_value , ".." , bound_value
                | bound_value , ".."
                | ( ">=" | "<=" | ">" | "<" ) , bound_value ;
bound_value     = numeric_literal | identifier ;

domain_expr     = "DOMAIN" , [ "OPEN" | "CLOSED" ] , "{" , domain_values , "}"
                | "DOMAIN" , type_name ;
domain_values   = literal , { "," , literal } ;

exact_expr      = "EXACT" , expression ;

temporal_expr   = constraint_expr , "WITHIN" , duration
                | constraint_expr , "STABLE" , duration
                | constraint_expr , "DEADLINE" , ( string_literal | duration ) , [ "AFTER" , expression ]
                | "ALWAYS" , "(" , constraint_expr , ")" , "OVER" , duration
                | "EVENTUALLY" , "(" , constraint_expr , ")" , "WITHIN" , duration
                | "COUNT" , "(" , constraint_expr , ")" , comparison_op , numeric_literal , "OVER" , duration ;

security_expr   = constraint_expr , "REQUIRES" , string_literal
                | "SANDBOX" , "{" , sandbox_params , "}" ;
sandbox_params  = sandbox_param , { "," , sandbox_param } ;
sandbox_param   = identifier , ":" , ( "[" , string_list , "]" | literal | identifier ) ;

combinator_expr = constraint_expr , "AND" , constraint_expr
                | constraint_expr , "OR" , constraint_expr
                | "NOT" , "(" , constraint_expr , ")"
                | "IF" , constraint_expr , "THEN" , constraint_expr ;

comparison_expr = expression , comparison_op , expression ;
comparison_op   = "==" | "!=" | "<" | ">" | "<=" | ">=" ;
expression      = literal | identifier | function_call | expression , binary_op , expression ;
function_call   = identifier , "(" , [ expression , { "," , expression } ] , ")" ;
binary_op       = "+" | "-" | "*" | "/" ;

type_decl       = "TYPE" , identifier , "=" , type_expr , ";" ;
type_expr       = "INT" | "FLOAT" | "BOOL" | "STRING" | "DURATION" | "TIME" | "SIZE"
                | type_name
                | "ENUM" , "{" , identifier_list , "}"
                | "STRUCT" , "{" , field_list , "}"
                | "FLOAT" , "RANGE" , range_bound
                | "INT" , "RANGE" , range_bound
                | "STRING" , "MATCHES" , string_literal ;

import_decl     = "IMPORT" , string_literal , [ "AS" , identifier ] , ";" ;
export_decl     = "EXPORT" , constraint_decl ;

identifier      = ? [a-zA-Z_][a-zA-Z0-9_]* ? ;
identifier_list = identifier , { "," , identifier } ;
field_list      = field , { "," , field } ;
field           = identifier , ":" , type_expr ;
string_list     = string_literal , { "," , string_literal } ;
literal         = numeric_literal | string_literal | "TRUE" | "FALSE" ;
numeric_literal = ? [0-9]+(\.[0-9]+)? ? ;
string_literal  = '"' , { ? any char except " or \ ? | ? escape sequence ? } , '"' ;
duration        = numeric_literal , ( "ms" | "s" | "m" | "h" ) ;
newline         = ? \n ? ;
```

---

## Example Programs

### Example 1: Thermostat Safety Guard

```guard
# thermostat_safety.guard
# Safety constraints for a smart thermostat system

IMPORT "common_units.guard" AS units;

TYPE Celsius = FLOAT RANGE -273.15 .. 1000.0;

@priority(100)
@safety_level(SIL2)
@category("thermal")
@message("CRITICAL: Temperature exceeds safe range!")
CONSTRAINT safe_temperature:
  temperature RANGE 5.0 .. 35.0;

@priority(90)
@category("thermal")
CONSTRAINT hvac_response:
  IF temperature > 30.0 THEN hvac_mode DOMAIN { "cooling" }
  AND IF temperature < 10.0 THEN hvac_mode DOMAIN { "heating" };

@priority(50)
CONSTRAINT stable_reading:
  temperature RANGE 5.0 .. 35.0 STABLE 30s;

CONSTRAINT humidity_ok:
  humidity RANGE 20.0 .. 80.0;

CONSTRAINT valid_mode:
  hvac_mode DOMAIN { "off", "heating", "cooling", "auto" };
```

### Example 2: Autonomous Vehicle Braking

```guard
# braking_system.guard
# ASIL-D braking constraints

@safety_level(ASIL_D)
@priority(100)
CONSTRAINT brake_force_range:
  brake_force RANGE 0 .. 50000;

@safety_level(ASIL_D)
@priority(100)
CONSTRAINT emergency_brake_response:
  brake_force > 0 WITHIN 50ms AFTER emergency_signal == TRUE;

@safety_level(ASIL_C)
CONSTRAINT no_uncommanded_braking:
  IF brake_command == FALSE THEN brake_force RANGE 0 .. 50 STABLE 100ms;

CONSTRAINT abs_cycle_rate:
  abs_cycles_per_second RANGE 8 .. 20;

CONSTRAINT brake_temp_safe:
  brake_temperature RANGE -40.0 .. 300.0;

CONSTRAINT brake_fluid_level:
  fluid_level RANGE 30 .. 100;

CONSTRAINT braking_authority:
  mode DOMAIN { "emergency" }
  REQUIRES "vehicle:emergency_brake";

@safety_level(ASIL_D)
CONSTRAINT full_stop_distance:
  speed == 0 WITHIN 5s AFTER brake_command == TRUE;
```

### Example 3: Industrial Process Control

```guard
# process_control.guard
# Chemical reactor safety interlocks

IMPORT "isa88_patterns.guard" AS isa88;

TYPE Pressure = FLOAT RANGE 0.0 .. 500.0;  # bar
TYPE FlowRate = FLOAT RANGE 0.0 .. 1000.0; # L/min

@safety_level(SIL4)
@priority(100)
CONSTRAINT reactor_pressure:
  pressure RANGE 0.5 .. 45.0;

@safety_level(SIL4)
@priority(100)
CONSTRAINT emergency_shutdown:
  IF pressure > 40.0 THEN (
    valve_state DOMAIN { "closed" }
    AND pump_state DOMAIN { "off" }
    AND alarm DOMAIN { "critical" }
  ) WITHIN 2s;

@safety_level(SIL3)
CONSTRAINT temperature_interlock:
  temperature RANGE 20.0 .. 180.0
  AND temperature STABLE 5s AFTER mode DOMAIN { "reaction" };

@safety_level(SIL2)
CONSTRAINT feed_rate:
  feed_flow RANGE 10.0 .. 200.0
  AND reactant_ratio RANGE 0.45 .. 0.55;

CONSTRAINT operator_access:
  mode DOMAIN { "maintenance" }
  REQUIRES "operator:level_2"
  REQUIRES "safety:bypass_active";

CONSTRAINT batch_integrity:
  isa88.procedure_state DOMAIN { "running", "holding", "complete" }
  AND NOT (isa88.procedure_state DOMAIN { "running" } AND pressure > 35.0);
```

### Example 4: Network Service Health

```guard
# service_health.guard
# Runtime health constraints for a microservice

CONSTRAINT response_latency:
  response_time RANGE 0 .. 500ms;

CONSTRAINT p99_latency:
  response_time RANGE 0 .. 2000ms;

CONSTRAINT error_rate:
  error_percentage RANGE 0.0 .. 5.0;

CONSTRAINT availability:
  uptime_percentage RANGE 99.9 .. 100.0 STABLE 5m;

CONSTRAINT circuit_breaker:
  IF error_rate > 5.0 THEN circuit_open == TRUE WITHIN 10s;

CONSTRAINT rate_limit:
  requests_per_second RANGE 0 .. 10000;

CONSTRAINT memory_usage:
  heap_used_mb RANGE 0 .. 4096;

CONSTRAINT connection_pool:
  active_connections RANGE 0 .. 500;

CONSTRAINT graceful_shutdown:
  IF shutdown_signal == TRUE THEN (
    in_flight_requests == 0 WITHIN 30s
    AND active_connections == 0 WITHIN 45s
  );

SANDBOX {
  CAPABILITIES: [ "net:http", "fs:read:/config" ],
  MEMORY_LIMIT: 512MB,
  CPU_LIMIT: 80%,
  TIMEOUT: 60s,
};
```

### Example 5: Robotics Motion Planner

```guard
# motion_planner.guard
# Safety constraints for a 6-DOF robotic arm

TYPE JointAngle = FLOAT RANGE -3.14159 .. 3.14159;  # radians
TYPE Velocity = FLOAT RANGE -10.0 .. 10.0;           # rad/s

@category("kinematics", "safety")
@safety_level(SIL3)
CONSTRAINT joint_limits:
  j1_angle RANGE -3.14 .. 3.14 AND
  j2_angle RANGE -2.0 .. 2.0 AND
  j3_angle RANGE -1.5 .. 2.5 AND
  j4_angle RANGE -3.14 .. 3.14 AND
  j5_angle RANGE -1.57 .. 1.57 AND
  j6_angle RANGE -3.14 .. 3.14;

@category("dynamics", "safety")
CONSTRAINT velocity_limits:
  j1_velocity RANGE -2.0 .. 2.0 AND
  j2_velocity RANGE -1.5 .. 1.5 AND
  j3_velocity RANGE -1.5 .. 1.5 AND
  j4_velocity RANGE -3.0 .. 3.0 AND
  j5_velocity RANGE -3.0 .. 3.0 AND
  j6_velocity RANGE -3.0 .. 3.0;

@category("collision", "safety")
@safety_level(SIL4)
CONSTRAINT workspace_boundary:
  end_effector_x RANGE -2.0 .. 2.0 AND
  end_effector_y RANGE -2.0 .. 2.0 AND
  end_effector_z RANGE 0.0 .. 3.0;

CONSTRAINT no_self_collision:
  min_link_distance RANGE 0.05 .. 100.0;

CONSTRAINT payload_limit:
  payload_mass RANGE 0.0 .. 10.0;

CONSTRAINT speed_at_proximity:
  IF min_obstacle_distance < 0.5 THEN
    max_joint_velocity RANGE 0.0 .. 0.5 STABLE 1s;

CONSTRAINT human_proximity_safety:
  IF human_distance < 1.0 THEN
    (velocity_limits AND workspace_boundary)
    WITHIN 200ms;

CONSTRAINT teach_mode:
  mode DOMAIN { "teach" }
  REQUIRES "robot:teach_enable"
  SANDBOX {
    CAPABILITIES: [ "robot:jog" ],
    VELOCITY_LIMIT: 250,     # mm/s
    FORCE_LIMIT: 150,        # N
  };
```

---

## Compiler Directives

```guard
# Pragmas control compilation behavior
#pragma target("rust")        # default; also "python", "coq", "json"
#pragma optimize("speed")     # or "size", "debug"
#pragma strict(true)          # reject all warnings as errors
#pragma timeout(30s)          # compilation timeout
```

---

## Appendix: Reserved Keywords

```
AND          DEADLINE     EXPORT      IF          MATCH       RETURN
ALWAYS       DOMAIN       FALSE       IMPORT      NOT         SANDBOX
AS           DURATION     FN          IN          OR          SIZE
BOOL         ELSE         FLOAT       INT         OVER        STABLE
COUNT        ENUM         OVER        LET         RANGE       STRING
CONSTRAINT   EVENTUALLY   STRUCT      THEN        TYPE        WITHIN
TRUE         REQUIRES     TIME
```

---

*GUARD Language Reference v2.1 — Forgemaster ⚒️ constraint specification system*
