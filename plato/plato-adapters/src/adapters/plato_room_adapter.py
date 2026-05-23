"""PLATO room adapter — reads existing PLATO rooms, produces derived tiles.

Capabilities:
    - Reads room content and generates Q&A tiles from it
    - Cross-references tiles across rooms to find connections
    - Generates "bridge" tiles connecting domain knowledge
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..adapter import ProvenanceRecord, TileAdapter, TileSpec


class PlatoRoomAdapter(TileAdapter):
    """Extract and cross-reference tiles from PLATO rooms."""

    TAG = "plato-room"

    def __init__(self, rooms_dir: str | Path):
        self.rooms_dir = Path(rooms_dir)
        if not self.rooms_dir.is_dir():
            raise NotADirectoryError(f"PLATO rooms directory not found: {rooms_dir}")

    # -- public API ---------------------------------------------------------

    def extract(self, source: str = "") -> list[TileSpec]:
        """Extract tiles from all rooms (or a specific room file).

        *source* is optional — if empty, processes all .md files in rooms_dir.
        If provided, processes only that room file.
        """
        if source:
            files = [self.rooms_dir / source]
        else:
            files = sorted(self.rooms_dir.glob("*.md"))

        tiles: list[TileSpec] = []
        for fpath in files:
            if not fpath.exists():
                continue
            prov = self._file_provenance(fpath)
            content = fpath.read_text(encoding="utf-8")
            tiles.extend(self._extract_from_room(content, fpath.stem, prov))

        # Cross-reference: generate bridge tiles
        if len(tiles) >= 2:
            tiles.extend(self._generate_bridges(tiles))

        return tiles

    def provenance(self, source: str = "") -> ProvenanceRecord:
        if source:
            return self._file_provenance(self.rooms_dir / source)
        # Aggregate provenance for all rooms
        content = b""
        for f in sorted(self.rooms_dir.glob("*.md")):
            content += f.read_bytes()
        return ProvenanceRecord.now(
            extractor_name=self.__class__.__name__,
            source_uri=f"dir://{self.rooms_dir}",
            content=content,
        )

    def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
        valid = []
        seen_questions: set[str] = set()
        for t in tiles:
            # Deduplicate by normalized question
            q_norm = re.sub(r"\s+", " ", t.question.lower().strip())
            if q_norm in seen_questions:
                continue
            seen_questions.add(q_norm)
            if len(t.answer.strip()) <= 20:
                continue
            if t.confidence < 0.4:
                continue
            valid.append(t)
        return valid

    # -- internal -----------------------------------------------------------

    def _file_provenance(self, fpath: Path) -> ProvenanceRecord:
        content = fpath.read_bytes()
        return ProvenanceRecord.now(
            extractor_name=self.__class__.__name__,
            source_uri=f"plato-room://{fpath.stem}",
            content=content,
        )

    @staticmethod
    def _extract_from_room(content: str, room_name: str, prov: ProvenanceRecord) -> list[TileSpec]:
        """Parse a PLATO room into Q&A tiles."""
        tiles: list[TileSpec] = []

        # Pattern 1: ## Question / Answer pairs
        sections = re.split(r"(?=^#{1,4}\s+)", content, flags=re.MULTILINE)
        for sec in sections:
            heading_match = re.match(r"^#{1,4}\s+(.*)", sec, re.MULTILINE)
            if not heading_match:
                continue
            heading = heading_match.group(1).strip()
            body = re.sub(r"^#{1,4}\s+.*\n?", "", sec, count=1).strip()
            if not body or len(body) < 25:
                continue
            tiles.append(
                TileSpec(
                    domain=room_name,
                    question=heading,
                    answer=body[:600],
                    source=prov.source_uri,
                    confidence=0.8,
                    tags=[PlatoRoomAdapter.TAG, room_name],
                    provenance=prov,
                )
            )

        # Pattern 2: key-value or "- **Key**: Value" lines
        kv_pattern = re.compile(r"^[-*]\s+\*\*(.+?)\*\*:\s*(.+)$", re.MULTILINE)
        for m in kv_pattern.finditer(content):
            key, value = m.group(1).strip(), m.group(2).strip()
            if len(value) < 20:
                continue
            tiles.append(
                TileSpec(
                    domain=room_name,
                    question=f"What is {key} ({room_name})?",
                    answer=value,
                    source=prov.source_uri,
                    confidence=0.7,
                    tags=[PlatoRoomAdapter.TAG, room_name, "kv-pair"],
                    provenance=prov,
                )
            )

        return tiles

    @staticmethod
    def _generate_bridges(tiles: list[TileSpec]) -> list[TileSpec]:
        """Find connections between tiles from different rooms/domains.

        Generates "bridge" tiles that link related knowledge across domains.
        """
        bridges: list[TileSpec] = []
        # Group tiles by domain
        by_domain: dict[str, list[TileSpec]] = {}
        for t in tiles:
            by_domain.setdefault(t.domain, []).append(t)

        domains = list(by_domain.keys())
        if len(domains) < 2:
            return bridges

        # Simple keyword overlap detection between domains
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                domain_a, domain_b = domains[i], domains[j]
                tiles_a, tiles_b = by_domain[domain_a], by_domain[domain_b]

                for ta in tiles_a:
                    words_a = set(re.findall(r"\b\w{4,}\b", ta.question.lower()))
                    for tb in tiles_b:
                        words_b = set(re.findall(r"\b\w{4,}\b", tb.question.lower()))
                        overlap = words_a & words_b
                        # Need at least 2 shared meaningful words
                        if len(overlap) >= 2:
                            shared = ", ".join(sorted(overlap)[:5])
                            bridges.append(
                                TileSpec(
                                    domain="bridge",
                                    question=f"How does {domain_a} relate to {domain_b} regarding {shared}?",
                                    answer=(
                                        f"In {domain_a}: {ta.answer[:200]}\n\n"
                                        f"In {domain_b}: {tb.answer[:200]}"
                                    ),
                                    source=f"bridge:{domain_a}:{domain_b}",
                                    confidence=0.5,
                                    tags=[PlatoRoomAdapter.TAG, "bridge", domain_a, domain_b],
                                    provenance=ta.provenance,
                                )
                            )
        # Cap bridges to avoid explosion
        return bridges[:50]
