"""Core types for the CoCapn PLATO client."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


class PLATOError(Exception):
    """Base exception for all PLATO client errors."""

    def __init__(self, message: str, *, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __repr__(self) -> str:
        parts = [f"{self.__class__.__name__}({self.message!r}"]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.response_body is not None:
            parts.append(f"response_body={self.response_body!r}")
        return ", ".join(parts) + ")"


@dataclass(frozen=True, slots=True)
class Tile:
    """An immutable knowledge tile as stored in PLATO."""

    domain: str
    question: str
    answer: str
    source: str
    confidence: float
    tags: list[str] = field(default_factory=list)
    provenance: str = ""
    _hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", float(self.confidence))
        if not self._hash:
            object.__setattr__(self, "_hash", self._compute_hash())

    def _compute_hash(self) -> str:
        """Deterministic SHA-256 hash of the tile's canonical content."""
        payload = {
            "domain": self.domain,
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "confidence": round(self.confidence, 6),
            "tags": sorted(self.tags),
            "provenance": self.provenance,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tile to a plain dictionary."""
        return {
            "domain": self.domain,
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "provenance": self.provenance,
            "_hash": self._hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tile:
        """Deserialize a tile from a plain dictionary."""
        return cls(
            domain=data["domain"],
            question=data["question"],
            answer=data["answer"],
            source=data["source"],
            confidence=data["confidence"],
            tags=list(data.get("tags", [])),
            provenance=data.get("provenance", ""),
            _hash=data.get("_hash", ""),
        )
