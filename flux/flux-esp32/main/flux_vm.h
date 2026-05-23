/*
 * flux_vm.h — FLUX Constraint-Checking VM for ESP32 Xtensa LX7
 *
 * Core definitions for a 43-opcode register-based VM optimized for
 * real-time constraint checking on the ESP32 dual-core MCU.
 *
 * Architecture:
 *   - Core 1 pinned at priority 24 for FLUX execution
 *   - Dispatch loop + hot opcodes in IRAM (IRAM_ATTR)
 *   - INT8 x8 parallel comparisons via bit-manipulation (no SIMD needed)
 *   - Lock-free ring buffer for inter-core communication
 *   - Static allocation only — no heap in the checking path
 */
#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "esp_attr.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

#define FLUX_MAX_OPCODES        43
#define FLUX_MAX_SETS           16      /* Maximum constraint sets         */
#define FLUX_STACK_DEPTH        256     /* Evaluation stack depth           */
#define FLUX_MAX_CONSTRAINTS    4096    /* Max constraints across all sets  */
#define FLUX_BYTECODE_SIZE      16384   /* Max bytecode size in bytes       */
#define FLUX_DATA_RAM_SIZE      256     /* Addressable data slots           */

/* Core affinity */
#define FLUX_CORE_WIFI          0       /* FreeRTOS + WiFi/BLE on Core 0   */
#define FLUX_CORE_VM            1       /* FLUX VM pinned to Core 1        */

/* Task priority — highest on Core 1, never preempted by network */
#define FLUX_VM_PRIORITY        (configMAX_PRIORITIES - 1)

/* ------------------------------------------------------------------ */
/*  Error codes                                                        */
/* ------------------------------------------------------------------ */

typedef enum {
    FLUX_OK                  =  0,
    FLUX_ERR_INVALID_OPCODE  = -1,
    FLUX_ERR_STACK_UNDERFLOW = -2,
    FLUX_ERR_STACK_OVERFLOW  = -3,
    FLUX_ERR_DIV_ZERO        = -4,
    FLUX_ERR_TIMEOUT         = -5,
    FLUX_ERR_INVALID_SET     = -6,
} flux_status_t;

/* ------------------------------------------------------------------ */
/*  INT8 x8 packed type — 8 signed bytes in 64 bits                    */
/* ------------------------------------------------------------------ */

typedef union {
    int8_t   bytes[8];
    uint32_t words[2];
    uint64_t qword;
} flux_int8x8_t;

/* INT8 x8 comparison result — 1 bit per byte lane */
typedef union {
    uint8_t mask;
    struct {
        uint8_t b0:1, b1:1, b2:1, b3:1, b4:1, b5:1, b6:1, b7:1;
    } bits;
} flux_int8_result_t;

/* ------------------------------------------------------------------ */
/*  Opcode enumeration (43 total)                                      */
/* ------------------------------------------------------------------ */

typedef enum {
    /* Control */
    OP_NOP       = 0,
    OP_HALT      = 42,

    /* Memory */
    OP_LOAD      = 1,   /* Load 32-bit from data[imm8]     */
    OP_STORE     = 2,   /* Store 32-bit to data[imm8]      */
    OP_LOAD8     = 3,   /* Load signed 8-bit                */
    OP_LOAD8U    = 4,   /* Load unsigned 8-bit              */
    OP_STORE8    = 5,   /* Store 8-bit                      */

    /* Arithmetic */
    OP_ADD_I32   = 6,
    OP_SUB_I32   = 7,
    OP_MUL_I32   = 8,

    /* Bitwise */
    OP_AND       = 9,
    OP_OR        = 10,
    OP_XOR       = 11,

    /* Shift */
    OP_SLL       = 12,
    OP_SRL       = 13,
    OP_SRA       = 14,

    /* Extrema */
    OP_MIN_I32   = 15,
    OP_MAX_I32   = 16,

    /* Unary */
    OP_CLZ       = 17,
    OP_ABS_I32   = 18,

    /* Comparison */
    OP_CMP_EQ    = 19,
    OP_CMP_LT    = 20,
    OP_CMP_GT    = 21,
    OP_CMP_LE    = 22,
    OP_CMP_GE    = 23,

    /* Control flow */
    OP_BRA       = 24,
    OP_BRA_COND  = 25,
    OP_CALL      = 26,
    OP_RET       = 27,

    /* Stack */
    OP_PUSH      = 28,
    OP_POP       = 29,

    /* INT8 x8 packed operations */
    OP_INT8X8_LD  = 30,
    OP_INT8X8_CMP = 31,
    OP_INT8X8_AND = 32,
    OP_INT8X8_OR  = 33,
    OP_INT8X8_XOR = 34,

    /* FPU (single-precision only, use sparingly) */
    OP_FPU_ADD   = 35,
    OP_FPU_SUB   = 36,
    OP_FPU_MUL   = 37,
    OP_FPU_CMP   = 38,
    OP_FPU_CVT   = 39,
    OP_FPU_CVTI  = 40,

    /* Debug / assertion */
    OP_ASSERT    = 41,
    OP_TRACE     = 43,  /* Actually index 42 is HALT, 43 is TRACE if extended */
} flux_opcode_t;

/* ------------------------------------------------------------------ */
/*  VM State                                                           */
/* ------------------------------------------------------------------ */

typedef struct {
    uint16_t pc;                                /* Program counter             */
    uint16_t sp;                                /* Stack pointer               */
    int32_t  stack[FLUX_STACK_DEPTH];           /* Evaluation stack            */
    const uint8_t *bytecode;                    /* Bytecode (DRAM, 4-aligned)  */
    const uint8_t *constraints;                 /* Constraint table (DRAM)     */
    uint8_t *data_ram;                          /* Data RAM (256 bytes)        */
    uint16_t set_offsets[FLUX_MAX_SETS];        /* Bytecode offset per set     */
    uint16_t set_counts[FLUX_MAX_SETS];         /* Constraint count per set    */
    uint16_t num_sets;                          /* Active constraint sets      */
    volatile uint32_t total_checks;             /* Cumulative checks           */
    volatile uint32_t total_violations;         /* Cumulative violations       */
    volatile uint64_t total_cycles;             /* Cumulative CPU cycles       */
    volatile bool    halted;                    /* VM halt flag                */
} flux_vm_state_t;

/* ------------------------------------------------------------------ */
/*  Inter-core IPC (lock-free, single-producer single-consumer)         */
/* ------------------------------------------------------------------ */

#define IPC_CMD_CHECK_SET    1
#define IPC_CMD_RELOAD_BC    2
#define IPC_CMD_GET_STATS    3
#define IPC_CMD_PAUSE        4
#define IPC_CMD_RESUME       5

typedef struct {
    volatile uint32_t command;
    volatile uint32_t param;
    volatile int32_t  result;
    volatile uint32_t sequence;     /* ACK sequence number */
} flux_ipc_slot_t;

/* ------------------------------------------------------------------ */
/*  Persistent state (RTC FAST memory — survives deep sleep)            */
/* ------------------------------------------------------------------ */

typedef struct {
    uint32_t last_check_count;
    uint32_t last_violation_count;
    uint32_t checksum;             /* CRC32 for integrity */
} flux_persistent_state_t;

/* ------------------------------------------------------------------ */
/*  Placement macros                                                   */
/* ------------------------------------------------------------------ */

/* Hot path: force into IRAM */
#define FLUX_HOT     IRAM_ATTR

/* DRAM data with cache-line alignment */
#define FLUX_ALIGNED(x)  __attribute__((aligned(x)))

/* RTC-persistent data */
#define FLUX_PERSISTENT  __attribute__((section(".flux.persistent")))

/* ------------------------------------------------------------------ */
/*  Public API                                                         */
/* ------------------------------------------------------------------ */

/**
 * Initialize the FLUX VM with bytecode and constraint data.
 * Both must remain valid for the lifetime of the VM.
 */
flux_status_t flux_vm_init(flux_vm_state_t *vm,
                           const uint8_t *bytecode,
                           const uint8_t *constraints);

/**
 * Reload bytecode (e.g., OTA update). Thread-safe via IPC.
 */
flux_status_t flux_vm_reload(flux_vm_state_t *vm, const uint8_t *new_bytecode);

/**
 * Run a single constraint set. Returns violation bitmap (0 = all pass).
 * Entire function lives in IRAM for zero cache-miss dispatch.
 */
uint32_t FLUX_HOT flux_run_set(flux_vm_state_t *vm, uint32_t set_id);

/**
 * Run all constraint sets sequentially. Returns OR'd violation bitmap.
 */
uint32_t FLUX_HOT flux_run_all(flux_vm_state_t *vm);

/**
 * Get aggregate statistics (check count, violation count, cycles).
 */
uint32_t flux_vm_get_stats(const flux_vm_state_t *vm);

/* INT8 x8 parallel comparison routines — all in IRAM */
flux_int8_result_t FLUX_HOT flux_int8x8_lt(flux_int8x8_t a, flux_int8x8_t b);
flux_int8_result_t FLUX_HOT flux_int8x8_eq(flux_int8x8_t a, flux_int8x8_t b);
flux_int8_result_t FLUX_HOT flux_int8x8_range(flux_int8x8_t val,
                                               flux_int8x8_t lo,
                                               flux_int8x8_t hi);

/**
 * Launch the FLUX VM on Core 1. Creates FreeRTOS task at max priority.
 */
void flux_start_vm(void);

/**
 * Send IPC command from Core 0 to Core 1 FLUX task.
 * Blocks until ACK or timeout.
 */
int flux_send_command(uint32_t cmd, uint32_t param, uint32_t timeout_ms);

#ifdef __cplusplus
}
#endif
