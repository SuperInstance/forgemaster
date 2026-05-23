"""Analysis tools: distance, clustering, reporting, comparison."""

import json
import math
import os
from typing import List, Dict, Any
import numpy as np

from .reduction import StandardScaler, PCA
from .extractor import SoulExtractor


def _safe_vector(data: Dict[str, Any]) -> np.ndarray:
    """Extract the PCA vector from a soul dict or use raw features."""
    if "pca_vector" in data:
        vec = np.asarray(data["pca_vector"], dtype=np.float64)
    elif "raw_features" in data:
        vec = np.asarray(list(data["raw_features"].values()), dtype=np.float64)
    else:
        vec = np.asarray(list(data.values()), dtype=np.float64)
    return vec


def cosine_distance(repo_a: Dict[str, Any], repo_b: Dict[str, Any]) -> float:
    """Cosine distance between two soul vectors (0 = identical, 1 = orthogonal)."""
    a = _safe_vector(repo_a)
    b = _safe_vector(repo_b)
    if a.shape != b.shape:
        raise ValueError(f"Vector shape mismatch: {a.shape} vs {b.shape}")
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    # Clamp to [-1, 1] to avoid floating-point drift
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def _vec_cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def soul_distance(repo_a_path: str, repo_b_path: str) -> float:
    """Load two .soul.json files and return cosine distance."""
    with open(repo_a_path, "r", encoding="utf-8") as f:
        a = json.load(f)
    with open(repo_b_path, "r", encoding="utf-8") as f:
        b = json.load(f)
    return cosine_distance(a, b)


def _linkage_matrix(vectors: np.ndarray) -> List[List[float]]:
    """Hierarchical clustering via single linkage (naive O(n^3))."""
    n = vectors.shape[0]
    if n < 2:
        return []

    members = {i: [i] for i in range(n)}
    active = set(range(n))
    dist_map = {}
    for i in range(n):
        for j in range(i + 1, n):
            dist_map[(i, j)] = _vec_cosine_distance(vectors[i], vectors[j])

    linkage = []
    next_id = n

    while len(active) > 1:
        best_d = float("inf")
        best_pair = None
        active_list = sorted(active)
        for idx_a in range(len(active_list)):
            for idx_b in range(idx_a + 1, len(active_list)):
                i, j = active_list[idx_a], active_list[idx_b]
                key = (i, j)
                d = dist_map.get(key, float("inf"))
                if d < best_d:
                    best_d = d
                    best_pair = (i, j)

        if best_pair is None:
            break

        i, j = best_pair
        new_members = members[i] + members[j]
        size = len(new_members)
        linkage.append([float(i), float(j), best_d, float(size)])

        active.discard(i)
        active.discard(j)

        for k in active:
            min_d = float("inf")
            for a_idx in new_members:
                for b_idx in members[k]:
                    key = (min(a_idx, b_idx), max(a_idx, b_idx))
                    min_d = min(min_d, dist_map.get(key, float("inf")))
            dist_map[(min(k, next_id), max(k, next_id))] = min_d

        members[next_id] = new_members
        active.add(next_id)
        next_id += 1

    return linkage


def soul_cluster(repo_paths: List[str]) -> Dict[str, Any]:
    """Hierarchical clustering of repos based on soul vectors."""
    vectors = []
    names = []
    for path in repo_paths:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vectors.append(_safe_vector(data))
        names.append(data.get("metadata", {}).get("repo_name", path))

    # Pad to same length
    max_len = max(len(v) for v in vectors)
    padded = np.zeros((len(vectors), max_len), dtype=np.float64)
    for i, v in enumerate(vectors):
        padded[i, : len(v)] = v

    linkage = _linkage_matrix(padded)

    return {
        "names": names,
        "linkage": linkage,
        "n_repos": len(names),
    }


def soul_report(repo_path: str) -> str:
    """Generate a human-readable report from a .soul.json file."""
    with open(repo_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    raw = data.get("raw_features", {})
    pca = data.get("pca_vector", [])

    lines = []
    lines.append("=" * 50)
    lines.append("SOUL REPORT")
    lines.append("=" * 50)
    lines.append(f"Repository : {meta.get('repo_name', 'unknown')}")
    lines.append(f"Language   : {meta.get('primary_language', 'unknown')}")
    lines.append(f"Commits    : {meta.get('commit_count', 'unknown')}")
    lines.append(f"Soul dims  : {len(pca)} (from {len(raw)} raw features)")
    lines.append("")

    # Top feature values
    lines.append("Top Raw Features (by |z-score|)")
    lines.append("-" * 50)
    if raw:
        values = np.asarray(list(raw.values()), dtype=np.float64)
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            std = 1.0
        zscores = {k: abs((v - mean) / std) for k, v in raw.items()}
        top = sorted(zscores.items(), key=lambda x: x[1], reverse=True)[:10]
        for k, z in top:
            lines.append(f"  {k:40s} {raw[k]:10.4f} (z={z:.2f})")
    lines.append("")

    # PC loadings summary
    lines.append("PCA Summary")
    lines.append("-" * 50)
    lines.append(f"  Intrinsic dimensionality: {len(pca)}")
    lines.append("")
    lines.append("=" * 50)

    return "\n".join(lines)


def feature_importance(data: List[Dict[str, Any]]) -> List[tuple]:
    """Identify which raw features contribute most to the PCA dimensions.
    Uses the PCA components_ matrix (loadings) weighted by explained_variance_ratio_.
    Returns a list of (feature_name, importance_score) sorted descending.
    """
    if not data:
        return []
    all_keys = sorted({k for d in data for k in d.get("raw_features", {})})
    if not all_keys:
        return []
    X = np.array([[d["raw_features"].get(k, 0.0) for k in all_keys] for d in data], dtype=np.float64)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    pca = PCA(variance_threshold=0.95)
    pca.fit(Xs)
    n_components = pca.n_components_
    loadings = pca.components_[:n_components]  # shape (k, n_features)
    ratios = pca.explained_variance_ratio_[:n_components]
    importance = np.sum(np.abs(loadings) * ratios[:, np.newaxis], axis=0)
    idx = np.argsort(importance)[::-1]
    return [(all_keys[i], float(importance[i])) for i in idx]


def dendrogram_text(linkage: List[List[float]], names: List[str]) -> str:
    """Render a text-based dendrogram from the linkage matrix and names list.
    Uses simple box-drawing characters and shows merge distances.
    """
    if not names:
        return ""
    if not linkage:
        if len(names) == 1:
            return names[0]
        return ""
    nodes = {}
    for i, name in enumerate(names):
        nodes[i] = ("leaf", name)
    next_id = len(names)
    for row in linkage:
        i, j, d, size = row
        i = int(round(float(i)))
        j = int(round(float(j)))
        left = nodes[i]
        right = nodes[j]
        nodes[next_id] = ("node", float(d), left, right, int(size))
        next_id += 1
    root = nodes[next_id - 1]
    lines = []
    def _render(node, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
        if node[0] == "leaf":
            lines.append(f"{prefix}{connector}{node[1]}")
        else:
            _, dist, left, right, size = node
            lines.append(f"{prefix}{connector}merge dist={dist:.4f}")
            children = [left, right]
            for idx_child, child in enumerate(children):
                child_is_last = (idx_child == len(children) - 1)
                child_prefix = prefix + ("    " if is_last else "│   ")
                _render(child, child_prefix, child_is_last)
    _render(root, "", True)
    return "\n".join(lines)


def batch_extract(directory: str) -> Dict[str, Any]:
    """Scan a directory for git repos, extract all, fit PCA, transform, write soul files.
    Returns summary dict with count, avg_features, pca_dims.
    """
    directory = os.path.abspath(directory)
    repo_paths = []
    for entry in os.listdir(directory):
        path = os.path.join(directory, entry)
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, ".git")):
            repo_paths.append(path)
    if not repo_paths:
        return {"count": 0, "avg_features": 0.0, "pca_dims": 0}
    extractor = SoulExtractor()
    extractor.fit(repo_paths)
    total_features = 0
    for repo_path in repo_paths:
        raw = extractor.extract(repo_path)
        total_features += len(raw["raw_features"])
        transformed = extractor.transform(raw)
        extractor.write(transformed, output_dir=None)
    return {
        "count": len(repo_paths),
        "avg_features": total_features / len(repo_paths),
        "pca_dims": int(extractor.pca.n_components_),
    }


_FEATURE_PHRASES = {
    "commit_frequency": ("frequent committer", "sparse committer"),
    "commit_burstiness": ("burst committer", "steady committer"),
    "commit_size_mean": ("large commits", "small commits"),
    "commit_size_std": ("variable commit sizes", "uniform commit sizes"),
    "commit_size_max": ("massive commits", "tiny commits"),
    "batch_vs_incremental": ("batch committer", "incremental committer"),
    "function_length_mean": ("verbose functions", "concise functions"),
    "function_length_std": ("inconsistent function lengths", "consistent function lengths"),
    "function_length_median": ("long median functions", "short median functions"),
    "naming_convention_score": ("snake_case purist", "camelCase enthusiast"),
    "doc_comment_frequency": ("highly documented", "barely documented"),
    "error_handling_style": ("unwrap enthusiast", "Result handler"),
    "type_annotation_density": ("typed fanatic", "untyped free spirit"),
    "magic_number_frequency": ("magic number lover", "literal purist"),
    "test_ratio": ("test-driven", "test-averse"),
    "documentation_ratio": ("doc-heavy", "doc-light"),
    "directory_depth_mean": ("deeply nested", "flat layout"),
    "module_cohesion": ("tight module", "loosely coupled"),
    "dep_count": ("dependency-heavy", "minimalist"),
    "dev_dep_ratio": ("dev-tooling heavy", "runtime-focused"),
    "dep_freshness": ("bleeding-edge deps", "stable deps"),
    "dep_overlap": ("mainstream stack", "niche stack"),
    "msg_length_mean": ("verbose commit messages", "terse commit messages"),
    "msg_length_std": ("inconsistent message lengths", "consistent message lengths"),
    "msg_length_max": ("epic commit messages", "brief commit messages"),
    "conventional_commit_score": ("conventional committer", "free-form committer"),
    "imperative_verb_frequency": ("imperative committer", "descriptive committer"),
    "emoji_frequency": ("emoji committer", "emoji-free committer"),
    "reference_frequency": ("reference-heavy committer", "self-contained committer"),
    "vocabulary_richness": ("rich vocabulary", "plain vocabulary"),
    "metaphor_density": ("metaphorical writer", "literal writer"),
    "architecture_mention_frequency": ("architecture-aware", "implementation-focused"),
    "doc_length_total": ("prolific documenter", "sparse documenter"),
}


def soul_signature(data: Dict[str, Any]) -> str:
    """Generate a compact human-readable summary: top 3 distinguishing traits.
    Maps high-z features to plain language short phrases.
    """
    raw = data.get("raw_features", {})
    if not raw:
        return "unknown"
    values = np.asarray(list(raw.values()), dtype=np.float64)
    mean = np.mean(values)
    std = np.std(values)
    if std == 0:
        std = 1.0
    zscores = {k: (v - mean) / std for k, v in raw.items()}
    sorted_features = sorted(zscores.items(), key=lambda x: abs(x[1]), reverse=True)
    traits = []
    for k, z in sorted_features[:3]:
        phrase = _FEATURE_PHRASES.get(k)
        if phrase is None:
            if k.startswith("file_count_"):
                lang = k.split("_", 2)[2]
                phrase = (f"{lang}-purist", f"{lang}-averse")
            elif k.startswith("commit_hour_"):
                phrase = ("hour-biased committer", "hour-agnostic committer")
            else:
                phrase = (f"high {k}", f"low {k}")
        traits.append(phrase[0] if z > 0 else phrase[1])
    return ", ".join(traits)


def soul_compare(repo_a_path: str, repo_b_path: str) -> str:
    """Compare two repos and highlight the dimensions that differ most."""
    with open(repo_a_path, "r", encoding="utf-8") as f:
        a = json.load(f)
    with open(repo_b_path, "r", encoding="utf-8") as f:
        b = json.load(f)

    raw_a = a.get("raw_features", {})
    raw_b = b.get("raw_features", {})
    all_keys = sorted(set(raw_a.keys()) | set(raw_b.keys()))

    diffs = []
    for k in all_keys:
        va = raw_a.get(k, 0.0)
        vb = raw_b.get(k, 0.0)
        diff = abs(va - vb)
        diffs.append((k, va, vb, diff))

    diffs.sort(key=lambda x: x[3], reverse=True)

    name_a = a.get("metadata", {}).get("repo_name", "A")
    name_b = b.get("metadata", {}).get("repo_name", "B")

    lines = []
    lines.append("=" * 60)
    lines.append(f"SOUL COMPARISON: {name_a} vs {name_b}")
    lines.append("=" * 60)
    lines.append(f"{'Feature':<36} {'A':>10} {'B':>10} {'|Diff|':>10}")
    lines.append("-" * 60)
    for k, va, vb, diff in diffs[:15]:
        lines.append(f"{k:<36} {va:>10.4f} {vb:>10.4f} {diff:>10.4f}")
    lines.append("")
    lines.append(f"Cosine distance: {cosine_distance(a, b):.4f}")
    lines.append("=" * 60)

    return "\n".join(lines)
