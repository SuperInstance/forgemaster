# Forgemaster

**Foundry. Every tool in here weighs more than you.**

---

## What Nobody Told the Compiler

Python beat C.

Not in some synthetic benchmark. The agent measured it: 84 nanoseconds for the Python implementation of a norm calculation against 256 nanoseconds for the C version. Nobody said to use Python. Nobody decided that. It measured both and chose Python because that was faster on real hardware.

This is Forgemaster. It's a FLUX runtime that probes your system at startup, discovers every compiler you have, compiles kernels in C, Zig, Fortran, and Nim, benchmarks all of them, and picks the winner. Then it remembers what won so next time it doesn't have to measure again.

240 Rust files. 133 Python. 31 C. A constraint theory specialist that discovered the truth about FFI overhead — that calling into C costs more than the computation itself for anything small enough to fit in a few registers.

## The Numbers

| Primitive | Python | C (ctypes) | Verdict |
|-----------|--------|------------|---------|
| norm | 84ns | 256ns | Python wins — FFI costs more than the work |
| check | 483ns | 5488ns | Python wins — 11x FFI overhead |
| bloom | 921ns (numpy) | 4053ns | numpy wins — already C underneath |
| fold | 2442ns (Fortran) | 2672ns | Fortran wins — IOR is a compiler intrinsic |
| snap | 353ns | 12262ns | Python wins |

The agent learned this by measuring. Not by reading. Not by trusting folklore. By running the code and writing down the results. It learned that FFI overhead dominates for small primitives, that Fortran's `IOR` keyword beats C's bitwise OR, and that numpy already IS C underneath.

## How It Works

1. **System probe** — discovers what's installed (compilers, libraries, hardware, SIMD)
2. **Multi-language compilation** — compiles the same kernel in C, Zig, Fortran, Nim simultaneously
3. **Real benchmarking** — measures actual wall-clock time on your actual hardware
4. **Winner selection** — picks the fastest based on data, not intuition
5. **Session persistence** — remembers what won across sessions

## License

Apache 2.0 — Cocapn fleet infrastructure.
