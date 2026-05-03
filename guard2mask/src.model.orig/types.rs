use hashbrown::HashMap;
use std::fmt;

// ------------------------------
// Ternary Weight (Core Variable Type)
// ------------------------------
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum TernaryWeight {
    PlusOne,
    Zero,
    MinusOne,
}

impl TernaryWeight {
    /// Bit position for BitmaskDomain encoding
    pub const fn bit(self) -> u8 {
        match self {
            TernaryWeight::PlusOne => 0,
            TernaryWeight::Zero => 1,
            TernaryWeight::MinusOne => 2,
        }
    }

    /// Bitmask for this value alone
    pub const fn mask(self) -> BitmaskDomain {
        1 << self.bit() as BitmaskDomain
    }

    /// Convert to signed integer for constraint calculations
    pub const fn to_i32(self) -> i32 {
        match self {
            TernaryWeight::PlusOne => 1,
            TernaryWeight::Zero => 0,
            TernaryWeight::MinusOne => -1,
        }
    }
}

impl fmt::Display for TernaryWeight {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TernaryWeight::PlusOne => write!(f, "+1"),
            TernaryWeight::Zero => write!(f, "0"),
            TernaryWeight::MinusOne => write!(f, "-1"),
        }
    }
}

// ------------------------------
// BitmaskDomain (CSP Variable Domain)
// u64 where each bit represents membership of a TernaryWeight
// ------------------------------
pub type BitmaskDomain = u64;

pub const FULL_TERNARY_DOMAIN: BitmaskDomain = 
    TernaryWeight::PlusOne.mask() | TernaryWeight::Zero.mask() | TernaryWeight::MinusOne.mask();

pub trait BitmaskDomainExt {
    /// Check if a TernaryWeight is in the domain
    fn contains(self, value: TernaryWeight) -> bool;
    /// Get all allowed values from the domain
    fn values(self) -> Vec<TernaryWeight>;
    /// Check if domain is empty (no solution)
    fn is_empty(self) -> bool;
    /// Get number of allowed values
    fn len(self) -> u32;
}

impl BitmaskDomainExt for BitmaskDomain {
    fn contains(self, value: TernaryWeight) -> bool {
        (self & value.mask()) != 0
    }

    fn values(self) -> Vec<TernaryWeight> {
        let mut vals = Vec::new();
        if self.contains(TernaryWeight::PlusOne) { vals.push(TernaryWeight::PlusOne); }
        if self.contains(TernaryWeight::Zero) { vals.push(TernaryWeight::Zero); }
        if self.contains(TernaryWeight::MinusOne) { vals.push(TernaryWeight::MinusOne); }
        vals
    }

    fn is_empty(self) -> bool { self == 0 }
    fn len(self) -> u32 { self.count_ones() }
}

// ------------------------------
// Via Pattern (Mask Layout Primitive)
// ------------------------------
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum ViaPolarity {
    Positive, // Maps to TernaryWeight::PlusOne
    Negative, // Maps to TernaryWeight::MinusOne
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ViaPattern {
    pub x: u32,
    pub y: u32,
    pub polarity: ViaPolarity,
}

// ------------------------------
// Constraint (GUARD DSL Safety Constraints)
// ------------------------------
#[derive(Clone, Debug)]
pub enum Scope {
    Global,
    Row(u32),
    Column(u32),
    Region { x0: u32, x1: u32, y0: u32, y1: u32 },
    AllRows,
    AllColumns,
}

#[derive(Clone, Debug)]
pub enum Constraint {
    /// Sum of weights in scope is [min_sum, max_sum]
    Range {
        min_sum: i32,
        max_sum: i32,
        scope: Scope,
    },
    /// Max power dissipation (W) for scope (each non-zero = 1mW)
    Thermal {
        max_power: f32,
        scope: Scope,
    },
    /// Max ratio of non-zero weights (0.0 = all zero, 1.0 = no sparsity)
    Sparsity {
        max_non_zero_ratio: f32,
        scope: Scope,
    },
    /// Custom predicate over variables in scope
    Custom {
        name: String,
        predicate: Box<dyn Fn(&[TernaryWeight]) -> bool + 'static + Clone>,
        scope: Scope,
    },
}

// ------------------------------
// CSP Core Types
// ------------------------------
pub type VarId = (u32, u32); // (x, y) position of weight variable

#[derive(Clone, Debug)]
pub struct CspVariable {
    pub id: VarId,
    pub domain: BitmaskDomain,
}

#[derive(Clone, Debug)]
pub struct ConstraintSystem {
    pub width: u32,
    pub height: u32,
    pub variables: HashMap<VarId, CspVariable>,
    pub constraints: Vec<Constraint>,
}

#[derive(Clone, Debug)]
pub struct Assignment(pub HashMap<VarId, TernaryWeight>);

// ------------------------------
// Error Type
// ------------------------------
#[derive(Debug, thiserror::Error)]
pub enum Guard2MaskError {
    #[error("Parse error: {0}")]
    ParseError(String),
    #[error("CSP error: {0}")]
    CspError(String),
    #[error("No valid assignment found: {0}")]
    NoSolutionError(String),
    #[error("GDSII export error: {0}")]
    GdsExportError(String),
}
