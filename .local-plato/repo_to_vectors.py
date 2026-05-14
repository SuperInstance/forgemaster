"""
Repo to Vector Space — spring-load any repo into a searchable dart.

Takes a git repo, extracts every meaningful unit (files, functions,
commits, issues, PRs), embeds each one, and saves the result as a
single .fvt (FLUX Vector Twin) file.

Query time: 0.1ms across the entire repo's knowledge.

Usage:
    from repo_to_vectors import repo_to_vectors
    repo_to_vectors("SuperInstance/plato-training", token="gho_...")
    # → .fvt file ready for instant search
"""

from __future__ import annotations
import json, os, re, subprocess, time, math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

# Re-use the embedding infrastructure
import sys
sys.path.insert(0, str(Path.home() / ".openclaw" / "workspace" / ".local-plato"))
from flux_vector_twin import FluxVectorTwin, text_to_embedding, VectorEntry


# ─── Extraction: what counts as a "tile" in a repo ────────────────

@dataclass
class RepoTile:
    """A single unit of meaning extracted from a repo."""
    tile_type: str       # "function", "class", "file", "commit", "issue", "pr", "readme"
    path: str            # file path or "commit:{sha}" or "issue:{num}"
    name: str            # function/class name, or commit message title
    content: str         # the actual content (code, message, description)
    language: str = ""   # file extension
    line_start: int = 0
    line_end: int = 0
    metadata: Dict = field(default_factory=dict)


def extract_file_tiles(filepath: str, content: str) -> List[RepoTile]:
    """Extract functions/classes from a source file."""
    tiles = []
    ext = Path(filepath).suffix
    lines = content.split("\n")
    
    # Language-specific extraction
    if ext in (".py",):
        tiles.extend(_extract_python(filepath, content, lines))
    elif ext in (".rs",):
        tiles.extend(_extract_rust(filepath, content, lines))
    elif ext in (".c", ".h",):
        tiles.extend(_extract_c(filepath, content, lines))
    elif ext in (".ts", ".js",):
        tiles.extend(_extract_js(filepath, content, lines))
    else:
        # Generic: whole file as one tile
        tiles.append(RepoTile(
            tile_type="file", path=filepath, name=Path(filepath).name,
            content=content[:2000], language=ext,
        ))
    
    return tiles


def _extract_python(filepath, content, lines) -> List[RepoTile]:
    """Extract Python functions and classes."""
    tiles = []
    
    # Classes and functions via regex
    pattern = re.compile(r'^(class |def |async def )(\w+)', re.MULTILINE)
    for match in pattern.finditer(content):
        name = match.group(2)
        start_line = content[:match.start()].count("\n")
        
        # Get the body (until next def/class at same or lower indent)
        indent = len(match.group(0)) - len(match.group(0).lstrip())
        end_line = start_line + 1
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                continue
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= indent and (line.strip().startswith("def ") or 
                                          line.strip().startswith("class ") or
                                          line.strip().startswith("async def ")):
                break
            end_line = i + 1
        
        body = "\n".join(lines[start_line:end_line])
        tile_type = "class" if match.group(1) == "class " else "function"
        
        tiles.append(RepoTile(
            tile_type=tile_type, path=filepath, name=name,
            content=body[:2000], language=".py",
            line_start=start_line + 1, line_end=end_line,
        ))
    
    # If nothing extracted, use whole file
    if not tiles:
        tiles.append(RepoTile(
            tile_type="file", path=filepath, name=Path(filepath).name,
            content=content[:2000], language=".py",
        ))
    
    return tiles


def _extract_rust(filepath, content, lines) -> List[RepoTile]:
    """Extract Rust functions, structs, impls."""
    tiles = []
    pattern = re.compile(r'^(pub )?(async )?fn (\w+)|(pub )?struct (\w+)|(pub )?enum (\w+)', re.MULTILINE)
    
    for match in pattern.finditer(content):
        name = match.group(3) or match.group(5) or match.group(7)
        if not name:
            continue
        start_line = content[:match.start()].count("\n")
        
        # Get body (simplified: next 50 lines or until next top-level item)
        end_line = min(start_line + 50, len(lines))
        body = "\n".join(lines[start_line:end_line])
        
        tile_type = "function" if match.group(3) else "struct"
        tiles.append(RepoTile(
            tile_type=tile_type, path=filepath, name=name,
            content=body[:2000], language=".rs",
            line_start=start_line + 1, line_end=end_line,
        ))
    
    if not tiles:
        tiles.append(RepoTile(
            tile_type="file", path=filepath, name=Path(filepath).name,
            content=content[:2000], language=".rs",
        ))
    
    return tiles


def _extract_c(filepath, content, lines) -> List[RepoTile]:
    """Extract C functions."""
    tiles = []
    # Match function definitions (simplified)
    pattern = re.compile(r'^\w[\w\s\*]+ (\w+)\s*\(', re.MULTILINE)
    
    for match in pattern.finditer(content):
        name = match.group(1)
        if name in ("if", "while", "for", "switch", "return"):
            continue
        start_line = content[:match.start()].count("\n")
        end_line = min(start_line + 30, len(lines))
        body = "\n".join(lines[start_line:end_line])
        
        tiles.append(RepoTile(
            tile_type="function", path=filepath, name=name,
            content=body[:2000], language=".c",
            line_start=start_line + 1, line_end=end_line,
        ))
    
    if not tiles:
        tiles.append(RepoTile(
            tile_type="file", path=filepath, name=Path(filepath).name,
            content=content[:2000], language=".c",
        ))
    
    return tiles


def _extract_js(filepath, content, lines) -> List[RepoTile]:
    """Extract JS/TS functions and classes."""
    tiles = []
    pattern = re.compile(r'(function |const \w+ = |class (\w+)|export (default )?function (\w+))', re.MULTILINE)
    
    for match in pattern.finditer(content):
        name_match = re.search(r'(?:function |class |const )(\w+)', match.group(0))
        if not name_match:
            continue
        name = name_match.group(1)
        start_line = content[:match.start()].count("\n")
        end_line = min(start_line + 30, len(lines))
        body = "\n".join(lines[start_line:end_line])
        
        tiles.append(RepoTile(
            tile_type="function", path=filepath, name=name,
            content=body[:2000], language=Path(filepath).suffix,
            line_start=start_line + 1, line_end=end_line,
        ))
    
    if not tiles:
        tiles.append(RepoTile(
            tile_type="file", path=filepath, name=Path(filepath).name,
            content=content[:2000], language=Path(filepath).suffix,
        ))
    
    return tiles


def extract_commits(repo_path: str, max_commits: int = 200) -> List[RepoTile]:
    """Extract commit messages as tiles."""
    tiles = []
    try:
        result = subprocess.run(
            ["git", "log", f"-{max_commits}", "--format=%H|%s|%an|%at"],
            capture_output=True, text=True, cwd=repo_path, timeout=30,
        )
        for line in result.stdout.strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            sha, msg, author, ts = parts
            tiles.append(RepoTile(
                tile_type="commit", path=f"commit:{sha[:12]}",
                name=msg[:100], content=msg, metadata={"author": author, "ts": float(ts)},
            ))
    except:
        pass
    return tiles


def extract_readme(repo_path: str) -> Optional[RepoTile]:
    """Extract README as a tile."""
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        path = os.path.join(repo_path, name)
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            return RepoTile(
                tile_type="readme", path=name, name="README",
                content=content[:5000],
            )
    return None


# ─── Main: repo → vector space ────────────────────────────────────

def repo_to_vectors(
    repo_url_or_path: str,
    output_path: Optional[str] = None,
    token: Optional[str] = None,
    clone_dir: str = "/tmp/repo-vectors",
    dim: int = 64,
    max_commits: int = 200,
) -> Dict:
    """
    Spring-load a repo into a searchable vector space.
    
    1. Clone the repo (if URL)
    2. Extract all meaningful units (functions, classes, files, commits, README)
    3. Embed each unit
    4. Save as .fvt file
    
    Returns stats and the path to the .fvt file.
    """
    # Resolve repo path
    if repo_url_or_path.startswith("http") or "/" in repo_url_or_path and not os.path.exists(repo_url_or_path):
        # It's a GitHub repo
        repo_name = repo_url_or_path.split("/")[-1].replace(".git", "")
        repo_path = os.path.join(clone_dir, repo_name)
        
        if not os.path.exists(repo_path):
            url = repo_url_or_path
            if token and "github.com" in url:
                url = url.replace("github.com", f"{token}@github.com")
            subprocess.run(
                ["git", "clone", "--depth", str(max_commits), url, repo_path],
                capture_output=True, timeout=60,
            )
    else:
        repo_path = repo_url_or_path
        repo_name = Path(repo_path).name
    
    # Output path
    if output_path is None:
        output_path = os.path.join(clone_dir, f"{repo_name}.fvt")
    
    # Extract tiles
    all_tiles: List[RepoTile] = []
    
    # README
    readme = extract_readme(repo_path)
    if readme:
        all_tiles.append(readme)
    
    # Source files
    code_extensions = {".py", ".rs", ".c", ".h", ".cpp", ".hpp", ".js", ".ts", ".tsx", ".go", ".java", ".rb"}
    skip_dirs = {".git", "node_modules", "__pycache__", "target", "build", "dist", ".venv", "venv"}
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            ext = Path(fname).suffix
            if ext in code_extensions:
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, repo_path)
                try:
                    with open(fpath, "r", errors="ignore") as f:
                        content = f.read()
                    tiles = extract_file_tiles(rel_path, content)
                    all_tiles.extend(tiles)
                except:
                    pass
    
    # Commits
    commits = extract_commits(repo_path, max_commits)
    all_tiles.extend(commits)
    
    # Build vector twin
    twin = FluxVectorTwin(dim=dim)
    
    # Convert RepoTiles to indexable entries
    # We abuse the Tile dataclass from local_plato
    from local_plato import Tile
    plato_tiles = []
    for i, rt in enumerate(all_tiles):
        text = f"{rt.tile_type}: {rt.name}\n{rt.content}"
        plato_tiles.append(Tile(
            tile_id=f"{repo_name}:{rt.tile_type}:{i}",
            room=repo_name,
            domain=rt.path,
            question=f"{rt.tile_type}: {rt.name} ({rt.path})",
            answer=rt.content[:2000],
            source="repo-extractor",
            tags=[rt.tile_type, rt.language] if rt.language else [rt.tile_type],
            timestamp=rt.metadata.get("ts", 0),
        ))
    
    # Index
    indexed = twin.index_tiles(plato_tiles)
    
    # Save
    twin.save(output_path)
    
    # Stats
    type_counts = Counter(t.tile_type for t in all_tiles)
    lang_counts = Counter(t.language for t in all_tiles if t.language)
    
    return {
        "repo": repo_name,
        "tiles_extracted": len(all_tiles),
        "tiles_indexed": indexed,
        "type_breakdown": dict(type_counts),
        "language_breakdown": dict(lang_counts),
        "output_path": output_path,
        "output_size_kb": os.path.getsize(output_path) / 1024,
    }


def search_repo(fvt_path: str, query: str, top_k: int = 10) -> List[Tuple[VectorEntry, float]]:
    """
    Search a spring-loaded repo. Loads .fvt, runs semantic search.
    
    This is the "throwing the dart" — the repo was pre-loaded,
    now you query it in ~0.1ms.
    """
    twin = FluxVectorTwin()
    twin.load(fvt_path)
    return twin.search(query, top_k=top_k)


def repo_report(fvt_path: str) -> str:
    """Human-readable summary of a spring-loaded repo."""
    twin = FluxVectorTwin()
    twin.load(fvt_path)
    
    lines = [
        f"=== REPO VECTOR REPORT: {Path(fvt_path).stem} ===",
        f"Tiles: {twin.count}",
        f"Dimensions: {twin.dim}",
        f"IDF features: {len(twin.idf_weights)}",
        f"",
        "Sample entries:",
    ]
    for entry in twin.entries[:10]:
        lines.append(f"  [{entry.room}] {entry.snippet[:80]}")
    
    return "\n".join(lines)
