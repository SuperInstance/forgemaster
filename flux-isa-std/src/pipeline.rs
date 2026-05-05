use thiserror::Error;

use crate::bytecode::{FluxBytecode, BytecodeError};
use crate::gate::{GateConfig, QualityGate};
use crate::vm::{FluxVM, VMConfig, VMError};

#[derive(Debug, Error)]
pub enum PipelineError {
    #[error("VM error: {0}")]
    VM(#[from] VMError),
    #[error("Bytecode error: {0}")]
    Bytecode(#[from] BytecodeError),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Gate rejected: {0}")]
    GateRejected(String),
}

/// Output format for pipeline results
#[derive(Debug, Clone)]
pub enum OutputFormat {
    Json,
    Plain,
    Compact,
}

/// Pipeline configuration
#[derive(Debug, Clone)]
pub struct PipelineConfig {
    pub vm: VMConfig,
    pub gate: GateConfig,
    pub validate_before_run: bool,
    pub output_format: OutputFormat,
    pub trace: bool,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        let mut vm = VMConfig::default();
        vm.trace_enabled = false;
        Self {
            vm,
            gate: GateConfig::default(),
            validate_before_run: true,
            output_format: OutputFormat::Plain,
            trace: false,
        }
    }
}

/// Pipeline result
#[derive(Debug)]
pub struct PipelineResult {
    pub success: bool,
    pub stack: Vec<f64>,
    pub output: Vec<String>,
    pub trace_count: usize,
    pub error: Option<String>,
}

/// Processing pipeline: receive → validate → execute → forward
pub struct Pipeline {
    config: PipelineConfig,
    vm: FluxVM,
    gate: QualityGate,
}

impl Pipeline {
    pub fn new(config: PipelineConfig) -> Self {
        let vm = FluxVM::new(config.vm.clone());
        let gate = QualityGate::new(config.gate.clone());
        Self { config, vm, gate }
    }

    pub fn with_default_config() -> Self {
        Self::new(PipelineConfig::default())
    }

    /// Process a single bytecode
    pub fn process(&mut self, bytecode: &FluxBytecode) -> PipelineResult {
        // Validate
        if self.config.validate_before_run {
            if let Err(e) = bytecode.validate() {
                return PipelineResult {
                    success: false,
                    stack: vec![],
                    output: vec![],
                    trace_count: 0,
                    error: Some(format!("Validation failed: {}", e)),
                };
            }
        }

        // Execute
        match self.vm.execute_bytecode(bytecode) {
            Ok(()) => PipelineResult {
                success: true,
                stack: self.vm.stack().to_vec(),
                output: self.vm.output().to_vec(),
                trace_count: self.vm.trace().len(),
                error: None,
            },
            Err(e) => PipelineResult {
                success: false,
                stack: self.vm.stack().to_vec(),
                output: self.vm.output().to_vec(),
                trace_count: self.vm.trace().len(),
                error: Some(format!("{}", e)),
            },
        }
    }

    /// Process bytecode loaded from a file
    pub fn process_file(&mut self, path: &str) -> PipelineResult {
        match FluxBytecode::load_from_file(path) {
            Ok(bytecode) => self.process(&bytecode),
            Err(e) => PipelineResult {
                success: false,
                stack: vec![],
                output: vec![],
                trace_count: 0,
                error: Some(format!("Load error: {}", e)),
            },
        }
    }

    /// Batch process multiple bytecodes
    pub fn process_batch(&mut self, bytecodes: &[FluxBytecode]) -> Vec<PipelineResult> {
        bytecodes.iter().map(|bc| self.process(bc)).collect()
    }

    /// Run quality gate check on text output
    pub fn gate_check(&self, text: &str) -> crate::gate::GateVerdict {
        self.gate.check(text)
    }

    /// Process and format output
    pub fn process_formatted(&mut self, bytecode: &FluxBytecode) -> (PipelineResult, String) {
        let result = self.process(bytecode);
        let formatted = match self.config.output_format {
            OutputFormat::Json => serde_json::to_string_pretty(&serde_json::json!({
                "success": result.success,
                "stack": result.stack,
                "output": result.output,
                "error": result.error,
            })).unwrap_or_else(|_| "JSON error".into()),
            OutputFormat::Plain => {
                let mut s = String::new();
                if result.success {
                    s.push_str("OK\n");
                } else {
                    s.push_str(&format!("ERROR: {}\n", result.error.as_deref().unwrap_or("unknown")));
                }
                if !result.stack.is_empty() {
                    s.push_str(&format!("Stack: {:?}\n", result.stack));
                }
                for line in &result.output {
                    s.push_str(&format!("> {}\n", line));
                }
                s
            }
            OutputFormat::Compact => {
                if result.success {
                    result.output.join(",")
                } else {
                    format!("ERR:{}", result.error.as_deref().unwrap_or("?"))
                }
            }
        };
        (result, formatted)
    }
}
