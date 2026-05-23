use fluxc_ast::Expr;
use fluxc_codegen::{codegen, WasmTarget};
use fluxc_ir::lower;
use fluxc_parser::parse;

#[test]
fn test_end_to_end() -> Result<(), Box<dyn std::error::Error>> {
    let input = "x in [0, 100] AND y == 42 OR NOT z in domain 0xFF";
    let ast = parse(input)?;
    assert!(matches!(&ast, Expr::Or(_, _)));
    let ir = lower(&ast);
    assert!(!ir.constraints.is_empty());
    let code = codegen(&ir, &WasmTarget)?;
    assert!(code.contains("module"));
    Ok(())
}
