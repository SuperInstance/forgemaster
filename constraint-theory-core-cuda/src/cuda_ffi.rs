//! CUDA FFI Bridge for constraint-theory-core
//!
//! Connects the published Rust CSP solver (crates.io v2.1.0) to
//! GPU-accelerated parallel constraint solving via the flux-cuda kernels.
//!
//! Architecture:
//!   Rust CSP formulation → FFI → CUDA batch kernel → results back to Rust
//!
//! Target: JetsonClaw1 (Jetson Xavier, 512 CUDA cores, 8GB unified memory)

use std::ffi::{c_double, c_int};
use std::os::raw::c_uint;

/// Opaque handle to CUDA device context
#[repr(C)]
pub struct FluxCudaContext {
    _opaque: [u8; 0],
}

/// Result from a batch CSP solve on GPU
#[repr(C)]
#[derive(Debug, Clone)]
pub struct CudaCspResult {
    /// Number of problems solved
    pub problem_count: c_int,
    /// Pointer to solution arrays (problem_count * max_variables doubles)
    pub solutions: *mut c_double,
    /// Pointer to satisfaction flags (problem_count ints, 1=satisfied, 0=unsatisfiable)
    pub satisfied: *mut c_int,
    /// Pointer to solve times in microseconds
    pub solve_times_us: *mut c_double,
}

/// Result from batch sonar physics computation
#[repr(C)]
#[derive(Debug, Clone)]
pub struct CudaSonarResult {
    pub count: c_int,
    /// Sound speeds (m/s)
    pub sound_speeds: *mut c_double,
    /// Absorption coefficients (dB/km)
    pub absorptions: *mut c_double,
    /// Wavelengths (m)
    pub wavelengths: *mut c_double,
}

/// Error codes from CUDA operations
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CudaError {
    Success = 0,
    NoDevice = -1,
    DeviceInit = -2,
    MemoryAlloc = -3,
    MemoryCopy = -4,
    KernelLaunch = -5,
    InvalidValue = -6,
    Timeout = -7,
    ConstraintViolation = -8,
}

extern "C" {
    // Device management
    pub fn flux_cuda_init() -> *mut FluxCudaContext;
    pub fn flux_cuda_device_info(ctx: *mut FluxCudaContext) -> c_int;
    pub fn flux_cuda_cleanup(ctx: *mut FluxCudaContext);

    // Batch CSP solving
    pub fn flux_cuda_csp_solve(
        ctx: *mut FluxCudaContext,
        variable_counts: *const c_int,    // [problem_count]
        domains: *const c_double,          // flattened: problem1_vars then problem2_vars...
        domain_sizes: *const c_int,        // flattened domain sizes
        constraint_counts: *const c_int,   // [problem_count]
        constraint_data: *const c_double,  // flattened constraint coefficients
        problem_count: c_int,
        max_variables: c_int,
        result: *mut CudaCspResult,
    ) -> CudaError;

    // Batch arc consistency pruning
    pub fn flux_cuda_arc_consistency(
        ctx: *mut FluxCudaContext,
        domain_sizes: *const c_int,
        constraint_indices: *const c_int,
        problem_count: c_int,
        pruned_domains: *mut c_int,        // output: new domain sizes after pruning
    ) -> CudaError;

    // Batch sonar physics
    pub fn flux_cuda_sonar_physics(
        ctx: *mut FluxCudaContext,
        depths: *const c_double,
        temps: *const c_double,
        salinities: *const c_double,
        frequencies: *const c_double,
        count: c_int,
        result: *mut CudaSonarResult,
    ) -> CudaError;

    // Batch FLUX VM execution
    pub fn flux_cuda_batch_execute(
        ctx: *mut FluxCudaContext,
        bytecode: *const c_uint,            // FLUX bytecode blob
        bytecode_size: c_int,
        inputs: *const c_double,            // [instance_count * input_size]
        input_size: c_int,
        instance_count: c_int,
        outputs: *mut c_double,             // [instance_count * output_size]
        constraint_flags: *mut c_int,       // [instance_count]
    ) -> CudaError;

    // Memory management for results
    pub fn flux_cuda_free_csp_result(result: *mut CudaCspResult);
    pub fn flux_cuda_free_sonar_result(result: *mut CudaSonarResult);
}

/// Safe Rust wrapper for CUDA CSP solver
pub struct GpuCspSolver {
    ctx: *mut FluxCudaContext,
}

impl GpuCspSolver {
    /// Initialize CUDA device context
    pub fn new() -> Result<Self, CudaError> {
        let ctx = unsafe { flux_cuda_init() };
        if ctx.is_null() {
            return Err(CudaError::DeviceInit);
        }
        Ok(Self { ctx })
    }

    /// Get device compute capability (e.g., 72 for Jetson Xavier)
    pub fn device_info(&self) -> i32 {
        unsafe { flux_cuda_device_info(self.ctx) }
    }

    /// Solve multiple independent CSP problems in parallel on GPU
    ///
    /// Each problem has its own variable set, domains, and constraints.
    /// The GPU explores all problems simultaneously, using one thread block
    /// per problem instance.
    ///
    /// Returns vector of (satisfied, solution) tuples.
    pub fn solve_batch(
        &self,
        problems: &[CspProblem],
    ) -> Result<Vec<CspSolution>, CudaError> {
        let n = problems.len() as c_int;
        let max_vars = problems.iter().map(|p| p.variable_count).max().unwrap_or(0) as c_int;

        // Flatten domains and constraints for GPU transfer
        let mut var_counts: Vec<c_int> = Vec::with_capacity(problems.len());
        let mut constraint_counts: Vec<c_int> = Vec::with_capacity(problems.len());
        let mut all_domains: Vec<c_double> = Vec::new();
        let mut domain_sizes_flat: Vec<c_int> = Vec::new();
        let mut all_constraints: Vec<c_double> = Vec::new();

        for problem in problems {
            var_counts.push(problem.variable_count as c_int);
            constraint_counts.push(problem.constraints.len() as c_int);
            for domain in &problem.domains {
                domain_sizes_flat.push(domain.len() as c_int);
                for &val in domain {
                    all_domains.push(val);
                }
            }
            for c in &problem.constraints {
                all_constraints.push(c.coefficients[0]);
                all_constraints.push(c.coefficients[1]);
                all_constraints.push(c.rhs);
            }
        }

        let mut result: CudaCspResult = unsafe { std::mem::zeroed() };

        let err = unsafe {
            flux_cuda_csp_solve(
                self.ctx,
                var_counts.as_ptr(),
                all_domains.as_ptr(),
                domain_sizes_flat.as_ptr(),
                constraint_counts.as_ptr(),
                all_constraints.as_ptr(),
                n,
                max_vars,
                &mut result,
            )
        };

        if err != CudaError::Success {
            return Err(err);
        }

        // Extract results
        let mut solutions = Vec::with_capacity(problems.len());
        unsafe {
            for i in 0..problems.len() {
                let satisfied = *result.satisfied.add(i);
                let mut sol = vec![0.0f64; problems[i].variable_count];
                for j in 0..problems[i].variable_count {
                    sol[j] = *result.solutions.add(i * max_vars as usize + j);
                }
                solutions.push(CspSolution {
                    satisfied: satisfied != 0,
                    values: sol,
                });
            }
            flux_cuda_free_csp_result(&mut result);
        }

        Ok(solutions)
    }

    /// Batch sonar physics computation on GPU
    ///
    /// Computes Mackenzie 1981 sound speed + Francois-Garrison 1982 absorption
    /// for thousands of depth/temp/salinity/frequency tuples in parallel.
    pub fn sonar_physics_batch(
        &self,
        depths: &[f64],
        temps: &[f64],
        salinities: &[f64],
        frequencies: &[f64],
    ) -> Result<Vec<SonarResult>, CudaError> {
        assert_eq!(depths.len(), temps.len());
        assert_eq!(depths.len(), salinities.len());
        assert_eq!(depths.len(), frequencies.len());

        let n = depths.len() as c_int;
        let mut result: CudaSonarResult = unsafe { std::mem::zeroed() };

        let err = unsafe {
            flux_cuda_sonar_physics(
                self.ctx,
                depths.as_ptr() as *const c_double,
                temps.as_ptr() as *const c_double,
                salinities.as_ptr() as *const c_double,
                frequencies.as_ptr() as *const c_double,
                n,
                &mut result,
            )
        };

        if err != CudaError::Success {
            return Err(err);
        }

        let mut results = Vec::with_capacity(depths.len());
        unsafe {
            for i in 0..depths.len() {
                results.push(SonarResult {
                    sound_speed: *result.sound_speeds.add(i),
                    absorption: *result.absorptions.add(i),
                    wavelength: *result.wavelengths.add(i),
                });
            }
            flux_cuda_free_sonar_result(&mut result);
        }

        Ok(results)
    }
}

impl Drop for GpuCspSolver {
    fn drop(&mut self) {
        unsafe { flux_cuda_cleanup(self.ctx) };
    }
}

// Safe Rust types for CSP problems

/// A single CSP problem for batch GPU solving
pub struct CspProblem {
    pub variable_count: usize,
    pub domains: Vec<Vec<f64>>,
    pub constraints: Vec<LinearConstraint>,
}

/// Linear constraint: a*x + b*y <= rhs (or ==, >= depending on type)
pub struct LinearConstraint {
    pub coefficients: [f64; 2],
    pub rhs: f64,
}

/// Solution from GPU CSP solver
pub struct CspSolution {
    pub satisfied: bool,
    pub values: Vec<f64>,
}

/// Sonar physics result from GPU computation
pub struct SonarResult {
    pub sound_speed: f64,
    pub absorption: f64,
    pub wavelength: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_solver_init() {
        // Will fail on non-CUDA machine — that's expected
        let solver = GpuCspSolver::new();
        match solver {
            Ok(s) => {
                let info = s.device_info();
                println!("CUDA device compute capability: {}", info);
                assert!(info > 0);
            }
            Err(e) => {
                println!("No CUDA device available: {:?}", e);
                // This is fine — we're testing the API, not the hardware
            }
        }
    }

    #[test]
    fn test_problem_construction() {
        let problem = CspProblem {
            variable_count: 2,
            domains: vec![vec![1.0, 2.0, 3.0], vec![1.0, 2.0, 3.0]],
            constraints: vec![
                LinearConstraint { coefficients: [1.0, -1.0], rhs: 0.0 },  // x != y (represented as x - y != 0)
                LinearConstraint { coefficients: [1.0, 1.0], rhs: 4.0 },   // x + y <= 4
            ],
        };
        assert_eq!(problem.variable_count, 2);
        assert_eq!(problem.constraints.len(), 2);
    }
}
