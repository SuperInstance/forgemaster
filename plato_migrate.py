#!/usr/bin/env python3
"""plato_migrate.py — PLATO Engine Tile Migration Script

Reads tiles from a live PLATO server and validates them against
the Rust plato-engine gate rules.

Usage:
    python3 plato_migrate.py [--server URL] [--output FILE] [--max-rooms N] [--room NAME]
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
ABSOLUTE_WORDS_PATTERN = re.compile(
    r"(?i)\b(always|never|impossible|definitely|certainly|without doubt|undeniably)\b"
)
# PLATO tile fields: domain, question, answer, confidence, source, _hash, provenance, energy, reinforcement_count
REQUIRED_FIELDS = ("domain", "question", "answer", "confidence", "source")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get_json(url: str) -> Any:
    """Fetch JSON from *url* with retries and timeout."""
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = Request(url, method="GET", headers={"Accept": "application/json"})
            with urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)
        except HTTPError as exc:
            last_error = exc
            if 400 <= exc.code < 500:
                raise RuntimeError(
                    f"HTTP {exc.code} {exc.reason} for URL {url}"
                ) from exc
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


def fetch_rooms(server_url: str) -> Dict[str, Dict[str, Any]]:
    """Return rooms dict from the server. Keys are room names, values are room metadata."""
    url = f"{server_url}/rooms"
    result = _http_get_json(url)
    if not isinstance(result, dict):
        raise RuntimeError(f"Expected dict from /rooms, got {type(result).__name__}")
    return result


def fetch_tiles(server_url: str, room_name: str) -> List[Dict[str, Any]]:
    """Return the list of tiles for a given room via /room/{room_name}."""
    url = f"{server_url}/room/{room_name}"
    result = _http_get_json(url)
    if isinstance(result, dict):
        return result.get("tiles", [])
    if isinstance(result, list):
        return result
    raise RuntimeError(f"Unexpected response from /room/{room_name}: {type(result).__name__}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_tile(
    tile: Dict[str, Any],
    room_name: str,
    seen_contents: Set[str],
) -> Tuple[bool, List[str], List[str]]:
    """Validate a single tile against the Rust plato-engine gate rules.

    Returns:
        (passed, reasons, matched_words)
    """
    reasons: List[str] = []
    matched_words: List[str] = []

    # 1. Missing fields
    for field in REQUIRED_FIELDS:
        value = tile.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            reasons.append("missing_fields")

    # 2. Empty question
    question = tile.get("question", "")
    if not isinstance(question, str) or question.strip() == "":
        reasons.append("empty_question")

    # 3. Invalid confidence
    confidence = tile.get("confidence")
    if confidence is not None:
        try:
            c = float(confidence)
            if not (0.0 <= c <= 1.0):
                reasons.append("invalid_confidence")
        except (ValueError, TypeError):
            reasons.append("invalid_confidence")
    else:
        reasons.append("invalid_confidence")

    # 4. Domain mismatch
    domain = tile.get("domain", "")
    if isinstance(domain, str) and isinstance(room_name, str):
        if domain.strip().lower() != room_name.strip().lower():
            reasons.append("domain_mismatch")

    # 5. Too short (check 'answer' as main content)
    answer = tile.get("answer", "")
    if isinstance(answer, str):
        if len(answer.strip()) < 10:
            reasons.append("too_short")
    else:
        reasons.append("too_short")

    # 6. Absolute claims (check 'answer' as main content)
    if isinstance(answer, str):
        found = ABSOLUTE_WORDS_PATTERN.findall(answer)
        if found:
            reasons.append("absolute_claims")
            matched_words = [w.lower() for w in found]

    # 7. Duplicates (global, based on 'answer')
    if isinstance(answer, str):
        normalised = answer.strip().lower()
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

def run_migration(
    server_url: str,
    max_rooms: Optional[int] = None,
    single_room: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the full migration pipeline and return the report dict."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    rooms_dict = fetch_rooms(server_url)
    room_names = sorted(rooms_dict.keys())
    total_rooms_available = len(room_names)

    # Filter to single room if specified
    if single_room:
        if single_room not in rooms_dict:
            raise RuntimeError(
                f"Room '{single_room}' not found. Available rooms: {len(room_names)}"
            )
        room_names = [single_room]

    # Apply max_rooms limit
    if max_rooms is not None and max_rooms > 0:
        room_names = room_names[:max_rooms]

    seen_contents: Set[str] = set()
    rejected_tiles: List[Dict[str, Any]] = []
    per_room_stats: List[Dict[str, Any]] = []
    rejection_counter: Counter = Counter()

    total_tiles = 0
    total_passed = 0

    for room_name in room_names:
        try:
            tiles = fetch_tiles(server_url, room_name)
        except RuntimeError as exc:
            per_room_stats.append({
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
                room_total -= 1
                continue

            passed, reasons, matched_words = validate_tile(tile, room_name, seen_contents)
            total_tiles += 1

            if passed:
                total_passed += 1
                room_passed += 1
            else:
                room_failed += 1

                answer = tile.get("answer", "")
                content_str = answer if isinstance(answer, str) else str(answer)
                primary_reason = reasons[0]

                rejected_entry: Dict[str, Any] = {
                    "tile_domain": tile.get("domain", ""),
                    "reason": primary_reason,
                    "content_preview": _content_preview(content_str),
                }

                if primary_reason == "absolute_claims" and matched_words:
                    rejected_entry["matched_words"] = matched_words

                rejected_tiles.append(rejected_entry)

                for reason in reasons:
                    rejection_counter[reason] += 1

        per_room_stats.append({
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
            "total_rooms": total_rooms_available,
            "rooms_scanned": len(room_names),
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
            "invalid_confidence": rejection_counter.get("invalid_confidence", 0),
            "empty_question": rejection_counter.get("empty_question", 0),
            "domain_mismatch": rejection_counter.get("domain_mismatch", 0),
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
    parser.add_argument(
        "--max-rooms",
        type=int,
        default=None,
        help="Limit scanning to N rooms (default: scan all)",
    )
    parser.add_argument(
        "--room",
        type=str,
        default=None,
        help="Scan a specific room by name",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server_url = args.server.rstrip("/")

    try:
        report = run_migration(
            server_url,
            max_rooms=args.max_rooms,
            single_room=args.room,
        )
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
