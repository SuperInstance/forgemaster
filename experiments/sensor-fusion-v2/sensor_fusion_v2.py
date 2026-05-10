#!/usr/bin/env python3
"""
Sensor Fusion V2 — Adaptive Sheaf H¹ Detector with Multi-Resolution Analysis

Fixes identified in V1:
  - False positives on normal data (fixed threshold)
  - Missed time-delay failures (fixed threshold)
  - Single-resolution sheaf missed frequency-specific failures

Key improvements:
  1. Adaptive threshold: depends on sensor noise + EKF covariance + running statistics
  2. Multi-resolution: coarse (1Hz), medium (10Hz), fine (100Hz) — different failures at different scales
  3. Realistic drone flight: 300s with takeoff/cruise/landing phases
  4. ROC validation against covariance and residual methods
  5. Zero false positives on normal data while detecting all failure modes
"""

import numpy as np
from scipy import linalg, signal
from scipy.sparse.csgraph import connected_components
import json
import os
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# PART 0: Ground Truth Sensor Models
# =============================================================================

class SensorSpec:
    """Realistic sensor specifications for a small UAV"""
    def __init__(self):
        # IMU (ICM-20948 grade)
        self.accel_noise_std = 0.05    # m/s² — MEMS IMU
        self.gyro_noise_std = 0.01     # rad/s
        self.accel_bias_std = 0.02     # m/s² — turn-on bias
        self.gyro_bias_std = 0.005     # rad/s
        self.accel_scale_error = 0.01  # 1% scale factor
        
        # GPS (u-blox F9 grade)
        self.gps_pos_noise_std = 0.3   # meters — horizontal
        self.gps_vel_noise_std = 0.05  # m/s
        self.gps_update_rate = 10      # Hz
        
        # Barometer
        self.baro_noise_std = 0.5      # meters (altitude)
        self.baro_drift_rate = 0.1     # m/s

class TrueState:
    """Ground truth trajectory generator"""
    @staticmethod
    def generate(t=300.0, dt=0.01, seed=42):
        """Generate realistic 3D drone trajectory with takeoff/cruise/landing"""
        rng = np.random.RandomState(seed)
        n = int(t / dt)
        time = np.arange(n) * dt
        
        # Position (meters), Velocity (m/s), Acceleration (m/s²)
        pos = np.zeros((n, 3))
        vel = np.zeros((n, 3))
        acc = np.zeros((n, 3))
        
        # Phase masks
        takeoff_mask = time < 60.0
        cruise_mask = (time >= 60.0) & (time < 240.0)
        landing_mask = time >= 240.0
        
        # ---- Takeoff (0-60s): high dynamics ----
        n_takeoff = int(60.0 / dt)
        # Smooth upward acceleration then deceleration (SCurve profile)
        t_rel = time[:n_takeoff] / 60.0
        # Z: smooth s-curve climb to 100m
        z_takeoff = 100.0 * (3*t_rel**2 - 2*t_rel**3)  # cubic hermite
        vel_z_takeoff = np.gradient(z_takeoff, dt)
        acc_z_takeoff = np.gradient(vel_z_takeoff, dt)
        
        # XY: small lateral drift during takeoff + rotation
        x_takeoff = 2.0 * np.sin(2*np.pi * t_rel * 0.5)
        y_takeoff = 3.0 * np.sin(2*np.pi * t_rel * 0.3)
        vel_x_takeoff = np.gradient(x_takeoff, dt)
        vel_y_takeoff = np.gradient(y_takeoff, dt)
        
        pos[:n_takeoff] = np.column_stack([x_takeoff, y_takeoff, z_takeoff])
        vel[:n_takeoff] = np.column_stack([vel_x_takeoff, vel_y_takeoff, vel_z_takeoff])
        acc[:n_takeoff] = np.column_stack([
            np.gradient(vel_x_takeoff, dt),
            np.gradient(vel_y_takeoff, dt),
            np.gradient(vel_z_takeoff, dt)
        ])
        
        # ---- Cruise (60-240s): steady flight with gentle turns ----
        n_cruise_pts = int(180.0 / dt)
        cruise_t = np.arange(n_cruise_pts) * dt
        # Gentle circular arc
        cruise_radius = 50.0
        cruise_omega = 2*np.pi / 120.0  # full circle in 2 minutes
        cruise_angle = cruise_omega * cruise_t
        
        x_cruise = cruise_radius * np.cos(cruise_angle) + 2.0
        y_cruise = cruise_radius * np.sin(cruise_angle) + 2.0
        z_cruise = 100.0 + 5.0 * np.sin(2*np.pi * cruise_t / 180.0)  # gentle altitude changes
        
        idx_offset = n_takeoff
        pos[idx_offset:idx_offset+n_cruise_pts] = np.column_stack([x_cruise, y_cruise, z_cruise])
        vel[idx_offset:idx_offset+n_cruise_pts, 0] = np.gradient(x_cruise, dt)
        vel[idx_offset:idx_offset+n_cruise_pts, 1] = np.gradient(y_cruise, dt)
        vel[idx_offset:idx_offset+n_cruise_pts, 2] = np.gradient(z_cruise, dt)
        acc[idx_offset:idx_offset+n_cruise_pts] = np.gradient(vel[idx_offset:idx_offset+n_cruise_pts], dt, axis=0)
        
        # ---- Landing (240-300s): descending with GPS degradation ----
        n_landing = int(60.0 / dt)
        l_t_rel = np.arange(n_landing) / n_landing
        # Flip coordinates for landing pattern
        # Smooth descent from current position to ground
        # Start from last cruise position
        last_cruise_pos = pos[idx_offset+n_cruise_pts-1]
        last_cruise_vel = vel[idx_offset+n_cruise_pts-1]
        
        for i in range(n_landing):
            t_norm = l_t_rel[i]
            # Cubic descent profile
            factor = 3*t_norm**2 - 2*t_norm**3
            pos[idx_offset+n_cruise_pts+i] = last_cruise_pos * (1 - factor) + np.array([0, 0, 0]) * factor
            pos[idx_offset+n_cruise_pts+i, 2] = last_cruise_pos[2] * (1 - factor)  # z goes to 0
            # Add slight wobble during landing
            pos[idx_offset+n_cruise_pts+i, 0] += 0.5 * np.sin(2*np.pi * i * dt * 2)
            pos[idx_offset+n_cruise_pts+i, 1] += 0.5 * np.cos(2*np.pi * i * dt * 1.7)
        
        # Recompute velocities and accelerations after landing path
        vel = np.gradient(pos, dt, axis=0)
        acc = np.gradient(vel, dt, axis=0)
        
        return time, pos, vel, acc


# =============================================================================
# PART 1: Adaptive Sheaf H¹ Detector
# =============================================================================

class AdaptiveSheafDetector:
    """
    Sheaf cohomology H¹ detector with adaptive threshold.
    
    The threshold adapts based on:
    - Sensor noise covariance (from sensor specs)
    - EKF state uncertainty (from filter covariance)
    - Running statistics of recent measurements
    
    Agreement threshold = k * sqrt(P_sensor + P_ekf + P_running)
    where P are covariance magnitudes at each node.
    """
    
    def __init__(self, sensor_spec, k_factor=3.0, window_size=100):
        self.sensor_spec = sensor_spec
        self.k_factor = k_factor  # Number of standard deviations for threshold
        self.window_size = window_size
        self.running_mean = {}
        self.running_std = {}
        self.history = {}
        
    def _compute_node_covariance(self, sensor_name):
        """Get expected noise covariance for a sensor node"""
        spec = self.sensor_spec
        # Base noise levels for each sensor
        noise_map = {
            'accel': spec.accel_noise_std,
            'gyro': spec.gyro_noise_std,
            'gps': spec.gps_pos_noise_std,
            'baro': spec.baro_noise_std,
        }
        base_std = noise_map.get(sensor_name, 0.1)
        return base_std ** 2
    
    def _compute_ekf_uncertainty(self, ekf_cov):
        """Extract uncertainty magnitude from EKF covariance matrix"""
        if ekf_cov is None or np.all(ekf_cov == 0):
            return 0.0
        # Frobenius norm as scalar uncertainty measure
        return np.linalg.norm(ekf_cov) / ekf_cov.shape[0]
    
    def _compute_running_statistics(self, sensor_name, value):
        """Update and return running mean and std for a sensor"""
        if sensor_name not in self.history:
            self.history[sensor_name] = []
            self.running_mean[sensor_name] = value
            self.running_std[sensor_name] = self._compute_node_covariance(sensor_name) ** 0.5
        
        self.history[sensor_name].append(value)
        if len(self.history[sensor_name]) > self.window_size:
            self.history[sensor_name].pop(0)
        
        if len(self.history[sensor_name]) >= 5:  # Need minimum samples
            self.running_mean[sensor_name] = np.mean(self.history[sensor_name])
            self.running_std[sensor_name] = np.std(self.history[sensor_name]) + 1e-10
        
        return self.running_mean[sensor_name], self.running_std[sensor_name]
    
    def compute_adaptive_threshold(self, sensor_a, sensor_b, value_a, value_b, 
                                    ekf_cov=None):
        """Compute adaptive agreement threshold between two sensors"""
        # 1. Sensor noise component
        noise_a = self._compute_node_covariance(sensor_a)
        noise_b = self._compute_node_covariance(sensor_b)
        
        # 2. EKF uncertainty component
        ekf_uncertainty = self._compute_ekf_uncertainty(ekf_cov)
        
        # 3. Running statistics component
        _, std_a = self._compute_running_statistics(sensor_a, value_a)
        _, std_b = self._compute_running_statistics(sensor_b, value_b)
        
        # Effective threshold = k * sqrt(sensor_noise² + ekf² + running_variance²)
        var_total = noise_a + noise_b + ekf_uncertainty**2 + std_a**2 + std_b**2
        threshold = self.k_factor * np.sqrt(var_total)
        
        return threshold
    
    def compute_agreement(self, sensor_a, sensor_b, value_a, value_b, ekf_cov=None):
        """Compute agreement (0=perfect, higher=disagreement) with adaptive threshold"""
        diff = abs(value_a - value_b)
        threshold = self.compute_adaptive_threshold(
            sensor_a, sensor_b, value_a, value_b, ekf_cov
        )
        # Agreement metric: 0 if diff <= threshold, scaled diff beyond threshold
        if diff <= threshold:
            return 0.0
        else:
            return (diff - threshold) / threshold
    
    def compute_h1(self, sensor_readings, sensor_names, ekf_cov=None):
        """
        Compute sheaf H¹ magnitude from pairwise agreements.
        
        The sheaf has one node per sensor. Restriction maps compare 
        sensor values. H¹ = sum of pairwise disagreements that exceed
        adaptive thresholds, weighted by sheaf coboundary operator.
        """
        agreements = {}
        total_disagreement = 0.0
        n_pairs = 0
        
        for (a, b) in combinations(range(len(sensor_readings)), 2):
            name_a = sensor_names[a]
            name_b = sensor_names[b]
            val_a = sensor_readings[a]
            val_b = sensor_readings[b]
            
            # Compute agreement with adaptive threshold
            agreement = self.compute_agreement(
                name_a, name_b, val_a, val_b, ekf_cov
            )
            
            pair_key = f"{name_a}_{name_b}"
            agreements[pair_key] = agreement
            
            # H¹ is sum of squared agreement violations (sheaf coboundary)
            total_disagreement += agreement ** 2
            n_pairs += 1
        
        # H¹ magnitude: normalized sum of squared disagreements
        # 0 = perfect agreement within thresholds
        # > 0 = at least one pair exceeds adaptive threshold
        h1_mag = total_disagreement / max(n_pairs, 1)
        
        # Overall agreement: worst-case single pair
        overall = min(agreements.values()) if agreements else 1.0
        
        return {
            'h1_mag': h1_mag,
            'h1_dim': 1 if h1_mag > 0 else 0,
            'agreements': agreements,
            'overall': overall,
            'n_pairs': n_pairs
        }


# =============================================================================
# PART 2: Multi-Resolution Sheaf
# =============================================================================

class MultiResolutionSheaf:
    """
    Sheaf H¹ computed at multiple temporal resolutions.
    
    Different failure modes manifest at different scales:
    - Coarse (1Hz):   Systematic bias, GPS drift — long-term consistency
    - Medium (10Hz):  Time delays, dynamic mismatches — short-term dynamics
    - Fine (100Hz):   Noise anomalies, vibration changes — high-frequency content
    """
    
    def __init__(self, sensor_spec, base_dt=0.01):
        self.base_dt = base_dt
        self.detectors = {
            'coarse': AdaptiveSheafDetector(sensor_spec, k_factor=4.0, window_size=20),
            'medium': AdaptiveSheafDetector(sensor_spec, k_factor=3.5, window_size=50),
            'fine': AdaptiveSheafDetector(sensor_spec, k_factor=3.0, window_size=100),
        }
        self.decimations = {
            'coarse': 100,   # 1Hz from 100Hz base
            'medium': 10,    # 10Hz from 100Hz base
            'fine': 1,       # 100Hz (base rate)
        }
    
    def analyze_window(self, readings_window, sensor_names, ekf_cov=None):
        """
        Analyze a time window at all three resolutions.
        
        Returns H¹ magnitude at each resolution and a combined score.
        """
        results = {}
        
        for res_name, decimation in self.decimations.items():
            window_len = len(readings_window)
            if window_len < decimation:
                h1_result = {'h1_mag': 0.0, 'h1_dim': 0, 'overall': 1.0}
            else:
                # Decimate readings
                decimated = readings_window[::decimation]
                if len(decimated) > 0:
                    # Take latest reading from decimated window
                    latest = decimated[-1]
                    # Run detector on latest values
                    h1_result = self.detectors[res_name].compute_h1(
                        latest, sensor_names, ekf_cov
                    )
                else:
                    h1_result = {'h1_mag': 0.0, 'h1_dim': 0, 'overall': 1.0}
            
            results[res_name] = h1_result
        
        # Combined score: weighted sum across resolutions
        # Coarse: global consistency (weight 1.0)
        # Medium: dynamic consistency (weight 1.5)
        # Fine: noise consistency (weight 0.5)
        combined = (
            1.0 * results['coarse']['h1_mag'] +
            1.5 * results['medium']['h1_mag'] +
            0.5 * results['fine']['h1_mag']
        )
        
        results['combined'] = combined
        return results


# =============================================================================
# PART 3: Full Sensor Simulation
# =============================================================================

class SensorSimulator:
    """Simulates realistic sensor readings with configurable failure injection"""
    
    def __init__(self, sensor_spec, true_pos, true_vel, true_acc, dt=0.01):
        self.spec = sensor_spec
        self.true_pos = true_pos
        self.true_vel = true_vel
        self.true_acc = true_acc
        self.dt = dt
        self.n = len(true_pos)
        self.rng = np.random.RandomState(42)
        
        # State
        self.accel_bias = np.array([
            self.rng.normal(0, sensor_spec.accel_bias_std),
            self.rng.normal(0, sensor_spec.accel_bias_std),
            self.rng.normal(0, sensor_spec.accel_bias_std)
        ])
        self.gyro_bias = np.array([
            self.rng.normal(0, sensor_spec.gyro_bias_std),
            self.rng.normal(0, sensor_spec.gyro_bias_std),
            self.rng.normal(0, sensor_spec.gyro_bias_std)
        ])
        
        # Failure state
        self.failures = {
            'bias_start': -1,
            'bias_end': -1,
            'bias_magnitude': 0.0,
            'delay_start': -1,
            'delay_end': -1,
            'delay_samples': 0,
            'gps_fail_start': -1,
            'gps_fail_end': -1,
            'noise_anomaly_start': -1,
            'noise_anomaly_end': -1,
            'noise_anomaly_factor': 1.0,
        }
    
    def inject_bias(self, start_time, end_time, magnitude=1.0):
        """Inject bias into accelerometer"""
        start_idx = int(start_time / self.dt)
        end_idx = int(end_time / self.dt)
        self.failures['bias_start'] = start_idx
        self.failures['bias_end'] = end_idx
        self.failures['bias_magnitude'] = magnitude
    
    def inject_delay(self, start_time, end_time, delay_ms=100):
        """Inject time delay into GPS (delay in milliseconds)"""
        start_idx = int(start_time / self.dt)
        end_idx = int(end_time / self.dt)
        delay_samples = int(delay_ms / (self.dt * 1000))
        self.failures['delay_start'] = start_idx
        self.failures['delay_end'] = end_idx
        self.failures['delay_samples'] = delay_samples
    
    def inject_gps_failure(self, start_time, end_time):
        """Inject complete GPS failure (jumps to random position)"""
        start_idx = int(start_time / self.dt)
        end_idx = int(end_time / self.dt)
        self.failures['gps_fail_start'] = start_idx
        self.failures['gps_fail_end'] = end_idx
    
    def inject_noise_anomaly(self, start_time, end_time, factor=5.0):
        """Inject increased noise into IMU"""
        start_idx = int(start_time / self.dt)
        end_idx = int(end_time / self.dt)
        self.failures['noise_anomaly_start'] = start_idx
        self.failures['noise_anomaly_end'] = end_idx
        self.failures['noise_anomaly_factor'] = factor
    
    def get_readings(self, time_idx):
        """Get sensor readings at a given time index. Returns dict of sensor_name: (value, ekf_cov)"""
        i = min(time_idx, self.n - 1)
        
        # True values
        true_pos_i = self.true_pos[i]
        true_vel_i = self.true_vel[i]
        true_acc_i = self.true_acc[i]
        
        readings = {}
        
        # ---- Accelerometer ----
        accel_noise = self.rng.normal(0, self.spec.accel_noise_std, 3)
        failure_factor = 1.0
        
        # Check noise anomaly failure
        if (self.failures['noise_anomaly_start'] <= i < self.failures['noise_anomaly_end']):
            failure_factor = self.failures['noise_anomaly_factor']
        
        # Check bias failure
        if (self.failures['bias_start'] <= i < self.failures['bias_end']):
            bias = np.array([self.failures['bias_magnitude'], 0, 0])
        else:
            bias = self.accel_bias
        
        accel_reading = true_acc_i + bias + accel_noise * failure_factor
        readings['accel'] = (np.linalg.norm(accel_reading), np.eye(3) * self.spec.accel_noise_std**2)
        
        # ---- Gyroscope ----
        gyro_noise = self.rng.normal(0, self.spec.gyro_noise_std, 3)
        # Extract angular velocity from trajectory (simplified)
        # Use cross product of velocity change as proxy
        if i > 0:
            angular_rate = np.cross(true_vel_i, self.true_vel[i-1]) / (self.dt * np.linalg.norm(true_vel_i + 1e-10) + 1e-10)
        else:
            angular_rate = np.zeros(3)
        
        gyro_reading = angular_rate + self.gyro_bias + gyro_noise * failure_factor
        readings['gyro'] = (np.linalg.norm(gyro_reading), np.eye(3) * self.spec.gyro_noise_std**2)
        
        # ---- GPS ----
        gps_noise = self.rng.normal(0, self.spec.gps_pos_noise_std, 3)
        
        # Check delay failure: return stale position
        delay_samples = self.failures['delay_samples']
        if delay_samples > 0 and self.failures['delay_start'] <= i < self.failures['delay_end']:
            stale_idx = max(0, i - delay_samples)
            gps_pos = self.true_pos[stale_idx] + gps_noise
        else:
            gps_pos = true_pos_i + gps_noise
        
        # Check GPS failure: wild position
        if self.failures['gps_fail_start'] <= i < self.failures['gps_fail_end']:
            # Random jump (meter-scale)
            gps_pos = gps_pos + self.rng.uniform(-50, 50, 3)
        
        readings['gps'] = (np.linalg.norm(gps_pos), np.eye(3) * self.spec.gps_pos_noise_std**2)
        
        # ---- Barometer (altitude only) ----
        baro_noise = self.rng.normal(0, self.spec.baro_noise_std)
        baro_drift = self.spec.baro_drift_rate * i * self.dt
        baro_reading = true_pos_i[2] + baro_drift + baro_noise
        readings['baro'] = (baro_reading, np.array([[self.spec.baro_noise_std**2]]))
        
        return readings
    
    def get_ekf_cov_estimate(self, time_idx):
        """Simulate EKF covariance (simplified: depends on phase)"""
        i = min(time_idx, self.n - 1)
        t = i * self.dt
        
        # EKF uncertainty increases during maneuvers and GPS degradation
        base_cov = np.eye(6) * 0.1  # 6-state EKF (pos, vel)
        
        # Takeoff: higher uncertainty
        if t < 60:
            base_cov *= 2.0
        # Landing: GPS degradation
        elif t >= 240:
            base_cov *= 3.0
        
        # GPS failure: covariance blows up
        if (self.failures['gps_fail_start'] <= i < self.failures['gps_fail_end']):
            base_cov *= 10.0
        
        return base_cov


# =============================================================================
# PART 4: Baseline Detectors (for ROC comparison)
# =============================================================================

class CovarianceDetector:
    """Detect failures using measurement innovation covariance"""
    def __init__(self, threshold_factor=3.0):
        self.threshold_factor = threshold_factor
        self.running_mean = 0
        self.running_std = 1e-6
        self.n = 0
    
    def update(self, innovation):
        """Update running statistics and return anomaly score"""
        self.n += 1
        if self.n == 1:
            self.running_mean = innovation
            return 0.0
        
        # Running mean/std (Welford style)
        old_mean = self.running_mean
        self.running_mean = old_mean + (innovation - old_mean) / self.n
        if self.n > 1:
            self.running_std = np.sqrt(
                ((self.n - 1) * self.running_std**2 + 
                 (innovation - old_mean) * (innovation - self.running_mean)) / self.n
            ) + 1e-10
        
        # Mahalanobis-like distance
        if self.running_std > 0:
            return abs(innovation - self.running_mean) / self.running_std
        return 0.0

class ResidualDetector:
    """Detect failures using prediction residuals"""
    def __init__(self, window=20):
        self.window = window
        self.history = []
        self.threshold = 0.1
    
    def update(self, residual):
        """Update and return anomaly score (normalized residual)"""
        self.history.append(residual)
        if len(self.history) > self.window:
            self.history.pop(0)
        
        if len(self.history) >= 5:
            mean = np.mean(self.history)
            std = np.std(self.history) + 1e-10
            return abs(residual - mean) / std
        return 0.0


# =============================================================================
# PART 5: Main Experiment Runner
# =============================================================================

def scan_threshold(detector_name, scores, ground_truth, thresholds):
    """Compute TPR and FPR at each threshold"""
    tpr = []
    fpr = []
    
    for thresh in thresholds:
        predictions = (np.array(scores) > thresh).astype(int)
        gt = np.array(ground_truth)
        
        tp = np.sum((predictions == 1) & (gt == 1))
        fp = np.sum((predictions == 1) & (gt == 0))
        fn = np.sum((predictions == 0) & (gt == 1))
        tn = np.sum((predictions == 0) & (gt == 0))
        
        tpr_val = tp / max(tp + fn, 1)
        fpr_val = fp / max(fp + tn, 1)
        
        tpr.append(tpr_val)
        fpr.append(fpr_val)
    
    return fpr, tpr

def compute_auc(fpr, tpr):
    """Compute area under ROC curve using trapezoidal rule"""
    # Sort by fpr
    pairs = sorted(zip(fpr, tpr))
    fpr_sorted, tpr_sorted = zip(*pairs) if pairs else ([], [])
    
    auc = 0.0
    for i in range(1, len(fpr_sorted)):
        auc += (fpr_sorted[i] - fpr_sorted[i-1]) * (tpr_sorted[i] + tpr_sorted[i-1]) / 2
    
    return auc


def run_experiment():
    """Run complete sensor fusion v2 experiment"""
    
    print("=" * 70)
    print("SENSOR FUSION V2 — Adaptive Sheaf H¹ Detector")
    print("=" * 70)
    
    # =========================================================================
    # Setup
    # =========================================================================
    spec = SensorSpec()
    T = 300.0  # seconds
    dt = 0.01   # 100Hz
    n_total = int(T / dt)
    
    # Generate ground truth
    time, true_pos, true_vel, true_acc = TrueState.generate(T, dt)
    
    # Create simulator
    sim = SensorSimulator(spec, true_pos, true_vel, true_acc, dt)
    
    # Inject failures at realistic times
    # Bias failure: accelerometer bias during cruise (t=90-100s)
    sim.inject_bias(90, 100, magnitude=2.0)
    
    # Time delay: GPS delay during cruise (t=130-140s)
    sim.inject_delay(130, 140, delay_ms=200)
    
    # GPS failure: complete GPS failure during landing (t=260-270s)
    sim.inject_gps_failure(260, 270)
    
    # Noise anomaly: IMU noise spike during landing (t=275-285s)
    sim.inject_noise_anomaly(275, 285, factor=8.0)
    
    # Ground truth: which time indices have any failure active
    ground_truth = np.zeros(n_total, dtype=int)
    for key in ['bias_start', 'delay_start', 'gps_fail_start', 'noise_anomaly_start']:
        start = sim.failures[key]
        end_key = key.replace('_start', '_end')
        end = sim.failures[end_key]
        if start >= 0:
            ground_truth[start:end] = 1
    
    # =========================================================================
    # Run detectors
    # =========================================================================
    print("\nRunning detectors across 300s flight...")
    
    # Detectors
    adaptive_detector = AdaptiveSheafDetector(spec, k_factor=3.0, window_size=100)
    multi_res = MultiResolutionSheaf(spec)
    cov_detector = CovarianceDetector()
    res_detector = ResidualDetector()
    
    # Score storage
    h1_scores = []
    h1_coarse = []
    h1_medium = []
    h1_fine = []
    h1_combined = []
    cov_scores = []
    res_scores = []
    
    # For computing detection latency
    failure_detection_times = {}
    for fname in ['bias', 'delay', 'gps_fail', 'noise_anomaly']:
        failure_detection_times[fname] = {'start': sim.failures[f'{fname}_start'],
                                           'h1_detect': None, 'cov_detect': None, 'res_detect': None}
    
    # Window for multi-resolution analysis
    window_size = 100  # 1 second of data
    
    for i in range(n_total):
        # Get sensor readings
        readings = sim.get_readings(i)
        sensor_names = list(readings.keys())
        sensor_values = [readings[n][0] for n in sensor_names]
        ekf_cov = sim.get_ekf_cov_estimate(i)
        
        # --- Adaptive H¹ ---
        h1_result = adaptive_detector.compute_h1(sensor_values, sensor_names, ekf_cov)
        h1_scores.append(h1_result['h1_mag'])
        
        # --- Multi-resolution (buffered) ---
        if i >= window_size:
            window_readings = []
            for j in range(i - window_size + 1, i + 1):
                r = sim.get_readings(j)
                window_readings.append([r[n][0] for n in sensor_names])
            
            mr_result = multi_res.analyze_window(window_readings, sensor_names, ekf_cov)
            h1_coarse.append(mr_result['coarse']['h1_mag'])
            h1_medium.append(mr_result['medium']['h1_mag'])
            h1_fine.append(mr_result['fine']['h1_mag'])
            h1_combined.append(mr_result['combined'])
        else:
            h1_coarse.append(0.0)
            h1_medium.append(0.0)
            h1_fine.append(0.0)
            h1_combined.append(0.0)
        
        # --- Covariance ---
        # Innovation = difference between accelerometer prediction and GPS measurement
        accel_reading = readings['accel'][0]
        gps_reading = readings['gps'][0]
        innovation = abs(accel_reading - gps_reading)
        cov_score = cov_detector.update(innovation)
        cov_scores.append(cov_score)
        
        # --- Residual ---
        residual = abs(accel_reading - gps_reading)
        res_score = res_detector.update(residual)
        res_scores.append(res_score)
        
        # Track detection latency
        if ground_truth[i] == 1:
            for fname, finfo in failure_detection_times.items():
                start_idx = sim.failures[f'{fname}_start']
                if start_idx <= i <= start_idx + int(5.0 / dt):  # Check first 5 seconds of failure
                    if finfo['h1_detect'] is None and h1_scores[-1] > 1e-6:
                        finfo['h1_detect'] = i
                    if finfo['cov_detect'] is None and cov_scores[-1] > 3.0:
                        finfo['cov_detect'] = i
                    if finfo['res_detect'] is None and res_scores[-1] > 3.0:
                        finfo['res_detect'] = i
        
        # Progress
        if i % (n_total // 20) == 0 and i > 0:
            print(f"  Progress: {100 * i // n_total}%")
    
    # =========================================================================
    # Results Analysis
    # =========================================================================
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # --- Analysis Windows ---
    failure_labels = [
        ('Normal Flight', 0, 3*60),
        ('Takeoff', 0, 60),
        ('Cruise (pre-failure)', 60, 90),
        ('Bias Failure', 90, 100),
        ('Cruise (recovery)', 100, 130),
        ('Delay Failure', 130, 140),
        ('Cruise (recovery 2)', 140, 240),
        ('Landing', 240, 260),
        ('GPS Failure', 260, 270),
        ('Noise Anomaly', 275, 285),
        ('Landing (post-failure)', 285, 300),
    ]
    
    results_summary = {}
    
    for label, t_start, t_end in failure_labels:
        i_start = int(t_start / dt)
        i_end = int(t_end / dt)
        
        h1_window = h1_scores[i_start:i_end]
        cov_window = cov_scores[i_start:i_end]
        res_window = res_scores[i_start:i_end]
        
        # Count samples where each detector fires (above natural baseline)
        h1_fires = sum(1 for s in h1_window if s > 1e-6)
        cov_fires = sum(1 for s in cov_window if s > 3.0)
        res_fires = sum(1 for s in res_window if s > 3.0)
        
        is_failure_period = any(ground_truth[i_start:i_end])
        
        results_summary[label] = {
            't_range': [t_start, t_end],
            'h1_mean': float(np.mean(h1_window)),
            'h1_max': float(np.max(h1_window)),
            'h1_fire_rate': float(h1_fires / max(len(h1_window), 1)),
            'cov_mean': float(np.mean(cov_window)),
            'cov_max': float(np.max(cov_window)),
            'res_mean': float(np.mean(res_window)),
            'res_max': float(np.max(res_window)),
            'is_failure_period': bool(is_failure_period),
            'h1_correct': (
                (is_failure_period and h1_fires > len(h1_window) * 0.01) or  # detects failure
                (not is_failure_period and h1_fires == 0)  # no false positive
            )
        }
        
        status = "✅" if results_summary[label]['h1_correct'] else "❌"
        h1_val = results_summary[label]['h1_mean']
        print(f"  {status} {label:35s} | H¹={h1_val:.6f} | fires={h1_fires:4d}/{len(h1_window):6d}")
    
    print(f"\n  Baseline comparison:")
    for label, t_start, t_end in failure_labels:
        i_start = int(t_start / dt)
        i_end = int(t_end / dt)
        h1_window = h1_scores[i_start:i_end]
        cov_window = cov_scores[i_start:i_end]
        res_window = res_scores[i_start:i_end]
        
        is_failure = any(ground_truth[i_start:i_end])
        h1_fires = sum(1 for s in h1_window if s > 1e-6)
        cov_fires = sum(1 for s in cov_window if s > 3.0)
        res_fires = sum(1 for s in res_window if s > 3.0)
        
        cov_rate = cov_fires / max(len(cov_window), 1)
        res_rate = res_fires / max(len(res_window), 1)
        h1_rate = h1_fires / max(len(h1_window), 1)
        
        print(f"  {label:35s} | H¹={h1_rate:.3f} | Cov={cov_rate:.3f} | Res={res_rate:.3f} | Failure={is_failure}")
    
    # =========================================================================
    # Detection Latency
    # =========================================================================
    print("\n" + "-" * 70)
    print("Detection Latency (seconds from failure onset)")
    print("-" * 70)
    
    latency_data = {}
    for fname, finfo in failure_detection_times.items():
        start_s = finfo['start'] * dt if finfo['start'] >= 0 else None
        
        latencies = {}
        for detector in ['h1', 'cov', 'res']:
            detect_idx = finfo[f'{detector}_detect']
            if start_s is not None and detect_idx is not None:
                latencies[detector] = (detect_idx - finfo['start']) * dt
            else:
                latencies[detector] = None
        
        latency_data[fname] = {
            'start_time': start_s,
            'h1_latency': latencies['h1'],
            'cov_latency': latencies['cov'],
            'res_latency': latencies['res']
        }
        
        if start_s is not None:
            print(f"  {fname:15s} @ t={start_s:5.1f}s | H¹={latencies['h1']}s | Cov={latencies['cov']}s | Res={latencies['res']}s")
    
    # =========================================================================
    # ROC Curve Data
    # =========================================================================
    print("\n" + "-" * 70)
    print("ROC Curve Analysis")
    print("-" * 70)
    
    # Generate thresholds for each detector
    h1_thresholds = np.logspace(-8, 0, 200)
    cov_thresholds = np.linspace(0, 20, 200)
    res_thresholds = np.linspace(0, 20, 200)
    
    h1_fpr, h1_tpr = scan_threshold('H¹', h1_scores, ground_truth, h1_thresholds)
    cov_fpr, cov_tpr = scan_threshold('Covariance', cov_scores, ground_truth, cov_thresholds)
    res_fpr, res_tpr = scan_threshold('Residual', res_scores, ground_truth, res_thresholds)
    
    h1_auc = compute_auc(h1_fpr, h1_tpr)
    cov_auc = compute_auc(cov_fpr, cov_tpr)
    res_auc = compute_auc(res_fpr, res_tpr)
    
    roc_data = {
        'h1': {'fpr': h1_fpr, 'tpr': h1_tpr, 'auc': h1_auc},
        'covariance': {'fpr': cov_fpr, 'tpr': cov_tpr, 'auc': cov_auc},
        'residual': {'fpr': res_fpr, 'tpr': res_tpr, 'auc': res_auc}
    }
    
    print(f"  H¹ detector AUC:        {h1_auc:.4f}")
    print(f"  Covariance detector AUC: {cov_auc:.4f}")
    print(f"  Residual detector AUC:   {res_auc:.4f}")
    
    # Find optimal operating point (max TPR - FPR)
    youden_h1 = max([t - f for t, f in zip(h1_tpr, h1_fpr)])
    youden_cov = max([t - f for t, f in zip(cov_tpr, cov_fpr)])
    youden_res = max([t - f for t, f in zip(res_tpr, res_fpr)])
    
    print(f"  H¹ Youden index:        {youden_h1:.4f}")
    print(f"  Covariance Youden index: {youden_cov:.4f}")
    print(f"  Residual Youden index:   {youden_res:.4f}")
    
    # =========================================================================
    # Multi-Resolution Analysis
    # =========================================================================
    print("\n" + "-" * 70)
    print("Multi-Resolution Sheaf Analysis")
    print("-" * 70)
    
    mr_results = {}
    for label, t_start, t_end in failure_labels:
        i_start = int(t_start / dt)
        i_end = int(t_end / dt)
        
        coarse_window = h1_coarse[i_start:i_end]
        medium_window = h1_medium[i_start:i_end]
        fine_window = h1_fine[i_start:i_end]
        combined_window = h1_combined[i_start:i_end]
        
        mr_results[label] = {
            'coarse_mean': float(np.mean(coarse_window)),
            'medium_mean': float(np.mean(medium_window)),
            'fine_mean': float(np.mean(fine_window)),
            'combined_mean': float(np.mean(combined_window)),
        }
        
        c = mr_results[label]['coarse_mean']
        m = mr_results[label]['medium_mean']
        f = mr_results[label]['fine_mean']
        print(f"  {label:35s} | C={c:.6f} | M={m:.6f} | F={f:.6f}")
    
    # =========================================================================
    # Zero False Positive Check
    # =========================================================================
    print("\n" + "-" * 70)
    print("Zero False Positive Validation")
    print("-" * 70)
    
    normal_mask = (ground_truth == 0)
    h1_normal = np.array(h1_scores)[normal_mask]
    cov_normal = np.array(cov_scores)[normal_mask]
    res_normal = np.array(res_scores)[normal_mask]
    
    h1_false_positives = np.sum(h1_normal > 1e-6)
    cov_false_positives = np.sum(cov_normal > 3.0)
    res_false_positives = np.sum(res_normal > 3.0)
    
    total_normal = np.sum(normal_mask)
    
    print(f"  Total normal data points: {total_normal}")
    print(f"  H¹ false positives:        {h1_false_positives} / {total_normal} ({100*h1_false_positives/max(total_normal,1):.4f}%)")
    print(f"  Covariance false positives: {cov_false_positives} / {total_normal} ({100*cov_false_positives/max(total_normal,1):.4f}%)")
    print(f"  Residual false positives:   {res_false_positives} / {total_normal} ({100*res_false_positives/max(total_normal,1):.4f}%)")
    
    h1_zero_fp = (h1_false_positives == 0)
    
    # =========================================================================
    # Compile Full Results
    # =========================================================================
    all_results = {
        'experiment': 'sensor_fusion_v2',
        'settings': {
            'duration': T,
            'dt': dt,
            'k_factor': 3.0,
            'window_size': 100
        },
        'failure_injection': {
            'bias': {'start': 90, 'end': 100, 'magnitude': 2.0},
            'delay': {'start': 130, 'end': 140, 'delay_ms': 200},
            'gps_fail': {'start': 260, 'end': 270},
            'noise_anomaly': {'start': 275, 'end': 285, 'factor': 8.0}
        },
        'phase_analysis': results_summary,
        'multi_resolution': mr_results,
        'detection_latency': latency_data,
        'roc': roc_data,
        'zero_false_positives': bool(h1_zero_fp),
        'h1_false_positive_count': int(h1_false_positives),
        'cov_false_positive_count': int(cov_false_positives),
        'res_false_positive_count': int(res_false_positives),
        'total_normal_points': int(total_normal),
        'overall_pass': bool(
            h1_auc > cov_auc and
            h1_auc > res_auc and
            h1_zero_fp
        )
    }
    
    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, 'fusion_results_v2.json')
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {json_path}")
    
    # =========================================================================
    # Generate ROC plot data as JSON (for plotting)
    # =========================================================================
    plot_data = {
        'h1': {'fpr': h1_fpr, 'tpr': h1_tpr},
        'covariance': {'fpr': cov_fpr, 'tpr': cov_tpr},
        'residual': {'fpr': res_fpr, 'tpr': res_tpr},
    }
    plot_path = os.path.join(OUTPUT_DIR, 'roc_plot_data.json')
    with open(plot_path, 'w') as f:
        json.dump(plot_data, f, indent=2)
    
    # Save time series data
    ts_data = {
        'time': time.tolist(),
        'ground_truth': ground_truth.tolist(),
        'h1_scores': h1_scores,
        'cov_scores': cov_scores,
        'res_scores': res_scores,
        'h1_coarse': h1_coarse,
        'h1_medium': h1_medium,
        'h1_fine': h1_fine,
        'h1_combined': h1_combined,
    }
    ts_path = os.path.join(OUTPUT_DIR, 'time_series_data.json')
    with open(ts_path, 'w') as f:
        json.dump(ts_data, f, indent=2)
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("OVERALL RESULT")
    print("=" * 70)
    
    if all_results['overall_pass']:
        print("  ✅ PASS - All criteria met")
    else:
        print("  ⚠️  PARTIAL - Some criteria not met")
    
    print(f"\n  Zero false positives: {h1_zero_fp}")
    print(f"  H¹ AUC: {h1_auc:.4f} (target: > covariance and residual)")
    print(f"  Covariance AUC: {cov_auc:.4f}")
    print(f"  Residual AUC: {res_auc:.4f}")
    
    return all_results


if __name__ == '__main__':
    run_experiment()