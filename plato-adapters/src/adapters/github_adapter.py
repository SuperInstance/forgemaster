"""GitHub adapter — extracts knowledge tiles from GitHub repos.

Supports:
    - README sections as Q&A tiles
    - Code comments as constraint-knowledge tiles
    - Git metadata for provenance (commit hash, author, date)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from ..adapter import ProvenanceRecord, TileAdapter, TileSpec


class GitHubAdapter(TileAdapter):
    """Extract Q&A tiles from GitHub repositories (local clone or URL)."""

    TAG = "github"

    # Code-comment patterns that look like constraint knowledge
    CONSTRAINT_PATTERNS = [
        re.compile(r"//\s*(MUST|SHALL|MUST NOT|SHOULD|NEVER|ALWAYS|REQUIRED|IMPORTANT):?\s*(.*)", re.IGNORECASE),
        re.compile(r"#\s*(MUST|SHALL|MUST NOT|SHOULD|NEVER|ALWAYS|REQUIRED|IMPORTANT):?\s*(.*)", re.IGNORECASE),
        re.compile(r'/\*\s*(MUST|SHALL|MUST NOT|SHOULD|NEVER|ALWAYS|REQUIRED|IMPORTANT):?\s*(.*?)\*/', re.IGNORECASE | re.DOTALL),
    ]

    # -- public API ---------------------------------------------------------

    def extract(self, source: str) -> list[TileSpec]:
        """Extract tiles from a GitHub URL or local repo path.

        *source* can be:
            - A GitHub HTTPS URL (will clone to temp dir)
            - A local path to an already-cloned repo
        """
        repo_path = self._resolve_source(source)
        prov = self.provenance(source)
        tiles: list[TileSpec] = []

        # Extract README tiles
        readme_tiles = self._extract_readme(repo_path, prov)
        tiles.extend(readme_tiles)

        # Extract constraint-knowledge from code comments
        code_tiles = self._extract_code_constraints(repo_path, prov)
        tiles.extend(code_tiles)

        return tiles

    def provenance(self, source: str) -> ProvenanceRecord:
        repo_path = self._resolve_source(source)
        git_info = self._git_info(repo_path)
        content = json.dumps(git_info, sort_keys=True).encode()
        return ProvenanceRecord(
            extractor_name=self.__class__.__name__,
            source_uri=source,
            timestamp=git_info.get("date", ""),
            checksum=hashlib.sha256(content).hexdigest(),
        )

    def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
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

    # -- source resolution --------------------------------------------------

    @staticmethod
    def _resolve_source(source: str) -> Path:
        """Return a local path to the repo, cloning if necessary."""
        if source.startswith("https://github.com/") or source.startswith("git@github.com:"):
            # Clone to temp dir
            tmp = Path(f"/tmp/plato-gh-{hashlib.md5(source.encode()).hexdigest()}")
            if not tmp.exists():
                subprocess.run(
                    ["git", "clone", "--depth", "1", source, str(tmp)],
                    check=True,
                    capture_output=True,
                )
            return tmp
        path = Path(source)
        if not path.is_dir():
            raise FileNotFoundError(f"repo path does not exist: {source}")
        return path

    # -- git metadata -------------------------------------------------------

    @staticmethod
    def _git_info(repo_path: Path) -> dict[str, str]:
        """Extract git metadata for provenance."""
        info: dict[str, str] = {}
        try:
            info["commit"] = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=str(repo_path), stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            info["commit"] = "unknown"
        try:
            info["author"] = subprocess.check_output(
                ["git", "log", "-1", "--format=%an"], cwd=str(repo_path), stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            info["author"] = "unknown"
        try:
            info["date"] = subprocess.check_output(
                ["git", "log", "-1", "--format=%aI"], cwd=str(repo_path), stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            info["date"] = ""
        try:
            info["remote"] = subprocess.check_output(
                ["git", "remote", "get-url", "origin"], cwd=str(repo_path), stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            info["remote"] = str(repo_path)
        return info

    # -- README extraction --------------------------------------------------

    def _extract_readme(self, repo_path: Path, prov: ProvenanceRecord) -> list[TileSpec]:
        """Find README and extract heading+paragraph Q&A tiles."""
        readme = self._find_readme(repo_path)
        if readme is None:
            return []
        content = readme.read_text(encoding="utf-8", errors="replace")
        repo_name = repo_path.name
        tiles: list[TileSpec] = []

        # Split into heading sections
        sections = re.split(r"(?=^#{1,4}\s+)", content, flags=re.MULTILINE)
        for sec in sections:
            heading_match = re.match(r"^#{1,4}\s+(.+)", sec, re.MULTILINE)
            if not heading_match:
                continue
            heading = heading_match.group(1).strip()
            # Get body (everything after heading line)
            body = re.sub(r"^#{1,4}\s+.*\n", "", sec, count=1).strip()
            # Skip very short bodies
            if len(body) < 30:
                continue
            tiles.append(
                TileSpec(
                    domain=repo_name,
                    question=f"What does {repo_name} say about {heading}?",
                    answer=body[:500],  # Cap answer length
                    source=prov.source_uri,
                    confidence=0.75,
                    tags=[self.TAG, "readme", repo_name, heading.lower().replace(" ", "-")],
                    provenance=prov,
                )
            )
        return tiles

    @staticmethod
    def _find_readme(repo_path: Path) -> Path | None:
        for name in ("README.md", "README.rst", "README.txt", "README", "readme.md"):
            p = repo_path / name
            if p.exists():
                return p
        return None

    # -- code constraint extraction -----------------------------------------

    def _extract_code_constraints(self, repo_path: Path, prov: ProvenanceRecord) -> list[TileSpec]:
        """Scan source files for constraint-style comments."""
        tiles: list[TileSpec] = []
        code_extensions = {".py", ".rs", ".ts", ".js", ".go", ".java", ".c", ".cpp", ".h", ".rb"}

        for root, _dirs, files in os.walk(repo_path):
            # Skip hidden and common noise directories
            root_path = Path(root)
            if any(part.startswith(".") for part in root_path.parts):
                continue
            if any(part in {"node_modules", "target", "vendor", "__pycache__", "dist", "build"} for part in root_path.parts):
                continue

            for fname in files:
                fpath = root_path / fname
                if fpath.suffix not in code_extensions:
                    continue
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                rel_path = fpath.relative_to(repo_path)
                tiles.extend(self._scan_constraints(text, str(rel_path), prov))

        return tiles

    def _scan_constraints(self, text: str, file_path: str, prov: ProvenanceRecord) -> list[TileSpec]:
        tiles: list[TileSpec] = []
        for pattern in self.CONSTRAINT_PATTERNS:
            for m in pattern.finditer(text):
                keyword = m.group(1).upper()
                body = m.group(2).strip()
                if len(body) < 10:
                    continue
                tiles.append(
                    TileSpec(
                        domain="constraint",
                        question=f"What constraint exists in {file_path}?",
                        answer=f"{keyword}: {body}",
                        source=prov.source_uri,
                        confidence=0.85,
                        tags=[self.TAG, "constraint", keyword.lower(), file_path],
                        provenance=prov,
                    )
                )
        return tiles
