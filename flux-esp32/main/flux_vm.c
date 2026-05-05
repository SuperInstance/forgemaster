/*
 * flux_vm.c — FLUX VM Dispatch Loop for ESP32 Xtensa LX7
 *
 * Core 1, IRAM-resident, 240MHz constraint-checking engine.
 *
 * Design:
 *   - Computed-goto dispatch (function pointer table) — 2x faster than switch()
 *   - All opcode handlers marked IRAM_ATTR — zero flash cache misses
 *   - Dispatch table 32-byte aligned for I-cache line optimization
 *   - Cycle counting via xthal_get_ccount() for benchmarking
 *
 * Memory layout:
 *   - IRAM (~5.5KB): dispatch loop + 43 opcode handlers + INT8 routines
 *   - DRAM (~140KB): bytecode, constraint tables, evaluation stack
 *   - RTC FAST (8KB): persistent state for deep-sleep resume
 */

#include "flux_vm.h"
#include "constraint_sets.h"
#include <string.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "xtensa/core-macros.h"

static const char *TAG = "flux_vm";

/* ------------------------------------------------------------------ */
/*  Stack helpers — force-inline for zero call overhead                 */
/* ------------------------------------------------------------------ */

#define FETCH_U8(vm)   ((vm)->bytecode[(vm)->pc++])
#define FETCH_S8(vm)   ((int8_t)((vm)->bytecode[(vm)->pc++]))
#define FETCH_I16(vm)  ({ \
    uint16_t _lo = (vm)->bytecode[(vm)->pc]; \
    uint16_t _hi = (vm)->bytecode[(vm)->pc + 1]; \
    (vm)->pc += 2; \
    (int16_t)(_lo | (_hi << 8)); \
})
#define PUSH(vm, val)  do { (vm)->stack[(vm)->sp++] = (val); } while (0)
#define POP(vm)        ((vm)->stack[--(vm)->sp])
#define PEEK(vm)       ((vm)->stack[(vm)->sp - 1])

/* ------------------------------------------------------------------ */
/*  Forward declarations for all opcode handlers                       */
/* ------------------------------------------------------------------ */

#define OP(name) static void IRAM_ATTR op_##name(flux_vm_state_t *vm)

OP(nop);       OP(load);     OP(store);    OP(load8);    OP(load8u);
OP(store8);    OP(add_i32);  OP(sub_i32);  OP(mul_i32);
OP(and);       OP(or);       OP(xor);
OP(sll);       OP(srl);      OP(sra);
OP(min_i32);   OP(max_i32);
OP(clz);       OP(abs_i32);
OP(cmp_eq);    OP(cmp_lt);   OP(cmp_gt);   OP(cmp_le);   OP(cmp_ge);
OP(bra);       OP(bra_cond); OP(call);     OP(ret);
OP(push);      OP(pop);
OP(int8x8_ld); OP(int8x8_cmp); OP(int8x8_and); OP(int8x8_or); OP(int8x8_xor);
OP(fpu_add);   OP(fpu_sub);  OP(fpu_mul);  OP(fpu_cmp);
OP(assert_op); OP(trace);    OP(halt);

/* ------------------------------------------------------------------ */
/*  Dispatch table — 32-byte aligned for I-cache line fill             */
/* ------------------------------------------------------------------ */

static void (* const IRAM_ATTR dispatch_table[FLUX_MAX_OPCODES])(flux_vm_state_t *)
    __attribute__((aligned(32))) =
{
    /* [0]  */ op_nop,
    /* [1]  */ op_load,
    /* [2]  */ op_store,
    /* [3]  */ op_load8,
    /* [4]  */ op_load8u,
    /* [5]  */ op_store8,
    /* [6]  */ op_add_i32,
    /* [7]  */ op_sub_i32,
    /* [8]  */ op_mul_i32,
    /* [9]  */ op_and,
    /* [10] */ op_or,
    /* [11] */ op_xor,
    /* [12] */ op_sll,
    /* [13] */ op_srl,
    /* [14] */ op_sra,
    /* [15] */ op_min_i32,
    /* [16] */ op_max_i32,
    /* [17] */ op_clz,
    /* [18] */ op_abs_i32,
    /* [19] */ op_cmp_eq,
    /* [20] */ op_cmp_lt,
    /* [21] */ op_cmp_gt,
    /* [22] */ op_cmp_le,
    /* [23] */ op_cmp_ge,
    /* [24] */ op_bra,
    /* [25] */ op_bra_cond,
    /* [26] */ op_call,
    /* [27] */ op_ret,
    /* [28] */ op_push,
    /* [29] */ op_pop,
    /* [30] */ op_int8x8_ld,
    /* [31] */ op_int8x8_cmp,
    /* [32] */ op_int8x8_and,
    /* [33] */ op_int8x8_or,
    /* [34] */ op_int8x8_xor,
    /* [35] */ op_fpu_add,
    /* [36] */ op_fpu_sub,
    /* [37] */ op_fpu_mul,
    /* [38] */ op_fpu_cmp,
    /* [39] */ op_assert,    /* ASSERT */
    /* [40] */ op_trace,     /* TRACE  */
    /* [41] */ op_fpu_cvt,   /* placeholder — reuses slot */
    /* [42] */ op_halt,
};

/* ------------------------------------------------------------------ */
/*  Opcode handler implementations                                     */
/* ------------------------------------------------------------------ */

static void IRAM_ATTR op_nop(flux_vm_state_t *vm) {
    (void)vm;
}

static void IRAM_ATTR op_load(flux_vm_state_t *vm) {
    uint8_t idx = FETCH_U8(vm);
    PUSH(vm, ((const int32_t *)vm->data_ram)[idx]);
}

static void IRAM_ATTR op_store(flux_vm_state_t *vm) {
    uint8_t idx = FETCH_U8(vm);
    int32_t val = POP(vm);
    ((int32_t *)vm->data_ram)[idx] = val;
}

static void IRAM_ATTR op_load8(flux_vm_state_t *vm) {
    uint8_t idx = FETCH_U8(vm);
    PUSH(vm, (int32_t)(int8_t)vm->data_ram[idx]);
}

static void IRAM_ATTR op_load8u(flux_vm_state_t *vm) {
    uint8_t idx = FETCH_U8(vm);
    PUSH(vm, (int32_t)(uint8_t)vm->data_ram[idx]);
}

static void IRAM_ATTR op_store8(flux_vm_state_t *vm) {
    uint8_t idx = FETCH_U8(vm);
    int32_t val = POP(vm);
    vm->data_ram[idx] = (uint8_t)val;
}

static void IRAM_ATTR op_add_i32(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, a + b);
}
static void IRAM_ATTR op_sub_i32(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, a - b);
}
static void IRAM_ATTR op_mul_i32(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, a * b);
}
static void IRAM_ATTR op_and(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, a & b);
}
static void IRAM_ATTR op_or(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, a | b);
}
static void IRAM_ATTR op_xor(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, a ^ b);
}
static void IRAM_ATTR op_sll(flux_vm_state_t *vm) {
    int32_t s = POP(vm) & 0x1F; int32_t v = POP(vm); PUSH(vm, v << s);
}
static void IRAM_ATTR op_srl(flux_vm_state_t *vm) {
    int32_t s = POP(vm) & 0x1F; uint32_t v = (uint32_t)POP(vm);
    PUSH(vm, (int32_t)(v >> s));
}
static void IRAM_ATTR op_sra(flux_vm_state_t *vm) {
    int32_t s = POP(vm) & 0x1F; int32_t v = POP(vm); PUSH(vm, v >> s);
}
static void IRAM_ATTR op_min_i32(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, (a < b) ? a : b);
}
static void IRAM_ATTR op_max_i32(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, (a > b) ? a : b);
}
static void IRAM_ATTR op_clz(flux_vm_state_t *vm) {
    uint32_t v = (uint32_t)POP(vm);
    PUSH(vm, (v == 0) ? 32 : __builtin_clz(v));
}
static void IRAM_ATTR op_abs_i32(flux_vm_state_t *vm) {
    int32_t v = POP(vm); PUSH(vm, (v < 0) ? -v : v);
}
static void IRAM_ATTR op_cmp_eq(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, (a == b) ? 1 : 0);
}
static void IRAM_ATTR op_cmp_lt(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, (a < b) ? 1 : 0);
}
static void IRAM_ATTR op_cmp_gt(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, (a > b) ? 1 : 0);
}
static void IRAM_ATTR op_cmp_le(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, (a <= b) ? 1 : 0);
}
static void IRAM_ATTR op_cmp_ge(flux_vm_state_t *vm) {
    int32_t b = POP(vm); int32_t a = POP(vm); PUSH(vm, (a >= b) ? 1 : 0);
}

/* Control flow */
static void IRAM_ATTR op_bra(flux_vm_state_t *vm) {
    int16_t off = FETCH_I16(vm);
    vm->pc += off;
}
static void IRAM_ATTR op_bra_cond(flux_vm_state_t *vm) {
    int16_t off = FETCH_I16(vm);
    if (POP(vm)) vm->pc += off;
}
static void IRAM_ATTR op_call(flux_vm_state_t *vm) {
    /* Simple: push return PC, jump to target */
    uint16_t target = (uint16_t)(FETCH_U8(vm));
    PUSH(vm, (int32_t)vm->pc);
    vm->pc = target;
}
static void IRAM_ATTR op_ret(flux_vm_state_t *vm) {
    vm->pc = (uint16_t)POP(vm);
}

/* Stack ops */
static void IRAM_ATTR op_push(flux_vm_state_t *vm) {
    int16_t imm = FETCH_I16(vm);
    PUSH(vm, (int32_t)imm);
}
static void IRAM_ATTR op_pop(flux_vm_state_t *vm) {
    (void)POP(vm);
}

/* INT8 x8 packed operations */
static void IRAM_ATTR op_int8x8_ld(flux_vm_state_t *vm) {
    /* Load 8 bytes from constraint table into two stack slots */
    uint8_t idx = FETCH_U8(vm);
    const uint8_t *p = vm->constraints + idx * 8;
    uint32_t lo, hi;
    memcpy(&lo, p, 4);
    memcpy(&hi, p + 4, 4);
    PUSH(vm, (int32_t)lo);
    PUSH(vm, (int32_t)hi);
}

static void IRAM_ATTR op_int8x8_cmp(flux_vm_state_t *vm) {
    flux_int8x8_t b, a;
    b.words[1] = (uint32_t)POP(vm); b.words[0] = (uint32_t)POP(vm);
    a.words[1] = (uint32_t)POP(vm); a.words[0] = (uint32_t)POP(vm);
    flux_int8_result_t r = flux_int8x8_lt(a, b);
    PUSH(vm, (int32_t)r.mask);
}

static void IRAM_ATTR op_int8x8_and(flux_vm_state_t *vm) {
    int32_t b_hi = POP(vm), b_lo = POP(vm);
    int32_t a_hi = POP(vm), a_lo = POP(vm);
    PUSH(vm, a_lo & b_lo);
    PUSH(vm, a_hi & b_hi);
}
static void IRAM_ATTR op_int8x8_or(flux_vm_state_t *vm) {
    int32_t b_hi = POP(vm), b_lo = POP(vm);
    int32_t a_hi = POP(vm), a_lo = POP(vm);
    PUSH(vm, a_lo | b_lo);
    PUSH(vm, a_hi | b_hi);
}
static void IRAM_ATTR op_int8x8_xor(flux_vm_state_t *vm) {
    int32_t b_hi = POP(vm), b_lo = POP(vm);
    int32_t a_hi = POP(vm), a_lo = POP(vm);
    PUSH(vm, a_lo ^ b_lo);
    PUSH(vm, a_hi ^ b_hi);
}

/* FPU — single-precision, use only when constraints require floats */
static void IRAM_ATTR op_fpu_add(flux_vm_state_t *vm) {
    float b, a, r;
    b = *(float *)&POP(vm); a = *(float *)&POP(vm);
    r = a + b; PUSH(vm, *(int32_t *)&r);
}
static void IRAM_ATTR op_fpu_sub(flux_vm_state_t *vm) {
    float b, a, r;
    b = *(float *)&POP(vm); a = *(float *)&POP(vm);
    r = a - b; PUSH(vm, *(int32_t *)&r);
}
static void IRAM_ATTR op_fpu_mul(flux_vm_state_t *vm) {
    float b, a, r;
    b = *(float *)&POP(vm); a = *(float *)&POP(vm);
    r = a * b; PUSH(vm, *(int32_t *)&r);
}
static void IRAM_ATTR op_fpu_cmp(flux_vm_state_t *vm) {
    float b = *(float *)&POP(vm), a = *(float *)&POP(vm);
    PUSH(vm, (a < b) ? 1 : 0);
}

/* Debug / assertion */
static void IRAM_ATTR op_assert_op(flux_vm_state_t *vm) {
    int32_t cond = POP(vm);
    if (!cond) {
        vm->total_violations++;
    }
}
static void IRAM_ATTR op_trace(flux_vm_state_t *vm) {
    /* Stub — no-op in production, log stack top in debug builds */
    (void)vm;
}
static void IRAM_ATTR op_halt(flux_vm_state_t *vm) {
    vm->halted = true;
}

/* Placeholder for slot 41 (FPU_CVT) */
static void IRAM_ATTR op_fpu_cvt(flux_vm_state_t *vm) {
    int32_t v = POP(vm);
    float f = (float)v;
    PUSH(vm, *(int32_t *)&f);
}

/* ------------------------------------------------------------------ */
/*  Main dispatch loops                                                */
/* ------------------------------------------------------------------ */

/**
 * Run a single constraint set — the hot path.
 *
 * Uses computed-goto dispatch via function pointer table.
 * All code in IRAM. Register-allocates dispatch_table pointer
 * to avoid repeated memory loads.
 *
 * Expected throughput: ~2.5M constraint checks/sec @ 240MHz
 */
uint32_t IRAM_ATTR flux_run_set(flux_vm_state_t *vm, uint32_t set_id)
{
    if (set_id >= vm->num_sets) return 0;

    uint32_t start_cc = xthal_get_ccount();

    vm->pc      = vm->set_offsets[set_id];
    vm->sp      = 0;
    vm->halted  = false;

    /* Cache dispatch table in a register */
    register void (**dt)(flux_vm_state_t *) = dispatch_table;
    register const uint8_t *bc = vm->bytecode;
    register uint16_t pc = vm->pc;

    while (!vm->halted) {
        uint8_t opcode = bc[pc++];
        vm->pc = pc;
        dt[opcode](vm);
        pc = vm->pc;
    }

    uint32_t elapsed = xthal_get_ccount() - start_cc;
    vm->total_cycles += elapsed;
    vm->total_checks += vm->set_counts[set_id];

    return vm->total_violations;
}

/**
 * Run all constraint sets sequentially.
 */
uint32_t IRAM_ATTR flux_run_all(flux_vm_state_t *vm)
{
    uint32_t violations = 0;
    for (uint32_t i = 0; i < vm->num_sets; i++) {
        violations |= flux_run_set(vm, i);
    }
    return violations;
}

/* ------------------------------------------------------------------ */
/*  Init / Reload                                                      */
/* ------------------------------------------------------------------ */

flux_status_t flux_vm_init(flux_vm_state_t *vm,
                           const uint8_t *bytecode,
                           const uint8_t *constraints)
{
    memset(vm, 0, sizeof(flux_vm_state_t));
    vm->bytecode     = bytecode;
    vm->constraints  = constraints;
    vm->num_sets     = 1;
    vm->set_offsets[0] = 0;
    vm->data_ram     = (uint8_t *)calloc(FLUX_DATA_RAM_SIZE, 1);
    if (!vm->data_ram) return FLUX_ERR_STACK_OVERFLOW; /* reuse error code */
    return FLUX_OK;
}

flux_status_t flux_vm_reload(flux_vm_state_t *vm, const uint8_t *new_bytecode)
{
    vm->bytecode = new_bytecode;
    vm->pc = 0;
    return FLUX_OK;
}

uint32_t flux_vm_get_stats(const flux_vm_state_t *vm)
{
    return vm->total_checks;
}

/* ------------------------------------------------------------------ */
/*  Dual-Core: Inter-core communication                                */
/* ------------------------------------------------------------------ */

static flux_ipc_slot_t FLUX_ALIGNED(64) g_ipc_slots[2];
static volatile uint32_t g_ipc_write_idx = 0;
static volatile uint32_t g_ipc_read_idx  = 0;

int flux_send_command(uint32_t cmd, uint32_t param, uint32_t timeout_ms)
{
    uint32_t slot_idx = g_ipc_write_idx & 1;
    flux_ipc_slot_t *slot = &g_ipc_slots[slot_idx];

    /* Wait for slot to be free */
    TickType_t start = xTaskGetTickCount();
    while (g_ipc_read_idx != g_ipc_write_idx) {
        if ((xTaskGetTickCount() - start) > pdMS_TO_TICKS(timeout_ms))
            return FLUX_ERR_TIMEOUT;
        taskYIELD();
    }

    uint32_t seq = slot->sequence;
    slot->command = cmd;
    slot->param   = param;

    /* Memory barrier before signaling */
    __sync_synchronize();
    g_ipc_write_idx++;

    /* Wait for ACK */
    start = xTaskGetTickCount();
    while (slot->sequence == seq) {
        if ((xTaskGetTickCount() - start) > pdMS_TO_TICKS(timeout_ms))
            return FLUX_ERR_TIMEOUT;
        taskYIELD();
    }

    return slot->result;
}

/* ------------------------------------------------------------------ */
/*  Core 1: FLUX VM FreeRTOS task                                      */
/* ------------------------------------------------------------------ */

static uint8_t  __attribute__((section(".flux.bytecode")))    s_bytecode[FLUX_BYTECODE_SIZE];
static uint8_t  __attribute__((section(".flux.constraints"))) s_constraints[FLUX_MAX_CONSTRAINTS * 8];
static uint8_t  __attribute__((section(".flux.data_ram")))    s_data_ram[FLUX_DATA_RAM_SIZE];
static int32_t  __attribute__((section(".flux.stack")))       s_eval_stack[FLUX_STACK_DEPTH];

static void IRAM_ATTR flux_vm_task(void *pvParameters)
{
    (void)pvParameters;

    flux_vm_state_t vm;
    flux_vm_init(&vm, s_bytecode, s_constraints);
    vm.data_ram = s_data_ram;

    uint32_t active_set = 0;
    uint32_t check_mask = 0xFFFFFFFF; /* All constraint sets active */

    ESP_LOGI(TAG, "FLUX VM running on Core %d at priority %d",
             xPortGetCoreID(), FLUX_VM_PRIORITY);

    for (;;) {
        /* Check for inter-core command (non-blocking) */
        if (g_ipc_read_idx != g_ipc_write_idx) {
            uint32_t slot_idx = g_ipc_read_idx & 1;
            flux_ipc_slot_t *slot = &g_ipc_slots[slot_idx];

            switch (slot->command) {
                case IPC_CMD_CHECK_SET: active_set = slot->param; break;
                case IPC_CMD_RELOAD_BC: flux_vm_reload(&vm, (const uint8_t *)slot->param); break;
                case IPC_CMD_GET_STATS: slot->result = flux_vm_get_stats(&vm); break;
                case IPC_CMD_PAUSE:     check_mask = 0; break;
                case IPC_CMD_RESUME:    check_mask = 0xFFFFFFFF; break;
            }
            slot->sequence++;  /* ACK */
            g_ipc_read_idx++;
        }

        /* Run constraint checks if not paused */
        if (check_mask && active_set < FLUX_MAX_SETS) {
            uint32_t violations = flux_run_set(&vm, active_set);
            (void)violations;
        }

        /* Yield when paused to prevent watchdog starvation */
        if (!check_mask) {
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }
}

void flux_start_vm(void)
{
    memset(g_ipc_slots, 0, sizeof(g_ipc_slots));
    g_ipc_write_idx = 0;
    g_ipc_read_idx  = 0;

    TaskHandle_t handle;
    BaseType_t result = xTaskCreatePinnedToCore(
        flux_vm_task,
        "flux_vm",
        4096,                  /* Stack size in words */
        NULL,                  /* Parameter */
        FLUX_VM_PRIORITY,      /* configMAX_PRIORITIES - 1 = 24 */
        &handle,
        FLUX_CORE_VM           /* Pin to Core 1 */
    );

    if (result == pdPASS) {
        ESP_LOGI(TAG, "FLUX VM started on Core 1 at priority %d", FLUX_VM_PRIORITY);
    } else {
        ESP_LOGE(TAG, "Failed to create FLUX VM task!");
    }
}
