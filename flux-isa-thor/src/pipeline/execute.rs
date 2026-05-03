use std::sync::Arc;
use tokio::sync::{mpsc, Semaphore};
use tracing::{debug, warn};

use super::{PipelineItem, Stage, StageMetrics};

/// EXECUTE stage: run FLUX bytecode through the VM.
pub async fn run(
    mut input: mpsc::Receiver<PipelineItem>,
    output: mpsc::Sender<PipelineItem>,
    metrics: &dashmap::DashMap<Stage, StageMetrics>,
    semaphore: Arc<Semaphore>,
) {
    debug!("EXECUTE stage started");
    while let Some(mut item) = input.recv().await {
        let _permit = semaphore.acquire().await.unwrap();

        // Execute bytecode (simplified — production would use ThorVm)
        match execute_bytecode(&item.payload) {
            Ok(result_payload) => {
                item.payload = result_payload;
            }
            Err(e) => {
                if let Some(mut m) = metrics.get_mut(&Stage::Execute) {
                    m.errors += 1;
                }
                item.error = Some(format!("execution error: {e}"));
                warn!("EXECUTE: failed for item {}: {e}", item.id);
                continue;
            }
        }

        item.stage = Stage::Commit;
        if let Some(mut m) = metrics.get_mut(&Stage::Execute) {
            m.processed += 1;
        }
        if output.send(item).await.is_err() {
            warn!("EXECUTE: downstream channel closed");
            break;
        }
    }
    debug!("EXECUTE stage finished");
}

/// Minimal bytecode interpreter for pipeline execution.
/// Production: delegates to ThorVm::execute().
fn execute_bytecode(bytecode: &[u8]) -> Result<Vec<u8>, String> {
    let mut pc = 0;
    let mut stack: Vec<f64> = Vec::new();

    while pc < bytecode.len() {
        let op = bytecode[pc];
        match op {
            0x00 => {} // NOP
            0x01 => {
                // PUSH
                if pc + 9 > bytecode.len() {
                    return Err("PUSH: insufficient bytes".into());
                }
                let val = f64::from_be_bytes(
                    bytecode[pc + 1..pc + 9].try_into().map_err(|_| "bad float")?,
                );
                stack.push(val);
                pc += 8;
            }
            0x10 => binop_stack(&mut stack, |a, b| a + b)?,
            0x11 => binop_stack(&mut stack, |a, b| a - b)?,
            0x12 => binop_stack(&mut stack, |a, b| a * b)?,
            0x13 => binop_stack(&mut stack, |a, b| a / b)?,
            0x45 => break, // HALT
            0x54 => {
                // VERIFY — push result
                let ok = stack.pop().unwrap_or(1.0);
                stack.push(ok);
            }
            _ => return Err(format!("unknown opcode 0x{op:02X} at pc={pc}")),
        }
        pc += 1;
    }

    // Serialize stack as result
    Ok(serde_json::to_vec(&stack).unwrap_or_default())
}

fn binop_stack(stack: &mut Vec<f64>, f: impl Fn(f64, f64) -> f64) -> Result<(), String> {
    let b = stack.pop().ok_or("stack underflow (b)")?;
    let a = stack.pop().ok_or("stack underflow (a)")?;
    stack.push(f(a, b));
    Ok(())
}
