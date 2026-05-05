// constraint_checker.rs — Rust FFI bindings for Fortran constraint checking
//
// Usage: Build the Fortran library first:
//   gfortran -O3 -march=znver5 -ffast-math -c constraint_checker.f90
//   ar rcs libconstraint_checker.a constraint_checker.o
//
// Then link in Cargo.toml:
//   [build-dependencies]
//   cc = "1.0"

use std::os::raw::{c_double, c_int, c_bool};

extern "C" {
    fn check_range_f64(values: *const c_double, n: c_int, lo: c_double, hi: c_double, mask: *mut c_bool);
    fn count_in_range_f64(values: *const c_double, n: c_int, lo: c_double, hi: c_double) -> c_int;
    fn check_bitmask_i64(domains: *const i64, n: c_int, mask_bits: i64, result: *mut i64);
    fn check_multi_f64(values: *const c_double, n: c_int, lo: *const c_double, hi: *const c_double, m: c_int, result: *mut c_bool);
}

/// Check if each value falls within [lo, hi]. Returns a boolean mask.
pub fn check_range(values: &[f64], lo: f64, hi: f64) -> Vec<bool> {
    let n = values.len() as c_int;
    let mut mask = vec![false as c_bool; values.len()];
    unsafe {
        check_range_f64(values.as_ptr(), n, lo, hi, mask.as_mut_ptr());
    }
    mask.iter().map(|&b| b != 0).collect()
}

/// Count values in range [lo, hi] without allocating a mask.
pub fn count_in_range(values: &[f64], lo: f64, hi: f64) -> usize {
    let n = values.len() as c_int;
    let count = unsafe {
        count_in_range_f64(values.as_ptr(), n, lo, hi)
    };
    count as usize
}

/// Bitmask AND: result[i] = domains[i] & mask_bits
pub fn check_bitmask(domains: &[i64], mask_bits: i64) -> Vec<i64> {
    let n = domains.len() as c_int;
    let mut result = vec![0i64; domains.len()];
    unsafe {
        check_bitmask_i64(domains.as_ptr(), n, mask_bits, result.as_mut_ptr());
    }
    result
}

/// Multi-constraint AND: check values against multiple [lo, hi] ranges.
/// Returns mask where result[i] = true iff ALL constraints are satisfied for values[i].
pub fn check_multi(values: &[f64], lo: &[f64], hi: &[f64]) -> Vec<bool> {
    assert_eq!(lo.len(), hi.len());
    let n = values.len() as c_int;
    let m = lo.len() as c_int;
    let mut result = vec![false as c_bool; values.len()];
    unsafe {
        check_multi_f64(
            values.as_ptr(), n,
            lo.as_ptr(), hi.as_ptr(), m,
            result.as_mut_ptr(),
        );
    }
    result.iter().map(|&b| b != 0).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_range_check() {
        let values = vec![0.0, 0.5, 1.0, 1.5, 2.0];
        let mask = check_range(&values, 0.5, 1.5);
        assert_eq!(mask, vec![false, true, true, true, false]);
    }

    #[test]
    fn test_count_in_range() {
        let values: Vec<f64> = (0..100).map(|i| i as f64 / 100.0).collect();
        let count = count_in_range(&values, 0.1, 0.9);
        assert_eq!(count, 81); // 0.10 through 0.90 inclusive
    }

    #[test]
    fn test_bitmask() {
        let domains = vec![0xFF, 0x0F, 0xF0, 0x55];
        let result = check_bitmask(&domains, 0x0F);
        assert_eq!(result, vec![0x0F, 0x0F, 0x00, 0x05]);
    }
}
