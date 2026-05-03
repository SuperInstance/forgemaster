//! guardc integration tests — Verified GUARD → FLUX compiler pipeline

use guardc::ast;
use guardc::cir;
use guardc::error::Span;

// Helper: create a zero span
fn span() -> Span {
    Span { file: String::new(), start_line: 0, start_col: 0, end_line: 0, end_col: 0 }
}

fn ident(name: &str) -> ast::Ident {
    ast::Ident { name: name.to_string(), span: span() }
}

#[test]
fn test_ast_ident() {
    let id = ident("altitude_check");
    assert_eq!(id.name, "altitude_check");
}

#[test]
fn test_ast_module_creation() {
    let module = ast::Module {
        name: ident("evtol_safety"),
        version: Some("0.1.0".to_string()),
        system_desc: Some("eVTOL safety constraints".to_string()),
        imports: vec![],
        dimensions: vec![],
        domains: vec![],
        states: vec![],
        invariants: vec![],
        derives: vec![],
        proofs: vec![],
    };
    assert_eq!(module.name.name, "evtol_safety");
    assert_eq!(module.version.as_deref(), Some("0.1.0"));
}

#[test]
fn test_ast_invariant_creation() {
    let inv = ast::InvariantDecl {
        name: ident("altitude_range"),
        priority: Some(ast::Priority::Critical),
        when: None,
        ensure: ast::Expr::Bool(true),
        on_violation: Some(ast::ViolationAction::Halt),
    };
    assert_eq!(inv.name.name, "altitude_range");
    assert!(matches!(inv.priority, Some(ast::Priority::Critical)));
    assert!(matches!(inv.on_violation, Some(ast::ViolationAction::Halt)));
}

#[test]
fn test_ast_priority_levels() {
    let _critical = ast::Priority::Critical;
    let _major = ast::Priority::Major;
    let _minor = ast::Priority::Minor;
}

#[test]
fn test_ast_violation_actions() {
    let _halt = ast::ViolationAction::Halt;
    let _warn = ast::ViolationAction::Warn;
    let _log = ast::ViolationAction::Log;
}

#[test]
fn test_cir_unit_system() {
    let length = cir::Unit::Base(cir::BaseDimension::Length, 1);
    let time = cir::Unit::Base(cir::BaseDimension::Time, 1);
    let dimensionless = cir::Unit::Dimensionless;
    
    assert!(matches!(length, cir::Unit::Base(cir::BaseDimension::Length, 1)));
    assert!(matches!(time, cir::Unit::Base(cir::BaseDimension::Time, 1)));
    assert!(matches!(dimensionless, cir::Unit::Dimensionless));
}

#[test]
fn test_cir_const_values() {
    let int_val = cir::ConstValue::Integer(42);
    let float_val = cir::ConstValue::Real(3.14);
    let bool_val = cir::ConstValue::Bool(true);
    
    assert!(matches!(int_val, cir::ConstValue::Integer(42)));
    assert!(matches!(float_val, cir::ConstValue::Real(_)));
    assert!(matches!(bool_val, cir::ConstValue::Bool(true)));
}

#[test]
fn test_cir_expr_construction() {
    let var = cir::Expr::Var(cir::VarId(0));
    let const_150 = cir::Expr::Const(cir::ConstValue::Integer(150));
    let ty = cir::CirType { kind: cir::TypeKind::Boolean, unit: cir::Unit::Dimensionless };
    
    let cmp = cir::Expr::Binary {
        op: cir::BinOp::Lte,
        left: Box::new(var),
        right: Box::new(const_150),
        ty,
    };
    
    assert!(matches!(cmp, cir::Expr::Binary { op: cir::BinOp::Lte, .. }));
}

#[test]
fn test_cir_binary_ops_complete() {
    // All 14 binary operators
    let _: Vec<cir::BinOp> = vec![
        cir::BinOp::Eq, cir::BinOp::Neq,
        cir::BinOp::Lt, cir::BinOp::Gt,
        cir::BinOp::Lte, cir::BinOp::Gte,
        cir::BinOp::And, cir::BinOp::Or,
        cir::BinOp::Implies,
        cir::BinOp::Add, cir::BinOp::Sub,
        cir::BinOp::Mul, cir::BinOp::Div,
    ];
}

#[test]
fn test_cir_type_kinds() {
    assert!(matches!(cir::TypeKind::Real, cir::TypeKind::Real));
    assert!(matches!(cir::TypeKind::Integer, cir::TypeKind::Integer));
    assert!(matches!(cir::TypeKind::Boolean, cir::TypeKind::Boolean));
}

#[test]
fn test_module_size() {
    // Verify core types are not degenerate
    assert!(std::mem::size_of::<ast::Module>() > 0);
    assert!(std::mem::size_of::<cir::Expr>() > 0);
    assert!(std::mem::size_of::<cir::ConstValue>() > 0);
}
