use crate::bytecode::Bytecode;
use crate::instruction::Instruction;
use crate::opcode::OpCode;
use crate::sensor::pipeline::SensorSource;

/// Sonar sensor configuration.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SonarConfig {
    /// Water temperature in °C.
    pub temperature_c: f64,
    /// Salinity in PSU (practical salinity units).
    pub salinity_psu: f64,
    /// Depth in meters.
    pub depth_m: f64,
    /// Sonar frequency in kHz.
    pub frequency_khz: f64,
    /// Minimum valid range (meters).
    pub min_range_m: f64,
    /// Maximum valid range (meters).
    pub max_range_m: f64,
}

impl Default for SonarConfig {
    fn default() -> Self {
        SonarConfig {
            temperature_c: 10.0,
            salinity_psu: 35.0,
            depth_m: 100.0,
            frequency_khz: 200.0,
            min_range_m: 0.1,
            max_range_m: 200.0,
        }
    }
}

/// Mackenzie 1981 sound speed equation (m/s).
pub fn mackenzie_sound_speed(temp_c: f64, salinity_psu: f64, depth_m: f64) -> f64 {
    let t = temp_c;
    let s = salinity_psu;
    let d = depth_m;
    1448.96
        + 4.591 * t
        - 5.304e-2 * t * t
        + 2.374e-4 * t * t * t
        + 1.340 * (s - 35.0)
        + 1.630e-2 * d
        + 1.675e-7 * d * d
        - 1.025e-2 * t * (s - 35.0)
        - 7.139e-13 * t * d * d * d
}

/// Francois-Garrison 1982 absorption coefficient (dB/km).
pub fn francois_garrison_absorption(frequency_khz: f64, temp_c: f64, salinity_psu: f64, depth_m: f64) -> f64 {
    let f = frequency_khz;
    let t = temp_c;
    let s = salinity_psu;
    let d = depth_m;

    // Simplified Francois-Garrison model.
    let f1 = 0.78 * (s / 35.0).sqrt() * (t / 26.0).exp();
    let f2 = 42.0 * (t / 17.0).exp();

    let a1 = 0.106 * ((f1 * f1) / (f1 * f1 + f * f)).exp();
    let a2 = 0.52 * (1.0 + t / 43.0) * (s / 35.0) * ((f2 * f2) / (f2 * f2 + f * f)).exp();
    let a3 = 0.00049 * f * f;

    let p = 1.0 - 3.83e-5 * d + 4.9e-10 * d * d;
    (a1 + a2 + a3) * p
}

/// Sonar sensor that generates FLUX bytecodes from its config.
pub struct SonarSensor {
    config: SonarConfig,
    /// Pre-compiled validation bytecode.
    validation_bytecode: Bytecode,
    /// Simulated data (for testing; replace with real hardware reads).
    simulated: bool,
}

impl SonarSensor {
    pub fn new(config: SonarConfig) -> Self {
        let validation_bytecode = Self::compile_validation(&config);
        SonarSensor {
            config,
            validation_bytecode,
            simulated: false,
        }
    }

    pub fn simulated(config: SonarConfig) -> Self {
        let validation_bytecode = Self::compile_validation(&config);
        SonarSensor {
            config,
            validation_bytecode,
            simulated: true,
        }
    }

    /// Compile sensor validation rules into FLUX bytecode.
    /// Validates that readings fall within [min_range, max_range].
    pub fn compile_validation(config: &SonarConfig) -> Bytecode {
        // Program: read value, push min, push max, VALIDATE, ASSERT, HALT
        let instructions = vec![
            Instruction::new(OpCode::Input),                              // push reading
            Instruction::with_operand(OpCode::Push, config.min_range_m),  // min bound
            Instruction::with_operand(OpCode::Push, config.max_range_m),  // max bound
            Instruction::new(OpCode::Validate),                           // check [min, max]
            Instruction::new(OpCode::Assert),                             // assert valid
            Instruction::new(OpCode::Halt),
        ];
        Bytecode::new(instructions).with_label("sonar-validation")
    }

    /// Validate a single reading against physical bounds.
    pub fn validate_reading(&self, reading_m: f64) -> bool {
        reading_m >= self.config.min_range_m && reading_m <= self.config.max_range_m
    }

    /// Get the sound speed for current config.
    pub fn sound_speed(&self) -> f64 {
        mackenzie_sound_speed(
            self.config.temperature_c,
            self.config.salinity_psu,
            self.config.depth_m,
        )
    }

    /// Get the absorption for current config.
    pub fn absorption(&self) -> f64 {
        francois_garrison_absorption(
            self.config.frequency_khz,
            self.config.temperature_c,
            self.config.salinity_psu,
            self.config.depth_m,
        )
    }

    pub fn config(&self) -> &SonarConfig {
        &self.config
    }

    pub fn validation_bytecode(&self) -> &Bytecode {
        &self.validation_bytecode
    }
}

impl SensorSource for SonarSensor {
    fn read_sensor_data(&mut self) -> Vec<f64> {
        if self.simulated {
            // Generate a simulated sonar ping within valid range.
            let mid = (self.config.min_range_m + self.config.max_range_m) / 2.0;
            let range = self.config.max_range_m - self.config.min_range_m;
            // Simple pseudo-random variation.
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos() as f64;
            let noise = ((now % 1000.0) / 1000.0 - 0.5) * range * 0.1;
            vec![(mid + noise).clamp(self.config.min_range_m, self.config.max_range_m)]
        } else {
            // In production, read from hardware (NVIDIA Jetson GPIO/I2S/SPI).
            vec![]
        }
    }

    fn sensor_name(&self) -> &str {
        "sonar"
    }
}
