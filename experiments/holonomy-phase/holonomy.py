"""
holonomy.py — Holonomy computation for representation vectors

Holonomy measures how much a vector changes when parallel-transported
around a closed loop. In the training context:

- Representation vectors for the same data point change as the model
  trains on different tasks
- After a cycle of tasks (A→B→C→A), if the representation doesn't return
  to its starting point, the deficit is holonomy
- Holonomy measures systematic bias that's invisible to loss functions

This is classical geometric phase (Hannay angle), not quantum Berry phase.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class TransportStep:
    """Result of transporting a representation through one training step."""
    step: int
    phase: int               # Which phase of the curriculum (A=0, B=1, C=2)
    representation: np.ndarray  # Representation after this step
    displacement: np.ndarray    # Change from previous step


@dataclass
class HolonomyResult:
    """Result of holonomy computation for one cycle."""
    cycle: int
    start_repr: np.ndarray      # Representation at cycle start
    end_repr: np.ndarray        # Representation at cycle end
    holonomy_vector: np.ndarray # end - start (the deficit)
    holonomy_norm: float        # ||end - start||
    angle: float                # Angle between start and end (radians)
    accumulated_per_step: List[float]  # Displacement magnitude at each step


def compute_transport(
    representations: List[np.ndarray],
    labels: List[int],
    n_phases: int = 3,
) -> Dict[int, List[TransportStep]]:
    """
    Organize representation history by curriculum phase.

    Args:
        representations: List of representations at each training step
        labels: Which curriculum phase each step belongs to
        n_phases: Number of phases in the curriculum cycle

    Returns:
        Dict mapping phase index to list of TransportSteps
    """
    phases = {i: [] for i in range(n_phases)}
    prev_repr = representations[0]

    for step, (repr_vec, phase) in enumerate(zip(representations, labels)):
        displacement = repr_vec - prev_repr
        phases[phase].append(TransportStep(
            step=step,
            phase=phase,
            representation=repr_vec.copy(),
            displacement=displacement.copy(),
        ))
        prev_repr = repr_vec

    return phases


def compute_holonomy_single_cycle(
    representations: List[np.ndarray],
    cycle_start: int,
    cycle_end: int,
) -> HolonomyResult:
    """
    Compute holonomy for a single curriculum cycle.

    The holonomy is the difference between the representation at the
    start and end of a complete cycle. If the curriculum is A→B→C→A,
    the holonomy measures how much the "A" representation drifts.
    """
    start_repr = representations[cycle_start]
    end_repr = representations[cycle_end]

    holonomy_vector = end_repr - start_repr
    holonomy_norm = np.linalg.norm(holonomy_vector)

    # Angle between start and end representations
    norm_start = np.linalg.norm(start_repr)
    norm_end = np.linalg.norm(end_repr)

    if norm_start > 1e-10 and norm_end > 1e-10:
        cos_angle = np.clip(
            np.dot(start_repr, end_repr) / (norm_start * norm_end),
            -1.0, 1.0
        )
        angle = np.arccos(cos_angle)
    else:
        angle = 0.0

    # Accumulated displacement at each step
    accumulated = []
    running = np.zeros_like(start_repr)
    for i in range(cycle_start, cycle_end):
        running += representations[min(i + 1, len(representations) - 1)] - representations[i]
        accumulated.append(np.linalg.norm(running))

    return HolonomyResult(
        cycle=0,  # caller sets this
        start_repr=start_repr,
        end_repr=end_repr,
        holonomy_vector=holonomy_vector,
        holonomy_norm=holonomy_norm,
        angle=angle,
        accumulated_per_step=accumulated,
    )


def compute_holonomy_across_cycles(
    representations: List[np.ndarray],
    cycle_length: int,
    n_cycles: int,
) -> List[HolonomyResult]:
    """
    Compute holonomy for each cycle in a multi-cycle curriculum.

    If the theory is right, holonomy should:
    1. Be nonzero (representation doesn't return to start)
    2. Accumulate across cycles (drift increases)
    3. Not be detected by loss function (loss stays low)
    """
    results = []

    for cycle in range(n_cycles):
        start_idx = cycle * cycle_length
        end_idx = min((cycle + 1) * cycle_length, len(representations) - 1)

        if start_idx >= len(representations) or end_idx >= len(representations):
            break

        result = compute_holonomy_single_cycle(representations, start_idx, end_idx)
        result.cycle = cycle
        results.append(result)

    return results


def compute_phase_shift(
    representations: List[np.ndarray],
    cycle_boundaries: List[int],
) -> Dict[str, float]:
    """
    Compute the phase shift accumulated across cycles.

    The phase shift is the angular drift of representations over cycles.
    If it grows linearly, it's a systematic bias. If it grows faster,
    there's a compounding effect.
    """
    shifts = []

    for i in range(1, len(cycle_boundaries)):
        start_idx = cycle_boundaries[i - 1]
        end_idx = cycle_boundaries[i]

        if end_idx >= len(representations):
            break

        start = representations[start_idx]
        end = representations[end_idx]

        # Phase shift = angle between representations
        n_s = np.linalg.norm(start)
        n_e = np.linalg.norm(end)

        if n_s > 1e-10 and n_e > 1e-10:
            cos_a = np.clip(np.dot(start, end) / (n_s * n_e), -1.0, 1.0)
            shifts.append(np.arccos(cos_a))
        else:
            shifts.append(0.0)

    # Compute shift accumulation rate
    if len(shifts) > 1:
        total_shift = sum(shifts)
        shift_rate = shifts[-1] - shifts[0] if len(shifts) > 1 else 0
    else:
        total_shift = shifts[0] if shifts else 0.0
        shift_rate = 0.0

    return {
        "per_cycle_shifts": shifts,
        "total_shift": total_shift,
        "shift_rate": shift_rate,
        "is_accumulating": total_shift > 0.1 and shifts[-1] > shifts[0] if len(shifts) > 1 else False,
    }


def representation_trajectory_pca(
    representations: List[np.ndarray],
    n_components: int = 2,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Project representation trajectory to 2D via PCA for visualization.

    Returns:
        projected: (n_steps, n_components) array
        explained_variance: variance explained by each component
    """
    X = np.array(representations)
    # Center
    X_centered = X - X.mean(axis=0)

    # PCA via SVD
    U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)

    projected = X_centered @ Vt[:n_components].T
    total_var = (S ** 2).sum()
    explained_variance = (S[:n_components] ** 2) / total_var if total_var > 0 else np.zeros(n_components)

    return projected, explained_variance
