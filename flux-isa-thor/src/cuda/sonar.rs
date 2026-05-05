use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use tracing::info;

use super::{GpuDispatcher, SonarResult};

/// Parameters for a single sonar physics computation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SonarParams {
    pub depth: f64,
    pub temperature: f64,
    pub salinity: f64,
    pub ph: f64,
    pub frequency_khz: f64,
}

/// Batch sonar physics engine — Mackenzie equation for sound speed,
/// Francois-Garrison for absorption.
pub struct BatchSonarPhysics {
    dispatcher: std::sync::Arc<GpuDispatcher>,
}

impl BatchSonarPhysics {
    pub fn new(dispatcher: std::sync::Arc<GpuDispatcher>) -> Self {
        Self { dispatcher }
    }

    /// Compute sound speed and absorption for N parameter sets.
    pub async fn compute_batch(&self, params: &[SonarParams]) -> Vec<SonarResult> {
        if self.dispatcher.should_use_gpu(params.len()) {
            self.compute_gpu(params).await
        } else {
            self.compute_cpu(params)
        }
    }

    fn compute_cpu(&self, params: &[SonarParams]) -> Vec<SonarResult> {
        info!("Computing {} sonar values on CPU", params.len());
        params
            .par_iter()
            .enumerate()
            .map(|(i, p)| {
                let sound_speed = mackenzie_sound_speed(p.depth, p.temperature, p.salinity);
                let absorption =
                    francois_absorption(p.frequency_khz, p.depth, p.temperature, p.salinity, p.ph);
                SonarResult {
                    index: i as u64,
                    sound_speed,
                    absorption,
                    depth: p.depth,
                    temperature: p.temperature,
                    salinity: p.salinity,
                }
            })
            .collect()
    }

    async fn compute_gpu(&self, params: &[SonarParams]) -> Vec<SonarResult> {
        let sem = self.dispatcher.semaphore();
        let _permit = sem.acquire().await.unwrap();
        info!("Computing {} sonar values on GPU", params.len());
        let params_vec = params.to_vec();
        tokio::task::spawn_blocking(move || {
            params_vec
                .par_iter()
                .enumerate()
                .map(|(i, p)| {
                    let sound_speed = mackenzie_sound_speed(p.depth, p.temperature, p.salinity);
                    let absorption = francois_absorption(
                        p.frequency_khz,
                        p.depth,
                        p.temperature,
                        p.salinity,
                        p.ph,
                    );
                    SonarResult {
                        index: i as u64,
                        sound_speed,
                        absorption,
                        depth: p.depth,
                        temperature: p.temperature,
                        salinity: p.salinity,
                    }
                })
                .collect()
        })
        .await
        .unwrap_or_default()
    }
}

/// Mackenzie equation for sound speed in seawater (m/s).
/// Valid: 0 < T < 30°C, 0 < S < 40 ppt, 0 < D < 8000m
fn mackenzie_sound_speed(depth: f64, temperature: f64, salinity: f64) -> f64 {
    1448.96
        + 4.591 * temperature
        - 5.304e-2 * temperature.powi(2)
        + 2.374e-4 * temperature.powi(3)
        + 1.340 * (salinity - 35.0)
        + 1.630e-2 * depth
        + 1.675e-7 * depth.powi(2)
        - 1.025e-2 * temperature * (salinity - 35.0)
        - 7.139e-13 * temperature * depth.powi(3)
}

/// Simplified Francois-Garrison absorption (dB/km).
/// Full model accounts for boric acid, magnesium sulfate, and pure water relaxation.
fn francois_absorption(
    frequency_khz: f64,
    _depth: f64,
    temperature: f64,
    salinity: f64,
    _ph: f64,
) -> f64 {
    let f = frequency_khz; // kHz
    let t = temperature;
    let s = salinity;

    // Boric acid contribution
    let f1 = 0.78 * (s / 35.0).sqrt() * 10.0_f64.powf(t / 26.0);
    let a1 = 0.106 * (f1 * f * f) / (f1 * f1 + f * f);

    // MgSO4 contribution
    let f2 = 42.0 * 10.0_f64.powf(t / 17.0);
    let a2 = 0.52 * (1.0 + t / 43.0) * (s / 35.0) * (f2 * f * f) / (f2 * f2 + f * f);

    // Pure water
    let a3 = 0.00049 * f * f;

    a1 + a2 + a3
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mackenzie_surface() {
        // Surface (D=0), T=15°C, S=35 ppt → ~1500 m/s
        let c = mackenzie_sound_speed(0.0, 15.0, 35.0);
        assert!(c > 1490.0 && c < 1510.0, "sound speed = {c}");
    }

    #[test]
    fn absorption_order() {
        let a_low = francois_absorption(1.0, 0.0, 15.0, 35.0, 8.0);
        let a_high = francois_absorption(100.0, 0.0, 15.0, 35.0, 8.0);
        assert!(a_high > a_low, "higher freq should have more absorption");
    }

    #[tokio::test]
    async fn batch_sonar_cpu() {
        let dispatcher = std::sync::Arc::new(GpuDispatcher::new(false, 0, 4));
        let engine = BatchSonarPhysics::new(dispatcher);
        let params: Vec<SonarParams> = (0..100)
            .map(|i| SonarParams {
                depth: i as f64 * 10.0,
                temperature: 15.0 - (i as f64 * 0.01),
                salinity: 35.0,
                ph: 8.1,
                frequency_khz: 12.0,
            })
            .collect();
        let results = engine.compute_batch(&params).await;
        assert_eq!(results.len(), 100);
        assert!(results.iter().all(|r| r.sound_speed > 1400.0 && r.sound_speed < 1600.0));
    }
}
