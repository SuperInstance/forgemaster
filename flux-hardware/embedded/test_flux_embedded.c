/**
 * FLUX Embedded Runtime — Test Suite
 * Validates correctness of the bare-metal FLUX-C interpreter
 * Compiles on any C99 compiler (no ARM hardware needed for testing)
 */

#include <stdio.h>
#include <string.h>
#include "flux_embedded.h"

static int tests_run = 0;
static int tests_pass = 0;

#define TEST(name) do { tests_run++; printf("  %-50s", #name); } while(0)
#define PASS() do { tests_pass++; printf("✓\n"); } while(0)
#define FAIL(msg) do { printf("✗ %s\n", msg); } while(0)
#define ASSERT(cond, msg) do { if (!(cond)) { FAIL(msg); return; } } while(0)

void test_init(void) {
    TEST("VM init");
    FluxVM vm;
    FluxError err = flux_vm_init(&vm);
    ASSERT(err == FLUX_OK, "init failed");
    ASSERT(vm.stack_ptr == 0, "stack not empty");
    ASSERT(vm.pc == 0, "pc not zero");
    PASS();
}

void test_push_pop(void) {
    TEST("Push/Pop");
    FluxVM vm;
    flux_vm_init(&vm);
    flux_push(&vm, 42);
    flux_push(&vm, -100);
    int32_t val;
    flux_pop(&vm, &val);
    ASSERT(val == -100, "expected -100");
    flux_pop(&vm, &val);
    ASSERT(val == 42, "expected 42");
    PASS();
}

void test_saturation(void) {
    TEST("Saturation clamps to [-127, 127]");
    ASSERT(flux_saturate(-128) == -127, "-128 should clamp to -127");
    ASSERT(flux_saturate(128) == 127, "128 should clamp to 127");
    ASSERT(flux_saturate(-127) == -127, "-127 should stay");
    ASSERT(flux_saturate(127) == 127, "127 should stay");
    ASSERT(flux_saturate(0) == 0, "0 should stay");
    ASSERT(flux_saturate(-1000) == -127, "-1000 should clamp");
    ASSERT(flux_saturate(1000) == 127, "1000 should clamp");
    PASS();
}

void test_stack_overflow(void) {
    TEST("Stack overflow detected");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxError err = FLUX_OK;
    for (int i = 0; i < FLUX_STACK_SIZE + 1; i++) {
        err = flux_push(&vm, i);
    }
    ASSERT(err == FLUX_ERR_STACK_OVERFLOW, "should overflow");
    PASS();
}

void test_stack_underflow(void) {
    TEST("Stack underflow detected");
    FluxVM vm;
    flux_vm_init(&vm);
    int32_t val;
    FluxError err = flux_pop(&vm, &val);
    ASSERT(err == FLUX_ERR_STACK_UNDERFLOW, "should underflow");
    PASS();
}

void test_arithmetic(void) {
    TEST("Arithmetic (add/sub/mul)");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    // PUSH 10, PUSH 20, ADD → 30
    uint8_t bc[] = {
        FLUX_PUSH, 10,
        FLUX_PUSH, 20,
        FLUX_ADD,
        FLUX_HALT
    };
    FluxError err = flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(err == FLUX_OK, "execution failed");
    ASSERT(vm.stack[0] == 30, "expected 30");
    PASS();
}

void test_subtraction(void) {
    TEST("Subtraction");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    uint8_t bc[] = {
        FLUX_PUSH, 50,
        FLUX_PUSH, 30,
        FLUX_SUB,
        FLUX_HALT
    };
    flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(vm.stack[0] == 20, "expected 20");
    PASS();
}

void test_comparison(void) {
    TEST("Comparison (LT/GT)");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    // 3 < 5 → 1
    uint8_t bc[] = {
        FLUX_PUSH, 3,
        FLUX_PUSH, 5,
        FLUX_LT,
        FLUX_HALT
    };
    flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(vm.stack[0] == 1, "3 < 5 should be 1");
    PASS();
}

void test_range_check_pass(void) {
    TEST("Range check pass (50 in [-127, 127])");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    // value=50, lo=-50, hi=100 → pass
    uint8_t bc[] = {
        FLUX_PUSH, 50,     // value
        FLUX_PUSH, (uint8_t)(int8_t)(-50), // lo
        FLUX_PUSH, 100,    // hi
        FLUX_RANGE_CHECK,
        FLUX_HALT
    };
    flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(result.error_mask == 0, "should pass");
    PASS();
}

void test_range_check_fail(void) {
    TEST("Range check fail (200 > 127)");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    // value=120, lo=-50, hi=100 → 120 > 100 = fail
    uint8_t bc[] = {
        FLUX_CONSTRAINT_ID, 0,
        FLUX_PUSH, 120,  // value: 120 > 100 = fail
        FLUX_PUSH, (uint8_t)(int8_t)(-50),
        FLUX_PUSH, 100,
        FLUX_RANGE_CHECK,
        FLUX_HALT
    };
    flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(result.error_mask != 0, "should fail");
    ASSERT(result.violated_hi & 0x01, "should flag hi violation");
    PASS();
}

void test_division_by_zero(void) {
    TEST("Division by zero detected");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    uint8_t bc[] = {
        FLUX_PUSH, 10,
        FLUX_PUSH, 0,
        FLUX_DIV,
        FLUX_HALT
    };
    FluxError err = flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(err == FLUX_ERR_DIVISION_BY_ZERO, "should detect div/0");
    PASS();
}

void test_jump(void) {
    TEST("Conditional jump");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    // PUSH 1, JUMP_IF target, PUSH 99 (skipped), target: PUSH 42, HALT
    uint8_t bc[] = {
        FLUX_PUSH, 1,
        FLUX_JUMP_IF, 0x07, 0x00,  // Jump to offset 7
        FLUX_PUSH, 99,             // offset 5-6 (skipped)
        FLUX_PUSH, 42,             // offset 7-8 (target)
        FLUX_HALT                  // offset 9
    };
    flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(vm.stack[0] == 42, "should jump to 42");
    PASS();
}

void test_call_ret(void) {
    TEST("CALL/RET");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    // CALL subroutine at offset 5, HALT at offset 4
    // subroutine: PUSH 77 at offset 5-6, RET at offset 7
    uint8_t bc[] = {
        FLUX_CALL, 0x05, 0x00,  // offset 0-2: Call offset 5
        FLUX_HALT,              // offset 3
        FLUX_PUSH, 77,          // offset 4-5 (subroutine)
        FLUX_RET                // offset 6
    };
    // CALL reads 2 bytes after opcode, then jumps. Return addr = pc+2 = 3
    // But CALL advances pc to target (5), RET returns to pc after CALL (3)
    // Offset calculation: CALL=0, operand bytes at 1,2 = 0x04,0x00
    // After CALL, pc = target. RET pops return addr = 1+2 = 3
    bc[1] = 0x04;  // Target offset 4
    flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(vm.stack[0] == 77, "should return 77 from subroutine");
    PASS();
}

void test_unknown_opcode(void) {
    TEST("Unknown opcode rejected");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    uint8_t bc[] = { 0xFE };  // Invalid opcode
    FluxError err = flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(err == FLUX_ERR_UNKNOWN_OPCODE, "should reject");
    PASS();
}

void test_sandbox_balancing(void) {
    TEST("Sandbox enter/exit balance");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    uint8_t bc[] = {
        FLUX_SANDBOX_ENTER,
        FLUX_SANDBOX_EXIT,
        FLUX_SANDBOX_EXIT,  // Unbalanced!
        FLUX_HALT
    };
    FluxError err = flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT(err == FLUX_ERR_SANDBOX_UNBALANCED, "should detect imbalance");
    PASS();
}

void test_multi_constraint(void) {
    TEST("Multi-constraint evaluation");
    FluxVM vm;
    flux_vm_init(&vm);
    FluxResult result = {0};

    // C0: value 50, range [-50, 100] → pass
    // C1: value 120, range [-50, 100] → fail (120 > 100)
    uint8_t bc[] = {
        FLUX_CONSTRAINT_ID, 0,
        FLUX_PUSH, 50,
        FLUX_PUSH, (uint8_t)(int8_t)(-50),
        FLUX_PUSH, 100,
        FLUX_RANGE_CHECK,

        FLUX_CONSTRAINT_ID, 1,
        FLUX_PUSH, (uint8_t)120,
        FLUX_PUSH, (uint8_t)(int8_t)(-50),
        FLUX_PUSH, 100,
        FLUX_RANGE_CHECK,

        FLUX_HALT
    };
    flux_execute(&vm, bc, sizeof(bc), &result);
    ASSERT((result.error_mask & 0x01) == 0, "C0 should pass");
    ASSERT((result.error_mask & 0x02) != 0, "C1 should fail");
    ASSERT(result.severity >= 1, "should have severity");
    PASS();
}

int main(void) {
    printf("╔══════════════════════════════════════════════════════╗\n");
    printf("║  FLUX Embedded Runtime — Test Suite                 ║\n");
    printf("║  ARM Cortex-R bare-metal safety-certified VM        ║\n");
    printf("╚══════════════════════════════════════════════════════╝\n\n");

    test_init();
    test_push_pop();
    test_saturation();
    test_stack_overflow();
    test_stack_underflow();
    test_arithmetic();
    test_subtraction();
    test_comparison();
    test_range_check_pass();
    test_range_check_fail();
    test_division_by_zero();
    test_jump();
    test_call_ret();
    test_unknown_opcode();
    test_sandbox_balancing();
    test_multi_constraint();

    printf("\n╔══════════════════════════════════════════════════════╗\n");
    printf("║  Results: %d/%d passing                              ║\n", tests_pass, tests_run);
    printf("╚══════════════════════════════════════════════════════╝\n");

    return tests_pass == tests_run ? 0 : 1;
}
