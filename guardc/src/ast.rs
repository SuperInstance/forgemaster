//! Raw AST produced by the GUARD parser.
//!
//! This is a direct representation of the source syntax.  Type checking
//! and unit analysis happen on this tree before lowering to CIR.

use crate::error::Span;

// ---------------------------------------------------------------------------
// Identifiers & Literals
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct Ident {
    pub name: String,
    pub span: Span,
}

#[derive(Debug, Clone, PartialEq)]
pub struct QualifiedId {
    pub parts: Vec<Ident>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Quantity {
    pub value: f64,
    pub unit: String,
    pub span: Span,
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum TypeDesc {
    Real,
    Integer,
    Boolean,
    Enum(QualifiedId),
    Array { low: Quantity, high: Quantity, of: Box<TypeDesc> },
    Record { fields: Vec<Field> },
}

#[derive(Debug, Clone, PartialEq)]
pub struct Field {
    pub name: Ident,
    pub ty: TypeDesc,
    pub domain: Option<DomainRef>,
}

// ---------------------------------------------------------------------------
// Domains
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum DomainBody {
    Enum { variants: Vec<Ident> },
    Interval { low: Quantity, high: Quantity },
    Product { members: Vec<DomainBody> },
}

#[derive(Debug, Clone, PartialEq)]
pub enum DomainRef {
    Named(QualifiedId),
    Inline(DomainBody),
}

// ---------------------------------------------------------------------------
// Expressions
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum Expr {
    Ident(QualifiedId),
    Quantity(Quantity),
    Bool(bool),
    Unary { op: UnaryOp, expr: Box<Expr>, span: Span },
    Binary { op: BinOp, left: Box<Expr>, right: Box<Expr>, span: Span },
    If { cond: Box<Expr>, then_branch: Box<Expr>, else_branch: Box<Expr>, span: Span },
    Call { func: Ident, args: Vec<Expr>, span: Span },
    ArrayIndex { array: Ident, index: Box<Expr>, span: Span },
    FieldAccess { record: Ident, field: Ident, span: Span },
    // Quantified expressions (sugar before lowering)
    Forall { var: Ident, domain: DomainRef, body: Box<Expr>, span: Span },
    Exists { var: Ident, domain: DomainRef, body: Box<Expr>, span: Span },
    // Temporal operators
    Always(Box<Expr>, Span),
    Eventually(Box<Expr>, Span),
    Next(Box<Expr>, Span),
    Until { left: Box<Expr>, right: Box<Expr>, span: Span },
    Since { left: Box<Expr>, right: Box<Expr>, span: Span },
    For { duration: Quantity, body: Box<Expr>, span: Span },
    After { duration: Quantity, body: Box<Expr>, span: Span },
    // Special accessors
    Old(Box<Expr>, Span),
    RateOf(Box<Expr>, Span),
    Delta(Box<Expr>, Span),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum UnaryOp {
    Neg,
    Abs,
    Not,
    Old,
    RateOf,
    Delta,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BinOp {
    // Arithmetic
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    // Comparison
    Eq,
    Neq,
    Lt,
    Gt,
    Lte,
    Gte,
    In,
    // Logic
    And,
    Or,
    Implies,
    Iff,
}

// ---------------------------------------------------------------------------
// Declarations
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct Module {
    pub name: Ident,
    pub version: Option<String>,
    pub system_desc: Option<String>,
    pub imports: Vec<Import>,
    pub dimensions: Vec<DimensionDecl>,
    pub domains: Vec<DomainDecl>,
    pub states: Vec<StateDecl>,
    pub invariants: Vec<InvariantDecl>,
    pub derives: Vec<DeriveDecl>,
    pub proofs: Vec<ProofDecl>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Import {
    pub path: QualifiedId,
    pub alias: Option<Ident>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DimensionDecl {
    pub name: Ident,
    pub base: String, // "real", "integer"
    pub unit_expr: String,
    pub range: Option<(Quantity, Quantity)>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DomainDecl {
    pub name: Ident,
    pub body: DomainBody,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StateDecl {
    pub name: Ident,
    pub ty: TypeDesc,
    pub domain: Option<DomainRef>,
    pub initial: Option<Expr>,
    pub sample_period: Option<Quantity>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
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
    Transition(Ident),
}

#[derive(Debug, Clone, PartialEq)]
pub struct InvariantDecl {
    pub name: Ident,
    pub priority: Option<Priority>,
    pub when: Option<Expr>,
    pub ensure: Expr,
    pub on_violation: Option<ViolationAction>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DeriveDecl {
    pub name: Ident,
    pub premises: Vec<Premise>,
    pub when: Option<Expr>,
    pub conclude: Expr,
    pub proof_obligation: Option<Expr>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Premise {
    Named(Ident),
    Expr(Expr),
}

#[derive(Debug, Clone, PartialEq)]
pub struct ProofDecl {
    pub name: Ident,
    pub steps: Vec<ProofStep>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ProofStep {
    Tactic { name: Ident },
    Lemma { name: Ident, expr: Expr },
    ReduceTo(Ident),
    Certificate(CertConfig),
}

#[derive(Debug, Clone, PartialEq)]
pub struct CertConfig {
    pub format: CertFormat,
    pub include_trace: bool,
    pub include_counterexample: bool,
    pub hash: HashAlgo,
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
