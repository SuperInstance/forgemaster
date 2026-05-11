/**
 * @file core_ade.c
 * @brief ADE topology data, Eisenstein snap (NEON SIMD), vector math.
 */

#include "snapkit/snapkit_internal.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>

/* ===========================================================================
 * ADE Topology Data
 * ========================================================================= */

static const snapkit_ade_data_t ade_table[SNAPKIT_TOPOLOGY_COUNT] = {
    {SNAPKIT_TOPOLOGY_BINARY,      "A₁", 1, 2, 2,   2, NULL,                "Binary \xe2\x80\x94 coin flip",       1.0},
    {SNAPKIT_TOPOLOGY_TETRAHEDRAL, "A₃", 3, 4, 12,  4, "Tetrahedron",       "4 categories",             2.0},
    {SNAPKIT_TOPOLOGY_HEXAGONAL,   "A₂", 2, 3, 6,   3, NULL,                "Hexagonal \xe2\x80\x94 Eisenstein \xe2\x84\xa4[\xcf\x89]", 2.7},
    {SNAPKIT_TOPOLOGY_CUBIC,       "Zn", 0, 0, 0,   0, "Cube",              "Standard uniform grid",    1.5},
    {SNAPKIT_TOPOLOGY_OCTAHEDRAL,  "B\xe2\x82\x83", 3, 3, 18,  6, "Octahedron",        "8 directions, \xc2\xb1axes",      2.8},
    {SNAPKIT_TOPOLOGY_DODECAHEDRAL,"H\xe2\x82\x83", 3, 3, 30, 10, "Dodecahedron",      "20-category combinatorial",2.5},
    {SNAPKIT_TOPOLOGY_ICOSAHEDRAL, "H\xe2\x82\x83", 3, 3, 30, 10, "Icosahedron",       "12-direction golden clusters", 2.9},
    {SNAPKIT_TOPOLOGY_GRADIENT,    "∞",  0, 0, 0,   0, NULL,                "Near-continuous (d100)",   0.5}
};

const snapkit_ade_data_t* snapkit_ade_data(snapkit_topology_t type) {
    if (type < 0 || type >= SNAPKIT_TOPOLOGY_COUNT) return NULL;
    return &ade_table[type];
}

snapkit_topology_t snapkit_recommend_topology(int num_categories, int dimension) {
    if (num_categories == 2) return SNAPKIT_TOPOLOGY_BINARY;
    if (num_categories == 4 || num_categories == 3) return SNAPKIT_TOPOLOGY_TETRAHEDRAL;
    if (dimension <= 2 || num_categories == 6) return SNAPKIT_TOPOLOGY_HEXAGONAL;
    if (dimension <= 4 || num_categories <= 20) return SNAPKIT_TOPOLOGY_DODECAHEDRAL;
    return SNAPKIT_TOPOLOGY_OCTAHEDRAL;
}

const char* snapkit_topology_name(snapkit_topology_t t) {
    const snapkit_ade_data_t* d = snapkit_ade_data(t);
    return d ? d->name : "UNKNOWN";
}

const char* snapkit_severity_name(snapkit_severity_t s) {
    static const char* names[] = {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"};
    if (s < 0 || s >= SNAPKIT_SEVERITY_COUNT) return "UNKNOWN";
    return names[s];
}

snapkit_severity_t snapkit_compute_severity(double magnitude, double tolerance) {
    if (tolerance <= 0.0) return SNAPKIT_SEVERITY_CRITICAL;
    double ratio = magnitude / tolerance;
    if (ratio <= 1.0)  return SNAPKIT_SEVERITY_NONE;
    if (ratio <= 1.5)  return SNAPKIT_SEVERITY_LOW;
    if (ratio <= 3.0)  return SNAPKIT_SEVERITY_MEDIUM;
    if (ratio <= 5.0)  return SNAPKIT_SEVERITY_HIGH;
    return SNAPKIT_SEVERITY_CRITICAL;
}

/* ===========================================================================
 * Vector math helpers
 * ========================================================================= */

double snapkit_l2_norm(const double* v, size_t n) {
    double sum = 0.0;
    for (size_t i = 0; i < n; i++) sum += v[i] * v[i];
    return sqrt(sum);
}

double snapkit_cosine_similarity(const double* a, const double* b, size_t n) {
    double dot = 0.0, na = 0.0, nb = 0.0;
    for (size_t i = 0; i < n; i++) {
        dot += a[i] * b[i];
        na  += a[i] * a[i];
        nb  += b[i] * b[i];
    }
    double norm = sqrt(na) * sqrt(nb);
    if (norm < 1e-15) return 0.0;
    return dot / norm;
}
