//! Tide bar — progress indicator for long operations.
//! Named for the ocean tide: steady, rhythmic, inevitable.

use std::io::{self, Write};

/// A simple progress bar for fleet operations
pub struct TideBar {
    total: usize,
    current: usize,
    label: String,
}

impl TideBar {
    pub fn new(total: usize, label: &str) -> Self {
        Self { total, current: 0, label: label.to_string() }
    }

    pub fn update(&mut self, delta: usize, detail: &str) {
        self.current = (self.current + delta).min(self.total);
        let pct = if self.total > 0 { self.current * 100 / self.total } else { 100 };
        let filled = pct / 5;
        let empty = 20 - filled;
        let bar: String = "▓".repeat(filled) + &"░".repeat(empty);
        eprint!("\r[{}] {} {}/{} ({}%) | {}", 
            self.label, bar, self.current, self.total, pct, detail);
        io::stderr().flush().ok();
    }

    pub fn finish(&mut self) {
        eprintln!();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tide_bar_create() {
        let bar = TideBar::new(100, "IMPORT");
        assert_eq!(bar.total, 100);
        assert_eq!(bar.current, 0);
    }
}
