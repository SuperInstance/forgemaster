pub mod compile;
pub mod execute;
pub mod ingest;
pub mod validate;

use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tokio::sync::{mpsc, Semaphore};


/// Pipeline stage names.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Stage {
    Ingest,
    Validate,
    Compile,
    Execute,
    Commit,
}

impl std::fmt::Display for Stage {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Stage::Ingest => write!(f, "INGEST"),
            Stage::Validate => write!(f, "VALIDATE"),
            Stage::Compile => write!(f, "COMPILE"),
            Stage::Execute => write!(f, "EXECUTE"),
            Stage::Commit => write!(f, "COMMIT"),
        }
    }
}

/// Item flowing through the pipeline.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineItem {
    pub id: uuid::Uuid,
    pub stage: Stage,
    pub payload: Vec<u8>,
    pub error: Option<String>,
    pub entered_at_ns: u64,
}

/// Pipeline metrics per stage.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct StageMetrics {
    pub processed: u64,
    pub errors: u64,
    pub total_time_ns: u64,
}

/// Pipeline configuration.
#[derive(Debug, Clone)]
pub struct PipelineConfig {
    pub channel_capacity: usize,
    pub max_concurrent_execute: usize,
    pub checkpoint_interval_secs: u64,
    pub batch_size: usize,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        Self {
            channel_capacity: 1024,
            max_concurrent_execute: 8,
            checkpoint_interval_secs: 60,
            batch_size: 64,
        }
    }
}

/// The complete 5-stage pipeline: INGEST → VALIDATE → COMPILE → EXECUTE → COMMIT
pub struct Pipeline {
    config: PipelineConfig,
    metrics: Arc<dashmap::DashMap<Stage, StageMetrics>>,
    throughput: Arc<AtomicU64>,
}

impl Pipeline {
    pub fn new(config: PipelineConfig) -> Self {
        let metrics = Arc::new(dashmap::DashMap::new());
        for stage in [
            Stage::Ingest,
            Stage::Validate,
            Stage::Compile,
            Stage::Execute,
            Stage::Commit,
        ] {
            metrics.insert(stage, StageMetrics::default());
        }
        Self {
            config,
            metrics,
            throughput: Arc::new(AtomicU64::new(0)),
        }
    }

    /// Run the pipeline with the given input channel.
    /// Returns the committed-item counter for monitoring.
    pub async fn run(
        &self,
        input: mpsc::Receiver<PipelineItem>,
    ) {
        let cap = self.config.channel_capacity;

        // INGEST → VALIDATE
        let (tx_validate, rx_validate) = mpsc::channel(cap);
        // VALIDATE → COMPILE
        let (tx_compile, rx_compile) = mpsc::channel(cap);
        // COMPILE → EXECUTE
        let (tx_execute, rx_execute) = mpsc::channel(cap);
        // EXECUTE → COMMIT
        let (tx_commit, mut rx_commit) = mpsc::channel(cap);

        let metrics = self.metrics.clone();
        let throughput = self.throughput.clone();
        let exec_semaphore = Arc::new(Semaphore::new(self.config.max_concurrent_execute));

        // Stage 1: INGEST
        let m1 = metrics.clone();
        tokio::spawn(async move {
            ingest::run(input, tx_validate, &m1).await;
        });

        // Stage 2: VALIDATE
        let m2 = metrics.clone();
        tokio::spawn(async move {
            validate::run(rx_validate, tx_compile, &m2).await;
        });

        // Stage 3: COMPILE
        let m3 = metrics.clone();
        tokio::spawn(async move {
            compile::run(rx_compile, tx_execute, &m3).await;
        });

        // Stage 4: EXECUTE
        let m4 = metrics.clone();
        let sem = exec_semaphore;
        tokio::spawn(async move {
            execute::run(rx_execute, tx_commit, &m4, sem).await;
        });

        // Stage 5: COMMIT
        let m5 = metrics.clone();
        let tp = throughput.clone();
        tokio::spawn(async move {
            // Commit stage just passes through and counts
            while let Some(_item) = rx_commit.recv().await {
                tp.fetch_add(1, Ordering::Relaxed);
                if let Some(mut m) = m5.get_mut(&Stage::Commit) {
                    m.processed += 1;
                }
            }
        });
    }

    /// Get metrics snapshot.
    pub fn metrics_snapshot(&self) -> std::collections::HashMap<Stage, StageMetrics> {
        let mut map = std::collections::HashMap::new();
        for entry in self.metrics.iter() {
            map.insert(*entry.key(), entry.value().clone());
        }
        map
    }

    /// Total items committed.
    pub fn total_committed(&self) -> u64 {
        self.throughput.load(Ordering::Relaxed)
    }
}
