#include "flux_midi/flux.h"
#include <math.h>
#include <string.h>

void flux_zero(FluxVector* v) {
    memset(v, 0, sizeof(FluxVector));
}

void flux_uniform(FluxVector* v, double sal, double tol) {
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        v->channels[i].salience = sal;
        v->channels[i].tolerance = tol;
    }
}

double flux_distance(const FluxVector* a, const FluxVector* b) {
    double sum = 0.0;
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        double d = a->channels[i].salience - b->channels[i].salience;
        sum += d * d;
    }
    return sqrt(sum);
}

double flux_jaccard(const FluxVector* a, const FluxVector* b, double threshold) {
    int intersection = 0, union_count = 0;
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        int a_active = a->channels[i].salience > threshold;
        int b_active = b->channels[i].salience > threshold;
        if (a_active || b_active) union_count++;
        if (a_active && b_active) intersection++;
    }
    return union_count == 0 ? 1.0 : (double)intersection / union_count;
}

double flux_cosine(const FluxVector* a, const FluxVector* b) {
    double dot = 0.0, norm_a = 0.0, norm_b = 0.0;
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        double sa = a->channels[i].salience;
        double sb = b->channels[i].salience;
        dot += sa * sb;
        norm_a += sa * sa;
        norm_b += sb * sb;
    }
    double denom = sqrt(norm_a) * sqrt(norm_b);
    return denom < 1e-12 ? 0.0 : dot / denom;
}

void flux_blend(const FluxVector* a, const FluxVector* b, double alpha, FluxVector* out) {
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        out->channels[i].salience = alpha * a->channels[i].salience +
                                    (1.0 - alpha) * b->channels[i].salience;
        out->channels[i].tolerance = alpha * a->channels[i].tolerance +
                                     (1.0 - alpha) * b->channels[i].tolerance;
    }
}

void flux_decay(FluxVector* v, double decay) {
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        v->channels[i].salience *= decay;
    }
}

void flux_clamp(FluxVector* v) {
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        if (v->channels[i].salience < 0.0) v->channels[i].salience = 0.0;
        if (v->channels[i].salience > 1.0) v->channels[i].salience = 1.0;
        if (v->channels[i].tolerance < 0.0) v->channels[i].tolerance = 0.0;
        if (v->channels[i].tolerance > 1.0) v->channels[i].tolerance = 1.0;
    }
}

int flux_get(const FluxVector* v, int idx, FluxChannel* out) {
    if (idx < 0 || idx >= FLUX_CHANNELS) return -1;
    *out = v->channels[idx];
    return 0;
}

int flux_set(FluxVector* v, int idx, double salience, double tolerance) {
    if (idx < 0 || idx >= FLUX_CHANNELS) return -1;
    v->channels[idx].salience = salience;
    v->channels[idx].tolerance = tolerance;
    return 0;
}
