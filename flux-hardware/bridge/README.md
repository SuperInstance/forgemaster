# flux-bridge

**FLUX-X ↔ FLUX-C TrustZone-style bridge protocol.**

Connects the extended instruction set (FLUX-X, 247 opcodes, register machine) to the constraint enforcement ISA (FLUX-C, 43 opcodes, stack machine) via a secure, one-way bridge modeled on ARM TrustZone SMC.

## Architecture

```
FLUX-X (247 opcodes, registers R0-R15)
  │
  ├── CONSTRAINT_CHECK ──→ FLUX-C (43 opcodes, 256-byte stack)
  │                         ├── Executes constraint bytecode
  │                         ├── Gas-bounded (no infinite loops)
  │                         └── Returns Pass / Fail(fault)
  │
  └── On Fail → Safe State Transition
      ├── HaltAndClockGate (range/whitelist/bitmask violations)
      ├── FallbackMode (thermal/sparsity)
      └── WarmReset (gas exhaustion, stack corruption)
```

## Security Properties

- **One-way:** FLUX-C cannot call back into FLUX-X
- **Locked by default:** Bridge cannot be unlocked at runtime
- **Atomic:** No interleaving during context switch
- **Auditable:** All bridge calls logged with full context
- **Gas-bounded:** FLUX-C execution always terminates

## Usage

```rust
use flux_bridge::{FluxBridge, BridgeConfig, BridgeResult};

let mut bridge = FluxBridge::new(BridgeConfig::default());
let registers = [0u64; 16];
let constraint_bytecode = vec![0x1A]; // HALT = pass

match bridge.constraint_check(&registers, 0, 1, &constraint_bytecode) {
    BridgeResult::Pass => println!("Constraint satisfied"),
    BridgeResult::Fail(fault) => println!("VIOLATION: {:?}", fault),
}
```

## Fault Codes

| Fault | Safe State | Description |
|-------|-----------|-------------|
| RangeViolation | HaltAndClockGate | Value outside [min, max] |
| WhitelistViolation | HaltAndClockGate | Value not in allowed set |
| BitmaskViolation | HaltAndClockGate | Bit pattern invalid |
| ThermalExceeded | FallbackMode | Power budget exceeded |
| SparsityInsufficient | FallbackMode | Too few active neurons |
| AssertFailed | HaltAndClockGate | Generic assertion |
| GasExhausted | WarmReset | Execution did not terminate |
| StackCorruption | WarmReset | Stack integrity check failed |

## License

MIT OR Apache-2.0
