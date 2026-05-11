/* test_eisenstein.c — tests for Eisenstein snapping */
#include <stdio.h>
#include <math.h>
#include "snapkit.h"

static int tests_run = 0;
static int tests_pass = 0;

#define ASSERT(cond, msg) do { \
    tests_run++; \
    if (cond) { tests_pass++; } \
    else { printf("  FAIL: %s\n", msg); } \
} while(0)

#define ASSERT_EQ(a, b, msg) ASSERT((a) == (b), msg)
#define ASSERT_FEQ(a, b, eps, msg) ASSERT(fabs((a)-(b)) < (eps), msg)

int main(void) {
    printf("Eisenstein tests\n");

    /* --- Basic properties --- */
    {
        sk_eisenstein e = {3, 1};
        double x = sk_eisenstein_x(e.a, e.b);
        double y = sk_eisenstein_y(e.b);
        ASSERT_FEQ(x, 2.5, 1e-12, "eisenstein_x(3,1) = 2.5");
        ASSERT_FEQ(y, SNAPKIT_HALF_SQRT3, 1e-12, "eisenstein_y(1) = √3/2");
    }

    /* --- Norm squared --- */
    {
        int n2 = sk_eisenstein_norm2(1, 0);
        ASSERT_EQ(n2, 1, "norm(1,0) = 1");
        n2 = sk_eisenstein_norm2(1, 1);
        ASSERT_EQ(n2, 1, "norm(1,1) = 1");  /* 1 - 1 + 1 = 1 */
        n2 = sk_eisenstein_norm2(2, 1);
        ASSERT_EQ(n2, 3, "norm(2,1) = 3");  /* 4 - 2 + 1 = 3 */
    }

    /* --- Snap origin --- */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(0.0, 0.0);
        ASSERT_EQ(e.a, 0, "snap(0,0).a = 0");
        ASSERT_EQ(e.b, 0, "snap(0,0).b = 0");
    }

    /* --- Snap to (1,0) --- */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(1.0, 0.0);
        ASSERT_EQ(e.a, 1, "snap(1,0).a = 1");
        ASSERT_EQ(e.b, 0, "snap(1,0).b = 0");
    }

    /* --- Snap to (0,1) — ω --- */
    {
        double x = sk_eisenstein_x(0, 1);
        double y = sk_eisenstein_y(1);
        sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);
        ASSERT_EQ(e.a, 0, "snap(ω).a = 0");
        ASSERT_EQ(e.b, 1, "snap(ω).b = 1");
    }

    /* --- Covering radius guarantee --- */
    {
        /* The covering radius of the A2 lattice is 1/√3 ≈ 0.5774.
           For any point, the distance to the nearest lattice point must be ≤ 1/√3. */
        double worst = 0.0;
        /* Test on a fine grid around the origin */
        for (double x = -0.5; x <= 0.5; x += 0.05) {
            for (double y = -0.5; y <= 0.5; y += 0.05) {
                sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);
                double cx = sk_eisenstein_x(e.a, e.b);
                double cy = sk_eisenstein_y(e.b);
                double dx = x - cx;
                double dy = y - cy;
                double dist = sqrt(dx*dx + dy*dy);
                if (dist > worst) worst = dist;
            }
        }
        printf("  Worst-case distance in test grid: %.6f (limit: %.6f)\n",
               worst, SNAPKIT_COVERING_RADIUS);
        ASSERT(worst <= SNAPKIT_COVERING_RADIUS + 1e-12,
               "covering radius ≤ 1/√3");
    }

    /* --- Naive vs Voronoi agreement --- */
    {
        double test_points[][2] = {
            {0.3, 0.1}, {-0.7, 0.4}, {1.2, -0.8}, {0.0, 0.3},
            {0.5, 0.5}, {-1.0, -0.5}, {2.3, 1.7}, {-0.1, -0.2}
        };
        int np = sizeof(test_points) / sizeof(test_points[0]);
        for (int i = 0; i < np; i++) {
            sk_eisenstein n = sk_eisenstein_snap_naive(test_points[i][0], test_points[i][1]);
            sk_eisenstein v = sk_eisenstein_snap_voronoi(test_points[i][0], test_points[i][1]);
            /* Both should snap to the same point (they may differ on ties but distance should be equal) */
            double nx = sk_eisenstein_x(n.a, n.b), ny = sk_eisenstein_y(n.b);
            double vx = sk_eisenstein_x(v.a, v.b), vy = sk_eisenstein_y(v.b);
            double dn = sqrt(pow(test_points[i][0]-nx,2) + pow(test_points[i][1]-ny,2));
            double dv = sqrt(pow(test_points[i][0]-vx,2) + pow(test_points[i][1]-vy,2));
            ASSERT(fabs(dn - dv) < 1e-9, "naive and voronoi distances agree");
        }
    }

    /* --- Snap with tolerance --- */
    {
        sk_snap_result r = sk_eisenstein_snap(0.01, 0.01, 0.5);
        ASSERT(r.is_snap, "small offset is a snap");
        ASSERT_FEQ(r.distance, sqrt(0.01*0.01 + 0.01*0.01), 1e-6,
                   "distance ≈ 0.014");

        r = sk_eisenstein_snap(1.0, 0.0, 0.01);
        ASSERT(r.is_snap, "exact lattice point is a snap");
        ASSERT_FEQ(r.distance, 0.0, 1e-12, "distance = 0 at lattice point");
    }

    /* --- Batch --- */
    {
        double x[] = {0.0, 1.0, 0.5, -0.3};
        double y[] = {0.0, 0.0, 0.3, 0.4};
        sk_eisenstein out[4];
        sk_eisenstein_snap_batch(x, y, 4, out);
        ASSERT_EQ(out[0].a, 0, "batch[0].a");
        ASSERT_EQ(out[0].b, 0, "batch[0].b");
        ASSERT_EQ(out[1].a, 1, "batch[1].a");
        ASSERT_EQ(out[1].b, 0, "batch[1].b");
    }

    /* --- Eisenstein distance --- */
    {
        double d = sk_eisenstein_distance(0.0, 0.0, 1.0, 0.0);
        ASSERT_FEQ(d, 1.0, 1e-9, "distance(0,0 → 1,0) = 1");
    }

    printf("  %d/%d passed\n", tests_pass, tests_run);
    return (tests_pass == tests_run) ? 0 : 1;
}
