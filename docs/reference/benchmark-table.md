# FLUX Constraint Checker Benchmark Comparison Table

| Target                  | Throughput       | Power          | Safe-TOPS/W | Verified               |
|-------------------------|------------------|----------------|-------------|------------------------|
| Python single-thread    | 45M/s            | 15W            | 3M          | differential            |
| C scalar                | 5.2B/s           | 15W            | 347M        | proofs                  |
| C AVX-512 12T           | 5.6B/s           | 65W            | 86M         | proofs                  |
| CUDA RTX 4050           | 665M/s           | 17W            | 39M         | 73M tests               |
| FPGA Artix-7            | 1.7% LUTs        | 120mW          | estimated   | estimated               |
| WebGPU browser          | varies           | GPU power      | 0           | N/A                     |

---

### Note
All CPU and GPU benchmark results were measured on real physical hardware.

---

To save this content to the specified path:
```bash
cat > /home/phoenix/.openclaw/workspace/docs/reference/benchmark-table.md << 'EOF'
# FLUX Constraint Checker Benchmark Comparison Table

| Target                  | Throughput       | Power          | Safe-TOPS/W | Verified               |
|-------------------------|------------------|----------------|-------------|------------------------|
| Python single-thread    | 45M/s            | 15W            | 3M          | differential            |
| C scalar                | 5.2B/s           | 15W            | 347M        | proofs                  |
| C AVX-512 12T           | 5.6B/s           | 65W            | 86M         | proofs                  |
| CUDA RTX 4050           | 665M/s           | 17W            | 39M         | 73M tests               |
| FPGA Artix-7            | 1.7% LUTs        | 120mW          | estimated   | estimated               |
| WebGPU browser          | varies           | GPU power      | 0           | N/A                     |

---

### Note
All CPU and GPU benchmark results were measured on real physical hardware.
EOF
```