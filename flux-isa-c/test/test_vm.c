#include "flux.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static int tests_passed = 0;
static int tests_failed = 0;

#define ASSERT(cond, msg) do { \
    if (!(cond)) { \
        printf("  FAIL: %s (line %d)\n", msg, __LINE__); \
        tests_failed++; \
        return; \
    } \
} while(0)

#define TEST(name) static void name(void)
#define RUN(name) do { printf("  %-40s", #name); name(); tests_passed++; printf("PASS\n"); } while(0)

static flux_instruction_t make_inst(flux_opcode_t op, const char *label,
                                     int opc, double o0, double o1, double o2, double o3) {
    flux_instruction_t i;
    memset(&i, 0, sizeof(i));
    i.opcode = op;
    i.operand_count = opc;
    i.operands[0] = o0;
    i.operands[1] = o1;
    i.operands[2] = o2;
    i.operands[3] = o3;
    if (label) strncpy(i.label, label, FLUX_LABEL_SIZE - 1);
    return i;
}

/* ─────────────────────────────────────────────────────────────────── */

TEST(test_add_sub_mul) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=2, .operands={10.0, 20.0}});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_ADD});
    /* stack: [30] */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={5.0}});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_SUB});
    /* stack: [25] */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={4.0}});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_MUL});
    /* stack: [100] */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_SNAP});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == 0, "execute should succeed");
    ASSERT(result.output_count == 1, "should have 1 output");
    ASSERT(fabs(result.outputs[0] - 100.0) < 1e-9, "output should be 100");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_division_by_zero) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=2, .operands={10.0, 0.0}});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_DIV});

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == -2, "should return -2 for division by zero");

    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_constraint_assert_pass) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    /* Push 1.0 and assert it's truthy */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={1.0}});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_ASSERT});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == 0, "execute should succeed");
    ASSERT(result.constraints_satisfied == 1, "constraints should be satisfied");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_constraint_assert_fail) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    /* Push 0.0 and assert it's truthy → should fail */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={0.0}});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_ASSERT});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == 0, "execute should succeed (assert fail doesn't halt)");
    ASSERT(result.constraints_satisfied == 0, "constraints should NOT be satisfied");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_validate_bounds) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    /* Push 5.0 and validate it's in [0, 10] */
    flux_instruction_t v = make_inst(FLUX_VALIDATE, NULL, 2, 0.0, 10.0, 0.0, 0.0);
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={5.0}});
    flux_bytecode_push(&bc, &v);
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == 0, "execute should succeed");
    ASSERT(result.constraints_satisfied == 1, "5 in [0,10] should pass");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_snap_quantize) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    /* Push 3.7, quantize to step 0.5 → should be 3.5, snap it */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={3.7}});
    flux_instruction_t q = make_inst(FLUX_QUANTIZE, NULL, 1, 0.5, 0.0, 0.0, 0.0);
    flux_bytecode_push(&bc, &q);
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_SNAP});
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == 0, "execute should succeed");
    ASSERT(result.output_count == 1, "should have 1 output");
    ASSERT(fabs(result.outputs[0] - 3.5) < 1e-9, "quantized 3.7 with step 0.5 should be 3.5");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_branch_conditional) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    /* Push 1 (true), branch to index 5 (the PUSH 42), else push 0 and halt */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={1.0}});   /* 0 */
    flux_instruction_t br = make_inst(FLUX_BRANCH, NULL, 1, 5.0, 0.0, 0.0, 0.0);
    flux_bytecode_push(&bc, &br);                                                                           /* 1 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={0.0}});   /* 2 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_SNAP});                                      /* 3 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});                                      /* 4 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={42.0}});  /* 5 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_SNAP});                                      /* 6 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});                                      /* 7 */

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == 0, "execute should succeed");
    ASSERT(result.output_count == 1, "should have 1 output");
    ASSERT(fabs(result.outputs[0] - 42.0) < 1e-9, "branch should have gone to PUSH 42");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_call_return) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 32);
    /* Main: push 3, call func at index 3, snap, halt */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={3.0}});   /* 0 */
    flux_instruction_t call = make_inst(FLUX_CALL, NULL, 1, 3.0, 0.0, 0.0, 0.0);
    flux_bytecode_push(&bc, &call);                                                                           /* 1 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_SNAP});                                       /* 2 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});                                       /* 3 — actually unused, func starts at 3 */

    /* Func: push 2, add (3+2=5), return */
    /* But wait — we call index 3, and index 3 is HALT. Let me fix the layout. */

    /* Redo the layout */
    flux_bytecode_reset(&bc);

    /* 0: PUSH 3 */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={3.0}});
    /* 1: CALL 4 */
    flux_instruction_t call2 = make_inst(FLUX_CALL, NULL, 1, 4.0, 0.0, 0.0, 0.0);
    flux_bytecode_push(&bc, &call2);
    /* 2: SNAP */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_SNAP});
    /* 3: HALT */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_HALT});
    /* 4: PUSH 2 (func entry) */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_PUSH, .operand_count=1, .operands={2.0}});
    /* 5: ADD (3 + 2 = 5) */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_ADD});
    /* 6: RETURN */
    flux_bytecode_push(&bc, &(flux_instruction_t){.opcode=FLUX_RETURN});

    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    int rc = flux_vm_execute(&vm, &bc, &result);
    ASSERT(rc == 0, "execute should succeed");
    ASSERT(result.output_count == 1, "should have 1 output");
    ASSERT(fabs(result.outputs[0] - 5.0) < 1e-9, "call should add 2 to 3 giving 5");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc);
}

TEST(test_encode_decode_roundtrip) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    flux_instruction_t i1 = make_inst(FLUX_PUSH, "start", 2, 1.0, 2.0, 0.0, 0.0);
    flux_instruction_t i2 = make_inst(FLUX_ADD, "", 0, 0, 0, 0, 0);
    flux_instruction_t i3 = make_inst(FLUX_SNAP, "result", 0, 0, 0, 0, 0);
    flux_instruction_t i4 = make_inst(FLUX_HALT, "", 0, 0, 0, 0, 0);
    flux_bytecode_push(&bc, &i1);
    flux_bytecode_push(&bc, &i2);
    flux_bytecode_push(&bc, &i3);
    flux_bytecode_push(&bc, &i4);

    uint8_t *buf = NULL;
    size_t len = flux_bytecode_encode(&bc, &buf);
    ASSERT(buf != NULL, "encode should produce a buffer");
    ASSERT(len > 0, "encoded length should be > 0");

    flux_bytecode_t bc2;
    int rc = flux_bytecode_decode(buf, len, &bc2);
    ASSERT(rc == 0, "decode should succeed");
    ASSERT(bc2.instruction_count == 4, "should have 4 instructions");
    ASSERT(bc2.instructions[0].opcode == FLUX_PUSH, "inst 0 should be PUSH");
    ASSERT(bc2.instructions[0].operand_count == 2, "inst 0 should have 2 operands");
    ASSERT(fabs(bc2.instructions[0].operands[0] - 1.0) < 1e-9, "operand 0 should be 1.0");
    ASSERT(fabs(bc2.instructions[0].operands[1] - 2.0) < 1e-9, "operand 1 should be 2.0");
    ASSERT(strcmp(bc2.instructions[0].label, "start") == 0, "label should be 'start'");
    ASSERT(bc2.instructions[1].opcode == FLUX_ADD, "inst 1 should be ADD");
    ASSERT(bc2.instructions[2].opcode == FLUX_SNAP, "inst 2 should be SNAP");
    ASSERT(strcmp(bc2.instructions[2].label, "result") == 0, "inst 2 label should be 'result'");
    ASSERT(bc2.instructions[3].opcode == FLUX_HALT, "inst 3 should be HALT");

    /* Execute the decoded bytecode */
    flux_vm_t vm;
    flux_vm_init(&vm, 0);
    flux_result_t result;
    rc = flux_vm_execute(&vm, &bc2, &result);
    ASSERT(rc == 0, "execute decoded bytecode should succeed");
    ASSERT(result.output_count == 1, "should have 1 output");
    ASSERT(fabs(result.outputs[0] - 3.0) < 1e-9, "1+2 should be 3");

    free(result.trace);
    flux_vm_destroy(&vm);
    flux_bytecode_free(&bc2);
    flux_bytecode_free(&bc);
    free(buf);
}

TEST(test_disassemble) {
    flux_bytecode_t bc;
    flux_bytecode_init(&bc, 16);
    flux_instruction_t i1 = make_inst(FLUX_PUSH, "entry", 2, 42.0, 7.0, 0.0, 0.0);
    flux_instruction_t i2 = make_inst(FLUX_ADD, "", 0, 0, 0, 0, 0);
    flux_instruction_t i3 = make_inst(FLUX_HALT, "", 0, 0, 0, 0, 0);
    flux_bytecode_push(&bc, &i1);
    flux_bytecode_push(&bc, &i2);
    flux_bytecode_push(&bc, &i3);

    char *disasm = flux_disassemble_all(&bc);
    ASSERT(disasm != NULL, "disassemble should return non-null");
    ASSERT(strstr(disasm, "entry") != NULL, "should contain 'entry' label");
    ASSERT(strstr(disasm, "PUSH") != NULL, "should contain 'PUSH'");
    ASSERT(strstr(disasm, "ADD") != NULL, "should contain 'ADD'");
    ASSERT(strstr(disasm, "HALT") != NULL, "should contain 'HALT'");
    ASSERT(strstr(disasm, "42") != NULL, "should contain operand 42");

    printf("\n%s", disasm);
    free(disasm);
    flux_bytecode_free(&bc);
}

/* ─────────────────────────────────────────────────────────────────── */

int main(void) {
    printf("FLUX ISA VM Tests\n");
    printf("=================\n");

    RUN(test_add_sub_mul);
    RUN(test_division_by_zero);
    RUN(test_constraint_assert_pass);
    RUN(test_constraint_assert_fail);
    RUN(test_validate_bounds);
    RUN(test_snap_quantize);
    RUN(test_branch_conditional);
    RUN(test_call_return);
    RUN(test_encode_decode_roundtrip);
    RUN(test_disassemble);

    printf("\n=================\n");
    printf("Results: %d passed, %d failed\n", tests_passed, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
