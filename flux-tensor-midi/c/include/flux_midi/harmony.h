#ifndef FLUX_MIDI_HARMONY_H
#define FLUX_MIDI_HARMONY_H

#ifdef __cplusplus
extern "C" {
#endif

#include "flux.h"

/*
 * Harmony — measures of alignment between RoomMusicians.
 *
 * Three layers:
 *   1. Jaccard similarity — which FLUX channels are co-active
 *   2. Connectome — structural alignment of listening graphs
 *   3. Spectrum — frequency-domain harmonic analysis of event streams
 */

typedef struct {
    double jaccard;        /* Channel overlap similarity [0..1] */
    double cosine;         /* Weighted cosine similarity [0..1] */
    double euclidean;      /* Euclidean distance [0..∞] */
    double combined;       /* Weighted combination [0..1] */
} HarmonyScore;

/* Compute harmony between two flux vectors */
HarmonyScore harmony_compute(const FluxVector* a, const FluxVector* b,
                             double jaccard_weight, double cosine_weight,
                             double euclidean_weight);

/* Quick Jaccard check — are these rooms "in tune"? */
int harmony_in_tune(const FluxVector* a, const FluxVector* b, double threshold);

/* Connectome alignment: fraction of shared listeners between two rooms.
 * Returns [0..1] where 1.0 = identical listening sets. */
double connectome_alignment(const char** listen_a, int n_a,
                            const char** listen_b, int n_b);

/* Spectrum analysis: compute harmonic ratio from an array of event intervals.
 * intervals: array of N inter-onset intervals
 * Returns harmonic ratio [0..1] where 1.0 = perfectly harmonic. */
double spectrum_harmonic_ratio(const double* intervals, int n);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_HARMONY_H */
