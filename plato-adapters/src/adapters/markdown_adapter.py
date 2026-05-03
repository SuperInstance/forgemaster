"""Markdown adapter — extracts Q&A pairs from structured markdown files.

Recognised patterns:
    ## Question text ...  **Answer:** text ...
    ### Q: text ...       **A:** text ...
    ## Heading            paragraph-as-answer (next block)

Any heading level 2–4 is treated as a question candidate.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..adapter import ProvenanceRecord, TileAdapter, TileSpec


class MarkdownAdapter(TileAdapter):
    """Extract Q&A tiles from markdown files."""

    TAG = "markdown"

    # -- public API ---------------------------------------------------------

    def extract(self, source: str) -> list[TileSpec]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"markdown source not found: {source}")
        content = path.read_text(encoding="utf-8")
        prov = self.provenance(source)
        tiles = self._parse_qa_pairs(content, prov)
        # Also extract heading + paragraph pairs
        tiles.extend(self._parse_headings(content, prov))
        return tiles

    def provenance(self, source: str) -> ProvenanceRecord:
        path = Path(source)
        content = path.read_bytes()
        return ProvenanceRecord.now(
            extractor_name=self.__class__.__name__,
            source_uri=f"file://{path.resolve()}",
            content=content,
        )

    def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
        """Markdown-specific: require answer > 20 chars."""
        valid = []
        for t in tiles:
            if len(t.answer.strip()) <= 20:
                continue
            if not t.question.strip():
                continue
            if t.confidence < 0.5:
                continue
            valid.append(t)
        return valid

    # -- internal parsers ---------------------------------------------------

    @staticmethod
    def _parse_qa_pairs(content: str, prov: ProvenanceRecord) -> list[TileSpec]:
        """Find ## Q / **Answer** patterns."""
        tiles: list[TileSpec] = []
        # Split into heading sections
        sections = re.split(r"(?=^#{1,4}\s+)", content, flags=re.MULTILINE)
        for sec in sections:
            heading_match = re.match(r"^#{1,4}\s+(.*)", sec, re.MULTILINE)
            if not heading_match:
                continue
            heading = heading_match.group(1).strip()
            # Look for an answer marker
            answer_match = re.search(
                r"\*{0,2}Answer[:\uff1a]\s*\*{0,2}(.*?)(?=\n#{1,4}\s|\Z)",
                sec,
                re.DOTALL | re.IGNORECASE,
            )
            if not answer_match:
                continue
            answer = answer_match.group(1).strip()
            # Clean up answer — strip leading bold markers
            answer = re.sub(r"^\*{1,2}\s*", "", answer)
            tiles.append(
                TileSpec(
                    domain="extracted",
                    question=heading,
                    answer=answer,
                    source=prov.source_uri,
                    confidence=0.8,
                    tags=[MarkdownAdapter.TAG, "qa-pair"],
                    provenance=prov,
                )
            )
        return tiles

    @staticmethod
    def _parse_headings(content: str, prov: ProvenanceRecord) -> list[TileSpec]:
        """Extract headings with their following paragraph as Q&A."""
        tiles: list[TileSpec] = []
        # Match ## Heading followed by paragraph text
        pattern = re.compile(
            r"^#{1,4}\s+(.+?)\n+(?!#{1,4}\s)(.+?)(?=\n#{1,4}\s|\n```|\n\*\*|\n-|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        for m in pattern.finditer(content):
            heading = m.group(1).strip()
            # Skip if this looks like a Q&A pair (already captured)
            if re.search(r"\bAnswer\b", heading, re.IGNORECASE):
                continue
            paragraph = m.group(2).strip()
            if len(paragraph) < 30:
                continue
            tiles.append(
                TileSpec(
                    domain="extracted",
                    question=f"What is {heading}?",
                    answer=paragraph,
                    source=prov.source_uri,
                    confidence=0.6,
                    tags=[MarkdownAdapter.TAG, "heading-paragraph"],
                    provenance=prov,
                )
            )
        return tiles
