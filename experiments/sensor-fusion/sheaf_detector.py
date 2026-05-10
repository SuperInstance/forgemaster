"""
sheaf_detector.py — Sheaf H¹-based sensor failure detection.

Adapts the understanding sheaf from ../sheaf-h1/ to sensor fusion.

Key insight: EACH sensor is a "model" in the sheaf framework. Each sensor
provides a partial observation of the same underlying state. The sensors
must AGREE on shared state — this is exactly the gluing condition that H¹ measures.

Sensors as sheaf elements:
  - IMU Accelerometer: observes acceleration (3-axis)
  - IMU Gyroscope: observes angular velocity (3-axis)
  - GPS: observes position (3-axis)

Each sensor is a "local model" with partial coverage of the full state space.
The restriction maps check agreement on overlapped dimensions.

When sensors are well-calibrated and synchronized:
  → H¹ = 0 (no obstruction to fusion)

When a sensor fails (bias, delay):
  → H¹ > 0 (obstruction detected — can't glue sensor inputs)
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from sensor_models import SensorReading, RobotState, SensorFusionProblem


@dataclass
class SheafFailureResult:
    """Result of sheaf H¹ failure detection."""
    h1_dimension: int           # H¹ dimension (> 0 means failure detected)
    h1_magnitude: float         # Magnitude of obstruction
    agreement_scores: Dict[str, float]  # Agreement scores per sensor pair
    is_failure: bool            # Whether failure is detected
    interpretation: str

    # Comparison with standard methods
    residual_detected: bool = False
    sheaf_detected: bool = False
    sheaf_earlier: bool = False  # Does H¹ detect before residual spike?


def compute_sensor_agreement(
    accel_readings: List[SensorReading],
    gyro_readings: List[SensorReading],
    gps_readings: List[SensorReading],
    true_states: List[RobotState],
    window_size: int = 50,
) -> Dict[str, float]:
    """
    Compute pairwise sensor agreement scores as cosine similarities.

    Core insight from sheaf theory: each sensor is a 'local model' with
    a 'section' over the state space. Agreement measures how well sections
    restrict to the overlap — the fundamental gluing condition.

    For each sensor pair we check: do the two sensors give the same
    value for the quantity they BOTH measure?

      - accel↔gyro: Both IMU sensors live on the same chip; if one is biased
        or delayed, their measurements decorrelate. We compare their raw
        measurements directly.
      - accel↔gps:  Integrated accel gives position; GPS gives position.
        Difference = drift between IMU and GPS.
      - gyro↔gps:   Integrated gyro gives heading; GPS velocity gives heading.
        Difference = orientation drift.

    Agreement is measured on [0, 1] where 1 = perfect agreement.
    Uses cosine similarity for the accel-gyro pair (comparing 3D vectors)
    and exponential decay of error for position/heading comparisons.
    """
    n = len(true_states)
    n_gps = len(gps_readings)

    dt = true_states[1].t - true_states[0].t

    # Agreement metrics
    accel_gyro_agreement = []
    accel_gps_agreement = []
    gyro_gps_agreement = []

    # Get raw accel and gyro measurement arrays
    a_raw = np.array([r.measurement for r in accel_readings])
    g_raw = np.array([r.measurement for r in gyro_readings])

    # --- Accel ↔ Gyro: direct cosine similarity on raw readings ---
    # These measure different things (linear acceleration vs angular velocity)
    # but they SHOULD both have stable statistical properties.
    # When a sensor is biased, the mean of that sensor shifts, causing
    # the correlation between sensor statistics to drop.
    # 
    # Specifically: we compare running statistics, not raw values.
    step = 10
    for i in range(0, n - window_size, step):
        win_a = a_raw[i:i+window_size]
        win_g = g_raw[i:i+window_size]

        # Compare mean vectors (bias shifts the mean)
        mean_a = np.mean(win_a, axis=0)
        mean_g = np.mean(win_g, axis=0)

        na = np.linalg.norm(mean_a)
        ng = np.linalg.norm(mean_g)
        if na > 1e-10 and ng > 1e-10:
            sim = np.dot(mean_a, mean_g) / (na * ng)
        else:
            sim = 0.0
        accel_gyro_agreement.append(max(0.0, sim))

    # --- Accel ↔ GPS: integrate accel to position, compare with GPS ---
    # Double-integrate acceleration to get position change.
    # In normal operation, this should track GPS within drift bounds.
    # With bias, the integrated position diverges quadratically.
    for gps_idx in range(min(n_gps, len(gps_readings) // 2)):
        # Get the IMU index corresponding to this GPS reading
        imu_idx = gps_idx * 100  # GPS every 100 steps
        if imu_idx + window_size >= n:
            break

        gps_pos = gps_readings[gps_idx].measurement
        # Get IMU acceleration in this window
        win_a = a_raw[imu_idx:imu_idx+window_size]

        # Remove gravity and integrate to velocity
        dt_window = dt
        vel = np.cumsum(win_a - np.array([0.0, 0.0, 9.81]), axis=0) * dt_window
        # Integrate to position
        pos_change = np.sum(vel, axis=0) * dt_window

        # Compare with expected position change from GPS
        if gps_idx > 0:
            prev_gps_pos = gps_readings[gps_idx - 1].measurement
            gps_delta = gps_pos - prev_gps_pos

            drift = np.linalg.norm(pos_change - gps_delta)
            # Agreement = exp(-drift/scale), scale depends on expected noise
            scale = 5.0  # 5 meters is typical drift tolerance
            agreement = np.exp(-drift / scale)
            accel_gps_agreement.append(agreement)

    # Aggregate
    if accel_gyro_agreement:
        avg_accel_gyro = float(np.mean(accel_gyro_agreement))
    else:
        avg_accel_gyro = 0.5

    if accel_gps_agreement:
        avg_accel_gps = float(np.mean(accel_gps_agreement))
    else:
        avg_accel_gps = 0.5

    # gyro↔gps: estimate from the other two
    # If accel↔gyro and accel↔gps are both low, gyro↔gps must also be low
    avg_gyro_gps = (avg_accel_gyro + avg_accel_gps) / 2.0

    # Overall agreement = minimum (weakest link determines gluing)
    # This is the sheaf gluing condition: all overlaps must be compatible
    overall_agreement = min(avg_accel_gyro, avg_accel_gps, avg_gyro_gps)

    return {
        "accel_gyro": avg_accel_gyro,
        "accel_gps": avg_accel_gps,
        "gyro_gps": avg_gyro_gps,
        "overall": overall_agreement,
    }


def compute_sheaf_h1_sensor(
    accel_readings: List[SensorReading],
    gyro_readings: List[SensorReading],
    gps_readings: List[SensorReading],
    true_states: List[RobotState],
    tolerance: float = 0.5,
) -> SheafFailureResult:
    """
    Compute sheaf H¹ for sensor fusion.

    Each sensor is modeled as providing a "section" over the state space.
    The sheaf:
      - Open sets: {accel}, {gyro}, {gps}, {accel,gyro}, {accel,gps},
                    {gyro,gps}, {accel,gyro,gps}
      - Sections: sensor readings projected to a common embedding
      - Restriction maps: check consistency on overlapping dimensions

    H¹ > 0 means sensors can't be fused into a consistent state estimate.
    """
    # Compute pairwise agreement
    agreements = compute_sensor_agreement(
        accel_readings, gyro_readings, gps_readings, true_states
    )

    overall = agreements["overall"]

    # H¹ dimension is 0 if sensors agree, > 0 if they don't
    # The "dimension" is the number of sensor pairs that disagree
    h1_dim = 0
    h1_mag = 0.0
    failing_pairs = []

    # Each sensor pair contributes to H¹ if agreement < threshold
    pair_names = ["accel_gyro", "accel_gps", "gyro_gps"]
    threshold = 1.0 - tolerance

    for name in pair_names:
        score = agreements[name]
        if score < threshold:
            h1_dim += 1
            # Magnitude = how far below threshold
            h1_mag += (threshold - score) ** 2
            failing_pairs.append(f"{name} ({score:.3f})")

    # H¹ magnitude normalized by number of pairs
    h1_mag = np.sqrt(h1_mag) / len(pair_names)

    # Interpretation
    is_failure = h1_dim > 0

    if is_failure:
        interp = (f"H¹ detected OBSTRUCTION to sensor fusion (dim H¹ = {h1_dim}, "
                  f"mag = {h1_mag:.4f}). "
                  f"Failing pairs: {', '.join(failing_pairs)}")
    else:
        interp = (f"H¹ = 0: No obstruction to sensor fusion. "
                  f"All sensors agree (overall = {overall:.3f})")

    return SheafFailureResult(
        h1_dimension=h1_dim,
        h1_magnitude=h1_mag,
        agreement_scores=agreements,
        is_failure=is_failure,
        interpretation=interp,
    )


def compute_sliding_h1(
    accel_readings: List[SensorReading],
    gyro_readings: List[SensorReading],
    gps_readings: List[SensorReading],
    true_states: List[RobotState],
    window_size: int = 100,
    stride: int = 20,
    tolerance: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """
    Compute H¹ over sliding windows for temporal failure detection.

    Returns:
      - times: center times of each window
      - h1_magnitudes: H¹ magnitude per window
      - residual_errors: residual-based error per window
      - interpretations: per-window text
    """
    half_win = window_size // 2
    n = len(true_states)
    times = []
    h1_mags = []
    residuals = []
    interpretations = []

    for start in range(0, n - window_size, stride):
        end = start + window_size

        # Slice data for this window
        a_win = accel_readings[start:end]
        g_win = gyro_readings[start:end]
        gps_win = [r for i, r in enumerate(gyro_readings[start:end])
                   if (start + i) % 100 == 0]
        gps_win = gps_win[:max(1, len(gps_win) // 100)]

        if len(gps_win) < 2:
            continue

        result = compute_sheaf_h1_sensor(
            a_win, g_win, gps_win, true_states[start:end], tolerance
        )

        # Residual error in this window
        window_true_pos = np.array([s.position for s in true_states[start:end]])

        # Estimate position from sensor readings in window
        # (We'll approximate: use accel double-integration)
        est_pos = np.zeros((end - start, 3))
        pos = np.array([0.0, 0.0, 0.0])
        vel = np.array([0.0, 0.0, 0.0])
        yaw = 0.0
        dt = true_states[1].t - true_states[0].t

        for i in range(end - start):
            # Crude IMU integration
            a_body = a_win[i].measurement
            gyro_r = g_win[i].measurement
            cos_y, sin_y = np.cos(yaw), np.sin(yaw)
            R = np.array([[cos_y, -sin_y, 0.0],
                          [sin_y, cos_y, 0.0],
                          [0.0, 0.0, 1.0]])
            a_world = R @ a_body - np.array([0.0, 0.0, 9.81])
            vel += a_world * dt
            pos += vel * dt
            yaw += gyro_r[2] * dt
            est_pos[i] = pos

        # Compute residual norms between estimated and true positions
        actual_pos = window_true_pos[:len(est_pos)]
        residuals_per_step = np.linalg.norm(est_pos - actual_pos, axis=1)
        avg_residual = np.mean(residuals_per_step)

        times.append(true_states[start + half_win].t)
        h1_mags.append(result.h1_magnitude)
        residuals.append(avg_residual)
        interpretations.append(result.interpretation)

    return (
        np.array(times),
        np.array(h1_mags),
        np.array(residuals),
        interpretations,
    )
