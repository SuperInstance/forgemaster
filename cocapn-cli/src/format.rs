//! Output formatters for fleet-standard display.

/// Format a comparison table (markdown)
pub fn comparison_table(headers: &[&str], rows: &[Vec<String>]) -> String {
    let mut out = String::new();
    
    // Header
    out.push_str(&format!("| {} |\n", headers.join(" | ")));
    out.push_str(&format!("|{}|\n", headers.iter().map(|_| "---".to_string()).collect::<Vec<_>>().join("|")));
    
    // Rows
    for row in rows {
        out.push_str(&format!("| {} |\n", row.join(" | ")));
    }
    
    out
}

/// Format a Safe-TOPS/W comparison table
pub fn safe_tops_w_table() -> String {
    let headers = &["Chip", "Raw TOPS/W", "S Factor", "Pass Rate", "Power OH", "Safe-TOPS/W"];
    let rows = vec![
        vec!["FLUX-LUCID".into(), "24.0".into(), "1.0".into(), "0.9999999".into(), "1.19x".into(), "**20.17**".into()],
        vec!["Jetson Orin AGX".into(), "5.7".into(), "0.0".into(), "0.0".into(), "1.0x".into(), "**0.00**".into()],
        vec!["Hailo-8 Safety".into(), "9.7".into(), "0.72".into(), "0.99981".into(), "1.32x".into(), "**5.29**".into()],
        vec!["Groq LPU".into(), "21.4".into(), "0.0".into(), "0.0".into(), "1.0x".into(), "**0.00**".into()],
        vec!["Google TPU v5e".into(), "28.8".into(), "0.0".into(), "0.0".into(), "1.0x".into(), "**0.00**".into()],
        vec!["Mobileye EyeQ6H".into(), "7.2".into(), "0.88".into(), "0.99997".into(), "1.27x".into(), "**4.99**".into()],
    ];
    comparison_table(headers, &rows)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_comparison_table() {
        let t = comparison_table(&["A", "B"], &vec![vec!["1".into(), "2".into()]]);
        assert!(t.contains("| A | B |"));
        assert!(t.contains("|---|---|"));
    }

    #[test]
    fn test_safe_tops_w_table() {
        let t = safe_tops_w_table();
        assert!(t.contains("FLUX-LUCID"));
        assert!(t.contains("20.17"));
    }
}
