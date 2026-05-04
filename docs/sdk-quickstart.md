# FLUX Constraint Checking SDK Quickstart
Validate business rules, input sanitization, and system state compliance with the standardized FLUX constraint checking SDKs, available across Python, JavaScript/TypeScript, and Rust. No need to write custom validation logic for cross-language rule enforcement—these SDKs handle parsing, bytecode execution, and result formatting for you. All implementations run on the same formally verified FLUX-C bytecode core, ensuring consistent, auditable constraint evaluation across every environment. This guide walks you through a minimal 5-line setup to validate a common user data rule: ensuring a user’s age is between 18 and 120, and their email address contains an `@` symbol.

## Python SDK
The official Python SDK wraps the FLUX-C core for easy integration with data pipelines, Flask/Django APIs, and scripting workflows, with support for both synchronous and asynchronous validation for high-throughput use cases.
### Installation
```bash
pip install constraint-theory
```
### Import Statement
```python
from constraint_theory import FluxChecker, compile_constraints
```
### 5-Line Validation Example
```python
constraint_bytecode = compile_constraints("age >= 18 and age <= 120 and '@' in email")
test_input = {"age": 22, "email": "alice@example.com"}
check_result = FluxChecker.check(constraint_bytecode, test_input)
print(f"Validation Passed: {check_result.passed}")
print(f"Violations Detected: {check_result.violations}")
```
### Sample Output
```
Validation Passed: True
Violations Detected: []
```

## JavaScript/TypeScript SDK
The `@superinstance/ct-bridge` package brings FLUX constraint checking to Node.js, Deno, and TypeScript projects, with full type definitions for IDE autocompletion and static type safety. It mirrors the Python SDK’s API for minimal cognitive overhead across language stacks, and works with both CommonJS and ES module syntax for maximum project compatibility.
### Installation
```bash
npm install @superinstance/ct-bridge
```
### Import Statement
```typescript
import { FluxConstraintChecker, compileFluxConstraints } from "@superinstance/ct-bridge";
```
### 5-Line Validation Example
```typescript
const constraintBytes = compileFluxConstraints("age >= 18 && age <= 120 && email.includes('@')");
const testInput = { age: 22, email: "bob@example.org" };
const checker = new FluxConstraintChecker();
const validationResult = checker.validate(constraintBytes, testInput);
console.log(`JS Check Result: Passed=${validationResult.passed}, Violations=${validationResult.violations.length}`);
```
### Sample Output
```
JS Check Result: Passed=true, Violations=0
```

## Rust SDK
The `constraint-theory-core` crate provides direct, low-level access to the FLUX-C bytecode engine for high-performance, low-latency constraint checking in Rust production services, CLI tools, and WASM modules. Ideal for embedded systems or performance-critical microservices where every millisecond counts, with optional serde support for JSON input handling.
### Installation
```bash
cargo add constraint-theory-core
```
*Note: Run `cargo add serde --features json` to add required JSON serialization support.*
### Import Statement
```rust
use constraint_theory_core::{FluxChecker, compile_constraints};
use serde_json::json;
```
### 5-Line Validation Example
```rust
let constraints = compile_constraints("age >= 18 && age <= 120 && email.contains('@')").unwrap();
let test_input = json!({"age": 22, "email": "charlie@rust-lang.org"});
let checker = FluxChecker::new();
let result = checker.validate(&constraints, &test_input);
println!("Rust Check Result: Passed={}, Issues={}", result.passed, result.issues.len());
```
### Sample Output
```
Rust Check Result: Passed=true, Issues=0
```

All three SDKs use the same verified FLUX-C bytecode under the hood.