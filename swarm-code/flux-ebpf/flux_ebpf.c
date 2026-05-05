/* flux_ebpf.c — eBPF Constraint Filter for Linux (BPF CO-RE)
 *
 * Attaches to tracepoints and enforces runtime constraints on syscalls.
 * Requires: libbpf, kernel >= 5.8, BTF enabled.
 *
 * Build:
 *   clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -c flux_ebpf.c -o flux_ebpf.o
 *   sudo bpftool prog load flux_ebpf.o /sys/fs/bpf/flux_prog type tracepoint
 */

#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

#define MAX_CONSTRAINTS 32

#define CONSTR_NONE  0
#define CONSTR_LT    1
#define CONSTR_LE    2
#define CONSTR_EQ    3
#define CONSTR_GT    4
#define CONSTR_GE    5
#define CONSTR_NE    6

struct constraint_policy {
    __u32 active;
    __u32 ctype;
    __s64 threshold;
    __u32 target_fd;
    __u32 pad;
};

struct violation_event {
    __u32 pid;
    __u32 constraint_id;
    __s64 observed;
    __s64 threshold;
    __u64 timestamp_ns;
};

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, MAX_CONSTRAINTS);
    __type(key, __u32);
    __type(value, struct constraint_policy);
} policy_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, MAX_CONSTRAINTS);
    __type(key, __u32);
    __type(value, __u64);
} checks_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, MAX_CONSTRAINTS);
    __type(key, __u32);
    __type(value, __u64);
} violations_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} rb SEC(".maps");

static __always_inline __u32 eval_constraint(__s64 value, const struct constraint_policy *pol) {
    switch (pol->ctype) {
    case CONSTR_LT: return value < pol->threshold ? 1 : 0;
    case CONSTR_LE: return value <= pol->threshold ? 1 : 0;
    case CONSTR_EQ: return value == pol->threshold ? 1 : 0;
    case CONSTR_GT: return value > pol->threshold ? 1 : 0;
    case CONSTR_GE: return value >= pol->threshold ? 1 : 0;
    case CONSTR_NE: return value != pol->threshold ? 1 : 0;
    default: return 1;
    }
}

SEC("tracepoint/syscalls/sys_enter_write")
int trace_enter_write(struct trace_event_raw_sys_enter *ctx) {
    __u32 pid = bpf_get_current_pid_tgid() >> 32;
    __s64 count = BPF_CORE_READ(ctx, args[2]);

    #pragma unroll
    for (__u32 i = 0; i < MAX_CONSTRAINTS; i++) {
        struct constraint_policy *pol = bpf_map_lookup_elem(&policy_map, &i);
        if (!pol || !pol->active) continue;

        if (pol->target_fd != 0) {
            __u32 fd = (__u32)BPF_CORE_READ(ctx, args[0]);
            if (fd != pol->target_fd) continue;
        }

        __u64 *checks = bpf_map_lookup_elem(&checks_map, &i);
        if (checks) __sync_fetch_and_add(checks, 1);

        __u32 ok = eval_constraint(count, pol);
        if (!ok) {
            __u64 *viol = bpf_map_lookup_elem(&violations_map, &i);
            if (viol) __sync_fetch_and_add(viol, 1);

            struct violation_event *e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
            if (e) {
                e->pid = pid;
                e->constraint_id = i;
                e->observed = count;
                e->threshold = pol->threshold;
                e->timestamp_ns = bpf_ktime_get_ns();
                bpf_ringbuf_submit(e, 0);
            }
        }
    }
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_read")
int trace_enter_read(struct trace_event_raw_sys_enter *ctx) {
    __s64 count = BPF_CORE_READ(ctx, args[2]);
    __u32 zero = 0;
    struct constraint_policy *pol = bpf_map_lookup_elem(&policy_map, &zero);
    if (pol && pol->active) {
        __u64 *checks = bpf_map_lookup_elem(&checks_map, &zero);
        if (checks) __sync_fetch_and_add(checks, 1);
        if (count > pol->threshold) {
            __u64 *viol = bpf_map_lookup_elem(&violations_map, &zero);
            if (viol) __sync_fetch_and_add(viol, 1);
        }
    }
    return 0;
}

char _license[] SEC("license") = "GPL";
