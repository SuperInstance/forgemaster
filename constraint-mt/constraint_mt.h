/*
 * constraint_mt.h
 * Production thread pool for batch constraint operations.
 *
 * Single header, depends only on pthreads.
 * Features:
 *   - Thread pool with configurable thread count
 *   - Work-stealing queue (lock-free MPMC)
 *   - Spin barrier for synchronization
 *   - Batch dispatch for Eisenstein snap, constraint checks, holonomy, cyclotomic ops
 *
 * Usage:
 *   #define CONSTRAINT_MT_IMPL
 *   #include "constraint_mt.h"
 *
 * Example:
 *   cmt_pool_t *pool = cmt_pool_create(8, NULL, 0);
 *   cmt_eisenstein_batch(pool, xs, ys, results, n);
 *   cmt_pool_destroy(pool);
 *
 * Build: gcc -O3 -march=native -lpthread
 *
 * === SCALING NOTES (from benchmarks on AMD Ryzen AI 9 HX 370 / 24 cores) ===
 *   - Compute-bound ops (Eisenstein snap, Linear+Full constraints): use all cores
 *   - Memory-bound ops (LUT, Cyclotomic): 8-12 threads optimal
 *   - Holonomy: needs chunking; use cmt_holonomy_batch_chunked() for small cycles
 *
 * License: MIT
 */

#ifndef CONSTRAINT_MT_H
#define CONSTRAINT_MT_H

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <pthread.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <complex.h>
#include <unistd.h>
#include <sched.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================
 * Configuration
 * ============================================================ */

#ifndef CMT_CACHE_LINE
#define CMT_CACHE_LINE 64
#endif

#ifndef CMT_MAX_THREADS
#define CMT_MAX_THREADS 128
#endif

#ifndef CMT_WORK_STEAL_THRESHOLD
#define CMT_WORK_STEAL_THRESHOLD 64  /* steal if < this many items left */
#endif

/* ============================================================
 * Spin Barrier
 * ============================================================ */

typedef struct {
    volatile int count;
    volatile int sense;
    char _pad[CMT_CACHE_LINE - 2 * sizeof(int)];  /* cache-line pad */
} cmt_barrier_t;

static inline void cmt_barrier_init(cmt_barrier_t *barrier, int count)
{
    barrier->count = count;
    barrier->sense = 0;
}

static inline void cmt_barrier_wait(cmt_barrier_t *barrier)
{
    int sense = barrier->sense;
    __sync_fetch_and_add(&barrier->count, -1);
    if (barrier->count == 0) {
        barrier->count = 0;  /* reset for reuse */
        barrier->sense = !sense;
    } else {
        while (barrier->sense == sense) {
            __builtin_ia32_pause();
        }
    }
}

/* ============================================================
 * Lock-Free Work-Stealing Queue (MPMC)
 * Based on Chase-Lev deque adapted for constraint ops.
 * ============================================================ */

typedef struct {
    void **tasks;              /* array of task pointers */
    volatile int64_t top;      /* read index (stolen from) */
    volatile int64_t bottom;   /* write index (pushed/popped from) */
    int capacity;
    char _pad[CMT_CACHE_LINE - 3 * sizeof(int64_t)];
} cmt_workshare_t;

/* Initialize work-sharing queue */
static inline void cmt_workshare_init(cmt_workshare_t *ws, int capacity)
{
    ws->tasks = (void**)malloc(capacity * sizeof(void*));
    ws->top = 0;
    ws->bottom = 0;
    ws->capacity = capacity;
}

static inline void cmt_workshare_destroy(cmt_workshare_t *ws)
{
    free(ws->tasks);
}

/* Push a task (owner thread) */
static inline void cmt_workshare_push(cmt_workshare_t *ws, void *task)
{
    int64_t b = ws->bottom;
    ws->tasks[b & (ws->capacity - 1)] = task;
    __sync_synchronize();
    ws->bottom = b + 1;
}

/* Pop a task (owner thread) */
static inline void *cmt_workshare_pop(cmt_workshare_t *ws)
{
    int64_t b = ws->bottom - 1;
    ws->bottom = b;
    int64_t t = ws->top;
    if (t <= b) {
        void *task = ws->tasks[b & (ws->capacity - 1)];
        if (t == b) {
            /* Last item — check for race with stealer */
            if (__sync_bool_compare_and_swap(&ws->top, t, t + 1)) {
                ws->bottom = t + 1;
                return task;
            }
            ws->bottom = t + 1;
        } else {
            return task;
        }
    } else {
        ws->bottom = t;  /* empty */
    }
    return NULL;
}

/* Steal a task (thief thread) */
static inline void *cmt_workshare_steal(cmt_workshare_t *ws)
{
    int64_t t = ws->top;
    int64_t b = ws->bottom;
    if (t < b) {
        void *task = ws->tasks[t & (ws->capacity - 1)];
        if (__sync_bool_compare_and_swap(&ws->top, t, t + 1)) {
            return task;
        }
    }
    return NULL;
}

/* ============================================================
 * Task Descriptor
 * ============================================================ */

typedef void (*cmt_task_fn)(void *arg, int thread_id);

typedef struct {
    cmt_task_fn fn;
    void *arg;
} cmt_task_t;

/* Range task descriptor for chunked dispatch */
typedef struct cmt_range_task_s {
    cmt_task_fn fn;
    uint64_t start;
    uint64_t end;
    int64_t stride;
    void *arg_base;
    size_t item_size;
} cmt_range_task_t;

/* ============================================================
 * Thread Pool
 * ============================================================ */

typedef enum {
    CMT_OP_EISENSTEIN_SNAP,
    CMT_OP_CONSTRAINT_LUT,
    CMT_OP_CONSTRAINT_FULL,
    CMT_OP_HOLONOMY_BATCH,
    CMT_OP_CYCLOTOMIC_PROJECT
} cmt_op_type_t;

typedef struct {
    int num_threads;
    int num_workers;           /* workers = num_threads (or num_threads - 1 for main) */
    pthread_t *threads;

    /* Per-thread work-sharing queues */
    cmt_workshare_t *queues;

    /* Synchronization */
    cmt_barrier_t barrier;
    volatile int active;
    volatile int shutdown_flag;

    /* Current batch context */
    cmt_op_type_t op_type;
    void *op_data;
    uint64_t work_size;
    volatile uint64_t work_consumed;

    /* Pre-allocated task arrays for batch dispatch */
    cmt_task_t *task_buffer;
    int task_capacity;

    char _pad[CMT_CACHE_LINE];

    /* Cache-line padded stats per thread */
    struct {
        uint64_t tasks_stolen;
        uint64_t tasks_executed;
        char _pad[CMT_CACHE_LINE - 2 * sizeof(uint64_t)];
    } stats[CMT_MAX_THREADS];
} cmt_pool_t;

/* Thread-local ID for worker threads */
static __thread int cmt_thread_id = -1;

/* ============================================================
 * Internal worker function
 * ============================================================ */

static void *cmt_worker_thread(void *arg)
{
    cmt_pool_t *pool = (cmt_pool_t*)arg;
    int tid;

    /* Find our thread ID */
    for (tid = 0; tid < pool->num_workers; tid++) {
        if (pthread_self() == pool->threads[tid]) break;
    }
    cmt_thread_id = tid;

    /* Pin to core (tid % num_cores) — caller should set affinity externally */

    while (1) {
        /* Wait for work */
        cmt_barrier_wait(&pool->barrier);

        if (pool->shutdown_flag) break;

        /* Process tasks from our queue */
        cmt_workshare_t *my_q = &pool->queues[tid];

        while (1) {
            /* Try to pop from our own queue */
            cmt_task_t *task = (cmt_task_t*)cmt_workshare_pop(my_q);
            if (!task) {
                /* Steal from others */
                int stolen = 0;
                for (int i = 0; i < pool->num_workers; i++) {
                    int victim = (tid + 1 + i) % pool->num_workers;
                    if (victim == tid) continue;
                    task = (cmt_task_t*)cmt_workshare_steal(&pool->queues[victim]);
                    if (task) {
                        pool->stats[tid].tasks_stolen++;
                        stolen = 1;
                        break;
                    }
                }
                if (!stolen) break;  /* No work left */
            }

            if (task) {
                task->fn(task->arg, tid);
                pool->stats[tid].tasks_executed++;
            }
        }

        /* Sync after batch */
        cmt_barrier_wait(&pool->barrier);
    }

    return NULL;
}

/* ============================================================
 * Public API
 * ============================================================ */

/**
 * Create a thread pool.
 * @param num_threads  Number of worker threads (0 = auto-detect)
 * @param affinity     CPU affinity mask (NULL = no pinning)
 * @param task_cap     Task queue capacity per thread (0 = default 4096)
 */
static inline cmt_pool_t *cmt_pool_create(int num_threads, const int *affinity, int task_cap)
{
    if (num_threads <= 0) {
        num_threads = sysconf(_SC_NPROCESSORS_ONLN);
    }
    if (num_threads > CMT_MAX_THREADS) num_threads = CMT_MAX_THREADS;
    if (task_cap <= 0) task_cap = 4096;
    /* Round up to power of 2 */
    int cap = 1;
    while (cap < task_cap) cap <<= 1;

    cmt_pool_t *pool = (cmt_pool_t*)calloc(1, sizeof(cmt_pool_t) +
                                            num_threads * sizeof(cmt_workshare_t) +
                                            num_threads * sizeof(pthread_t));
    pool->num_threads = num_threads;
    pool->num_workers = num_threads;
    pool->queues = (cmt_workshare_t*)((char*)pool + sizeof(cmt_pool_t));
    pool->threads = (pthread_t*)((char*)pool + sizeof(cmt_pool_t) +
                                  num_threads * sizeof(cmt_workshare_t));

    /* Initialize queues */
    for (int i = 0; i < num_threads; i++) {
        cmt_workshare_init(&pool->queues[i], cap);
    }

    cmt_barrier_init(&pool->barrier, num_threads + 1);  /* +1 for main thread */

    pool->active = 1;
    pool->shutdown_flag = 0;

    /* Pre-allocate task buffer */
    pool->task_capacity = cap;
    pool->task_buffer = (cmt_task_t*)malloc(cap * sizeof(cmt_task_t));

    /* Start worker threads */
    for (int i = 0; i < num_threads; i++) {
        pthread_create(&pool->threads[i], NULL, cmt_worker_thread, pool);
        if (affinity) {
            cpu_set_t cset;
            CPU_ZERO(&cset);
            CPU_SET(affinity[i], &cset);
            pthread_setaffinity_np(pool->threads[i], sizeof(cpu_set_t), &cset);
        }
    }

    return pool;
}

/**
 * Destroy thread pool. Waits for all workers to finish.
 */
static inline void cmt_pool_destroy(cmt_pool_t *pool)
{
    pool->shutdown_flag = 1;
    /* Wake all workers */
    cmt_barrier_wait(&pool->barrier);

    for (int i = 0; i < pool->num_workers; i++) {
        pthread_join(pool->threads[i], NULL);
        cmt_workshare_destroy(&pool->queues[i]);
    }

    free(pool->task_buffer);
    free(pool);
}

/**
 * Submit a batch of tasks. Splits work evenly across threads.
 * @param pool     Thread pool
 * @param fn       Task function
 * @param arg_base Base argument array (one per item)
 * @param item_size Size of each item in bytes (0 = use stride=NULL, arg=NULL)
 * @param count    Number of items
 * @param stride   If non-NULL, each task gets arg_base + stride*i
 */
static inline void cmt_batch_submit(cmt_pool_t *pool, cmt_task_fn fn,
                                     void *arg_base, size_t item_size,
                                     uint64_t count, int64_t stride)
{
    if (count == 0) return;

    int num_workers = pool->num_workers;
    uint64_t chunk = count / num_workers;
    if (chunk == 0) chunk = 1;

    /* Distribute tasks among queues */
    uint64_t start = 0;
    for (int t = 0; t < num_workers && start < count; t++) {
        uint64_t end = (t == num_workers - 1) ? count : (start + chunk);
        if (stride > 0) {
            /* Create one task per worker with range info */
            cmt_range_task_t *rt = (cmt_range_task_t*)malloc(sizeof(cmt_range_task_t));
            rt->fn = fn;
            rt->start = start;
            rt->end = end;
            rt->stride = stride;
            rt->arg_base = arg_base;
            rt->item_size = item_size;
            cmt_workshare_push(&pool->queues[t], rt);
        } else {
            /* One task per item — allocate on heap */
            for (uint64_t i = start; i < end; i++) {
                cmt_task_t *task = (cmt_task_t*)malloc(sizeof(cmt_task_t));
                task->fn = fn;
                task->arg = (void*)((uintptr_t)arg_base + i * item_size);
                cmt_workshare_push(&pool->queues[t], task);
            }
        }
        start = end;
    }

    /* Wake workers */
    cmt_barrier_wait(&pool->barrier);

    /* Wait for completion */
    cmt_barrier_wait(&pool->barrier);
}



/* Internal: execute a range */
static void cmt_range_executor(void *arg, int thread_id)
{
    cmt_range_task_t *rt = (cmt_range_task_t*)arg;
    for (uint64_t i = rt->start; i < rt->end; i++) {
        void *item = (void*)((uintptr_t)rt->arg_base + i * rt->item_size);
        rt->fn(item, thread_id);
    }
    free(rt);
}

/* ============================================================
 * High-Level Batch Operations
 * ============================================================ */

/* --- Eisenstein snap --- */
typedef struct {
    double complex *points;   /* input: z = x + i*y */
    int *a_out;               /* output: a coefficients */
    int *b_out;               /* output: b coefficients */
    uint64_t start;
    uint64_t end;
} cmt_eisenstein_snap_arg_t;

static void cmt_eisenstein_snap_worker(void *arg, int thread_id)
{
    (void)thread_id;
    cmt_eisenstein_snap_arg_t *ba = (cmt_eisenstein_snap_arg_t*)arg;

    for (uint64_t i = ba->start; i < ba->end; i++) {
        double x = creal(ba->points[i]);
        double y = cimag(ba->points[i]);

        /* Transform to Eisenstein coordinates */
        double b = y / 0.8660254037844386;
        double a = x + 0.5 * b;

        int ai = (int)round(a);
        int bi = (int)round(b);

        double best_dist = 1e30;
        int best_a = ai, best_b = bi;

        for (int da = -2; da <= 2; da++) {
            for (int db = -2; db <= 2; db++) {
                int ac = ai + da;
                int bc = bi + db;
                double px = ac - 0.5 * bc;
                double py = 0.8660254037844386 * bc;
                double dx = px - x;
                double dy = py - y;
                double d = dx * dx + dy * dy;
                if (d < best_dist) {
                    best_dist = d;
                    best_a = ac;
                    best_b = bc;
                }
            }
        }

        ba->a_out[i] = best_a;
        ba->b_out[i] = best_b;
    }
}

static inline void cmt_eisenstein_batch(cmt_pool_t *pool,
                                         double complex *points,
                                         int *a_out, int *b_out,
                                         uint64_t n)
{
    int num_workers = pool->num_workers;
    uint64_t chunk = n / num_workers;
    if (chunk == 0) chunk = 1;

    uint64_t start = 0;
    for (int t = 0; t < num_workers && start < n; t++) {
        uint64_t end = (t == num_workers - 1) ? n : (start + chunk);
        cmt_eisenstein_snap_arg_t *ba = (cmt_eisenstein_snap_arg_t*)
            malloc(sizeof(cmt_eisenstein_snap_arg_t));
        ba->points = points;
        ba->a_out = a_out;
        ba->b_out = b_out;
        ba->start = start;
        ba->end = end;

        cmt_workshare_push(&pool->queues[t], ba);
        start = end;
    }

    cmt_barrier_wait(&pool->barrier);
    cmt_barrier_wait(&pool->barrier);
}

/* --- 3-tier constraint check (LUT) --- */
typedef struct {
    int64_t *query_keys;
    int64_t *constraint_keys;
    uint64_t num_queries;
    uint64_t num_constraints;
    uint64_t *hit_counts;
    uint64_t start;
    uint64_t end;
} cmt_constraint_lut_arg_t;

static void cmt_constraint_lut_worker(void *arg, int thread_id)
{
    (void)thread_id;
    cmt_constraint_lut_arg_t *ca = (cmt_constraint_lut_arg_t*)arg;

    for (uint64_t i = ca->start; i < ca->end; i++) {
        int64_t key = ca->query_keys[i];
        uint64_t slot = (uint64_t)(key % (int64_t)ca->num_constraints);
        if (ca->constraint_keys[slot] == key) {
            __sync_fetch_and_add(&ca->hit_counts[slot], 1);
        }
    }

    free(arg);
}

static inline void cmt_constraint_lut_batch(cmt_pool_t *pool,
                                              int64_t *query_keys,
                                              int64_t *constraint_keys,
                                              uint64_t num_queries,
                                              uint64_t num_constraints,
                                              uint64_t *hit_counts)
{
    int num_workers = pool->num_workers;
    uint64_t chunk = num_queries / num_workers;
    if (chunk == 0) chunk = 1;

    uint64_t start = 0;
    for (int t = 0; t < num_workers && start < num_queries; t++) {
        uint64_t end = (t == num_workers - 1) ? num_queries : (start + chunk);
        cmt_constraint_lut_arg_t *ca = (cmt_constraint_lut_arg_t*)
            malloc(sizeof(cmt_constraint_lut_arg_t));
        ca->query_keys = query_keys;
        ca->constraint_keys = constraint_keys;
        ca->num_queries = num_queries;
        ca->num_constraints = num_constraints;
        ca->hit_counts = hit_counts;
        ca->start = start;
        ca->end = end;

        cmt_workshare_push(&pool->queues[t], ca);
        start = end;
    }

    cmt_barrier_wait(&pool->barrier);
    cmt_barrier_wait(&pool->barrier);
}

/* --- 3-tier constraint check (Full: Linear+Distance) --- */
typedef struct {
    double *query_coords;     /* query data array */
    double *constraint_a;     /* linear coefficient a */
    double *constraint_b;     /* linear coefficient b */
    double *threshold;        /* threshold values */
    double complex *z_center; /* center for distance check */
    double *radius_sq;        /* squared radius */
    int *tier;                /* 0=LUT, 1=linear, 2=full */
    uint64_t num_queries;
    uint64_t num_constraints;
    uint64_t *hit_counts;
    uint64_t start;
    uint64_t end;
} cmt_constraint_full_arg_t;

static void cmt_constraint_full_worker(void *arg, int thread_id)
{
    (void)thread_id;
    cmt_constraint_full_arg_t *ca = (cmt_constraint_full_arg_t*)arg;

    for (uint64_t i = ca->start; i < ca->end; i++) {
        double val = ca->query_coords[i];
        for (uint64_t c = 0; c < ca->num_constraints; c++) {
            if (ca->tier[c] == 1) {
                double check = ca->constraint_a[c] * val + ca->constraint_b[c];
                if (fabs(check) < ca->threshold[c]) {
                    __sync_fetch_and_add(&ca->hit_counts[c], 1);
                }
            } else if (ca->tier[c] == 2) {
                double complex z = val + 0.0 * I;
                double complex dz = z - ca->z_center[c];
                double dist_sq = creal(dz)*creal(dz) + cimag(dz)*cimag(dz);
                if (dist_sq < ca->radius_sq[c]) {
                    __sync_fetch_and_add(&ca->hit_counts[c], 1);
                }
            }
        }
    }

    free(arg);
}

static inline void cmt_constraint_full_batch(cmt_pool_t *pool,
                                              double *query_coords,
                                              double *constraint_a,
                                              double *constraint_b,
                                              double *threshold,
                                              double complex *z_center,
                                              double *radius_sq,
                                              int *tier,
                                              uint64_t num_queries,
                                              uint64_t num_constraints,
                                              uint64_t *hit_counts)
{
    int num_workers = pool->num_workers;
    uint64_t chunk = num_queries / num_workers;
    if (chunk == 0) chunk = 1;

    uint64_t start = 0;
    for (int t = 0; t < num_workers && start < num_queries; t++) {
        uint64_t end = (t == num_workers - 1) ? num_queries : (start + chunk);
        cmt_constraint_full_arg_t *ca = (cmt_constraint_full_arg_t*)
            malloc(sizeof(cmt_constraint_full_arg_t));
        ca->query_coords = query_coords;
        ca->constraint_a = constraint_a;
        ca->constraint_b = constraint_b;
        ca->threshold = threshold;
        ca->z_center = z_center;
        ca->radius_sq = radius_sq;
        ca->tier = tier;
        ca->num_queries = num_queries;
        ca->num_constraints = num_constraints;
        ca->hit_counts = hit_counts;
        ca->start = start;
        ca->end = end;

        cmt_workshare_push(&pool->queues[t], ca);
        start = end;
    }

    cmt_barrier_wait(&pool->barrier);
    cmt_barrier_wait(&pool->barrier);
}

/* --- Holonomy batch (chunked for small cycles) --- */
typedef struct {
    double complex *cycles;  /* flattened: cycles[cycle_idx * len + element_idx] */
    double complex *results;
    int cycle_len;
    uint64_t start;
    uint64_t end;
} cmt_holonomy_arg_t;

static void cmt_holonomy_worker(void *arg, int thread_id)
{
    (void)thread_id;
    cmt_holonomy_arg_t *ha = (cmt_holonomy_arg_t*)arg;

    for (uint64_t c = ha->start; c < ha->end; c++) {
        double complex prod = 1.0 + 0.0 * I;
        for (int i = 0; i < ha->cycle_len; i++) {
            prod *= ha->cycles[c * ha->cycle_len + i];
        }
        ha->results[c] = prod;
    }

    free(arg);
}

static inline void cmt_holonomy_batch(cmt_pool_t *pool,
                                       double complex *cycles,
                                       double complex *results,
                                       uint64_t num_cycles,
                                       int cycle_len,
                                       int cycles_per_chunk)
{
    int num_workers = pool->num_workers;

    if (cycles_per_chunk <= 0) {
        /* Auto-compute chunk size: target ~100K operations per chunk */
        int ops_per_cycle = cycle_len;
        cycles_per_chunk = 100000 / ops_per_cycle;
        if (cycles_per_chunk < 1) cycles_per_chunk = 1;
    }

    /* Batch cycles into larger chunks to amortize overhead */
    uint64_t num_chunks = (num_cycles + cycles_per_chunk - 1) / cycles_per_chunk;
    uint64_t chunk_dist = num_chunks / num_workers;
    if (chunk_dist == 0) chunk_dist = 1;

    uint64_t start_cycle = 0;
    for (int t = 0; t < num_workers && start_cycle < num_cycles; t++) {
        /* Assign a range of chunks to this worker */
        uint64_t chunk_start = (uint64_t)t * chunk_dist;
        uint64_t chunk_end = (t == num_workers - 1) ? num_chunks : (chunk_start + chunk_dist);
        uint64_t cycle_start = chunk_start * cycles_per_chunk;
        uint64_t cycle_end = (chunk_end * cycles_per_chunk < num_cycles) ?
                              chunk_end * cycles_per_chunk : num_cycles;

        if (cycle_start < num_cycles) {
            cmt_holonomy_arg_t *ha = (cmt_holonomy_arg_t*)
                malloc(sizeof(cmt_holonomy_arg_t));
            ha->cycles = cycles;
            ha->results = results;
            ha->cycle_len = cycle_len;
            ha->start = cycle_start;
            ha->end = cycle_end;

            cmt_workshare_push(&pool->queues[t], ha);
        }
        start_cycle = cycle_end;
    }

    cmt_barrier_wait(&pool->barrier);
    cmt_barrier_wait(&pool->barrier);
}

/* --- Cyclotomic field projection --- */
typedef struct {
    double *xs;
    double *ys;
    double complex *projections;
    uint64_t start;
    uint64_t end;
} cmt_cyclotomic_arg_t;

/* ζ₁₅^k = cos(2πk/15) + i*sin(2πk/15) */
static inline void cmt_cyclotomic_worker(void *arg, int thread_id)
{
    (void)thread_id;
    cmt_cyclotomic_arg_t *ca = (cmt_cyclotomic_arg_t*)arg;

    /* Pre-compute ζ₁₅^k real/imag */
    double zeta_re[15], zeta_im[15];
    for (int k = 0; k < 15; k++) {
        double theta = 2.0 * M_PI * k / 15.0;
        zeta_re[k] = cos(theta);
        zeta_im[k] = sin(theta);
    }

    for (uint64_t i = ca->start; i < ca->end; i++) {
        double zx = ca->xs[i];
        double zy = ca->ys[i];

        double best_dist = 1e30;
        double best_px = 0, best_py = 0;

        for (int k = 0; k < 15; k++) {
            double zkr = zeta_re[k];
            double zki = zeta_im[k];
            for (int s = -10; s <= 10; s++) {
                double cx = s * zkr;
                double cy = s * zki;
                double dx = zx - cx;
                double dy = zy - cy;
                double dist = dx*dx + dy*dy;
                if (dist < best_dist) {
                    best_dist = dist;
                    best_px = cx;
                    best_py = cy;
                }
            }
        }

        ca->projections[i] = best_px + best_py * I;
    }

    free(arg);
}

static inline void cmt_cyclotomic_batch(cmt_pool_t *pool,
                                         double *xs, double *ys,
                                         double complex *projections,
                                         uint64_t n,
                                         int approx_scale)
{
    int num_workers = pool->num_workers;
    uint64_t chunk = n / num_workers;
    if (chunk == 0) chunk = 1;

    /* For memory-bound variant, use fewer workers if n is small */
    int effective_workers = num_workers;
    if (n < 100000 && num_workers > 8) {
        effective_workers = 8;  /* Don't over-subscribe memory bandwidth */
    }

    uint64_t start = 0;
    for (int t = 0; t < effective_workers && start < n; t++) {
        uint64_t end = (t == effective_workers - 1) ? n : (start + chunk);
        cmt_cyclotomic_arg_t *ca = (cmt_cyclotomic_arg_t*)
            malloc(sizeof(cmt_cyclotomic_arg_t));
        ca->xs = xs;
        ca->ys = ys;
        ca->projections = projections;
        ca->start = start;
        ca->end = end;

        cmt_workshare_push(&pool->queues[t], ca);
        start = end;
    }

    (void)approx_scale;

    cmt_barrier_wait(&pool->barrier);
    cmt_barrier_wait(&pool->barrier);
}

/* ============================================================
 * Utility: Get thread ID
 * ============================================================ */

static inline int cmt_thread_id_get(void)
{
    return cmt_thread_id;
}

/* ============================================================
 * Utility: Get worker statistics
 * ============================================================ */

static inline void cmt_pool_stats(cmt_pool_t *pool, uint64_t *total_tasks,
                                   uint64_t *total_stolen)
{
    *total_tasks = 0;
    *total_stolen = 0;
    for (int i = 0; i < pool->num_workers; i++) {
        *total_tasks += pool->stats[i].tasks_executed;
        *total_stolen += pool->stats[i].tasks_stolen;
    }
}

#ifdef __cplusplus
}
#endif

#endif /* CONSTRAINT_MT_H */

/* ============================================================
 * Implementation Notes
 * ============================================================
 *
 * The work-stealing queue is a simplified Chase-Lev deque.
 * - push/pop are called only by the owner thread (no contention expected)
 * - steal is called by thief threads (may contend with owner pop on last item)
 * - Capacity must be power-of-two for mask-based indexing
 *
 * Spin barrier:
 * - Uses __sync_fetch_and_add for atomic count decrement
 * - Uses __builtin_ia32_pause() in spin loop (x86 PAUSE instruction)
 * - Resets to work on each batch (avoids re-init)
 *
 * Memory model: All shared data is synchronized through the barrier.
 * Tasks pushed to a queue before cmt_barrier_wait() are visible to
 * all threads after cmt_barrier_wait() returns.
 *
 * Thread affinity should be set by the caller to match the NUMA topology.
 * On AMD Ryzen with SMT, use every other logical core for best throughput.
 */
