"""Unit tests for the TileAdapter protocol."""

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.adapter import PLATOSubmitter, ProvenanceRecord, TileAdapter, TileSpec


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def make_tile(
    question: str = "What is PLATO?",
    answer: str = "PLATO is a knowledge management system with quality gates.",
    domain: str = "test",
    confidence: float = 0.8,
    **overrides,
) -> TileSpec:
    kwargs = dict(
        domain=domain,
        question=question,
        answer=answer,
        source="test://mock",
        confidence=confidence,
        tags=["test"],
    )
    kwargs.update(overrides)
    return TileSpec(**kwargs)


# ---------------------------------------------------------------------------
# TileSpec tests
# ---------------------------------------------------------------------------


class TestTileSpec:
    def test_to_dict_basic(self):
        tile = make_tile()
        d = tile.to_dict()
        assert d["domain"] == "test"
        assert d["question"] == "What is PLATO?"
        assert d["confidence"] == 0.8
        assert "provenance" not in d  # omitted when None

    def test_to_dict_with_provenance(self):
        prov = ProvenanceRecord(
            extractor_name="TestAdapter",
            source_uri="file:///test.md",
            timestamp="2025-01-01T00:00:00+00:00",
            checksum="abc123",
        )
        tile = make_tile(provenance=prov)
        d = tile.to_dict()
        assert d["provenance"]["extractor_name"] == "TestAdapter"
        assert d["provenance"]["checksum"] == "abc123"

    def test_tile_spec_frozen_provenance(self):
        prov = ProvenanceRecord("a", "b", "c", "d")
        assert prov.extractor_name == "a"


# ---------------------------------------------------------------------------
# ProvenanceRecord tests
# ---------------------------------------------------------------------------


class TestProvenanceRecord:
    def test_now_creates_valid_record(self):
        prov = ProvenanceRecord.now("TestExtractor", "file:///test.md", b"hello")
        assert prov.extractor_name == "TestExtractor"
        assert prov.source_uri == "file:///test.md"
        assert "T" in prov.timestamp  # ISO format
        assert len(prov.checksum) == 64  # SHA-256 hex

    def test_now_string_content(self):
        prov = ProvenanceRecord.now("X", "y", "string content")
        assert len(prov.checksum) == 64

    def test_deterministic_checksum(self):
        prov1 = ProvenanceRecord.now("X", "y", b"data")
        prov2 = ProvenanceRecord.now("X", "y", b"data")
        assert prov1.checksum == prov2.checksum


# ---------------------------------------------------------------------------
# TileAdapter base class tests
# ---------------------------------------------------------------------------


class TestTileAdapterBase:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            TileAdapter()

    def test_default_validate_keeps_good_tiles(self):
        class Dummy(TileAdapter):
            def extract(self, source):
                return []
            def provenance(self, source):
                return ProvenanceRecord("x", "y", "z", "w")

        adapter = Dummy()
        tiles = [
            make_tile(confidence=0.9),
            make_tile(confidence=0.3),  # too low
            make_tile(question="", confidence=0.9),  # empty Q
            make_tile(answer="  ", confidence=0.9),  # empty A
        ]
        valid = adapter.validate(tiles)
        assert len(valid) == 1
        assert valid[0].confidence == 0.9


# ---------------------------------------------------------------------------
# PLATOSubmitter tests
# ---------------------------------------------------------------------------


class TestPLATOSubmitter:
    def test_dry_run_accepts_good_tiles(self):
        submitter = PLATOSubmitter()
        tiles = [make_tile()]
        accepted, rejected, reasons = submitter.submit(tiles, dry_run=True)
        assert len(accepted) == 1
        assert len(rejected) == 0

    def test_dry_run_rejects_bad_tiles(self):
        submitter = PLATOSubmitter()
        tiles = [
            make_tile(question="Hi", answer="x" * 30),  # too short Q
            make_tile(answer="short", question="Unique question one?"),  # too short A
            make_tile(confidence=0.1, question="Unique question two?", answer="x" * 30),  # too low confidence
            make_tile(domain="", question="Unique question three?", answer="x" * 30),  # missing domain
        ]
        accepted, rejected, reasons = submitter.submit(tiles, dry_run=True)
        assert len(accepted) == 0
        assert len(rejected) == 4
        assert len(reasons) == 4

    @patch("src.adapter.httpx.Client")
    def test_submit_accepted(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "accepted"}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        submitter = PLATOSubmitter()
        tiles = [make_tile()]
        accepted, rejected, reasons = submitter.submit(tiles)
        assert len(accepted) == 1
        assert len(rejected) == 0

    @patch("src.adapter.httpx.Client")
    def test_submit_rejected_by_gate(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "rejected",
            "reason": "duplicate",
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        submitter = PLATOSubmitter()
        tiles = [make_tile()]
        accepted, rejected, reasons = submitter.submit(tiles)
        assert len(accepted) == 0
        assert len(rejected) == 1
        assert "duplicate" in reasons[tiles[0].question]

    @patch("src.adapter.httpx.Client")
    def test_submit_network_error(self, mock_client_cls):
        import httpx
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_client_cls.return_value = mock_client

        submitter = PLATOSubmitter()
        tiles = [make_tile()]
        accepted, rejected, reasons = submitter.submit(tiles)
        assert len(accepted) == 0
        assert len(rejected) == 1
        assert "connection refused" in reasons[tiles[0].question]


# ---------------------------------------------------------------------------
# MarkdownAdapter tests
# ---------------------------------------------------------------------------


class TestMarkdownAdapter:
    def test_extract_qa_pairs(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(textwrap.dedent("""\
            ## What is PLATO?
            
            **Answer:** PLATO is a knowledge management system that uses quality gates to ensure tile integrity.
            
            ## How does drift work?
            
            **Answer:** Drift is the gradual deviation from constraint satisfaction over time. It must be measured precisely.
        """))
        from src.adapters.markdown_adapter import MarkdownAdapter
        adapter = MarkdownAdapter()
        tiles = adapter.extract(str(md))
        qa_tiles = [t for t in tiles if "qa-pair" in t.tags]
        assert len(qa_tiles) >= 2

    def test_validate_rejects_short_answers(self, tmp_path):
        md = tmp_path / "short.md"
        md.write_text(textwrap.dedent("""\
            ## Short answer
            
            **Answer:** Too short
        """))
        from src.adapters.markdown_adapter import MarkdownAdapter
        adapter = MarkdownAdapter()
        tiles = adapter.extract(str(md))
        valid = adapter.validate(tiles)
        # All should be rejected due to short answer
        for t in valid:
            assert len(t.answer) > 20

    def test_file_not_found(self):
        from src.adapters.markdown_adapter import MarkdownAdapter
        adapter = MarkdownAdapter()
        with pytest.raises(FileNotFoundError):
            adapter.extract("/nonexistent/file.md")


# ---------------------------------------------------------------------------
# GitHubAdapter tests
# ---------------------------------------------------------------------------


class TestGitHubAdapter:
    def test_extract_readme_tiles(self, tmp_path):
        # Create a fake git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

        readme = tmp_path / "README.md"
        readme.write_text(textwrap.dedent("""\
            # My Project
            
            ## Overview
            This is a very cool project that does many things and has lots of features.
            
            ## Installation
            Run pip install myproject and then configure the settings file properly.
        """))
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

        from src.adapters.github_adapter import GitHubAdapter
        adapter = GitHubAdapter()
        tiles = adapter.extract(str(tmp_path))
        assert len(tiles) >= 2
        readme_tiles = [t for t in tiles if "readme" in t.tags]
        assert len(readme_tiles) >= 2

    def test_constraint_extraction(self, tmp_path):
        import subprocess
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True)

        code = tmp_path / "main.py"
        code.write_text('# MUST: Always validate input before processing\n# NEVER: Trust user data without sanitization\n')
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

        from src.adapters.github_adapter import GitHubAdapter
        adapter = GitHubAdapter()
        tiles = adapter.extract(str(tmp_path))
        constraint_tiles = [t for t in tiles if "constraint" in t.tags]
        assert len(constraint_tiles) >= 1


# ---------------------------------------------------------------------------
# PlatoRoomAdapter tests
# ---------------------------------------------------------------------------


class TestPlatoRoomAdapter:
    def test_extract_from_rooms(self, tmp_path):
        room1 = tmp_path / "physics.md"
        room1.write_text(textwrap.dedent("""\
            ## What is gravity?
            
            Gravity is a fundamental force of nature that attracts objects with mass towards each other.
            
            ## Speed of light
            
            The speed of light in vacuum is approximately 299792458 meters per second and is constant.
        """))

        from src.adapters.plato_room_adapter import PlatoRoomAdapter
        adapter = PlatoRoomAdapter(rooms_dir=str(tmp_path))
        tiles = adapter.extract()
        assert len(tiles) >= 2

    def test_bridge_generation(self, tmp_path):
        room_a = tmp_path / "alpha.md"
        room_a.write_text("## Constraint drift analysis\n\nDrift analysis measures constraint violation over time and space dimensions thoroughly.\n")
        room_b = tmp_path / "beta.md"
        room_b.write_text("## Drift constraint metrics\n\nConstraint metrics track drift across multiple dimensions of the problem space.\n")

        from src.adapters.plato_room_adapter import PlatoRoomAdapter
        adapter = PlatoRoomAdapter(rooms_dir=str(tmp_path))
        tiles = adapter.extract()
        bridge_tiles = [t for t in tiles if t.domain == "bridge"]
        assert len(bridge_tiles) >= 1

    def test_deduplication_in_validate(self, tmp_path):
        room = tmp_path / "test.md"
        room.write_text("## Same question\n\nThis is a sufficiently long answer that will pass validation checks.\n")

        from src.adapters.plato_room_adapter import PlatoRoomAdapter
        adapter = PlatoRoomAdapter(rooms_dir=str(tmp_path))
        tiles = adapter.extract()
        valid = adapter.validate(tiles)
        # Should not have duplicates
        questions = [t.question for t in valid]
        assert len(questions) == len(set(questions))


# ---------------------------------------------------------------------------
# WebAdapter tests (with mocked HTTP)
# ---------------------------------------------------------------------------


class TestWebAdapter:
    def test_extract_heading_paragraphs(self):
        html = textwrap.dedent("""\
            <html><body>
            <h1>Test Page</h1>
            <h2>Python Decorators</h2>
            <p>Decorators are a powerful feature in Python that allow you to modify function behavior without changing the function itself. They wrap existing functions.</p>
            <h2>Type Hints</h2>
            <p>Type hints allow you to annotate function signatures with expected types for better IDE support and static analysis.</p>
            </body></html>
        """)

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with patch("src.adapters.web_adapter.httpx.Client", return_value=mock_client):
            from src.adapters.web_adapter import WebAdapter
            adapter = WebAdapter()
            tiles = adapter.extract("https://example.com/docs")
            assert len(tiles) >= 2

    @patch("src.adapters.web_adapter.httpx.Client")
    def test_extract_faq(self, mock_client_cls):
        html = """<html><body>
        Q: What is Python?
        A: Python is a high-level programming language known for its readability and versatility.
        
        Q: What is Rust?
        A: Rust is a systems programming language focused on safety and performance.
        </body></html>"""

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.adapters.web_adapter import WebAdapter
        adapter = WebAdapter()
        tiles = adapter.extract("https://example.com/faq")
        faq_tiles = [t for t in tiles if "faq" in t.tags]
        assert len(faq_tiles) >= 2
