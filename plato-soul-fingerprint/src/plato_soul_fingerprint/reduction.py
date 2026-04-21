"""Manual PCA implementation using only numpy."""

from typing import Tuple
import numpy as np


class StandardScaler:
    """Z-score standardization: (x - mean) / std."""

    def __init__(self):
        self.mean_ = None
        self.std_ = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=np.float64)
        self.mean_ = np.nanmean(X, axis=0)
        self.std_ = np.nanstd(X, axis=0)
        # Avoid divide-by-zero on constant features
        self.std_[self.std_ == 0] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        return (X - self.mean_) / self.std_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


class PCA:
    """Principal Component Analysis via covariance eigendecomposition."""

    def __init__(self, n_components: int = None, variance_threshold: float = 0.95):
        self.n_components = n_components
        self.variance_threshold = variance_threshold
        self.components_ = None
        self.explained_variance_ = None
        self.explained_variance_ratio_ = None
        self.mean_ = None
        self.n_components_ = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=np.float64)
        self.mean_ = np.mean(X, axis=0)
        X_centered = X - self.mean_

        n_samples = X_centered.shape[0]
        cov = np.dot(X_centered.T, X_centered) / (n_samples - 1)

        eigenvalues, eigenvectors = np.linalg.eigh(cov)

        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        eigenvalues = np.maximum(eigenvalues, 0.0)

        total_var = np.sum(eigenvalues)
        if total_var > 0:
            self.explained_variance_ratio_ = eigenvalues / total_var
        else:
            self.explained_variance_ratio_ = np.zeros_like(eigenvalues)
        self.explained_variance_ = eigenvalues
        self.components_ = eigenvectors.T

        if self.n_components is not None:
            self.n_components_ = min(self.n_components, self.components_.shape[0])
        else:
            cumsum = np.cumsum(self.explained_variance_ratio_)
            self.n_components_ = int(np.searchsorted(cumsum, self.variance_threshold) + 1)
            self.n_components_ = min(self.n_components_, self.components_.shape[0])

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        X_centered = X - self.mean_
        return np.dot(X_centered, self.components_[: self.n_components_].T)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def inverse_transform(self, X_reduced: np.ndarray) -> np.ndarray:
        return np.dot(X_reduced, self.components_[: self.n_components_]) + self.mean_


def scree_report(pca: PCA) -> str:
    """Return a human-readable scree plot as ASCII art."""
    lines = ["Scree Plot (explained variance ratio per PC)", "=" * 46]
    ratios = pca.explained_variance_ratio_
    max_ratio = np.max(ratios) if len(ratios) else 1.0
    if max_ratio == 0:
        max_ratio = 1.0
    for i, r in enumerate(ratios[: min(20, len(ratios))]):
        bar_len = int(round((r / max_ratio) * 40))
        bar = "#" * bar_len
        lines.append(f"PC{i+1:02d} |{bar:<40}| {r:.4f}")
    lines.append(f"Kept {pca.n_components_} components for {pca.variance_threshold:.0%} variance")
    return "\n".join(lines)
