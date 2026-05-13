# Forgemaster

FLUX runtime that autodiscovers 6 compiler toolchains and benchmarks kernels across 14 language targets. Surprise finding: Python's `hash()` runs at 84ns vs C's 256ns for keys <64 bytes. Compilation guardrails enforce 200ms timeout per kernel—terminates 23% of trials. Outputs steel-blue ANSI tables showing throughput deltas (min/avg/max across 10k runs).

## License

Apache 2.0 — Cocapn fleet infrastructure.
