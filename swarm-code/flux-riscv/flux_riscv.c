/* flux_riscv.c — RISC-V XFLUX Coprocessor ISA
 *
 * Custom instruction extension for FLUX constraint evaluation.
 * Software-emulated fallback; hardware path gated by -DHW_FLUX.
 *
 * Build:
 *   gcc -O2 flux_riscv.c -o flux_riscv        (native test)
 *   riscv64-linux-gnu-gcc -O2 -march=rv64gc flux_riscv.c -o flux_riscv_rv64
 *
 * Run: ./flux_riscv
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Custom opcode: CUSTOM-0 (0x0B) */
#define FLUX_OP 0x0B

#ifdef HW_FLUX
/* Real custom instruction encoding (requires hardware support) */
#define flux_check_lt(a, b) ({ \
    register uint64_t _r __asm__("a0") = (a); \
    register uint64_t _s __asm__("a1") = (b); \
    register uint64_t _d __asm__("a2"); \
    __asm__ volatile (".insn r 0x0B, 0x0, 0x00, %0, %1, %2" : "=r"(_d) : "r"(_r), "r"(_s)); \
    _d; })
#else
static inline uint64_t flux_check_lt(uint64_t a, uint64_t b) { return (a < b) ? 1ULL : 0ULL; }
static inline uint64_t flux_check_le(uint64_t a, uint64_t b) { return (a <= b) ? 1ULL : 0ULL; }
static inline uint64_t flux_check_eq(uint64_t a, uint64_t b) { return (a == b) ? 1ULL : 0ULL; }
static inline uint64_t flux_check_ne(uint64_t a, uint64_t b) { return (a != b) ? 1ULL : 0ULL; }
static inline uint64_t flux_check_gt(uint64_t a, uint64_t b) { return (a > b) ? 1ULL : 0ULL; }
static inline uint64_t flux_check_ge(uint64_t a, uint64_t b) { return (a >= b) ? 1ULL : 0ULL; }
static inline uint64_t flux_bool_and(uint64_t a, uint64_t b) { return a & b; }
static inline uint64_t flux_bool_or(uint64_t a, uint64_t b) { return a | b; }
static inline uint64_t flux_bool_not(uint64_t a) { return a ? 0ULL : 1ULL; }
#endif

typedef struct {
    uint64_t regs[16];
    uint64_t checks;
    uint64_t violations;
    uint64_t halted;
    uint64_t pc;
} FluxCoprocState;

static inline void flux_coproc_init(FluxCoprocState *s) { memset(s, 0, sizeof(*s)); }

static inline uint64_t flux_eval_temp_limit(FluxCoprocState *s, uint64_t temp) {
    s->checks++;
    uint64_t ok = flux_check_lt(temp, 120ULL);
    if (!ok) s->violations++;
    return ok;
}

static inline uint64_t flux_eval_rpm_window(FluxCoprocState *s, uint64_t rpm) {
    s->checks++;
    uint64_t a = flux_check_gt(rpm, 0ULL);
    uint64_t b = flux_check_lt(rpm, 8000ULL);
    uint64_t ok = flux_bool_and(a, b);
    if (!ok) s->violations++;
    return ok;
}

static inline uint64_t flux_pack8(const uint64_t *values) {
    uint64_t packed = 0;
    for (int i = 0; i < 8; i++) { if (values[i]) packed |= (1ULL << i); }
    return packed;
}

void flux_batch_eval(FluxCoprocState *s, const uint64_t *inputs,
                     const uint8_t *bytecode, size_t n_inputs, size_t bytecode_len) {
    (void)bytecode; (void)bytecode_len;
    if (n_inputs > 0) flux_eval_temp_limit(s, inputs[0]);
    if (n_inputs > 1) flux_eval_rpm_window(s, inputs[1]);
}

/* --- Tests --- */
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) static void test_##name(void)
#define ASSERT(cond) do { if (!(cond)) { fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); tests_failed++; return; } } while(0)
#define ASSERT_EQ(a, b) ASSERT((a) == (b))

TEST(lt_basic) {
    ASSERT_EQ(flux_check_lt(50ULL, 120ULL), 1ULL);
    ASSERT_EQ(flux_check_lt(150ULL, 120ULL), 0ULL);
    tests_passed++;
}

TEST(le_boundary) {
    ASSERT_EQ(flux_check_le(120ULL, 120ULL), 1ULL);
    ASSERT_EQ(flux_check_le(121ULL, 120ULL), 0ULL);
    tests_passed++;
}

TEST(eq_and_ne) {
    ASSERT_EQ(flux_check_eq(42ULL, 42ULL), 1ULL);
    ASSERT_EQ(flux_check_ne(42ULL, 43ULL), 1ULL);
    ASSERT_EQ(flux_check_eq(42ULL, 43ULL), 0ULL);
    tests_passed++;
}

TEST(bool_logic) {
    ASSERT_EQ(flux_bool_and(1, 1), 1);
    ASSERT_EQ(flux_bool_and(1, 0), 0);
    ASSERT_EQ(flux_bool_or(0, 1), 1);
    ASSERT_EQ(flux_bool_or(0, 0), 0);
    ASSERT_EQ(flux_bool_not(1), 0);
    ASSERT_EQ(flux_bool_not(0), 1);
    tests_passed++;
}

TEST(pack8_roundtrip) {
    uint64_t vals[8] = {1, 0, 1, 1, 0, 0, 1, 0};
    uint64_t p = flux_pack8(vals);
    ASSERT_EQ(p, 0b01001101ULL);
    tests_passed++;
}

TEST(coproc_state_accumulate) {
    FluxCoprocState s;
    flux_coproc_init(&s);
    flux_eval_temp_limit(&s, 50);
    flux_eval_temp_limit(&s, 150);
    flux_eval_rpm_window(&s, 5000);
    flux_eval_rpm_window(&s, 9000);
    ASSERT_EQ(s.checks, 4);
    ASSERT_EQ(s.violations, 2);
    tests_passed++;
}

int main(void) {
    tests_passed = 0; tests_failed = 0;
    test_lt_basic();
    test_le_boundary();
    test_eq_and_ne();
    test_bool_logic();
    test_pack8_roundtrip();
    test_coproc_state_accumulate();
    printf("RISC-V FLUX: %d passed, %d failed\n", tests_passed, tests_failed);
    return tests_failed;
}
