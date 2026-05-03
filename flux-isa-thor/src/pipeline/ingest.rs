use tokio::sync::mpsc;
use tracing::{debug, warn};

use super::{PipelineItem, Stage, StageMetrics};

/// INGEST stage: accept raw items and pass to validation.
pub async fn run(
    mut input: mpsc::Receiver<PipelineItem>,
    output: mpsc::Sender<PipelineItem>,
    metrics: &dashmap::DashMap<Stage, StageMetrics>,
) {
    debug!("INGEST stage started");
    while let Some(mut item) = input.recv().await {
        item.stage = Stage::Validate;
        if let Some(mut m) = metrics.get_mut(&Stage::Ingest) {
            m.processed += 1;
        }
        if output.send(item).await.is_err() {
            warn!("INGEST: downstream channel closed");
            break;
        }
    }
    debug!("INGEST stage finished");
}
