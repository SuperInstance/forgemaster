/**
 * @file flux_runtime_arm.c
 * @brief FLUX Constraint Checker — ARM Cortex-R Safety-Critical Runtime
 *
 * Zero-heap, bounded-execution bytecode interpreter.
 * Compiles with arm-none-eabi-gcc -std=c11 -mcpu=cortex-r5 -mthumb -O2.
 *
 * MISRA-C:2012 guidelines followed where practicable:
 *   - No dynamic allocation (Rule 21.3)
 *   - Bounded loops with constant upper limit (Rule 14.3)
 *   - Explicit types from stdint.h (Rule 10.x)
 *   - No implicit conversions (Directive 4.6)
 *   - All switch cases have break/default (Rule 16.4)
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 SuperInstance
 */

#include "flux_runtime_arm.h"
#include <stdint.h>
#include <stddef.h>

/* ------------------------------------------------------------------ */
/* Inline helpers                                                      */
/* ------------------------------------------------------------------ */

/** Stack push with overflow check. Returns 0 on success. */
static inline int stack_push(flux_state_t* st, int32_t val)
{
    if (st->sp >= FLUX_STACK_SIZE) {
        st->fault = (uint8_t)FLUX_STACK_OVERFLOW;
        return FLUX_STACK_OVERFLOW;
    }
    st->stack[st->sp] = val;
    st->sp++;
    return 0;
}

/** Stack pop with underflow check. Returns 0 on success. */
static inline int stack_pop(flux_state_t* st, int32_t* out)
{
    if (st->sp == 0U) {
        st->fault = (uint8_t)FLUX_STACK_UNDERFLOW;
        return FLUX_STACK_UNDERFLOW;
    }
    st->sp--;
    *out = st->stack[st->sp];
    return 0;
}

/** Read a little-endian int16_t from bytecode at offset. Returns 0 on ok. */
static inline int read_i16(
    const uint8_t* bc, uint16_t bc_len, uint16_t offset, int16_t* out)
{
    if ((uint32_t)offset + 1U >= (uint32_t)bc_len) {
        return FLUX_BAD_BYTECODE;
    }
    /* MISRA: explicit cast chain, no punning */
    uint16_t raw = (uint16_t)((uint16_t)bc[offset] |
                              ((uint16_t)bc[(uint16_t)(offset + 1U)] << 8));
    *out = (int16_t)raw;
    return 0;
}

/** Read a little-endian int32_t from bytecode at offset. Returns 0 on ok. */
static inline int read_i32(
    const uint8_t* bc, uint16_t bc_len, uint16_t offset, int32_t* out)
{
    if ((uint32_t)offset + 3U >= (uint32_t)bc_len) {
        return FLUX_BAD_BYTECODE;
    }
    uint32_t raw = (uint32_t)bc[offset]
                 | ((uint32_t)bc[(uint16_t)(offset + 1U)] << 8)
                 | ((uint32_t)bc[(uint16_t)(offset + 2U)] << 16)
                 | ((uint32_t)bc[(uint16_t)(offset + 3U)] << 24);
    *out = (int32_t)raw;
    return 0;
}

/** Consume gas. Returns 0 if gas remains, FLUX_GAS_EXHAUSTED if depleted. */
static inline int consume_gas(flux_state_t* st, uint16_t cost)
{
    if (st->gas < cost) {
        st->gas = 0U;
        st->fault = (uint8_t)FLUX_GAS_EXHAUSTED;
        return FLUX_GAS_EXHAUSTED;
    }
    st->gas = (uint16_t)(st->gas - cost);
    return 0;
}

/* ------------------------------------------------------------------ */
/* ARM inline-assembly helpers (Cortex-R5 Thumb-2)                     */
/* ------------------------------------------------------------------ */

/**
 * Clz-based fast gas check — single instruction on ARM.
 * Returns non-zero if value is zero (gas exhausted).
 */
#if defined(__ARM_ARCH) && (__ARM_ARCH >= 7)
static inline uint32_t arm_is_zero(uint32_t v)
{
    uint32_t result;
    __asm__ volatile ("clz %0, %1" : "=r" (result) : "r" (v));
    /* clz returns 32 for input 0, <32 otherwise */
    return (result >> 5U);  /* 1 if v==0, 0 otherwise */
}
#endif

/* ------------------------------------------------------------------ */
/* Core interpreter                                                    */
/* ------------------------------------------------------------------ */

int flux_check(
    const uint8_t* bytecode,
    uint16_t       bc_len,
    int32_t        input,
    uint16_t       max_gas,
    uint16_t*      gas_used)
{
    /* ---- Validate arguments ---- */
    if ((bytecode == NULL) || (bc_len == 0U)) {
        if (gas_used != NULL) { *gas_used = 0U; }
        return FLUX_BAD_BYTECODE;
    }

    /* ---- Init state (all on stack, zero heap) ---- */
    flux_state_t st;
    flux_state_reset(&st);
    st.gas = (max_gas != 0U) ? max_gas : (uint16_t)FLUX_DEFAULT_GAS;

    /* ---- Push input as initial stack value ---- */
    if (stack_push(&st, input) != 0) {
        if (gas_used != NULL) { *gas_used = 0U; }
        return (int)st.fault;
    }

    /* ---- Dispatch loop (bounded by gas) ---- */
    int result = FLUX_PASS;
    uint16_t total_gas_used = 0U;

    while ((st.fault == 0U) && (st.pc < bc_len)) {
        uint8_t opcode = bytecode[st.pc];

        /* ---- Base gas for every opcode ---- */
        uint16_t gas_cost = (uint16_t)FLUX_GAS_PER_OPCODE;

        switch (opcode) {

        /* ---------------------------------------------------------- */
        case FLUX_OP_NOP:
            st.pc++;
            break;

        /* ---------------------------------------------------------- */
        case FLUX_OP_HALT:  /* 0x1A */
            st.pc++;
            /* Normal termination — result is top of stack */
            {
                int32_t top;
                if (stack_pop(&st, &top) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
                result = (top != 0) ? FLUX_PASS : FLUX_FAULT;
            }
            goto done;

        /* ---------------------------------------------------------- */
        case FLUX_OP_ASSERT:  /* 0x1B */
            st.pc++;
            {
                int32_t cond;
                if (stack_pop(&st, &cond) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
                if (cond == 0) {
                    result = FLUX_FAULT;
                    st.fault = (uint8_t)FLUX_FAULT;
                    goto done;
                }
                /* Push result back (ASSERT passes — keep stack consistent) */
                (void)stack_push(&st, 1);
            }
            break;

        /* ---------------------------------------------------------- */
        case FLUX_OP_CHECK_DOMAIN:  /* 0x1C */
            st.pc++;
            gas_cost = (uint16_t)FLUX_GAS_CHECK_DOMAIN;
            {
                int32_t val;
                if (stack_pop(&st, &val) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
                /*
                 * CHECK_DOMAIN: pop top, push 1 if val != 0 (truthy),
                 * push 0 otherwise. Semantic: "is this value in the
                 * boolean domain?".
                 */
                int32_t in_domain = (val != 0) ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, in_domain) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        /* ---------------------------------------------------------- */
        case FLUX_OP_RANGE:  /* 0x1D */
            st.pc++;
            gas_cost = (uint16_t)FLUX_GAS_RANGE;
            {
                /* RANGE imm16_lo imm16_hi — pop value, push 1 if
                 * lo <= val <= hi (unsigned range check on stack value) */
                int16_t lo;
                int16_t hi;
                if (read_i16(bytecode, bc_len, st.pc, &lo) != 0) {
                    result = FLUX_BAD_BYTECODE;
                    st.fault = (uint8_t)FLUX_BAD_BYTECODE;
                    goto done;
                }
                st.pc = (uint16_t)(st.pc + 2U);
                if (read_i16(bytecode, bc_len, st.pc, &hi) != 0) {
                    result = FLUX_BAD_BYTECODE;
                    st.fault = (uint8_t)FLUX_BAD_BYTECODE;
                    goto done;
                }
                st.pc = (uint16_t)(st.pc + 2U);

                int32_t val;
                if (stack_pop(&st, &val) != 0) {
                    result = (int)st.fault;
                    goto done;
                }

                int32_t in_range = ((val >= (int32_t)lo) &&
                                    (val <= (int32_t)hi))
                                   ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, in_range) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        /* ---------------------------------------------------------- */
        case FLUX_OP_BOOL_AND:  /* 0x26 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                int32_t r = ((a != 0) && (b != 0)) ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, r) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        /* ---------------------------------------------------------- */
        case FLUX_OP_BOOL_OR:  /* 0x27 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                int32_t r = ((a != 0) || (b != 0)) ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, r) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        /* ---------------------------------------------------------- */
        case FLUX_OP_DUP:  /* 0x28 */
            st.pc++;
            {
                if (st.sp == 0U) {
                    st.fault = (uint8_t)FLUX_STACK_UNDERFLOW;
                    result = FLUX_STACK_UNDERFLOW;
                    goto done;
                }
                int32_t top = st.stack[(uint16_t)(st.sp - 1U)];
                if (stack_push(&st, top) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        /* ---------------------------------------------------------- */
        case FLUX_OP_SWAP:  /* 0x29 */
            st.pc++;
            {
                if (st.sp < 2U) {
                    st.fault = (uint8_t)FLUX_STACK_UNDERFLOW;
                    result = FLUX_STACK_UNDERFLOW;
                    goto done;
                }
                uint16_t idx_a = (uint16_t)(st.sp - 1U);
                uint16_t idx_b = (uint16_t)(st.sp - 2U);
                int32_t tmp    = st.stack[idx_a];
                st.stack[idx_a] = st.stack[idx_b];
                st.stack[idx_b] = tmp;
            }
            break;

        /* ---------------------------------------------------------- */
        /* Extended opcodes: push immediates & load input              */
        /* ---------------------------------------------------------- */
        case FLUX_OP_PUSH_I8:  /* 0x01 */
            st.pc++;
            {
                if (st.pc >= bc_len) {
                    result = FLUX_BAD_BYTECODE;
                    st.fault = (uint8_t)FLUX_BAD_BYTECODE;
                    goto done;
                }
                int32_t val = (int32_t)(int8_t)bytecode[st.pc];
                st.pc++;
                if (stack_push(&st, val) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_PUSH_I16:  /* 0x02 */
            st.pc++;
            {
                int16_t val;
                if (read_i16(bytecode, bc_len, st.pc, &val) != 0) {
                    result = FLUX_BAD_BYTECODE;
                    st.fault = (uint8_t)FLUX_BAD_BYTECODE;
                    goto done;
                }
                st.pc = (uint16_t)(st.pc + 2U);
                if (stack_push(&st, (int32_t)val) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_PUSH_I32:  /* 0x03 */
            st.pc++;
            {
                int32_t val;
                if (read_i32(bytecode, bc_len, st.pc, &val) != 0) {
                    result = FLUX_BAD_BYTECODE;
                    st.fault = (uint8_t)FLUX_BAD_BYTECODE;
                    goto done;
                }
                st.pc = (uint16_t)(st.pc + 4U);
                if (stack_push(&st, val) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_LOAD_INPUT:  /* 0x10 */
            st.pc++;
            if (stack_push(&st, input) != 0) {
                result = (int)st.fault;
                goto done;
            }
            break;

        /* ---------------------------------------------------------- */
        /* Arithmetic / comparison                                    */
        /* ---------------------------------------------------------- */
        case FLUX_OP_ADD:  /* 0x20 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                if (stack_push(&st, a + b) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_SUB:  /* 0x21 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                if (stack_push(&st, a - b) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_MUL:  /* 0x22 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                if (stack_push(&st, a * b) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_EQ:  /* 0x23 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                int32_t r = (a == b) ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, r) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_LT:  /* 0x24 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                int32_t r = (a < b) ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, r) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_GT:  /* 0x25 */
            st.pc++;
            {
                int32_t a, b;
                if ((stack_pop(&st, &b) != 0) || (stack_pop(&st, &a) != 0)) {
                    result = (int)st.fault;
                    goto done;
                }
                int32_t r = (a > b) ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, r) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        case FLUX_OP_NOT:  /* 0x2A */
            st.pc++;
            {
                int32_t a;
                if (stack_pop(&st, &a) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
                int32_t r = (a == 0) ? (int32_t)1 : (int32_t)0;
                if (stack_push(&st, r) != 0) {
                    result = (int)st.fault;
                    goto done;
                }
            }
            break;

        /* ---------------------------------------------------------- */
        default:
            /* Unknown opcode — fault immediately */
            st.pc++;
            result = FLUX_FAULT;
            st.fault = (uint8_t)FLUX_FAULT;
            goto done;
        }

        /* ---- Consume gas after dispatch ---- */
        total_gas_used = (uint16_t)(total_gas_used + gas_cost);
        if (consume_gas(&st, gas_cost) != 0) {
            result = FLUX_GAS_EXHAUSTED;
            goto done;
        }
    }

    /* If we fell out of the loop without HALT, it's truncated bytecode */
    if ((st.fault == 0U) && (st.pc >= bc_len)) {
        result = FLUX_BAD_BYTECODE;
    }

done:
    if (gas_used != NULL) {
        *gas_used = total_gas_used;
    }
    return result;
}

/* ------------------------------------------------------------------ */
/* State reset                                                         */
/* ------------------------------------------------------------------ */

void flux_state_reset(flux_state_t* st)
{
    if (st == NULL) { return; }

    /* Zero the stack — MISRA-compliant bounded loop */
    uint16_t i;
    for (i = 0U; i < FLUX_STACK_SIZE; i++) {
        st->stack[i] = (int32_t)0;
    }
    st->sp    = (uint16_t)0;
    st->pc    = (uint16_t)0;
    st->gas   = (uint16_t)FLUX_DEFAULT_GAS;
    st->fault = (uint8_t)0;
}
