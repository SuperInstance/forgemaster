/* constraint_checker.h — C header for Fortran constraint checking library
 * 
 * Usage:
 *   #include "constraint_checker.h"
 *   // Compile: gcc -o main main.c constraint_checker.o -lgfortran -lm
 */

#ifndef CONSTRAINT_CHECKER_H
#define CONSTRAINT_CHECKER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Range check: values[i] in [lo, hi] for i in [0, n-1]
 * mask[i] = true if values[i] is in range */
void check_range_f64(const double *values, int n, double lo, double hi, bool *mask);

/* Count values in range — returns count without allocating mask */
int count_in_range_f64(const double *values, int n, double lo, double hi);

/* Bitmask domain operation: result[i] = domains[i] & mask_bits */
void check_bitmask_i64(const int64_t *domains, int n, int64_t mask_bits, int64_t *result);

/* Multi-constraint AND check
 * n values, m constraints
 * lo[j], hi[j] define constraint j
 * result[i] = AND over all j: lo[j] <= values[i] <= hi[j] */
void check_multi_f64(const double *values, int n,
                     const double *lo, const double *hi, int m,
                     bool *result);

#ifdef __cplusplus
}
#endif

#endif /* CONSTRAINT_CHECKER_H */
