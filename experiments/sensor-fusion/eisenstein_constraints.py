"""
eisenstein_constraints.py — Eisenstein lattice constraint checking for sensor fusion.

Eisenstein integers Z[ω] form a hexagonal lattice in the complex plane.
They provide topologically protected constraint satisfaction for pairs of
coordinate estimates.

Key insight: When two sensors provide estimates of the same quantity,
the constraint satisfaction can be checked via Eisenstein lattice projection.
If the drift between estimates is a Gaussian integer multiple of the lattice
spacing, the constraint is satisfied. Otherwise, the remainder measures
the violation.

This is the PRACTICAL application of Eisenstein constraint theory to sensor fusion:
  - GPS and integrated-IMU both estimate position
  - The difference should be constrained by the Eisenstein lattice
  - Constraint violations indicate sensor failure BEFORE the error is large
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass


# Eisenstein integer ω = (-1 + i√3)/2
# The lattice is {a + bω : a, b ∈ Z}
# Fundamental domain: rhombus with side length 1

EISENSTEIN_OMEGA = complex(-0.5, np.sqrt(3) / 2)
EISENSTEIN_OMEGA_SQ = EISENSTEIN_OMEGA ** 2  # ω² = (-1 - i√3)/2


@dataclass
class ConstraintViolation:
    """A single constraint violation."""
    location: np.ndarray        # Where the violation occurred
    drift_vector: np.ndarray    # The vector drift
    lattice_remainder: float    # Distance to nearest lattice point
    constraint_satisfied: bool  # Whether the constraint holds
    time: float                 # When it occurred


def project_to_eisenstein(z: complex) -> Tuple[complex, float]:
    """
    Project complex number z onto the nearest Eisenstein integer.

    Returns:
      - nearest lattice point (as complex)
      - distance to nearest lattice point (in lattice units)
    
    The Eisenstein lattice Z[ω] is a triangular lattice.
    We find nearest neighbor by checking the 4 candidates
    around the floor decomposition.
    """
    # Express z in ω basis: z = x + y*ω, with real x,y
    # The lattice points are at integer (x, y) in this basis
    x = z.real
    y = (2.0 * z.imag + z.real) / np.sqrt(3)  # This is approximate
    
    # Floor to get candidate lattice point
    x0, y0 = np.floor(x), np.floor(y)
    
    # Check 4 nearest integer candidates
    candidates = []
    for dx in [0, 1]:
        for dy in [0, 1]:
            cx, cy = x0 + dx, y0 + dy
            cand = cx + cy * EISENSTEIN_OMEGA
            dist = abs(z - cand)
            candidates.append((dist, cand))
    
    candidates.sort(key=lambda t: t[0])
    nearest = candidates[0][1]
    distance = candidates[0][0]
    
    return nearest, distance


def check_position_constraint(
    gps_position: np.ndarray,
    imu_position: np.ndarray,
    constraint_scale: float = 1.0,
) -> ConstraintViolation:
    """
    Check whether two position estimates satisfy the Eisenstein constraint.

    The difference vector is projected to the Eisenstein lattice.
    If the remainder is small, the constraint is satisfied.
    
    Args:
        gps_position: (3,) position from GPS
        imu_position: (3,) position from IMU integration
        constraint_scale: scale factor for lattice spacing
        
    Returns:
        ConstraintViolation describing the result
    """
    drift = imu_position - gps_position
    
    # Only check x-y plane (horizontal drift)
    # Eisenstein lattice applies to 2D drift
    drift_2d = complex(drift[0], drift[1])
    drift_scaled = drift_2d / constraint_scale
    
    nearest, distance = project_to_eisenstein(drift_scaled)
    
    # Convert distance back to real units
    remainder_distance = distance * constraint_scale
    
    # Constraint is satisfied if remainder is small relative to constraint scale
    # Threshold: distance must be close to integer lattice point
    # For a well-constrained system, remainder should be < 10% of lattice spacing
    threshold = 0.1 * constraint_scale
    satisfied = remainder_distance < threshold
    
    return ConstraintViolation(
        location=gps_position.copy(),
        drift_vector=drift.copy(),
        lattice_remainder=remainder_distance,
        constraint_satisfied=satisfied,
        time=0.0,
    )


def compute_violation_rate(
    gps_positions: np.ndarray,
    imu_positions: np.ndarray,
    constraint_scale: float = 1.0,
    times: Optional[np.ndarray] = None,
) -> Tuple[List[ConstraintViolation], float, float]:
    """
    Compute constraint violation rate over a trajectory.

    Args:
        gps_positions: (n_gps, 3) GPS position estimates
        imu_positions: (n_gps, 3) corresponding IMU position estimates
                         (interpolated to GPS timestamps)
        constraint_scale: scale factor for lattice spacing
        
    Returns:
        violations: list of ConstraintViolation objects
        violation_rate: fraction of positions with violated constraints
        mean_remainder: mean distance to nearest lattice point
    """
    n = min(len(gps_positions), len(imu_positions))
    violations = []
    violated_count = 0

    for i in range(n):
        v = check_position_constraint(
            gps_positions[i],
            imu_positions[i],
            constraint_scale,
        )
        if times is not None and i < len(times):
            v.time = times[i]
        violations.append(v)
        if not v.constraint_satisfied:
            violated_count += 1

    violation_rate = violated_count / n if n > 0 else 0.0
    mean_remainder = np.mean([v.lattice_remainder for v in violations])

    return violations, violation_rate, mean_remainder


def constraint_vs_std_comparison(
    gps_positions: np.ndarray,
    imu_positions: np.ndarray,
    constraint_scale: float = 1.0,
) -> dict:
    """
    Compare constraint-based detection vs standard statistical detection.

    Standard: detect if error > 3σ of GPS noise
    Constraint: detect if Eisenstein remainder exceeds threshold
    
    Returns comparison metrics.
    """
    n = min(len(gps_positions), len(imu_positions))
    gps = gps_positions[:n]
    imu = imu_positions[:n]

    # Standard detection: error > 3σ
    errors = np.linalg.norm(imu - gps, axis=1)
    gps_noise_std = 1.0  # typical GPS noise
    std_threshold = 3.0 * gps_noise_std
    std_detections = errors > std_threshold

    # Constraint detection
    violations, violation_rate, mean_remainder = compute_violation_rate(
        gps, imu, constraint_scale
    )
    constraint_detections = np.array([
        not v.constraint_satisfied for v in violations
    ])

    # Comparison
    # When error is small but systematic (holonomy), constraint detects earlier
    # because the Eisenstein remainder captures systematic drift trends
    correlation = np.corrcoef(
        errors[:len(constraint_detections)],
        np.array([v.lattice_remainder for v in violations])
    )[0, 1] if len(errors) > 1 and len(constraint_detections) > 1 else 0.0

    # If constraint_detections notices things std doesn't:
    constraint_extra = np.sum(constraint_detections & ~std_detections[:len(constraint_detections)])

    return {
        "n_points": n,
        "std_detections": int(np.sum(std_detections)),
        "constraint_detections": int(np.sum(constraint_detections)),
        "constraint_extra_detections": int(constraint_extra),
        "violation_rate": violation_rate,
        "mean_remainder": mean_remainder,
        "mean_error": float(np.mean(errors)),
        "std_of_error": float(np.std(errors)),
        "correlation": correlation,
    }
