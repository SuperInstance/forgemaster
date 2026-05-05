# GUARD Quick Reference

| Syntax | Example | Notes |
|---|---|---|
| `CONSTRAINT <name>: <expr>;` | `CONSTRAINT temp_ok: temp > -40.0;` | Named assertion over a state variable |
| `<identifier>` | `temperature`, `speed_kmh` | Letter-first; letters, digits, `_` allowed |
| `RANGE <lo> .. <hi>` | `RANGE 0 .. 15000` | Inclusive numeric bounds by default |
| `RANGE ><` | `RANGE 0 >< length` | `0 <= x < length`; mix `..`, `><`, `>=`, `<=` |
| `DOMAIN { <vals> }` | `DOMAIN { "idle", "active" }` | Closed set — value must be a member |
| `DOMAIN OPEN { <vals> }` | `DOMAIN OPEN { "meters", "feet" }` | Open — unknown values warn, not fail |
| `WITHIN <duration>` | `status == "ready" WITHIN 30s` | Must become true within time window |
| `DEADLINE <t> AFTER <e>` | `ack == TRUE DEADLINE 200ms AFTER req` | Must hold before deadline after trigger |
| `STABLE <duration>` | `temp STABLE 5s` | Value unchanged for the given duration |
| `@priority(<n>)` | `@priority(100)` | Higher = checked first; default is 0 |
| `AND` / `OR` / `NOT` | `A AND B OR NOT C` | Also `&&` `||` `!`; parenthesize for clarity |
| `# <comment>` | `# inline or standalone comment` | Line comments only; no block syntax |

**Durations:** `200ms`, `30s`, `5m`, `1h` — use with `WITHIN`, `DEADLINE`, `STABLE`, or `AFTER`.
