/*
 * Validate snapkit-c implementation against the test corpus.
 * Build: gcc validate_c.c -lm -o validate_c && ./validate_c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>

#define SQRT3 1.7320508075688772
#define COVERING_RADIUS (1.0 / SQRT3)
#define MAX_CASES 1024

typedef struct {
    int id;
    double x, y;
    int exp_a, exp_b;
    double snap_error;
    double snap_error_max;
} TestCase;

double snap_error(double x, double y, int a, int b) {
    double lx = (double)a - (double)b / 2.0;
    double ly = (double)b * SQRT3 / 2.0;
    return sqrt((x - lx) * (x - lx) + (y - ly) * (y - ly));
}

void eisenstein_snap(double x, double y, int *out_a, int *out_b) {
    double b_float = 2.0 * y / SQRT3;
    double a_float = x + y / SQRT3;

    int a_lo = (int)floor(a_float);
    int b_lo = (int)floor(b_float);

    int best_a = 0, best_b = 0;
    double best_err = DBL_MAX;

    /* Check 4 floor/ceil candidates */
    for (int da = 0; da <= 1; da++) {
        for (int db = 0; db <= 1; db++) {
            int ca = a_lo + da;
            int cb = b_lo + db;
            double err = snap_error(x, y, ca, cb);
            if (err < best_err - 1e-15) {
                best_a = ca; best_b = cb; best_err = err;
            } else if (fabs(err - best_err) < 1e-15) {
                if (ca < best_a || (ca == best_a && cb < best_b)) {
                    best_a = ca; best_b = cb;
                }
            }
        }
    }

    /* Check ±1 neighborhood */
    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            int ca = best_a + da;
            int cb = best_b + db;
            double err = snap_error(x, y, ca, cb);
            if (err < best_err - 1e-15) {
                best_a = ca; best_b = cb; best_err = err;
            } else if (fabs(err - best_err) < 1e-15) {
                if (ca < best_a || (ca == best_a && cb < best_b)) {
                    best_a = ca; best_b = cb;
                }
            }
        }
    }

    *out_a = best_a;
    *out_b = best_b;
}

/* Minimal JSON parser for corpus format */
int parse_corpus(const char *filename, TestCase *cases, int max_cases) {
    FILE *f = fopen(filename, "r");
    if (!f) { fprintf(stderr, "Cannot open %s\n", filename); return -1; }

    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *data = malloc(fsize + 1);
    fread(data, 1, fsize, f);
    data[fsize] = 0;
    fclose(f);

    int count = 0;
    char *p = data;

    while (count < max_cases) {
        /* Find next "id" */
        char *id_pos = strstr(p, "\"id\":");
        if (!id_pos) break;

        TestCase *tc = &cases[count];

        /* Parse id */
        id_pos += 5;
        tc->id = atoi(id_pos);

        /* Parse x */
        char *x_pos = strstr(id_pos, "\"x\":");
        if (!x_pos) break;
        x_pos += 4;
        tc->x = strtod(x_pos, NULL);

        /* Parse y */
        char *y_pos = strstr(x_pos, "\"y\":");
        if (!y_pos) break;
        y_pos += 4;
        tc->y = strtod(y_pos, NULL);

        /* Parse expected a */
        char *a_pos = strstr(y_pos, "\"a\":");
        if (!a_pos) break;
        /* Skip to the "a" in expected */
        char *exp_pos = strstr(y_pos, "\"expected\"");
        if (!exp_pos) break;
        a_pos = strstr(exp_pos, "\"a\":");
        if (!a_pos) break;
        a_pos += 4;
        tc->exp_a = atoi(a_pos);

        /* Parse expected b */
        char *b_pos = strstr(a_pos, "\"b\":");
        if (!b_pos) break;
        b_pos += 4;
        tc->exp_b = atoi(b_pos);

        /* Parse snap_error */
        char *se_pos = strstr(b_pos, "\"snap_error\":");
        if (!se_pos) break;
        se_pos += 13;
        tc->snap_error = strtod(se_pos, NULL);

        /* Parse snap_error_max */
        char *sem_pos = strstr(se_pos, "\"snap_error_max\":");
        if (!sem_pos) break;
        sem_pos += 17;
        tc->snap_error_max = strtod(sem_pos, NULL);

        p = sem_pos;
        count++;
    }

    free(data);
    return count;
}

int main(void) {
    TestCase cases[MAX_CASES];
    int n = parse_corpus("corpus/snap_corpus.json", cases, MAX_CASES);

    if (n <= 0) {
        fprintf(stderr, "ERROR: No cases parsed from corpus\n");
        return 1;
    }

    int passed = 0, failed = 0;
    int error_count = 0;

    for (int i = 0; i < n; i++) {
        int a, b;
        eisenstein_snap(cases[i].x, cases[i].y, &a, &b);
        double err = snap_error(cases[i].x, cases[i].y, a, b);

        int ok = 1;
        if (a != cases[i].exp_a) {
            if (error_count < 20) printf("Case %d: a=%d, expected=%d\n", cases[i].id, a, cases[i].exp_a);
            ok = 0; error_count++;
        }
        if (b != cases[i].exp_b) {
            if (error_count < 20) printf("Case %d: b=%d, expected=%d\n", cases[i].id, b, cases[i].exp_b);
            ok = 0; error_count++;
        }
        if (err > cases[i].snap_error_max + 1e-10) {
            if (error_count < 20) printf("Case %d: snap_error=%.10f > max=%.10f\n", cases[i].id, err, cases[i].snap_error_max);
            ok = 0; error_count++;
        }

        if (ok) passed++; else failed++;
    }

    printf("Results: %d/%d passed, %d failed\n", passed, n, failed);

    if (failed > 0) return 1;
    printf("All cases passed ✓\n");
    return 0;
}
