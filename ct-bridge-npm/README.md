# @cocapn/ct-bridge

Constraint Theory solver bridge — CSP compilation and FLUX execution for Node.js.

Wraps the Python [`constraint-theory`](https://pypi.org/project/constraint-theory/) package for use in Node.js via a persistent subprocess bridge with JSON-RPC messaging.

## Requirements

- **Node.js** >= 18
- **Python** >= 3.11
- **constraint-theory** pip package: `pip install constraint-theory`

## Installation

```bash
npm install @cocapn/ct-bridge
```

## Quick Start

```typescript
import { CTBridge } from "@cocapn/ct-bridge";

async function main() {
  const ct = new CTBridge();
  await ct.init();

  const solution = await ct.solve(
    ["x", "y", "z"],
    {
      x: { type: "range", min: 1, max: 10 },
      y: { type: "range", min: 1, max: 10 },
      z: { type: "range", min: 1, max: 10 },
    },
    [
      { id: "c1", variables: ["x", "y"], expression: "x + y == 10" },
      { id: "c2", variables: ["y", "z"], expression: "y < z" },
    ],
    "backtracking",
  );

  console.log(solution.assignments); // { x: 1, y: 9, z: 10 } (example)
  console.log(solution.consistent);  // true

  // Verify the solution
  const verification = await ct.verify(solution.assignments, [
    { id: "c1", variables: ["x", "y"], expression: "x + y == 10" },
    { id: "c2", variables: ["y", "z"], expression: "y < z" },
  ]);
  console.log(verification.valid); // true

  ct.destroy();
}
```

## API Reference

### `CTBridge`

Main class. Manages the Python subprocess lifecycle.

#### `new CTBridge(options?)`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `pythonPath` | `string` | `"python3"` | Path to Python binary |
| `callTimeout` | `number` | `30000` | Timeout per call (ms) |
| `maxRestarts` | `number` | `3` | Max auto-restarts on crash |

#### `init(): Promise<void>`

Start the Python bridge process. Call once before any other method.

#### `solve(variables, domains, constraints, method?): Promise<Solution>`

Solve a constraint satisfaction problem.

| Parameter | Type | Description |
|-----------|------|-------------|
| `variables` | `string[]` | Variable names |
| `domains` | `Record<string, Domain>` | Per-variable domains |
| `constraints` | `Constraint[]` | Boolean predicates |
| `method` | `SolveMethod` | Solver strategy (default: `"backtracking"`) |

Returns a `Solution` with `assignments`, `consistent`, and `solveTimeMs`.

**Solver methods:**
- `"backtracking"` — Classic depth-first search with backtracking
- `"forward_checking"` — Backtracking with forward checking
- `"arc_consistency"` — AC-3 preprocessing + backtracking
- `"min_conflicts"` — Local search for optimization problems

#### `compile(problem): Promise<FLUXBytecode>`

Compile a CSP to FLUX bytecode. Returns the full instruction list with variable and constraint maps.

```typescript
const bytecode = await ct.compile({
  variables: ["x", "y"],
  domains: { x: { type: "set", values: [1, 2, 3] }, y: { type: "set", values: [4, 5, 6] } },
  constraints: [{ id: "c1", variables: ["x", "y"], expression: "x != y" }],
});
console.log(bytecode.count);           // instruction count
console.log(bytecode.variableMap);     // { x: 0, y: 1 }
console.log(bytecode.sourceHash);      // deterministic hash
```

#### `verify(solution, constraints): Promise<VerificationResult>`

Check whether a variable assignment satisfies all constraints.

```typescript
const result = await ct.verify(
  { x: 3, y: 7 },
  [{ id: "c1", variables: ["x", "y"], expression: "x + y == 10" }],
);
// result.valid === true
// result.violations === []
```

#### `destroy(): void`

Kill the Python subprocess and clean up.

### Types

```typescript
type Domain =
  | { type: "set"; values: number[] }
  | { type: "range"; min: number; max: number }
  | { type: "range_step"; min: number; max: number; step: number };

interface Constraint {
  id: string;
  variables: string[];
  expression: string;
}

interface Solution {
  assignments: Record<string, number>;
  consistent: boolean;
  solveTimeMs: number;
}

interface VerificationResult {
  valid: boolean;
  violations: string[];
  checkedCount: number;
}
```

## FLUX ISA Overview

FLUX is the intermediate bytecode used by constraint-theory. The opcode space is divided into functional groups:

| Range | Category | Example opcodes |
|-------|----------|-----------------|
| `0x00-0x06` | Control flow | `NOP`, `HALT`, `JMP`, `JZ`, `CALL`, `RET` |
| `0x10-0x15` | Stack / data | `PUSH`, `POP`, `DUP`, `LOAD`, `STORE` |
| `0x20-0x26` | Domain ops | `DOMAIN_INIT`, `DOMAIN_RESTRICT`, `DOMAIN_INTERSECT` |
| `0x30-0x33` | Constraint eval | `CONSTRAINT_LOAD`, `CONSTRAINT_EVAL`, `CONSTRAINT_PROPAGATE` |
| `0x40-0x58` | Arithmetic / logic | `ADD`, `EQ`, `LT`, `AND`, `NOT` |
| `0x60-0x64` | Solver strategy | `BACKTRACK`, `FORWARD_CHECK`, `SELECT_VARIABLE` |
| `0x70-0x72` | Solution | `SOLUTION_EMIT`, `SOLUTION_COUNT`, `VERIFY` |

Each FLUX instruction is `[opcode, ...operands]`. The `compile()` method returns the full instruction list with metadata for debugging and introspection.

## Error Handling

- **Missing Python**: Bridge startup fails with clear error message
- **Missing constraint-theory**: Detected during `init()`, reports installation instructions
- **Call timeout**: Configurable via `callTimeout` option
- **Process crash**: Auto-restart up to `maxRestarts` times
- **Invalid constraints**: Returned as `BridgeError` with code and message

## License

Apache-2.0
