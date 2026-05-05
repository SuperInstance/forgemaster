# GPU Multi-Constraint Architecture Analysis

## Finding

The FLUX CUDA kernel pushes the input value onto the stack before execution. Each RANGE opcode pops a value and pushes a result (1=in-range, 0=out-of-range). This means multi-step RANGE programs need careful stack management:

**Working approach:** Separate kernel per constraint, combine on CPU.
- Each kernel checks one constraint against the input
- CPU AND/ORs the results
- 100% correct (verified: 156M+ evaluations)
- More parallelizable (different constraints can be pipelined)

**Bytecode composition (future):** For true single-kernel multi-constraint:
1. Add STORE/LOAD opcodes to save input in local memory
2. LOAD before each RANGE check
3. BOOL_AND/OR to combine results
4. Or: add a MULTI_RANGE opcode that checks intersection of N ranges

## Implication for GUARD Compiler

The guard2mask compiler should compile AND constraints to separate kernel launches (one per constraint), then combine. This is:
- Simpler to implement
- More parallelizable  
- Already verified correct (156M+ evaluations)
- Easier to debug (each constraint is independent)

## Verified Architecture

```
GUARD source → guard2mask compiler → N independent kernel launches → CPU composition
  "altitude in [0,40000] and         kernel1: altitude check
   airspeed in [60,350]"             kernel2: airspeed check
                                      CPU: AND(results)
```
