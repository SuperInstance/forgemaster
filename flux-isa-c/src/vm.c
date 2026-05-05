#include "flux.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

/* ── Helpers ──────────────────────────────────────────────────────── */

static void trace_push(flux_vm_t *vm, int step, flux_opcode_t opcode,
                        const double *sb, int sb_len,
                        const double *sa, int sa_len,
                        int constraint)
{
    if (!vm->trace_buf || vm->trace_len >= vm->trace_cap) return;
    flux_trace_entry_t *e = &vm->trace_buf[vm->trace_len++];
    e->step = step;
    e->opcode = (int)opcode;
    e->constraint_result = constraint;
    {
        int i, n = sb_len < FLUX_TRACE_SNAPSHOT ? sb_len : FLUX_TRACE_SNAPSHOT;
        for (i = 0; i < FLUX_TRACE_SNAPSHOT; i++) e->stack_before[i] = 0;
        for (i = 0; i < n; i++) e->stack_before[i] = sb[i];
    }
    {
        int i, n = sa_len < FLUX_TRACE_SNAPSHOT ? sa_len : FLUX_TRACE_SNAPSHOT;
        for (i = 0; i < FLUX_TRACE_SNAPSHOT; i++) e->stack_after[i] = 0;
        for (i = 0; i < n; i++) e->stack_after[i] = sa[i];
    }
}

static void snapshot_stack(flux_vm_t *vm, double *buf, int *out_len) {
    int n = vm->sp < FLUX_TRACE_SNAPSHOT ? vm->sp : FLUX_TRACE_SNAPSHOT;
    for (int i = 0; i < n; i++) buf[i] = vm->stack[i];
    *out_len = n;
}

static int push_output(flux_vm_t *vm, double val) {
    if (vm->output_count >= vm->output_cap) {
        int new_cap = vm->output_cap * 2;
        double *tmp = (double *)realloc(vm->outputs, (size_t)new_cap * sizeof(double));
        if (!tmp) return -1;
        vm->outputs = tmp;
        vm->output_cap = new_cap;
    }
    vm->outputs[vm->output_count++] = val;
    return 0;
}

#define BINOP(vm, op) do { \
    if ((vm)->sp < 2) return -1; \
    double b = (vm)->stack[--(vm)->sp]; \
    double a = (vm)->stack[--(vm)->sp]; \
    (vm)->stack[(vm)->sp++] = (a op b); \
} while(0)

#define CMPOP(vm, op) do { \
    if ((vm)->sp < 2) return -1; \
    double b = (vm)->stack[--(vm)->sp]; \
    double a = (vm)->stack[--(vm)->sp]; \
    (vm)->stack[(vm)->sp++] = (a op b) ? 1.0 : 0.0; \
} while(0)

/* ── Public API ───────────────────────────────────────────────────── */

int flux_vm_init(flux_vm_t *vm, int trace_cap) {
    if (!vm) return -1;
    memset(vm, 0, sizeof(*vm));
    vm->trace_cap = trace_cap > 0 ? trace_cap : FLUX_TRACE_DEFAULT;
    vm->trace_buf = (flux_trace_entry_t *)calloc((size_t)vm->trace_cap, sizeof(flux_trace_entry_t));
    if (!vm->trace_buf) return -1;
    vm->output_cap = 64;
    vm->outputs = (double *)calloc((size_t)vm->output_cap, sizeof(double));
    if (!vm->outputs) { free(vm->trace_buf); vm->trace_buf = NULL; return -1; }
    return 0;
}

void flux_vm_destroy(flux_vm_t *vm) {
    if (!vm) return;
    free(vm->trace_buf);
    free(vm->outputs);
    memset(vm, 0, sizeof(*vm));
}

int flux_vm_execute(flux_vm_t *vm, const flux_bytecode_t *bc, flux_result_t *out) {
    if (!vm || !bc || !out) return -1;

    /* Reset runtime state but keep buffers */
    vm->sp = 0;
    vm->csp = 0;
    vm->trace_len = 0;
    vm->halted = 0;
    vm->constraint_failures = 0;
    vm->constraint_checks = 0;
    vm->output_count = 0;
    memset(vm->stack, 0, sizeof(vm->stack));
    memset(vm->registers, 0, sizeof(vm->registers));

    memset(out, 0, sizeof(*out));

    int pc = 0;
    int step = 0;

    while (pc < bc->instruction_count && !vm->halted) {
        const flux_instruction_t *inst = &bc->instructions[pc];
        flux_opcode_t op = inst->opcode;

        double before[FLUX_TRACE_SNAPSHOT];
        int before_len = 0;
        snapshot_stack(vm, before, &before_len);

        int constraint = -1; /* not a constraint by default */

        switch (op) {
        /* ── Arithmetic ──────────────────────────────────────── */
        case FLUX_ADD:  BINOP(vm, +); break;
        case FLUX_SUB:  BINOP(vm, -); break;
        case FLUX_MUL:  BINOP(vm, *); break;
        case FLUX_DIV:
            if (vm->sp < 2) return -1;
            {
                double b = vm->stack[--vm->sp];
                double a = vm->stack[--vm->sp];
                if (b == 0.0) return -2; /* division by zero */
                vm->stack[vm->sp++] = a / b;
            }
            break;
        case FLUX_MOD:
            if (vm->sp < 2) return -1;
            {
                double b = vm->stack[--vm->sp];
                double a = vm->stack[--vm->sp];
                if (b == 0.0) return -2;
                vm->stack[vm->sp++] = fmod(a, b);
            }
            break;

        /* ── Constraints ─────────────────────────────────────── */
        case FLUX_ASSERT:
            if (vm->sp < 1) return -1;
            vm->constraint_checks++;
            constraint = (vm->stack[vm->sp - 1] != 0.0) ? 1 : 0;
            if (!constraint) vm->constraint_failures++;
            break;
        case FLUX_CHECK:
            if (vm->sp < 1) return -1;
            vm->constraint_checks++;
            constraint = (vm->stack[vm->sp - 1] != 0.0) ? 1 : 0;
            if (!constraint) vm->constraint_failures++;
            break;
        case FLUX_VALIDATE:
            if (vm->sp < 1) return -1;
            {
                double val = vm->stack[vm->sp - 1];
                double lo = inst->operand_count > 0 ? inst->operands[0] : 0.0;
                double hi = inst->operand_count > 1 ? inst->operands[1] : 1.0;
                vm->constraint_checks++;
                constraint = (val >= lo && val <= hi) ? 1 : 0;
                if (!constraint) vm->constraint_failures++;
            }
            break;
        case FLUX_REJECT:
            if (vm->sp < 1) return -1;
            vm->constraint_checks++;
            constraint = (vm->stack[vm->sp - 1] == 0.0) ? 1 : 0;
            if (!constraint) vm->constraint_failures++;
            break;

        /* ── Control flow ────────────────────────────────────── */
        case FLUX_JUMP:
            pc = (inst->operand_count > 0) ? (int)inst->operands[0] - 1 : pc;
            break;
        case FLUX_BRANCH:
            if (vm->sp < 1) return -1;
            {
                double cond = vm->stack[--vm->sp];
                if (cond != 0.0 && inst->operand_count > 0)
                    pc = (int)inst->operands[0] - 1;
            }
            break;
        case FLUX_CALL:
            if (vm->csp >= FLUX_CALL_DEPTH) return -3;
            vm->call_stack[vm->csp++] = pc;
            if (inst->operand_count > 0)
                pc = (int)inst->operands[0] - 1;
            break;
        case FLUX_RETURN:
            if (vm->csp <= 0) return -4;
            pc = vm->call_stack[--vm->csp];
            break;
        case FLUX_HALT:
            vm->halted = 1;
            break;

        /* ── Memory / Stack ──────────────────────────────────── */
        case FLUX_LOAD:
            if (inst->operand_count > 0) {
                int reg = (int)inst->operands[0];
                if (reg < 0 || reg >= FLUX_REGISTERS) return -1;
                if (vm->sp >= FLUX_STACK_SIZE) return -1;
                vm->stack[vm->sp++] = vm->registers[reg];
            }
            break;
        case FLUX_STORE:
            if (inst->operand_count > 0) {
                int reg = (int)inst->operands[0];
                if (reg < 0 || reg >= FLUX_REGISTERS) return -1;
                if (vm->sp < 1) return -1;
                vm->registers[reg] = vm->stack[--vm->sp];
            }
            break;
        case FLUX_PUSH:
            for (int i = 0; i < inst->operand_count && vm->sp < FLUX_STACK_SIZE; i++)
                vm->stack[vm->sp++] = inst->operands[i];
            break;
        case FLUX_POP:
            if (vm->sp < 1) return -1;
            vm->sp--;
            break;
        case FLUX_SWAP:
            if (vm->sp < 2) return -1;
            {
                double tmp = vm->stack[vm->sp - 1];
                vm->stack[vm->sp - 1] = vm->stack[vm->sp - 2];
                vm->stack[vm->sp - 2] = tmp;
            }
            break;

        /* ── Precision / Type ────────────────────────────────── */
        case FLUX_SNAP:
            /* Snapshot top-of-stack to output stream */
            if (vm->sp < 1) return -1;
            push_output(vm, vm->stack[vm->sp - 1]);
            break;
        case FLUX_QUANTIZE:
            if (vm->sp < 1) return -1;
            {
                double step_q = inst->operand_count > 0 ? inst->operands[0] : 1.0;
                if (step_q == 0.0) step_q = 1.0;
                double v = vm->stack[vm->sp - 1];
                vm->stack[vm->sp - 1] = round(v / step_q) * step_q;
            }
            break;
        case FLUX_CAST:
            /* Truncate top-of-stack to integer */
            if (vm->sp < 1) return -1;
            vm->stack[vm->sp - 1] = (double)(int64_t)vm->stack[vm->sp - 1];
            break;
        case FLUX_PROMOTE:
            /* No-op for doubles (already max precision) */
            break;

        /* ── Logical ─────────────────────────────────────────── */
        case FLUX_AND: BINOP(vm, &&); break;  /* double logical AND */
        case FLUX_OR:  BINOP(vm, ||); break;
        case FLUX_NOT:
            if (vm->sp < 1) return -1;
            vm->stack[vm->sp - 1] = (vm->stack[vm->sp - 1] == 0.0) ? 1.0 : 0.0;
            break;
        case FLUX_XOR:
            if (vm->sp < 2) return -1;
            {
                double b = vm->stack[--vm->sp];
                double a = vm->stack[--vm->sp];
                vm->stack[vm->sp++] = ((a != 0.0) != (b != 0.0)) ? 1.0 : 0.0;
            }
            break;

        /* ── Comparison ──────────────────────────────────────── */
        case FLUX_EQ:  CMPOP(vm, ==); break;
        case FLUX_NEQ: CMPOP(vm, !=); break;
        case FLUX_LT:  CMPOP(vm, <);  break;
        case FLUX_GT:  CMPOP(vm, >);  break;
        case FLUX_LTE: CMPOP(vm, <=); break;
        case FLUX_GTE: CMPOP(vm, >=); break;

        /* ── Debug / Meta ────────────────────────────────────── */
        case FLUX_NOP:
            break;
        case FLUX_DEBUG:
            /* No-op in release; could write to stderr in debug build */
            break;
        case FLUX_TRACE:
            /* Explicit trace point — already captured below */
            break;
        case FLUX_DUMP:
            /* Dump all registers to output */
            for (int i = 0; i < FLUX_REGISTERS; i++)
                push_output(vm, vm->registers[i]);
            break;

        default:
            return -5; /* unknown opcode */
        }

        /* Record trace */
        {
            double after[FLUX_TRACE_SNAPSHOT];
            int after_len = 0;
            snapshot_stack(vm, after, &after_len);
            trace_push(vm, step, op, before, before_len, after, after_len, constraint);
        }

        step++;
        pc++;
    }

    /* Fill result */
    {
        int n = vm->output_count < FLUX_MAX_OUTPUTS ? vm->output_count : FLUX_MAX_OUTPUTS;
        for (int i = 0; i < n; i++) out->outputs[i] = vm->outputs[i];
        out->output_count = n;
    }
    out->constraints_satisfied = (vm->constraint_checks > 0)
        ? (vm->constraint_failures == 0) : -1;

    /* Copy trace into result */
    if (vm->trace_len > 0) {
        size_t sz = (size_t)vm->trace_len * sizeof(flux_trace_entry_t);
        out->trace = (flux_trace_entry_t *)malloc(sz);
        if (out->trace) {
            memcpy(out->trace, vm->trace_buf, sz);
            out->trace_count = vm->trace_len;
        }
    }

    return 0;
}

/* ── Bytecode builder helpers ─────────────────────────────────────── */

int flux_bytecode_init(flux_bytecode_t *bc, int initial_cap) {
    if (!bc) return -1;
    bc->capacity = initial_cap > 0 ? initial_cap : 32;
    bc->instruction_count = 0;
    bc->instructions = (flux_instruction_t *)calloc((size_t)bc->capacity, sizeof(flux_instruction_t));
    return bc->instructions ? 0 : -1;
}

int flux_bytecode_push(flux_bytecode_t *bc, const flux_instruction_t *inst) {
    if (!bc || !inst) return -1;
    if (bc->instruction_count >= bc->capacity) {
        int new_cap = bc->capacity * 2;
        flux_instruction_t *tmp = (flux_instruction_t *)realloc(bc->instructions,
            (size_t)new_cap * sizeof(flux_instruction_t));
        if (!tmp) return -1;
        bc->instructions = tmp;
        bc->capacity = new_cap;
    }
    bc->instructions[bc->instruction_count++] = *inst;
    return 0;
}

void flux_bytecode_reset(flux_bytecode_t *bc) {
    if (bc) bc->instruction_count = 0;
}

void flux_bytecode_free(flux_bytecode_t *bc) {
    if (!bc) return;
    free(bc->instructions);
    bc->instructions = NULL;
    bc->instruction_count = 0;
    bc->capacity = 0;
}
