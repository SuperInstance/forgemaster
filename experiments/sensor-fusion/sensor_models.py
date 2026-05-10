"""
sensor_models.py — Realistic sensor models for the fusion experiment.

Three sensor types:
  1. IMU Accelerometer — measures linear acceleration (3-axis)
  2. IMU Gyroscope    — measures angular velocity (3-axis)
  3. GPS              — measures absolute position (3-axis)

Each sensor provides partial, noisy information about the robot's true state.
The sensors must be FUSED — exactly the kind of multi-model composition
that our constraint-theory math (sheaf H¹, holonomy, Eisenstein lattices) addresses.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable


@dataclass
class RobotState:
    """True state of the robot at a point in time."""
    t: float                # time (seconds)
    position: np.ndarray    # (3,) — x, y, z position (meters)
    velocity: np.ndarray    # (3,) — linear velocity (m/s)
    orientation: np.ndarray # (3,) — roll, pitch, yaw (radians)
    omega: np.ndarray       # (3,) — angular velocity (rad/s)
    acceleration: np.ndarray # (3,) — linear acceleration (m/s²)


@dataclass
class SensorReading:
    """A single sensor reading with metadata."""
    sensor_id: str          # "accel", "gyro", "gps"
    t: float                # timestamp
    measurement: np.ndarray # The actual measurement vector
    true_value: np.ndarray  # Ground truth (for evaluation)
    bias: np.ndarray        # Systematic bias applied
    noise_std: float        # Noise standard deviation


@dataclass
class SensorCalibration:
    """Calibration parameters for a sensor."""
    bias: np.ndarray        # Systematic bias vector
    noise_std: float        # Measurement noise standard deviation
    scale_factor: float     # Scale factor (1.0 = perfect)
    delay: float            # Time delay in seconds (0 = none)


# ============================================================
# True Trajectory Generator
# ============================================================

def generate_trajectory(
    duration: float = 30.0,
    dt: float = 0.01,
    seed: int = 42,
    trajectory_type: str = "figure8",
) -> List[RobotState]:
    """
    Generate a ground-truth robot trajectory.

    Options:
      - "figure8": Figure-8 path in x-y plane with constant z
      - "loop":   Simple circular loop (for holonomy experiment)
      - "random": Random acceleration profile
    """
    rng = np.random.RandomState(seed)
    n_steps = int(duration / dt)
    states = []

    t = 0.0
    pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    vel = np.array([0.5, 0.0, 0.0], dtype=np.float64)
    roll, pitch, yaw = 0.0, 0.0, 0.0
    omega = np.array([0.0, 0.0, 0.0], dtype=np.float64)

    if trajectory_type == "figure8":
        # Figure-8: x = A*sin(ωt), y = A*sin(2ωt)
        A = 5.0
        omega_traj = 0.5

        for step in range(n_steps):
            t = step * dt

            # True position
            px = A * np.sin(omega_traj * t)
            py = A * np.sin(2.0 * omega_traj * t)
            pz = 0.0

            # Velocity (analytic derivative)
            vx = A * omega_traj * np.cos(omega_traj * t)
            vy = 2.0 * A * omega_traj * np.cos(2.0 * omega_traj * t)
            vz = 0.0

            # Acceleration (analytic second derivative)
            ax = -A * omega_traj**2 * np.sin(omega_traj * t)
            ay = -4.0 * A * omega_traj**2 * np.sin(2.0 * omega_traj * t)
            az = 0.0

            # Orientation (yaw follows velocity direction)
            yaw = np.arctan2(vy, vx)
            # Angular velocity
            yaw_rate = (2.0 * omega_traj * np.cos(2.0 * omega_traj * t) *
                        np.cos(omega_traj * t) - omega_traj * np.sin(omega_traj * t) *
                        np.sin(2.0 * omega_traj * t)) / (vy**2 + vx**2 + 1e-10)
            omega = np.array([0.0, 0.0, yaw_rate])

            states.append(RobotState(
                t=t,
                position=np.array([px, py, pz]),
                velocity=np.array([vx, vy, vz]),
                orientation=np.array([roll, pitch, yaw]),
                omega=omega.copy(),
                acceleration=np.array([ax, ay, az]),
            ))

    elif trajectory_type == "loop":
        # Circular loop — start and end at same point
        radius = 5.0
        angular_speed = 0.3

        for step in range(n_steps):
            t = step * dt
            theta = angular_speed * t

            px = radius * np.cos(theta)
            py = radius * np.sin(theta)
            pz = 0.0

            vx = -radius * angular_speed * np.sin(theta)
            vy = radius * angular_speed * np.cos(theta)
            vz = 0.0

            ax = -radius * angular_speed**2 * np.cos(theta)
            ay = -radius * angular_speed**2 * np.sin(theta)
            az = 0.0

            yaw = np.arctan2(vy, vx)
            omega = np.array([0.0, 0.0, angular_speed])

            states.append(RobotState(
                t=t,
                position=np.array([px, py, pz]),
                velocity=np.array([vx, vy, vz]),
                orientation=np.array([roll, pitch, yaw]),
                omega=omega.copy(),
                acceleration=np.array([ax, ay, az]),
            ))

    else:  # random
        acc_profile = 2.0 * rng.randn(n_steps, 3) * 0.1
        acc_profile = np.cumsum(acc_profile, axis=0) * dt  # smooth random walk

        for step in range(n_steps):
            t = step * dt
            if step == 0:
                continue

            # Integrate from previous
            dt_actual = dt
            vel = states[-1].velocity + acc_profile[step] * dt_actual
            pos = states[-1].position + vel * dt_actual
            yaw = np.arctan2(vel[1], vel[0])

            states.append(RobotState(
                t=t,
                position=pos.copy(),
                velocity=vel.copy(),
                orientation=np.array([roll, pitch, yaw]),
                omega=np.array([0.0, 0.0, 0.0]),
                acceleration=acc_profile[step].copy(),
            ))

    return states


# ============================================================
# Sensor Models
# ============================================================

def simulate_accelerometer(
    true_state: RobotState,
    cal: SensorCalibration,
    rng: np.random.RandomState,
) -> SensorReading:
    """
    Simulate an IMU accelerometer reading.

    True measurement: acceleration in body frame + gravity compensation.
    Measurement model: z = S * (R^T * (a_true + g)) + b + noise

    Where:
      S = scale factor
      R = rotation matrix (body to world = orientation)
      g = gravity vector
      b = bias
    """
    # Gravity in world frame
    g = np.array([0.0, 0.0, 9.81])

    # Rotation matrix from body to world (simplified: just yaw)
    yaw = true_state.orientation[2]
    R = np.array([
        [np.cos(yaw), -np.sin(yaw), 0.0],
        [np.sin(yaw),  np.cos(yaw), 0.0],
        [0.0,          0.0,         1.0],
    ])

    # True acceleration in world frame
    a_true = true_state.acceleration

    # Transform to body frame and subtract gravity
    a_body = R.T @ (a_true + g)

    # Apply sensor model
    measurement = cal.scale_factor * a_body + cal.bias + \
                  cal.noise_std * rng.randn(3)

    return SensorReading(
        sensor_id="accel",
        t=true_state.t,
        measurement=measurement,
        true_value=a_body,
        bias=cal.bias,
        noise_std=cal.noise_std,
    )


def simulate_gyroscope(
    true_state: RobotState,
    cal: SensorCalibration,
    rng: np.random.RandomState,
) -> SensorReading:
    """
    Simulate an IMU gyroscope reading.

    True measurement: angular velocity in body frame.
    Measurement model: z = S * omega + b + noise
    """
    omega_body = true_state.omega  # already in body frame

    measurement = cal.scale_factor * omega_body + cal.bias + \
                  cal.noise_std * rng.randn(3)

    return SensorReading(
        sensor_id="gyro",
        t=true_state.t,
        measurement=measurement,
        true_value=omega_body,
        bias=cal.bias,
        noise_std=cal.noise_std,
    )


def simulate_gps(
    true_state: RobotState,
    cal: SensorCalibration,
    rng: np.random.RandomState,
) -> SensorReading:
    """
    Simulate a GPS reading.

    True measurement: absolute position (x, y, z).
    Measurement model: z = S * position + b + noise

    GPS typically has:
      - No significant bias (or slowly varying)
      - Higher noise std (~1-3m)
      - Lower update rate (handled outside this function)
    """
    measurement = cal.scale_factor * true_state.position + cal.bias + \
                  cal.noise_std * rng.randn(3)

    return SensorReading(
        sensor_id="gps",
        t=true_state.t,
        measurement=measurement,
        true_value=true_state.position,
        bias=cal.bias,
        noise_std=cal.noise_std,
    )


# ============================================================
# Sensor Fusion Problem Definition
# ============================================================

@dataclass
class SensorFusionProblem:
    """Defines the complete sensor fusion problem."""

    trajectory: List[RobotState]
    dt: float

    # Calibrations
    accel_cal: SensorCalibration
    gyro_cal: SensorCalibration
    gps_cal: SensorCalibration

    # GPS update rate (every N time steps)
    gps_every_n: int = 100

    # Whether to add time synchronization error
    accel_delay_steps: int = 0
    gyro_delay_steps: int = 0
    gps_delay_steps: int = 0

    def generate_readings(self, seed: int = 42) -> dict:
        """Generate all sensor readings for this problem."""
        rng = np.random.RandomState(seed)
        n_steps = len(self.trajectory)

        # Apply time delay by shifting indices
        accel_states = self._apply_delay(self.trajectory, self.accel_delay_steps)
        gyro_states = self._apply_delay(self.trajectory, self.gyro_delay_steps)
        gps_states = self._apply_delay(self.trajectory, self.gps_delay_steps)

        readings = {
            "accel": [],
            "gyro": [],
            "gps": [],
        }

        for step in range(n_steps):
            # IMU sensors at full rate
            accel_reading = simulate_accelerometer(
                accel_states[step], self.accel_cal, rng
            )
            gyro_reading = simulate_gyroscope(
                gyro_states[step], self.gyro_cal, rng
            )
            readings["accel"].append(accel_reading)
            readings["gyro"].append(gyro_reading)

            # GPS at lower rate
            if step % self.gps_every_n == 0:
                gps_reading = simulate_gps(
                    gps_states[step], self.gps_cal, rng
                )
                readings["gps"].append(gps_reading)

        return readings

    def _apply_delay(self, states, delay_steps):
        """Apply time delay by prepending zeros and trimming end."""
        if delay_steps == 0:
            return states
        # Pad with first state, then shift
        padded = [states[0]] * delay_steps + states
        return padded[:len(states)]


def create_default_problem(
    trajectory_type: str = "figure8",
    duration: float = 30.0,
    dt: float = 0.01,
    seed: int = 42,
) -> SensorFusionProblem:
    """Create a sensor fusion problem with default calibrations."""

    traj = generate_trajectory(duration=duration, dt=dt, seed=seed,
                               trajectory_type=trajectory_type)

    # Default calibrations (well-calibrated sensors)
    accel_cal = SensorCalibration(
        bias=np.zeros(3),
        noise_std=0.05,  # 0.05 m/s² — good IMU
        scale_factor=1.0,
        delay=0.0,
    )
    gyro_cal = SensorCalibration(
        bias=np.zeros(3),
        noise_std=0.01,  # 0.01 rad/s — good IMU
        scale_factor=1.0,
        delay=0.0,
    )
    gps_cal = SensorCalibration(
        bias=np.zeros(3),
        noise_std=1.0,   # 1.0 m — typical GPS
        scale_factor=1.0,
        delay=0.0,
    )

    return SensorFusionProblem(
        trajectory=traj,
        dt=dt,
        accel_cal=accel_cal,
        gyro_cal=gyro_cal,
        gps_cal=gps_cal,
    )
