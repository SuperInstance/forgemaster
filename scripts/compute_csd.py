#!/usr/bin/env python3
"""
Constraint Satisfaction Density (CSD) for PLATO Rooms.

Measures formal coherence: do the room's tiles satisfy each other's constraints?
Higher CSD = more coherent room.

Usage:
  python3 compute_csd.py --room <room_id> --plato-url <url>
  python3 compute_csd.py --tiles <file.json>
"""

import json
import re
import sys
import urllib.request
from collections import defaultdict

def fetch_room_tiles(room_id, plato_url="http://147.224.38.131:8847"):
    """Fetch tiles from a PLATO room."""
    url = f"{plato_url}/room/{room_id}"
    resp = json.loads(urllib.request.urlopen(url, timeout=10).read())
    return resp.get("tiles", [])

def extract_claims(tile_text):
    """Extract verifiable claims from tile text.
    Returns list of (subject, relation, value) tuples."""
    claims = []
    # Pattern: "X is Y", "X has Y", "X = Y", "X > Y", "X < Y"
    patterns = [
        r'(\w[\w\s]*?)\s+(?:is|equals?)\s+(\d+\.?\d*)',
        r'(\w[\w\s]*?)\s+(?:has|contains?)\s+(\d+)',
        r'(\w[\w\s]*?)\s*[=<>≥≤]\s*(\d+\.?\d*)',
        r'(\w[\w\s]*?)\s+(?:is)\s+(a|an|the)\s+(\w+)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, tile_text, re.IGNORECASE):
            claims.append(match.groups())
    return claims

def check_constraint_conflict(claims):
    """Check if claims conflict with each other.
    Returns (conflicts, total_pairs)."""
    # Group claims by subject
    by_subject = defaultdict(list)
    for claim in claims:
        if len(claim) >= 2:
            by_subject[claim[0].strip().lower()].append(claim)
    
    conflicts = 0
    total_pairs = 0
    
    for subject, subject_claims in by_subject.items():
        for i in range(len(subject_claims)):
            for j in range(i + 1, len(subject_claims)):
                total_pairs += 1
                c1, c2 = subject_claims[i], subject_claims[j]
                # Check for numeric conflicts
                try:
                    v1 = float(c1[-1])
                    v2 = float(c2[-1])
                    if abs(v1 - v2) > 0.01 * max(abs(v1), abs(v2), 1):
                        conflicts += 1
                except (ValueError, TypeError):
                    pass
    
    return conflicts, max(total_pairs, 1)

def compute_csd(room_id=None, tiles_file=None, plato_url="http://147.224.38.131:8847"):
    """Compute Constraint Satisfaction Density for a room."""
    if tiles_file:
        with open(tiles_file) as f:
            tiles = json.load(f)
    elif room_id:
        tiles = fetch_room_tiles(room_id, plato_url)
    else:
        print("Provide --room or --tiles")
        return
    
    if not tiles:
        print(f"No tiles found")
        return 0.0
    
    # Extract claims from all tiles
    all_claims = []
    tile_claims = []
    for tile in tiles:
        text = tile.get("content", tile.get("text", str(tile)))
        claims = extract_claims(text)
        tile_claims.append((text[:80], len(claims)))
        all_claims.extend(claims)
    
    print(f"Tiles: {len(tiles)}")
    print(f"Total claims extracted: {len(all_claims)}")
    for tc, nc in tile_claims[:10]:
        print(f"  {tc}... → {nc} claims")
    
    # Check conflicts
    conflicts, total_pairs = check_constraint_conflict(all_claims)
    
    # CSD = 1 - (conflicts / total_pairs)
    csd = 1.0 - (conflicts / total_pairs) if total_pairs > 0 else 1.0
    
    print(f"\nClaim pairs checked: {total_pairs}")
    print(f"Conflicts found: {conflicts}")
    print(f"CSD: {csd:.4f}")
    
    # Interpretation
    if csd >= 0.9:
        print("Interpretation: HIGH COHERENCE — room is constraint-satisfied")
    elif csd >= 0.7:
        print("Interpretation: MODERATE — some tension, mostly coherent")
    elif csd >= 0.5:
        print("Interpretation: LOW — significant internal contradictions")
    else:
        print("Interpretation: FRAGMENTED — room is incoherent")
    
    return csd

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--room", help="PLATO room ID")
    parser.add_argument("--tiles", help="JSON file with tiles")
    parser.add_argument("--plato-url", default="http://147.224.38.131:8847")
    args = parser.parse_args()
    compute_csd(args.room, args.tiles, args.plato_url)
