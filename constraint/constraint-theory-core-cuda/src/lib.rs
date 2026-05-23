//! constraint-theory-core-cuda
//!
//! CUDA FFI bridge connecting the constraint-theory-core Rust CSP solver
//! to GPU-accelerated parallel constraint solving via flux-cuda kernels.
//!
//! Target hardware: JetsonClaw1 (Jetson Xavier NX, 512 CUDA cores, 8GB unified)
//!
//! # Architecture
//!
//! ```text
//! Rust CSP formulation (constraint-theory-core)
//!         │
//!     FFI boundary (this crate)
//!         │
//! CUDA kernels (flux-cuda)
//!     ├── flux_vm_kernel — parallel FLUX VM execution
//!     ├── csp_solver_kernel — parallel backtracking + AC-3
//!     └── sonar_physics_kernel — batch Mackenzie 1981 / Francois-Garrison 1982
//! ```

pub mod cuda_ffi;

pub use cuda_ffi::{
    CspProblem, CspSolution, CudaError, GpuCspSolver, SonarResult,
    LinearConstraint,
};
