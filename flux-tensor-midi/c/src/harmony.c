#include "flux_midi/harmony.h"
#include <math.h>
#include <string.h>

HarmonyScore harmony_compute(const FluxVector* a, const FluxVector* b,
                             double jaccard_weight, double cosine_weight,
                             double euclidean_weight) {
    HarmonyScore score;
    score.jaccard = flux_jaccard(a, b, 0.5);
    score.cosine = flux_cosine(a, b);

    double dist = flux_distance(a, b);
    /* Normalize: max distance for 9 channels is sqrt(9) = 3.0 */
    score.euclidean = 1.0 - (dist / 3.0);
    if (score.euclidean < 0.0) score.euclidean = 0.0;

    double total_weight = jaccard_weight + cosine_weight + euclidean_weight;
    if (total_weight < 1e-12) total_weight = 1.0;

    score.combined = (jaccard_weight * score.jaccard +
                      cosine_weight * score.cosine +
                      euclidean_weight * score.euclidean) / total_weight;
    return score;
}

int harmony_in_tune(const FluxVector* a, const FluxVector* b, double threshold) {
    HarmonyScore s = harmony_compute(a, b, 1.0, 1.0, 0.5);
    return s.combined >= threshold;
}

double connectome_alignment(const char** listen_a, int n_a,
                            const char** listen_b, int n_b) {
    if (n_a == 0 && n_b == 0) return 1.0;
    if (n_a == 0 || n_b == 0) return 0.0;

    int shared = 0;
    for (int i = 0; i < n_a; i++) {
        for (int j = 0; j < n_b; j++) {
            if (strcmp(listen_a[i], listen_b[j]) == 0) {
                shared++;
                break;
            }
        }
    }

    /* Jaccard: |A ∩ B| / |A ∪ B| */
    int union_size = n_a + n_b - shared;
    return union_size == 0 ? 1.0 : (double)shared / union_size;
}

double spectrum_harmonic_ratio(const double* intervals, int n) {
    if (n < 2) return 1.0;

    /* Simple harmonic ratio: how close are consecutive interval ratios to
     * simple integer ratios. We check each pair against {1:1, 1:2, 2:1, 1:3, 3:1}. */
    static const double simple_ratios[] = {1.0, 0.5, 2.0, 1.0/3.0, 3.0};
    static const int n_ratios = 5;
    static const double tolerance = 0.15; /* 15% tolerance */

    int harmonic_count = 0;
    for (int i = 0; i < n - 1; i++) {
        if (intervals[i] < 1e-10) continue;
        double ratio = intervals[i + 1] / intervals[i];
        for (int r = 0; r < n_ratios; r++) {
            if (fabs(ratio - simple_ratios[r]) / simple_ratios[r] < tolerance) {
                harmonic_count++;
                break;
            }
        }
    }

    return (double)harmonic_count / (n - 1);
}
