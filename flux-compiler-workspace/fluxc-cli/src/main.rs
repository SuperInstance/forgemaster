use clap::{Parser, Subcommand, ValueEnum};
use std::fs;
use std::path::PathBuf;

use fluxc_codegen::{
    codegen, Avx512Target, CudaTarget, EbpfTarget, RiscvTarget, WasmTarget,
};
use fluxc_ir::lower;
use fluxc_optimize::{optimize, IdentityPass};
use fluxc_parser::parse;
use fluxc_verify::verify;

#[derive(Parser)]
#[command(name = "fluxc")]
#[command(about = "Flux Compiler")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Compile {
        #[arg(value_enum)]
        target: TargetType,
        input: PathBuf,
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    Bench {
        input: PathBuf,
        #[arg(short, long, default_value = "1000")]
        iterations: u32,
    },
    Show {
        input: PathBuf,
    },
    Verify {
        input: PathBuf,
    },
}

#[derive(Clone, ValueEnum)]
enum TargetType {
    Avx512,
    Cuda,
    Wasm,
    Ebpf,
    Riscv,
}

#[derive(Debug, thiserror::Error)]
enum CliError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse error: {0}")]
    Parse(String),
    #[error("codegen error: {0}")]
    Codegen(String),
    #[error("verify error: {0}")]
    Verify(String),
    #[error("optimize error: {0}")]
    Optimize(String),
}

fn main() -> Result<(), CliError> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Compile {
            target,
            input,
            output,
        } => {
            let src = fs::read_to_string(&input)?;
            let ast = parse(&src).map_err(|e| CliError::Parse(e.to_string()))?;
            let mut ir = lower(&ast);
            optimize(&mut ir, &[&IdentityPass]).map_err(CliError::Optimize)?;
            let result = match target {
                TargetType::Avx512 => codegen(&ir, &Avx512Target),
                TargetType::Cuda => codegen(&ir, &CudaTarget),
                TargetType::Wasm => codegen(&ir, &WasmTarget),
                TargetType::Ebpf => codegen(&ir, &EbpfTarget),
                TargetType::Riscv => codegen(&ir, &RiscvTarget),
            };
            let code = result.map_err(|e| CliError::Codegen(e.to_string()))?;
            match output {
                Some(path) => fs::write(path, code)?,
                None => println!("{}", code),
            }
        }
        Commands::Bench { input, iterations } => {
            let src = fs::read_to_string(&input)?;
            for i in 0..iterations {
                let ast = parse(&src).map_err(|e| CliError::Parse(e.to_string()))?;
                let mut ir = lower(&ast);
                optimize(&mut ir, &[&IdentityPass]).map_err(CliError::Optimize)?;
                verify(&ast, &ir).map_err(|e| CliError::Verify(e.to_string()))?;
                if i == iterations - 1 {
                    println!("Benchmark completed: {} iterations", iterations);
                }
            }
        }
        Commands::Show { input } => {
            let src = fs::read_to_string(&input)?;
            let ast = parse(&src).map_err(|e| CliError::Parse(e.to_string()))?;
            println!("{:#?}", ast);
        }
        Commands::Verify { input } => {
            let src = fs::read_to_string(&input)?;
            let ast = parse(&src).map_err(|e| CliError::Parse(e.to_string()))?;
            let ir = lower(&ast);
            verify(&ast, &ir).map_err(|e| CliError::Verify(e.to_string()))?;
            println!("Verification passed");
        }
    }
    Ok(())
}
