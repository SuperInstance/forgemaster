use super::{parser, ConstraintProblem};

/// Sonar domain parser.
/// Extracts sonar parameters from natural language and builds a constraint problem.
pub fn parse(claim: &str) -> Result<ConstraintProblem, String> {
    let lower = claim.to_lowercase();

    // Extract frequency (kHz or Hz)
    let frequency_hz = parser::extract_number_with_unit(&lower, &["khz", "hz"])
        .or_else(|| parser::extract_number_before(&lower, "khz").map(|f| f * 1000.0))
        .or_else(|| parser::extract_number_before(&lower, "hz"))
        .ok_or("Could not extract frequency from claim")?;

    // Normalize to Hz
    let freq_normalized = if lower.contains("khz") && frequency_hz < 1000.0 {
        frequency_hz * 1000.0
    } else {
        frequency_hz
    };

    // Extract depth
    let depth_m = parser::extract_number_before(&lower, "m depth")
        .or_else(|| parser::extract_number_before(&lower, "meters depth"))
        .or_else(|| parser::extract_number_before(&lower, "depth"))
        .or_else(|| parser::extract_number_near(&lower, "depth"))
        .ok_or("Could not extract depth from claim")?;

    // Extract range/distance
    let range_m = parser::extract_number_before(&lower, "km")
        .map(|km| km * 1000.0)
        .or_else(|| parser::extract_number_before(&lower, "range"))
        .or_else(|| parser::extract_number_near(&lower, "range"))
        .ok_or("Could not extract range from claim")?;

    // Extract target strength (optional, default -10 dB)
    let target_strength_db = parser::extract_number_before(&lower, "db target")
        .or_else(|| parser::extract_number_near(&lower, "target"))
        .unwrap_or(10.0); // default 10 dB target strength

    // Environmental defaults
    let temp_c = parser::extract_number_near(&lower, "temperature").unwrap_or(15.0);
    let salinity_ppt = parser::extract_number_near(&lower, "salinity").unwrap_or(35.0);

    let frequency_khz = freq_normalized / 1000.0;

    Ok(ConstraintProblem {
        domain: "sonar".into(),
        variables: vec![
            super::Variable {
                name: "depth_m".into(),
                value: depth_m,
                desc: "depth (m)".into(),
            },
            super::Variable {
                name: "frequency_hz".into(),
                value: freq_normalized,
                desc: "frequency (Hz)".into(),
            },
            super::Variable {
                name: "range_m".into(),
                value: range_m,
                desc: "range (m)".into(),
            },
            super::Variable {
                name: "target_strength_db".into(),
                value: target_strength_db,
                desc: "target strength (dB)".into(),
            },
        ],
        constraints: vec![
            super::Constraint::SoundVelocity {
                depth_m,
                temp_c,
                salinity_ppt,
            },
            super::Constraint::Absorption {
                frequency_khz,
                depth_m,
                temp_c,
                salinity_ppt,
            },
            super::Constraint::TransmissionLoss {
                range_m,
                frequency_khz,
                depth_m,
                temp_c,
                salinity_ppt,
            },
        ],
        assertion: super::Assertion {
            assertion_type: "gt".into(),
            expected: 0.0,
            actual_expr: "signal excess (dB)".into(),
        },
    })
}
