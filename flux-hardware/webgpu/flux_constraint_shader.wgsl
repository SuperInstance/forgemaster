/**
 * flux_constraint_shader.wgsl — WebGPU Compute Shader for FLUX Constraint Checking
 *
 * Runs FLUX-C constraint VM in the browser via WebGPU.
 * Complements Oracle1's flux-sandbox.html with a real GPU backend.
 *
 * Usage:
 *   1. Create GPU device
 *   2. Create buffers: bytecode, inputs, results
 *   3. Dispatch workgroups
 *   4. Read results
 */

// FLUX-C VM state per thread
struct VMState {
    stack: array<i32, 64>,
    sp: i32,
    pc: i32,
    gas: i32,
    fault: i32,
    passed: i32,
    result: i32,
};

// Uniforms passed from JS
struct Params {
    bytecode_len: i32,
    n_inputs: i32,
    max_gas: i32,
    _pad: i32,
};

@group(0) @binding(0) var<storage, read> bytecode: array<u32>;
@group(0) @binding(1) var<storage, read> inputs: array<i32>;
@group(0) @binding(2) var<storage, read_write> results: array<i32>;
@group(0) @binding(3) var<storage, read_write> pass_count: atomic<i32>;
@group(0) @binding(4) var<storage, read_write> fail_count: atomic<i32>;
@group(0) @binding(5) var<uniform> params: Params;

@compute @workgroup_size(256)
fn flux_vm_batch(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = i32(gid.x);
    if (idx >= params.n_inputs) {
        return;
    }

    // Initialize VM state
    var stack: array<i32, 64>;
    var sp: i32 = 0;
    var pc: i32 = 0;
    var gas: i32 = params.max_gas;
    var fault: i32 = 0;
    var passed: i32 = 0;

    // Push input onto stack
    stack[0] = inputs[idx];
    sp = 1;

    // Execute bytecode
    while (pc < params.bytecode_len && gas > 0 && fault == 0 && passed == 0) {
        gas = gas - 1;
        let op = extract_opcode(bytecode[pc / 4], pc % 4);

        switch (op) {
            case 0x00u: {
                // PUSH - next byte is operand
                pc = pc + 1;
                stack[sp] = extract_opcode(bytecode[pc / 4], pc % 4);
                sp = sp + 1;
                pc = pc + 1;
            }
            case 0x1Au: {
                // HALT - passed
                passed = 1;
                pc = params.bytecode_len;
            }
            case 0x1Bu: {
                // ASSERT - pop, fail if 0
                sp = sp - 1;
                if (stack[sp] == 0) {
                    fault = 1;
                }
                pc = pc + 1;
            }
            case 0x1Cu: {
                // CHECK_DOMAIN - bitmask check
                sp = sp - 1;
                let val = stack[sp];
                pc = pc + 1;
                let mask = extract_opcode(bytecode[pc / 4], pc % 4);
                stack[sp] = select(0, 1, (val & i32(mask)) == val);
                sp = sp + 1;
                pc = pc + 1;
            }
            case 0x1Du: {
                // BITMASK_RANGE - range check [lo, hi]
                sp = sp - 1;
                let val = stack[sp];
                pc = pc + 1;
                let lo = extract_opcode(bytecode[pc / 4], pc % 4);
                pc = pc + 1;
                let hi = extract_opcode(bytecode[pc / 4], pc % 4);
                stack[sp] = select(0, 1, val >= i32(lo) && val <= i32(hi));
                sp = sp + 1;
                pc = pc + 1;
            }
            case 0x20u: {
                // GUARD_TRAP - immediate fault
                fault = 1;
                pc = pc + 1;
            }
            case 0x24u: {
                // CMP_GE - a >= b ?
                sp = sp - 1;
                let b = stack[sp];
                sp = sp - 1;
                let a = stack[sp];
                stack[sp] = select(0, 1, a >= b);
                sp = sp + 1;
                pc = pc + 1;
            }
            case 0x25u: {
                // CMP_EQ - a == b ?
                sp = sp - 1;
                let b = stack[sp];
                sp = sp - 1;
                let a = stack[sp];
                stack[sp] = select(0, 1, a == b);
                sp = sp + 1;
                pc = pc + 1;
            }
            default: {
                pc = pc + 1;
            }
        }
    }

    // Write result
    let my_result = select(0, 1, passed == 1 && fault == 0);
    results[idx] = my_result;

    // Atomic counting (no warp vote in WebGPU, use atomics)
    if (my_result == 1) {
        atomicAdd(&pass_count, 1);
    } else {
        atomicAdd(&fail_count, 1);
    }
}

// Extract a single byte from a u32 word
fn extract_opcode(word: u32, byte_pos: i32) -> u32 {
    let shift = u32(byte_pos * 8);
    return (word >> shift) & 0xFFu;
}
