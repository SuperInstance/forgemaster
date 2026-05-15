#!/usr/bin/env python3
"""
Boot: Agent Self-Bootstrap from PLATO Loop Tiles
=================================================
Run this on startup. It loads the loop tiles, indexes them by
trigger pattern, and provides a retrieval function.

Usage:
    from plato_loops import bootstrap
    loops = bootstrap()
    matching = loops.match("test model arithmetic capability")
    for loop in matching:
        print(loop["id"], loop["body"])
"""
import json, re
from pathlib import Path

TILES_PATH = Path(__file__).parent / "plato-loop-tiles.json"

class LoopRetriever:
    def __init__(self, tiles_path=TILES_PATH):
        with open(tiles_path) as f:
            data = json.load(f)
        self.loops = data["loops"]
        self._index()
    
    def _index(self):
        """Build a simple keyword index."""
        self.index = {}
        for loop in self.loops:
            words = set(re.findall(r'\w+', 
                f"{loop['trigger']} {loop['domain']} {loop['capability']} "
                f"{' '.join(loop['evidence'])}".lower()))
            self.index[loop["id"]] = words
    
    def match(self, query, top_k=3):
        """Find loops matching a query string."""
        query_words = set(re.findall(r'\w+', query.lower()))
        scores = []
        for loop in self.loops:
            overlap = len(query_words & self.index[loop["id"]])
            score = overlap * loop["confidence"]
            scores.append((score, loop))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [loop for score, loop in scores[:top_k] if score > 0]
    
    def get(self, loop_id):
        """Get a specific loop by ID."""
        return next((l for l in self.loops if l["id"] == loop_id), None)
    
    def execute(self, loop_id, **kwargs):
        """Print the algorithm for a loop (agent reads and follows)."""
        loop = self.get(loop_id)
        if not loop:
            print(f"Loop {loop_id} not found")
            return
        print(f"\n{'='*60}")
        print(f"LOOP: {loop['id']}")
        print(f"TRIGGER: {loop['trigger']}")
        print(f"CONFIDENCE: {loop['confidence']:.0%}")
        print(f"{'='*60}")
        if loop.get("seed"):
            print(f"\nSEED (proven prompt):")
            print(f"  System: {loop['seed']['system']}")
            print(f"  Template: {loop['seed']['template']}")
            print(f"  Temp: {loop['seed']['temperature']}, Max tokens: {loop['seed']['max_tokens']}")
        print(f"\nALGORITHM:")
        print(loop["body"].strip())
        print(f"\nBOUNDARY CONDITIONS:")
        print(f"  {loop['negative']}")
        print(f"\nEVIDENCE: {', '.join(loop['evidence'])}")

def bootstrap():
    """Load and return the loop retriever."""
    return LoopRetriever()

if __name__ == "__main__":
    retriever = bootstrap()
    print(f"Loaded {len(retriever.loops)} PLATO loop tiles")
    print(f"Available loops:")
    for loop in retriever.loops:
        print(f"  {loop['id']}: {loop['trigger'][:60]}")
