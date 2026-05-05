//! Fleet color palette — bioluminescent terminal aesthetic.

/// Fleet color constants (ANSI escape codes)
pub mod colors {
    pub const CYAN: &str = "\x1b[36m";
    pub const MAGENTA: &str = "\x1b[35m";
    pub const AMBER: &str = "\x1b[33m";
    pub const RED: &str = "\x1b[31m";
    pub const GREEN: &str = "\x1b[32m";
    pub const DIM: &str = "\x1b[2m";
    pub const BOLD: &str = "\x1b[1m";
    pub const RESET: &str = "\x1b[0m";
}

/// Fleet tag format: `[TAG  ]` with consistent 6-char width
pub fn tag(label: &str) -> String {
    format!("\x1b[36m[{:6}]\x1b[0m", label.to_uppercase())
}

/// Standard tags for fleet operations
pub mod tags {
    use super::tag;
    pub fn plato() -> String { tag("plato") }
    pub fn valid() -> String { tag("valid") }
    pub fn ask() -> String { tag("ask") }
    pub fn rank() -> String { tag("rank") }
    pub fn import() -> String { tag("import") }
    pub fn flux() -> String { tag("flux") }
    pub fn guard() -> String { tag("guard") }
    pub fn deploy() -> String { tag("deploy") }
    pub fn certify() -> String { tag("cert") }
    pub fn error() -> String { tag("error") }
    pub fn warn() -> String { tag("warn") }
}

/// Format a progress line: `[TAG] ████████░░ 60% | detail`
pub fn progress(tag_str: &str, current: usize, total: usize, detail: &str) -> String {
    let pct = if total > 0 { current * 100 / total } else { 100 };
    let filled = pct / 5;
    let empty = 20 - filled;
    let bar: String = "█".repeat(filled) + &"░".repeat(empty);
    format!("{} {} {}% | {}", tag_str, bar, pct, detail)
}

/// Format a health status line: `│ Label │ value │ status │`
pub fn health_line(label: &str, value: &str, ok: bool) -> String {
    let status = if ok { "✅" } else { "🔴" };
    format!("│ {:18} │ {:10} │ {} │", label, value, status)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tag_format() {
        let t = tag("plato");
        assert!(t.contains("PLATO"));
    }

    #[test]
    fn test_progress() {
        let p = progress("[PLATO]", 50, 100, "test");
        assert!(p.contains("50%"));
        assert!(p.contains("test"));
    }

    #[test]
    fn test_health_line() {
        let h = health_line("Tests", "26", true);
        assert!(h.contains("✅"));
    }
}
