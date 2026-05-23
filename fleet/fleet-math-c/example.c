/**
 * example.c — Usage example for fleet_math.h
 *
 * Compile:
 *   gcc -O3 -march=native -lm -D FLEET_MATH_IMPLEMENTATION \
 *       -o example example.c
 *
 *   (or: make example)
 */

#define FLEET_MATH_IMPLEMENTATION
#include "include/fleet_math.h"
#include <stdio.h>

int main(void) {
    printf("=== fleet-math-c Example ===\n\n");

    /* 1. Snap a point to the A₂ Eisenstein lattice */
    printf("1. Eisenstein Snap\n");
    double px = 1.5, py = 2.3;
    fm_snap_result_t snap;
    fm_eins_snap(px, py, &snap);
    printf("   Point (%.2f, %.2f) → (%ld, %ld) error=%.6f\n",
           px, py, (long)snap.coords.a, (long)snap.coords.b, snap.error);

    /* Cartesian output */
    double sx, sy;
    fm_eins_snap_cartesian(px, py, &sx, &sy);
    printf("   Snapped Cartesian: (%.6f, %.6f)\n", sx, sy);

    /* 2. Dodecet code */
    printf("\n2. Dodecet Encoding\n");
    uint16_t code = fm_dodecet_code(snap.coords.a, snap.coords.b);
    printf("   dodecet(%ld,%ld) = %u (0x%03x)\n",
           (long)snap.coords.a, (long)snap.coords.b, code, code);

    /* 3. LUT-based constraint checking */
    printf("\n3. Dodecet LUT\n");
    fm_dodecet_lut_t *lut = fm_lut_create();
    fm_lut_insert(lut, 3, 5);
    fm_lut_insert(lut, snap.coords.a, snap.coords.b);
    printf("   (3,5) in LUT: %s\n", fm_lut_query(lut, 3, 5) ? "yes" : "no");
    printf("   (1,1) in LUT: %s\n", fm_lut_query(lut, 1, 1) ? "yes" : "no");
    fm_lut_destroy(lut);

    /* 4. 3-tier constraint database */
    printf("\n4. 3-Tier Constraint DB\n");
    fm_constraint_db_t *db = fm_db_create(100);
    fm_db_insert(db, 3, 5);
    fm_db_insert(db, 7, -2);
    printf("   query(3,5):  %s\n", fm_db_query(db, 3, 5)  ? "found" : "not found");
    printf("   query(1,1):  %s\n", fm_db_query(db, 1, 1)  ? "found" : "not found");
    fm_db_free(db);

    /* 5. Cyclotomic rotation */
    printf("\n5. ζ₁₅ Rotation\n");
    double rx, ry;
    fm_zeta15_rotate(1.0, 0.0, 3, &rx, &ry);
    printf("   ζ₁₅³ · (1,0) = (%.6f, %.6f)\n", rx, ry);
    printf("   Expected:    ≈ (%.6f, %.6f)\n",
           cos(6.0 * M_PI / 15.0), sin(6.0 * M_PI / 15.0));

    /* 6. Bounded drift */
    printf("\n6. Bounded Drift\n");
    double bound_open = fm_drift_bound_open(10, 1e-15);
    double bound_closed = fm_drift_bound_closed(10, 1e-15);
    printf("   Open walk bound (n=10):   %.15f\n", bound_open);
    printf("   Closed cycle bound (n=10): %.15f (tighter)\n", bound_closed);

    /* 7. Galois trace */
    printf("\n7. Galois Connection\n");
    printf("   trace(1.0)  = %.6f (expected 8/15 ≈ %.6f)\n",
           fm_galois_trace(1.0, 0.0), 8.0/15.0);
    printf("   trace(0.0)  = %.6f\n", fm_galois_trace(0.0, 0.0));
    printf("   trace(-0.5) = %.6f (clamped)\n", fm_galois_trace(-0.5, 0.0));

    printf("\n=== All examples complete ===\n");
    return 0;
}
