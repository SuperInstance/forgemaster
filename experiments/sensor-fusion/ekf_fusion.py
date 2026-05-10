"""
ekf_fusion.py — Extended Kalman Filter for 3-sensor fusion.

Fuses IMU accelerometer, IMU gyroscope, and GPS into a single state estimate.

State vector: [x, y, z, vx, vy, vz, roll, pitch, yaw] (9-dim)
  - Position (3): from GPS
  - Velocity (3): from accelerometer integration
  - Orientation (3): from gyroscope integration

The EKF:
  1. PREDICT: IMU-driven state propagation
  2. UPDATE: GPS position correction
  3. Compares to ground truth for error analysis
"""

import numpy as np
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from sensor_models import RobotState, SensorReading, SensorFusionProblem


@dataclass
class EKFState:
    """EKF internal state."""
    x: np.ndarray           # State vector (9,)
    P: np.ndarray           # Covariance matrix (9, 9)
    t: float                # Current time
    step: int               # Current step


@dataclass
class EKFResult:
    """Result of EKF fusion run."""
    estimated_positions: np.ndarray  # (n_steps, 3)
    estimated_velocities: np.ndarray # (n_steps, 3)
    estimated_orientations: np.ndarray # (n_steps, 3)
    true_positions: np.ndarray       # (n_steps, 3)
    position_errors: np.ndarray      # (n_steps,) — RMSE per step
    covariances: np.ndarray          # (n_steps, 9, 9)
    innovations: np.ndarray          # GPS innovation vectors
    times: np.ndarray                # (n_steps,)


class SensorFusionEKF:
    """
    Extended Kalman Filter for IMU + GPS fusion.

    State: [px, py, pz, vx, vy, vz, roll, pitch, yaw]^T
    Control: IMU acceleration + angular velocity
    Measurement: GPS position (x, y, z)
    """

    def __init__(
        self,
        problem: SensorFusionProblem,
        process_noise_scale: float = 1.0,
        init_cov_scale: float = 1.0,
    ):
        self.problem = problem
        self.dt = problem.dt

        # State dimension
        self.nx = 9  # [pos(3), vel(3), orientation(3)]

        # Process noise covariance
        self.Q = np.eye(self.nx)
        # Position process noise: random walk
        self.Q[0:3, 0:3] *= 0.001 * process_noise_scale
        # Velocity process noise: acceleration uncertainty
        self.Q[3:6, 3:6] *= 0.01 * process_noise_scale
        # Orientation process noise: angular velocity uncertainty
        self.Q[6:9, 6:9] *= 0.0001 * process_noise_scale

        # Measurement noise covariance (GPS)
        gps_noise = problem.gps_cal.noise_std
        self.R_gps = np.eye(3) * (gps_noise ** 2)

        # Initial state from first GPS reading
        self.initialized = False

    def _init_state(self, gps_reading: SensorReading) -> EKFState:
        """Initialize EKF state from first GPS reading."""
        x0 = np.zeros(self.nx)
        # Position from GPS
        x0[0:3] = gps_reading.measurement - self.problem.gps_cal.bias
        # Velocity: assume 0
        x0[3:6] = np.zeros(3)
        # Orientation: assume 0
        x0[6:9] = np.zeros(3)

        # Initial covariance
        P0 = np.eye(self.nx)
        P0[0:3, 0:3] *= 1.0  # position uncertainty (GPS)
        P0[3:6, 3:6] *= 10.0  # velocity uncertainty (unknown)
        P0[6:9, 6:9] *= 1.0   # orientation uncertainty

        return EKFState(x=x0, P=P0, t=0.0, step=0)

    def _measurement_function(self, x: np.ndarray) -> np.ndarray:
        """Measurement prediction: h(x) = position (xyz)."""
        return x[0:3]

    def _measurement_jacobian(self, x: np.ndarray) -> np.ndarray:
        """Jacobian of measurement function: H = ∂h/∂x."""
        H = np.zeros((3, self.nx))
        H[0:3, 0:3] = np.eye(3)  # ∂pos/∂pos = I
        return H

    def predict(
        self,
        state: EKFState,
        accel: SensorReading,
        gyro: SensorReading,
    ) -> EKFState:
        """
        EKF PREDICT step using IMU measurements.

        State transition: x_{k+1} = f(x_k, u_k)
        where u_k = [accel_body, gyro_body]

        Position: p += v * dt + 0.5 * R * accel * dt²
        Velocity: v += R * accel_body * dt
        Orientation: q += omega * dt
        """
        dt = self.dt

        # Extract states
        pos = state.x[0:3]
        vel = state.x[3:6]
        ori = state.x[6:9]  # [roll, pitch, yaw]

        # Extract IMU measurements
        accel_body = accel.measurement - self.problem.accel_cal.bias
        omega_body = gyro.measurement - self.problem.gyro_cal.bias

        # Subtract gravity from accelerometer
        # Accel in body frame: a_body = R^T * (a_world + g)
        # So a_world = R * a_body - g
        yaw = ori[2]
        cos_y, sin_y = np.cos(yaw), np.sin(yaw)
        R = np.array([
            [cos_y, -sin_y, 0.0],
            [sin_y,  cos_y, 0.0],
            [0.0,    0.0,   1.0],
        ])

        # Convert body acceleration to world frame
        g = np.array([0.0, 0.0, 9.81])
        accel_world = R @ accel_body
        accel_world -= g  # Subtract gravity

        # Kinematics integration (semi-implicit Euler)
        new_vel = vel + accel_world * dt
        new_pos = pos + new_vel * dt  # use new velocity for better stability

        # Orientation integration
        new_ori = ori + omega_body * dt

        # Build new state
        new_x = np.zeros(self.nx)
        new_x[0:3] = new_pos
        new_x[3:6] = new_vel
        new_x[6:9] = new_ori

        # Compute state transition Jacobian
        # F = ∂f/∂x
        F = np.eye(self.nx)

        # ∂pos/∂vel = I * dt
        F[0:3, 3:6] = np.eye(3) * dt

        # ∂vel/∂accel_world = I * dt  (accel depends on orientation)
        # ∂accel_world/∂yaw = ∂(R*a_body)/∂yaw
        # For yaw rotation: dR/dyaw * a_body
        da_dyaw = dt * np.array([
            [-sin_y * accel_body[0] - cos_y * accel_body[1]],
            [cos_y * accel_body[0] - sin_y * accel_body[1]],
            [0.0]
        ]).flatten()
        # Also ∂pos/∂yaw = dt²/2 * da_dyaw (accel contribution already in vel)
        F[0:3, 8] = da_dyaw  # velocity contribution to position
        F[3:6, 8] = da_dyaw / dt  # acceleration contribution to velocity

        # Covariance prediction
        new_P = F @ state.P @ F.T + self.Q

        return EKFState(x=new_x, P=new_P, t=state.t, step=state.step + 1)

    def update_gps(
        self,
        state: EKFState,
        gps_reading: SensorReading,
    ) -> EKFState:
        """
        EKF UPDATE step using GPS measurement.

        z = GPS position measurement
        h(x) = position (xyz)
        """
        z = gps_reading.measurement - self.problem.gps_cal.bias

        # Measurement prediction
        H = self._measurement_jacobian(state.x)
        h = self._measurement_function(state.x)

        # Innovation
        y = z - h  # (3,)

        # Innovation covariance
        S = H @ state.P @ H.T + self.R_gps  # (3, 3)

        # Kalman gain
        K = state.P @ H.T @ np.linalg.inv(S)  # (9, 3)

        # State update
        new_x = state.x + K @ y
        new_P = (np.eye(self.nx) - K @ H) @ state.P

        return EKFState(x=new_x, P=new_P, t=state.t, step=state.step + 1)

    def run(
        self,
        readings: dict,
        ground_truth: List[RobotState],
    ) -> EKFResult:
        """
        Run the full EKF fusion on a sensor readings dataset.

        Args:
            readings: dict with keys "accel", "gyro", "gps"
            ground_truth: list of RobotState for comparison

        Returns:
            EKFResult with full fusion history
        """
        n_steps = len(ground_truth)
        gps_idx = 0

        # Storage
        est_positions = np.zeros((n_steps, 3))
        est_velocities = np.zeros((n_steps, 3))
        est_orientations = np.zeros((n_steps, 3))
        true_positions = np.array([s.position for s in ground_truth])
        position_errors = np.zeros(n_steps)
        covariances = np.zeros((n_steps, self.nx, self.nx))
        innovations = []
        times = np.array([s.t for s in ground_truth])

        state = None

        for step in range(n_steps):
            true_state = ground_truth[step]
            accel = readings["accel"][step]
            gyro = readings["gyro"][step]

            # On first GPS reading, initialize
            if not self.initialized:
                if (step % self.problem.gps_every_n == 0 and
                        gps_idx < len(readings["gps"])):
                    gps = readings["gps"][gps_idx]
                    state = self._init_state(gps)
                    self.initialized = True
                    gps_idx += 1
                else:
                    continue

            # Predict step (using IMU)
            state = self.predict(state, accel, gyro)

            # Update step (using GPS, when available)
            if (step % self.problem.gps_every_n == 0 and
                    gps_idx < len(readings["gps"])):
                gps = readings["gps"][gps_idx]
                state = self.update_gps(state, gps)
                innovations.append({
                    "step": step,
                    "time": true_state.t,
                    "innovation": state.x[0:3] - gps.measurement,
                })
                gps_idx += 1

            # Store
            est_positions[step] = state.x[0:3]
            est_velocities[step] = state.x[3:6]
            est_orientations[step] = state.x[6:9]
            position_errors[step] = np.linalg.norm(
                state.x[0:3] - true_state.position
            )
            covariances[step] = state.P

        return EKFResult(
            estimated_positions=est_positions,
            estimated_velocities=est_velocities,
            estimated_orientations=est_orientations,
            true_positions=true_positions,
            position_errors=position_errors,
            covariances=covariances,
            innovations=innovations,
            times=times,
        )


# ============================================================
# Baseline Comparison: Dead Reckoning (no GPS correction)
# ============================================================

def dead_reckoning(
    problem: SensorFusionProblem,
    readings: dict,
    ground_truth: List[RobotState],
    gps_initialized: bool = True,
) -> np.ndarray:
    """
    Pure IMU dead-reckoning (no GPS correction).

    Used as baseline comparison for the EKF fusion.
    Returns position estimates over time.

    If gps_initialized=True, starts from first GPS position.
    """
    dt = problem.dt
    n_steps = len(ground_truth)

    # Get initial position from ground truth if GPS initialized
    if gps_initialized and len(readings.get("gps", [])) > 0:
        first_gps = readings["gps"][0].measurement
        pos = first_gps.copy()
    else:
        pos = ground_truth[0].position.copy()
    vel = np.array([0.0, 0.0, 0.0])
    yaw = 0.0

    positions = np.zeros((n_steps, 3))

    for step in range(n_steps):
        accel = readings["accel"][step]
        gyro = readings["gyro"][step]

        # Remove bias
        accel_body = accel.measurement - problem.accel_cal.bias
        omega = gyro.measurement - problem.gyro_cal.bias

        # Body to world
        cos_y, sin_y = np.cos(yaw), np.sin(yaw)
        R = np.array([
            [cos_y, -sin_y, 0.0],
            [sin_y,  cos_y, 0.0],
            [0.0,    0.0,   1.0],
        ])

        g = np.array([0.0, 0.0, 9.81])
        accel_world = R @ accel_body - g

        # Integrate
        vel += accel_world * dt
        pos += vel * dt
        yaw += omega[2] * dt

        positions[step] = pos

    return positions


# ============================================================
# Sheaf-based failure detector (simple version for full comparison later)
# ============================================================

def compute_residual_based_detector(
    result: EKFResult,
    window: int = 50,
) -> np.ndarray:
    """
    Standard residual-based failure detection.

    Tracks the running RMSE — spikes indicate sensor failure.
    Returns the log-RMSE (smoothed) for comparison with H¹.
    """
    errors = result.position_errors
    smoothed = np.zeros(len(errors))

    for i in range(len(errors)):
        start = max(0, i - window)
        end = min(len(errors), i + window)
        smoothed[i] = np.sqrt(np.mean(errors[start:end]**2))

    return smoothed
