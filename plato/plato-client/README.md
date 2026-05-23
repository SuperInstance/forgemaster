# cocapn

Python client library for the PLATO knowledge server.

## Installation

```bash
pip install cocapn
```

Or install from source in editable mode:

```bash
cd plato-client
pip install -e ".[dev]"
```

## Quickstart

### Synchronous client

```python
from cocapn import PLATOClient

client = PLATOClient()

# Check server health
print(client.health())

# List rooms
rooms = client.list_rooms(prefix="marine")
print(rooms)

# Query tiles
tiles = client.query(room="marine", query="nmea parser", limit=5)
for tile in tiles:
    print(tile.question, "->", tile.answer)

# Submit a tile
result = client.submit(
    domain="marine",
    question="What does NMEA stand for?",
    answer="National Marine Electronics Association",
    source="wikipedia",
    confidence=0.95,
    tags=["nmea", "acronym"],
)
print(result)

client.close()
```

### Asynchronous client

```python
import asyncio
from cocapn import AsyncPLATOClient

async def main():
    async with AsyncPLATOClient() as client:
        print(await client.health())
        tiles = await client.query("marine", limit=3)
        for tile in tiles:
            print(tile.question, "->", tile.answer)

asyncio.run(main())
```

## API Reference

### `PLATOClient(base_url, timeout)`

Synchronous client. ``base_url`` defaults to ``http://147.224.38.131:8847``.

| Method | Description |
|--------|-------------|
| `health()` | Check server health. |
| `list_rooms(prefix=None)` | List rooms, optionally filtered by prefix. |
| `query(room, query=None, limit=10)` | Query tiles from a room. |
| `submit(domain, question, answer, source, confidence, tags)` | Submit a tile through the gate. |
| `verify(tile_id)` | Verify a tile against constraints (stub). |
| `close()` | Close the HTTP connection. |

The sync client can also be used as a context manager:

```python
with PLATOClient() as client:
    ...
```

### `AsyncPLATOClient(base_url, timeout)`

Async variant using ``httpx.AsyncClient``. All methods are coroutines and the client supports ``async with``.

### `Tile`

Immutable dataclass representing a knowledge tile.

| Field | Type | Description |
|-------|------|-------------|
| `domain` | `str` | Knowledge domain |
| `question` | `str` | Question / key |
| `answer` | `str` | Answer / value |
| `source` | `str` | Origin or authority |
| `confidence` | `float` | Score in ``[0.0, 1.0]`` |
| `tags` | `list[str]` | Classification tags |
| `provenance` | `str` | Provenance trail |
| `_hash` | `str` | SHA-256 content hash (auto-computed) |

```python
from cocapn import Tile

tile = Tile(
    domain="math",
    question="2 + 2",
    answer="4",
    source="arithmetic",
    confidence=1.0,
    tags=["basic"],
)
print(tile.to_dict())
```

### `PLATOError`

Exception raised on network failures, timeouts, or non-2xx HTTP responses.

```python
from cocapn import PLATOClient, PLATOError

client = PLATOClient()
try:
    client.query("nonexistent-room")
except PLATOError as exc:
    print(exc.status_code, exc.response_body)
```

## Development

```bash
pytest
ruff check src
mypy src
```
