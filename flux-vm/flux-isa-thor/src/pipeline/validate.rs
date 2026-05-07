use tokio::sync::mpsc;
use tracing::{debug, warn};

use super::{PipelineItem, Stage, StageMetrics};

/// VALIDATE stage: check payload integrity.
pub async fn run(
    mut input: mpsc::Receiver<PipelineItem>,
    output: mpsc::Sender<PipelineItem>,
    metrics: &dashmap::DashMap<Stage, StageMetrics>,
) {
    debug!("VALIDATE stage started");
    while let Some(mut item) = input.recv().await {
        // Validate: payload must not be empty
        if item.payload.is_empty() {
            if let Some(mut m) = metrics.get_mut(&Stage::Validate) {
                m.errors += 1;
            }
            item.error = Some("empty payload".into());
            warn!("VALIDATE: empty payload for item {}", item.id);
            continue; // Drop invalid items (or send to dead-letter)
        }

        // Validate: first byte must be a valid opcode
        if let Some(&first) = item.payload.first() {
            if crate::opcode::Instruction::from_byte(first).is_none()
                && item.payload.len() > 1
            {
                // Might be a CSP spec rather than bytecode — allow through
                debug!("VALIDATE: first byte 0x{:02X} not an opcode, assuming CSP spec", first);
            }
        }

        item.stage = Stage::Compile;
        item.error = None;
        if let Some(mut m) = metrics.get_mut(&Stage::Validate) {
            m.processed += 1;
        }
        if output.send(item).await.is_err() {
            warn!("VALIDATE: downstream channel closed");
            break;
        }
    }
    debug!("VALIDATE stage finished");
}
