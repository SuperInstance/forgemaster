# GUARD Constraint DSL — Quick Reference Card

| Syntax | Example | Description |
|--------|---------|-------------|
| `# comment` | `# max temp: 85°C` | Line comment; ignored by compiler. |
| `CONSTRAINT <name>: <expr>;` | `CONSTRAINT max_temp: temp RANGE 0 .. 85;` | Declare a named constraint. |
| `TYPE <name> = <type>;` | `TYPE Celsius = FLOAT RANGE -40 .. 125;` | Bind a type alias with optional range. |
| `LET <id> = <expr> IN <expr>` | `LET limit = 2 * base IN x RANGE 0 .. limit;` | Local variable binding. |
| `RANGE <low> .. <high>` | `pressure RANGE 0.0 .. 300.0;` | Inclusive numeric range check. |
| `RANGE >= <low>` | `speed RANGE >= 0;` | One-sided lower bound only. |
| `DOMAIN { <vals> }` | `mode DOMAIN { "idle", "active" };` | Value must belong to enumerated set. |
| `DOMAIN <type>` | `name DOMAIN STRING;` | Value must match primitive type domain. |
| `WITHIN <duration>` | `ready == TRUE WITHIN 30s;` | Property must become true before time expires. |
| `STABLE <duration>` | `altitude RANGE 0 .. 1 STABLE 10s;` | Property must hold continuously for duration. |
| `DEADLINE <time> AFTER <event>` | `rsp == TRUE DEADLINE 200ms AFTER req;` | Property must hold before deadline after event. |
| `@priority(HIGH)` | `@priority(HIGH) CONSTRAINT ...` | High runtime triage priority (checked first). |
| `@priority(MEDIUM)` | `@priority(MEDIUM) CONSTRAINT ...` | Medium runtime triage priority. |
| `@priority(LOW)` | `@priority(LOW) CONSTRAINT ...` | Low runtime triage priority (checked last). |
| `AND` | `x RANGE 0 .. 10 AND y RANGE 0 .. 5;` | Conjunction: all sub-constraints must hold. |
| `OR` | `a DOMAIN {"x"} OR b DOMAIN {"y"};` | Disjunction: at least one must hold. |
| `NOT` | `NOT (temp > 90 AND duration > 60);` | Negation: sub-constraint must not hold. |
| `IF ... THEN ...` | `IF temp > 80 THEN fan RANGE 80 .. 100;` | Implication sugar for `NOT A OR B`. |

**Units:** `ms`, `s`, `m`, `h` for time; `KB`, `MB`, `GB` for size.  
**Bounds:** Inclusive by default; use `<` or `>` for exclusive (e.g., `RANGE >0 .. <1`).  
**Nesting:** Parentheses group sub-expressions arbitrarily deep.

---
*GUARD v2.1 — Forgemaster constraint specification system*
