/**
 * @file core_delta.c
 * @brief Delta detector, attention budget, script library, constraint sheaf.
 */

#include "snapkit/snapkit_internal.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>

/* ===========================================================================
 * Delta Detector -- Implementation
 * ========================================================================= */

snapkit_delta_detector_t* snapkit_detector_create(void) {
    snapkit_delta_detector_t* dd = (snapkit_delta_detector_t*)
        calloc(1, sizeof(snapkit_delta_detector_t));
    if (!dd) return NULL;
    dd->num_streams = 0;
    dd->tick = 0;

    for (int i = 0; i < SNAPKIT_MAX_STREAMS; i++) {
        dd->streams[i].snap.history.results = NULL;
        dd->streams[i].has_current = false;
    }

    return dd;
}

void snapkit_detector_free(snapkit_delta_detector_t* dd) {
    if (!dd) return;
    for (int i = 0; i < SNAPKIT_MAX_STREAMS; i++) {
        free(dd->streams[i].snap.history.results);
    }
    free(dd);
}

snapkit_error_t snapkit_detector_add_stream(snapkit_delta_detector_t* dd,
                                             const char* stream_id,
                                             double tolerance,
                                             snapkit_topology_t topology,
                                             double actionability,
                                             double urgency) {
    if (!dd || !stream_id) return SNAPKIT_ERR_NULL;
    if (dd->num_streams >= SNAPKIT_MAX_STREAMS) return SNAPKIT_ERR_SIZE;

    int idx = dd->num_streams;
    snapkit_delta_stream_t* s = &dd->streams[idx];

    strncpy(s->stream_id, stream_id, sizeof(s->stream_id) - 1);
    s->stream_id[sizeof(s->stream_id) - 1] = '\0';

    s->snap.tolerance       = tolerance;
    s->snap.topology        = topology;
    s->snap.baseline        = 0.0;
    s->snap.adaptation_rate = SNAPKIT_DEFAULT_ADAPTATION_RATE;
    s->snap.history.results = (snapkit_snap_result_t*)
        calloc(SNAPKIT_SNAP_HISTORY_MAX, sizeof(snapkit_snap_result_t));
    if (!s->snap.history.results) return SNAPKIT_ERR_NULL;
    s->snap.history.head = 0;
    s->snap.history.count = 0;
    s->snap.history.sum_delta = 0.0;
    s->snap.history.max_delta = 0.0;
    s->snap.history.snap_cnt = 0;
    s->snap.history.delta_cnt = 0;

    s->actionability = (isnan(actionability)) ? 1.0 : actionability;
    s->urgency       = (isnan(urgency)) ? 1.0 : urgency;
    s->has_current   = false;

    dd->num_streams++;
    return SNAPKIT_OK;
}

static snapkit_delta_stream_t* find_stream(snapkit_delta_detector_t* dd,
                                            const char* stream_id) {
    for (int i = 0; i < dd->num_streams; i++) {
        if (strcmp(dd->streams[i].stream_id, stream_id) == 0)
            return &dd->streams[i];
    }
    return NULL;
}

snapkit_error_t snapkit_detector_observe(snapkit_delta_detector_t* dd,
                                          const char* stream_id,
                                          double value,
                                          snapkit_delta_t* out) {
    if (!dd || !stream_id) return SNAPKIT_ERR_NULL;

    snapkit_delta_stream_t* s = find_stream(dd, stream_id);
    if (!s) return SNAPKIT_ERR_NULL;

    dd->tick++;

    snapkit_snap_result_t snap_res;
    snapkit_snap(&s->snap, value, NAN, &snap_res);

    snapkit_delta_t delta;
    delta.value       = value;
    delta.expected    = s->snap.baseline;
    delta.magnitude   = snap_res.delta;
    delta.tolerance   = s->snap.tolerance;
    delta.severity    = snapkit_compute_severity(snap_res.delta, s->snap.tolerance);
    delta.timestamp   = dd->tick;
    strncpy(delta.stream_id, stream_id, sizeof(delta.stream_id) - 1);
    delta.stream_id[sizeof(delta.stream_id) - 1] = '\0';
    delta.actionability = s->actionability;
    delta.urgency       = s->urgency;

    s->current = delta;
    s->has_current = true;

    if (out) *out = delta;
    return SNAPKIT_OK;
}

snapkit_error_t snapkit_detector_observe_batch(snapkit_delta_detector_t* dd,
                                                const char** stream_ids,
                                                const double* values,
                                                size_t n,
                                                snapkit_delta_t* deltas) {
    if (!dd || !stream_ids || !values) return SNAPKIT_ERR_NULL;
    for (size_t i = 0; i < n; i++) {
        snapkit_error_t err = snapkit_detector_observe(dd, stream_ids[i], values[i],
                                                        deltas ? &deltas[i] : NULL);
        if (err != SNAPKIT_OK) return err;
    }
    return SNAPKIT_OK;
}

snapkit_error_t snapkit_detector_current_delta(snapkit_delta_detector_t* dd,
                                                const char* stream_id,
                                                snapkit_delta_t* out) {
    if (!dd || !stream_id || !out) return SNAPKIT_ERR_NULL;
    snapkit_delta_stream_t* s = find_stream(dd, stream_id);
    if (!s || !s->has_current) return SNAPKIT_ERR_NULL;
    *out = s->current;
    return SNAPKIT_OK;
}

void snapkit_detector_statistics(const snapkit_delta_detector_t* dd,
                                  int* num_streams,
                                  size_t* total_deltas,
                                  double* delta_rate) {
    if (!dd) return;
    if (num_streams) *num_streams = dd->num_streams;

    size_t total_d = 0, total_obs = 0;
    for (int i = 0; i < dd->num_streams; i++) {
        total_d   += dd->streams[i].snap.history.delta_cnt;
        total_obs += dd->streams[i].snap.history.snap_cnt +
                     dd->streams[i].snap.history.delta_cnt;
    }

    if (total_deltas) *total_deltas = total_d;
    if (delta_rate)   *delta_rate = total_obs > 0 ?
                                    (double)total_d / (double)total_obs : 0.0;
}

/* ===========================================================================
 * Attention Budget -- Implementation
 * ========================================================================= */

snapkit_attention_budget_t* snapkit_budget_create(double total_budget,
                                                    snapkit_strategy_t strategy) {
    snapkit_attention_budget_t* ab = (snapkit_attention_budget_t*)
        calloc(1, sizeof(snapkit_attention_budget_t));
    if (!ab) return NULL;
    ab->total_budget     = total_budget;
    ab->remaining        = total_budget;
    ab->strategy         = strategy;
    ab->exhaustion_count = 0;
    ab->cycle_count      = 0;
    return ab;
}

void snapkit_budget_free(snapkit_attention_budget_t* ab) {
    free(ab);
}

/* Helper: copy reason string safely */
static void set_reason(char* dest, size_t dest_size, const char* src) {
    size_t len = strlen(src);
    if (len >= dest_size) len = dest_size - 1;
    memcpy(dest, src, len);
    dest[len] = '\0';
}

snapkit_error_t snapkit_budget_allocate(snapkit_attention_budget_t* ab,
                                         const snapkit_delta_t* deltas,
                                         size_t n,
                                         snapkit_allocation_t* allocs,
                                         size_t* n_allocated) {
    if (!ab || !deltas || !allocs || !n_allocated) return SNAPKIT_ERR_NULL;

    ab->cycle_count++;
    ab->remaining = ab->total_budget;
    size_t allocated_count = 0;

    if (n == 0) { *n_allocated = 0; return SNAPKIT_OK; }

    switch (ab->strategy) {
    case SNAPKIT_STRATEGY_ACTIONABILITY: {
        /* Weight = magnitude * actionability * urgency */
        double* weights = (double*)malloc(n * sizeof(double));
        if (!weights) return SNAPKIT_ERR_NULL;
        double total_weight = 0.0;
        for (size_t i = 0; i < n; i++) {
            weights[i] = deltas[i].magnitude * deltas[i].actionability * deltas[i].urgency;
            if (deltas[i].severity == SNAPKIT_SEVERITY_NONE) weights[i] = 0.0;
            total_weight += weights[i];
        }

        if (total_weight <= 0.0) {
            free(weights);
            *n_allocated = 0;
            return SNAPKIT_OK;
        }

        /* Sort indices by weight descending (simple bubble sort) */
        size_t* indices = (size_t*)malloc(n * sizeof(size_t));
        if (!indices) { free(weights); return SNAPKIT_ERR_NULL; }
        for (size_t i = 0; i < n; i++) indices[i] = i;
        for (size_t i = 0; i < n; i++) {
            for (size_t j = i + 1; j < n; j++) {
                if (weights[indices[j]] > weights[indices[i]]) {
                    size_t tmp = indices[i]; indices[i] = indices[j]; indices[j] = tmp;
                }
            }
        }

        double budget_remaining = ab->total_budget;
        for (size_t pi = 0; pi < n; pi++) {
            size_t idx = indices[pi];
            double w = weights[idx];
            if (w <= 0 || budget_remaining <= 0) {
                allocs[allocated_count].delta = deltas[idx];
                allocs[allocated_count].allocated = 0.0;
                allocs[allocated_count].priority = (int)pi + 1;
                set_reason(allocs[allocated_count].reason,
                           sizeof(allocs[allocated_count].reason), "BUDGET_EXHAUSTED");
                allocated_count++;
                continue;
            }
            double prop = (w / total_weight) * ab->total_budget;
            double alloc_amount = (prop < budget_remaining) ? prop : budget_remaining;
            budget_remaining -= alloc_amount;

            allocs[allocated_count].delta = deltas[idx];
            allocs[allocated_count].allocated = alloc_amount;
            allocs[allocated_count].priority = (int)pi + 1;

            /* Build reason string */
            char reason[48];
            reason[0] = '\0';
            if (deltas[idx].actionability > 0.7) {
                snprintf(reason, sizeof(reason), "act=%.2f", deltas[idx].actionability);
            }
            if (deltas[idx].urgency > 0.7) {
                size_t off = strlen(reason);
                snprintf(reason + off, sizeof(reason) - off,
                         "%surg=%.2f", reason[0] ? ";" : "", deltas[idx].urgency);
            }
            if (deltas[idx].magnitude > 3.0 * deltas[idx].tolerance) {
                size_t off = strlen(reason);
                snprintf(reason + off, sizeof(reason) - off,
                         "%sbig=%.1f", reason[0] ? ";" : "", deltas[idx].magnitude);
            }
            if (reason[0] == '\0') {
                snprintf(reason, sizeof(reason), "weighted");
            }
            reason[sizeof(reason) - 1] = '\0';
            set_reason(allocs[allocated_count].reason,
                       sizeof(allocs[allocated_count].reason), reason);
            allocated_count++;
        }

        ab->remaining = budget_remaining;
        free(weights);
        free(indices);
        break;
    }

    case SNAPKIT_STRATEGY_REACTIVE: {
        /* Sort by magnitude descending, allocate greedily */
        size_t* indices = (size_t*)malloc(n * sizeof(size_t));
        if (!indices) return SNAPKIT_ERR_NULL;
        for (size_t i = 0; i < n; i++) indices[i] = i;
        for (size_t i = 0; i < n; i++) {
            for (size_t j = i + 1; j < n; j++) {
                if (deltas[indices[j]].magnitude > deltas[indices[i]].magnitude) {
                    size_t tmp = indices[i]; indices[i] = indices[j]; indices[j] = tmp;
                }
            }
        }

        double budget_remaining = ab->total_budget;
        for (size_t pi = 0; pi < n; pi++) {
            size_t idx = indices[pi];
            if (deltas[idx].severity == SNAPKIT_SEVERITY_NONE || budget_remaining <= 0) {
                allocs[allocated_count].delta = deltas[idx];
                allocs[allocated_count].allocated = 0.0;
                allocs[allocated_count].priority = (int)pi + 1;
                set_reason(allocs[allocated_count].reason,
                           sizeof(allocs[allocated_count].reason), "BUDGET_EXHAUSTED");
                allocated_count++;
                continue;
            }
            double alloc_amount = (deltas[idx].magnitude < budget_remaining) ?
                                   deltas[idx].magnitude : budget_remaining;
            budget_remaining -= alloc_amount;
            allocs[allocated_count].delta = deltas[idx];
            allocs[allocated_count].allocated = alloc_amount;
            allocs[allocated_count].priority = (int)pi + 1;
            set_reason(allocs[allocated_count].reason,
                       sizeof(allocs[allocated_count].reason), "REACTIVE");
            allocated_count++;
        }
        ab->remaining = budget_remaining;
        free(indices);
        break;
    }

    case SNAPKIT_STRATEGY_UNIFORM: {
        size_t actionable = 0;
        for (size_t i = 0; i < n; i++) {
            if (deltas[i].severity != SNAPKIT_SEVERITY_NONE) actionable++;
        }
        if (actionable == 0) { *n_allocated = 0; return SNAPKIT_OK; }
        double per_delta = ab->total_budget / (double)actionable;
        for (size_t i = 0; i < n; i++) {
            if (deltas[i].severity != SNAPKIT_SEVERITY_NONE) {
                allocs[allocated_count].delta = deltas[i];
                allocs[allocated_count].allocated = per_delta;
                allocs[allocated_count].priority = (int)i + 1;
                set_reason(allocs[allocated_count].reason,
                           sizeof(allocs[allocated_count].reason), "UNIFORM");
                allocated_count++;
            }
        }
        ab->remaining = 0.0;
        break;
    }

    default:
        return SNAPKIT_ERR_STATE;
    }

    if (ab->remaining <= 0.0) ab->exhaustion_count++;
    *n_allocated = allocated_count;
    return ab->remaining <= 0.0 ? SNAPKIT_ERR_BUDGET : SNAPKIT_OK;
}

void snapkit_budget_status(const snapkit_attention_budget_t* ab,
                            double* remaining,
                            double* utilization) {
    if (!ab) return;
    if (remaining)    *remaining    = ab->remaining;
    if (utilization)  *utilization  = ab->total_budget > 0.0 ?
                                      1.0 - ab->remaining / ab->total_budget : 0.0;
}

/* ===========================================================================
 * Script Library -- Implementation
 * ========================================================================= */

snapkit_script_library_t* snapkit_script_library_create(double match_threshold) {
    snapkit_script_library_t* lib = (snapkit_script_library_t*)
        calloc(1, sizeof(snapkit_script_library_t));
    if (!lib) return NULL;
    lib->match_threshold = match_threshold;
    lib->num_scripts = 0;
    lib->hit_count = 0;
    lib->miss_count = 0;
    lib->tick = 0;
    return lib;
}

void snapkit_script_library_free(snapkit_script_library_t* lib) {
    free(lib);
}

snapkit_error_t snapkit_script_library_add(snapkit_script_library_t* lib,
                                            const char* id,
                                            const char* name,
                                            const double* trigger,
                                            size_t trigger_dim,
                                            double response) {
    if (!lib || !id || !trigger) return SNAPKIT_ERR_NULL;
    if (lib->num_scripts >= SNAPKIT_MAX_SCRIPTS) return SNAPKIT_ERR_SIZE;
    if (trigger_dim > SNAPKIT_MAX_PATTERN_DIM) return SNAPKIT_ERR_DIM;

    int idx = lib->num_scripts;
    snapkit_script_t* s = &lib->scripts[idx];

    strncpy(s->id, id, SNAPKIT_SCRIPT_ID_MAX - 1);
    s->id[SNAPKIT_SCRIPT_ID_MAX - 1] = '\0';
    strncpy(s->name, name ? name : id, SNAPKIT_SCRIPT_NAME_MAX - 1);
    s->name[SNAPKIT_SCRIPT_NAME_MAX - 1] = '\0';

    memcpy(s->trigger, trigger, trigger_dim * sizeof(double));
    s->trigger_dim = trigger_dim;
    s->response = response;
    s->match_threshold = lib->match_threshold;
    s->status = SNAPKIT_SCRIPT_ACTIVE;
    s->use_count = 0;
    s->success_count = 0;
    s->fail_count = 0;
    s->last_used = 0;
    s->created_at = lib->tick;
    s->confidence = 1.0;

    lib->num_scripts++;
    return SNAPKIT_OK;
}

static snapkit_script_t* find_script_int(snapkit_script_library_t* lib,
                                          const char* script_id) {
    for (int i = 0; i < lib->num_scripts; i++) {
        if (strcmp(lib->scripts[i].id, script_id) == 0)
            return &lib->scripts[i];
    }
    return NULL;
}

snapkit_error_t snapkit_script_library_match(snapkit_script_library_t* lib,
                                              const double* observation,
                                              size_t obs_dim,
                                              snapkit_script_match_t* match) {
    if (!lib || !observation || !match) return SNAPKIT_ERR_NULL;

    lib->tick++;

    double best_confidence = 0.0;
    int best_idx = -1;
    double best_delta = 0.0;

    for (int i = 0; i < lib->num_scripts; i++) {
        snapkit_script_t* s = &lib->scripts[i];
        if (s->status != SNAPKIT_SCRIPT_ACTIVE) continue;
        if (s->trigger_dim != obs_dim) continue;

        double sim = snapkit_cosine_similarity(observation, s->trigger, obs_dim);
        double confidence = (sim + 1.0) / 2.0; /* cos in [-1,1] -> conf in [0,1] */
        double delta = 0.0;
        for (size_t j = 0; j < obs_dim; j++) {
            double d = observation[j] - s->trigger[j];
            delta += d * d;
        }
        delta = sqrt(delta);

        if (confidence > best_confidence) {
            best_confidence = confidence;
            best_idx = i;
            best_delta = delta;
        }
    }

    if (best_idx < 0 || best_confidence < lib->match_threshold) {
        lib->miss_count++;
        match->confidence = best_confidence;
        match->is_match = false;
        match->delta_from_template = best_delta;
        match->script_id[0] = '\0';
        return SNAPKIT_ERR_NULL;
    }

    lib->hit_count++;
    strncpy(match->script_id, lib->scripts[best_idx].id, SNAPKIT_SCRIPT_ID_MAX - 1);
    match->script_id[SNAPKIT_SCRIPT_ID_MAX - 1] = '\0';
    match->confidence = best_confidence;
    match->is_match = true;
    match->delta_from_template = best_delta;
    return SNAPKIT_OK;
}

void snapkit_script_library_record_use(snapkit_script_library_t* lib,
                                        const char* script_id,
                                        bool success) {
    if (!lib || !script_id) return;
    snapkit_script_t* s = find_script_int(lib, script_id);
    if (!s) return;

    s->use_count++;
    s->last_used = lib->tick;
    if (success) s->success_count++;
    else         s->fail_count++;

    if (s->use_count > 0) {
        double success_rate = (double)s->success_count / (double)s->use_count;
        double min_uses = fmin(1.0, (double)s->success_count / 5.0);
        s->confidence = success_rate * min_uses;
        if (s->use_count > 5 && success_rate < 0.5) {
            s->status = SNAPKIT_SCRIPT_DEGRADED;
        }
    }
}

snapkit_error_t snapkit_script_library_forget(snapkit_script_library_t* lib,
                                               const char* script_id) {
    if (!lib || !script_id) return SNAPKIT_ERR_NULL;
    snapkit_script_t* s = find_script_int(lib, script_id);
    if (!s) return SNAPKIT_ERR_NULL;
    s->status = SNAPKIT_SCRIPT_ARCHIVED;
    return SNAPKIT_OK;
}

void snapkit_script_library_statistics(const snapkit_script_library_t* lib,
                                        int* active,
                                        int* total,
                                        double* hit_rate) {
    if (!lib) return;
    if (total) *total = lib->num_scripts;
    int act = 0;
    for (int i = 0; i < lib->num_scripts; i++) {
        if (lib->scripts[i].status == SNAPKIT_SCRIPT_ACTIVE) act++;
    }
    if (active) *active = act;
    if (hit_rate) {
        size_t total_lookups = lib->hit_count + lib->miss_count;
        *hit_rate = total_lookups > 0 ?
                    (double)lib->hit_count / (double)total_lookups : 0.0;
    }
}

/* ===========================================================================
 * Constraint Sheaf -- Implementation
 * ========================================================================= */

snapkit_constraint_sheaf_t* snapkit_sheaf_create(snapkit_topology_t topology,
                                                   double tolerance) {
    snapkit_constraint_sheaf_t* sheaf = (snapkit_constraint_sheaf_t*)
        calloc(1, sizeof(snapkit_constraint_sheaf_t));
    if (!sheaf) return NULL;
    sheaf->topology = topology;
    sheaf->tolerance = tolerance;
    sheaf->num_constraints = 0;
    sheaf->num_dependencies = 0;
    return sheaf;
}

void snapkit_sheaf_free(snapkit_constraint_sheaf_t* sheaf) {
    free(sheaf);
}

snapkit_error_t snapkit_sheaf_add_constraint(snapkit_constraint_sheaf_t* sheaf,
                                              const char* name,
                                              double value,
                                              double expected) {
    if (!sheaf || !name) return SNAPKIT_ERR_NULL;
    if (sheaf->num_constraints >= SNAPKIT_MAX_CONSTRAINTS) return SNAPKIT_ERR_SIZE;

    int idx = sheaf->num_constraints;
    strncpy(sheaf->constraints[idx].name, name, SNAPKIT_CONSTRAINT_NAME_MAX - 1);
    sheaf->constraints[idx].name[SNAPKIT_CONSTRAINT_NAME_MAX - 1] = '\0';
    sheaf->constraints[idx].value = value;

    if (!isnan(expected)) {
        sheaf->constraints[idx].expected = expected;
        sheaf->constraints[idx].has_expected = true;
    } else {
        sheaf->constraints[idx].expected = value;
        sheaf->constraints[idx].has_expected = false;
    }

    sheaf->num_constraints++;
    return SNAPKIT_OK;
}

snapkit_error_t snapkit_sheaf_add_dependency(snapkit_constraint_sheaf_t* sheaf,
                                              const char* source,
                                              const char* target) {
    if (!sheaf || !source || !target) return SNAPKIT_ERR_NULL;
    if (sheaf->num_dependencies >= SNAPKIT_MAX_DEPENDENCIES) return SNAPKIT_ERR_SIZE;

    int idx = sheaf->num_dependencies;
    strncpy(sheaf->dependencies[idx].source, source, SNAPKIT_CONSTRAINT_NAME_MAX - 1);
    sheaf->dependencies[idx].source[SNAPKIT_CONSTRAINT_NAME_MAX - 1] = '\0';
    strncpy(sheaf->dependencies[idx].target, target, SNAPKIT_CONSTRAINT_NAME_MAX - 1);
    sheaf->dependencies[idx].target[SNAPKIT_CONSTRAINT_NAME_MAX - 1] = '\0';

    sheaf->num_dependencies++;
    return SNAPKIT_OK;
}

snapkit_error_t snapkit_sheaf_check(snapkit_constraint_sheaf_t* sheaf,
                                     snapkit_consistency_report_t* report) {
    if (!sheaf || !report) return SNAPKIT_ERR_NULL;

    if (sheaf->num_constraints == 0) {
        report->num_constraints = 0;
        report->max_delta = 0.0;
        report->mean_delta = 0.0;
        report->h1_analog = 0;
        report->delta_detected = false;
        report->tolerance = sheaf->tolerance;
        report->topology = (int)sheaf->topology;
        return SNAPKIT_OK;
    }

    int max_deltas = sheaf->num_constraints + sheaf->num_dependencies;
    double* deltas = (double*)calloc((size_t)max_deltas, sizeof(double));
    if (!deltas) return SNAPKIT_ERR_NULL;
    int num_deltas = 0;

    /* Check individual constraint deltas */
    for (int i = 0; i < sheaf->num_constraints; i++) {
        double d = fabs(sheaf->constraints[i].value - sheaf->constraints[i].expected);
        deltas[num_deltas++] = d;
    }

    /* Check dependency compatibility */
    for (int i = 0; i < sheaf->num_dependencies; i++) {
        const char* src = sheaf->dependencies[i].source;
        const char* tgt = sheaf->dependencies[i].target;

        double s_val = 0.0, t_val = 0.0, s_exp = 0.0, t_exp = 0.0;
        bool found_s = false, found_t = false;

        for (int j = 0; j < sheaf->num_constraints; j++) {
            if (strcmp(sheaf->constraints[j].name, src) == 0) {
                s_val = sheaf->constraints[j].value;
                s_exp = sheaf->constraints[j].expected;
                found_s = true;
            }
            if (strcmp(sheaf->constraints[j].name, tgt) == 0) {
                t_val = sheaf->constraints[j].value;
                t_exp = sheaf->constraints[j].expected;
                found_t = true;
            }
        }

        if (found_s && found_t) {
            double s_delta = s_val - s_exp;
            double t_delta = t_val - t_exp;
            double compat_delta = fabs(s_delta - t_delta);
            deltas[num_deltas++] = compat_delta * 0.5;
        }
    }

    /* Compute statistics */
    double max_d = 0.0, sum_d = 0.0;
    int h1 = 0;
    for (int i = 0; i < num_deltas; i++) {
        if (deltas[i] > max_d) max_d = deltas[i];
        sum_d += deltas[i];
        if (deltas[i] > sheaf->tolerance) h1++;
    }

    report->num_constraints = sheaf->num_constraints;
    report->max_delta = max_d;
    report->mean_delta = num_deltas > 0 ? sum_d / (double)num_deltas : 0.0;
    report->h1_analog = h1;
    report->delta_detected = max_d > sheaf->tolerance;
    report->tolerance = sheaf->tolerance;
    report->topology = (int)sheaf->topology;

    free(deltas);
    return SNAPKIT_OK;
}

snapkit_error_t snapkit_sheaf_update_expected(snapkit_constraint_sheaf_t* sheaf,
                                               const char* name,
                                               double expected) {
    if (!sheaf || !name) return SNAPKIT_ERR_NULL;

    for (int i = 0; i < sheaf->num_constraints; i++) {
        if (strcmp(sheaf->constraints[i].name, name) == 0) {
            sheaf->constraints[i].expected = expected;
            sheaf->constraints[i].has_expected = true;
            return SNAPKIT_OK;
        }
    }
    return SNAPKIT_ERR_NULL;
}
