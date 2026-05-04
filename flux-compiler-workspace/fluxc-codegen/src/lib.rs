use fluxc_ir::Module;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum CodegenError {
    #[error("unsupported target: {0}")]
    UnsupportedTarget(String),
    #[error("codegen failed: {0}")]
    Other(String),
}

pub trait Target {
    fn emit(&self, module: &Module, output: &mut String) -> Result<(), CodegenError>;
}

pub struct Avx512Target;

impl Target for Avx512Target {
    fn emit(&self, _module: &Module, _output: &mut String) -> Result<(), CodegenError> {
        #[cfg(feature = "avx512")]
        {
            _output.push_str("; AVX-512 codegen stub\n");
            Ok(())
        }
        #[cfg(not(feature = "avx512"))]
        {
            Err(CodegenError::UnsupportedTarget("avx512".to_string()))
        }
    }
}

pub struct WasmTarget;

impl Target for WasmTarget {
    fn emit(&self, _module: &Module, _output: &mut String) -> Result<(), CodegenError> {
        #[cfg(feature = "wasm")]
        {
            _output.push_str("(module ;; wasm stub)\n");
            Ok(())
        }
        #[cfg(not(feature = "wasm"))]
        {
            Err(CodegenError::UnsupportedTarget("wasm".to_string()))
        }
    }
}

pub struct EbpfTarget;

impl Target for EbpfTarget {
    fn emit(&self, _module: &Module, _output: &mut String) -> Result<(), CodegenError> {
        #[cfg(feature = "ebpf")]
        {
            _output.push_str("; eBPF codegen stub\n");
            Ok(())
        }
        #[cfg(not(feature = "ebpf"))]
        {
            Err(CodegenError::UnsupportedTarget("ebpf".to_string()))
        }
    }
}

pub struct RiscvTarget;

impl Target for RiscvTarget {
    fn emit(&self, _module: &Module, _output: &mut String) -> Result<(), CodegenError> {
        #[cfg(feature = "riscv")]
        {
            _output.push_str("; RISC-V codegen stub\n");
            Ok(())
        }
        #[cfg(not(feature = "riscv"))]
        {
            Err(CodegenError::UnsupportedTarget("riscv".to_string()))
        }
    }
}

pub struct CudaTarget;

impl Target for CudaTarget {
    fn emit(&self, _module: &Module, _output: &mut String) -> Result<(), CodegenError> {
        #[cfg(feature = "cuda")]
        {
            _output.push_str("; CUDA codegen stub\n");
            Ok(())
        }
        #[cfg(not(feature = "cuda"))]
        {
            Err(CodegenError::UnsupportedTarget("cuda".to_string()))
        }
    }
}

pub fn codegen(module: &Module, target: &dyn Target) -> Result<String, CodegenError> {
    let mut output = String::new();
    target.emit(module, &mut output)?;
    Ok(output)
}
