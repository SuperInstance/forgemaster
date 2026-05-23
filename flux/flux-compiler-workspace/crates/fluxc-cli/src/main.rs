//! fluxc-cli — Command-line interface for the FLUX compiler.

use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "fluxc")]
#[command(about = "FLUX constraint compiler")]
#[command(version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Compile a FLUX constraint file.
    Compile {
        /// Input constraint file.
        #[arg(short, long)]
        input: PathBuf,

        /// Target platform (native, avx512, cuda, wasm, ebpf, riscv).
        #[arg(short, long, default_value = "native")]
        target: String,

        /// Output file path.
        #[arg(short, long)]
        output: Option<PathBuf>,
    },

    /// Benchmark compiled constraints.
    Bench {
        /// Input constraint file.
        #[arg(short, long)]
        input: PathBuf,

        /// Number of iterations.
        #[arg(short, long, default_value_t = 1000)]
        iterations: u64,
    },

    /// Show IR or assembly for a constraint file.
    Show {
        /// Input constraint file.
        #[arg(short, long)]
        input: PathBuf,

        /// Target platform for assembly output.
        #[arg(short, long, default_value = "native")]
        target: String,
    },

    /// Verify translation correctness.
    Verify {
        /// Input constraint file.
        #[arg(short, long)]
        input: PathBuf,

        /// Path to compiled output for validation.
        #[arg(short, long)]
        compiled: PathBuf,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Compile { input, target, output } => {
            println!("Compiling {:?} for target '{}' -> {:?}", input, target, output);
        }
        Commands::Bench { input, iterations } => {
            println!("Benchmarking {:?} ({} iterations)", input, iterations);
        }
        Commands::Show { input, target } => {
            println!("Showing {:?} for target '{}'", input, target);
        }
        Commands::Verify { input, compiled } => {
            println!("Verifying {:?} against {:?}", input, compiled);
        }
    }
}
