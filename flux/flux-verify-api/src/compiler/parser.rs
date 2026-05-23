/// Shared parsing utilities for extracting numbers and patterns from natural language.

/// Extract a number that appears immediately before the given keyword.
pub fn extract_number_before(text: &str, keyword: &str) -> Option<f64> {
    let idx = text.find(keyword)?;
    let prefix = &text[..idx];
    let num_str = prefix
        .rsplit(|c: char| !c.is_ascii_digit() && c != '.' && c != '-')
        .next()?;
    num_str.parse().ok()
}

/// Extract a number near a keyword (within 30 chars before it).
pub fn extract_number_near(text: &str, keyword: &str) -> Option<f64> {
    let idx = text.find(keyword)?;
    let start = if idx > 30 { idx - 30 } else { 0 };
    let window = &text[start..idx];
    // Find the last number in the window
    let parts: Vec<&str> = window.split(|c: char| !c.is_ascii_digit() && c != '.' && c != '-')
        .filter(|s| !s.is_empty())
        .collect();
    parts.last().and_then(|s| s.parse().ok())
}

/// Extract a number with a unit suffix (e.g., "50khz", "200hz").
pub fn extract_number_with_unit<'a>(text: &str, units: &[&'a str]) -> Option<f64> {
    for unit in units {
        for part in text.split_whitespace() {
            if part.ends_with(unit) {
                let num_str = &part[..part.len() - unit.len()];
                if let Ok(v) = num_str.parse() {
                    return Some(v);
                }
            }
        }
    }
    None
}

/// Extract a range from patterns like "X to Y", "between X and Y".
pub fn extract_range(text: &str) -> Option<(f64, f64)> {
    // Pattern: "between X and Y" or "range of X to Y" or "X to Y"
    if let Some(rest) = text.strip_prefix("between ") {
        let parts: Vec<&str> = rest.split(" and ").collect();
        if parts.len() == 2 {
            let a = parts[0].trim().parse::<f64>().ok()?;
            let b = parts[1].split_whitespace().next()?.parse::<f64>().ok()?;
            return Some((a.min(b), a.max(b)));
        }
    }

    // Look for "safe range" or "range of X to Y" or "from X to Y"
    // First try: extract numbers around "to" after "range" or "safe range"
    if let Some(idx) = text.find("safe range") {
        let rest = &text[idx + 10..];
        // Remove non-numeric noise like degree symbols
        let clean = rest.replace("°c", " ").replace("°", " ").replace("celsius", " ");
        if let Some(range) = extract_range_from_text(clean.trim()) {
            return Some(range);
        }
    }
    if let Some(idx) = text.find("range of ") {
        let rest = &text[idx + 9..];
        let clean = rest.replace("°c", " ").replace("°", " ").replace("celsius", " ");
        if let Some(range) = extract_range_from_text(clean.trim()) {
            return Some(range);
        }
    }

    for pattern in &["from "] {
        if let Some(idx) = text.find(pattern) {
            let rest = &text[idx + pattern.len()..];
            let parts: Vec<&str> = rest.split(" to ").collect();
            if parts.len() >= 2 {
                let a = parts[0].trim().parse::<f64>().ok()?;
                let b = parts[1].split_whitespace().next()?.parse::<f64>().ok()?;
                return Some((a.min(b), a.max(b)));
            }
        }
    }

    None
}

fn extract_range_from_text(text: &str) -> Option<(f64, f64)> {
    let parts: Vec<&str> = text.split(" to ").collect();
    if parts.len() >= 2 {
        let a = parts[0].trim().parse::<f64>().ok()?;
        let b = parts[1].split(|c: char| !c.is_ascii_digit() && c != '.' && c != '-')
            .next()?
            .parse::<f64>()
            .ok()?;
        return Some((a.min(b), a.max(b)));
    }
    // Try "X - Y" with spaces around dash
    let parts: Vec<&str> = text.split(" - ").collect();
    if parts.len() >= 2 {
        let a = parts[0].trim().parse::<f64>().ok()?;
        let b = parts[1].split(|c: char| !c.is_ascii_digit() && c != '.' && c != '-')
            .next()?
            .parse::<f64>()
            .ok()?;
        return Some((a.min(b), a.max(b)));
    }
    None
}

/// Extract a comparison: "X is greater than Y", "X > Y", "X is at least Y"
pub fn extract_comparison(text: &str) -> Option<(f64, String, f64, String)> {
    // Direct operator: "X > Y", "X >= Y", "X < Y", "X <= Y", "X == Y"
    for op in &[">=", "<=", ">", "<", "==", "="] {
        if let Some(idx) = text.find(op) {
            let left_str = text[..idx].trim();
            let right_str = text[idx + op.len()..].trim();
            let left = left_str.split_whitespace().last()?.parse::<f64>().ok()?;
            let right = right_str.split_whitespace().next()?.parse::<f64>().ok()?;
            let op_name = match *op {
                ">=" => "gte",
                "<=" => "lte",
                ">" => "gt",
                "<" => "lt",
                "==" | "=" => "eq",
                _ => "gt",
            };
            return Some((left, op_name.to_string(), right, text.to_string()));
        }
    }

    // Natural language: "X is greater than Y", "X is at least Y", etc.
    let patterns = [
        ("greater than or equal to", "gte"),
        ("less than or equal to", "lte"),
        ("at least", "gte"),
        ("at most", "lte"),
        ("greater than", "gt"),
        ("less than", "lt"),
        ("equal to", "eq"),
        ("equals", "eq"),
        ("is above", "gt"),
        ("is below", "lt"),
    ];

    for (phrase, op) in &patterns {
        if let Some(idx) = text.find(phrase) {
            let left_str = text[..idx].trim();
            let right_str = text[idx + phrase.len()..].trim();
            // Try to extract numbers
            let left = extract_trailing_number(left_str)?;
            let right = extract_leading_number(right_str)?;
            return Some((left, op.to_string(), right, text.to_string()));
        }
    }

    None
}

fn extract_trailing_number(text: &str) -> Option<f64> {
    let parts: Vec<&str> = text.split(|c: char| !c.is_ascii_digit() && c != '.' && c != '-')
        .filter(|s| !s.is_empty())
        .collect();
    parts.last().and_then(|s| s.parse().ok())
}

fn extract_leading_number(text: &str) -> Option<f64> {
    let parts: Vec<&str> = text.split(|c: char| !c.is_ascii_digit() && c != '.' && c != '-')
        .filter(|s| !s.is_empty())
        .collect();
    parts.first().and_then(|s| s.parse().ok())
}

/// Extract a range check: "X is between Y and Z"
pub fn extract_range_check(text: &str) -> Option<(f64, f64, f64, String)> {
    if let Some(idx) = text.find("between ") {
        let rest = &text[idx + 8..];
        let parts: Vec<&str> = rest.split(" and ").collect();
        if parts.len() >= 2 {
            let min = parts[0].trim().parse::<f64>().ok()?;
            let right = parts[1].split_whitespace().collect::<Vec<_>>();
            let max = right.get(0)?.parse::<f64>().ok()?;
            // Find the value being checked — look before "between"
            let prefix = &text[..idx];
            let value = extract_trailing_number(prefix)?;
            return Some((value, min, max, text.to_string()));
        }
    }
    // "X is within [Y, Z]" or "X is in [Y, Z]"
    for phrase in &["within ", "in "] {
        if let Some(idx) = text.find(phrase) {
            let rest = &text[idx + phrase.len()..];
            let clean = rest.trim_start_matches(|c| c == '[' || c == '(');
            let parts: Vec<&str> = clean.split(|c| c == ',' || c == ']').collect();
            if parts.len() >= 2 {
                let min = parts[0].trim().parse::<f64>().ok()?;
                let max = parts[1].trim().parse::<f64>().ok()?;
                let prefix = &text[..idx];
                let value = extract_trailing_number(prefix)?;
                return Some((value, min, max, text.to_string()));
            }
        }
    }
    None
}

/// Extract a bound: "X is within Y of Z" → (X, Z-Y, Z+Y)
pub fn extract_bound(text: &str) -> Option<(f64, f64, f64, String)> {
    if let Some(idx) = text.find("within ") {
        let rest = &text[idx + 7..];
        let parts: Vec<&str> = rest.split(" of ").collect();
        if parts.len() >= 2 {
            let tolerance = parts[0].trim().parse::<f64>().ok()?;
            let center = extract_leading_number(parts[1])?;
            let prefix = &text[..idx];
            let value = extract_trailing_number(prefix)?;
            return Some((value, center - tolerance, center + tolerance, text.to_string()));
        }
    }
    None
}
