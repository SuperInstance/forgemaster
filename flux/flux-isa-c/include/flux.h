#ifndef FLUX_H
#define FLUX_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Opcodes ─────────────────────────────────────────────────────── */

typedef enum {
    FLUX_ADD       = 0x01,
    FLUX_SUB       = 0x02,
    FLUX_MUL       = 0x03,
    FLUX_DIV       = 0x04,
    FLUX_MOD       = 0x05,

    FLUX_ASSERT    = 0x10,
    FLUX_CHECK     = 0x11,
    FLUX_VALIDATE  = 0x12,
    FLUX_REJECT    = 0x13,

    FLUX_JUMP      = 0x20,
    FLUX_BRANCH    = 0x21,
    FLUX_CALL      = 0x22,
    FLUX_RETURN    = 0x23,
    FLUX_HALT      = 0x24,

    FLUX_LOAD      = 0x30,
    FLUX_STORE     = 0x31,
    FLUX_PUSH      = 0x32,
    FLUX_POP       = 0x33,
    FLUX_SWAP      = 0x34,

    FLUX_SNAP      = 0x40,
    FLUX_QUANTIZE  = 0x41,
    FLUX_CAST      = 0x42,
    FLUX_PROMOTE   = 0x43,

    FLUX_AND       = 0x50,
    FLUX_OR        = 0x51,
    FLUX_NOT       = 0x52,
    FLUX_XOR       = 0x53,

    FLUX_EQ        = 0x60,
    FLUX_NEQ       = 0x61,
    FLUX_LT        = 0x62,
    FLUX_GT        = 0x63,
    FLUX_LTE       = 0x64,
    FLUX_GTE       = 0x65,

    FLUX_NOP       = 0x70,
    FLUX_DEBUG     = 0x71,
    FLUX_TRACE     = 0x72,
    FLUX_DUMP      = 0x73
} flux_opcode_t;

/* ── Core types ───────────────────────────────────────────────────── */

#define FLUX_MAX_OPERANDS  4
#define FLUX_LABEL_SIZE    32
#define FLUX_MAX_OUTPUTS   64
#define FLUX_TRACE_SNAPSHOT 8

typedef struct {
    flux_opcode_t opcode;
    int           operand_count;
    double        operands[FLUX_MAX_OPERANDS];
    char          label[FLUX_LABEL_SIZE];
} flux_instruction_t;

typedef struct {
    int                 instruction_count;
    int                 capacity;
    flux_instruction_t *instructions;
} flux_bytecode_t;

typedef struct {
    int    step;
    int    opcode;
    double stack_before[FLUX_TRACE_SNAPSHOT];
    double stack_after[FLUX_TRACE_SNAPSHOT];
    int    constraint_result; /* -1 = not a constraint, 0 = fail, 1 = pass */
} flux_trace_entry_t;

typedef struct {
    int    output_count;
    double outputs[FLUX_MAX_OUTPUTS];
    int    constraints_satisfied;
    int    trace_count;
    flux_trace_entry_t *trace;
} flux_result_t;

/* ── VM (opaque-ish, caller allocates) ────────────────────────────── */

#define FLUX_STACK_SIZE    256
#define FLUX_CALL_DEPTH    64
#define FLUX_TRACE_DEFAULT 1024
#define FLUX_REGISTERS     16

typedef struct {
    double          stack[FLUX_STACK_SIZE];
    int             sp;
    int             call_stack[FLUX_CALL_DEPTH];
    int             csp;
    double          registers[FLUX_REGISTERS];
    flux_trace_entry_t *trace_buf;
    int             trace_cap;
    int             trace_len;
    int             halted;
    int             constraint_failures;
    int             constraint_checks;
    double         *outputs;
    int             output_count;
    int             output_cap;
    int             flags;          /* runtime flags */
} flux_vm_t;

/* ── API ──────────────────────────────────────────────────────────── */

/* Initialise a VM. trace_cap = 0 → use default (1024). */
int  flux_vm_init(flux_vm_t *vm, int trace_cap);
/* Execute bytecode on vm, result written to *out. Returns 0 on success. */
int  flux_vm_execute(flux_vm_t *vm, const flux_bytecode_t *bc, flux_result_t *out);
/* Release VM resources. */
void flux_vm_destroy(flux_vm_t *vm);

/* Bytecode encode / decode.
   encode returns malloc'd buffer; caller must free.
   decode fills *bc; caller must flux_bytecode_free when done. */
size_t flux_bytecode_encode(const flux_bytecode_t *bc, uint8_t **out_buf);
int    flux_bytecode_decode(const uint8_t *buf, size_t len, flux_bytecode_t *bc);
void   flux_bytecode_free(flux_bytecode_t *bc);

/* Disassemble one instruction into human-readable dst (dst_size bytes). */
void flux_disassemble(const flux_instruction_t *inst, char *dst, size_t dst_size);
/* Disassemble an entire bytecode block, returns malloc'd string. */
char *flux_disassemble_all(const flux_bytecode_t *bc);

/* Bytecode builder helpers. */
int flux_bytecode_init(flux_bytecode_t *bc, int initial_cap);
int flux_bytecode_push(flux_bytecode_t *bc, const flux_instruction_t *inst);
void flux_bytecode_reset(flux_bytecode_t *bc);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_H */
