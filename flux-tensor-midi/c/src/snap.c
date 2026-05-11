#include "flux_midi/snap.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void eisenstein_snap(double interval_a, double interval_b,
                     double base_tempo, SnapResult* result) {
    /* Normalize by base tempo */
    double a = interval_a / base_tempo;
    double b = interval_b / base_tempo;

    /* Eisenstein coordinates: (a + b/√3, 2b/√3) */
    const double sqrt3 = 1.7320508075688772;
    double af = a + b / sqrt3;
    double bf = 2.0 * b / sqrt3;

    /* Round to nearest lattice point */
    result->eisenstein_a = (int)round(af);
    result->eisenstein_b = (int)round(bf);

    /* Eisenstein norm: a² - ab + b² */
    int ea = result->eisenstein_a;
    int eb = result->eisenstein_b;
    result->norm = (double)(ea * ea - ea * eb + eb * eb);

    /* Angle and ratio for classification */
    result->ratio = (a > 1e-10) ? b / a : 999.0;
    result->angle_deg = atan2(b, a) * 180.0 / M_PI;

    /* Classify by ratio b/a */
    double r = result->ratio;
    if (r < 0.3)       result->shape = SNAP_COLLAPSE;
    else if (r < 0.7)  result->shape = SNAP_DECEL;
    else if (r < 1.5)  result->shape = SNAP_STEADY;
    else if (r < 3.0)  result->shape = SNAP_ACCEL;
    else                result->shape = SNAP_BURST;
}

const char* snap_shape_name(SnapShape s) {
    switch (s) {
        case SNAP_BURST:    return "burst";
        case SNAP_STEADY:   return "steady";
        case SNAP_COLLAPSE: return "collapse";
        case SNAP_ACCEL:    return "accel";
        case SNAP_DECEL:    return "decel";
        default:            return "unknown";
    }
}

double snap_to_grid(double interval, double grid_unit, int* subdivisions) {
    double raw = interval / grid_unit;
    int subs = (int)round(raw);
    if (subs < 1) subs = 1;
    if (subdivisions) *subdivisions = subs;
    return subs * grid_unit;
}
