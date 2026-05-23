/*
 * benchmark_csp.c — C99 benchmark harness for CSP solver comparison
 * Compiles: gcc -O2 -std=c99 -lm -o benchmark_csp benchmark_csp.c
 */
#define _POSIX_C_SOURCE 200809L

#define _POSIX_C_SOURCE 200809L
#include <unistd.h>

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <sys/resource.h>

/* ─── Timing helpers ─────────────────────────────────────────────── */

static struct timespec ts_start, ts_end;

static void timer_start(void) {
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
}

static long long timer_stop_ns(void) {
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    return (long long)(ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL
         + (ts_end.tv_nsec - ts_start.tv_nsec);
}

static long get_memory_kb(void) {
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    return ru.ru_maxrss;
}

/* ─── Problem 1: 8-Queens ────────────────────────────────────────── */

static int queens_count;
static int queens_col[8];
static int queens_diag1[15]; /* row + col */
static int queens_diag2[15]; /* row - col + 7 */

static void queens_solve(int row) {
    if (row == 8) {
        queens_count++;
        return;
    }
    for (int col = 0; col < 8; col++) {
        if (queens_col[col] || queens_diag1[row + col] || queens_diag2[row - col + 7])
            continue;
        queens_col[col] = 1;
        queens_diag1[row + col] = 1;
        queens_diag2[row - col + 7] = 1;
        queens_solve(row + 1);
        queens_col[col] = 0;
        queens_diag1[row + col] = 0;
        queens_diag2[row - col + 7] = 0;
    }
}

static int run_queens(void) {
    queens_count = 0;
    memset(queens_col, 0, sizeof(queens_col));
    memset(queens_diag1, 0, sizeof(queens_diag1));
    memset(queens_diag2, 0, sizeof(queens_diag2));
    queens_solve(0);
    return queens_count;
}

/* ─── Problem 2: Graph Coloring ──────────────────────────────────── */

#define GC_NODES 20
#define GC_EDGES 40
#define GC_COLORS 3

/* Simple LCG for reproducibility */
static unsigned int lcg_state;

static unsigned int lcg_next(void) {
    lcg_state = lcg_state * 1103515245u + 12345u;
    return (lcg_state >> 16) & 0x7fff;
}

static int gc_adj[GC_NODES][GC_NODES];
static int gc_color[GC_NODES];
static int gc_count;

static void gc_generate_graph(void) {
    lcg_state = 42;
    memset(gc_adj, 0, sizeof(gc_adj));
    int placed = 0;
    while (placed < GC_EDGES) {
        int u = lcg_next() % GC_NODES;
        int v = lcg_next() % GC_NODES;
        if (u == v || gc_adj[u][v]) continue;
        gc_adj[u][v] = 1;
        gc_adj[v][u] = 1;
        placed++;
    }
}

static void gc_solve(int node) {
    if (node == GC_NODES) {
        gc_count++;
        return;
    }
    for (int c = 0; c < GC_COLORS; c++) {
        int ok = 1;
        for (int j = 0; j < node; j++) {
            if (gc_adj[node][j] && gc_color[j] == c) {
                ok = 0;
                break;
            }
        }
        if (!ok) continue;
        gc_color[node] = c;
        gc_solve(node + 1);
    }
    /* no need to reset gc_color[node] — overwritten next visit */
}

static int run_graph_coloring(void) {
    gc_generate_graph();
    gc_count = 0;
    memset(gc_color, 0, sizeof(gc_color));
    gc_solve(0);
    return gc_count;
}

/* ─── Problem 3: Job Scheduling (minimize makespan) ──────────────── */

#define JS_NTASKS  10
#define JS_NRES    5
#define JS_MAX_TIME 200  /* upper bound for search */

static const int js_duration[JS_NTASKS] = {2, 5, 3, 7, 1, 4, 6, 2, 3, 5};
/* Each task uses exactly 1 of 5 resources — we assign round-robin:
 * task i uses resource (i % 5) to ensure contention */
static const int js_resource[JS_NTASKS] = {0, 1, 2, 3, 4, 0, 1, 2, 3, 4};

static int js_start[JS_NTASKS];
static int js_best_makespan;
static int js_schedule_count;
/* Track resource usage: for each resource, list of end times for scheduled tasks */
static int js_res_end[JS_NRES][JS_NTASKS];
static int js_res_count[JS_NRES];

static int compute_current_makespan(void) {
    int ms = 0;
    for (int i = 0; i < JS_NTASKS; i++) {
        int end = js_start[i] + js_duration[i];
        if (end > ms) ms = end;
    }
    return ms;
}

static int earliest_start_for_task(int task) {
    /* Find the earliest time task can start respecting its resource */
    int res = js_resource[task];
    int earliest = 0;
    for (int k = 0; k < js_res_count[res]; k++) {
        /* The resource becomes free at js_res_end[res][k], task can start then */
        if (js_res_end[res][k] > earliest)
            earliest = js_res_end[res][k];
    }
    /* Actually, we need to wait for ALL tasks on this resource to finish before
     * we can start — no, the resource can only serve one task at a time.
     * So the new task can start after the latest finish of tasks on this resource. */
    /* The above loop already finds the max end time for this resource.
     * But we should also consider that tasks are scheduled sequentially. */
    return earliest;
}

static void js_solve(int task) {
    if (task == JS_NTASKS) {
        int ms = compute_current_makespan();
        js_schedule_count++;
        if (ms < js_best_makespan) {
            js_best_makespan = ms;
        }
        return;
    }

    int res = js_resource[task];
    /* Compute earliest start based on resource availability */
    int earliest = 0;
    for (int k = 0; k < js_res_count[res]; k++) {
        if (js_res_end[res][k] > earliest)
            earliest = js_res_end[res][k];
    }

    /* Also consider starting at time 0 or after each previously scheduled task
     * on ANY resource that might affect ordering — but for correctness and
     * finding optimal, we try start times from 0 up to current best makespan */
    int upper = js_best_makespan - 1; /* no point starting at or beyond best */
    if (upper < 0) upper = JS_MAX_TIME;

    for (int t = earliest; t <= upper; t++) {
        js_start[task] = t;

        /* Prune: if this task alone pushes makespan beyond best, skip */
        if (t + js_duration[task] >= js_best_makespan) continue;

        /* Add to resource */
        int idx = js_res_count[res];
        js_res_end[res][idx] = t + js_duration[task];
        js_res_count[res]++;

        js_solve(task + 1);

        js_res_count[res]--;
    }
}

static int run_job_scheduling(void) {
    memset(js_start, 0, sizeof(js_start));
    memset(js_res_end, 0, sizeof(js_res_end));
    memset(js_res_count, 0, sizeof(js_res_count));
    js_best_makespan = JS_MAX_TIME;
    js_schedule_count = 0;
    js_solve(0);
    return js_best_makespan;
}

/* ─── Platform detection ─────────────────────────────────────────── */

#if defined(__aarch64__) || defined(__ARM_ARCH)
#define ARCH_NAME "aarch64"
#elif defined(__x86_64__) || defined(__amd64__)
#define ARCH_NAME "x86_64"
#elif defined(__i386__)
#define ARCH_NAME "x86"
#else
#define ARCH_NAME "unknown"
#endif

static int get_cores(void) {
    long n = sysconf(_SC_NPROCESSORS_ONLN);
    return (n > 0) ? (int)n : 1;
}

/* ─── Main ───────────────────────────────────────────────────────── */

int main(void) {
    int solutions_queens, solutions_gc, makespan_js;
    long long wall_ns;
    clock_t cpu_start, cpu_end;
    long mem_kb;

    printf("{\n");
    printf("  \"problems\": [\n");

    /* ── 8-Queens ── */
    cpu_start = clock();
    timer_start();
    solutions_queens = run_queens();
    wall_ns = timer_stop_ns();
    cpu_end = clock();
    mem_kb = get_memory_kb();

    printf("    {\n");
    printf("      \"name\": \"8-queens\",\n");
    printf("      \"solutions_found\": %d,\n", solutions_queens);
    printf("      \"wall_time_ns\": %lld,\n", wall_ns);
    printf("      \"cpu_cycles\": %.0f,\n", (double)(cpu_end - cpu_start));
    printf("      \"memory_peak_kb\": %ld,\n", mem_kb);
    printf("      \"solver\": \"backtracking\"\n");
    printf("    },\n");

    /* ── Graph Coloring ── */
    cpu_start = clock();
    timer_start();
    solutions_gc = run_graph_coloring();
    wall_ns = timer_stop_ns();
    cpu_end = clock();
    mem_kb = get_memory_kb();

    printf("    {\n");
    printf("      \"name\": \"graph-coloring-20n-40e-3c\",\n");
    printf("      \"solutions_found\": %d,\n", solutions_gc);
    printf("      \"wall_time_ns\": %lld,\n", wall_ns);
    printf("      \"cpu_cycles\": %.0f,\n", (double)(cpu_end - cpu_start));
    printf("      \"memory_peak_kb\": %ld,\n", mem_kb);
    printf("      \"solver\": \"backtracking\"\n");
    printf("    },\n");

    /* ── Job Scheduling ── */
    cpu_start = clock();
    timer_start();
    makespan_js = run_job_scheduling();
    wall_ns = timer_stop_ns();
    cpu_end = clock();
    mem_kb = get_memory_kb();

    printf("    {\n");
    printf("      \"name\": \"job-scheduling-10t-5r\",\n");
    printf("      \"solutions_found\": %d,\n", makespan_js);
    printf("      \"wall_time_ns\": %lld,\n", wall_ns);
    printf("      \"cpu_cycles\": %.0f,\n", (double)(cpu_end - cpu_start));
    printf("      \"memory_peak_kb\": %ld,\n", mem_kb);
    printf("      \"solver\": \"backtracking\"\n");
    printf("    }\n");

    printf("  ],\n");

    printf("  \"platform\": {\n");
    printf("    \"compiler\": \"gcc\",\n");
    printf("    \"arch\": \"%s\",\n", ARCH_NAME);
    printf("    \"cores\": %d\n", get_cores());
    printf("  }\n");

    printf("}\n");
    return 0;
}
