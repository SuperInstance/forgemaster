pub mod solver;
pub mod sonar;

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Semaphore;

/// Solution from a single CSP instance.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CspSolution {
    pub instance_id: u64,
    pub satisfied: bool,
    pub assignments: Vec<(String, f64)>,
    pub solve_time_ns: u64,
}

/// Result from a batch sonar computation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SonarResult {
    pub index: u64,
    pub sound_speed: f64,
    pub absorption: f64,
    pub depth: f64,
    pub temperature: f64,
    pub salinity: f64,
}

/// Dispatches work to GPU or CPU based on problem size.
pub struct GpuDispatcher {
    gpu_available: bool,
    gpu_memory_mb: u32,
    max_concurrent_kernels: usize,
    semaphore: Arc<Semaphore>,
}

impl GpuDispatcher {
    pub fn new(gpu_available: bool, gpu_memory_mb: u32, max_concurrent_kernels: usize) -> Self {
        Self {
            gpu_available,
            gpu_memory_mb,
            max_concurrent_kernels,
            semaphore: Arc::new(Semaphore::new(max_concurrent_kernels)),
        }
    }

    /// Returns true if the batch size warrants GPU offload.
    pub fn should_use_gpu(&self, batch_size: usize) -> bool {
        self.gpu_available && batch_size >= 256
    }

    /// GPU memory in MB.
    pub fn gpu_memory_mb(&self) -> u32 {
        self.gpu_memory_mb
    }

    /// Available kernel slots.
    pub fn available_slots(&self) -> usize {
        self.semaphore.available_permits()
    }

    pub fn semaphore(&self) -> Arc<Semaphore> {
        self.semaphore.clone()
    }
}
