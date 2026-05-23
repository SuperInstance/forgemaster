"""Structural features from file tree."""

import os
from collections import defaultdict


EXTENSION_MAP = {
    ".py": "python",
    ".rs": "rust",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".c": "c",
    ".cpp": "cpp",
    ".cu": "cuda",
    ".cuh": "cuda",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".rb": "ruby",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
}


def _is_test_file(name: str) -> bool:
    lowered = name.lower()
    return "test" in lowered or "spec" in lowered


def _is_doc_file(ext: str) -> bool:
    return ext in {".md", ".rst", ".txt"}


def extract_structural_features(repo_path: str) -> dict:
    features = defaultdict(float)
    ext_counts = defaultdict(int)
    test_count = 0
    doc_count = 0
    code_count = 0
    depths = []
    internal_imports = 0
    external_imports = 0

    for root, dirs, files in os.walk(repo_path):
        if ".git" in root:
            continue
        rel_root = os.path.relpath(root, repo_path)
        depth = rel_root.count(os.sep) if rel_root != "." else 0

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            lang = EXTENSION_MAP.get(ext, "other")
            ext_counts[lang] += 1

            path = os.path.join(root, f)
            if lang in ("python", "rust", "javascript", "typescript", "go", "c", "cpp", "java", "ruby"):
                code_count += 1
                depths.append(depth)
                if _is_test_file(f):
                    test_count += 1

                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            line = line.strip()
                            if lang == "python":
                                if line.startswith("import ") or line.startswith("from "):
                                    if line.startswith("from .") or line.startswith("import ."):
                                        internal_imports += 1
                                    else:
                                        external_imports += 1
                            elif lang == "rust":
                                if line.startswith("use "):
                                    if "crate::" in line or "self::" in line or "super::" in line:
                                        internal_imports += 1
                                    else:
                                        external_imports += 1
                except Exception:
                    pass

            if _is_doc_file(ext):
                doc_count += 1

    total_files = sum(ext_counts.values())
    for lang, count in ext_counts.items():
        features[f"file_count_{lang}"] = count / max(total_files, 1.0)

    features["test_ratio"] = test_count / max(total_files, 1.0)
    features["documentation_ratio"] = doc_count / max(code_count, 1.0)

    if depths:
        features["directory_depth_mean"] = sum(depths) / len(depths)
    else:
        features["directory_depth_mean"] = 0.0

    total_imp = internal_imports + external_imports
    if total_imp > 0:
        features["module_cohesion"] = internal_imports / total_imp
    else:
        features["module_cohesion"] = 0.0

    return dict(features)
