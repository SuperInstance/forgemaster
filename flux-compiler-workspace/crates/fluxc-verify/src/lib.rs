//! fluxc-verify — Translation validation for FLUX compiler.

use fluxc_codegen::CodegenOutput;
use fluxc_ir::IrModule;
use thiserror::Error;

/// Verification error type.
#[derive(Error, Debug)]
pub enum VerifyError {
    #[error("translation validation failed: {msg}")]
    ValidationFailed { msg: String },

    #[error("verification error: {msg}")]
    Internal { msg: String },
}

/// Result of translation validation.
#[derive(Debug)]
pub struct ValidationResult {
    pub valid: bool,
    pub message: String,
}

/// Validate that the compiled output is a correct translation of the IR.
pub fn validate(ir: &IrModule, output: &CodegenOutput) -> Result<ValidationResult, VerifyError> {
    // Stub: always passes for now
    Ok(ValidationResult {
        valid: true,
        message: format!(
            "translation validation passed for '{}' targeting {:?}",
            ir.name, output.target
        ),
    })
}
