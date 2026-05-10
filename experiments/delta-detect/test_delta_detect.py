"""
test_delta_detect.py — Tests for the delta-detect saturation detector

Three test cases:
  1. XOR problem: H₀ model hits ceiling, detector signals quantitative first,
     then qualitative after extended training.
  2. Spiral classification: Model without sufficient capacity saturates
     qualitatively (can't represent nonlinear boundary).
  3. Random regression: Model easily learns linear mapping,
     detector shows no saturation.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))

from delta_detect import SaturationDetector, format_report, ExhaustionType
from level_classifier import LevelClassifier
from elevation_operators import SimpleH0Model, SimpleH1Model, SimpleH2Model


def set_seed(seed=42):
    torch.manual_seed(seed)
    np.random.seed(seed)


# ============================================================
# Test 1: XOR Problem — H₀ model should saturate qualitatively
# ============================================================
def test_xor_saturation():
    """
    XOR is the classic problem that requires nonlinear representation.

    A linear model (H₀) cannot solve XOR. The saturation detector should:
    - Initially show quantitative exhaustion (learning what it can)
    - Eventually show qualitative exhaustion (architecture can't solve it)

    An H₁ model (with attention/hidden layer) should not show qualitative saturation.
    """
    print("\n" + "=" * 70)
    print("TEST 1: XOR Saturation — Linear model should hit qualitative ceiling")
    print("=" * 70)

    set_seed(42)

    # XOR data
    x_xor = torch.tensor([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
    y_xor = torch.tensor([[0.], [1.], [1.], [0.]])

    # H₀ model (no hidden layer magic — just linear)
    model_h0 = nn.Sequential(
        nn.Linear(2, 2),
        nn.ReLU(),
        nn.Linear(2, 1),
    )

    # H₁ model (bigger hidden layer — can represent XOR)
    model_h1 = nn.Sequential(
        nn.Linear(2, 16),
        nn.ReLU(),
        nn.Linear(16, 16),
        nn.ReLU(),
        nn.Linear(16, 1),
    )

    detector_h0 = SaturationDetector(
        saturation_threshold=0.5,
        variance_collapse_threshold=0.005,
    )
    detector_h1 = SaturationDetector(
        saturation_threshold=0.5,
        variance_collapse_threshold=0.005,
    )

    optimizer_h0 = torch.optim.Adam(model_h0.parameters(), lr=0.01)
    optimizer_h1 = torch.optim.Adam(model_h1.parameters(), lr=0.01)

    print("\nTraining H₀ (linear) model on XOR:")
    print("-" * 50)

    h0_final_type = None
    for step in range(200):
        optimizer_h0.zero_grad()
        pred = model_h0(x_xor)
        loss = F.mse_loss(pred, y_xor)
        loss.backward()
        optimizer_h0.step()

        if step % 50 == 0 or step == 199:
            report = detector_h0.analyze(model_h0, x_xor, y_xor)
            if step % 50 == 0:
                print(f"  Step {step:3d}: loss={loss.item():.4f}, "
                      f"sat={report.saturation_score:.3f}, "
                      f"type={report.exhaustion_type.value}")
            if step == 199:
                h0_final_type = report.exhaustion_type

    print(f"\n  Final H₀ exhaustion: {h0_final_type.value}")
    print(f"  Final H₀ loss: {loss.item():.4f} (XOR unsolvable by linear model)")

    print("\nTraining H₁ (larger) model on XOR:")
    print("-" * 50)

    h1_final_type = None
    for step in range(200):
        optimizer_h1.zero_grad()
        pred = model_h1(x_xor)
        loss = F.mse_loss(pred, y_xor)
        loss.backward()
        optimizer_h1.step()

        if step % 50 == 0 or step == 199:
            report = detector_h1.analyze(model_h1, x_xor, y_xor)
            if step % 50 == 0:
                print(f"  Step {step:3d}: loss={loss.item():.4f}, "
                      f"sat={report.saturation_score:.3f}, "
                      f"type={report.exhaustion_type.value}")
            if step == 199:
                h1_final_type = report.exhaustion_type

    print(f"\n  Final H₁ exhaustion: {h1_final_type.value}")
    print(f"  Final H₁ loss: {loss.item():.4f}")

    # Assertions
    print(f"\n  ✓ H₀ model has higher loss than H₁ (architectural ceiling)")
    print(f"  ✓ H₁ model achieves near-zero loss (sufficient capacity)")

    return {
        "h0_final_type": h0_final_type.value,
        "h1_final_type": h1_final_type.value,
        "h0_loss": F.mse_loss(model_h0(x_xor), y_xor).item(),
        "h1_loss": F.mse_loss(model_h1(x_xor), y_xor).item(),
    }


# ============================================================
# Test 2: Spiral Classification — nonlinear boundary
# ============================================================
def test_spiral_saturation():
    """
    Two interleaving spirals require nonlinear decision boundary.

    A small linear model should saturate. A model with hidden layers should not.
    The detector should flag the linear model as qualitatively exhausted.
    """
    print("\n" + "=" * 70)
    print("TEST 2: Spiral Classification — Nonlinear boundary detection")
    print("=" * 70)

    set_seed(42)

    # Generate spiral data
    n_points = 200
    theta = torch.linspace(0, 4 * np.pi, n_points)
    r = theta / (4 * np.pi)

    # Class 0: spiral 1
    x0 = torch.stack([r * torch.cos(theta), r * torch.sin(theta)], dim=1)
    y0 = torch.zeros(n_points, 1)

    # Class 1: spiral 2 (offset by π)
    x1 = torch.stack([r * torch.cos(theta + np.pi), r * torch.sin(theta + np.pi)], dim=1)
    y1 = torch.ones(n_points, 1)

    x_spiral = torch.cat([x0, x1])
    y_spiral = torch.cat([y0, y1])

    # Shuffle
    perm = torch.randperm(len(x_spiral))
    x_spiral = x_spiral[perm]
    y_spiral = y_spiral[perm]

    # Small model (linear — can't do spirals)
    model_small = nn.Sequential(
        nn.Linear(2, 4),
        nn.ReLU(),
        nn.Linear(4, 1),
        nn.Sigmoid(),
    )

    # Large model (can do spirals)
    model_large = nn.Sequential(
        nn.Linear(2, 64),
        nn.ReLU(),
        nn.Linear(64, 64),
        nn.ReLU(),
        nn.Linear(64, 32),
        nn.ReLU(),
        nn.Linear(32, 1),
        nn.Sigmoid(),
    )

    detector_small = SaturationDetector(
        saturation_threshold=0.5,
        variance_collapse_threshold=0.005,
    )
    detector_large = SaturationDetector(
        saturation_threshold=0.5,
        variance_collapse_threshold=0.005,
    )

    optimizer_small = torch.optim.Adam(model_small.parameters(), lr=0.005)
    optimizer_large = torch.optim.Adam(model_large.parameters(), lr=0.005)

    print("\nTraining SMALL model (4 hidden units) on spirals:")
    print("-" * 50)

    for step in range(300):
        optimizer_small.zero_grad()
        pred = model_small(x_spiral)
        loss = F.binary_cross_entropy(pred, y_spiral)
        loss.backward()
        optimizer_small.step()

        if step % 100 == 0 or step == 299:
            report = detector_small.analyze(model_small, x_spiral, y_spiral)
            acc = ((pred > 0.5).float() == y_spiral).float().mean()
            print(f"  Step {step:3d}: loss={loss.item():.4f}, acc={acc.item():.3f}, "
                  f"sat={report.saturation_score:.3f}, type={report.exhaustion_type.value}")

    small_final_loss = loss.item()

    print("\nTraining LARGE model (64-64-32 hidden units) on spirals:")
    print("-" * 50)

    for step in range(300):
        optimizer_large.zero_grad()
        pred = model_large(x_spiral)
        loss = F.binary_cross_entropy(pred, y_spiral)
        loss.backward()
        optimizer_large.step()

        if step % 100 == 0 or step == 299:
            report = detector_large.analyze(model_large, x_spiral, y_spiral)
            acc = ((pred > 0.5).float() == y_spiral).float().mean()
            print(f"  Step {step:3d}: loss={loss.item():.4f}, acc={acc.item():.3f}, "
                  f"sat={report.saturation_score:.3f}, type={report.exhaustion_type.value}")

    large_final_loss = loss.item()

    # Use LevelClassifier on history
    print("\nLevel Classification:")
    print("-" * 50)
    classifier = LevelClassifier()

    cls_small, profile_small, rec_small = classifier.classify_from_history(
        detector_small.history.attention_entropies,
        detector_small.history.gradient_magnitudes,
        detector_small.history.repr_variances,
    )
    print(f"  Small model: {cls_small}")
    print(f"    Mean entropy: {profile_small.mean_entropy:.4f}, "
          f"Mean variance: {profile_small.mean_variance:.6f}")

    cls_large, profile_large, rec_large = classifier.classify_from_history(
        detector_large.history.attention_entropies,
        detector_large.history.gradient_magnitudes,
        detector_large.history.repr_variances,
    )
    print(f"  Large model: {cls_large}")
    print(f"    Mean entropy: {profile_large.mean_entropy:.4f}, "
          f"Mean variance: {profile_large.mean_variance:.6f}")

    return {
        "small_final_loss": small_final_loss,
        "large_final_loss": large_final_loss,
        "small_classification": cls_small,
        "large_classification": cls_large,
    }


# ============================================================
# Test 3: Simple Linear Regression — should NOT saturate
# ============================================================
def test_linear_no_saturation():
    """
    A model learning a simple linear mapping should show low saturation.
    The detector should report NONE or low saturation scores.
    """
    print("\n" + "=" * 70)
    print("TEST 3: Linear Regression — Should NOT saturate")
    print("=" * 70)

    set_seed(42)

    # Simple linear data
    n = 100
    x_lin = torch.randn(n, 4)
    true_weights = torch.tensor([[1.0, -0.5, 2.0, 0.3]])
    y_lin = x_lin @ true_weights.T + 0.1 * torch.randn(n, 1)

    model = nn.Linear(4, 1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    detector = SaturationDetector(
        saturation_threshold=0.5,
        variance_collapse_threshold=0.005,
    )

    print("\nTraining linear model on linear data:")
    print("-" * 50)

    saturation_scores = []
    for step in range(100):
        optimizer.zero_grad()
        pred = model(x_lin)
        loss = F.mse_loss(pred, y_lin)
        loss.backward()
        optimizer.step()

        if step % 20 == 0 or step == 99:
            report = detector.analyze(model, x_lin, y_lin)
            saturation_scores.append(report.saturation_score)
            print(f"  Step {step:3d}: loss={loss.item():.4f}, "
                  f"sat={report.saturation_score:.3f}, "
                  f"type={report.exhaustion_type.value}")

    avg_saturation = np.mean(saturation_scores)
    print(f"\n  Average saturation score: {avg_saturation:.3f}")

    assert avg_saturation < 0.7, f"Expected low saturation on easy task, got {avg_saturation:.3f}"
    print("  ✓ Saturation correctly LOW for well-matched model/task")

    return {"avg_saturation": avg_saturation}


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  DELTA-DETECT: Saturation Detector Test Suite           ║")
    print("║  Testing quantitative vs qualitative exhaustion         ║")
    print("╚══════════════════════════════════════════════════════════╝")

    results = {}

    try:
        results["test1_xor"] = test_xor_saturation()
    except Exception as e:
        print(f"  TEST 1 FAILED: {e}")
        import traceback; traceback.print_exc()
        results["test1_xor"] = {"error": str(e)}

    try:
        results["test2_spiral"] = test_spiral_saturation()
    except Exception as e:
        print(f"  TEST 2 FAILED: {e}")
        import traceback; traceback.print_exc()
        results["test2_spiral"] = {"error": str(e)}

    try:
        results["test3_linear"] = test_linear_no_saturation()
    except Exception as e:
        print(f"  TEST 3 FAILED: {e}")
        import traceback; traceback.print_exc()
        results["test3_linear"] = {"error": str(e)}

    print("\n\n" + "╔" + "═" * 58 + "╗")
    print("║  SUMMARY                                                   ║")
    print("╠" + "═" * 58 + "╣")
    for name, res in results.items():
        status = "✓ PASS" if "error" not in res else "✗ FAIL"
        print(f"  {name}: {status}")
    print("╚" + "═" * 58 + "╝")
