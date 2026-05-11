#ifndef FLUX_MIDI_FLUX_H
#define FLUX_MIDI_FLUX_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * FLUX Vector — 9-channel intent representation.
 *
 * Each channel carries (salience, tolerance):
 *   salience  — how strongly this intent is held [0..1]
 *   tolerance — how much deviation is acceptable [0..1]
 *
 * Channels (by convention):
 *   0 — Arousal        (energy, activation)
 *   1 — Valence        (positive/negative feeling)
 *   2 — Dominance      (control vs submission)
 *   3 — Uncertainty    (epistemic doubt)
 *   4 — Novelty        (surprise, newness)
 *   5 — Relevance      (importance to current goal)
 *   6 — Competence     (self-efficacy estimate)
 *   7 — Affiliation    (social bonding drive)
 *   8 — Urgency        (time pressure)
 */

#define FLUX_CHANNELS 9

typedef struct {
    double salience;
    double tolerance;
} FluxChannel;

typedef struct {
    FluxChannel channels[FLUX_CHANNELS];
} FluxVector;

/* Initialize a zero flux vector */
void flux_zero(FluxVector* v);

/* Initialize a uniform flux vector (all channels = sal, tol) */
void flux_uniform(FluxVector* v, double sal, double tol);

/* Euclidean distance between two flux vectors (salience only) */
double flux_distance(const FluxVector* a, const FluxVector* b);

/* Jaccard-like similarity: |intersection| / |union| based on active channels.
 * A channel is "active" if salience > threshold. */
double flux_jaccard(const FluxVector* a, const FluxVector* b, double threshold);

/* Weighted cosine similarity across all 9 channels */
double flux_cosine(const FluxVector* a, const FluxVector* b);

/* Blend two flux vectors: out = alpha * a + (1-alpha) * b */
void flux_blend(const FluxVector* a, const FluxVector* b, double alpha, FluxVector* out);

/* Decay all channels by factor (multiply salience by decay) */
void flux_decay(FluxVector* v, double decay);

/* Clamp all salience values to [0, 1] */
void flux_clamp(FluxVector* v);

/* Get/set a single channel by index (0-8). Returns 0 on success, -1 on bad index. */
int flux_get(const FluxVector* v, int idx, FluxChannel* out);
int flux_set(FluxVector* v, int idx, double salience, double tolerance);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_FLUX_H */
