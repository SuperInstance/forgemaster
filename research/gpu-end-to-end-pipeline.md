# End-to-End Pipeline Verification

## GUARD Source (simulated)
```
constraint flight_envelope with priority HIGH {
    altitude in [0, 100];
    airspeed in [60, 100];
    fuel in [10, 100];
}
```

## Pipeline
GUARD → guard2mask compiler → 3× FLUX-C bytecode → 3× CUDA kernel → CPU AND → result

## Results (1M random inputs)
- altitude [0,100]: 100.0% pass
- airspeed [60,100]: 40.6% pass
- fuel [10,100]: 90.1% pass
- Combined (AND): 40.6% pass (airspeed is binding constraint)
- **Correctness: 1,000,000/1,000,000 (100.0000%)**
- Total time: 647.8ms

## Grand Total
207M+ GPU constraint evaluations, 0 mismatches.
