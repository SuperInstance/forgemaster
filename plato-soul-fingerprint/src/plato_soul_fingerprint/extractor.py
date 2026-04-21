"""Main SoulExtractor class."""

import os
import json
import subprocess
from typing import Dict, Any, List

from .features import (
    extract_temporal_features,
    extract_stylistic_features,
    extract_structural_features,
    extract_dependency_features,
    extract_communication_features,
    extract_philosophical_features,
)
from .reduction import StandardScaler, PCA, scree_report


class SoulExtractor:
    """Extracts raw features, reduces them via PCA, and writes soul files."""

    def __init__(self, variance_threshold: float = 0.95):
        self.variance_threshold = variance_threshold
        self.scaler = StandardScaler()
        self.pca = PCA(variance_threshold=variance_threshold)

    def extract_raw(self, repo_path: str) -> Dict[str, Any]:
        repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            raise ValueError(f"Not a git repository: {repo_path}")

        py_count = 0
        rs_count = 0
        for root, _, files in os.walk(repo_path):
            if ".git" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    py_count += 1
                elif f.endswith(".rs"):
                    rs_count += 1

        primary = "python" if py_count >= rs_count else "rust"

        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        commit_count = int(result.stdout.strip()) if result.returncode == 0 else 0

        raw = {}
        raw.update(extract_temporal_features(repo_path))
        raw.update(extract_stylistic_features(repo_path))
        raw.update(extract_structural_features(repo_path))
        raw.update(extract_dependency_features(repo_path))
        raw.update(extract_communication_features(repo_path))
        raw.update(extract_philosophical_features(repo_path))

        raw = {k: float(v) for k, v in raw.items()}

        metadata = {
            "repo_name": os.path.basename(repo_path),
            "repo_path": repo_path,
            "primary_language": primary,
            "commit_count": commit_count,
            "raw_feature_count": len(raw),
        }

        return {"metadata": metadata, "raw_features": raw}

    def fit(self, repos: List[str]):
        all_keys = set()
        matrices = []
        for repo in repos:
            data = self.extract_raw(repo)
            all_keys.update(data["raw_features"].keys())
            matrices.append(data)

        all_keys = sorted(all_keys)
        X = []
        for data in matrices:
            vec = [data["raw_features"].get(k, 0.0) for k in all_keys]
            X.append(vec)

        import numpy as np
        X = self.scaler.fit_transform(X)
        self.pca.fit(X)
        self._feature_keys = all_keys
        return self

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        if not hasattr(self, "_feature_keys"):
            raise RuntimeError("Extractor must be fit before transform")

        import numpy as np
        vec = [raw_data["raw_features"].get(k, 0.0) for k in self._feature_keys]
        vec = self.scaler.transform([vec])
        pca_vec = self.pca.transform(vec)[0]

        result = dict(raw_data)
        result["pca_vector"] = pca_vec.tolist()
        result["pca_metadata"] = {
            "n_components": int(self.pca.n_components_),
            "variance_threshold": self.variance_threshold,
            "explained_variance_ratio_cumsum": float(
                np.cumsum(self.pca.explained_variance_ratio_)[self.pca.n_components_ - 1]
            ),
        }
        return result

    def extract(self, repo_path: str) -> Dict[str, Any]:
        return self.extract_raw(repo_path)

    def write(self, data: Dict[str, Any], output_dir: str = None):
        repo_name = data["metadata"]["repo_name"]
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base = os.path.join(output_dir, repo_name)
        else:
            base = os.path.join(data["metadata"]["repo_path"], repo_name)

        json_path = base + ".soul.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        txt_path = base + ".soul.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self._human_report(data))

        return json_path, txt_path

    def _human_report(self, data: Dict[str, Any]) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("SOUL FINGERPRINT REPORT")
        lines.append("=" * 60)
        meta = data["metadata"]
        lines.append(f"Repository : {meta['repo_name']}")
        lines.append(f"Language   : {meta['primary_language']}")
        lines.append(f"Commits    : {meta['commit_count']}")
        lines.append(f"Raw dims   : {meta['raw_feature_count']}")
        if "pca_vector" in data:
            lines.append(f"Soul dims  : {len(data['pca_vector'])}")
            lines.append(
                f"Variance   : {data['pca_metadata']['explained_variance_ratio_cumsum']:.2%}"
            )
        lines.append("")
        lines.append("Top Raw Features (by absolute value)")
        lines.append("-" * 60)
        raw = data["raw_features"]
        top = sorted(raw.items(), key=lambda x: abs(x[1]), reverse=True)[:15]
        for k, v in top:
            lines.append(f"  {k:<46s} {v:10.4f}")
        lines.append("")
        if "pca_vector" in data:
            lines.append("PCA Vector (first 20 dimensions)")
            lines.append("-" * 60)
            vec = data["pca_vector"]
            for i, v in enumerate(vec[:20]):
                lines.append(f"  dim_{i:03d}: {v:10.4f}")
            if len(vec) > 20:
                lines.append(f"  ... ({len(vec) - 20} more)")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
