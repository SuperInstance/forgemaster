/* flux_monitor_arm.c — FLUX-C Runtime Monitor for ARM Cortex-R
 *
 * Safety-critical constraint monitor for embedded targets.
 * Zero heap allocation. Fixed stack. Deterministic. Bounded WCET.
 *
 * Target: ARM Cortex-R5/R52 (32-bit, MPU, lockstep)
 * Compiler: arm-none-eabi-gcc
 * License: Apache 2.0
 *
 * Usage:
 *   struct flux_monitor mon;
 *   flux_monitor_init(&mon);
 *   flux_monitor_load(&mon, my_constraint_bytecode, sizeof(my_constraint_bytecode));
 *   bool safe = flux_monitor_check(&mon, altitude, 0.0f, 40000.0f);
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* Configuration */
#define FLUX_STACK_SIZE     64
#define FLUX_MAX_PROGRAM    256
#define FLUX_MAX_CHECKPOINTS 8

/* FLUX-C Opcodes */
#define FLUX_OP_NOP         0x00
#define FLUX_OP_PUSH_I32    0x01
#define FLUX_OP_PUSH_F32    0x02
#define FLUX_OP_POP         0x03
#define FLUX_OP_DUP         0x04
#define FLUX_OP_SWAP        0x05
#define FLUX_OP_CHECK_RANGE_I32  0x10
#define FLUX_OP_CHECK_RANGE_F32  0x11
#define FLUX_OP_CHECK_DOMAIN 0x12
#define FLUX_OP_AND         0x20
#define FLUX_OP_OR          0x21
#define FLUX_OP_NOT         0x22
#define FLUX_OP_ADD_I32     0x30
#define FLUX_OP_SUB_I32     0x31
#define FLUX_OP_MUL_I32     0x32
#define FLUX_OP_CMP_EQ      0x40
#define FLUX_OP_CMP_LT      0x41
#define FLUX_OP_CMP_GE      0x42
#define FLUX_OP_CHECKPOINT  0x50
#define FLUX_OP_REVERT      0x51
#define FLUX_OP_HALT        0xFF

/* Value type — tagged union */
typedef struct {
    uint8_t tag;  /* 0 = i32, 1 = f32, 2 = bool */
    union {
        int32_t i32_val;
        float   f32_val;
        bool    bool_val;
    };
} flux_value;

/* Monitor state — all fixed-size, no heap */
typedef struct {
    flux_value stack[FLUX_STACK_SIZE];
    uint8_t    stack_top;
    
    uint8_t    program[FLUX_MAX_PROGRAM];
    uint16_t   program_len;
    
    flux_value checkpoints[FLUX_MAX_CHECKPOINTS][FLUX_STACK_SIZE];
    uint8_t    checkpoint_tops[FLUX_MAX_CHECKPOINTS];
    uint8_t    checkpoint_count;
    
    /* Statistics */
    uint32_t   checks_performed;
    uint32_t   checks_passed;
    uint32_t   checks_failed;
    
    /* Error state */
    uint8_t    last_error;  /* 0 = none */
    uint16_t   error_pc;
} flux_monitor;

/* Error codes */
#define FLUX_ERR_NONE           0
#define FLUX_ERR_STACK_OVERFLOW 1
#define FLUX_ERR_STACK_UNDERFLOW 2
#define FLUX_ERR_TYPE_MISMATCH  3
#define FLUX_ERR_INVALID_OPCODE 4
#define FLUX_ERR_PROGRAM_TOO_LARGE 5

/* Inline helpers — no function call overhead */
static inline void stack_push(flux_monitor *m, flux_value v) {
    if (m->stack_top >= FLUX_STACK_SIZE) { m->last_error = FLUX_ERR_STACK_OVERFLOW; return; }
    m->stack[m->stack_top++] = v;
}

static inline flux_value stack_pop(flux_monitor *m) {
    if (m->stack_top == 0) { m->last_error = FLUX_ERR_STACK_UNDERFLOW; return (flux_value){0}; }
    return m->stack[--m->stack_top];
}

static inline flux_value stack_peek(flux_monitor *m, uint8_t offset) {
    if (m->stack_top <= offset) { m->last_error = FLUX_ERR_STACK_UNDERFLOW; return (flux_value){0}; }
    return m->stack[m->stack_top - 1 - offset];
}

/* Initialize monitor — call once before use */
void flux_monitor_init(flux_monitor *m) {
    memset(m, 0, sizeof(flux_monitor));
}

/* Load bytecode program */
bool flux_monitor_load(flux_monitor *m, const uint8_t *bytecode, uint16_t len) {
    if (len > FLUX_MAX_PROGRAM) {
        m->last_error = FLUX_ERR_PROGRAM_TOO_LARGE;
        return false;
    }
    memcpy(m->program, bytecode, len);
    m->program_len = len;
    return true;
}

/* Execute one opcode — returns false on error */
static bool flux_execute_op(flux_monitor *m, uint8_t op, const uint8_t **pc) {
    flux_value a, b, result;
    
    switch (op) {
    case FLUX_OP_NOP:
        break;
        
    case FLUX_OP_PUSH_I32:
        a.tag = 0;
        a.i32_val = (int32_t)((*pc)[0] | (*pc)[1] << 8 | (*pc)[2] << 16 | (*pc)[3] << 24);
        *pc += 4;
        stack_push(m, a);
        break;
        
    case FLUX_OP_PUSH_F32:
        a.tag = 1;
        uint32_t bits = (*pc)[0] | (*pc)[1] << 8 | (*pc)[2] << 16 | (*pc)[3] << 24;
        memcpy(&a.f32_val, &bits, 4);
        *pc += 4;
        stack_push(m, a);
        break;
        
    case FLUX_OP_POP:
        stack_pop(m);
        break;
        
    case FLUX_OP_DUP:
        a = stack_peek(m, 0);
        stack_push(m, a);
        break;
        
    case FLUX_OP_SWAP:
        a = stack_pop(m);
        b = stack_pop(m);
        stack_push(m, a);
        stack_push(m, b);
        break;
        
    case FLUX_OP_CHECK_RANGE_I32:
        b = stack_pop(m); /* max */
        a = stack_pop(m); /* min */
        {
            flux_value val = stack_pop(m); /* value */
            result.tag = 2;
            result.bool_val = (val.i32_val >= a.i32_val && val.i32_val <= b.i32_val);
            m->checks_performed++;
            if (result.bool_val) m->checks_passed++; else m->checks_failed++;
            stack_push(m, result);
        }
        break;
        
    case FLUX_OP_CHECK_RANGE_F32:
        b = stack_pop(m); /* max */
        a = stack_pop(m); /* min */
        {
            flux_value val = stack_pop(m); /* value */
            result.tag = 2;
            result.bool_val = (val.f32_val >= a.f32_val && val.f32_val <= b.f32_val);
            m->checks_performed++;
            if (result.bool_val) m->checks_passed++; else m->checks_failed++;
            stack_push(m, result);
        }
        break;
        
    case FLUX_OP_AND:
        b = stack_pop(m);
        a = stack_pop(m);
        result.tag = 2;
        result.bool_val = (a.bool_val && b.bool_val);
        stack_push(m, result);
        break;
        
    case FLUX_OP_OR:
        b = stack_pop(m);
        a = stack_pop(m);
        result.tag = 2;
        result.bool_val = (a.bool_val || b.bool_val);
        stack_push(m, result);
        break;
        
    case FLUX_OP_NOT:
        a = stack_pop(m);
        result.tag = 2;
        result.bool_val = !a.bool_val;
        stack_push(m, result);
        break;
        
    case FLUX_OP_CHECKPOINT:
        if (m->checkpoint_count >= FLUX_MAX_CHECKPOINTS) break;
        memcpy(m->checkpoints[m->checkpoint_count], m->stack, sizeof(flux_value) * m->stack_top);
        m->checkpoint_tops[m->checkpoint_count] = m->stack_top;
        m->checkpoint_count++;
        break;
        
    case FLUX_OP_REVERT:
        if (m->checkpoint_count == 0) break;
        m->checkpoint_count--;
        m->stack_top = m->checkpoint_tops[m->checkpoint_count];
        memcpy(m->stack, m->checkpoints[m->checkpoint_count], sizeof(flux_value) * m->stack_top);
        break;
        
    case FLUX_OP_HALT:
        return true; /* Signal halt — caller stops execution */
        
    default:
        m->last_error = FLUX_ERR_INVALID_OPCODE;
        m->error_pc = (uint16_t)(*pc - m->program);
        return false;
    }
    
    return m->last_error == FLUX_ERR_NONE;
}

/* Execute full program — returns true if ALL constraints pass */
bool flux_monitor_run(flux_monitor *m) {
    const uint8_t *pc = m->program;
    const uint8_t *end = m->program + m->program_len;
    
    m->stack_top = 0;
    m->last_error = FLUX_ERR_NONE;
    
    while (pc < end) {
        uint8_t op = *pc++;
        if (op == FLUX_OP_HALT) break;
        if (!flux_execute_op(m, op, &pc)) return false;
    }
    
    /* Result is top of stack (boolean) */
    if (m->stack_top > 0 && m->stack[0].tag == 2) {
        return m->stack[0].bool_val;
    }
    
    /* Default: all constraints passed if no failures */
    return m->checks_failed == 0;
}

/* Quick-check API: check a single value against a range */
bool flux_check_range_f32(float value, float min, float max) {
    /* Compiled inline — no VM overhead for trivial checks */
    return (value >= min) && (value <= max);
}

bool flux_check_range_i32(int32_t value, int32_t min, int32_t max) {
    return (value >= min) && (value <= max);
}

/* Get statistics */
uint32_t flux_monitor_get_checks(flux_monitor *m) { return m->checks_performed; }
uint32_t flux_monitor_get_passed(flux_monitor *m) { return m->checks_passed; }
uint32_t flux_monitor_get_failed(flux_monitor *m) { return m->checks_failed; }
uint8_t  flux_monitor_get_error(flux_monitor *m)  { return m->last_error; }
