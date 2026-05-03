#!/usr/bin/env python3
"""plato_migrate.py — PLATO Engine Tile Migration Script

Reads tiles from a live PLATO server and validates them against
the Rust plato-engine gate rules.

Usage:
    python3 plato_migrate.py [--server URL] [--output FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_SERVER = "http://147.224.38.131:8847"
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds
REQUEST_TIMEOUT = 10  # seconds
VALID_TYPES = {"fact", "claim", "question", "evidence", "inference"}
ABSOLUTE_WORDS_PATTERN = re.compile(
    r"(?i)\b(always|never|impossible|definitely|certainly|without doubt|undeniably)\b"
)
REQUIRED_FIELDS = ("id", "room_id", "content", "type")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get_json(url: str) -> Any:
    """Fetch JSON from *url* with retries and timeout.

    Raises:
        RuntimeError: if the server is unreachable after all retries or
                      returns an HTTP error status.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = Request(url, method="GET", headers={"Accept": "application/json"})
            with urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)
        except HTTPError as exc:
            last_error = exc
            # Non-retryable 4xx client errors — don't retry
            if 400 <= exc.code < 500:
                raise RuntimeError(
                    f"HTTP {exc.code} {exc.reason} for URL {url}"
                ) from exc
            # 5xx — retry
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError(
                f"HTTP {exc.code} {exc.reason} for URL {url} after {MAX_RETRIES} attempts"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError(
                f"Failed to reach {url} after {MAX_RETRIES} attempts: {exc}"
            ) from exc

    raise RuntimeError(
        f"Failed to fetch {url} after {MAX_RETRIES} attempts: {last_error}"
    )


def fetch_rooms(server_url: str) -> List[Dict[str, Any]]:
    """Return the list of rooms from the server."""
    url = f"{server_url}/rooms"
    result = _http_get_json(url)
    if not isinstance(result, list):
        raise RuntimeError(f"Expected list from /rooms, got {type(result).__name__}")
    return result


def fetch_tiles(server_url: str, room_id: str) -> List[Dict[str, Any]]:
    """Return the list of tiles for a given room."""
    url = f"{server_url}/rooms/{room_id}/tiles"
    result = _http_get_json(url)
    if not isinstance(result, list):
        raise RuntimeError(f"Expected list from /rooms/{room_id}/tiles, got {type(result).__name__}")
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_tile(
    tile: Dict[str, Any],
    seen_contents: Set[str],
) -> Tuple[bool, List[str], List[str]]:
    """Validate a single tile against the Rust plato-engine gate rules.

    Returns:
        (passed, reasons, matched_words)
        * passed        – True if the tile passes ALL rules
        * reasons       – list of rejection reason keys (e.g. "absolute_claims")
        * matched_words – words from the absolute-claim regex that matched
                          (empty list when the rule did not fire)
    """
    reasons: List[str] = []
    matched_words: List[str] = []

    # 4. Missing fields
    for field in REQUIRED_FIELDS:
        value = tile.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            reasons.append("missing_fields")
            # Missing fields means we can't safely check the remaining rules
            # that depend on those fields, but we still want to surface ALL
            # applicable rejections.  We'll guard with fallbacks below.

    # 5. Invalid type
    tile_type = tile.get("type")
    if tile_type is not None and tile_type not in VALID_TYPES:
        reasons.append("invalid_type")

    # 3. Too short
    content = tile.get("content", "")
    if isinstance(content, str):
        if len(content.strip()) < 10:
            reasons.append("too_short")
    else:
        reasons.append("too_short")

    # 1. Absolute claims
    if isinstance(content, str):
        found = ABSOLUTE_WORDS_PATTERN.findall(content)
        if found:
            reasons.append("absolute_claims")
            matched_words = [w.lower() for w in found]

    # 2. Duplicates (global)
    if isinstance(content, str):
        normalised = content.strip().lower()
        if normalised in seen_contents:
            reasons.append("duplicates")
        else:
            seen_contents.add(normalised)

    passed = len(reasons) == 0
    return passed, reasons, matched_words


def _content_preview(content: str, max_len: int = 80) -> str:
    """Return first *max_len* chars of *content*, appending '...' when truncated."""
    if len(content) <= max_len:
        return content
    return content[:max_len] + "..."


# ---------------------------------------------------------------------------
# Migration engine
# ---------------------------------------------------------------------------

def run_migration(server_url: str) -> Dict[str, Any]:
    """Execute the full migration pipeline and return the report dict."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    rooms = fetch_rooms(server_url)
    total_rooms = len(rooms)

    seen_contents: Set[str] = set()
    rejected_tiles: List[Dict[str, Any]] = []
    per_room_stats: List[Dict[str, Any]] = []
    rejection_counter: Counter = Counter()

    total_tiles = 0
    total_passed = 0

    for room in rooms:
        room_id = room.get("id", "<unknown>")
        room_name = room.get("name", "<unnamed>")

        try:
            tiles = fetch_tiles(server_url, room_id)
        except RuntimeError as exc:
            # Gracefully skip rooms whose tiles cannot be fetched.
            per_room_stats.append({
                "room_id": room_id,
                "room_name": room_name,
                "total_tiles": 0,
                "passed": 0,
                "failed": 0,
                "error": str(exc),
            })
            continue

        room_total = len(tiles)
        room_passed = 0
        room_failed = 0

        for tile in tiles:
            if not isinstance(tile, dict):
                # Defensive: skip non-dict entries gracefully
                room_total -= 1
                continue

            passed, reasons, matched_words = validate_tile(tile, seen_contents)
            total_tiles += 1

            if passed:
                total_passed += 1
                room_passed += 1
            else:
                total_failed = total_tiles - total_passed
                room_failed += 1

                tile_id = tile.get("id", "<no-id>")
                tile_room_id = tile.get("room_id", room_id)
                content = tile.get("content", "")
                content_str = content if isinstance(content, str) else str(content)

                primary_reason = reasons[0]  # Use first reason as the main one

                rejected_entry: Dict[str, Any] = {
                    "tile_id": tile_id,
                    "room_id": tile_room_id,
                    "reason": primary_reason,
                    "content_preview": _content_preview(content_str),
                }

                if primary_reason == "absolute_claims" and matched_words:
                    rejected_entry["matched_words"] = matched_words

                rejected_tiles.append(rejected_entry)

                for reason in reasons:
                    rejection_counter[reason] += 1

        per_room_stats.append({
            "room_id": room_id,
            "room_name": room_name,
            "total_tiles": room_total,
            "passed": room_passed,
            "failed": room_failed,
        })

    total_failed = total_tiles - total_passed
    pass_rate = round(total_passed / total_tiles, 2) if total_tiles > 0 else 0.0

    report: Dict[str, Any] = {
        "migration": "plato_tiles",
        "server": server_url,
        "timestamp": timestamp,
        "summary": {
            "total_rooms": total_rooms,
            "total_tiles": total_tiles,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": pass_rate,
        },
        "rejection_breakdown": {
            "absolute_claims": rejection_counter.get("absolute_claims", 0),
            "duplicates": rejection_counter.get("duplicates", 0),
            "too_short": rejection_counter.get("too_short", 0),
            "missing_fields": rejection_counter.get("missing_fields", 0),
            "invalid_type": rejection_counter.get("invalid_type", 0),
        },
        "rejected_tiles": rejected_tiles,
        "per_room": per_room_stats,
    }

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PLATO Engine Tile Migration Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Reads tiles from a live PLATO server and validates them against "
            "the Rust plato-engine gate rules."
        ),
    )
    parser.add_argument(
        "--server",
        type=str,
        default=DEFAULT_SERVER,
        help=f"PLATO server base URL (default: {DEFAULT_SERVER})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional file path to write the JSON report",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server_url = args.server.rstrip("/")

    try:
        report = run_migration(server_url)
    except RuntimeError as exc:
        error_report = {
            "migration": "plato_tiles",
            "server": server_url,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": str(exc),
            "status": "failed",
        }
        json.dump(error_report, sys.stdout, indent=2)
        print()
        return 1

    json_output = json.dumps(report, indent=2)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(json_output)
                fh.write("\n")
        except OSError as exc:
            print(
                json.dumps(
                    {
                        "error": f"Failed to write output file {args.output}: {exc}",
                    }
                ),
                file=sys.stderr,
            )
            return 1

    print(json_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
