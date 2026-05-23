//! Rust FFI bindings for the fleet-math-c Eisenstein bridge.
//!
//! Wraps the C implementation of Eisenstein A₂ lattice snapping and holonomy checks.

use std::fmt;

pub mod ffi {
    use std::os::raw::c_float;

    #[repr(C, packed)]
    #[derive(Clone, Copy, Debug)]
    pub struct EisensteinResult {
        pub error: c_float,
        pub dodecet: u16,
        pub chamber: u8,
        pub flags: u8,
        pub snap_a: i32,
        pub snap_b: i32,
    }

    const _: () = assert!(size_of::<EisensteinResult>() == 16);

    pub const FLAG_SAFE: u8 = 0x01;
    pub const FLAG_PARITY: u8 = 0x02;

    extern "C" {
        pub fn eisenstein_snap(x: c_float, y: c_float) -> EisensteinResult;
        pub fn eisenstein_batch_snap(
            points: *const c_float,
            n: usize,
            results: *mut EisensteinResult,
        );
        pub fn eisenstein_holonomy_4cycle(results: *const EisensteinResult) -> c_float;
        pub fn eisenstein_batch_holonomy(
            results: *const EisensteinResult,
            n: usize,
            holonomy: *mut c_float,
        );
    }
}

/// A safe wrapper around an Eisenstein snap result.
#[derive(Clone, Copy, Debug)]
pub struct SnapResult {
    /// Distance from original point to snapped lattice point.
    pub error: f32,
    /// 12-bit constraint state (nibble-packed).
    pub dodecet: u16,
    /// Weyl chamber index (0-5).
    pub chamber: u8,
    /// Whether this snap is considered safe.
    pub is_safe: bool,
    /// Parity flag.
    pub parity: bool,
    /// Eisenstein a-coordinate of the snapped lattice point.
    pub snap_a: i32,
    /// Eisenstein b-coordinate of the snapped lattice point.
    pub snap_b: i32,
}

impl SnapResult {
    pub fn from_ffi(r: ffi::EisensteinResult) -> Self {
        // Use addr_of! to avoid creating references to packed fields (UB in Rust 1.95+)
        #[allow(unused_unsafe)]
        unsafe {
            let error = std::ptr::read_unaligned(std::ptr::addr_of!(r.error));
            let dodecet = std::ptr::read_unaligned(std::ptr::addr_of!(r.dodecet));
            let chamber = std::ptr::read_unaligned(std::ptr::addr_of!(r.chamber));
            let flags = std::ptr::read_unaligned(std::ptr::addr_of!(r.flags));
            let snap_a = std::ptr::read_unaligned(std::ptr::addr_of!(r.snap_a));
            let snap_b = std::ptr::read_unaligned(std::ptr::addr_of!(r.snap_b));
            Self {
                error,
                dodecet,
                chamber,
                is_safe: (flags & ffi::FLAG_SAFE) != 0,
                parity: (flags & ffi::FLAG_PARITY) != 0,
                snap_a,
                snap_b,
            }
        }
    }
}

impl fmt::Display for SnapResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Use addr_of! to avoid creating references to packed fields
        #[allow(unused_unsafe)]
        let e = unsafe { std::ptr::read_unaligned(std::ptr::addr_of!(self.error)) };
        let d = unsafe { std::ptr::read_unaligned(std::ptr::addr_of!(self.dodecet)) };
        let c = unsafe { std::ptr::read_unaligned(std::ptr::addr_of!(self.chamber)) };
        let s = self.is_safe;  // bool, Copy
        let p = self.parity;    // bool, Copy
        let sa = unsafe { std::ptr::read_unaligned(std::ptr::addr_of!(self.snap_a)) };
        let sb = unsafe { std::ptr::read_unaligned(std::ptr::addr_of!(self.snap_b)) };
        write!(
            f,
            "SnapResult {{ error: {:.6}, dodecet: 0x{:04x}, chamber: {}, safe: {}, parity: {}, snap:({}, {}) }}",
            e, d, c, s, p, sa, sb
        )
    }
}

/// Snap a single point (x, y) to the nearest Eisenstein A₂ lattice point.
pub fn snap(x: f32, y: f32) -> SnapResult {
    unsafe { SnapResult::from_ffi(ffi::eisenstein_snap(x, y)) }
}

/// Snap multiple points to the nearest Eisenstein lattice points.
///
/// `points` is interleaved (x0, y0, x1, y1, ...).
pub fn batch_snap(points: &[f32]) -> Vec<SnapResult> {
    assert!(points.len() % 2 == 0, "points must have even length (x,y pairs)");
    let n = points.len() / 2;
    let mut results: Vec<ffi::EisensteinResult> = vec![unsafe { std::mem::zeroed() }; n];
    unsafe {
        ffi::eisenstein_batch_snap(points.as_ptr(), n, results.as_mut_ptr());
    }
    results.into_iter().map(SnapResult::from_ffi).collect()
}

/// Compute holonomy for a 4-cycle (4 consecutive snap results).
///
/// Returns |H| in [0, 1]. Closer to 0 = more consistent.
pub fn holonomy_4cycle(results: &[SnapResult; 4]) -> f32 {
    let ffi_results: [ffi::EisensteinResult; 4] = [
        to_ffi(&results[0]),
        to_ffi(&results[1]),
        to_ffi(&results[2]),
        to_ffi(&results[3]),
    ];
    unsafe { ffi::eisenstein_holonomy_4cycle(ffi_results.as_ptr()) }
}

/// Compute holonomy for multiple 4-cycles in batch.
///
/// `results` has 4*n entries (4 consecutive per cycle).
pub fn batch_holonomy(results: &[SnapResult]) -> Vec<f32> {
    assert!(results.len() % 4 == 0, "results must be multiple of 4");
    let n = results.len() / 4;
    let ffi_results: Vec<ffi::EisensteinResult> = results.iter().map(|r| to_ffi(r)).collect();
    let mut holonomy = vec![0.0f32; n];
    unsafe {
        ffi::eisenstein_batch_holonomy(ffi_results.as_ptr(), n, holonomy.as_mut_ptr());
    }
    holonomy
}

fn to_ffi(r: &SnapResult) -> ffi::EisensteinResult {
    let mut flags = 0u8;
    if r.is_safe { flags |= ffi::FLAG_SAFE; }
    if r.parity { flags |= ffi::FLAG_PARITY; }
    // Copy values to locals before constructing the packed result
    let e = r.error;
    let d = r.dodecet;
    let c = r.chamber;
    let sa = r.snap_a;
    let sb = r.snap_b;
    ffi::EisensteinResult {
        error: e,
        dodecet: d,
        chamber: c,
        flags,
        snap_a: sa,
        snap_b: sb,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_snap_origin() {
        let r = snap(0.0, 0.0);
        assert!(r.error < 0.001, "Origin should snap to itself: error = {}", r.error);
    }

    #[test]
    fn test_snap_chamber_valid() {
        for _ in 0..100 {
            let x: f32 = rand_random(-5.0, 5.0);
            let y: f32 = rand_random(-5.0, 5.0);
            let r = snap(x, y);
            assert!(r.chamber <= 5, "Chamber must be 0-5, got {}", r.chamber);
        }
    }

    fn rand_random(lo: f32, hi: f32) -> f32 {
        lo + (hi - lo) * (rand_simple() % 10000) as f32 / 10000.0
    }

    fn rand_simple() -> u32 {
        // Simple xorshift for determinism
        use std::cell::Cell;
        thread_local! { static SEED: Cell<u32> = Cell::new(12345); }
        SEED.with(|s| {
            let mut v = s.get();
            v ^= v << 13;
            v ^= v >> 17;
            v ^= v << 5;
            s.set(v);
            v
        })
    }
}
