# RISC-V Constraint Coprocessor

Custom XFLUX instruction-set extension for FLUX constraint evaluation.

## Build

```bash
# Native (x86_64 test):
gcc -O2 flux_riscv.c -o flux_riscv && ./flux_riscv

# RISC-V cross-compile:
riscv64-linux-gnu-gcc -O2 -march=rv64gc flux_riscv.c -o flux_riscv_rv64
qemu-riscv64 ./flux_riscv_rv64
```

## Hardware Mode

Add `-DHW_FLUX` to compile with real custom instruction encodings (requires RISC-V hardware with XFLUS coprocessor).
