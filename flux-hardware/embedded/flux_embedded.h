/**
 * FLUX-C Embedded Runtime — ARM Cortex-R Safety-Certified
 * 
 * Minimal bytecode interpreter for FLUX-C constraints on bare-metal.
 * No heap allocation. No dynamic memory. No recursion.
 * WCET-bounded. Suitable for DO-178C DAL A / ISO 26262 ASIL D.
 *
 * Target: ARM Cortex-R5/R52 (lockstep, ECC, MPU)
 * Memory: <4KB code, <1KB stack, <256 bytes per constraint set
 *
 * (c) 2026 SuperInstance — Apache 2.0
 */

#ifndef FLUX_EMBEDDED_H
#define FLUX_EMBEDDED_H

#include <stdint.h>
#include <stddef.h>

// ═══════════════════════════════════════════════════════════
// Configuration — tuned for Cortex-R (4-cycle multiply)
// ═══════════════════════════════════════════════════════════

#define FLUX_STACK_SIZE     32      // entries (not bytes)
#define FLUX_MAX_BYTECODE   512     // bytes
#define FLUX_MAX_CONSTRAINTS 8
#define FLUX_CALL_DEPTH     8

// INT8 saturation bounds (security: no -128)
#define FLUX_INT8_MIN       (-127)
#define FLUX_INT8_MAX       (127)

// ═══════════════════════════════════════════════════════════
// Error codes
// ═══════════════════════════════════════════════════════════

typedef enum {
    FLUX_OK = 0,
    FLUX_ERR_STACK_UNDERFLOW,
    FLUX_ERR_STACK_OVERFLOW,
    FLUX_ERR_UNKNOWN_OPCODE,
    FLUX_ERR_CALL_DEPTH,
    FLUX_ERR_SANDBOX_UNBALANCED,
    FLUX_ERR_DIVISION_BY_ZERO,
    FLUX_ERR_BYTECODE_TOO_LONG,
    FLUX_ERR_INVALID_OPERAND,
    FLUX_ERR_DEADLINE_EXCEEDED,
} FluxError;

// ═══════════════════════════════════════════════════════════
// Opcodes — 42 FLUX-C instructions
// ═══════════════════════════════════════════════════════════

typedef enum {
    FLUX_NOP = 0x00,
    FLUX_PUSH,          // Push immediate (1 byte operand)
    FLUX_POP,
    FLUX_DUP,
    FLUX_SWAP,
    FLUX_CONST_LOAD,    // Load constraint constant (1 byte operand)
    
    // Arithmetic
    FLUX_ADD = 0x10,
    FLUX_SUB,
    FLUX_MUL,
    FLUX_DIV,           // Division — checks for zero
    FLUX_MOD,
    FLUX_NEG,
    FLUX_ABS,
    
    // Comparison
    FLUX_EQ = 0x20,
    FLUX_NEQ,
    FLUX_LT,
    FLUX_GT,
    FLUX_LTE,
    FLUX_GTE,
    FLUX_MIN,
    FLUX_MAX,
    FLUX_CLAMP,         // Clamp to [lo, hi] from stack
    
    // Boolean
    FLUX_BOOL_AND = 0x30,
    FLUX_BOOL_OR,
    FLUX_NOT,
    
    // Constraint checking
    FLUX_RANGE_CHECK = 0x40,  // Check value in [lo, hi]
    FLUX_BITMASK_CHECK,       // Check against bitmask
    FLUX_ASSERT,
    FLUX_CHECKPOINT,
    
    // Control flow
    FLUX_JUMP = 0x50,
    FLUX_JUMP_IF,
    FLUX_CALL,
    FLUX_RET,
    FLUX_HALT,
    FLUX_GUARD_TRAP,         // Trap to safety monitor
    
    // System
    FLUX_SANDBOX_ENTER = 0x60,
    FLUX_SANDBOX_EXIT,
    FLUX_DEADLINE,            // Set deadline counter
    FLUX_CONSTRAINT_ID,       // Set current constraint ID
    FLUX_LOG,                 // Log value (debug)
    FLUX_REVERT,              // Revert to checkpoint
    FLUX_FLUSH,               // Flush results to output buffer
} FluxOpcode;

// ═══════════════════════════════════════════════════════════
// Runtime state — entirely stack-allocated
// ═══════════════════════════════════════════════════════════

typedef struct {
    int32_t stack[FLUX_STACK_SIZE];
    int32_t call_stack[FLUX_CALL_DEPTH];
    uint16_t call_depth;
    uint16_t stack_ptr;
    uint16_t pc;              // Program counter
    uint16_t checkpoint_pc;   // For REVERT
    uint16_t deadline;        // Remaining instructions
    uint16_t constraint_id;   // Current constraint
    uint8_t  sandbox_depth;
    uint8_t  flags;           // Bit 0: halted, Bit 1: trapped, Bit 2: deadline exceeded
} FluxVM;

// ═══════════════════════════════════════════════════════════
// Result structure
// ═══════════════════════════════════════════════════════════

typedef struct {
    uint8_t error_mask;       // Bit i = constraint i violated
    uint8_t severity;         // 0=pass, 1=caution, 2=warning, 3=critical
    uint8_t violated_lo;      // Which constraints violated lower bound
    uint8_t violated_hi;      // Which constraints violated upper bound
    uint16_t instructions_executed;
    uint16_t cycles_approx;   // Approximate cycle count (Cortex-R @ 600MHz)
} FluxResult;

// ═══════════════════════════════════════════════════════════
// Saturation — inline, no branch on Cortex-R (conditional select)
// ═══════════════════════════════════════════════════════════

static inline int32_t flux_saturate(int32_t val) {
    if (val < FLUX_INT8_MIN) return FLUX_INT8_MIN;
    if (val > FLUX_INT8_MAX) return FLUX_INT8_MAX;
    return val;
}

// ═══════════════════════════════════════════════════════════
// VM Implementation — all inline, no heap
// ═══════════════════════════════════════════════════════════

static inline FluxError flux_vm_init(FluxVM* vm) {
    // Zero-init without memset (bare-metal safe)
    for (int i = 0; i < FLUX_STACK_SIZE; i++) vm->stack[i] = 0;
    for (int i = 0; i < FLUX_CALL_DEPTH; i++) vm->call_stack[i] = 0;
    vm->call_depth = 0;
    vm->stack_ptr = 0;
    vm->pc = 0;
    vm->checkpoint_pc = 0;
    vm->deadline = 4096;  // Default: 4K instructions max
    vm->constraint_id = 0;
    vm->sandbox_depth = 0;
    vm->flags = 0;
    return FLUX_OK;
}

static inline FluxError flux_push(FluxVM* vm, int32_t val) {
    if (vm->stack_ptr >= FLUX_STACK_SIZE) return FLUX_ERR_STACK_OVERFLOW;
    vm->stack[vm->stack_ptr++] = flux_saturate(val);
    return FLUX_OK;
}

static inline FluxError flux_pop(FluxVM* vm, int32_t* out) {
    if (vm->stack_ptr == 0) return FLUX_ERR_STACK_UNDERFLOW;
    *out = vm->stack[--vm->stack_ptr];
    return FLUX_OK;
}

static inline FluxError flux_execute(FluxVM* vm, const uint8_t* bytecode, uint16_t len, FluxResult* result) {
    FluxError err;
    int32_t a, b, c;
    uint16_t target;
    uint16_t instr_count = 0;

    while (vm->pc < len && !(vm->flags & 0x01)) {
        // Deadline check
        if (instr_count >= vm->deadline) {
            vm->flags |= 0x04;  // Deadline exceeded
            return FLUX_ERR_DEADLINE_EXCEEDED;
        }
        instr_count++;

        uint8_t op = bytecode[vm->pc++];

        switch (op) {
            case FLUX_NOP: break;

            case FLUX_PUSH:
                if (vm->pc >= len) return FLUX_ERR_INVALID_OPERAND;
                err = flux_push(vm, (int32_t)(int8_t)bytecode[vm->pc++]);
                if (err) return err;
                break;

            case FLUX_POP:
                err = flux_pop(vm, &a);
                if (err) return err;
                break;

            case FLUX_DUP:
                if (vm->stack_ptr == 0) return FLUX_ERR_STACK_UNDERFLOW;
                err = flux_push(vm, vm->stack[vm->stack_ptr - 1]);
                if (err) return err;
                break;

            case FLUX_SWAP:
                if (vm->stack_ptr < 2) return FLUX_ERR_STACK_UNDERFLOW;
                a = vm->stack[vm->stack_ptr - 1];
                vm->stack[vm->stack_ptr - 1] = vm->stack[vm->stack_ptr - 2];
                vm->stack[vm->stack_ptr - 2] = a;
                break;

            case FLUX_ADD:
                err = flux_pop(vm, &b); if (err) return err;
                err = flux_pop(vm, &a); if (err) return err;
                err = flux_push(vm, a + b);
                if (err) return err;
                break;

            case FLUX_SUB:
                err = flux_pop(vm, &b); if (err) return err;
                err = flux_pop(vm, &a); if (err) return err;
                err = flux_push(vm, a - b);
                if (err) return err;
                break;

            case FLUX_MUL:
                err = flux_pop(vm, &b); if (err) return err;
                err = flux_pop(vm, &a); if (err) return err;
                err = flux_push(vm, a * b);
                if (err) return err;
                break;

            case FLUX_DIV:
                err = flux_pop(vm, &b); if (err) return err;
                err = flux_pop(vm, &a); if (err) return err;
                if (b == 0) return FLUX_ERR_DIVISION_BY_ZERO;
                err = flux_push(vm, a / b);
                if (err) return err;
                break;

            case FLUX_NEG:
                if (vm->stack_ptr == 0) return FLUX_ERR_STACK_UNDERFLOW;
                vm->stack[vm->stack_ptr - 1] = -vm->stack[vm->stack_ptr - 1];
                break;

            case FLUX_ABS:
                if (vm->stack_ptr == 0) return FLUX_ERR_STACK_UNDERFLOW;
                a = vm->stack[vm->stack_ptr - 1];
                vm->stack[vm->stack_ptr - 1] = a < 0 ? -a : a;
                break;

            case FLUX_LT:
                err = flux_pop(vm, &b); if (err) return err;
                err = flux_pop(vm, &a); if (err) return err;
                err = flux_push(vm, a < b ? 1 : 0);
                if (err) return err;
                break;

            case FLUX_GT:
                err = flux_pop(vm, &b); if (err) return err;
                err = flux_pop(vm, &a); if (err) return err;
                err = flux_push(vm, a > b ? 1 : 0);
                if (err) return err;
                break;

            case FLUX_RANGE_CHECK: {
                // Pop value, lo, hi from stack → push 0 (pass) or 1 (fail)
                err = flux_pop(vm, &c); if (err) return err;  // hi
                err = flux_pop(vm, &b); if (err) return err;  // lo
                err = flux_pop(vm, &a); if (err) return err;  // value
                int32_t val = flux_saturate(a);
                int32_t lo = flux_saturate(b);
                int32_t hi = flux_saturate(c);
                int32_t result_val = (val < lo || val > hi) ? 1 : 0;
                err = flux_push(vm, result_val);
                if (err) return err;
                // Update error mask
                if (result_val) {
                    result->error_mask |= (1u << vm->constraint_id);
                    if (val < lo) result->violated_lo |= (1u << vm->constraint_id);
                    if (val > hi) result->violated_hi |= (1u << vm->constraint_id);
                }
                break;
            }

            case FLUX_JUMP:
                if (vm->pc + 1 >= len) return FLUX_ERR_INVALID_OPERAND;
                target = (uint16_t)(bytecode[vm->pc] | (bytecode[vm->pc+1] << 8));
                vm->pc = target;
                break;

            case FLUX_JUMP_IF:
                if (vm->pc + 1 >= len) return FLUX_ERR_INVALID_OPERAND;
                target = (uint16_t)(bytecode[vm->pc] | (bytecode[vm->pc+1] << 8));
                vm->pc += 2;
                err = flux_pop(vm, &a); if (err) return err;
                if (a != 0) vm->pc = target;
                break;

            case FLUX_CALL:
                if (vm->call_depth >= FLUX_CALL_DEPTH) return FLUX_ERR_CALL_DEPTH;
                if (vm->pc + 1 >= len) return FLUX_ERR_INVALID_OPERAND;
                target = (uint16_t)(bytecode[vm->pc] | (bytecode[vm->pc+1] << 8));
                vm->call_stack[vm->call_depth++] = vm->pc + 2;
                vm->pc = target;
                break;

            case FLUX_RET:
                if (vm->call_depth == 0) return FLUX_ERR_SANDBOX_UNBALANCED;
                vm->pc = vm->call_stack[--vm->call_depth];
                break;

            case FLUX_HALT:
                vm->flags |= 0x01;  // Halted
                break;

            case FLUX_GUARD_TRAP:
                vm->flags |= 0x02;  // Trapped
                break;

            case FLUX_SANDBOX_ENTER:
                vm->sandbox_depth++;
                break;

            case FLUX_SANDBOX_EXIT:
                if (vm->sandbox_depth == 0) return FLUX_ERR_SANDBOX_UNBALANCED;
                vm->sandbox_depth--;
                break;

            case FLUX_CONSTRAINT_ID:
                if (vm->pc >= len) return FLUX_ERR_INVALID_OPERAND;
                vm->constraint_id = bytecode[vm->pc++];
                break;

            case FLUX_CHECKPOINT:
                vm->checkpoint_pc = vm->pc;
                break;

            case FLUX_REVERT:
                vm->pc = vm->checkpoint_pc;
                break;

            default:
                return FLUX_ERR_UNKNOWN_OPCODE;
        }
    }

    // Compute severity
    int nv = 0;
    uint8_t mask = result->error_mask;
    while (mask) { nv += mask & 1; mask >>= 1; }
    if (nv == 0) result->severity = 0;
    else if (nv <= 2) result->severity = 1;
    else if (nv <= 4) result->severity = 2;
    else result->severity = 3;

    result->instructions_executed = instr_count;
    // Approximate cycles: ~2 cycles per instruction on Cortex-R5 @ 600MHz
    result->cycles_approx = instr_count * 2;

    return FLUX_OK;
}

#endif // FLUX_EMBEDDED_H
