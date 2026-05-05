# Write Your First Constraint — 5-Minute Quickstart

## What You'll Learn

In 5 minutes you'll write a safety constraint, compile it to bytecode, and run it on the FLUX constraint VM. No installation needed — use the playground.

## The Problem

You're building an autonomous drone. The drone's AI model outputs a velocity command every frame. But sometimes the AI says "go 500 km/h in a residential zone." That's a constraint violation — the drone should never exceed 50 km/h near buildings.

Software guards work... until a bit flips, an adversarial input sneaks through, or someone deploys a model update without testing. FLUX enforces constraints at a level that can be formally verified and hardware-enforced.

## Step 1: Write the Constraint

Open the [FLUX Playground](/playground) and type:

```guard
constraint drone_speed @priority(HARD) {
    range(0, 50)
}
```

This says: "the drone speed must always be between 0 and 50 km/h." The `@priority(HARD)` means this constraint can never be relaxed.

## Step 2: Watch It Compile

Click **Compile →**. The GUARD compiler translates your constraint to FLUX bytecode:

```
1D 00 32    BITMASK_RANGE 0 50
1B          ASSERT
1A          HALT
20          GUARD_TRAP
```

4 instructions. 8 bytes. This is the entire safety program. It fits in a single LUT on an FPGA.

## Step 3: Test With Safe Input

Set **Input Value** to `35` and click **▶ Execute**:

```
✅ ALL CONSTRAINTS PASSED
Gas: 4 / 1000 used
BITMASK_RANGE 0 50 → IN RANGE
ASSERT → PASS
HALT
```

The VM checked: is 35 between 0 and 50? Yes. Pass.

## Step 4: Test With Unsafe Input

Change the input to `200` and run again:

```
❌ FAULT: AssertFailed
Gas: 3 / 1000 used
BITMASK_RANGE 0 50 → OUT OF RANGE
ASSERT → FAULT
```

The AI said "go 200 km/h." The constraint VM said "no." The output is blocked.

## Step 5: Add More Constraints

Real systems have multiple constraints. Let's add a thermal budget:

```guard
constraint drone_speed @priority(HARD) {
    range(0, 50)
    thermal(5.0)
}
```

Click **Compile →** again:

```
1D 00 32    BITMASK_RANGE 0 50
1B          ASSERT
00 05       PUSH 5
24          CMP_GE
1B          ASSERT
1A          HALT
20          GUARD_TRAP
```

Now the VM checks two things: speed range AND thermal budget. Both must pass for the output to reach the actuators.

## What Just Happened

1. You wrote a **human-readable constraint** in GUARD DSL
2. The compiler translated it to **machine-executable bytecode** (FLUX)
3. The VM **proved the output was safe** or **blocked it with a fault**
4. The fault is **latching** — once triggered, the system enters safe state until reset

## Install Locally

Want to run this on your own machine?

```bash
# Rust
cargo add flux-vm
cargo add guard2mask

# Python
pip install flux-asm
pip install safe-tops-w
```

```rust
use flux_vm::FluxVM;

let mut vm = FluxVM::new(1000);
let bytecode = [0x1D, 0, 50, 0x1B, 0x1A]; // BITMASK_RANGE 0 50 ASSERT HALT
vm.execute(&bytecode, 100).unwrap();
```

## Next Steps

- [Temporal Constraints](/learn/temporal) — handle timeouts and rate-of-change
- [Multi-Agent Delegation](/learn/delegation) — agents checking each other's outputs
- [Hardware Implementation](/learn/hardware) — deploy to FPGA or ASIC
- [Formal Verification](/learn/formal) — prove your constraints are correct
- [Safe-TOPS/W Benchmark](/benchmark) — compare certified vs uncertified hardware

## The 30-Second Version

```
GUARD → compile → FLUX bytecode → VM execution → PASS or FAULT
```

That's it. Safety constraints as code. Formally verifiable. Hardware-enforceable. Open source.
