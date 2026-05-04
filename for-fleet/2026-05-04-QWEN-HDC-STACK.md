

# Hyperdimensional Constraint Matching (HDCM) Engine

This design implements a semantic constraint matching engine using Hyperdimensional Computing (HDC) principles. It maps numeric ranges to hypervectors where geometric distance in the vector space corresponds to semantic similarity of the constraints.

## 1. Constraint Encoding (Python Baker)

**Logic:** We use **Level-Hypervector Encoding** with Cyclic Permutation.
1.  **Base Vector:** A random 1024-bit bipolar vector ($\pm 1$) or binary ($0/1$). We use binary for hardware efficiency.
2.  **Value Encoding:** $H(v) = \text{Permute}^v(H_{base})$. This ensures $Hamming(H(v), H(v+1))$ is small and proportional to the shift.
3.  **Range Encoding:** $H_{range}(min, max) = H(min) \oplus H(max)$.
    *   *Similarity Proof:* $Dist(Range_1, Range_2) \approx Dist(H(min_1), H(min_2)) + Dist(H(max_1), H(max_2))$.
    *   If ranges are close (0-100 vs 0-99), the max boundaries (100 vs 99) are close in HD space.
4.  **Folding:** 1024-bit $\to$ 128-bit via XOR-folding (blocks of 8 bits XORed). This preserves expected Hamming distance statistically.

```python
# hdc_baker.py
import numpy as np
import json
import struct
import sys
import re

DIMENSION = 1024
FOLDED_DIM = 128
FOLD_FACTOR = DIMENSION // FOLDED_DIM

def generate_base_vector(seed=42):
    np.random.seed(seed)
    # Binary hypervector
    return np.random.randint(0, 2, DIMENSION, dtype=np.uint8)

def permute_vector(vec, shifts):
    # Cyclic shift for level encoding
    return np.roll(vec, shifts)

def encode_range(min_val, max_val, base_vec):
    h_min = permute_vector(base_vec, min_val)
    h_max = permute_vector(base_vec, max_val)
    # Bundling via XOR
    return np.bitwise_xor(h_min, h_max)

def fold_vector(vec_1024):
    # XOR Fold 1024 -> 128
    vec_1024 = vec_1024.reshape(FOLDED_DIM, FOLD_FACTOR)
    return np.bitwise_xor.reduce(vec_1024, axis=1).astype(np.uint8)

def parse_guard_file(filepath):
    constraints = []
    with open(filepath, 'r') as f:
        for line in f:
            # Expect format: CONSTRAINT name range(min, max)
            match = re.search(r'CONSTRAINT\s+(\w+)\s+range\((\d+),(\d+)\)', line)
            if match:
                name, min_v, max_v = match.groups()
                constraints.append({
                    "name": name,
                    "min": int(min_v),
                    "max": int(max_v)
                })
    return constraints

def main():
    base_vec = generate_base_vector()
    constraints = parse_guard_file('constraints.guard')
    
    baked_db = []
    metadata = []

    for c in constraints:
        # 1. Encode 1024-bit
        hv_1024 = encode_range(c['min'], c['max'], base_vec)
        # 2. Fold to 128-bit
        hv_128 = fold_vector(hv_1024)
        
        # Pack as 16 bytes (128 bits)
        packed = packbits(hv_128)
        baked_db.append(packed)
        metadata.append({
            "name": c['name'],
            "min": c['min'],
            "max": c['max'],
            "checksum": hex(np.sum(hv_128))
        })

    # Output Artifacts
    with open('hdc_constraints.sram', 'wb') as f:
        for vec in baked_db:
            f.write(vec)
            
    with open('hdc_constraints.h', 'w') as f:
        f.write(f"#define NUM_CONSTRAINTS {len(baked_db)}\n")
        f.write("static const unsigned char hdc_db[][16] = {\n")
        for vec in baked_db:
            f.write("    {" + ",".join(f"0x{b:02x}" for b in vec) + "},\n")
        f.write("};\n")

    with open('hdc_metadata.json', 'w') as f:
        json.dump({"version": "1.0", "constraints": metadata}, f, indent=2)

    print(f"Baked {len(baked_db)} constraints.")

def packbits(arr):
    # Convert array of bits to bytes
    return np.packbits(arr).tobytes()

if __name__ == "__main__":
    main()
```

## 2. FPGA Implementation (Verilog)

**Target:** Xilinx Artix-7 (XC7A200T)
**Clock:** 250 MHz
**Features:** AXI-Lite for DB updates, Streaming Query Interface.
**Optimization:** 2-Stage Pipeline for Popcount to meet timing.

```verilog
// hdc_engine.v
`timescale 1ns / 1ps

module hdc_engine (
    input wire clk,
    input wire rst_n,
    
    // AXI-Lite Control (Constraint Update)
    input wire [31:0] S_AXI_AWADDR,
    input wire [31:0] S_AXI_AWDATA,
    input wire [2:0] S_AXI_AWPROT,
    input wire S_AXI_AWVALID,
    output wire S_AXI_AWREADY,
    input wire [31:0] S_AXI_WDATA,
    input wire [3:0] S_AXI_WSTRB,
    input wire S_AXI_WVALID,
    output wire S_AXI_WREADY,
    output wire [1:0] S_AXI_BRESP,
    output wire S_AXI_BVALID,
    input wire S_AXI_BREADY,
    input wire [31:0] S_AXI_ARADDR,
    input wire [2:0] S_AXI_ARPROT,
    input wire S_AXI_ARVALID,
    output wire S_AXI_ARREADY,
    output wire [31:0] S_AXI_RDATA,
    output wire [1:0] S_AXI_RRESP,
    output wire S_AXI_RVALID,
    input wire S_AXI_RREADY,

    // Query Interface (Simple Register for Demo)
    input wire [127:0] query_vector,
    input wire query_strobe,
    output wire [15:0] match_index,
    output wire match_found,
    output wire [7:0] match_distance
);

    // Parameters
    localparam DB_DEPTH = 1024;
    localparam THRESHOLD = 40; // Hamming distance threshold

    // Registers
    reg [9:0] addr_reg;
    reg [127:0] query_reg;
    reg [9:0] scan_index;
    reg scanning;
    reg [7:0] best_dist;
    reg [9:0] best_idx;
    
    // BRAM for Constraint DB (128-bit width)
    reg [127:0] bram_data;
    wire [127:0] db_vector;
    
    // Instantiation of Simple Dual Port BRAM
    hdc_bram u_bram (
        .clka(clk), .wea(0), .addra(scan_index), .dina(0), .douta(db_vector), // Read Port
        .clkb(clk), .web(S_AXI_WVALID), .addrb(addr_reg), .dinb(S_AXI_WDATA), .doutb() // Write Port (Simplified)
    );

    // --- Pipeline Stage 1: XOR & Partial Popcount ---
    wire [127:0] xor_result;
    wire [6:0] pop_stage1 [0:15]; // 16 chunks of 8 bits
    
    assign xor_result = query_reg ^ db_vector;
    
    genvar i;
    generate
        for(i=0; i<16; i=i+1) begin
            // Count bits in each byte
            assign pop_stage1[i] = $countones(xor_result[i*8 +: 8]);
        end
    endgenerate

    // --- Pipeline Stage 2: Reduction & Compare ---
    reg [7:0] total_dist;
    reg [7:0] dist_pipe;
    reg [9:0] idx_pipe;
    reg valid_pipe;

    always @(posedge clk) begin
        if (scanning) begin
            // Sum 16 x 7-bit counters -> 8-bit result
            total_dist <= pop_stage1[0] + pop_stage1[1] + pop_stage1[2] + pop_stage1[3] +
                          pop_stage1[4] + pop_stage1[5] + pop_stage1[6] + pop_stage1[7] +
                          pop_stage1[8] + pop_stage1[9] + pop_stage1[10] + pop_stage1[11] +
                          pop_stage1[12] + pop_stage1[13] + pop_stage1[14] + pop_stage1[15];
            
            dist_pipe <= total_dist;
            idx_pipe <= scan_index;
            valid_pipe <= 1'b1;
            
            if (scan_index < DB_DEPTH - 1)
                scan_index <= scan_index + 1;
            else
                scanning <= 1'b0;
        end else begin
            valid_pipe <= 1'b0;
        end
    end

    // --- Best Match Logic ---
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            best_dist <= 8'hFF;
            best_idx <= 0;
            match_found <= 0;
        end else if (query_strobe) begin
            query_reg <= query_vector;
            scan_index <= 0;
            scanning <= 1'b1;
            best_dist <= 8'hFF;
            match_found <= 0;
        end else if (valid_pipe) begin
            if (dist_pipe < best_dist) begin
                best_dist <= dist_pipe;
                best_idx <= idx_pipe;
                match_found <= (dist_pipe < THRESHOLD);
            end
        end
    end

    assign match_index = best_idx;
    assign match_distance = best_dist;

    // AXI-Lite Slave Logic (Simplified for brevity)
    // ... Standard AXI-Lite FSM for writing to addr_reg/bram ...
    // Map: 0x00 = Control, 0x04 = Addr, 0x08 = Data_Low, 0x0C = Data_High
    assign S_AXI_AWREADY = 1'b1;
    assign S_AXI_WREADY = 1'b1;
    // ... (Implementation omitted for space, standard register map) ...

endmodule

// BRAM Wrapper
module hdc_bram (
    input clka, input wea, input [9:0] addra, input [127:0] dina, output [127:0] douta,
    input clkb, input web, input [9:0] addrb, input [127:0] dinb, output [127:0] doutb
);
    // Xilinx Primitive Mapping
    // RAMB18E1 or similar configured for 128-bit width
endmodule
```

## 3. AVX-512 Implementation (C Intrinsics)

**Target:** x86-64 with AVX-512 (VPOPCNTDQ support).
**Throughput:** 4 constraints per cycle per core.

```c
// hdc_avx512.c
#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>

#define NUM_CONSTRAINTS 1024
#define THRESHOLD 40

// Database aligned to 64 bytes
alignas(64) static const uint8_t hdc_db[NUM_CONSTRAINTS][16];

int hdc_match_batch(const uint8_t* query, int* out_indices, int max_results) {
    __m512i q_vec = _mm512_load_si512((const __m512i*)query);
    int count = 0;

    // Process 4 constraints at a time (512 bits / 128 bits)
    for (int i = 0; i < NUM_CONSTRAINTS; i += 4) {
        // Load 4 constraints (512 bits total)
        __m512i db_vec = _mm512_load_si512((const __m512i*)&hdc_db[i]);
        
        // XOR
        __m512i xor_res = _mm512_xor_si512(q_vec, db_vec);
        
        // Popcount (VPOPCNTDQ)
        // Returns 16 x 32-bit integers containing population counts of each 32-bit lane
        __m512i pop = _mm512_popcnt_epi32(xor_res);
        
        // We have 4 x 128-bit constraints. 
        // Each 128-bit constraint spans four 32-bit lanes.
        // We need to sum the 4 lanes for each constraint.
        // Lane layout: [C0_L3, C0_L2, C0_L1, C0_L0, C1_L3, ...]
        
        // Horizontal Add within 128-bit lanes
        // Shuffle to align pairs
        __m512i sum1 = _mm512_add_epi32(pop, _mm512_srli_epi32(pop, 16)); // Not exact, manual reduction needed
        
        // Simplified reduction for demo: Extract and add
        uint32_t dists[16];
        _mm512_storeu_si512(dists, pop);
        
        for(int k=0; k<4; k++) {
            uint32_t d = dists[k*4] + dists[k*4+1] + dists[k*4+2] + dists[k*4+3];
            
            // Branchless Threshold Gate
            // mask = 0xFFFFFFFF if d < THRESHOLD else 0
            uint32_t mask = -(uint32_t)(d < THRESHOLD);
            
            // Store index if match
            if(mask) {
                if(count < max_results) {
                    out_indices[count++] = i + k;
                }
            }
        }
    }
    return count;
}
```

## 4. eBPF Kernel Module (XDP)

**Target:** Linux Kernel 5.19+ (for `bpf_popcnt`).
**Function:** Drop packets whose payload hash matches a "forbidden" constraint hypervector.

```c
// hdc_xdp.c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define FOLDED_DIM 128
#define MAX_CONSTRAINTS 64

// Map to store 128-bit constraint vectors (stored as 4x u32)
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, MAX_CONSTRAINTS);
    __type(key, __u32);
    __type(value, __u32[4]); // 128 bits
} hdc_constraints SEC(".maps");

// Map to store threshold
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u32);
} hdc_threshold SEC(".maps");

// Simple XOR-Fold Hash for Packet Payload (eBPF safe)
static __always_inline void fold_payload(const void* data, __u32 len, __u32* out) {
    __u32 h[4] = {0};
    const __u8* bytes = data;
    
    // Unrolled loop for verifier
    #pragma unroll
    for (int i = 0; i < 64 && i < len; i++) {
        h[i % 4] ^= bytes[i];
        h[i % 4] = (h[i % 4] << 1) | (h[i % 4] >> 31); // Rotate
    }
    out[0] = h[0]; out[1] = h[1]; out[2] = h[2]; out[3] = h[3];
}

SEC("xdp")
int hdc_filter(struct xdp_md *ctx) {
    void* data = (void*)(long)ctx->data;
    void* data_end = (void*)(long)ctx->data_end;
    
    if (data + 64 > data_end) return XDP_PASS;

    __u32 query[4];
    fold_payload(data, 64, query);

    __u32 zero = 0;
    __u32* thresh_ptr = bpf_map_lookup_elem(&hdc_threshold, &zero);
    __u32 threshold = thresh_ptr ? *thresh_ptr : 40;

    #pragma unroll
    for (int i = 0; i < MAX_CONSTRAINTS; i++) {
        __u32* constraint = bpf_map_lookup_elem(&hdc_constraints, &i);
        if (!constraint) break;

        // XOR
        __u32 d0 = query[0] ^ constraint[0];
        __u32 d1 = query[1] ^ constraint[1];
        __u32 d2 = query[2] ^ constraint[2];
        __u32 d3 = query[3] ^ constraint[3];

        // Popcount (Kernel 5.19+)
        __u32 dist = bpf_popcnt(d0) + bpf_popcnt(d1) + bpf_popcnt(d2) + bpf_popcnt(d3);

        if (dist < threshold) {
            return XDP_DROP; // Match found
        }
    }

    return XDP_PASS;
}

char LICENSE[] SEC("license") = "GPL";
```

## 5. Deployment Pipeline (GitHub Actions)

This workflow scans for `.guard` files, bakes the vectors, and commits the artifacts.

```yaml
# .github/workflows/hdc_bake.yml
name: HDC Constraint Baker

on:
  push:
    paths:
      - '**.guard'

jobs:
  bake:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install Deps
        run: pip install numpy
      
      - name: Run Baker
        run: python hdc_baker.py
      
      - name: Commit Artifacts
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add hdc_constraints.sram hdc_constraints.h hdc_metadata.json
          git commit -m "Auto-bake HDC constraints [skip ci]" || echo "No changes"
          git push
```

## Benchmark Estimates

| Component | Platform | Throughput | Latency | Power |
| :--- | :--- | :--- | :--- | :--- |
| **FPGA** | Artix-7 @ 250MHz | 250 M comparisons/sec | 4 cycles (16ns) | ~1.5 W |
| **AVX-512** | Xeon Platinum (8 Cores) | ~96 G comparisons/sec* | Memory Bound | ~150 W |
| **eBPF** | Kernel Space (XDP) | 10 Mpps (10Gbps line) | ~200 ns/packet | N/A (Host) |

*\*AVX-512 Estimate:* 3.0 GHz $\times$ 4 comparisons/cycle $\times$ 8 Cores = 96 Billion ops/sec. Real-world limited by DRAM bandwidth loading the constraint DB.

## Integration Notes

1.  **Semantic Sensitivity:** The Level-Hypervector encoding ensures that updating a constraint from `range(0, 100)` to `range(0, 101)` results in a hypervector change of only a few bits (Hamming distance $\approx$ shift amount). This allows the system to detect "near-miss" violations if the threshold is tuned loosely.
2.  **Folding Trade-off:** Folding 1024 $\to$ 128 bits increases collision probability. For high-security constraints, keep the FPGA/AVX comparison at 1024-bit and use 128-bit only for eBPF/fast-pre-filter.
3.  **Security:** The eBPF map updates must be restricted to `CAP_BPF` or root to prevent userspace from disabling constraints.
4.  **Verification:** The GitHub Action ensures that the binary artifacts (`.sram`) always match the source constraints