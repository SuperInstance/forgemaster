"""Plato Soul Fingerprint - extract a soul vector from a git repository."""

from .extractor import SoulExtractor
from .analysis import soul_distance, soul_cluster, soul_report, soul_compare

__all__ = [
    "SoulExtractor",
    "soul_distance",
    "soul_cluster",
    "soul_report",
    "soul_compare",
    "feature_importance",
    "dendrogram_text",
    "batch_extract",
    "soul_signature",
]
