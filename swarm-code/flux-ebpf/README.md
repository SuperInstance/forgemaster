# eBPF Constraint Filter

Enforces safety constraints at the Linux kernel level using eBPF (BPF CO-RE).

## Build

```bash
clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -c flux_ebpf.c -o flux_ebpf.o
```

## Load

```bash
sudo bpftool prog load flux_ebpf.o /sys/fs/bpf/flux_prog type tracepoint
```

## Requirements

- Linux kernel >= 5.8 with BTF enabled
- `libbpf-dev`, `clang`, `llvm`
- Root/sudo for loading BPF programs
