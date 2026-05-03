pub mod generic;
pub mod parser;
pub mod sonar;
pub mod thermal;

use crate::engine::vm::Bytecode;

/// A parsed constraint problem ready for FLUX compilation.
#[derive(Debug, Clone)]
pub struct ConstraintProblem {
    pub domain: String,
    pub variables: Vec<Variable>,
    pub constraints: Vec<Constraint>,
    pub assertion: Assertion,
}

#[derive(Debug, Clone)]
pub struct Variable {
    pub name: String,
    pub value: f64,
    pub desc: String,
}

#[derive(Debug, Clone)]
pub enum Constraint {
    SoundVelocity { depth_m: f64, temp_c: f64, salinity_ppt: f64 },
    Absorption { frequency_khz: f64, depth_m: f64, temp_c: f64, salinity_ppt: f64 },
    TransmissionLoss { range_m: f64, frequency_khz: f64, depth_m: f64, temp_c: f64, salinity_ppt: f64 },
    ThermalBound { temp_c: f64, min_safe: f64, max_safe: f64 },
    GenericCompare { left: f64, operator: String, right: f64, desc: String },
    GenericBound { value: f64, min: f64, max: f64, desc: String },
    GenericRangeCheck { value: f64, min: f64, max: f64, desc: String },
}

#[derive(Debug, Clone)]
pub struct Assertion {
    pub assertion_type: String, // "gt" | "lt" | "eq" | "in_range"
    pub expected: f64,
    pub actual_expr: String, // description of what's being checked
}

/// Parse a natural language claim into a constraint problem.
pub fn parse_claim(claim: &str, domain: &str) -> Result<ConstraintProblem, String> {
    match domain {
        "sonar" => sonar::parse(claim),
        "thermal" => thermal::parse(claim),
        "generic" => generic::parse(claim),
        _ => Err(format!("Unknown domain: '{}'. Use sonar, thermal, or generic.", domain)),
    }
}

/// Compile a constraint problem into FLUX bytecodes.
pub fn compile(problem: &ConstraintProblem) -> Vec<Bytecode> {
    let mut bytecodes = Vec::new();

    // Load all variables
    for var in &problem.variables {
        bytecodes.push(Bytecode::Load {
            name: var.name.clone(),
            value: var.value,
            desc: var.desc.clone(),
        });
    }

    // Evaluate constraints
    for constraint in &problem.constraints {
        match constraint {
            Constraint::SoundVelocity { depth_m, temp_c, salinity_ppt } => {
                bytecodes.push(Bytecode::SonarSvp {
                    depth_m: *depth_m,
                    temp_c: *temp_c,
                    salinity_ppt: *salinity_ppt,
                });
            }
            Constraint::Absorption { frequency_khz, depth_m, temp_c, salinity_ppt } => {
                bytecodes.push(Bytecode::SonarAbsorption {
                    frequency_khz: *frequency_khz,
                    depth_m: *depth_m,
                    temp_c: *temp_c,
                    salinity_ppt: *salinity_ppt,
                });
            }
            Constraint::TransmissionLoss { range_m, frequency_khz, depth_m, temp_c, salinity_ppt } => {
                bytecodes.push(Bytecode::SonarTl {
                    range_m: *range_m,
                    frequency_khz: *frequency_khz,
                    depth_m: *depth_m,
                    temp_c: *temp_c,
                    salinity_ppt: *salinity_ppt,
                });
            }
            Constraint::ThermalBound { temp_c, min_safe, max_safe } => {
                bytecodes.push(Bytecode::ThermalBound {
                    temp_c: *temp_c,
                    min_safe: *min_safe,
                    max_safe: *max_safe,
                });
            }
            Constraint::GenericCompare { left, operator, right, desc } => {
                bytecodes.push(Bytecode::GenericCompare {
                    left: *left,
                    operator: operator.clone(),
                    right: *right,
                    desc: desc.clone(),
                });
            }
            Constraint::GenericBound { value, min, max, desc } => {
                bytecodes.push(Bytecode::GenericBound {
                    value: *value,
                    min: *min,
                    max: *max,
                    desc: desc.clone(),
                });
            }
            Constraint::GenericRangeCheck { value, min, max, desc } => {
                bytecodes.push(Bytecode::GenericRangeCheck {
                    value: *value,
                    min: *min,
                    max: *max,
                    desc: desc.clone(),
                });
            }
        }
    }

    // Add assertion
    bytecodes.push(Bytecode::Assert {
        assertion_type: problem.assertion.assertion_type.clone(),
        expected: problem.assertion.expected,
        desc: problem.assertion.actual_expr.clone(),
    });

    bytecodes
}
