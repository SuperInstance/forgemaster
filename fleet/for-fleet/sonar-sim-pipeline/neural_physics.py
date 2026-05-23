"""SonarVision Neural Physics Surrogate — learns FLUX physics from synthetic data.

A JEPA-style encoder-predictor that learns to simulate underwater acoustics
without running the full physics engine. Trained on FLUX-generated data.
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# =============================================================================
# FLUX physics engine (inline — zero deps beyond math)
# =============================================================================

WATER_TYPES = {0: "Coastal", 1: "Oceanic Type II", 2: "Oceanic Type IB", 3: "Clear Oceanic"}
SEDIMENT_NAMES = {0: "mud", 1: "sand", 2: "gravel", 3: "rock", 4: "seagrass"}
SEDIMENT_REFLECT = {0: 0.3, 1: 0.5, 2: 0.7, 3: 0.85, 4: 0.2}


def flux_physics(depth: float, chl: float = 5.0, season: int = 0,
                 sediment: int = 1, wl: float = 480.0, sal: float = 35.0) -> Dict[str, float]:
    """Compute FLUX 9-opcode physics at a single depth. Deterministic."""
    wt = 0 if chl > 10 else 1 if chl > 1 else 2 if chl > 0.1 else 3
    wa = wl / 1000.0
    if wt <= 1:
        ab = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
    elif wt == 2:
        ab = 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
    else:
        ab = 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))
    ns = 0.002 * (480.0 / wl)**4.3
    sc = ns * max(0.01, 1.0 - depth * 0.003)
    tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
    st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
    te = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
    dtdz = -(st - dt) * (depth - tc) / (tw**2) * math.exp(-((depth - tc)**2) / (2 * tw**2))
    sr = SEDIMENT_REFLECT.get(sediment, 0.5) * math.exp(-depth * 0.003)
    att = ab + sc
    vis = min(depth, 1.7 / max(att, 0.001))
    ss = (1449.2 + 4.6 * te - 0.055 * te**2 + 0.00029 * te**3 +
          (1.34 - 0.01 * te) * (sal - 35) + 0.016 * depth)
    return {
        "temperature": round(te, 2),
        "sound_speed": round(ss, 1),
        "absorption": round(ab, 4),
        "visibility": round(vis, 2),
        "seabed_reflectivity": round(sr, 4),
        "attenuation": round(att, 3),
    }


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class DataConfig:
    n_samples: int = 100000
    batch_size: int = 256
    train_split: float = 0.8
    val_split: float = 0.1
    seed: int = 42


@dataclass
class ModelConfig:
    input_dim: int = 5
    hidden_dim: int = 128
    latent_dim: int = 64
    output_dim: int = 6
    dropout: float = 0.15
    n_ensemble: int = 3


@dataclass
class TrainConfig:
    epochs: int = 50
    lr: float = 3e-4
    weight_decay: float = 1e-5
    early_stop: int = 20
    grad_clip: float = 1.0
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


# =============================================================================
# Synthetic dataset
# =============================================================================

def _gen_sample() -> Tuple[np.ndarray, np.ndarray]:
    """Generate a single (input, target) pair from FLUX physics."""
    depth = random.uniform(0, 100)
    chl = random.uniform(0.1, 20)
    season = random.randint(0, 1)
    sediment = random.randint(0, 4)
    x = np.array([depth, chl, season, sediment, 480.0], dtype=np.float32)
    p = flux_physics(depth, chl, season, sediment)
    y = np.array([p["temperature"], p["sound_speed"], p["absorption"],
                  p["visibility"], p["seabed_reflectivity"], p["attenuation"]],
                 dtype=np.float32)
    return x, y


class PhysicsDataset(torch.utils.data.Dataset):
    """Dataset of synthetic FLUX physics samples."""

    def __init__(self, n_samples: int = 100000, seed: int = 42):
        rng = random.Random(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        data = [_gen_sample() for _ in range(n_samples)]
        self.x = torch.tensor(np.stack([d[0] for d in data]))
        self.y = torch.tensor(np.stack([d[1] for d in data]))

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        return self.x[idx], self.y[idx]


def create_synthetic_data(n_samples: int = 100000, batch_size: int = 256,
                          seed: int = 42) -> Dict[str, torch.utils.data.DataLoader]:
    """Create train/val/test DataLoaders from synthetic FLUX data."""
    dataset = PhysicsDataset(n_samples, seed)
    n = len(dataset)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    n_test = n - n_train - n_val
    train, val, test = torch.utils.data.random_split(
        dataset, [n_train, n_val, n_test],
        generator=torch.Generator().manual_seed(seed))
    return {
        "train": torch.utils.data.DataLoader(train, batch_size=batch_size, shuffle=True),
        "val": torch.utils.data.DataLoader(val, batch_size=batch_size * 2),
        "test": torch.utils.data.DataLoader(test, batch_size=batch_size * 2),
    }


# =============================================================================
# Model architecture (JEPA-style encoder-predictor)
# =============================================================================

class DeepPhysEncoder(nn.Module):
    """Encoder: input → latent representation."""

    def __init__(self, input_dim: int = 5, hidden_dim: int = 128,
                 latent_dim: int = 64, dropout: float = 0.15):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.LayerNorm(hidden_dim * 2),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, latent_dim),
            nn.LayerNorm(latent_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MultiHeadPredictor(nn.Module):
    """Latent → 6 physics outputs, each with its own head."""

    def __init__(self, latent_dim: int = 64, output_dim: int = 6):
        super().__init__()
        self.heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(latent_dim, latent_dim // 2),
                nn.LeakyReLU(0.1),
                nn.Linear(latent_dim // 2, 1),
            )
            for _ in range(output_dim)
        ])

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        outputs = [head(z) for head in self.heads]
        return torch.cat(outputs, dim=-1)


class PhysicsInformedHead(nn.Module):
    """Wraps predictions with hard constraint enforcement."""

    def __init__(self, raw_head: MultiHeadPredictor):
        super().__init__()
        self.raw_head = raw_head

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        raw = self.raw_head(z)
        # Hard constraints for each output
        out = torch.zeros_like(raw)
        out[:, 0] = torch.clamp(raw[:, 0], -2.0, 40.0)         # temperature [-2, 40]
        out[:, 1] = torch.clamp(raw[:, 1], 1400.0, 1600.0)     # sound_speed [1400, 1600]
        out[:, 2] = raw[:, 2]  # absorption (no hard limit)
        out[:, 3] = torch.clamp(raw[:, 3], 0.0, 100.0)         # visibility [0, 100]
        out[:, 4] = torch.clamp(raw[:, 4], 0.0, 1.0)           # seabed_reflectivity [0, 1]
        out[:, 5] = raw[:, 5]  # attenuation (no hard limit)
        return out


class PhysicsSurrogate(nn.Module):
    """JEPA-style physics surrogate with ensemble voting."""

    def __init__(self, model_cfg: Optional[ModelConfig] = None):
        super().__init__()
        cfg = model_cfg or ModelConfig()
        self.encoder = DeepPhysEncoder(cfg.input_dim, cfg.hidden_dim, cfg.latent_dim, cfg.dropout)
        self.predictor = PhysicsInformedHead(MultiHeadPredictor(cfg.latent_dim, cfg.output_dim))
        self.ensemble = nn.ModuleList([
            nn.Sequential(
                DeepPhysEncoder(cfg.input_dim, cfg.hidden_dim, cfg.latent_dim, cfg.dropout),
                PhysicsInformedHead(MultiHeadPredictor(cfg.latent_dim, cfg.output_dim)),
            )
            for _ in range(cfg.n_ensemble)
        ])
        self.output_names = ["temperature", "sound_speed", "absorption",
                             "visibility", "seabed_reflectivity", "attenuation"]

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        z = self.encoder(x)
        pred = self.predictor(z)
        # Ensemble predictions
        ensemble_preds = torch.stack([enc(x) for enc, _ in self.ensemble])
        # Uncertainty as std across ensemble
        uncertainty = ensemble_preds.std(dim=0)
        return {
            "predictions": pred,
            "uncertainties": uncertainty,
            "ensemble_predictions": ensemble_preds.mean(dim=0),
            "latent": z,
        }

    def predict_dict(self, x: torch.Tensor) -> Dict[str, float]:
        """Convenience: forward pass returns dict of named outputs."""
        out = self.forward(x)
        preds = out["predictions"][0].detach().cpu().numpy()
        unc = out["uncertainties"][0].detach().cpu().numpy()
        return {
            name: {"value": float(preds[i]), "uncertainty": float(unc[i])}
            for i, name in enumerate(self.output_names)
        }


# =============================================================================
# Training
# =============================================================================

def _physics_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Combined MSE + physics gradient penalty."""
    mse = F.mse_loss(pred, target)
    # Gradient penalty: penalize non-smooth profiles
    grad = pred[:, 1] - pred[:, 0]  # temp gradient
    grad_penalty = 0.01 * (grad ** 2).mean()
    return mse + grad_penalty


def train(
    model: PhysicsSurrogate,
    dataloaders: Dict[str, torch.utils.data.DataLoader],
    train_cfg: Optional[TrainConfig] = None,
    model_cfg: Optional[ModelConfig] = None,
    callback=None,
) -> Dict:
    """Train the physics surrogate with early stopping and checkpointing."""
    cfg = train_cfg or TrainConfig()
    device = torch.device(cfg.device)
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)
    scaler = torch.amp.GradScaler() if device.type == "cuda" else None

    history = {"train_loss": [], "val_loss": [], "best_epoch": 0}
    best_loss = float("inf")
    no_improve = 0

    for epoch in range(cfg.epochs):
        model.train()
        train_loss = 0.0
        for x, y in dataloaders["train"]:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            if scaler:
                with torch.amp.autocast():
                    out = model(x)
                    loss = _physics_loss(out["predictions"], y)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                out = model(x)
                loss = _physics_loss(out["predictions"], y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                optimizer.step()
            train_loss += loss.item() * len(x)
        train_loss /= len(dataloaders["train"].dataset)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x, y in dataloaders["val"]:
                x, y = x.to(device), y.to(device)
                out = model(x)
                loss = _physics_loss(out["predictions"], y)
                val_loss += loss.item() * len(x)
        val_loss /= len(dataloaders["val"].dataset)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        scheduler.step()

        if callback:
            callback(epoch, train_loss, val_loss)

        if val_loss < best_loss:
            best_loss = val_loss
            history["best_epoch"] = epoch
            no_improve = 0
        else:
            no_improve += 1

        if no_improve >= cfg.early_stop:
            print(f"Early stopping at epoch {epoch}")
            break

    history["best_loss"] = best_loss
    return history


# =============================================================================
# Benchmarking
# =============================================================================

def benchmark(model: PhysicsSurrogate, n_queries: int = 10000,
              device: str = "cpu") -> Dict:
    """Benchmark the surrogate vs ground truth FLUX physics."""
    model.eval()
    device_t = torch.device(device)
    model = model.to(device_t)

    import time
    errors = {name: [] for name in model.output_names}
    ground_truths = {name: [] for name in model.output_names}

    # Generate random test cases
    for _ in range(n_queries):
        depth = random.uniform(0, 100)
        chl = random.uniform(0.1, 20)
        season = random.randint(0, 1)
        sediment = random.randint(0, 4)
        x = torch.tensor([[depth, chl, season, sediment, 480.0]], dtype=torch.float32).to(device_t)

        # Ground truth
        gt = flux_physics(depth, chl, season, sediment)

        # Surrogate prediction
        with torch.no_grad():
            out = model(x)
        pred = out["predictions"][0].cpu().numpy()

        for i, name in enumerate(model.output_names):
            errors[name].append(abs(pred[i] - gt[name]))
            ground_truths[name].append(gt[name])

    # Speed benchmark
    start = time.time()
    with torch.no_grad():
        x_batch = torch.randn(1000, 5, device=device_t)
        for _ in range(10):
            model(x_batch)
    elapsed = time.time() - start
    queries_per_sec = 10000 / elapsed

    return {
        "n_queries": n_queries,
        "queries_per_sec": round(queries_per_sec, 0),
        "mae": {name: round(float(np.mean(errors[name])), 4)
                for name in model.output_names},
        "rmse": {name: round(float(np.sqrt(np.mean(np.square(errors[name])))), 4)
                 for name in model.output_names},
        "max_error": {name: round(float(np.max(errors[name])), 4)
                      for name in model.output_names},
    }


# =============================================================================
# Profile prediction
# =============================================================================

def predict_profile(model: PhysicsSurrogate, start: float = 0, end: float = 100,
                    step: float = 5, chl: float = 5.0, season: int = 0,
                    sediment: int = 1, device: str = "cpu") -> Dict:
    """Predict a full depth profile and compare with ground truth."""
    model.eval()
    device_t = torch.device(device)
    model = model.to(device_t)

    depths = list(range(start, end + 1, int(step)))
    surrogate_out = []
    ground_truth = []

    for d in depths:
        x = torch.tensor([[float(d), chl, season, sediment, 480.0]], dtype=torch.float32).to(device_t)
        with torch.no_grad():
            out = model(x)
        pred = out["predictions"][0].cpu().numpy()
        names = model.output_names
        surrogate_out.append({names[i]: float(pred[i]) for i in range(len(names))})
        ground_truth.append(flux_physics(float(d), chl, season, sediment))

    return {
        "depths": depths,
        "surrogate": surrogate_out,
        "ground_truth": ground_truth,
        "parameters": {"chl": chl, "season": season, "sediment": sediment},
    }
