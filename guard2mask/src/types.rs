//! Core types for GUARD DSL and mask compilation.

use std::collections::HashMap;

/// Ternary weight values: -1, 0, +1
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TernaryWeight {
    Neg,
    Zero,
    Pos,
}

/// A GUARD constraint definition
#[derive(Debug, Clone, PartialEq)]
pub struct Constraint {
    pub name: String,
    pub priority: Priority,
    pub checks: Vec<Check>,
}

/// Constraint priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Priority {
    Hard,
    Soft,
    Default,
}

/// Individual constraint checks
#[derive(Debug, Clone, PartialEq)]
pub enum Check {
    Range { var: String, min: i64, max: i64 },
    Whitelist { var: String, values: Vec<i64> },
    Bitmask { var: String, mask: u64 },
    Thermal { budget_w: f64 },
    Sparsity { min_count: usize },
}

/// CSP variable assignment
#[derive(Debug, Clone, Default)]
pub struct Assignment {
    pub values: HashMap<String, TernaryWeight>,
}

impl Assignment {
    pub fn new() -> Self {
        Self::default()
    }
}

/// Via pattern for GDSII output
#[derive(Debug, Clone, PartialEq)]
pub struct ViaPattern {
    pub x: i64,
    pub y: i64,
    pub layer: u32,
    pub width: u64,
    pub height: u64,
}

/// GDSII output structure
#[derive(Debug, Clone, Default)]
pub struct GDSIIOutput {
    pub patterns: Vec<ViaPattern>,
    pub metadata: HashMap<String, String>,
}

impl GDSIIOutput {
    pub fn new() -> Self {
        Self::default()
    }
}
