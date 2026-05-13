"""Galois-aware PLATO tile retrieval engine — FCA-based retrieval with Heyting ranking."""

from .engine import (
    FormalContext,
    GaloisRetrievalEngine,
    RetrievalResult,
    generate_synthetic_tiles,
    heyting_rank,
    weighted_sum_rank,
    load_rooms_from_server,
    _score_entropy,
    main_cli,
)

__all__ = [
    "FormalContext",
    "GaloisRetrievalEngine",
    "RetrievalResult",
    "generate_synthetic_tiles",
    "heyting_rank",
    "weighted_sum_rank",
    "load_rooms_from_server",
]
