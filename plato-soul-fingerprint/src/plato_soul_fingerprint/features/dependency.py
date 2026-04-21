"""Dependency features from Cargo.toml / pyproject.toml."""

import os
import re
from collections import defaultdict


REFERENCE_DEPS = {
    "numpy", "pandas", "requests", "serde", "tokio", "clap", "click",
    "flask", "actix-web", "django", "rocket", "reqwest", "hyper",
    "log", "env_logger", "tracing", "anyhow", "thiserror",
}


def _parse_pyproject_deps(path: str):
    deps = {}
    dev_deps = {}
    in_deps = False
    in_dev_deps = False
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[project.dependencies]"):
                in_deps = True
                in_dev_deps = False
                continue
            if "dev-dependencies" in line.lower() or "optional-dependencies" in line.lower():
                in_dev_deps = True
                in_deps = False
                continue
            if line.startswith("[") and line.endswith("]"):
                in_deps = False
                in_dev_deps = False
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip().strip('"').strip("'")
                val = val.strip().strip('"').strip("'")
                if in_deps:
                    deps[key] = val
                elif in_dev_deps:
                    dev_deps[key] = val
                # Handle inline tables like dependencies = {foo = "1.0"}
                if not in_deps and not in_dev_deps:
                    if line.startswith("dependencies"):
                        # crude inline table parsing
                        for m in re.finditer(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"', line):
                            deps[m.group(1)] = m.group(2)
    return deps, dev_deps


def _parse_cargo_deps(path: str):
    deps = {}
    dev_deps = {}
    section = None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[dependencies]"):
                section = "deps"
                continue
            if line.startswith("[dev-dependencies]"):
                section = "dev"
                continue
            if line.startswith("["):
                section = None
                continue
            if "=" in line and section:
                key, val = line.split("=", 1)
                key = key.strip().strip('"')
                val = val.strip().strip('"')
                if section == "deps":
                    deps[key] = val
                elif section == "dev":
                    dev_deps[key] = val
    return deps, dev_deps


def _dep_version_age(version_str: str) -> float:
    """Heuristic: older-looking versions get higher age scores."""
    # Crude: count how many major version bumps away from latest we might be
    # We don't have real registry data, so use major version as proxy
    m = re.search(r"(\d+)", version_str)
    if m:
        major = int(m.group(1))
        return float(major)
    return 0.0


def extract_dependency_features(repo_path: str) -> dict:
    features = {}
    all_deps = {}
    all_dev = {}

    for root, _, files in os.walk(repo_path):
        if ".git" in root:
            continue
        for f in files:
            path = os.path.join(root, f)
            if f == "pyproject.toml":
                d, dd = _parse_pyproject_deps(path)
                all_deps.update(d)
                all_dev.update(dd)
            elif f == "Cargo.toml":
                d, dd = _parse_cargo_deps(path)
                all_deps.update(d)
                all_dev.update(dd)

    total = len(all_deps) + len(all_dev)
    features["dep_count"] = float(total)
    features["dev_dep_ratio"] = len(all_dev) / max(total, 1.0)

    if all_deps:
        ages = [_dep_version_age(v) for v in all_deps.values()]
        features["dep_freshness"] = sum(ages) / len(ages)
    else:
        features["dep_freshness"] = 0.0

    dep_names = set(all_deps.keys()) | set(all_dev.keys())
    if dep_names:
        overlap = len(dep_names & REFERENCE_DEPS) / len(dep_names)
    else:
        overlap = 0.0
    features["dep_overlap"] = overlap

    return features
