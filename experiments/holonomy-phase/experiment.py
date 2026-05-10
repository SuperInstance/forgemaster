"""
experiment.py — Holonomy Phase Experiment

Trains a small model on a cyclic curriculum (A→B→C→A) and measures
the geometric phase (holonomy) of representation vectors.

If our theory is right:
1. Holonomy accumulates across cycles (representations drift)
2. The drift is systematic (same direction each cycle)
3. It's invisible to the loss function (loss stays low)
4. It creates systematic bias in the model's predictions

This runs in <10 minutes on CPU.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Tuple, Dict
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from holonomy import (
    compute_holonomy_across_cycles,
    compute_phase_shift,
    representation_trajectory_pca,
    HolonomyResult,
)


# ============================================================
# Model
# ============================================================

class SmallModel(nn.Module):
    """Simple MLP with a representation layer we can track."""
    def __init__(self, input_dim=4, hidden_dim=16, repr_dim=8, output_dim=2):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
        )
        self.repr_layer = nn.Linear(hidden_dim, repr_dim)
        self.decoder = nn.Sequential(
            nn.ReLU(),
            nn.Linear(repr_dim, output_dim),
        )

    def forward(self, x):
        h = self.encoder(x)
        r = self.repr_layer(h)
        return self.decoder(r), r  # return (output, representation)


# ============================================================
# Cyclic Curriculum
# ============================================================

class CyclicCurriculum:
    """
    Generates data for a cyclic curriculum with 3 phases (A, B, C).

    Each phase has a different task:
      A: Classify based on first 2 features (linearly separable)
      B: Classify based on last 2 features (linearly separable)
      C: Classify based on XOR of all features (requires nonlinear repr)

    After A→B→C, we return to A. The question: does the representation
    for the same data points drift across cycles?
    """

    def __init__(self, n_points_per_phase=50, input_dim=4, seed=42):
        self.rng = np.random.RandomState(seed)
        self.n_points = n_points_per_phase
        self.input_dim = input_dim

        # Generate fixed data for each phase
        self.data_a = self.rng.randn(n_points_per_phase, input_dim).astype(np.float32)
        self.labels_a = (self.data_a[:, 0] + self.data_a[:, 1] > 0).astype(np.float32)

        self.data_b = self.rng.randn(n_points_per_phase, input_dim).astype(np.float32)
        self.labels_b = (self.data_b[:, 2] + self.data_b[:, 3] > 0).astype(np.float32)

        self.data_c = self.rng.randn(n_points_per_phase, input_dim).astype(np.float32)
        # XOR-like: class 1 if (x0*x1 > 0) XOR (x2*x3 > 0)
        cond1 = self.data_c[:, 0] * self.data_c[:, 1] > 0
        cond2 = self.data_c[:, 2] * self.data_c[:, 3] > 0
        self.labels_c = (cond1 ^ cond2).astype(np.float32)

        # Shared probe set (same data points used to track representations)
        self.probe_data = torch.tensor(
            self.rng.randn(20, input_dim).astype(np.float32)
        )
        self.probe_labels = torch.tensor(
            (self.probe_data.numpy()[:, 0] + self.probe_data.numpy()[:, 1] > 0).astype(np.int64)
        )

    def get_phase(self, phase_idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """Get (data, labels) for phase 0=A, 1=B, 2=C."""
        phase_idx = phase_idx % 3
        if phase_idx == 0:
            return (torch.tensor(self.data_a), torch.tensor(self.labels_a).long())
        elif phase_idx == 1:
            return (torch.tensor(self.data_b), torch.tensor(self.labels_b).long())
        else:
            return (torch.tensor(self.data_c), torch.tensor(self.labels_c).long())

    @property
    def phase_names(self):
        return ["A", "B", "C"]


# ============================================================
# Experiment Runner
# ============================================================

def run_experiment(
    n_cycles: int = 5,
    steps_per_phase: int = 30,
    lr: float = 0.01,
    seed: int = 42,
) -> Dict:
    """
    Run the holonomy phase experiment.

    For each cycle (A→B→C):
      1. Train on phase A, record representations of probe set
      2. Train on phase B, record representations
      3. Train on phase C, record representations
      4. Compute holonomy: how much did the representation drift?

    Returns results dict with holonomy data.
    """
    print("=" * 70)
    print("HOLONOMY PHASE EXPERIMENT")
    print("=" * 70)
    print(f"  Cycles: {n_cycles}, Steps/phase: {steps_per_phase}")
    print(f"  Total training steps: {n_cycles * 3 * steps_per_phase}")
    print()

    torch.manual_seed(seed)
    np.random.seed(seed)

    curriculum = CyclicCurriculum(n_points_per_phase=50, seed=seed)
    model = SmallModel(input_dim=4, hidden_dim=16, repr_dim=8, output_dim=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # Storage
    probe_representations: List[np.ndarray] = []
    probe_losses: List[float] = []
    phase_labels: List[int] = []
    step_labels: List[str] = []

    cycle_length = 3 * steps_per_phase

    # Record initial probe representation
    model.eval()
    with torch.no_grad():
        _, repr_init = model(curriculum.probe_data)
        probe_representations.append(repr_init.mean(dim=0).numpy())
        probe_losses.append(0.0)
        phase_labels.append(0)
        step_labels.append("init")

    total_steps = 0
    for cycle in range(n_cycles):
        print(f"  Cycle {cycle + 1}/{n_cycles}")

        for phase in range(3):
            data, labels = curriculum.get_phase(phase)
            phase_name = curriculum.phase_names[phase]

            model.train()
            for step in range(steps_per_phase):
                optimizer.zero_grad()
                output, _ = model(data)
                loss = F.cross_entropy(output, labels)
                loss.backward()
                optimizer.step()
                total_steps += 1

            # Record probe representation after this phase
            model.eval()
            with torch.no_grad():
                probe_out, probe_repr = model(curriculum.probe_data)
                probe_loss = F.cross_entropy(probe_out, curriculum.probe_labels)

                probe_representations.append(probe_repr.mean(dim=0).numpy())
                probe_losses.append(probe_loss.item())
                phase_labels.append(phase)
                step_labels.append(f"C{cycle+1}-{phase_name}")

            if phase == 0:  # Print after returning to A
                print(f"    Phase {phase_name}: loss={probe_loss.item():.4f}")

    # Compute holonomy across cycles
    print("\n  Computing holonomy...")
    # Probe is recorded once per phase (3 per cycle), not per training step
    probe_cycle_length = 3  # 3 recordings per cycle (A, B, C)
    holonomy_results = compute_holonomy_across_cycles(
        probe_representations,
        cycle_length=probe_cycle_length,
        n_cycles=n_cycles,
    )

    # Compute phase shifts
    # Each cycle = 3 phase recordings (one per phase A,B,C), recorded AFTER each phase
    # Plus initial recording. So indices: 0=init, 1=C1-A, 2=C1-B, 3=C1-C, 4=C2-A, ...
    # Cycle boundary = start of each cycle = indices 0, 4, 7, 10, ... (= 1 + cycle*3)
    cycle_boundaries = [0] + [1 + cycle * 3 for cycle in range(n_cycles)]
    cycle_boundaries = [b for b in cycle_boundaries if b < len(probe_representations)]
    phase_shifts = compute_phase_shift(probe_representations, cycle_boundaries)

    # PCA for trajectory visualization
    projected, explained_var = representation_trajectory_pca(probe_representations)

    # Print results
    print("\n" + "-" * 50)
    print("HOLONOMY RESULTS:")
    print("-" * 50)

    for h in holonomy_results:
        print(f"  Cycle {h.cycle + 1}: ||holonomy|| = {h.holonomy_norm:.6f}, "
              f"angle = {np.degrees(h.angle):.2f}°")

    if len(holonomy_results) > 1:
        norms = [h.holonomy_norm for h in holonomy_results]
        print(f"\n  Holonomy norms: {[f'{n:.6f}' for n in norms]}")
        print(f"  Is accumulating: {norms[-1] > norms[0]}")

    print(f"\n  Phase shifts per cycle: {[f'{s:.4f}' for s in phase_shifts['per_cycle_shifts']]}")
    print(f"  Total accumulated shift: {phase_shifts['total_shift']:.4f}")
    print(f"  Is accumulating: {phase_shifts['is_accumulating']}")

    # Check if holonomy is invisible to loss
    print(f"\n  Probe losses: {[f'{l:.4f}' for l in probe_losses[-6:]]}")
    loss_variance = np.var(probe_losses[-(n_cycles * 3):])
    holonomy_norms = [h.holonomy_norm for h in holonomy_results]
    print(f"  Loss variance (last cycles): {loss_variance:.6f}")
    print(f"  Mean holonomy norm: {np.mean(holonomy_norms):.6f}")

    # The key test: does holonomy accumulate while loss stays stable?
    if len(holonomy_results) >= 2:
        holonomy_increasing = holonomy_results[-1].holonomy_norm > holonomy_results[0].holonomy_norm
        loss_stable = loss_variance < 0.01

        print(f"\n  Holonomy increases across cycles: {holonomy_increasing}")
        print(f"  Loss stays stable: {loss_stable}")

        if holonomy_increasing and loss_stable:
            print("\n  ★ CONFIRMED: Holonomy accumulates while loss stays stable!")
            print("    This is systematic bias invisible to the loss function.")
        elif holonomy_increasing:
            print("\n  ~ PARTIAL: Holonomy increases but loss also varies.")
        else:
            print("\n  ✗ NOT CONFIRMED: Holonomy doesn't clearly accumulate.")

    return {
        "holonomy_results": holonomy_results,
        "phase_shifts": phase_shifts,
        "probe_representations": probe_representations,
        "probe_losses": probe_losses,
        "projected": projected,
        "explained_var": explained_var,
        "step_labels": step_labels,
    }


def plot_trajectory(results: Dict, save_path: str = None):
    """Plot the representation trajectory (requires matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (matplotlib not available, skipping plot)")
        return

    projected = results["projected"]
    labels = results["step_labels"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Trajectory plot
    ax = axes[0]
    colors = plt.cm.viridis(np.linspace(0, 1, len(projected)))
    ax.scatter(projected[:, 0], projected[:, 1], c=range(len(projected)),
               cmap="viridis", s=40, zorder=5)
    ax.plot(projected[:, 0], projected[:, 1], "k-", alpha=0.3, linewidth=0.5)

    # Mark cycle starts
    for i, label in enumerate(labels):
        if label.startswith("C") and label.endswith("-A"):
            ax.annotate(label, (projected[i, 0], projected[i, 1]),
                        fontsize=7, alpha=0.7)

    ax.set_xlabel(f"PC1 ({results['explained_var'][0]:.1%} var)")
    ax.set_ylabel(f"PC2 ({results['explained_var'][1]:.1%} var)")
    ax.set_title("Representation Trajectory Through Curriculum Cycles")

    # Holonomy accumulation plot
    ax = axes[1]
    holonomy_norms = [h.holonomy_norm for h in results["holonomy_results"]]
    angles = [np.degrees(h.angle) for h in results["holonomy_results"]]

    cycles = range(1, len(holonomy_norms) + 1)
    ax.bar(cycles, holonomy_norms, color="steelblue", alpha=0.7, label="||holonomy||")
    ax2 = ax.twinx()
    ax2.plot(cycles, angles, "ro-", label="angle (°)")
    ax2.set_ylabel("Angle (degrees)", color="red")

    ax.set_xlabel("Cycle")
    ax.set_ylabel("Holonomy norm")
    ax.set_title("Holonomy Accumulation Across Cycles")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"  Plot saved to {save_path}")
    else:
        plt.savefig(os.path.join(os.path.dirname(__file__), "holonomy_plot.png"), dpi=150)
        print(f"  Plot saved to holonomy_plot.png")

    plt.close()


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  HOLONOMY PHASE EXPERIMENT                               ║")
    print("║  Geometric Phase in Neural Training Trajectories         ║")
    print("║  Tests: Does holonomy accumulate across cycles?          ║")
    print("╚══════════════════════════════════════════════════════════╝")

    results = run_experiment(
        n_cycles=5,
        steps_per_phase=30,
        lr=0.01,
    )

    # Try to generate plot
    plot_trajectory(results)

    print("\nDone. Run time: ~30 seconds on CPU.")
