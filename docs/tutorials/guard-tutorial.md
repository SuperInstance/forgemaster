# GUARD Constraint DSL: A Progressive Tutorial for Embedded Engineers

If you have spent your career writing C for microcontrollers, the idea of a "domain-specific language" probably sounds like overhead. It is not. GUARD is a declarative constraint language that compiles to FLUX-C bytecode — a compact, deterministic stack-machine program that runs on your target with no operating system, no `malloc`, and no surprises. Think of it as writing requirements that *are* the runtime check.

Why bother? Because safety constraints in embedded systems usually start in a Word document, get re-implemented in Simulink, and then re-coded again in C. By the time the product ships, the three versions have drifted apart. GUARD collapses them into one artifact: a `.guard` file that is readable by safety engineers, compilable to bytecode, and enforceable by a tiny VM that fits alongside your control loop.

This tutorial walks you from a single temperature bound to a full multi-constraint safety program. Each section shows the concept, the GUARD source, the FLUX-C bytecode it produces, and what is happening under the hood. No prior DSL experience is assumed.

---

## 1. Your First Constraint — A Temperature Bound

**Concept.** A range constraint says: "this variable must stay between two numbers." In C you might write:

```c
if (temperature < -40.0f || temperature > 125.0f) {
    enter_safe_state();
}
```

In GUARD you declare the requirement, and the compiler generates the check.

**Code.**

```guard
CONSTRAINT temp_ok: temperature RANGE -40.0 .. 125.0;
```

**Expected FLUX-C Bytecode.**

```
Offset   Opcode     Operands
0        Nop
1        Push       125.0
2        Store      slot 0
3        Push       -40.0
4        Store      slot 1
5        Push       0.0
6        Store      slot 2       # default temperature
7        Trace
8        Load       slot 2       # push temperature
9        Load       slot 0       # push upper bound
10       Lte                     # temperature <= 125.0 ?
11       Assert     id=1         # hard constraint: temp_ok
12       Load       slot 2
13       Load       slot 1       # push lower bound
14       Gte                     # temperature >= -40.0 ?
15       Assert     id=2
16       Nop                     # yield / wait for next cycle
17       Jump       8            # loop forever
```

**Explanation.** FLUX-C is a stack VM. `Push` places an `f64` value on the stack. `Store` pops it into a memory slot (the VM has 256). `Load` pushes a slot back onto the stack. `Lte` pops two values and pushes `1` if the first is less than or equal to the second. `Assert` pops one value; if it is zero, the VM records a constraint violation and halts. The loop at offsets 8–17 executes every control cycle. Your firmware only has to write the live sensor value into slot 2 and call `flux_step()`. The VM does the rest.

---

## 2. Ranges — One-Sided, Exclusive, and Open-Ended

**Concept.** Not every bound has two sides. A motor current might only need an upper limit. An array index must be strictly less than its length. GUARD supports one-sided bounds and exclusive edges without forcing you to remember which comparison operator to use.

**Code.**

```guard
CONSTRAINT motor_current: RANGE <= 15.0;
CONSTRAINT array_index:   RANGE 0 >< length;      # 0 <= index < length
CONSTRAINT ratio:         RANGE >0.0 .. <1.0;     # exclusive on both sides
```

**Expected FLUX-C Bytecode (array_index example).**

```
Offset   Opcode     Operands
0        Push       0.0
1        Store      slot 0       # lower bound (inclusive)
2        Push       0.0
3        Store      slot 1       # default index
4        Trace
5        Load       slot 1       # push index
6        Load       slot 0       # push 0
7        Gte                     # index >= 0 ?
8        Assert     id=1
9        Load       slot 1       # push index
10       Load       slot 2       # push 'length' from host
11       Lt                      # index < length ?
12       Assert     id=2
13       Jump       4
```

**Explanation.** Inclusive bounds use `Gte`/`Lte`. Exclusive bounds use `Gt`/`Lt`. The compiler selects the comparison opcode to match the edge semantics you declared. This eliminates off-by-one bugs at the source: you state the intent (`0 >< length`), and the VM emits the correct comparison. No human has to remember whether to use `<` or `<=` at three in the morning during a board bring-up.

---

## 3. Priorities — Safety Triage

**Concept.** When everything fails at once, you need to know what to fix first. GUARD constraints carry numeric priorities. Higher numbers are checked first, and violation handlers can use the priority to decide whether to log, warn, or halt.

**Code.**

```guard
@priority(100)
@safety_level(SIL2)
@message("CRITICAL: Temperature exceeded safe operating range!")
CONSTRAINT temp_critical: temperature RANGE -40.0 .. 125.0;

@priority(50)
CONSTRAINT temp_warning:  temperature RANGE -20.0 .. 85.0;
```

**Expected FLUX-C Bytecode.**

```
Offset   Opcode     Operands
0        Push       125.0
1        Store      slot 0
2        Push       -40.0
3        Store      slot 1
4        Push       85.0
5        Store      slot 2
6        Push       -20.0
7        Store      slot 3
8        Trace
9        Load       slot 4       # temperature
10       Load       slot 0
11       Lte
12       Assert     id=1         # priority 100
13       Load       slot 4
14       Load       slot 1
15       Gte
16       Assert     id=2         # priority 100
17       Load       slot 4
18       Load       slot 2
19       Lte
20       Assert     id=3         # priority 50
21       Load       slot 4
22       Load       slot 3
23       Gte
24       Assert     id=4         # priority 50
25       Jump       8
```

**Explanation.** The `@priority` annotation does not change the opcode; it changes the **emission order** in the bytecode. The compiler sorts constraints by descending priority before emission, so the critical range is validated before the warning range. If the VM halts on the first violation, the highest-severity fault is always the one reported. The `@safety_level` and `@message` metadata travel in the debug symbol table and appear in the violation log so your fault recorder knows this is a `SIL2` event, not a casual diagnostic.

---

## 4. Temporal Constraints — Time Matters

**Concept.** A value inside its range for one sample means nothing if it has been out of range for the previous hundred samples. Temporal constraints let you say "must hold continuously for ten seconds" or "must become true within fifty milliseconds."

**Code.**

```guard
CONSTRAINT stable_temp:
  temperature RANGE 20.0 .. 25.0 STABLE 10s;

CONSTRAINT brake_response:
  brake_force > 0 WITHIN 50ms AFTER emergency_signal == TRUE;
```

**Expected FLUX-C Bytecode (stable_temp excerpt).**

```
Offset   Opcode     Operands
...
8        Tick                    # push cycle counter
9        Elapsed                 # time since last sample
10       Wait       10ms         # enforce sample period
11       Load       slot 4       # temperature
12       Load       slot 0       # 25.0
13       Lte
14       Load       slot 4
15       Load       slot 1       # 20.0
16       Gte
17       And                     # both bounds true?
18       Store      slot 128     # write to history buffer
19       Call       50           # sub-routine: check 1000-slot ring
...
```

**Explanation.** `STABLE 10s` at a 10 ms sample rate requires 1000 consecutive true samples. The compiler allocates a circular history buffer in slots 128–223 (the temporal range). Each cycle the boolean result of the range check is written to `slot 128 + (cycle % 1000)`. A subroutine iterates over the entire buffer and asserts that every entry is true. `Tick` and `Elapsed` let the VM verify that your host is actually calling it at the declared rate; if the cycle time drifts, `Wait` can trigger a temporal violation. This is all deterministic — no heap, no interrupts, no callback hell. Just a bounded loop you can count cycles on.

---

## 5. Logical Operators — AND, OR, NOT

**Concept.** Real safety rules are rarely one condition. You need "temperature OK AND pressure OK," or "on battery OR on external power," or "NOT in fault mode."

**Code.**

```guard
CONSTRAINT engine_safe:
  temperature RANGE 20.0 .. 90.0
  AND pressure RANGE 1.0 .. 5.0;

CONSTRAINT power_ok:
  source DOMAIN { "battery", "solar" }
  OR voltage RANGE 10.0 .. 14.0;

CONSTRAINT not_overheated:
  NOT (temperature > 90.0 AND duration > 60);
```

**Expected FLUX-C Bytecode (engine_safe).**

```
Offset   Opcode     Operands
...
8        Load       slot 4       # temperature
9        Load       slot 0       # 90.0
10       Lte
11       Load       slot 4
12       Load       slot 1       # 20.0
13       Gte
14       And                     # temp in range?
15       Load       slot 5       # pressure
16       Load       slot 2       # 5.0
17       Lte
18       Load       slot 5
19       Load       slot 3       # 1.0
20       Gte
21       And                     # pressure in range?
22       And                     # both true?
23       Assert     id=1
24       Jump       8
```

**Explanation.** Each comparison leaves a boolean (`1` or `0`) on the stack. The `And` opcode pops two values and pushes their logical conjunction. `Or` and `Not` work the same way. Nesting is free: the stack grows and shrinks with each sub-expression. For embedded engineers, this is equivalent to chaining `&&` and `||` in C, except the compiler guarantees short-circuit evaluation order and you cannot accidentally mix precedence. The implication `IF A THEN B` is syntactic sugar for `NOT A OR B`; the compiler desugars it before bytecode emission.

Because the VM is stack-based, there are no hidden temporaries cluttering your RAM. The stack depth is bounded at compile time, so you can predict worst-case memory usage the same way you would count nested function calls in C.

---

## 6. Multi-Constraint Programs — Putting It All Together

**Concept.** A real device has dozens of constraints: thermal, electrical, mechanical, temporal. GUARD lets you declare types with built-in bounds, attach metadata, and compose constraints into a single program that the VM executes in one shot.

**Code.**

```guard
# thermostat_safety.guard

TYPE Celsius = FLOAT RANGE -273.15 .. 1000.0;

@priority(100)
@safety_level(SIL2)
@category("thermal")
@message("CRITICAL: Temperature exceeds safe range!")
CONSTRAINT safe_temperature:
  temperature RANGE 5.0 .. 35.0;

@priority(90)
CONSTRAINT hvac_response:
  IF temperature > 30.0 THEN hvac_mode DOMAIN { "cooling" }
  AND IF temperature < 10.0 THEN hvac_mode DOMAIN { "heating" };

@priority(50)
CONSTRAINT stable_reading:
  temperature RANGE 5.0 .. 35.0 STABLE 30s;

CONSTRAINT humidity_ok:
  humidity RANGE 20.0 .. 80.0;
```

**Expected FLUX-C Bytecode (main loop).**

```
Offset   Opcode     Operands
0        Push       35.0
1        Store      slot 0
2        Push       5.0
3        Store      slot 1
4        Push       80.0
5        Store      slot 2
6        Push       20.0
7        Store      slot 3
8        Trace
9        Load       slot 32       # temperature (state var)
10       Load       slot 0
11       Lte
12       Load       slot 32
13       Load       slot 1
14       Gte
15       And
16       Assert     id=1          # safe_temperature (SIL2)

17       Load       slot 32
18       Load       slot 0        # 35.0
19       Gt                       # temp > 30 ?
20       Jz         28            # skip if false
21       Load       slot 33       # hvac_mode
22       CheckDomain  mask=0x02   # "cooling" bit
23       Assert     id=2

24       Load       slot 32
25       Load       slot 1        # 5.0
26       Lt
27       Jz         32
28       Load       slot 33
29       CheckDomain  mask=0x01   # "heating" bit
30       Assert     id=3

31       Call       100           # stable_reading temporal sub-routine
32       Load       slot 34       # humidity
33       Load       slot 2
34       Lte
35       Load       slot 34
36       Load       slot 3
37       Gte
38       And
39       Assert     id=4

40       Nop
41       Jump       8
```

**Explanation.** The compiled program follows the FLUX VM memory model: constants live in slots 0–31, state variables updated by your firmware live in slots 32–127, and temporal history buffers occupy 128–223. The compiler assigns `temperature` to slot 32, `hvac_mode` to slot 33, and `humidity` to slot 34. `CheckDomain` validates enum values against a bitmask rather than doing string comparison at runtime — the compiler encodes `"cooling"` and `"heating"` as bits at compile time. The `Jz` (jump-if-zero) opcodes implement conditional implication: if the antecedent is false, the consequent is skipped entirely. This entire loop executes in bounded time with zero dynamic allocation, making it suitable for hard-real-time tasks alongside your motor control loop.

You do not need to call seventeen different check functions from your main loop. You write all constraints into one `.guard` file, compile it, and the VM runs them as a single atomic validation pass. If you add a new sensor next year, you add one line to the GUARD file and recompile. The bytecode layout may change, but your C code does not.

---

## Closing

GUARD does not replace your C code. It replaces the fragile manual bounds checks scattered through it. You write the requirement once, compile it to a small bytecode blob, and link it with the C runtime in `flux-isa-c/`. Your firmware writes sensor values into the VM slots and steps the interpreter. If a constraint fails, you get a precise violation record: constraint name, source location, observed value, and safety level. No more `if (temp > MAX)` copied into seventeen files with seventeen opportunities for drift. The requirement *is* the check.

Start with one range constraint on your most critical sensor. Once you see the VM catch an out-of-bounds value and halt cleanly, add a second constraint, then a third. Within an afternoon you will have a safety envelope that is readable, reviewable, and mechanically enforced — without touching a single line of control code.
