/// constraint_compute.wgsl - WebGPU compute shaders for Penrose Memory Palace
///
/// Three compute shaders:
///   1. eisenstein_snap: Snap Cartesian coords to Eisenstein lattice
///   2. dodecet_encode: Pack 12 constraint states into bitfield
///   3. tiered_constraint: Run 3-tier constraint check on tile batches
///
/// Each shader processes workgroups of 64 invocations.

// ============================================================================
// Shared structures (defined as WGSL structs)
// ============================================================================

struct Tile {
    x: i32,
    y: i32,
    state: i32,
    color: i32,
}

struct ConstraintResult {
    // Bitfield result byte (expanded to u32 for alignment)
    result: u32,
    // Violation counts per tier
    tier1_violations: u32,
    tier2_violations: u32,
    tier3_violations: u32,
    // Padding to 16 bytes
    _pad: u32,
}

// ============================================================================
// Shader 1: Eisenstein Snap Compute Shader
// ============================================================================
//
// Reads Cartesian (x, y) from tiles[global_id], writes Eisenstein (a, b)
// back to state/color fields.
//
// Workgroup size: 64
// Dispatch: ceil(tile_count / 64) workgroups

@group(0) @binding(0) var<storage, read_write> tiles: array<Tile>;
@group(0) @binding(1) var<storage, read_write> results: array<ConstraintResult>;

// Constants for Eisenstein transformation
const INV_SQRT3_1000: i32 = 577;        // round(1000/√3)
const TWO_OVER_SQRT3_1000: i32 = 1155;   // round(2000/√3)
const SCALE: i32 = 1000;

// Fixed-point round helper
fn round_fixed(val: i32) -> i32 {
    if (val < 0) {
        return -((-val + SCALE / 2) / SCALE);
    }
    return (val + SCALE / 2) / SCALE;
}

// Eisenstein norm squared: N(a + bω) = a² - ab + b²
fn eisenstein_norm_sq(a: i32, b: i32) -> i32 {
    return a * a - a * b + b * b;
}

@compute @workgroup_size(64)
fn eisenstein_snap(
    @builtin(global_invocation_id) global_id: vec3<u32>,
    @builtin(num_workgroups) num_groups: vec3<u32>,
) {
    let idx = global_id.x;
    let tile_count = num_groups.x * 64u;

    if (idx >= tile_count) {
        return;
    }

    // Only snap tiles that haven't been snapped yet
    // (heuristic: if state == 0 and color == 0, it's a raw Cartesian coord)
    if (tiles[idx].state != 0 || tiles[idx].color != 0) {
        return;
    }

    let x = tiles[idx].x;
    let y = tiles[idx].y;

    // Convert to Eisenstein coordinates using fixed-point arithmetic
    let b_float = (y * TWO_OVER_SQRT3_1000) / 100;
    let a_float = (x * 100 + y * INV_SQRT3_1000) / 100;

    let a_round = round_fixed(a_float * SCALE);
    let b_round = round_fixed(b_float * SCALE);

    // Search nearest 7 lattice points for best fit
    var best_norm: i32 = 2147483647;  // INT32_MAX
    var best_a: i32 = a_round;
    var best_b: i32 = b_round;

    // Unrolled 3x3 search (skipping unnecessary checks)
    for (var da = -1; da <= 1; da++) {
        for (var db = -1; db <= 1; db++) {
            let test_a = a_round + da;
            let test_b = b_round + db;
            let norm = eisenstein_norm_sq(test_a, test_b);
            if (norm < best_norm) {
                best_norm = norm;
                best_a = test_a;
                best_b = test_b;
            }
        }
    }

    // Store Eisenstein coordinates in state/color fields
    tiles[idx].state = best_a;
    tiles[idx].color = best_b;
}

// ============================================================================
// Shader 2: Dodecet Encode Compute Shader
// ============================================================================
//
// Reads 12 consecutive tiles starting at workgroup_id * 12,
// packs their states into a 24-bit dodecet value.
//
// Workgroup size: 64 (but only processes 12 tiles per workgroup)
// Dispatch: ceil(tile_count / 12) workgroups

@compute @workgroup_size(64)
fn dodecet_encode_shader(
    @builtin(global_invocation_id) global_id: vec3<u32>,
    @builtin(workgroup_id) wg_id: vec3<u32>,
) {
    // Each workgroup processes one dodecet (12 tiles)
    let dodecet_id = wg_id.x;
    let base_tile = dodecet_id * 12u;

    // Only one invocation per workgroup does the encoding
    if (global_id.x != base_tile) {
        return;
    }

    var packed: u32 = 0u;
    for (var i = 0u; i < 12u; i++) {
        let state = u32(tiles[base_tile + i].state) & 3u;
        packed |= state << (i * 2u);
    }

    // Store result in the results array
    results[dodecet_id].result = packed;
}

// ============================================================================
// Shader 3: 3-Tier Constraint Check Compute Shader
// ============================================================================
//
// Runs the full 3-tier constraint check on a tile array.
// Uses workgroup-level reductions for efficiency.
//
// Workgroup size: 64
// Dispatch: ceil(tile_count / 64) workgroups
//
// Tier 1: Local - adjacent tiles must have different colors (Admit 432)
// Tier 2: Regional - cluster parity (even sum mod 2), density [1,3]
// Tier 3: Global - non-negative states, even total parity

// Workgroup shared memory for reductions
var<workgroup> wg_tier1_fail: atomic<u32>;
var<workgroup> wg_tier2_fail: atomic<u32>;
var<workgroup> wg_tier3_fail: atomic<u32>;
var<workgroup> wg_state_sum: atomic<i32>;
var<workgroup> wg_tile_count: u32;

@compute @workgroup_size(64)
fn tiered_constraint(
    @builtin(global_invocation_id) global_id: vec3<u32>,
    @builtin(local_invocation_id) local_id: vec3<u32>,
    @builtin(workgroup_id) wg_id: vec3<u32>,
    @builtin(num_workgroups) num_groups: vec3<u32>,
) {
    // First invocation initializes shared memory
    if (local_id.x == 0u) {
        atomicStore(&wg_tier1_fail, 0u);
        atomicStore(&wg_tier2_fail, 0u);
        atomicStore(&wg_tier3_fail, 0u);
        atomicStore(&wg_state_sum, 0);
    }

    // Barrier to ensure initialization is visible
    workgroupBarrier();

    let idx = global_id.x;
    let tile_count = num_groups.x * 64u;

    if (idx >= tile_count) {
        return;
    }

    let tile = tiles[idx];

    // === Tier 1: Local ===
    // Check if this tile has the same color as its neighbor
    if (idx + 1u < tile_count) {
        let next_tile = tiles[idx + 1u];
        if (tile.color == next_tile.color) {
            atomicAdd(&wg_tier1_fail, 1u);
        }
    }

    // === Tier 3: Global (per-tile checks) ===
    if (tile.state < 0) {
        atomicAdd(&wg_tier3_fail, 1u);
    }

    // Accumulate state sum (barrier needed before tier2 cluster check)
    atomicAdd(&wg_state_sum, tile.state);

    // Barrier: all tiles in workgroup must complete state accumulation
    workgroupBarrier();

    // === Tier 2: Regional (cluster-based) ===
    // Last invocation in each cluster of 4 checks cluster constraints
    let cluster_base = (idx / 4u) * 4u;
    let cluster_offset = idx - cluster_base;

    // Thread 3 in each cluster (last of the 4) runs the check
    if (cluster_offset == 3u && idx < tile_count) {
        var state_sum: i32 = 0;
        var occupied: u32 = 0;

        for (var j = 0u; j < 4u; j++) {
            if (cluster_base + j < tile_count) {
                let t = tiles[cluster_base + j];
                state_sum += t.state;
                if (t.state != 0) {
                    occupied++;
                }
            }
        }

        // Parity check: state sum must be even
        if ((state_sum & 1) != 0) {
            atomicAdd(&wg_tier2_fail, 1u);
        }

        // Density check: occupied in [1, 3]
        if (occupied < 1u || occupied > 3u) {
            atomicAdd(&wg_tier2_fail, 1u);
        }
    }

    // Final barrier
    workgroupBarrier();

    // First invocation writes workgroup result
    if (local_id.x == 0u) {
        let tier1_fails = atomicLoad(&wg_tier1_fail);
        let tier2_fails = atomicLoad(&wg_tier2_fail);
        let tier3_fails = atomicLoad(&wg_tier3_fail);
        let state_sum = atomicLoad(&wg_state_sum);

        var result: u32 = 0u;
        if (tier1_fails == 0u) { result |= 1u; }
        if (tier2_fails == 0u) { result |= 2u; }
        if (tier3_fails == 0u) { result |= 4u; }
        if (tier1_fails == 0u && tier2_fails == 0u && tier3_fails == 0u) { result |= 8u; }
        if (tier1_fails > 0u) { result |= 16u; }
        if (tier2_fails > 0u) { result |= 32u; }
        if (tier3_fails > 0u) { result |= 64u; }

        results[wg_id.x].result = result;
        results[wg_id.x].tier1_violations = tier1_fails;
        results[wg_id.x].tier2_violations = tier2_fails;
        results[wg_id.x].tier3_violations = tier3_fails;
    }
}

// ============================================================================
// Shader 4: Global Reduction (summarize per-workgroup results)
// ============================================================================
//
// Takes per-workgroup constraint results and produces a single global result.
// Dispatch: 1 workgroup of 64 invocations

@compute @workgroup_size(64)
fn global_reduce(
    @builtin(local_invocation_id) local_id: vec3<u32>,
    @builtin(num_workgroups) num_groups: vec3<u32>,
) {
    var<workgroup> wg_total_result: atomic<u32>;
    var<workgroup> wg_tier1_total: atomic<u32>;
    var<workgroup> wg_tier2_total: atomic<u32>;
    var<workgroup> wg_tier3_total: atomic<u32>;

    if (local_id.x == 0u) {
        atomicStore(&wg_total_result, 0u);
        atomicStore(&wg_tier1_total, 0u);
        atomicStore(&wg_tier2_total, 0u);
        atomicStore(&wg_tier3_total, 0u);
    }
    workgroupBarrier();

    let num_wgs = num_groups.x;
    let stride = 64u;

    // Each thread processes one group of workgroup results
    for (var i = local_id.x; i < num_wgs; i += stride) {
        let r = results[i];
        atomicOr(&wg_total_result, r.result);
        atomicAdd(&wg_tier1_total, r.tier1_violations);
        atomicAdd(&wg_tier2_total, r.tier2_violations);
        atomicAdd(&wg_tier3_total, r.tier3_violations);
    }
    workgroupBarrier();

    // Thread 0 writes final result
    if (local_id.x == 0u) {
        let total = atomicLoad(&wg_total_result);
        let t1 = atomicLoad(&wg_tier1_total);
        let t2 = atomicLoad(&wg_tier2_total);
        let t3 = atomicLoad(&wg_tier3_total);
        
        results[0].result = total;
        results[0].tier1_violations = t1;
        results[0].tier2_violations = t2;
        results[0].tier3_violations = t3;
    }
}
