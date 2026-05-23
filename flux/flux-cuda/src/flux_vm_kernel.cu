/*
 * flux_vm_kernel.cu — CUDA kernel for parallel FLUX ISA execution
 *
 * Each thread block executes one FLUX bytecode instance.
 * Shared memory used for per-instance stack (up to 256 doubles).
 * Warp-level reduction for constraint satisfaction checks.
 * Supports up to 1024 parallel instances per kernel launch.
 */

#include "flux_cuda.h"

/* ═══════════════════════════════════════════════════════════════
 *  FLUX ISA opcodes
 * ═════════════════════════════════════════════════════════════ */
enum flux_opcode : uint8_t {
    OP_NOP       = 0x00,
    OP_PUSH      = 0x01,  /* push immediate (8-byte double follows) */
    OP_LOAD      = 0x02,  /* load input by index (1-byte index)      */
    OP_STORE     = 0x03,  /* store to output (1-byte index)          */
    OP_ADD       = 0x10,
    OP_SUB       = 0x11,
    OP_MUL       = 0x12,
    OP_DIV       = 0x13,
    OP_NEG       = 0x14,
    OP_SQRT      = 0x15,
    OP_ABS       = 0x16,
    OP_MIN       = 0x17,
    OP_MAX       = 0x18,
    OP_CMP_EQ    = 0x20,
    OP_CMP_NE    = 0x21,
    OP_CMP_LT    = 0x22,
    OP_CMP_GT    = 0x23,
    OP_CMP_LE    = 0x24,
    OP_CMP_GE    = 0x25,
    OP_ASSERT    = 0x30,  /* pop; if zero → constraint violation    */
    OP_JMP       = 0x40,  /* 2-byte offset                           */
    OP_JZ        = 0x41,  /* pop; if zero jump (2-byte offset)       */
    OP_HALT      = 0xFF,
};

/* ═══════════════════════════════════════════════════════════════
 *  FLUX VM stack machine (executed per thread block, one instance)
 * ═════════════════════════════════════════════════════════════ */

/*
 * The kernel uses block-level parallelism: blockIdx.x selects the instance.
 * Thread 0 within each block executes the VM; other threads participate in
 * warp reductions for constraint checks.
 *
 * Shared memory layout per block:
 *   double stack[256]       — 2048 bytes
 *   double outputs[...]
 *   double inputs[...]
 */

/* Max bytecodes handled per instance */
#define FLUX_MAX_BYTECODE 8192

__launch_bounds__(32, 16)
__global__ void flux_vm_batch_kernel(
    const uint8_t*  __restrict__ bytecode_table,  /* flat: instance * bytecode_len */
    size_t                      bytecode_stride,   /* bytes between instance bytecodes */
    const double*   __restrict__ inputs_table,     /* flat: instance * inputs_per */
    int                         inputs_per_instance,
    double*          __restrict__ outputs_table,    /* flat: instance * outputs_per */
    int                         outputs_per_instance,
    int32_t*         __restrict__ violation_flags,  /* per instance */
    int                         max_stack,
    size_t                      bytecode_len)
{
    /* One instance per block */
    const int inst_id = blockIdx.x;
    if (inst_id >= gridDim.x) return;

    /* Shared memory for stack + local I/O */
    extern __shared__ char smem[];
    double* stack   = reinterpret_cast<double*>(smem);
    int*    sp      = reinterpret_cast<int*>(smem + max_stack * sizeof(double));
    double* local_in  = reinterpret_cast<double*>(smem + max_stack * sizeof(double) + sizeof(int));
    double* local_out = reinterpret_cast<double*>(smem + max_stack * sizeof(double) + sizeof(int)
                                                   + inputs_per_instance * sizeof(double));

    /* Only thread 0 executes the VM */
    if (threadIdx.x == 0) {
        *sp = 0;
        int32_t violation = 0;

        const uint8_t* bc = bytecode_table + inst_id * bytecode_stride;
        const double*  inp = inputs_table + inst_id * inputs_per_instance;
        double*        out = outputs_table + inst_id * outputs_per_instance;

        /* Copy inputs to shared */
        for (int i = 0; i < inputs_per_instance; ++i)
            local_in[i] = inp[i];
        for (int i = 0; i < outputs_per_instance; ++i)
            local_out[i] = 0.0;

        /* Stack helpers */
        auto push = [&](double v) {
            if (*sp < max_stack) stack[(*sp)++] = v;
        };
        auto pop = [&]() -> double {
            return (*sp > 0) ? stack[--(*sp)] : 0.0;
        };

        size_t pc = 0;
        while (pc < bytecode_len && !violation) {
            uint8_t op = bc[pc++];
            switch (op) {
            case OP_NOP:
                break;

            case OP_PUSH: {
                double val;
                memcpy(&val, bc + pc, sizeof(double));
                pc += sizeof(double);
                push(val);
                break;
            }

            case OP_LOAD: {
                uint8_t idx = bc[pc++];
                push((idx < inputs_per_instance) ? local_in[idx] : 0.0);
                break;
            }

            case OP_STORE: {
                uint8_t idx = bc[pc++];
                if (idx < outputs_per_instance)
                    local_out[idx] = pop();
                break;
            }

            case OP_ADD: { double b = pop(), a = pop(); push(a + b); break; }
            case OP_SUB: { double b = pop(), a = pop(); push(a - b); break; }
            case OP_MUL: { double b = pop(), a = pop(); push(a * b); break; }
            case OP_DIV: { double b = pop(), a = pop(); push((b != 0.0) ? (a / b) : 0.0); break; }
            case OP_NEG: { double a = pop(); push(-a); break; }
            case OP_SQRT: { double a = pop(); push((a >= 0.0) ? sqrt(a) : 0.0); break; }
            case OP_ABS: { double a = pop(); push(fabs(a)); break; }
            case OP_MIN: { double b = pop(), a = pop(); push(fmin(a, b)); break; }
            case OP_MAX: { double b = pop(), a = pop(); push(fmax(a, b)); break; }

            case OP_CMP_EQ: { double b = pop(), a = pop(); push((a == b) ? 1.0 : 0.0); break; }
            case OP_CMP_NE: { double b = pop(), a = pop(); push((a != b) ? 1.0 : 0.0); break; }
            case OP_CMP_LT: { double b = pop(), a = pop(); push((a < b)  ? 1.0 : 0.0); break; }
            case OP_CMP_GT: { double b = pop(), a = pop(); push((a > b)  ? 1.0 : 0.0); break; }
            case OP_CMP_LE: { double b = pop(), a = pop(); push((a <= b) ? 1.0 : 0.0); break; }
            case OP_CMP_GE: { double b = pop(), a = pop(); push((a >= b) ? 1.0 : 0.0); break; }

            case OP_ASSERT: {
                double val = pop();
                if (val == 0.0) violation = 1;
                break;
            }

            case OP_JMP: {
                int16_t offset;
                memcpy(&offset, bc + pc, sizeof(int16_t));
                pc += sizeof(int16_t);
                pc += offset;
                break;
            }

            case OP_JZ: {
                int16_t offset;
                memcpy(&offset, bc + pc, sizeof(int16_t));
                pc += sizeof(int16_t);
                double cond = pop();
                if (cond == 0.0) pc += offset;
                break;
            }

            case OP_HALT:
                pc = bytecode_len; /* exit loop */
                break;

            default:
                violation = 2; /* unknown opcode */
                break;
            }
        }

        /* Write outputs back to global memory */
        for (int i = 0; i < outputs_per_instance; ++i)
            out[i] = local_out[i];

        violation_flags[inst_id] = violation;
    }

    /* Warp-level reduction: OR all violation flags in this block */
    __syncthreads();
    if (threadIdx.x < 32) {
        int32_t v = (threadIdx.x == 0) ? violation_flags[inst_id] : 0;
        for (int off = 16; off > 0; off >>= 1)
            v |= __shfl_down_sync(0xFFFFFFFF, v, off);
        if (threadIdx.x == 0)
            violation_flags[inst_id] = v;
    }
}
