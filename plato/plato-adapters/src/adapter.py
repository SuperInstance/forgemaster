"""TileAdapter protocol — PLATO connector system with quality gates.

Inspired by LlamaIndex data connectors, but with PLATO's quality gate baked in.
Every adapter extracts knowledge as TileSpecs, tracks provenance, and validates
before submission.
"""

from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

import httpx

logger = logging.getLogger(__name__)

PLATO_SUBMIT_URL = "http://147.224.38.131:8847/submit"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProvenanceRecord:
    """Tracks where a tile came from and how it was extracted."""

    extractor_name: str
    source_uri: str
    timestamp: str  # ISO-8601
    checksum: str  # SHA-256 of source content used for extraction

    @classmethod
    def now(cls, extractor_name: str, source_uri: str, content: bytes | str) -> ProvenanceRecord:
        """Create a provenance record with current UTC time and auto-computed checksum."""
        if isinstance(content, str):
            content = content.encode()
        return cls(
            extractor_name=extractor_name,
            source_uri=source_uri,
            timestamp=datetime.now(timezone.utc).isoformat(),
            checksum=hashlib.sha256(content).hexdigest(),
        )


@dataclass
class TileSpec:
    """A single knowledge tile ready for PLATO ingestion."""

    domain: str
    question: str
    answer: str
    source: str
    confidence: float  # 0.0–1.0
    tags: list[str] = field(default_factory=list)
    provenance: ProvenanceRecord | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "domain": self.domain,
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "confidence": self.confidence,
            "tags": list(self.tags),
        }
        if self.provenance is not None:
            d["provenance"] = {
                "extractor_name": self.provenance.extractor_name,
                "source_uri": self.provenance.source_uri,
                "timestamp": self.provenance.timestamp,
                "checksum": self.provenance.checksum,
            }
        return d


# ---------------------------------------------------------------------------
# Abstract base — every adapter implements these three methods
# ---------------------------------------------------------------------------


class TileAdapter(ABC):
    """Base class for PLATO knowledge extractors.

    Subclass and implement:
        - extract(source) → list[TileSpec]
        - provenance(source) → ProvenanceRecord
        - validate(tiles) → list[TileSpec]        # quality gate (local)
    """

    @abstractmethod
    def extract(self, source: str) -> list[TileSpec]:
        """Read *source* and return raw tiles (before local validation)."""

    @abstractmethod
    def provenance(self, source: str) -> ProvenanceRecord:
        """Build a provenance record for *source*."""

    def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
        """Default validation: keep tiles with confidence ≥ 0.5 and non-empty Q&A.

        Override in subclasses for domain-specific checks.
        """
        valid: list[TileSpec] = []
        for t in tiles:
            if not t.question.strip() or not t.answer.strip():
                logger.debug("rejecting tile: empty Q or A — %s", t.question[:60])
                continue
            if t.confidence < 0.5:
                logger.debug("rejecting tile: low confidence %.2f — %s", t.confidence, t.question[:60])
                continue
            valid.append(t)
        return valid


# ---------------------------------------------------------------------------
# PLATO submitter — runs tiles through the remote quality gate
# ---------------------------------------------------------------------------


class PLATOSubmitter:
    """Submits validated tiles to the PLATO quality gate.

    Usage::

        submitter = PLATOSubmitter()
        accepted, rejected, reasons = submitter.submit(tiles)
    """

    def __init__(self, url: str = PLATO_SUBMIT_URL, timeout: float = 30.0):
        self.url = url
        self.timeout = timeout

    def submit(
        self,
        tiles: Sequence[TileSpec],
        dry_run: bool = False,
    ) -> tuple[list[TileSpec], list[TileSpec], dict[str, str]]:
        """POST each tile to PLATO. Returns (accepted, rejected, reasons).

        If *dry_run* is True, validates locally without hitting the network.
        """
        accepted: list[TileSpec] = []
        rejected: list[TileSpec] = []
        reasons: dict[str, str] = {}  # tile.question → reason

        if dry_run:
            for tile in tiles:
                reason = self._local_check(tile)
                if reason:
                    rejected.append(tile)
                    reasons[tile.question] = reason
                else:
                    accepted.append(tile)
            return accepted, rejected, reasons

        with httpx.Client(timeout=self.timeout) as client:
            for tile in tiles:
                try:
                    resp = client.post(self.url, json=tile.to_dict())
                    if resp.status_code < 300:
                        body = resp.json()
                        status = body.get("status", "accepted")
                        if status == "accepted":
                            accepted.append(tile)
                        else:
                            rejected.append(tile)
                            reasons[tile.question] = body.get("reason", f"HTTP {resp.status_code}")
                    else:
                        rejected.append(tile)
                        reasons[tile.question] = f"HTTP {resp.status_code}: {resp.text[:200]}"
                except httpx.RequestError as exc:
                    rejected.append(tile)
                    reasons[tile.question] = f"request error: {exc}"

        logger.info(
            "PLATO gate: %d accepted, %d rejected out of %d",
            len(accepted),
            len(rejected),
            len(tiles),
        )
        return accepted, rejected, reasons

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _local_check(tile: TileSpec) -> str | None:
        """Lightweight local checks that mirror the remote gate."""
        if not tile.domain:
            return "missing domain"
        if len(tile.question) < 5:
            return "question too short"
        if len(tile.answer) < 10:
            return "answer too short"
        if tile.confidence < 0.3:
            return f"confidence too low ({tile.confidence:.2f})"
        return None
