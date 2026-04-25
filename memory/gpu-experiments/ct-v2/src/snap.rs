#[derive(Debug, Clone, PartialEq)]
pub struct SnapReport {
    pub original: (f64, f64, f64),
    pub snapped: (i64, i64, i64),
    pub error: f64,
    pub is_exact: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum SnapError {
    NoTripleFound,
    OutOfBounds,
}
