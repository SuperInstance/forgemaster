/**
 * @file flux_runtime_arm.h
 * @brief FLUX Constraint Checker — ARM Cortex-R Safety-Critical Runtime
 *
 * Zero-heap, MISRA-C compliant bytecode interpreter for constraint validation.
 * Designed for arm-none-eabi-gcc bare-metal targets.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 SuperInstance
 */

#ifndef FLUX_RUNTIME_ARM_H
#define FLUX_RUNTIME_ARM_H

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/* Configuration macros                                                */
/* ------------------------------------------------------------------ */

/** Maximum stack depth (fixed-size, stack-allocated). */
#ifndef FLUX_STACK_SIZE
#define FLUX_STACK_SIZE  64U
#endif

/** Default gas limit if caller passes 0. */
#ifndef FLUX_DEFAULT_GAS
#define FLUX_DEFAULT_GAS  4096U
#endif

/** Gas cost per opcode dispatch (base). */
#ifndef FLUX_GAS_PER_OPCODE
#define FLUX_GAS_PER_OPCODE  1U
#endif

/** Gas cost for CHECK_DOMAIN (heavier operation). */
#ifndef FLUX_GAS_CHECK_DOMAIN
#define FLUX_GAS_CHECK_DOMAIN  3U
#endif

/** Gas cost for RANGE (two pops + two immediate bytes). */
#ifndef FLUX_GAS_RANGE
#define FLUX_GAS_RANGE  2U
#endif

/* ------------------------------------------------------------------ */
/* Opcodes                                                             */
/* ------------------------------------------------------------------ */

#define FLUX_OP_HALT          0x1AU
#define FLUX_OP_ASSERT        0x1BU
#define FLUX_OP_CHECK_DOMAIN  0x1CU
#define FLUX_OP_RANGE         0x1DU
#define FLUX_OP_BOOL_AND      0x26U
#define FLUX_OP_BOOL_OR       0x27U
#define FLUX_OP_DUP           0x28U
#define FLUX_OP_SWAP          0x29U

/* Arithmetic / logic (common extensions) */
#define FLUX_OP_PUSH_I8       0x01U
#define FLUX_OP_PUSH_I16      0x02U
#define FLUX_OP_PUSH_I32      0x03U
#define FLUX_OP_LOAD_INPUT    0x10U
#define FLUX_OP_ADD           0x20U
#define FLUX_OP_SUB           0x21U
#define FLUX_OP_MUL           0x22U
#define FLUX_OP_EQ            0x23U
#define FLUX_OP_LT            0x24U
#define FLUX_OP_GT            0x25U
#define FLUX_OP_NOT           0x2AU
#define FLUX_OP_NOP           0x00U

/* ------------------------------------------------------------------ */
/* Result codes                                                        */
/* ------------------------------------------------------------------ */

#define FLUX_PASS            0
#define FLUX_FAULT           1   /**< ASSERT failed or invalid opcode */
#define FLUX_GAS_EXHAUSTED   2   /**< Exceeded max_gas before HALT */
#define FLUX_STACK_OVERFLOW  3   /**< Push past FLUX_STACK_SIZE */
#define FLUX_STACK_UNDERFLOW 4   /**< Pop from empty stack */
#define FLUX_BAD_BYTECODE    5   /**< Truncated or malformed bytecode */

/* ------------------------------------------------------------------ */
/* Public types                                                        */
/* ------------------------------------------------------------------ */

/** Runtime state — exposed for unit-test inspection only. */
typedef struct {
    int32_t  stack[FLUX_STACK_SIZE];
    uint16_t sp;         /**< Stack pointer (next free slot) */
    uint16_t pc;         /**< Program counter */
    uint16_t gas;        /**< Remaining gas */
    uint8_t  fault;      /**< Non-zero on fault (MISRA: explicit flag) */
} flux_state_t;

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

/**
 * @brief Execute a FLUX constraint check.
 *
 * @param bytecode  Bytecode buffer (must remain valid for duration).
 * @param bc_len    Length of bytecode in bytes.
 * @param input     The input value to validate against constraints.
 * @param max_gas   Maximum gas (0 = FLUX_DEFAULT_GAS).
 * @param gas_used  [out] Actual gas consumed (may be NULL).
 *
 * @return One of FLUX_PASS, FLUX_FAULT, FLUX_GAS_EXHAUSTED,
 *         FLUX_STACK_OVERFLOW, FLUX_STACK_UNDERFLOW, FLUX_BAD_BYTECODE.
 */
int flux_check(
    const uint8_t* bytecode,
    uint16_t       bc_len,
    int32_t        input,
    uint16_t       max_gas,
    uint16_t*      gas_used
);

/**
 * @brief Reset runtime state (useful for pooling / re-use).
 *
 * @param st  State to zero-initialize.
 */
void flux_state_reset(flux_state_t* st);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_RUNTIME_ARM_H */
