use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::api::response::TraceEntry;
use crate::compiler::ConstraintProblem;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "opcode")]
pub enum Bytecode {
    #[serde(rename = "LOAD")]
    Load {
        name: String,
        value: f64,
        desc: String,
    },
    #[serde(rename = "SONAR_SVP")]
    SonarSvp {
        depth_m: f64,
        temp_c: f64,
        salinity_ppt: f64,
    },
    #[serde(rename = "SONAR_ABSORPTION")]
    SonarAbsorption {
        frequency_khz: f64,
        depth_m: f64,
        temp_c: f64,
        salinity_ppt: f64,
    },
    #[serde(rename = "SONAR_TL")]
    SonarTl {
        range_m: f64,
        frequency_khz: f64,
        depth_m: f64,
        temp_c: f64,
        salinity_ppt: f64,
    },
    #[serde(rename = "THERMAL_BOUND")]
    ThermalBound {
        temp_c: f64,
        min_safe: f64,
        max_safe: f64,
    },
    #[serde(rename = "GENERIC_COMPARE")]
    GenericCompare {
        left: f64,
        operator: String,
        right: f64,
        desc: String,
    },
    #[serde(rename = "GENERIC_BOUND")]
    GenericBound {
        value: f64,
        min: f64,
        max: f64,
        desc: String,
    },
    #[serde(rename = "GENERIC_RANGE_CHECK")]
    GenericRangeCheck {
        value: f64,
        min: f64,
        max: f64,
        desc: String,
    },
    #[serde(rename = "ASSERT_GT")]
    Assert {
        assertion_type: String,
        expected: f64,
        desc: String,
    },
}

#[derive(Debug, Clone)]
pub struct FluxVm {
    pub registers: HashMap<String, f64>,
    pub sound_velocity: f64,
    pub absorption_db_km: f64,
    pub transmission_loss_db: f64,
    pub signal_excess_db: f64,
    pub last_result: f64,
}

impl Default for FluxVm {
    fn default() -> Self {
        Self::new()
    }
}

impl FluxVm {
    pub fn new() -> Self {
        Self {
            registers: HashMap::new(),
            sound_velocity: 0.0,
            absorption_db_km: 0.0,
            transmission_loss_db: 0.0,
            signal_excess_db: 0.0,
            last_result: 0.0,
        }
    }

    /// Execute a sequence of bytecodes and produce a trace.
    pub fn execute(&mut self, bytecodes: &[Bytecode]) -> Vec<TraceEntry> {
        let mut trace = Vec::new();

        for bc in bytecodes {
            match bc {
                Bytecode::Load { name, value, desc } => {
                    self.registers.insert(name.clone(), *value);
                    self.last_result = *value;
                    trace.push(TraceEntry {
                        opcode: "LOAD".into(),
                        value: Some(*value),
                        result: None,
                        expected: None,
                        actual: None,
                        desc: desc.clone(),
                    });
                }
                Bytecode::SonarSvp {
                    depth_m,
                    temp_c,
                    salinity_ppt,
                } => {
                    let sv = mackenzie_sound_velocity(*depth_m, *temp_c, *salinity_ppt);
                    self.sound_velocity = sv;
                    self.last_result = sv;
                    self.registers.insert("sound_velocity_ms".into(), sv);
                    trace.push(TraceEntry {
                        opcode: "SONAR_SVP".into(),
                        value: None,
                        result: Some(sv),
                        expected: None,
                        actual: None,
                        desc: "sound velocity (Mackenzie 1981)".into(),
                    });
                }
                Bytecode::SonarAbsorption {
                    frequency_khz,
                    depth_m,
                    temp_c,
                    salinity_ppt,
                } => {
                    let abs_db_km = francois_garrison_absorption(
                        *frequency_khz,
                        *depth_m,
                        *temp_c,
                        *salinity_ppt,
                    );
                    self.absorption_db_km = abs_db_km;
                    self.last_result = abs_db_km;
                    self.registers.insert("absorption_db_km".into(), abs_db_km);
                    trace.push(TraceEntry {
                        opcode: "SONAR_ABSORPTION".into(),
                        value: None,
                        result: Some(abs_db_km),
                        expected: None,
                        actual: None,
                        desc: "absorption dB/km (FG 1982)".into(),
                    });
                }
                Bytecode::SonarTl {
                    range_m,
                    frequency_khz,
                    depth_m,
                    temp_c,
                    salinity_ppt,
                } => {
                    let sv = if self.sound_velocity > 0.0 {
                        self.sound_velocity
                    } else {
                        mackenzie_sound_velocity(*depth_m, *temp_c, *salinity_ppt)
                    };
                    let abs_db_km = if self.absorption_db_km > 0.0 {
                        self.absorption_db_km
                    } else {
                        francois_garrison_absorption(
                            *frequency_khz,
                            *depth_m,
                            *temp_c,
                            *salinity_ppt,
                        )
                    };
                    let tl = transmission_loss(*range_m, sv, abs_db_km);
                    self.transmission_loss_db = tl;
                    self.last_result = tl;
                    self.registers.insert("transmission_loss_db".into(), tl);
                    trace.push(TraceEntry {
                        opcode: "SONAR_TL".into(),
                        value: None,
                        result: Some(tl),
                        expected: None,
                        actual: None,
                        desc: "transmission loss (dB)".into(),
                    });
                }
                Bytecode::ThermalBound {
                    temp_c,
                    min_safe,
                    max_safe,
                } => {
                    let in_range = *temp_c >= *min_safe && *temp_c <= *max_safe;
                    let margin = if *temp_c < *min_safe {
                        *temp_c - *min_safe
                    } else if *temp_c > *max_safe {
                        *temp_c - *max_safe
                    } else {
                        (*temp_c - *min_safe).min(*max_safe - *temp_c)
                    };
                    self.last_result = margin;
                    self.registers.insert("thermal_margin".into(), margin);
                    trace.push(TraceEntry {
                        opcode: "THERMAL_BOUND".into(),
                        value: Some(*temp_c),
                        result: Some(margin),
                        expected: None,
                        actual: Some(if in_range { 1.0 } else { 0.0 }),
                        desc: format!("temp {}°C vs safe [{}, {}]", temp_c, min_safe, max_safe),
                    });
                }
                Bytecode::GenericCompare {
                    left,
                    operator,
                    right,
                    desc,
                } => {
                    let result = match operator.as_str() {
                        "gt" => left > right,
                        "gte" => left >= right,
                        "lt" => left < right,
                        "lte" => left <= right,
                        "eq" => (left - right).abs() < f64::EPSILON,
                        _ => false,
                    };
                    let actual = left - right;
                    self.last_result = actual;
                    trace.push(TraceEntry {
                        opcode: "GENERIC_COMPARE".into(),
                        value: Some(*left),
                        result: Some(if result { 1.0 } else { 0.0 }),
                        expected: Some(*right),
                        actual: Some(actual),
                        desc: desc.clone(),
                    });
                }
                Bytecode::GenericBound {
                    value,
                    min,
                    max,
                    desc,
                } => {
                    let in_range = *value >= *min && *value <= *max;
                    let margin = if in_range {
                        (*value - *min).min(*max - *value)
                    } else if *value < *min {
                        *value - *min
                    } else {
                        *value - *max
                    };
                    self.last_result = margin;
                    trace.push(TraceEntry {
                        opcode: "GENERIC_BOUND".into(),
                        value: Some(*value),
                        result: Some(margin),
                        expected: None,
                        actual: Some(if in_range { 1.0 } else { 0.0 }),
                        desc: desc.clone(),
                    });
                }
                Bytecode::GenericRangeCheck {
                    value,
                    min,
                    max,
                    desc,
                } => {
                    let in_range = *value >= *min && *value <= *max;
                    let margin = if in_range {
                        (*value - *min).min(*max - *value)
                    } else if *value < *min {
                        *value - *min
                    } else {
                        *value - *max
                    };
                    self.last_result = margin;
                    trace.push(TraceEntry {
                        opcode: "GENERIC_RANGE_CHECK".into(),
                        value: Some(*value),
                        result: Some(margin),
                        expected: None,
                        actual: Some(if in_range { 1.0 } else { 0.0 }),
                        desc: desc.clone(),
                    });
                }
                Bytecode::Assert {
                    assertion_type,
                    expected,
                    desc,
                } => {
                    match assertion_type.as_str() {
                        "gt" => {
                            // Active sonar equation: SE = SL - 2*TL + TS - DT
                            // Default source level 220 dB, detection threshold 5 dB
                            let source_level_db = 220.0;
                            let detection_threshold_db = 5.0;
                            let target_strength = self
                                .registers
                                .get("target_strength_db")
                                .copied()
                                .unwrap_or(10.0);
                            let tl = self.transmission_loss_db;
                            let signal_excess = source_level_db - 2.0 * tl + target_strength
                                - detection_threshold_db;
                            self.signal_excess_db = signal_excess;
                            self.registers
                                .insert("source_level_db".into(), source_level_db);
                            self.registers
                                .insert("signal_excess_db".into(), signal_excess);
                            trace.push(TraceEntry {
                                opcode: "ASSERT_GT".into(),
                                value: None,
                                result: None,
                                expected: Some(*expected),
                                actual: Some(signal_excess),
                                desc: desc.clone(),
                            });
                        }
                        "in_range" => {
                            let margin = self.last_result;
                            trace.push(TraceEntry {
                                opcode: "ASSERT_IN_RANGE".into(),
                                value: None,
                                result: Some(margin),
                                expected: Some(0.0),
                                actual: Some(margin),
                                desc: desc.clone(),
                            });
                        }
                        _ => {
                            trace.push(TraceEntry {
                                opcode: "ASSERT".into(),
                                value: None,
                                result: None,
                                expected: Some(*expected),
                                actual: Some(self.last_result),
                                desc: desc.clone(),
                            });
                        }
                    }
                }
            }
        }

        trace
    }

    /// Evaluate the trace and determine PROVEN/DISPROVEN with confidence.
    pub fn evaluate(
        &self,
        trace: &[TraceEntry],
        problem: &ConstraintProblem,
    ) -> (String, f64, Option<serde_json::Value>) {
        match problem.domain.as_str() {
            "sonar" => {
                let signal_excess = self.signal_excess_db;
                let proven = signal_excess > 0.0;
                let confidence = if proven {
                    1.0 - (-signal_excess / 20.0).exp().min(0.05)
                } else {
                    1.0 - (signal_excess / 20.0).exp().min(0.05)
                };

                let counterexample = if !proven {
                    Some(serde_json::json!({
                        "depth_m": self.registers.get("depth_m").copied().unwrap_or(0.0),
                        "frequency_hz": self.registers.get("frequency_hz").copied().unwrap_or(0.0),
                        "range_m": self.registers.get("range_m").copied().unwrap_or(0.0),
                        "sound_velocity_ms": self.sound_velocity,
                        "absorption_db_km": self.absorption_db_km,
                        "transmission_loss_db": self.transmission_loss_db,
                        "signal_excess_db": signal_excess,
                    }))
                } else {
                    None
                };

                (
                    if proven {
                        "PROVEN".into()
                    } else {
                        "DISPROVEN".into()
                    },
                    (confidence * 100.0).round() / 100.0,
                    counterexample,
                )
            }
            "thermal" => {
                let temp_c = self.registers.get("temp_c").copied().unwrap_or(0.0);
                let min_safe = self.registers.get("min_safe").copied().unwrap_or(0.0);
                let max_safe = self.registers.get("max_safe").copied().unwrap_or(0.0);
                let in_range = temp_c >= min_safe && temp_c <= max_safe;
                let confidence = if in_range { 0.99 } else { 0.98 };

                let counterexample = if !in_range {
                    Some(serde_json::json!({
                        "temp_c": temp_c,
                        "min_safe": min_safe,
                        "max_safe": max_safe,
                        "violation": if temp_c < min_safe { "below_min" } else { "above_max" },
                        "margin_c": temp_c - if temp_c < min_safe { min_safe } else { max_safe },
                    }))
                } else {
                    None
                };

                (
                    if in_range {
                        "PROVEN".into()
                    } else {
                        "DISPROVEN".into()
                    },
                    confidence,
                    counterexample,
                )
            }
            "generic" => {
                // Check the last compare/assert entry
                let mut proven = false;
                for entry in trace.iter().rev() {
                    if entry.opcode == "GENERIC_COMPARE"
                        || entry.opcode == "GENERIC_RANGE_CHECK"
                        || entry.opcode == "GENERIC_BOUND"
                    {
                        proven = entry.result.is_some_and(|v| v > 0.0);
                        break;
                    }
                    if entry.opcode == "ASSERT_IN_RANGE" {
                        proven = entry.result.is_some_and(|v| v >= 0.0);
                        break;
                    }
                }

                let counterexample = if !proven {
                    Some(serde_json::json!({
                        "registers": self.registers,
                    }))
                } else {
                    None
                };

                (
                    if proven {
                        "PROVEN".into()
                    } else {
                        "DISPROVEN".into()
                    },
                    0.95,
                    counterexample,
                )
            }
            _ => ("UNKNOWN".into(), 0.0, None),
        }
    }
}

// ── Sonar Physics ──

/// Mackenzie 1981 equation for sound velocity in seawater.
/// Valid for: 2°C ≤ T ≤ 30°C, 25‰ ≤ S ≤ 40‰, 0 ≤ D ≤ 8000m
pub fn mackenzie_sound_velocity(depth_m: f64, temp_c: f64, salinity_ppt: f64) -> f64 {
    let d = depth_m;
    let t = temp_c;
    let s = salinity_ppt;

    1448.96 + 4.591 * t - 5.304e-2 * t * t
        + 2.374e-4 * t * t * t
        + 1.340 * (s - 35.0)
        + 1.630e-2 * d
        + 1.675e-7 * d * d
        - 1.025e-2 * t * (s - 35.0)
        - 7.139e-13 * t * d * d * d
}

/// Francois-Garrison 1982 absorption model (dB/km).
/// Uses the simplified Thorp (1967) / Francois-Garrison (1982) formulation.
/// Valid for 0.4–100 kHz, temperature-corrected.
pub fn francois_garrison_absorption(
    frequency_khz: f64,
    depth_m: f64,
    temp_c: f64,
    salinity_ppt: f64,
) -> f64 {
    let f = frequency_khz; // kHz
    let t = temp_c;
    let s = salinity_ppt;
    let d = depth_m;

    // Temperature scaling factor (relative to 15°C reference)
    let temp_factor = 1.0 - 0.02 * (t - 15.0);
    // Salinity scaling (relative to 35‰)
    let sal_factor = (s / 35.0).sqrt();
    // Pressure relief at depth
    let pressure_factor = 1.0 - 3.0e-5 * d;

    // Thorp (1967) + FG (1982) simplified absorption formula (dB/km)
    // Boric acid relaxation: 0.11*f²/(1+f²)
    // MgSO4 relaxation: 44*f²/(4100+f²)
    // Viscous: 2.75e-4*f²
    let alpha =
        (0.11 * f * f / (1.0 + f * f) + 44.0 * f * f / (4100.0 + f * f) + 2.75e-4 * f * f + 0.003)
            * temp_factor
            * sal_factor
            * pressure_factor;

    alpha.max(0.001)
}

/// Transmission loss using spherical spreading + absorption.
/// TL = 20*log10(range) + alpha*range/1000
pub fn transmission_loss(range_m: f64, _sound_velocity_ms: f64, absorption_db_km: f64) -> f64 {
    let spreading = 20.0 * range_m.log10();
    let absorption = absorption_db_km * range_m / 1000.0;
    spreading + absorption
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mackenzie_surface_standard() {
        // Standard seawater: 15°C, 35‰, 0m → ~1500 m/s
        let sv = mackenzie_sound_velocity(0.0, 15.0, 35.0);
        assert!((sv - 1500.0).abs() < 10.0, "Expected ~1500 m/s, got {}", sv);
    }

    #[test]
    fn test_mackenzie_deep_cold() {
        // Deep cold: 4°C, 35‰, 4000m → ~1517 m/s (pressure dominates)
        let sv = mackenzie_sound_velocity(4000.0, 4.0, 35.0);
        assert!(sv > 1500.0, "Expected > 1500 m/s at depth, got {}", sv);
    }

    #[test]
    fn test_fg_absorption_low_freq() {
        // Low frequency (~1 kHz) should have low absorption (~0.06 dB/km)
        let abs = francois_garrison_absorption(1.0, 0.0, 15.0, 35.0);
        assert!(abs < 1.0, "Expected < 1 dB/km at 1 kHz, got {}", abs);
    }

    #[test]
    fn test_fg_absorption_high_freq() {
        // High frequency (~100 kHz) should have high absorption
        let abs = francois_garrison_absorption(100.0, 0.0, 15.0, 35.0);
        assert!(abs > 10.0, "Expected > 10 dB/km at 100 kHz, got {}", abs);
    }

    #[test]
    fn test_transmission_loss_short_range() {
        let tl = transmission_loss(1000.0, 1500.0, 0.1);
        // 20*log10(1000) = 60, plus 0.1 absorption
        assert!((tl - 60.1).abs() < 0.5, "Expected ~60.1 dB, got {}", tl);
    }
}
