"""Web adapter — fetches URLs and extracts structured Q&A tiles.

Strategies:
    - Heading + paragraph extraction (like markdown adapter)
    - FAQ-style Q&A detection
    - Definition extraction (term: description)
"""

from __future__ import annotations

import hashlib
import re

import httpx

from ..adapter import ProvenanceRecord, TileAdapter, TileSpec


class WebAdapter(TileAdapter):
    """Fetch a URL, extract Q&A tiles from the content."""

    TAG = "web"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: httpx.Client | None = None

    # -- public API ---------------------------------------------------------

    def extract(self, source: str) -> list[TileSpec]:
        """Fetch *source* URL and extract tiles."""
        html = self._fetch(source)
        text = self._html_to_text(html)
        prov = self.provenance(source)
        domain = self._extract_domain(source)
        tiles: list[TileSpec] = []

        # Strategy 1: heading + paragraph
        tiles.extend(self._extract_heading_paragraphs(text, domain, prov))
        # Strategy 2: FAQ-style Q&A
        tiles.extend(self._extract_faq(text, domain, prov))
        # Strategy 3: definition lists
        tiles.extend(self._extract_definitions(text, domain, prov))

        return tiles

    def provenance(self, source: str) -> ProvenanceRecord:
        content = self._fetch(source)
        return ProvenanceRecord.now(
            extractor_name=self.__class__.__name__,
            source_uri=source,
            content=content,
        )

    def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
        valid = []
        for t in tiles:
            if len(t.answer.strip()) <= 20:
                continue
            if not t.question.strip():
                continue
            if t.confidence < 0.4:
                continue
            valid.append(t)
        return valid

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # -- internal -----------------------------------------------------------

    def _fetch(self, url: str) -> str:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Crude HTML → text conversion. Good enough for extraction."""
        # Remove scripts and styles
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Preserve heading level markers FIRST
        text = re.sub(r"<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", text, flags=re.IGNORECASE)
        # Convert block elements to newlines (no more h tags to match)
        text = re.sub(r"<(p|div|li|br|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(h[1-6]|p|div|li|tr)>", "\n", text, flags=re.IGNORECASE)
        # Bold → **text**
        text = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.DOTALL | re.IGNORECASE)
        # Links → text
        text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL | re.IGNORECASE)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", "", text)
        # Decode entities
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        # Collapse whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _extract_domain(url: str) -> str:
        m = re.match(r"https?://([^/]+)", url)
        return m.group(1).replace("www.", "") if m else "unknown"

    @staticmethod
    def _extract_heading_paragraphs(text: str, domain: str, prov: ProvenanceRecord) -> list[TileSpec]:
        tiles: list[TileSpec] = []
        sections = re.split(r"(?=^#{1,6}\s+)", text, flags=re.MULTILINE)
        for sec in sections:
            heading_match = re.match(r"^#{1,6}\s+(.+)", sec, re.MULTILINE)
            if not heading_match:
                continue
            heading = heading_match.group(1).strip()
            body = re.sub(r"^#{1,6}\s+.*\n?", "", sec, count=1).strip()
            if len(body) < 30:
                continue
            tiles.append(
                TileSpec(
                    domain=domain,
                    question=f"What is {heading}?",
                    answer=body[:500],
                    source=prov.source_uri,
                    confidence=0.6,
                    tags=[WebAdapter.TAG, domain, "heading-paragraph"],
                    provenance=prov,
                )
            )
        return tiles

    @staticmethod
    def _extract_faq(text: str, domain: str, prov: ProvenanceRecord) -> list[TileSpec]:
        """Detect FAQ-style Q&A: 'Q: ...' / 'A: ...' patterns."""
        tiles: list[TileSpec] = []
        qa_pattern = re.compile(
            r"(?:Q[:\uff1a]\s*(.+?))\s*(?:A[:\uff1a]\s*(.+?))(?=\s*(?:Q[:\uff1a])|\Z)",
            re.DOTALL,
        )
        for m in qa_pattern.finditer(text):
            q = m.group(1).strip()
            a = m.group(2).strip()
            if len(a) < 20:
                continue
            tiles.append(
                TileSpec(
                    domain=domain,
                    question=q,
                    answer=a,
                    source=prov.source_uri,
                    confidence=0.85,
                    tags=[WebAdapter.TAG, domain, "faq"],
                    provenance=prov,
                )
            )
        return tiles

    @staticmethod
    def _extract_definitions(text: str, domain: str, prov: ProvenanceRecord) -> list[TileSpec]:
        """Extract definition-style content: 'Term — Definition' or '**Term**: Definition'."""
        tiles: list[TileSpec] = []
        def_pattern = re.compile(r"\*\*(.+?)\*\*[—\-:]\s*(.+?)(?:\n|$)", re.MULTILINE)
        for m in def_pattern.finditer(text):
            term = m.group(1).strip()
            definition = m.group(2).strip()
            if len(definition) < 20:
                continue
            tiles.append(
                TileSpec(
                    domain=domain,
                    question=f"What is {term}?",
                    answer=definition,
                    source=prov.source_uri,
                    confidence=0.7,
                    tags=[WebAdapter.TAG, domain, "definition", term.lower().replace(" ", "-")],
                    provenance=prov,
                )
            )
        return tiles
