"""
level_classifier.py — Classifies exhaustion as quantitative vs qualitative

A quantitative exhaustion means the model needs more of the same:
  - More training data
  - More epochs
  - Learning rate tuning
  - Regularization adjustment

A qualitative exhaustion means the model has hit an architectural ceiling:
  - Needs a different representation type
  - Needs structural/topological processing
  - Needs level elevation (hyperoperational jump)

The classifier uses the joint distribution of saturation signals to distinguish.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class LevelProfile:
    """Profile of a model at a given operational level."""
    mean_entropy: float       # Average attention entropy
    mean_gradient: float      # Average gradient magnitude
    mean_variance: float      # Average representation variance
    entropy_trend: float      # Slope of entropy over time
    gradient_trend: float     # Slope of gradients over time
    variance_trend: float     # Slope of variance over time


class LevelClassifier:
    """
    Classifies whether a model's saturation is quantitative or qualitative.

    Uses the following heuristics derived from the theory:

    QUANTITATIVE EXHAUSTION:
      - Entropy is still structured (0.1 < entropy < 0.9)
      - Gradient trend is declining but not collapsed
      - Variance is still meaningful (> threshold)
      - The model has "learned what it can" at the current rate
      → Fix: more training, data augmentation, hyperparameter tuning

    QUALITATIVE EXHAUSTION:
      - Entropy has collapsed (< 0.1) OR gone flat (> 0.95)
      - Variance has collapsed (< threshold) despite gradient signal
      - The model's architecture fundamentally cannot capture the structure
      → Fix: add structural layers, graph processing, topological awareness

    AMBIGUOUS:
      - Signals are mixed
      → Recommend conservative approach (more training first, then elevation)
    """

    def __init__(
        self,
        entropy_structured_low: float = 0.1,
        entropy_structured_high: float = 0.9,
        variance_healthy: float = 0.01,
        gradient_minimal: float = 1e-4,
        trend_window: int = 10,
    ):
        self.entropy_structured_low = entropy_structured_low
        self.entropy_structured_high = entropy_structured_high
        self.variance_healthy = variance_healthy
        self.gradient_minimal = gradient_minimal
        self.trend_window = trend_window

    def compute_trend(self, values: List[float]) -> float:
        """Compute linear trend of a time series. Returns slope."""
        if len(values) < 2:
            return 0.0
        recent = values[-self.trend_window:] if len(values) >= self.trend_window else values
        x = np.arange(len(recent), dtype=float)
        y = np.array(recent, dtype=float)
        if np.std(y) < 1e-10:
            return 0.0
        slope = np.polyfit(x, y, 1)[0]
        return float(slope)

    def classify_from_history(
        self,
        entropy_history: List[float],
        gradient_history: List[float],
        variance_history: List[float],
    ) -> Tuple[str, LevelProfile, str]:
        """
        Classify exhaustion type from metric history.

        Returns: (classification, profile, recommendation)
          classification: "quantitative", "qualitative", or "ambiguous"
        """
        if not entropy_history:
            return "ambiguous", LevelProfile(0.5, 0.0, 0.5, 0.0, 0.0, 0.0), "No data yet."

        profile = LevelProfile(
            mean_entropy=np.mean(entropy_history[-self.trend_window:]),
            mean_gradient=np.mean(gradient_history[-self.trend_window:]) if gradient_history else 0.0,
            mean_variance=np.mean(variance_history[-self.trend_window:]) if variance_history else 0.5,
            entropy_trend=self.compute_trend(entropy_history),
            gradient_trend=self.compute_trend(gradient_history),
            variance_trend=self.compute_trend(variance_history),
        )

        # Decision logic
        entropy_structured = (
            self.entropy_structured_low <= profile.mean_entropy <= self.entropy_structured_high
        )
        variance_healthy = profile.mean_variance >= self.variance_healthy
        gradient_alive = profile.mean_gradient >= self.gradient_minimal

        # Qualitative signatures
        entropy_collapsed = profile.mean_entropy < self.entropy_structured_low
        entropy_flat = profile.mean_entropy > self.entropy_structured_high
        variance_collapsed = profile.mean_variance < self.variance_healthy

        # Score-based classification
        qualitative_score = 0.0
        quantitative_score = 0.0

        # Entropy collapse → qualitative
        if entropy_collapsed:
            qualitative_score += 0.4
        elif entropy_flat:
            qualitative_score += 0.3  # flat attention is also bad
        elif entropy_structured:
            quantitative_score += 0.3

        # Variance collapse → qualitative
        if variance_collapsed:
            qualitative_score += 0.4
        else:
            quantitative_score += 0.3

        # Gradient alive but stuck → qualitative (has signal but can't use it)
        if gradient_alive and (entropy_collapsed or variance_collapsed):
            qualitative_score += 0.2
        elif not gradient_alive and not variance_collapsed:
            quantitative_score += 0.2
        elif gradient_alive and variance_healthy:
            quantitative_score += 0.2

        # Trend analysis
        if profile.variance_trend < -0.001:
            qualitative_score += 0.1  # variance declining = heading toward collapse
        if profile.gradient_trend < -0.0001:
            quantitative_score += 0.05  # gradient declining = converging (could be either)
        if profile.entropy_trend < -0.001:
            qualitative_score += 0.1

        # Final classification
        if qualitative_score > quantitative_score + 0.15:
            classification = "qualitative"
            recommendation = (
                "QUALITATIVE EXHAUSTION DETECTED.\n"
                "  → Model architecture has hit a ceiling.\n"
                "  → Recommend: add structural/topological processing layer.\n"
                "  → This is a hyperoperational level transition (Δₙ).\n"
                "  → More training at the current level will NOT help."
            )
        elif quantitative_score > qualitative_score + 0.15:
            classification = "quantitative"
            recommendation = (
                "QUANTITATIVE EXHAUSTION DETECTED.\n"
                "  → Model is converging but hasn't exhausted its architecture.\n"
                "  → Recommend: more training data, more epochs, LR scheduling.\n"
                "  → The current level can still learn more."
            )
        else:
            classification = "ambiguous"
            recommendation = (
                "AMBIGUOUS SIGNAL.\n"
                "  → Metrics are mixed — can't clearly classify.\n"
                "  → Recommend: continue training and re-measure.\n"
                "  → If saturation persists after 2x more training, reclassify as qualitative."
            )

        return classification, profile, recommendation

    def recommend_level_elevation(self, profile: LevelProfile) -> dict:
        """
        Given a qualitative exhaustion, recommend what kind of level elevation to perform.

        Returns a dict with elevation details.
        """
        elevation = {
            "current_level": "unknown",
            "target_level": "unknown",
            "transform": "unknown",
            "rationale": "",
        }

        # Heuristic mapping based on what saturated
        if profile.mean_entropy < self.entropy_structured_low:
            # Attention collapsed → model can't distinguish positions
            # → needs to go from token-level to sequence-level processing
            elevation.update({
                "current_level": "H₀ (token processing)",
                "target_level": "H₁ (sequence processing)",
                "transform": "Add attention mechanism or recurrent layer",
                "rationale": "Attention collapsed — model treats all positions the same. "
                             "Needs mechanism to accumulate information across sequences.",
            })
        elif profile.mean_entropy > self.entropy_structured_high:
            # Attention flat → model attends to everything equally
            # → needs structural processing (graph/tree)
            elevation.update({
                "current_level": "H₁ (sequence processing)",
                "target_level": "H₂ (structure processing)",
                "transform": "Add graph constructor or structural attention",
                "rationale": "Attention is flat — model can't find structure in sequences. "
                             "Needs explicit structure extraction.",
            })
        elif profile.mean_variance < self.variance_healthy:
            # Representation collapse → can't represent diversity
            # → needs topological processing
            elevation.update({
                "current_level": "H₂ (structure processing)",
                "target_level": "H₃ (topology processing)",
                "transform": "Add topological features or higher-order interactions",
                "rationale": "Representations collapsed — model can't maintain diverse "
                             "internal states. Needs topological awareness.",
            })

        return elevation
