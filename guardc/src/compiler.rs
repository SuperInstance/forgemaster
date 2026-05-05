//! Main compiler pipeline: GUARD source → FLUX bytecode + proof certificate.
//!
//! ```text
//! GUARD Source
//!      │
//!      ▼
//! ┌─────────────┐
//! │   Parser    │  → AST
//! └─────────────┘
//!      │
//!      ▼
//! ┌─────────────┐
//! │ Typechecker │  → Typed AST + unit-normalized expressions
//! └─────────────┘
//!      │
//!      ▼
//! ┌─────────────┐
//! │  CIR Build  │  → CIR (Constraint IR)
//! └─────────────┘
//!      │
//!      ▼
//! ┌─────────────┐
//! │  Lowering   │  → LCIR (flat, ANF, no quantifiers/temporal)
//! └─────────────┘
//!      │
//!      ▼
//! ┌─────────────┐
//! │   Codegen   │  → FLUX bytecode (.flux)
//! └─────────────┘
//!      │
//!      ▼
//! ┌─────────────┐
//! │   Prover    │  → Proof certificate (.guardcert)
//! └─────────────┘
//! ```

use crate::codegen::codegen;
use crate::error::{GuardError, Result};
use crate::lower::lower_module;
use crate::proof::ProofGen;
use flux_isa::bytecode::FluxBytecode;

/// The output of a successful compilation.
#[derive(Debug, Clone)]
pub struct CompileOutput {
    pub bytecode: FluxBytecode,
    pub certificate_json: String,
    pub source_hash: String,
}

/// Compile a CIR module directly (bypassing parser/typechecker for now).
///
/// In a full implementation, this would take raw GUARD source text,
/// parse it, typecheck it, and build the CIR module.  Here we accept
/// a pre-built CIR module so that the pipeline can be tested
/// independently of the frontend.
pub fn compile(module: &crate::cir::CirModule, source_text: &str) -> Result<CompileOutput> {
    // Phase 1: Lowering — CIR → LCIR
    let lcir = lower_module(module)?;

    // Phase 2: Codegen — LCIR → FLUX bytecode
    let bytecode = codegen(&lcir)?;

    // Phase 3: Encode bytecode for hashing
    let bytecode_bytes = bytecode.encode();

    // Phase 4: Proof certificate generation
    let proof_gen = ProofGen::new(module, source_text, &bytecode_bytes);
    let certificate = proof_gen.generate()?;
    let certificate_json =
        serde_json::to_string_pretty(&certificate).map_err(|e| GuardError::Validation(e.to_string()))?;

    let source_hash = sha256_hex(source_text.as_bytes());

    Ok(CompileOutput {
        bytecode,
        certificate_json,
        source_hash,
    })
}

fn sha256_hex(data: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(data);
    let mut s = String::with_capacity(64);
    for b in hasher.finalize() {
        s.push_str(&format!("{:02x}", b));
    }
    s
}
