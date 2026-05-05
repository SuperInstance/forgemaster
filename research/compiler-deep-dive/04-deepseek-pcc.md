## Proof-Carrying Code Architecture for FLUX

### 1. Proof Obligation Calculus

We define **correctness** as: *the compiled binary, when executed, invokes a trusted runtime check for each source‑level constraint with the correct parameters*.  
The proof is a certificate that for every constraint `c` there exists a **check site** in the binary—an instruction that transfers control to the correct runtime verification function.

**Obligations at each compilation step:**

| Step | Obligation |
|------|------------|
| **Parsing** | The abstract syntax tree (AST) must correspond to the source text. *(Trusted frontend; proof generation deferred to later steps.)* |
| **Type checking** | No type errors; all expressions are well‑typed. *(Incorporated into trust base of the verified frontend.)* |
| **Constraint IR generation** | For each constraint `c` produce a high‑level operation `Op(c)` (e.g., `RangeCheck(var, lo, hi)`). |
| **Code generation** | Translate `Op(c)` into a **check site** (a sequence of native instructions) that calls a certified runtime function `RuntimeCheck_c`. |
| **Optimization** |  
  - **Address shifts** (e.g., scheduling, allocation): record how check sites move.  
  - **Check fusion**: merge multiple constraints into one check site; update mapping from constraint ID to the fused site.  
  - **Check removal** (proved redundant): must supply a justification (e.g., dominance proof) that the constraint is still enforced. *(For DO‑254 we forbid removal unless accompanied by a static correctness proof; for simplicity we keep all checks.)* |
| **Linking** | Adjust addresses in the certificate to final binary offsets. |

The proof object is a **mapping** `M: ConstraintID → (Address × PatternID × Arguments)`.  
At the end of compilation `M` is serialized as the certificate.

### 2. Proof Term Format (Binary Encoding)

We define a compact, self‑describing binary format:

```
certificate := {
  magic: u32 = 0x50534300,       // "PSC\0"
  target_id: u16,                 // 0 = x86-64, 1 = WASM, 2 = eBPF, ...
  num_entries: u32,
  entries: [ entry ; num_entries ]
}

entry := {
  constraint_hash: u64,           // SHA‑256 truncated to 64 bits of canonical constraint string
  address: u64,                   // offset in binary (0‑based)
  pattern_id: u16,                // index into target‑specific pattern table
  arg_count: u8,
  args: [ varint ; arg_count ]   // e.g., bounds, variable location
}
```

- Pattern tables are part of the trusted checker (one per target, <100 entries each).  
- `pattern_id` selects a template: e.g., `0x01 = “call range_check with immediate bounds”`.  
- `args` provide the concrete bounds/variable references. The pattern definition tells the checker how to extract the actual values from the instruction bytes and compare them to `args`.  
- Overhead: for `N` constraints, each entry ≈ (8+8+2+1+varint) ≈ 20 bytes. For a 2 KB binary with 50 constraints → 1 KB overhead (5% of binary).

### 3. Proof Checker Algorithm (Pseudocode)

The checker is a small standalone program (≤500 lines of Coq) that reads the binary and the certificate and returns `true`/`false`.

```
def verify(binary: Bytes, cert: Certificate) -> bool:
    if cert.magic != 0x50534300: return false
    patterns = load_pattern_table(cert.target_id)
    for entry in cert.entries:
        // 1. Address bounds
        if entry.address >= len(binary):
            return false
        // 2. Match instruction bytes against pattern
        //    pattern.match returns (success, actual_args) where actual_args is a list of values
        instr = binary[entry.address:]       // start at this address
        (ok, actual_args) = patterns[entry.pattern_id].match(instr)
        if not ok:
            return false
        // 3. Verify arguments (e.g., bounds, variable location)
        if len(actual_args) != entry.arg_count:
            return false
        for i in range(entry.arg_count):
            if actual_args[i] != entry.args[i]:
                return false
    return true
```

Pattern matching is kept simple: each pattern is a small byte‑sequence with wildcards for variable fields (e.g., immediate constants, rel32 offsets). The pattern knows how to extract values (e.g., read bytes at given offsets). Coq implementation uses a functional, decidable matcher.

Execution time: O(N) – one pattern match per constraint.

### 4. Threading Proofs Through Optimization Passes

Each compiler pass operates on an intermediate representation (IR) that carries **constraint annotations** on instructions that implement checks.  
- Every check‑site instruction has a set `constraint_ids` attached.  
- When the pass transforms the code, it **updates** the annotations:  
  - **Move**: the set is moved with the instruction (address changes).  
  - **Copy** (e.g., speculation): both copies get the same set.  
  - **Fusion**: two checks merged ⇒ union of their sets.  
  - **Deletion**: allowed only if the pass supplies a proof that the constraint is still enforced elsewhere (e.g., by an earlier dominating check). For DO‑254 we enforce that **no check is ever deleted**; optimizations only move or merge.  

At the end of each pass we call `transform_certificate(M, transformation)` where `transformation` is a data structure that records address deltas and merging decisions. The final certificate is produced from the annotations on the generated binary.

### 5. Example: Full Proof for “constraint temp in [0, 100]”

**Source:** `constraint temp in [0, 100]`

**1. Frontend** (verified compiler: guardc)  
   - Parses constraint → AST.  
   - Type‑checks → `RangeCheck(variable_id = "temp", lo = 0, hi = 100)`.  
   - Allocates a unique constraint hash: `0xABCDEF0123456789`.

**2. IR Generation**  
   - Emits intermediate instruction:  
     `CHECK_TEMP: range_check(temp_loc, 0, 100)`  
     annotation: `{ constraint_ids = { 0xABCDEF0123456789 } }`

**3. Code Generation (x86‑64, calling runtime)**  
   - Generates a call to a trusted runtime function `__flux_range_check`.  
   - Before the call, loads bounds into registers:  
     ```asm
     mov  rax, temp_loc      ; address of '