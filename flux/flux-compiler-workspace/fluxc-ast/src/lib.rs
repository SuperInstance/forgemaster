use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Ident(pub String);

impl fmt::Display for Ident {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Expr {
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
    And(Box<Expr>, Box<Expr>),
    Or(Box<Expr>, Box<Expr>),
    Not(Box<Expr>),
}

impl Expr {
    pub fn range(name: impl Into<String>, lo: u64, hi: u64) -> Self {
        Self::Range {
            name: Ident(name.into()),
            lo,
            hi,
        }
    }

    pub fn domain(name: impl Into<String>, mask: u64) -> Self {
        Self::Domain {
            name: Ident(name.into()),
            mask,
        }
    }

    pub fn exact(name: impl Into<String>, val: u64) -> Self {
        Self::Exact {
            name: Ident(name.into()),
            val,
        }
    }

    pub fn and(lhs: Self, rhs: Self) -> Self {
        Self::And(Box::new(lhs), Box::new(rhs))
    }

    pub fn or(lhs: Self, rhs: Self) -> Self {
        Self::Or(Box::new(lhs), Box::new(rhs))
    }

    pub fn not(inner: Self) -> Self {
        Self::Not(Box::new(inner))
    }
}
