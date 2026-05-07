use tokio::sync::mpsc;
use tracing::{debug, warn};

use super::{PipelineItem, Stage, StageMetrics};

/// COMPILE stage: compile CSP spec to FLUX bytecode if needed.
pub async fn run(
    mut input: mpsc::Receiver<PipelineItem>,
    output: mpsc::Sender<PipelineItem>,
    metrics: &dashmap::DashMap<Stage, StageMetrics>,
) {
    debug!("COMPILE stage started");
    while let Some(mut item) = input.recv().await {
        // If payload starts with valid opcode, assume already compiled
        let already_compiled = item
            .payload
            .first()
            .and_then(|&b| crate::opcode::Instruction::from_byte(b))
            .is_some();

        if !already_compiled {
            // Compile CSP JSON spec → FLUX bytecode
            match compile_csp(&item.payload) {
                Ok(bytecode) => {
                    item.payload = bytecode;
                }
                Err(e) => {
                    if let Some(mut m) = metrics.get_mut(&Stage::Compile) {
                        m.errors += 1;
                    }
                    item.error = Some(format!("compile error: {e}"));
                    warn!("COMPILE: failed for item {}: {e}", item.id);
                    continue;
                }
            }
        }

        item.stage = Stage::Execute;
        if let Some(mut m) = metrics.get_mut(&Stage::Compile) {
            m.processed += 1;
        }
        if output.send(item).await.is_err() {
            warn!("COMPILE: downstream channel closed");
            break;
        }
    }
    debug!("COMPILE stage finished");
}

/// Compile a CSP JSON spec into FLUX bytecode.
/// Production: full CSP→FLUX compiler with arc-consistency preprocessing.
fn compile_csp(csp_json: &[u8]) -> Result<Vec<u8>, String> {
    // Parse as JSON to validate
    let _: serde_json::Value =
        serde_json::from_slice(csp_json).map_err(|e| format!("invalid JSON: {e}"))?;

    // Minimal bytecode: HALT
    // Production compiler would emit:
    //   PUSH vars... CONSTRAIN (per constraint) PROPAGATE SOLVE VERIFY HALT
    Ok(vec![0x45]) // HALT
}
