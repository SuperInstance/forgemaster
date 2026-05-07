//! Example: STM32 reading sonar data over SPI, validating via FLUX, forwarding.
//!
//! This is pseudocode-style — demonstrates the real API on real hardware.
//! Target: STM32F411 (Cortex-M4, 128KB SRAM) with MS5837 pressure sensor
//! on SPI1, UART TX to upstream gateway.
//!
//! Hardware connections:
//!   SPI1_SCK  → PA5
//!   SPI1_MISO → PA6
//!   SPI1_MOSI → PA7
//!   SPI1_CS   → PA4 (pressure sensor)
//!   UART_TX   → PA9 (upstream link)
//!   LED       → PA5 (error indicator)

#![no_std]
#![no_main]

use flux_isa_mini::{
    FluxOpcode, FluxInstruction, FluxVm,
    sonar_check,
};

// In a real project these come from pac + hal crates:
// use stm32f411_pac as pac;
// use stm32f4xx_hal::{spi::Spi, serial::Serial, gpio::*};

/// Hypothetical SPI read of MS5837 pressure sensor → depth in meters.
fn read_depth_spi() -> f64 {
    // Real implementation:
    //   let raw = spi.transfer(&mut [0x00; 3]);
    //   let pressure_dbar = f64::from(raw) * SCALE;
    //   depth = pressure_dbar / 10.0  // ~1 dbar per meter seawater
    45.3 // placeholder
}

/// Send validated data upstream via UART.
fn forward_upstream(_depth: f64, _sound_speed: f64) {
    // Real: uart.bwrite_all(&encode(&results, &mut buf))
}

/// Blink error LED — ASSERT failed, don't forward.
fn blink_error() {
    // Real: led.set_high(); delay(200.ms()); led.set_low();
}

/// Main sensor loop — read, validate, forward.
#[entry]
fn main() -> ! {
    let mut vm = FluxVm::new();

    loop {
        let depth = read_depth_spi();

        // Build constraint program:
        //   LOAD depth → VALIDATE [0, max_depth] → ASSERT → HALT
        let program: [FluxInstruction; 5] = [
            FluxInstruction::new(FluxOpcode::Load, depth, 0.0),       // push depth
            FluxInstruction::new(FluxOpcode::Load, 0.0, 0.0),        // push lower bound
            FluxInstruction::new(FluxOpcode::Load, 200.0, 0.0),      // push upper bound (200m rated)
            FluxInstruction::new(FluxOpcode::Validate, 0.0, 0.0),    // depth in [0, 200]?
            FluxInstruction::new(FluxOpcode::Assert, 0.0, 0.0),      // fail fast if out of bounds
        ];

        // Also run sonar const-checks before bothering the VM
        let depth_ok = sonar_check::check_depth_pressure(depth, 200.0);
        if !depth_ok {
            blink_error();
            continue;
        }

        match vm.execute(&program) {
            Ok(result) if result.constraints_satisfied => {
                // Pre-computed sound speed for deployment site
                let sound_speed = 1500.0;
                if sonar_check::check_sound_speed(sound_speed, 1430.0, 1560.0) {
                    forward_upstream(depth, sound_speed);
                } else {
                    blink_error();
                }
            }
            _ => {
                // Constraint violation — don't forward garbage data
                blink_error();
            }
        }

        vm.reset();

        // Real: delay(100.ms()); — 10 Hz sample rate
    }
}

// Stubs so this compiles as documentation example
mod __hack {
    pub use core;
    #[macro_export]
    #[doc(hidden)]
    macro_rules! entry {
        ($($t:tt)*) => {};
    }
}
use __hack::entry;
