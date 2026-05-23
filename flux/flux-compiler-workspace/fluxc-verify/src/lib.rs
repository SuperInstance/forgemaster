use fluxc_ast::Expr;
use fluxc_ir::Module;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum VerifyError {
    #[error("validation failed: {0}")]
    ValidationFailed(String),
    #[error("ast/ir mismatch: {0}")]
    Mismatch(String),
}

pub fn verify(_ast: &Expr, ir: &Module) -> Result<(), VerifyError> {
    if ir.constraints.is_empty() {
        return Err(VerifyError::ValidationFailed(
            "IR has no constraints".to_string(),
        ));
    }
    Ok(())
}
