//! CUDA module for FLUX production GPU kernels.
//!
//! Contains FFI declarations linking to the compiled CUDA kernels.
//! The actual CUDA source lives in `production_kernel.cu` and `incremental_update.cu`.

use std::os::raw::c_int;

// Opaque stream type — callers pass cudaStream_t as a pointer
pub type CudaStream = *mut std::ffi::c_void;

extern "C" {
    /// Launch the production constraint-checking kernel.
    ///
    /// - `flat_bounds`: [n_constraint_sets * 8] INT8 bounds
    /// - `constraint_set_ids`: which constraint set per sensor [n_sensors]
    /// - `sensor_values`: current readings [n_sensors]
    /// - `violation_masks`: output mask per sensor [n_sensors]
    /// - `violation_counts`: output per-constraint totals [8] (zeroed by kernel)
    /// - `n_sensors`: number of sensors
    /// - `stream`: CUDA stream (can be null for default)
    fn launch_flux_production_kernel(
        flat_bounds: *const u8,
        constraint_set_ids: *const c_int,
        sensor_values: *const c_int,
        violation_masks: *mut u8,
        violation_counts: *mut c_int,
        n_sensors: c_int,
        stream: CudaStream,
    );

    /// Launch the incremental bounds update kernel.
    ///
    /// - `bounds`: flat bounds array [n_constraint_sets * 8] (device, mutable)
    /// - `new_bounds`: new bounds data [n_updates * 8] (device)
    /// - `indices`: which constraint sets to update [n_updates] (device)
    /// - `n_updates`: number of constraint sets to update
    /// - `stream`: CUDA stream
    fn launch_flux_update_bounds(
        bounds: *mut u8,
        new_bounds: *const u8,
        indices: *const c_int,
        n_updates: c_int,
        stream: CudaStream,
    );
}

/// Safe wrapper to launch the production kernel.
///
/// # Safety
/// - All device pointers must be valid for the specified sizes.
/// - `violation_counts` must point to at least 8 `i32` values.
/// - `flat_bounds` must have at least `max(constraint_set_ids) * 8 + 8` bytes.
/// - `stream` must be a valid CUDA stream or null.
pub unsafe fn launch_production(
    flat_bounds: *const u8,
    constraint_set_ids: *const c_int,
    sensor_values: *const c_int,
    violation_masks: *mut u8,
    violation_counts: *mut c_int,
    n_sensors: usize,
    stream: CudaStream,
) {
    launch_flux_production_kernel(
        flat_bounds,
        constraint_set_ids,
        sensor_values,
        violation_masks,
        violation_counts,
        n_sensors as c_int,
        stream,
    );
}

/// Safe wrapper to launch the incremental update kernel.
///
/// # Safety
/// - `bounds` must be valid for `max(indices) * 8 + 8` bytes.
/// - `new_bounds` must be valid for `n_updates * 8` bytes.
/// - `indices` must be valid for `n_updates` ints.
/// - `stream` must be a valid CUDA stream or null.
pub unsafe fn launch_update(
    bounds: *mut u8,
    new_bounds: *const u8,
    indices: *const c_int,
    n_updates: usize,
    stream: CudaStream,
) {
    launch_flux_update_bounds(
        bounds,
        new_bounds,
        indices,
        n_updates as c_int,
        stream,
    );
}
