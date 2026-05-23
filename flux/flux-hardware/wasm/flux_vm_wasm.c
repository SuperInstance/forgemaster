/*
 * FLUX-C Constraint Checker VM — WebAssembly implementation
 * Compile: clang --target=wasm32-unknown-none -O2 -nostdlib -Wl,--no-entry \
 *          -Wl,--export=flux_init -Wl,--export=flux_check -Wl,--export=flux_batch \
 *          -Wl,--export=__heap_base flux_vm_wasm.c -o flux_vm.wasm
 *
 * Alternatively: wasm-ld or emscripten with -s STANDALONE_WASM
 */

#define STACK_SIZE 64
#define MAX_GAS    0xFFFF

/* Opcodes */
#define OP_HALT     0x1A
#define OP_ASSERT   0x1B
#define OP_RANGE    0x1D
#define OP_BOOL_AND 0x26
#define OP_BOOL_OR  0x27
#define OP_DUP      0x28
#define OP_SWAP     0x29

typedef signed int     i32;
typedef unsigned int   u32;
typedef unsigned char  u8;
typedef unsigned short u16;

/* VM state — lives in linear memory */
static i32 stack[STACK_SIZE];
static i32 sp;           /* stack pointer (next free slot) */
static u16 gas;

/* ── helpers (static inline so no external deps) ── */

static inline void push(i32 v) {
    if (sp < STACK_SIZE) stack[sp++] = v;
}

static inline i32 pop(void) {
    return sp > 0 ? stack[--sp] : 0;
}

/* ── exported API ── */

/* flux_init — zero out VM state */
__attribute__((visibility("default")))
void flux_init(void) {
    for (int i = 0; i < STACK_SIZE; i++) stack[i] = 0;
    sp  = 0;
    gas = 0;
}

/*
 * flux_check — run bytecode on a single input value.
 *   bytecode_ptr: pointer into linear memory
 *   bc_len:       length of bytecode in bytes
 *   input:        the value to validate
 *   returns: 0 = pass, 1 = fail (assertion), 2 = gas exhausted, 3 = stack overflow
 */
__attribute__((visibility("default")))
i32 flux_check(u8 *bytecode_ptr, u32 bc_len, i32 input) {
    sp  = 0;
    gas = 0;
    push(input);                       /* seed stack with the input value */

    u32 pc = 0;
    while (pc < bc_len) {
        if (++gas >= MAX_GAS) return 2; /* gas exhausted */

        u8 op = bytecode_ptr[pc++];

        switch (op) {
        case OP_HALT:
            /* top of stack is the result: 0 = pass */
            return (pop() == 0) ? 0 : 1;

        case OP_ASSERT: {
            i32 cond = pop();
            if (!cond) return 1;        /* assertion failed */
            break;
        }

        case OP_RANGE: {
            i32 hi   = pop();
            i32 lo   = pop();
            i32 val  = pop();
            push((val >= lo && val <= hi) ? 1 : 0);
            break;
        }

        case OP_BOOL_AND: {
            i32 b = pop();
            i32 a = pop();
            push((a && b) ? 1 : 0);
            break;
        }

        case OP_BOOL_OR: {
            i32 b = pop();
            i32 a = pop();
            push((a || b) ? 1 : 0);
            break;
        }

        case OP_DUP: {
            if (sp == 0) return 3;
            i32 v = stack[sp - 1];
            if (sp >= STACK_SIZE) return 3;
            push(v);
            break;
        }

        case OP_SWAP: {
            if (sp < 2) return 3;
            i32 tmp       = stack[sp - 1];
            stack[sp - 1] = stack[sp - 2];
            stack[sp - 2] = tmp;
            break;
        }

        default:
            return 3;                   /* unknown opcode */
        }
    }

    /* fell off the end without HALT — treat as pass if stack top == 0 */
    return (sp > 0 && stack[0] != 0) ? 1 : 0;
}

/*
 * flux_batch — run the same bytecode on an array of inputs.
 *   bytecode_ptr: pointer to bytecode
 *   bc_len:       bytecode length
 *   inputs_ptr:   pointer to i32[n] input array
 *   results_ptr:  pointer to i32[n] output array (0/1/2/3 per element)
 *   n:            number of inputs
 *   max_gas:      per-element gas limit
 *   returns: 0 on success, 1 if any element failed
 */
__attribute__((visibility("default")))
i32 flux_batch(u8 *bytecode_ptr, u32 bc_len, i32 *inputs_ptr,
               i32 *results_ptr, u32 n, u16 max_gas_param) {
    u16 saved_max = MAX_GAS;            /* we'd use a variable but keep it simple */
    i32 any_fail = 0;

    for (u32 i = 0; i < n; i++) {
        sp  = 0;
        gas = 0;
        push(inputs_ptr[i]);

        u32 pc = 0;
        i32 result = 0;                 /* default: pass */

        while (pc < bc_len) {
            if (++gas >= max_gas_param) { result = 2; break; }

            u8 op = bytecode_ptr[pc++];
            switch (op) {
            case OP_HALT:
                result = (pop() == 0) ? 0 : 1;
                goto done;

            case OP_ASSERT: {
                i32 cond = pop();
                if (!cond) { result = 1; goto done; }
                break;
            }

            case OP_RANGE: {
                i32 hi  = pop();
                i32 lo  = pop();
                i32 val = pop();
                push((val >= lo && val <= hi) ? 1 : 0);
                break;
            }

            case OP_BOOL_AND: {
                i32 b = pop(); i32 a = pop();
                push((a && b) ? 1 : 0);
                break;
            }

            case OP_BOOL_OR: {
                i32 b = pop(); i32 a = pop();
                push((a || b) ? 1 : 0);
                break;
            }

            case OP_DUP: {
                if (sp == 0 || sp >= STACK_SIZE) { result = 3; goto done; }
                push(stack[sp - 1]);
                break;
            }

            case OP_SWAP: {
                if (sp < 2) { result = 3; goto done; }
                i32 tmp       = stack[sp - 1];
                stack[sp - 1] = stack[sp - 2];
                stack[sp - 2] = tmp;
                break;
            }

            default:
                result = 3;
                goto done;
            }
        }
done:
        results_ptr[i] = result;
        if (result != 0) any_fail = 1;
    }

    return any_fail;
}
