use clap::{Parser, Subcommand};
use std::process;

use flux_isa_std::bytecode::FluxBytecode;
use flux_isa_std::vm::{FluxVM, VMConfig};

#[derive(Parser)]
#[command(name = "flux-isa-std")]
#[command(about = "FLUX ISA constraint VM for embedded Linux edge nodes")]
#[command(version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Execute a FLUX bytecode file
    Run {
        /// Path to .flux bytecode file
        file: String,
        /// Enable execution tracing
        #[arg(long)]
        trace: bool,
        /// Max stack size
        #[arg(long, default_value = "4096")]
        max_stack: usize,
    },
    /// Validate bytecode without executing
    Validate {
        /// Path to .flux bytecode file
        file: String,
    },
    /// Disassemble bytecode to human-readable form
    Disassemble {
        /// Path to .flux bytecode file
        file: String,
    },
    /// Compile CSP JSON spec to FLUX bytecode
    Compile {
        /// Input CSP JSON spec file
        #[arg(long)]
        csp: String,
        /// Output .flux file
        #[arg(long)]
        output: Option<String>,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Run { file, trace, max_stack } => {
            let bytecode = match FluxBytecode::load_from_file(&file) {
                Ok(bc) => bc,
                Err(e) => {
                    eprintln!("Error loading {}: {}", file, e);
                    process::exit(1);
                }
            };

            if let Err(e) = bytecode.validate() {
                eprintln!("Validation error: {}", e);
                process::exit(1);
            }

            let mut config = VMConfig::default();
            config.max_stack_size = max_stack;
            config.trace_enabled = trace;

            let mut vm = FluxVM::new(config);
            match vm.execute_bytecode(&bytecode) {
                Ok(()) => {
                    for line in vm.output() {
                        println!("{}", line);
                    }
                    if !vm.stack().is_empty() {
                        eprintln!("Stack: {:?}", vm.stack());
                    }
                }
                Err(e) => {
                    eprintln!("Execution error: {}", e);
                    process::exit(1);
                }
            }
        }
        Commands::Validate { file } => {
            let bytecode = match FluxBytecode::load_from_file(&file) {
                Ok(bc) => bc,
                Err(e) => {
                    eprintln!("Error loading {}: {}", file, e);
                    process::exit(1);
                }
            };
            match bytecode.validate() {
                Ok(()) => println!("Valid: {} instructions", bytecode.instructions.len()),
                Err(e) => {
                    eprintln!("Invalid: {}", e);
                    process::exit(1);
                }
            }
        }
        Commands::Disassemble { file } => {
            let bytecode = match FluxBytecode::load_from_file(&file) {
                Ok(bc) => bc,
                Err(e) => {
                    eprintln!("Error loading {}: {}", file, e);
                    process::exit(1);
                }
            };
            print!("{}", bytecode.disassemble());
        }
        Commands::Compile { csp, output } => {
            // Basic CSP-to-FLUX compiler stub
            let spec = match std::fs::read_to_string(&csp) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error reading {}: {}", csp, e);
                    process::exit(1);
                }
            };
            let _json: serde_json::Value = match serde_json::from_str(&spec) {
                Ok(v) => v,
                Err(e) => {
                    eprintln!("Invalid JSON in {}: {}", csp, e);
                    process::exit(1);
                }
            };

            // Stub: generate a simple bytecode that pushes the constraint count
            use flux_isa_std::instruction::FluxInstruction;
            use flux_isa_std::opcode::FluxOpCode;

            let bytecode = FluxBytecode::new(vec![
                FluxInstruction::new(FluxOpCode::Push).with_operand(0.0),
                FluxInstruction::new(FluxOpCode::Halt),
            ]);

            match output {
                Some(path) => {
                    if let Err(e) = bytecode.save_to_file(&path) {
                        eprintln!("Error saving {}: {}", path, e);
                        process::exit(1);
                    }
                    println!("Compiled to {}", path);
                }
                None => {
                    match bytecode.to_json() {
                        Ok(json) => println!("{}", json),
                        Err(e) => {
                            eprintln!("Error serializing: {}", e);
                            process::exit(1);
                        }
                    }
                }
            }
        }
    }
}
