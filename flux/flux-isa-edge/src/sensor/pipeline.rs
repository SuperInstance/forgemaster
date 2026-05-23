use std::time::Duration;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;
use uuid::Uuid;
use crate::bytecode::{Bytecode, ExecutionResult};
use crate::vm::{ExecutionLimits, Vm};

/// Source of sensor data.
pub trait SensorSource: Send + Sync + 'static {
    /// Read a batch of sensor data.
    fn read_sensor_data(&mut self) -> Vec<f64>;

    /// Human-readable name for this sensor.
    fn sensor_name(&self) -> &str;
}

/// Pipeline configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineConfig {
    /// Channel capacity for backpressure.
    pub channel_capacity: usize,
    /// Batch size: how many readings per FLUX execution.
    pub batch_size: usize,
    /// Timeout for a single batch.
    pub batch_timeout: Duration,
    /// What to do on constraint violation.
    pub violation_policy: ViolationPolicy,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        PipelineConfig {
            channel_capacity: 1024,
            batch_size: 64,
            batch_timeout: Duration::from_millis(100),
            violation_policy: ViolationPolicy::LogAndContinue,
        }
    }
}

/// What to do when a constraint violation occurs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ViolationPolicy {
    /// Log the violation and keep processing.
    LogAndContinue,
    /// Halt the pipeline on violation.
    Halt,
}

/// A batch of sensor data ready for processing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorBatch {
    pub sensor_name: String,
    pub readings: Vec<f64>,
    pub timestamp: u64,
    pub id: Uuid,
}

/// Pipeline processing result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineResult {
    pub batch_id: Uuid,
    pub sensor_name: String,
    pub execution: ExecutionResult,
    pub passed: bool,
}

/// A processing pipeline: SensorSource → FLUX validate → forward.
pub struct Pipeline<S: SensorSource> {
    sensor: S,
    bytecode: Bytecode,
    config: PipelineConfig,
    vm_limits: ExecutionLimits,
}

impl<S: SensorSource> Pipeline<S> {
    pub fn new(
        sensor: S,
        bytecode: Bytecode,
        config: PipelineConfig,
        vm_limits: ExecutionLimits,
    ) -> Self {
        Pipeline { sensor, bytecode, config, vm_limits }
    }

    /// Run the pipeline, sending results to the provided channel.
    pub async fn run(
        mut self,
        tx: mpsc::Sender<PipelineResult>,
        mut shutdown: tokio::sync::watch::Receiver<bool>,
    ) {
        let mut vm = Vm::new(self.vm_limits.clone());
        let mut batch_buf: Vec<f64> = Vec::with_capacity(self.config.batch_size);

        loop {
            tokio::select! {
                _ = shutdown.changed() => {
                    tracing::info!(sensor = self.sensor.sensor_name(), "pipeline shutting down");
                    break;
                }
                _ = tokio::time::sleep(Duration::from_millis(10)) => {
                    let readings = self.sensor.read_sensor_data();
                    batch_buf.extend(readings);

                    if batch_buf.len() >= self.config.batch_size {
                        self.process_batch(&mut vm, &batch_buf, &tx).await;
                        batch_buf.clear();
                    }
                }
            }
        }

        // Flush remaining.
        if !batch_buf.is_empty() {
            self.process_batch(&mut vm, &batch_buf, &tx).await;
        }
    }

    async fn process_batch(
        &self,
        vm: &mut Vm,
        readings: &[f64],
        tx: &mpsc::Sender<PipelineResult>,
    ) {
        let batch_id = Uuid::new_v4();
        vm.reset();
        vm.push_inputs(readings);

        let execution = vm.execute(&self.bytecode).await;
        let passed = execution.success && execution.violations == 0;

        let result = PipelineResult {
            batch_id,
            sensor_name: self.sensor.sensor_name().to_string(),
            execution,
            passed,
        };

        if tx.send(result).await.is_err() {
            tracing::warn!("pipeline result channel closed");
        }
    }
}
