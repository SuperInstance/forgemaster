use fluxc_ast::{Expr, Ident};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Constraint {
    Range {
        name: Ident,
        lo: u64,
        hi: u64,
    },
    Domain {
        name: Ident,
        mask: u64,
    },
    Exact {
        name: Ident,
        val: u64,
    },
    And(Vec<Constraint>),
    Or(Vec<Constraint>),
    Not(Box<Constraint>),
}

pub struct Module {
    pub constraints: Vec<Constraint>,
}

pub fn lower(ast: &Expr) -> Module {
    let mut constraints = Vec::new();
    lower_expr(ast, &mut constraints);
    Module { constraints }
}

fn lower_expr(expr: &Expr, out: &mut Vec<Constraint>) {
    match expr {
        Expr::Range { name, lo, hi } => out.push(Constraint::Range {
            name: name.clone(),
            lo: *lo,
            hi: *hi,
        }),
        Expr::Domain { name, mask } => out.push(Constraint::Domain {
            name: name.clone(),
            mask: *mask,
        }),
        Expr::Exact { name, val } => out.push(Constraint::Exact {
            name: name.clone(),
            val: *val,
        }),
        Expr::And(lhs, rhs) => {
            let mut children = Vec::new();
            lower_expr(lhs, &mut children);
            lower_expr(rhs, &mut children);
            out.push(Constraint::And(children));
        }
        Expr::Or(lhs, rhs) => {
            let mut children = Vec::new();
            lower_expr(lhs, &mut children);
            lower_expr(rhs, &mut children);
            out.push(Constraint::Or(children));
        }
        Expr::Not(inner) => {
            let mut children = Vec::new();
            lower_expr(inner, &mut children);
            if let Some(c) = children.pop() {
                out.push(Constraint::Not(Box::new(c)));
            }
        }
    }
}
