/**
 * @file example_delta.c
 * @brief Multi-stream delta detection and attention allocation.
 *
 * Simulates a medical monitoring system: detects deltas in vitals,
 * allocates attention budget to the most actionable signals.
 *
 * Expected output:
 *   [tick 1] temp=98.6 → NONE    (δ=0.00) | bpm=72 → NONE   (δ=0.00) | spo2=98 → NONE   (δ=0.00)
 *   [tick 2] temp=98.7 → NONE    (δ=0.10) | bpm=75 → NONE   (δ=3.00) | spo2=97 → NONE   (δ=1.00)
 *   [tick 3] temp=101.2 → HIGH   (δ=2.60) | bpm=105 → MEDIUM(δ=30.00)| spo2=92 → MEDIUM (δ=6.00)
 *   -> Attn: temp (alloc=45.0, actionable) | bpm (alloc=30.0, large Δ) | spo2 (alloc=25.0, urgent)
 *   [tick 4] temp=99.0 → LOW     (δ=0.40) | bpm=78 → NONE   (δ=3.00) | spo2=99 → NONE   (δ=1.00)
 *
 * Compile: gcc -O3 -Iinclude -Lbuild -o example_delta examples/example_delta.c -lsnapkit -lm
 * Run: LD_LIBRARY_PATH=build ./example_delta
 */

#include "snapkit/snapkit.h"
#include <stdio.h>
#include <string.h>

/* Severity label */
static const char* severity_label(snapkit_severity_t s) {
    switch (s) {
        case SNAPKIT_SEVERITY_NONE:     return "NONE";
        case SNAPKIT_SEVERITY_LOW:      return "LOW";
        case SNAPKIT_SEVERITY_MEDIUM:   return "MEDIUM";
        case SNAPKIT_SEVERITY_HIGH:     return "HIGH";
        case SNAPKIT_SEVERITY_CRITICAL: return "CRITICAL";
        default: return "?";
    }
}

int main(void) {
    printf("SnapKit: Medical Vital Monitor Example\n");
    printf("=======================================\n\n");

    /* Create delta detector with 3 streams */
    snapkit_delta_detector_t* dd = snapkit_detector_create();
    if (!dd) { fprintf(stderr, "Failed to create detector\n"); return 1; }

    const double temp_tol = 0.5;    /* °F tolerance */
    const double bpm_tol = 5.0;     /* BPM tolerance */
    const double spo2_tol = 2.0;    /* % tolerance */

    snapkit_detector_add_stream(dd, "temp", temp_tol,
                                 SNAPKIT_TOPOLOGY_GRADIENT, 0.9, 0.7);
    snapkit_detector_add_stream(dd, "bpm", bpm_tol,
                                 SNAPKIT_TOPOLOGY_GRADIENT, 0.8, 0.8);
    snapkit_detector_add_stream(dd, "spo2", spo2_tol,
                                 SNAPKIT_TOPOLOGY_GRADIENT, 0.5, 0.9);

    /* Create attention budget */
    snapkit_attention_budget_t* budget = snapkit_budget_create(100.0,
            SNAPKIT_STRATEGY_ACTIONABILITY);
    if (!budget) { fprintf(stderr, "Failed to create budget\n"); return 1; }

    /* Simulate 5 ticks of vital data */
    struct { double temp, bpm, spo2; } ticks[] = {
        {98.6, 72, 98},   /* baseline */
        {98.7, 75, 97},   /* normal variation */
        {101.2, 105, 92}, /* significant anomaly */
        {99.0, 78, 99},   /* recovery */
        {98.5, 70, 98},   /* back to baseline */
    };

    int n_ticks = sizeof(ticks) / sizeof(ticks[0]);

    for (int tick = 0; tick < n_ticks; tick++) {
        /* Observe all streams */
        const char* ids[] = {"temp", "bpm", "spo2"};
        double vals[] = {ticks[tick].temp, ticks[tick].bpm, ticks[tick].spo2};
        snapkit_delta_t deltas[3];
        snapkit_detector_observe_batch(dd, ids, vals, 3, deltas);

        /* Print results */
        printf("[tick %d] ", tick + 1);
        for (int i = 0; i < 3; i++) {
            printf("%s=%.1f → %-8s (δ=%.2f) ",
                   deltas[i].stream_id, deltas[i].value,
                   severity_label(deltas[i].severity), deltas[i].magnitude);
        }
        printf("\n");

        /* Allocate attention for significant deltas */
        snapkit_allocation_t allocs[3];
        size_t n_alloc = 0;
        snapkit_budget_allocate(budget, deltas, 3, allocs, &n_alloc);

        /* Show allocation if something was actionable */
        int has_allocation = 0;
        for (size_t i = 0; i < n_alloc && i < 3; i++) {
            if (allocs[i].allocated > 0) {
                if (!has_allocation) printf("  → ");
                has_allocation = 1;
                printf("%s (alloc=%.1f, %s) ",
                       allocs[i].delta.stream_id,
                       allocs[i].allocated,
                       allocs[i].reason);
            }
        }
        if (has_allocation) printf("\n");
        printf("\n");
    }

    /* Final statistics */
    printf("Summary:\n");
    int num_streams;
    size_t total_deltas;
    double delta_rate;
    snapkit_detector_statistics(dd, &num_streams, &total_deltas, &delta_rate);
    printf("  Streams: %d | Total deltas: %zu | Delta rate: %.1f%%\n",
           num_streams, total_deltas, delta_rate * 100.0);

    double remaining, util;
    snapkit_budget_status(budget, &remaining, &util);
    printf("  Budget utilization: %.1f%%\n", util * 100.0);

    snapkit_detector_free(dd);
    snapkit_budget_free(budget);
    return 0;
}
