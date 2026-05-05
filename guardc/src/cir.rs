//! Constraint IR (CIR) — the first high-level intermediate representation.
//!
//! CIR retains relational, quantified, and temporal structure.  It is the
//! output of type-checking and the input to lowering.

use crate::error::{GuardError, Result, Span};
use indexmap::IndexMap;
use std::fmt;

// ---------------------------------------------------------------------------
// Units & Types
// ---------------------------------------------------------------------------

/// A physical unit expressed as a rational power-product of base dimensions.
/// Examples:
///   - `m·s⁻²`   → `Length¹ · Time⁻²`
///   - `%`       → `Dimensionless`
///   - `kg·m/s`  → `Mass¹ · Length¹ · Time⁻¹`
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Unit {
    Dimensionless,
    Base(BaseDimension, i32), // dimension and exponent
    Product(Vec<(BaseDimension, i32)>),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BaseDimension {
    Length,
    Mass,
    Time,
    Temperature,
    Angle,
    Current,
    Amount,
}

impl BaseDimension {
    pub fn as_str(&self) -> &'static str {
        match self {
            BaseDimension::Length => "m",
            BaseDimension::Mass => "kg",
            BaseDimension::Time => "s",
            BaseDimension::Temperature => "K",
            BaseDimension::Angle => "rad",
            BaseDimension::Current => "A",
            BaseDimension::Amount => "mol",
        }
    }
}

impl Unit {
    /// Normalize a unit to canonical form (sorted, combined exponents).
    pub fn normalize(&self) -> Unit {
        match self {
            Unit::Dimensionless => Unit::Dimensionless,
            Unit::Base(d, e) => Unit::Product(vec![(*d, *e)]),
            Unit::Product(terms) => {
                let mut map: IndexMap<BaseDimension, i32> = IndexMap::new();
                for (d, e) in terms {
                    *map.entry(*d).or_insert(0) += e;
                }
                let mut pairs: Vec<_> = map.into_iter().filter(|(_, e)| *e != 0).collect();
                pairs.sort_by_key(|(d, _)| *d as u8);
                if pairs.is_empty() {
                    Unit::Dimensionless
                } else if pairs.len() == 1 {
                    Unit::Base(pairs[0].0, pairs[0].1)
                } else {
                    Unit::Product(pairs)
                }
            }
        }
    }

    /// Multiply two units.
    pub fn mul(&self, other: &Unit) -> Unit {
        let mut terms = self.to_terms();
        terms.extend(other.to_terms());
        Unit::Product(terms).normalize()
    }

    /// Divide two units.
    pub fn div(&self, other: &Unit) -> Unit {
        let mut terms = self.to_terms();
        for (d, e) in other.to_terms() {
            terms.push((d, -e));
        }
        Unit::Product(terms).normalize()
    }

    fn to_terms(&self) -> Vec<(BaseDimension, i32)> {
        match self.normalize() {
            Unit::Dimensionless => vec![],
            Unit::Base(d, e) => vec![(d, e)],
            Unit::Product(v) => v,
        }
    }
}

impl fmt::Display for Unit {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.normalize() {
            Unit::Dimensionless => write!(f, "1"),
            Unit::Base(d, 1) => write!(f, "{}", d.as_str()),
            Unit::Base(d, e) => write!(f, "{}^{}", d.as_str(), e),
            Unit::Product(terms) => {
                let parts: Vec<String> = terms
                    .iter()
                    .map(|(d, e)| {
                        if *e == 1 {
                            d.as_str().to_string()
                        } else {
                            format!("{}^{}", d.as_str(), e)
                        }
                    })
                    .collect();
                write!(f, "{}", parts.join("·"))
            }
        }
    }
}

/// CIR types carry both a value kind and a unit.
#[derive(Debug, Clone, PartialEq)]
pub struct CirType {
    pub kind: TypeKind,
    pub unit: Unit,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TypeKind {
    Real,
    Integer,
    Boolean,
    Enum(Vec<String>),
    Array { size: usize, elem: Box<TypeKind> },
    Record { fields: IndexMap<String, TypeKind> },
}

// ---------------------------------------------------------------------------
// Variables & Constants
// ---------------------------------------------------------------------------

/// A unique identifier for a CIR variable.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct VarId(pub u32);

/// A unique identifier for a temporal history buffer.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct BufferId(pub u32);

// ---------------------------------------------------------------------------
// CIR Expressions
// ---------------------------------------------------------------------------

/// CIR expression — fully typed, with explicit temporal and quantified nodes.
#[derive(Debug, Clone, PartialEq)]
pub enum Expr {
    Const(ConstValue),
    Var(VarId),
    Unary { op: UnOp, operand: Box<Expr>, ty: CirType },
    Binary { op: BinOp, left: Box<Expr>, right: Box<Expr>, ty: CirType },
    If { cond: Box<Expr>, then_branch: Box<Expr>, else_branch: Box<Expr>, ty: CirType },
    // Array / record access
    Index { array: VarId, index: Box<Expr>, ty: CirType },
    Field { record: VarId, field: String, ty: CirType },
    // Quantified (retained in CIR; eliminated in lowering)
    Forall { var: VarId, domain: Domain, body: Box<Expr>, ty: CirType },
    Exists { var: VarId, domain: Domain, body: Box<Expr>, ty: CirType },
    // Temporal (retained in CIR; expanded to buffer ops in lowering)
    Always(Box<Expr>, CirType),
    Eventually(Box<Expr>, CirType),
    Next(Box<Expr>, CirType),
    Until { left: Box<Expr>, right: Box<Expr>, ty: CirType },
    Since { left: Box<Expr>, right: Box<Expr>, ty: CirType },
    For { duration: usize, body: Box<Expr>, ty: CirType }, // duration in samples
    After { duration: usize, body: Box<Expr>, ty: CirType },
    Old(VarId, CirType),
    RateOf(VarId, CirType), // derivative: (x - old x) / dt
    Delta(VarId, CirType),  // x - old x
}

#[derive(Debug, Clone, PartialEq)]
pub enum ConstValue {
    Real(f64),
    Integer(i64),
    Bool(bool),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum UnOp {
    Neg,
    Abs,
    Not,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Eq,
    Neq,
    Lt,
    Gt,
    Lte,
    Gte,
    And,
    Or,
    Implies,
}

/// A finite domain for quantifier expansion.
#[derive(Debug, Clone, PartialEq)]
pub enum Domain {
    Enum(Vec<String>),
    Interval { low: i64, high: i64 },
    Array { size: usize },
}

impl Expr {
    /// Return the type of this expression.
    pub fn ty(&self) -> &CirType {
        match self {
            Expr::Const(c) => match c {
                ConstValue::Real(_) => {
                    static TY: CirType = CirType {
                        kind: TypeKind::Real,
                        unit: Unit::Dimensionless,
                    };
                    &TY
                }
                ConstValue::Integer(_) => {
                    static TY: CirType = CirType {
                        kind: TypeKind::Integer,
                        unit: Unit::Dimensionless,
                    };
                    &TY
                }
                ConstValue::Bool(_) => {
                    static TY: CirType = CirType {
                        kind: TypeKind::Boolean,
                        unit: Unit::Dimensionless,
                    };
                    &TY
                }
            },
            Expr::Var(_) => panic!("Var type must be looked up in symbol table"),
            Expr::Unary { ty, .. } => ty,
            Expr::Binary { ty, .. } => ty,
            Expr::If { ty, .. } => ty,
            Expr::Index { ty, .. } => ty,
            Expr::Field { ty, .. } => ty,
            Expr::Forall { ty, .. } => ty,
            Expr::Exists { ty, .. } => ty,
            Expr::Always(_, ty) => ty,
            Expr::Eventually(_, ty) => ty,
            Expr::Next(_, ty) => ty,
            Expr::Until { ty, .. } => ty,
            Expr::Since { ty, .. } => ty,
            Expr::For { ty, .. } => ty,
            Expr::After { ty, .. } => ty,
            Expr::Old(_, ty) => ty,
            Expr::RateOf(_, ty) => ty,
            Expr::Delta(_, ty) => ty,
        }
    }

    /// Check that this expression is boolean (for use in invariants).
    pub fn expect_bool(&self) -> Result<()> {
        let ty = self.ty();
        if !matches!(ty.kind, TypeKind::Boolean) {
            return Err(GuardError::Type {
                span: Span::new("<cir>", 0, 0),
                message: format!(
                    "expected boolean expression, got {:?}",
                    ty.kind
                ),
            });
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// CIR Module
// ---------------------------------------------------------------------------

/// A complete CIR module, ready for lowering.
#[derive(Debug, Clone, PartialEq)]
pub struct CirModule {
    pub name: String,
    pub version: String,
    pub sample_period_ms: f64,
    pub symbol_table: SymbolTable,
    pub invariants: Vec<CirInvariant>,
    pub derived: Vec<CirDerived>,
    pub proof_config: Vec<ProofConfig>,
}

/// Symbol table mapping variable IDs to their metadata.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct SymbolTable {
    pub vars: IndexMap<VarId, VarInfo>,
    pub buffers: IndexMap<BufferId, BufferInfo>,
    next_var: u32,
    next_buffer: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct VarInfo {
    pub name: String,
    pub ty: CirType,
    pub kind: VarKind,
    pub source_span: Span,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum VarKind {
    State,      // Updated by host every cycle
    Constant,   // Pre-loaded at boot
    Temporal,   // History buffer reference
    Local,      // Introduced by lowering
}

#[derive(Debug, Clone, PartialEq)]
pub struct BufferInfo {
    pub name: String,
    pub var: VarId,
    pub depth: usize, // number of historical samples retained
    pub slot_base: u8, // FLUX memory slot for buffer head
}

impl SymbolTable {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn fresh_var(&mut self, name: impl Into<String>, ty: CirType, kind: VarKind, span: Span) -> VarId {
        let id = VarId(self.next_var);
        self.next_var += 1;
        self.vars.insert(
            id,
            VarInfo {
                name: name.into(),
                ty,
                kind,
                source_span: span,
            },
        );
        id
    }

    pub fn fresh_buffer(&mut self, name: impl Into<String>, var: VarId, depth: usize, slot_base: u8) -> BufferId {
        let id = BufferId(self.next_buffer);
        self.next_buffer += 1;
        self.buffers.insert(
            id,
            BufferInfo {
                name: name.into(),
                var,
                depth,
                slot_base,
            },
        );
        id
    }

    pub fn var_info(&self, id: VarId) -> Option<&VarInfo> {
        self.vars.get(&id)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct CirInvariant {
    pub name: String,
    pub priority: Priority,
    pub when: Option<Expr>,   // guard condition
    pub ensure: Expr,         // boolean constraint
    pub on_violation: ViolationAction,
    pub source_span: Span,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Priority {
    Critical,
    Major,
    Minor,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ViolationAction {
    Halt,
    Warn,
    Log,
    Transition(String),
}

#[derive(Debug, Clone, PartialEq)]
pub struct CirDerived {
    pub name: String,
    pub premises: Vec<Expr>,
    pub when: Option<Expr>,
    pub conclude: Expr,
    pub source_span: Span,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ProofConfig {
    pub name: String,
    pub tactics: Vec<String>,
    pub cert_format: CertFormat,
    pub include_trace: bool,
    pub include_counterexample: bool,
    pub hash_algo: HashAlgo,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CertFormat {
    Smt2,
    Lfsc,
    Native,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum HashAlgo {
    Sha256,
    Blake3,
}
