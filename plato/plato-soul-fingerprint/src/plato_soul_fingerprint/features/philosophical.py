"""Philosophical features from README and architecture docs."""

import os
import re
from collections import Counter


ARCHITECTURE_PATTERNS = {
    "mvc", "mvvm", "mvp", "ecs", "microservices", "monolith", "serverless",
    "layered", "hexagonal", "onion", "clean architecture", "event driven",
    "cqrs", "ddd", "domain driven", "soa", "peer to peer", "p2p",
    "pipeline", "batch", "streaming", "reactive", "functional",
}

METAPHOR_PATTERNS = {
    "like a", "as a", "heart of", "soul of", "backbone", "brain",
    "engine", "wheel", "bridge", "foundation", "pillar", "ecosystem",
    "landscape", "journey", "roadmap", "vision", "philosophy",
}


def _read_docs(repo_path: str):
    """Yield text content from likely doc files."""
    candidates = []
    for root, _, files in os.walk(repo_path):
        if ".git" in root:
            continue
        for f in files:
            lowered = f.lower()
            if lowered.startswith("readme") or lowered.startswith("contributing") or lowered.startswith("architecture"):
                candidates.append(os.path.join(root, f))
            elif f.endswith(".md") or f.endswith(".rst"):
                candidates.append(os.path.join(root, f))

    for path in candidates[:20]:  # cap to avoid huge repos
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                yield fh.read()
        except Exception:
            pass


def _tokenize(text: str):
    return re.findall(r"[a-zA-Z']+", text.lower())


def extract_philosophical_features(repo_path: str) -> dict:
    features = {}
    texts = list(_read_docs(repo_path))
    full_text = " ".join(texts).lower()
    tokens = _tokenize(full_text)
    total_words = len(tokens)
    unique_words = len(set(tokens))

    if total_words == 0:
        features["vocabulary_richness"] = 0.0
        features["metaphor_density"] = 0.0
        features["architecture_mention_frequency"] = 0.0
        features["doc_length_total"] = 0.0
        return features

    features["vocabulary_richness"] = unique_words / total_words

    metaphor_hits = sum(1 for p in METAPHOR_PATTERNS if p in full_text)
    features["metaphor_density"] = metaphor_hits / total_words

    arch_hits = sum(1 for p in ARCHITECTURE_PATTERNS if p in full_text)
    features["architecture_mention_frequency"] = arch_hits / total_words

    features["doc_length_total"] = float(total_words)

    return features
