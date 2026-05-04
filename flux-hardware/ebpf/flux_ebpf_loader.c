### Complete FLUX eBPF Firewall Implementation
This production-grade solution includes **kernel eBPF code**, **userspace management tool**, **configuration**, **Makefile**, and **documentation**. It follows Linux kernel eBPF best practices (libbpf, CO-RE, per-CPU stats) and includes robust error handling.

---

## 1. Shared Header (`flux_ebpf_shared.h`)
*Used by both kernel and userspace to ensure ABI compatibility*
```c
#ifndef FLUX_EBPF_SHARED_H
#define FLUX_EBPF_SHARED_H

#include <linux/types.h>

/* --------------------------
 * Configuration Constants
 * -------------------------- */
#define FLUX_MAX_CONSTRAINTS 16  /* Max number of active rules */
#define FLUX_PIN_DIR "/sys/fs/bpf/flux"  /* Persistent map storage */

/* --------------------------
 * Constraint Types
 * -------------------------- */
enum flux_constraint_type {
    FLUX_CONSTRAINT_RANGE = 1,  /* Check if field is [lo, hi] */
    FLUX_CONSTRAINT_MASK = 2,   /* Check if (field & mask) == mask */
};

/* --------------------------
 * Packet Fields to Filter
 * -------------------------- */
enum flux_field {
    FLUX_FIELD_SRC_IP_OCT0 = 1,  /* First octet of IPv4 source (e.g., 192 in 192.168.1.1) */
    FLUX_FIELD_DST_PORT = 2,     /* TCP/UDP destination port */
    FLUX_FIELD_SRC_PORT_LOW = 3, /* Lower 8 bits of TCP/UDP source port */
};

/* --------------------------
 * Constraint Map Entry
 * -------------------------- */
struct flux_constraint {
    __u8 active;       /* 1 = rule enabled, 0 = disabled */
    __u8 type;         /* enum flux_constraint_type */
    __u8 field;        /* enum flux_field */
    __u32 lo;          /* Range: lower bound */
    __u32 hi;          /* Range: upper bound */
    __u32 mask;        /* Mask: bitmask to check */
};

/* --------------------------
 * Statistics (Per-CPU to Avoid Cache Bouncing)
 * -------------------------- */
struct flux_stats {
    __u64 total;       /* Total packets processed */
    __u64 passed;      /* Packets allowed by rules */
    __u64 violations;  /* Packets blocked by rules */
};

#endif /* FLUX_EBPF_SHARED_H */
```

---

## 2. Kernel eBPF Program (`flux_ebpf_kern.c`)
*XDP program that runs in the kernel, parses packets, and enforces constraints*
```c
#include "flux_ebpf_shared.h"
#include <vmlinux.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

/* --------------------------
 * BPF Maps (Kernel-Side)
 * -------------------------- */
/* Constraint Map: Key = Rule ID (0-FLUX_MAX_CONSTRAINTS-1), Value = Rule */
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, FLUX_MAX_CONSTRAINTS);
    __type(key, __u32);
    __type(value, struct flux_constraint);
} constraint_map SEC(".maps");

/* Stats Map: Per-CPU to eliminate cache contention */
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct flux_stats);
} stats_map SEC(".maps");

/* --------------------------
 * Helper: Extract Packet Field Value
 * -------------------------- */
static __always_inline __u32 get_field(enum flux_field field,
                                        struct iphdr *ip,
                                        __be16 src_port,
                                        __be16 dst_port) {
    switch (field) {
        case FLUX_FIELD_SRC_IP_OCT0:
            return (bpf_ntohl(ip->saddr) >> 24) & 0xFF;
        case FLUX_FIELD_DST_PORT:
            return bpf_ntohs(dst_port);
        case FLUX_FIELD_SRC_PORT_LOW:
            return bpf_ntohs(src_port) & 0xFF;
        default:
            return 0;
    }
}

/* --------------------------
 * XDP Filter Main Logic
 * -------------------------- */
SEC("xdp")
int flux_xdp_filter(struct xdp_md *xdp) {
    void *data_end = (void *)(long)xdp->data_end;
    void *data = (void *)(long)xdp->data;

    /* --------------------------
     * Parse Ethernet Header
     * -------------------------- */
    struct ethhdr *eth = data;
    if (data + sizeof(*eth) > data_end)
        return XDP_PASS;  /* Skip malformed packets */

    /* Only process IPv4 (skip ARP, IPv6, etc.) */
    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    /* --------------------------
     * Parse IPv4 Header
     * -------------------------- */
    struct iphdr *ip = data + sizeof(*eth);
    if (data + sizeof(*eth) + sizeof(*ip) > data_end)
        return XDP_PASS;
    if (ip->version != 4)
        return XDP_PASS;

    /* Calculate IP header length (ihl = 32-bit words) */
    __u32 ip_hdr_len = ip->ihl * 4;
    if (data + sizeof(*eth) + ip_hdr_len > data_end)
        return XDP_PASS;

    /* --------------------------
     * Parse TCP/UDP Header
     * -------------------------- */
    __be16 src_port = 0, dst_port = 0;
    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = data + sizeof(*eth) + ip_hdr_len;
        if (data + sizeof(*eth) + ip_hdr_len + sizeof(*tcp) > data_end)
            return XDP_PASS;
        src_port = tcp->source;
        dst_port = tcp->dest;
    } else if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = data + sizeof(*eth) + ip_hdr_len;
        if (data + sizeof(*eth) + ip_hdr_len + sizeof(*udp) > data_end)
            return XDP_PASS;
        src_port = udp->source;
        dst_port = udp->dest;
    } else {
        return XDP_PASS;  /* Skip non-TCP/UDP */
    }

    /* --------------------------
     * Update Stats (Per-CPU = No Atomics Needed)
     * -------------------------- */
    __u32 stats_key = 0;
    struct flux_stats *stats = bpf_map_lookup_elem(&stats_map, &stats_key);
    if (stats)
        __sync_fetch_and_add(&stats->total, 1);  /* Safe per-CPU increment */

    /* --------------------------
     * Enforce Constraints
     * -------------------------- */
    for (__u32 rule_id = 0; rule_id < FLUX_MAX_CONSTRAINTS; rule_id++) {
        struct flux_constraint *rule = bpf_map_lookup_elem(&constraint_map, &rule_id);
        if (!rule || !rule->active)
            continue;  /* Skip disabled/non-existent rules */

        /* Extract field from packet */
        __u32 field_val = get_field(rule->field, ip, src_port, dst_port);

        /* Check rule type */
        __u8 violation = 0;
        switch (rule->type) {
            case FLUX_CONSTRAINT_RANGE:
                if (field_val < rule->lo || field_val > rule->hi)
                    violation = 1;
                break;
            case FLUX_CONSTRAINT_MASK:
                if ((field_val & rule->mask) != rule->mask)
                    violation = 1;
                break;
            default:
                break;
        }

        /* Block packet if violated */
        if (violation) {
            if (stats)
                __sync_fetch_and_add(&stats->violations, 1);
            return XDP_DROP;
        }
    }

    /* --------------------------
     * Allow Packet If No Violations
     * -------------------------- */
    if (stats)
        __sync_fetch_and_add(&stats->passed, 1);
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
```

---

## 3. Userspace Management Tool (`flux_ebpf_loader.c`)
*Libbpf-based tool to load/manage eBPF program, constraints, and stats*
```c
#define _GNU_SOURCE
#include "flux_ebpf_shared.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <libgen.h>
#include <sys/stat.h>
#include <sys/sysinfo.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include <net/if.h>
#include <json-c/json.h>
#include <linux/if_link.h>

/* --------------------------
 * Global State (Simplified for Production)
 * -------------------------- */
static struct bpf_object *g_bpf_obj = NULL;
static int g_constraint_fd = -1;
static int g_stats_fd = -1;

/* --------------------------
 * Helper: Ensure BPF Pin Directory Exists
 * -------------------------- */
static int ensure_pin_dir(void) {
    struct stat st;
    if (stat(FLUX_PIN_DIR, &st) == 0)
        return 0;

    if (mkdir(FLUX_PIN_DIR, 0755) != 0 && errno != EEXIST) {
        fprintf(stderr, "ERROR: Failed to create pin dir %s: %s\n",
                FLUX_PIN_DIR, strerror(errno));
        return -1;
    }
    return 0;
}

/* --------------------------
 * Helper: Translate String to Enum
 * -------------------------- */
static enum flux_constraint_type str_to_constraint_type(const char *str) {
    if (strcmp(str, "range") == 0) return FLUX_CONSTRAINT_RANGE;
    if (strcmp(str, "domain") == 0) return FLUX_CONSTRAINT_MASK;  /* User "domain" = mask */
    return 0;
}

static enum flux_field str_to_field(const char *str) {
    if (strcmp(str, "src_ip_oct0") == 0) return FLUX_FIELD_SRC_IP_OCT0;
    if (strcmp(str, "dst_port") == 0) return FLUX_FIELD_DST_PORT;
    if (strcmp(str, "src_port_low") == 0) return FLUX_FIELD_SRC_PORT_LOW;
    return 0;
}

/* --------------------------
 * Load eBPF Program from Object File
 * -------------------------- */
static int load_ebpf(const char *obj_path) {
    if (ensure_pin_dir() != 0)
        return -1;

    /* Open BPF object */
    g_bpf_obj = bpf_object__open(obj_path);
    if (libbpf_get_error(g_bpf_obj)) {
        fprintf(stderr, "ERROR: Failed to open BPF object %s: %s\n",
                obj_path, strerror(errno));
        return -1;
    }

    /* Load BPF program into kernel */
    int ret = bpf_object__load(g_bpf_obj);
    if (ret) {
        fprintf(stderr, "ERROR: Failed to load BPF object: %s\n",
                libbpf_strerror(errno));
        bpf_object__close(g_bpf_obj);
        return -1;
    }

    /* Get map FDs and pin them for persistence */
    struct bpf_map *constraint_map = bpf_object__find_map_by_name(g_bpf_obj, "constraint_map");
    struct bpf_map *stats_map = bpf_object__find_map_by_name(g_bpf_obj, "stats_map");
    if (!constraint_map || !stats_map) {
        fprintf(stderr, "ERROR: Failed to find BPF maps\n");
        bpf_object__close(g_bpf_obj);
        return -1;
    }

    /* Pin maps (reuse if already pinned) */
    char pin_path[256];
    snprintf(pin_path, sizeof(pin_path), "%s/constraint_map", FLUX_PIN_DIR);
    ret = bpf_map__pin(constraint_map, pin_path);
    if (ret && ret != -EEXIST) {
        fprintf(stderr, "ERROR: Failed to pin constraint map: %s\n", libbpf_strerror(ret));
        bpf_object__close(g_bpf_obj);
        return -1;
    }

    snprintf(pin_path, sizeof(pin_path), "%s/stats_map", FLUX_PIN_DIR);
    ret = bpf_map__pin(stats_map, pin_path);
    if (ret && ret != -EEXIST) {
        fprintf(stderr, "ERROR: Failed to pin stats map: %s\n", libbpf_strerror(ret));
        bpf_object__close(g_bpf_obj);
        return -1;
    }

    /* Get map FDs */
    g_constraint_fd = bpf_map__fd(constraint_map);
    g_stats_fd = bpf_map__fd(stats_map);

    printf("SUCCESS: Loaded BPF program from %s\n", obj_path);
    return 0;
}

/* --------------------------
 * Set/Update Constraint Rule
 * -------------------------- */
static int set_constraint(__u32 id, const char *type_str, const char *field_str,
                           __u32 lo, __u32 hi, __u32 mask) {
    if (g_constraint_fd < 0) {
        fprintf(stderr, "ERROR: Constraint map not loaded (run 'load' first)\n");
        return -1;
    }

    if (id >= FLUX_MAX_CONSTRAINTS) {
        fprintf(stderr, "ERROR: Rule ID %u exceeds max %d\n", id, FLUX_MAX_CONSTRAINTS-1);
        return -1;
    }

    /* Translate strings to enums */
    enum flux_constraint_type type = str_to_constraint_type(type_str);
    enum flux_field field = str_to_field(field_str);
    if (type == 0 || field == 0) {
        fprintf(stderr, "ERROR: Invalid type (%s) or field (%s)\n", type_str, field_str);
        return -1;
    }

    /* Build constraint entry */
    struct flux_constraint rule = {
        .active = 1,
        .type = type,
        .field = field,
        .lo = lo,
        .hi = hi,
        .mask = mask
    };

    /* Update map */
    int ret = bpf_map_update_elem(g_constraint_fd, &id, &rule, BPF_ANY);
    if (ret) {
        fprintf(stderr, "ERROR: Failed to update constraint map: %s\n", strerror(errno));
        return -1;
    }

    printf("SUCCESS: Set rule ID %u: type=%s, field=%s, lo=%u, hi=%u, mask=0x%x\n",
           id, type_str, field_str, lo, hi, mask);
    return 0;
}

/* --------------------------
 * Read Statistics (Sum Per-CPU Entries)
 * -------------------------- */
static int get_stats(void) {
    if (g_stats_fd < 0) {
        fprintf(stderr, "ERROR: Stats map not loaded (run 'load' first)\n");
        return -1;
    }

    /* Get number of CPUs */
    int num_cpus = get_nprocs_conf();
    if (num_cpus < 1) {
        fprintf(stderr, "ERROR: Failed to get CPU count: %s\n", strerror(errno));
        return -1;
    }

    /* Allocate per-CPU stats buffer */
    struct flux_stats *stats_per_cpu = calloc(num_cpus, sizeof(*stats_per_cpu));
    if (!stats_per_cpu) {
        fprintf(stderr, "ERROR: Failed to allocate stats buffer: %s\n", strerror(errno));
        return -1;
    }

    /* Read per-CPU stats */
    __u32 key = 0;
    int ret = bpf_map_lookup_elem(g_stats_fd, &key, stats_per_cpu);
    if (ret) {
        fprintf(stderr, "ERROR: Failed to read stats map: %s\n", strerror(errno));
        free(stats_per_cpu);
        return -1;
    }

    /* Sum across CPUs */
    struct flux_stats total = {0};
    for (int i = 0; i < num_cpus; i++) {
        total.total += stats_per_cpu[i].total;
        total.passed += stats_per_cpu[i].passed;
        total.violations += stats_per_cpu[i].violations;
    }

    /* Print stats */
    printf("=== FLUX Firewall Statistics ===\n");
    printf("Total Packets:  %llu\n", total.total);
    printf("Allowed (Pass): %llu\n", total.passed);
    printf("Blocked (Viol): %llu\n", total.violations);
    printf("Pass Rate:      %.2f%%\n",
           total.total > 0 ? (100.0 * total.passed) / total.total : 0.0);

    free(stats_per_cpu);
    return 0;
}

/* --------------------------
 * List Active Constraints
 * -------------------------- */
static int list_constraints(void) {
    if (g_constraint_fd < 0) {
        fprintf(stderr, "ERROR: Constraint map not loaded (run 'load' first)\n");
        return -1;
    }

    printf("=== Active FLUX Constraints (Max: %d) ===\n", FLUX_MAX_CONSTRAINTS);
    for (__u32 id = 0; id < FLUX_MAX_CONSTRAINTS; id++) {
        struct flux_constraint rule;
        int ret = bpf_map_lookup_elem(g_constraint_fd, &id, &rule);
        if (ret || !rule.active)
            continue;

        const char *type_str = (rule.type == FLUX_CONSTRAINT_RANGE) ? "range" : "domain";
        const char *field_str = NULL;
        switch (rule.field) {
            case FLUX_FIELD_SRC_IP_OCT0: field_str = "src_ip_oct0"; break;
            case FLUX_FIELD_DST_PORT: field_str = "dst_port"; break;
            case FLUX_FIELD_SRC_PORT_LOW: field_str = "src_port_low"; break;
            default: field_str = "unknown";
        }

        printf("Rule ID %u: type=%s, field=%s, lo=%u, hi=%u, mask=0x%x\n",
               id, type_str, field_str, rule.lo, rule.hi, rule.mask);
    }
    return 0;
}

/* --------------------------
 * Attach XDP Program to Interface
 * -------------------------- */
static int attach_xdp(const char *ifname) {
    if (!g_bpf_obj) {
        fprintf(stderr, "ERROR: BPF program not loaded (run 'load' first)\n");
        return -1;
    }

    /* Get interface index */
    int ifindex = if_nametoindex(ifname);
    if (ifindex == 0) {
        fprintf(stderr, "ERROR: Invalid interface %s: %s\n", ifname, strerror(errno));
        return -1;
    }

    /* Get XDP program FD */
    struct bpf_program *prog = bpf_object__find_program_by_name(g_bpf_obj, "flux_xdp_filter");
    if (!prog) {
        fprintf(stderr, "ERROR: Failed to find XDP program\n");
        return -1;
    }
    int prog_fd = bpf_program__fd(prog);

    /* Try native XDP (DRV_MODE) first, fall back to generic (SKB_MODE) */
    int flags = XDP_FLAGS_DRV_MODE | XDP_FLAGS_UPDATE_IF_NOEXIST;
    int ret = bpf_xdp_attach(ifindex, prog_fd, flags, NULL);
    if (ret) {
        printf("WARN: Native XDP not supported for %s, falling back to generic\n", ifname);
        flags = XDP_FLAGS_SKB_MODE | XDP_FLAGS_UPDATE_IF_NOEXIST;
        ret = bpf_xdp_attach(ifindex, prog_fd, flags, NULL);
        if (ret) {
            fprintf(stderr, "ERROR: Failed to attach XDP to %s: %s\n",
                    ifname, libbpf_strerror(ret));
            return -1;
        }
    }

    printf("SUCCESS: Attached XDP to %s (mode: %s)\n",
           ifname, (flags & XDP_FLAGS_DRV_MODE) ? "native" : "generic");
    return 0;
}

/* --------------------------
 * Detach XDP Program from Interface
 * -------------------------- */
static int detach_xdp(const char *ifname) {
    int ifindex = if_nametoindex(ifname);
    if (ifindex == 0) {
        fprintf(stderr, "ERROR: Invalid interface %s: %s\n", ifname, strerror(errno));
        return -1;
    }

    /* Detach from both native and generic modes */
    int ret = bpf_xdp_detach(ifindex, XDP_FLAGS_DRV_MODE, NULL);
    ret |= bpf_xdp_detach(ifindex, XDP_FLAGS_SKB_MODE, NULL);
    if (ret) {
        fprintf(stderr, "ERROR: Failed to detach XDP from %s: %s\n",
                ifname, libbpf_strerror(ret));
        return -1;
    }

    printf("SUCCESS: Detached XDP from %s\n", ifname);
    return 0;
}

/* --------------------------
 * Parse JSON Config File
 * -------------------------- */
static int parse_config(const char *config_path) {
    struct json_object *root = json_object_from_file(config_path);
    if (!root) {
        fprintf(stderr, "ERROR: Failed to parse config %s: %s\n",
                config_path, json_util_get_last_err());
        return -1;
    }

    /* Get constraints array */
    struct json_object *constraints;
    if (!json_object_object_get_ex(root, "constraints", &constraints)) {
        fprintf(stderr, "ERROR: Config missing 'constraints' array\n");
        json_object_put(root);
        return -1;
    }

    /* Iterate over constraints */
    int num_constraints = json_object_array_length(constraints);
    for (int i = 0; i < num_constraints; i++) {
        struct json_object *rule = json_object_array_get_idx(constraints, i);
        __u32 id, lo, hi, mask;
        const char *type_str, *field_str;

        /* Extract fields (with validation) */
        if (!json_object_object_get_ex(rule, "id", &rule) ||
            !(id = json_object_get_int(rule)) ||
            !json_object_object_get_ex(rule, "type", &rule) ||
            !(type_str = json_object_get_string(rule)) ||
            !json_object_object_get_ex(rule, "field", &rule) ||
            !(field_str = json_object_get_string(rule)) ||
            !json_object_object_get_ex(rule, "lo", &rule) ||
            !(lo = json_object_get_int(rule)) ||
            !json_object_object_get_ex(rule, "hi", &rule) ||
            !(hi = json_object_get_int(rule)) ||
            !json_object_object_get_ex(rule, "mask", &rule) ||
            !(mask = json_object_get_int(rule))) {
            fprintf(stderr, "WARN: Skipping invalid rule %d\n", i);
            continue;
        }

        /* Set constraint */
        if (set_constraint(id, type_str, field_str, lo, hi, mask) != 0)
            fprintf(stderr, "WARN: Failed to set rule %u\n", id);
    }

    json_object_put(root);
    printf("SUCCESS: Loaded config from %s\n", config_path);
    return 0;
}

/* --------------------------
 * Cleanup/Unload Resources
 * -------------------------- */
static int unload_ebpf(void) {
    int ret = 0;

    /* Unpin maps */
    char pin_path[256];
    snprintf(pin_path, sizeof(pin_path), "%s/constraint_map", FLUX_PIN_DIR);
    if (g_constraint_fd >= 0) {
        ret |= bpf_map__unpin(NULL, pin_path);
        g_constraint_fd = -1;
    }
    snprintf(pin_path, sizeof(pin_path), "%s/stats_map", FLUX_PIN_DIR);
    if (g_stats_fd >= 0) {
        ret |= bpf_map__unpin(NULL, pin_path);
        g_stats_fd = -1;
    }

    /* Close BPF object */
    if (g_bpf_obj) {
        bpf_object__close(g_bpf_obj);
        g_bpf_obj = NULL;
    }

    printf("SUCCESS: Unloaded FLUX eBPF firewall\n");
    return ret;
}

/* --------------------------
 * Command-Line Help
 * -------------------------- */
static void print_help(void) {
    printf("FLUX eBPF Firewall Management Tool\n