//! fluxc-optimize — Optimization passes for FLUX IR.

use fluxc_ir::{FluxIR, IrModule};
use thiserror::Error;

/// Optimization error type.
#[derive(Error, Debug)]
pub enum OptError {
    #[error("optimization failed: {msg}")]
    Failed { msg: String },
}

/// Run all optimization passes on the module.
pub fn optimize(module: &mut IrModule) -> Result<(), OptError> {
    dead_code_elimination(module)?;
    fusion(module)?;
    strength_reduction(module)?;
    Ok(())
}

/// Remove unreachable / no-op instructions.
pub fn dead_code_elimination(module: &mut IrModule) -> Result<(), OptError> {
    for block in &mut module.blocks {
        block.instructions.retain(|inst| !matches!(inst, FluxIR::Nop));
    }
    Ok(())
}

/// Fuse adjacent compatible instructions.
pub fn fusion(_module: &mut IrModule) -> Result<(), OptError> {
    // Stub: instruction fusion pass
    Ok(())
}

/// Replace expensive operations with cheaper equivalents.
pub fn strength_reduction(_module: &mut IrModule) -> Result<(), OptError> {
    // Stub: strength reduction pass
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use fluxc_ir::FluxIR;

    #[test]
    fn dead_code_removes_nop() {
        let mut module = IrModule::new("test");
        let mut block = BasicBlock::new("entry");
        block.instructions.push(FluxIR::Nop);
        block.instructions.push(FluxIR::CheckExact { slot: 0, value: 1 });
        module.blocks.push(block);

        dead_code_elimination(&mut module).unwrap();
        assert_eq!(module.blocks[0].instructions.len(), 1);
    }
}
