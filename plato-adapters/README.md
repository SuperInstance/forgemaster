# PLATO TileAdapter Protocol

A connector system for extracting knowledge tiles from various sources and submitting them to PLATO's quality gate. Inspired by LlamaIndex's data connectors, but with PLATO's quality gate baked in.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from src.adapter import PLATOSubmitter
from src.adapters.markdown_adapter import MarkdownAdapter

# Extract tiles from a markdown file
adapter = MarkdownAdapter()
tiles = adapter.extract("docs/faq.md")
valid = adapter.validate(tiles)

# Submit to PLATO quality gate
submitter = PLATOSubmitter()
accepted, rejected, reasons = submitter.submit(valid)

print(f"Accepted: {len(accepted)}, Rejected: {len(rejected)}")
for q, reason in reasons.items():
    print(f"  REJECTED '{q[:50]}...': {reason}")
```

## Adapters

### MarkdownAdapter

Extracts Q&A pairs from structured markdown files.

```python
from src.adapters.markdown_adapter import MarkdownAdapter

adapter = MarkdownAdapter()
tiles = adapter.extract("knowledge-base.md")
valid = adapter.validate(tiles)  # filters answer length <= 20 chars
```

Recognized patterns:
- `## Question heading` → `**Answer:** response text`
- Any heading (## to ####) with a following paragraph

### GitHubAdapter

Extracts knowledge from GitHub repositories.

```python
from src.adapters.github_adapter import GitHubAdapter

adapter = GitHubAdapter()
# From a local repo
tiles = adapter.extract("/path/to/local/repo")
# From a GitHub URL (clones automatically)
tiles = adapter.extract("https://github.com/org/repo")
valid = adapter.validate(tiles)
```

Extracts:
- README sections as Q&A tiles
- Code comments containing constraint keywords (MUST, SHALL, NEVER, etc.)
- Git metadata (commit hash, author, date) as provenance

### PlatoRoomAdapter

Reads existing PLATO rooms and produces derived tiles with cross-referencing.

```python
from src.adapters.plato_room_adapter import PlatoRoomAdapter

adapter = PlatoRoomAdapter(rooms_dir="/path/to/plato/rooms")
# Process all rooms
tiles = adapter.extract()
# Process a specific room
tiles = adapter.extract("constraint-theory.md")
valid = adapter.validate(tiles)
```

Features:
- Extracts Q&A from room content
- Cross-references tiles across rooms
- Generates "bridge" tiles connecting related domains

### WebAdapter

Fetches web pages and extracts structured content.

```python
from src.adapters.web_adapter import WebAdapter

adapter = WebAdapter()
tiles = adapter.extract("https://example.com/docs")
valid = adapter.validate(tiles)
adapter.close()
```

Extraction strategies:
- Heading + paragraph Q&A
- FAQ-style (Q:/A:) patterns
- Definition extraction (**Term**: Definition)

## TileSpec

Every adapter produces `TileSpec` objects:

```python
from src.adapter import TileSpec, ProvenanceRecord

tile = TileSpec(
    domain="constraint-theory",
    question="What is zero drift?",
    answer="Zero drift means the constraint system maintains perfect satisfaction over time.",
    source="plato-room://constraint-theory",
    confidence=0.9,
    tags=["constraint", "drift", "plato-room"],
    provenance=ProvenanceRecord.now(
        extractor_name="PlatoRoomAdapter",
        source_uri="plato-room://constraint-theory",
        content=b"...",
    ),
)
```

## PLATO Submitter

```python
from src.adapter import PLATOSubmitter

submitter = PLATOSubmitter()  # defaults to http://147.224.38.131:8847/submit

# Real submission
accepted, rejected, reasons = submitter.submit(valid_tiles)

# Dry run (local validation only, no network)
accepted, rejected, reasons = submitter.submit(valid_tiles, dry_run=True)
```

## Running Tests

```bash
cd plato-adapters
python -m pytest tests/ -v
```
