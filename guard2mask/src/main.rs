use crate::types::*;
use crate::parser::*;
use crate::csp_optimizer::*;
use crate::backends::*;
use clap::Parser;
use std::fs;

// ------------------------------
// CLI Definition
// ------------------------------
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Input GUARD DSL file
    #[arg(short, long, value_name = "FILE")]
    input: std::path::PathBuf,

    /// Output GDSII mask file
    #[arg(short, long, value_name = "FILE")]
    output: std::path::PathBuf,

    /// Optimization objective
    #[arg(short, long, value_enum, default_value_t = Objective::MinimizeNonZeros)]
    objective: Objective,

    /// Verbose output
    #[arg(short, long, default_value_t = false)]
    verbose: bool,
}

// ------------------------------
// Pipeline Orchestration
// ------------------------------
fn run_pipeline(cli: &Cli) -> anyhow::Result<()> {
    // 1. Read & Parse GUARD DSL
    if cli.verbose { println!("Parsing GUARD DSL from {:?}...", cli.input); }
    let dsl_str = fs::read_to_string(&cli.input)?;
    let spec = parse_guard_dsl(&dsl_str)?;

    if cli.verbose {
        println!("Parsed spec: {} ({}x{})", spec.name, spec.width, spec.height);
        println!("Constraints: {:?}", spec.constraints);
    }

    // 2. Build Constraint System
    if cli.verbose { println!("Building constraint system..."); }
    let mut cs = ConstraintSystem {
        width: spec.width,
        height: spec.height,
        variables: HashMap::new(),
        constraints: Vec::new(),
    };

    // Initialize variables with full ternary domain
    for y in 0..spec.height {
        for x in 0..spec.width {
            cs.variables.insert((x, y), CspVariable {
                id: (x, y),
                domain: FULL_TERNARY_DOMAIN,
            });
        }
    }

    // Expand scope-based constraints (e.g., AllRows → per-row constraints)
    for constraint in spec.constraints {
        match &constraint {
            Constraint::Range { scope: Scope::AllRows, .. } |
            Constraint::Thermal { scope: Scope::AllRows, .. } |
            Constraint::Sparsity { scope: Scope::AllRows, .. } |
            Constraint::Custom { scope: Scope::AllRows, .. } => {
                for y in 0..spec.height {
                    let mut c = constraint.clone();
                    match &mut c {
                        Constraint::Range { scope, .. } => *scope = Scope::Row(y),
                        Constraint::Thermal { scope, .. } => *scope = Scope::Row(y),
                        Constraint::Sparsity { scope, .. } => *scope = Scope::Row(y),
                        Constraint::Custom { scope, .. } => *scope = Scope::Row(y),
                    }
                    cs.constraints.push(c);
                }
            }
            // Add AllColumns expansion, etc.
            _ => cs.constraints.push(constraint),
        }
    }

    // 3. Solve CSP
    if cli.verbose { println!("Solving CSP with objective: {:?}...", cli.objective); }
    let assignment = solve_csp(&cs, cli.objective.clone())?;

    if cli.verbose {
        let nonzeros = assignment.0.values().filter(|&&v| v != TernaryWeight::Zero).count();
        println!("Found valid assignment: {} non-zero weights ({}% sparsity)", 
            nonzeros, 100.0 * (1.0 - nonzeros as f32 / (spec.width * spec.height) as f32));
    }

    // 4. Generate Via Patterns
    if cli.verbose { println!("Generating via patterns..."); }
    let via_config = ViaGeneratorConfig::default();
    let vias = generate_vias(&assignment, &via_config);

    if cli.verbose { println!("Generated {} vias", vias.len()); }

    // 5. Export GDSII
    if cli.verbose { println!("Exporting GDSII to {:?}...", cli.output); }
    let gds_config = GdsExportConfig::default();
    export_gds(&vias, &via_config, &gds_config, &cli.output)?;

    println!("✓ Compilation complete! Mask written to {:?}", cli.output);
    Ok(())
}

// ------------------------------
// Main
// ------------------------------
fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    run_pipeline(&cli)?;
    Ok(())
}
