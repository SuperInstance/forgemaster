"""
delta_detect.py — Saturation Detector for Neural Networks

Measures when a model has exhausted its current operational level by tracking:
  1. Attention entropy (information distribution across positions)
  2. Gradient magnitude (learning signal strength)
  3. Representation variance (spread of activations in latent space)

Produces a saturation signal and classifies exhaustion as:
  - QUANTITATIVE: needs more training (same level, more data/epochs)
  - QUALITATIVE: needs architecture change (level elevation required)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class ExhaustionType(Enum):
    NONE = "none"
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"


@dataclass
class SaturationReport:
    """Full saturation analysis for a model at a given moment."""
    attention_entropy: float          # 0 (collapsed) to 1 (uniform)
    gradient_magnitude: float         # L2 norm of gradients
    repr_variance: float              # variance of last-layer representations
    saturation_score: float           # composite 0-1 (1 = fully saturated)
    exhaustion_type: ExhaustionType
    recommendation: str
    level_elevation: bool             # True = needs qualitative change


@dataclass
class SaturationHistory:
    """Tracks saturation metrics over training steps."""
    attention_entropies: List[float] = field(default_factory=list)
    gradient_magnitudes: List[float] = field(default_factory=list)
    repr_variances: List[float] = field(default_factory=list)
    saturation_scores: List[float] = field(default_factory=list)

    def record(self, report: SaturationReport):
        self.attention_entropies.append(report.attention_entropy)
        self.gradient_magnitudes.append(report.gradient_magnitude)
        self.repr_variances.append(report.repr_variance)
        self.saturation_scores.append(report.saturation_score)


class SaturationDetector:
    """
    Detects when a model's current operational level is saturated.

    Saturation is indicated by:
    - Attention entropy approaching 0 (collapsed) or 1 (uniform/flat)
    - Gradient magnitude declining toward zero
    - Representation variance collapsing (all inputs map to similar outputs)

    The composite saturation score combines these signals.
    Exhaustion type is classified by the PATTERN of saturation:
    - Quantitative: gradients declining but entropy/variance still reasonable
      → model is converging, just needs more data/time
    - Qualitative: entropy collapsing AND variance collapsing despite gradient signal
      → model architecture can't represent the needed structure
    """

    def __init__(
        self,
        entropy_collapse_threshold: float = 0.05,
        entropy_flat_threshold: float = 0.95,
        gradient_dead_threshold: float = 1e-5,
        variance_collapse_threshold: float = 0.01,
        saturation_threshold: float = 0.7,
        window_size: int = 5,
    ):
        self.entropy_collapse_threshold = entropy_collapse_threshold
        self.entropy_flat_threshold = entropy_flat_threshold
        self.gradient_dead_threshold = gradient_dead_threshold
        self.variance_collapse_threshold = variance_collapse_threshold
        self.saturation_threshold = saturation_threshold
        self.window_size = window_size
        self.history = SaturationHistory()

    def compute_attention_entropy(self, model: nn.Module, x: torch.Tensor) -> float:
        """
        Compute average normalized entropy of attention weights across all
        MultiheadAttention layers in the model.

        Returns value in [0, 1] where:
          0 = fully collapsed (one position dominates)
          1 = fully uniform (all positions equal)
        """
        entropies = []
        hooks = []

        def hook_fn(module, input, output):
            # For MultiheadAttention, output is (attn_output, attn_weights) if need_weights=True
            if isinstance(output, tuple) and len(output) >= 2:
                attn_weights = output[1]
                if attn_weights is not None and attn_weights.numel() > 0:
                    entropies.append(attn_weights.detach())

        # Register hooks on all attention modules
        for name, module in model.named_modules():
            if isinstance(module, nn.MultiheadAttention):
                hooks.append(module.register_forward_hook(hook_fn))

        # Forward pass to collect attention weights
        model.eval()
        with torch.no_grad():
            try:
                # Try with need_weights=True
                _ = model(x)
            except Exception:
                # If the model doesn't support need_weights directly,
                # we'll compute entropy from the representation layer instead
                pass

        # Remove hooks
        for h in hooks:
            h.remove()

        if not entropies:
            # No attention layers found — compute proxy from representation variance
            # This is a fallback: use the penultimate layer's activation distribution
            return self._compute_representation_entropy(model, x)

        # Compute normalized entropy for each attention weight matrix
        normalized_entropies = []
        for attn in entropies:
            # attn shape: (batch, heads, seq_len, seq_len) or similar
            attn = attn.flatten(0, 1)  # merge batch and heads
            for a in attn:
                # Normalize to probability distribution
                probs = F.softmax(a.flatten(), dim=0)
                # Compute entropy
                entropy = -(probs * (probs + 1e-10).log()).sum()
                # Normalize by max entropy (uniform distribution)
                max_entropy = np.log(probs.numel())
                if max_entropy > 0:
                    normalized_entropies.append((entropy / max_entropy).item())
                else:
                    normalized_entropies.append(0.0)

        return float(np.mean(normalized_entropies)) if normalized_entropies else 0.5

    def _compute_representation_entropy(self, model: nn.Module, x: torch.Tensor) -> float:
        """Fallback: compute entropy-like measure from representation distribution."""
        activations = self._get_representations(model, x)
        if activations is None:
            return 0.5

        # Use variance as proxy: high variance = diverse representations = high entropy
        var = activations.var().item()
        # Normalize: variance of standard normal is 1.0
        return min(var / 2.0, 1.0)  # cap at 1.0

    def _get_representations(self, model: nn.Module, x: torch.Tensor) -> Optional[torch.Tensor]:
        """Get representations from the last linear layer."""
        representation = [None]

        def hook_fn(module, input, output):
            representation[0] = output.detach()

        # Find the last Linear layer
        last_linear = None
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                last_linear = module

        if last_linear is None:
            return None

        hook = last_linear.register_forward_hook(hook_fn)
        with torch.no_grad():
            model.eval()
            _ = model(x)
        hook.remove()

        return representation[0]

    def compute_gradient_magnitude(self, model: nn.Module, x: torch.Tensor, y: torch.Tensor) -> float:
        """Compute L2 norm of gradients with respect to loss."""
        model.train()
        model.zero_grad()

        output = model(x)
        loss = F.mse_loss(output, y)
        loss.backward()

        total_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                total_norm += p.grad.data.norm(2).item() ** 2

        return float(np.sqrt(total_norm))

    def compute_representation_variance(self, model: nn.Module, x: torch.Tensor) -> float:
        """
        Compute variance of representations across different inputs.
        Low variance = all inputs map to similar outputs = representation collapse.
        """
        representations = self._get_representations(model, x)
        if representations is None:
            return 0.5

        # Compute per-feature variance across the batch
        # representations shape: (batch, features)
        per_feature_var = representations.var(dim=0)
        # Average across features
        avg_var = per_feature_var.mean().item()

        return avg_var

    def compute_saturation_score(
        self,
        attention_entropy: float,
        gradient_magnitude: float,
        repr_variance: float,
        grad_history: List[float] = None,
    ) -> float:
        """
        Compute composite saturation score in [0, 1].

        High saturation = model is stuck at current level.
        """
        # Entropy saturation: penalize both collapse and flatness
        # Optimal entropy is around 0.5-0.7 (structured but not uniform)
        entropy_score = 1.0 - 2.0 * abs(attention_entropy - 0.6)
        entropy_score = max(0.0, entropy_score)

        # Gradient saturation: how close to zero
        # Use log scale for gradient
        if gradient_magnitude > 0:
            grad_score = max(0.0, 1.0 - np.log10(gradient_magnitude + 1e-10) / 10.0)
        else:
            grad_score = 1.0

        # Trend-based gradient saturation
        if grad_history and len(grad_history) >= self.window_size:
            recent = grad_history[-self.window_size:]
            trend = np.polyfit(range(len(recent)), recent, 1)[0]
            # Negative trend = gradients declining = increasing saturation
            trend_score = max(0.0, min(1.0, -trend * 100 + 0.5))
        else:
            trend_score = 0.0

        # Variance saturation: how collapsed
        var_score = max(0.0, 1.0 - repr_variance * 10.0)  # scale up small variances

        # Composite: weighted combination
        composite = (
            0.3 * entropy_score +
            0.2 * grad_score +
            0.2 * trend_score +
            0.3 * var_score
        )

        return float(np.clip(composite, 0.0, 1.0))

    def classify_exhaustion(
        self,
        attention_entropy: float,
        gradient_magnitude: float,
        repr_variance: float,
        saturation_score: float,
    ) -> Tuple[ExhaustionType, str, bool]:
        """
        Classify the type of exhaustion based on the pattern of saturation.

        Quantitative: gradients are declining but representations are still diverse.
          → Model is learning but running out of easy gains.
          → Needs: more data, more epochs, learning rate adjustment.

        Qualitative: representations are collapsing AND attention is flat/collapsed,
          even though gradients may still be nonzero.
          → Model architecture cannot capture the needed structure.
          → Needs: architectural change, level elevation.
        """
        if saturation_score < self.saturation_threshold:
            return ExhaustionType.NONE, "Model not saturated. Keep training.", False

        # Check for qualitative exhaustion
        entropy_collapsed = attention_entropy < self.entropy_collapse_threshold
        entropy_flat = attention_entropy > self.entropy_flat_threshold
        variance_collapsed = repr_variance < self.variance_collapse_threshold
        gradient_alive = gradient_magnitude > self.gradient_dead_threshold

        # Qualitative: structure can't represent the problem
        # Signatures: attention collapsed/flat AND variance collapsed, even with gradient signal
        if (entropy_collapsed or entropy_flat) and variance_collapsed:
            if gradient_alive:
                return (
                    ExhaustionType.QUALITATIVE,
                    "QUALITATIVE SATURATION: Model has gradient signal but representations "
                    "are collapsing. Architecture cannot capture needed structure. "
                    "Recommend: level elevation (add structural/topological layer).",
                    True
                )
            else:
                return (
                    ExhaustionType.QUALITATIVE,
                    "QUALITATIVE SATURATION: Both gradients and representations collapsed. "
                    "Model is fully stuck. Recommend: architectural overhaul.",
                    True
                )

        # Quantitative: still has structure but running out of gradient
        if gradient_alive and not variance_collapsed:
            return (
                ExhaustionType.QUANTITATIVE,
                "QUANTITATIVE SATURATION: Gradients declining but representations still "
                "diverse. Model needs more training data or epochs, not architecture change.",
                False
            )

        # Edge case: gradient dead but variance ok (rare)
        if not gradient_alive and not variance_collapsed:
            return (
                ExhaustionType.QUANTITATIVE,
                "QUANTITATIVE SATURATION: Gradients vanished but representations still "
                "diverse. Try: learning rate adjustment, gradient clipping.",
                False
            )

        # Default to quantitative
        return (
            ExhaustionType.QUANTITATIVE,
            "QUANTITATIVE SATURATION: Model converging but not yet at capacity.",
            False
        )

    def analyze(
        self,
        model: nn.Module,
        x: torch.Tensor,
        y: Optional[torch.Tensor] = None,
    ) -> SaturationReport:
        """
        Run full saturation analysis on a model.

        Args:
            model: The neural network to analyze
            x: Input tensor (batch of samples)
            y: Target tensor (needed for gradient computation; if None, skip gradients)
        """
        # Compute metrics
        attention_entropy = self.compute_attention_entropy(model, x)
        repr_variance = self.compute_representation_variance(model, x)

        if y is not None:
            gradient_magnitude = self.compute_gradient_magnitude(model, x, y)
        else:
            gradient_magnitude = self.history.gradient_magnitudes[-1] if self.history.gradient_magnitudes else 0.0

        # Compute saturation
        saturation_score = self.compute_saturation_score(
            attention_entropy, gradient_magnitude, repr_variance,
            grad_history=self.history.gradient_magnitudes
        )

        # Classify
        exhaustion_type, recommendation, level_elevation = self.classify_exhaustion(
            attention_entropy, gradient_magnitude, repr_variance, saturation_score
        )

        report = SaturationReport(
            attention_entropy=attention_entropy,
            gradient_magnitude=gradient_magnitude,
            repr_variance=repr_variance,
            saturation_score=saturation_score,
            exhaustion_type=exhaustion_type,
            recommendation=recommendation,
            level_elevation=level_elevation,
        )

        self.history.record(report)
        return report


def format_report(report: SaturationReport, step: int = 0) -> str:
    """Pretty-print a saturation report."""
    lines = [
        f"{'='*60}",
        f"SATURATION REPORT — Step {step}",
        f"{'='*60}",
        f"  Attention Entropy:    {report.attention_entropy:.4f}",
        f"  Gradient Magnitude:   {report.gradient_magnitude:.6f}",
        f"  Repr Variance:        {report.repr_variance:.6f}",
        f"  Saturation Score:     {report.saturation_score:.4f}",
        f"  Exhaustion Type:      {report.exhaustion_type.value}",
        f"  Level Elevation:      {report.level_elevation}",
        f"  Recommendation:       {report.recommendation}",
        f"{'='*60}",
    ]
    return "\n".join(lines)
