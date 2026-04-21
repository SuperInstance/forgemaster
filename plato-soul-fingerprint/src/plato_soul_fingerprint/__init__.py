"""Plato Soul Fingerprint - extract a soul vector from a git repository."""

from .extractor import SoulExtractor
from .analysis import soul_distance, soul_cluster, soul_report, soul_compare

from .ct_quantize import (
    snap_to_pythagorean,
    snap_batch,
    quantization_error,
    find_optimal_density,
    soul_hash,
    verify_soul_integrity,
    ct_distance_report,
)

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
    "snap_to_pythagorean",
    "snap_batch",
    "quantization_error",
    "find_optimal_density",
    "soul_hash",
    "verify_soul_integrity",
    "ct_distance_report",
]
