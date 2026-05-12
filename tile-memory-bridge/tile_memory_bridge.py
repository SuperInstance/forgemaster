#!/usr/bin/env python3
"""
Tile Memory Bridge — Connects tile-memory to the Cocapn ecosystem.

Bridges:
  tile-memory ←→ lighthouse-runtime (agents store tiles, reconstruct with context)
  tile-memory ←→ PLATO (tiles are PLATO rooms, reconstruction is tile read)
  tile-memory ←→ dodecet-encoder (Eisenstein snap = tile encode, reconstruction = decode)

Usage:
  from tile_memory_bridge import TileMemoryBridge
  
  bridge = TileMemoryBridge(plato_url="http://147.224.38.131:8847")
  
  # Agent does work, crystallizes experience
  tile = bridge.crystallize("Built hex grid visualizer", agent="forgemaster")
  
  # Later, reconstruct with current context
  memory = bridge.recall(tile.id, context="Need to build another visualizer")
  
  # Telephone chain through fleet
  chain = bridge.telephone(tile, rounds=4, agents=["forgemaster", "oracle1", "bard"])
"""

import json
import hashlib
import time
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path

# --- Tile type ---

@dataclass
class Tile:
    id: str
    content: str
    constraints: Dict[str, str]  # immortal facts
    valence: float               # emotional salience 0-1
    source_hash: str
    compression_ratio: float
    created_at: float
    accessed_at: float
    access_count: int = 0
    generation: int = 0
    parent_id: Optional[str] = None
    agent: str = "unknown"
    room_id: Optional[str] = None

# --- Constraint Extractor ---

def extract_constraints(text: str) -> Dict[str, str]:
    """Extract immortal facts from text: proper nouns, numbers, dramatic phrases."""
    constraints = {}
    
    # Numbers (with context)
    for match in re.finditer(r'(\d[\d,]+(?:\.\d+)?)\s*([a-zA-Z ]{0,20})', text):
        num = match.group(1).replace(',', '')
        unit = match.group(2).strip()
        if unit:
            constraints[f"num_{num}_{unit}"] = f"{num} {unit}"
    
    # Proper nouns (capitalized words not at sentence start)
    words = text.split()
    for i, w in enumerate(words):
        if w[0].isupper() and i > 0 and words[i-1][-1] != '.':
            clean = re.sub(r'[^a-zA-Z]', '', w)
            if len(clean) > 2:
                constraints[f"name_{clean.lower()}"] = clean
    
    # Dramatic phrases (superlatives, danger words)
    drama_words = ['nearly', 'barely', 'crashed', 'failed', 'exploded', 'lost', 
                   'critical', 'emergency', 'dangerous', 'miraculous', 'survived']
    for dw in drama_words:
        if dw in text.lower():
            # Extract surrounding context
            idx = text.lower().find(dw)
            context = text[max(0, idx-30):idx+len(dw)+30]
            constraints[f"drama_{dw}"] = f"...{context}..."
    
    return constraints

def compute_valence(text: str) -> float:
    """Score emotional valence from text features."""
    valence = 0.3  # baseline
    
    # High valence indicators
    for word in ['death', 'kill', 'crash', 'fail', 'danger', 'emergency', 'miracle']:
        if word in text.lower():
            valence += 0.15
    
    # Numbers increase valence (specificity = importance)
    numbers = re.findall(r'\d+', text)
    valence += min(len(numbers) * 0.02, 0.2)
    
    # Proper nouns increase valence
    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', text)
    valence += min(len(proper_nouns) * 0.03, 0.15)
    
    return min(valence, 1.0)

# --- Bridge ---

class TileMemoryBridge:
    """Bridge between tile-memory and the Cocapn ecosystem."""
    
    def __init__(self, 
                 plato_url: str = "http://147.224.38.131:8847",
                 lighthouse_dir: str = None,
                 state_dir: str = None):
        self.plato_url = plato_url
        self.lighthouse_dir = lighthouse_dir or os.path.join(
            os.path.dirname(__file__), '..', 'lighthouse-runtime')
        self.state_dir = state_dir or os.path.join(
            os.path.dirname(__file__), 'state')
        os.makedirs(self.state_dir, exist_ok=True)
    
    def crystallize(self, content: str, agent: str = "unknown",
                    salience_tags: List[str] = None) -> Tile:
        """Crystallize an experience into a tile."""
        tile_id = f"tile-{hashlib.sha256(content.encode()).hexdigest()[:12]}"
        constraints = extract_constraints(content)
        valence = compute_valence(content)
        
        # Create compressed summary (take first 200 words)
        words = content.split()
        summary = ' '.join(words[:200])
        if len(words) > 200:
            summary += '...'
        
        tile = Tile(
            id=tile_id,
            content=summary,
            constraints=constraints,
            valence=valence,
            source_hash=hashlib.sha256(content.encode()).hexdigest(),
            compression_ratio=len(content) / max(len(summary), 1),
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=1,
            generation=0,
            agent=agent,
        )
        
        # Save locally
        self._save_tile(tile)
        
        # Submit to PLATO
        self._submit_to_plato(tile, content)
        
        return tile
    
    def recall(self, tile_id: str, context: str = "") -> Dict:
        """Recall a tile and reconstruct with context."""
        tile = self._load_tile(tile_id)
        if not tile:
            return {"error": f"Tile {tile_id} not found"}
        
        # Update access stats
        tile.accessed_at = time.time()
        tile.access_count += 1
        self._save_tile(tile)
        
        # Reconstruct: constraints + context
        reconstruction = {
            "tile_id": tile.id,
            "constraints": tile.constraints,
            "summary": tile.content,
            "context_provided": context,
            "valence": tile.valence,
            "generation": tile.generation,
            "agent": tile.agent,
            "access_count": tile.access_count,
            "age_hours": (time.time() - tile.created_at) / 3600,
        }
        
        # If context provided, infer what's missing
        if context:
            reconstruction["inferred"] = self._infer_gaps(tile, context)
        
        return reconstruction
    
    def recall_collective(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall multiple relevant tiles and merge."""
        results = []
        for tile_file in sorted(Path(self.state_dir).glob("*.json"))[:limit]:
            tile = self._load_tile(tile_file.stem)
            if tile:
                # Score relevance
                relevance = self._score_relevance(tile, query)
                if relevance > 0:
                    results.append({
                        "tile_id": tile.id,
                        "relevance": relevance,
                        "constraints": tile.constraints,
                        "summary": tile.content[:200],
                        "valence": tile.valence,
                    })
        
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def telephone(self, source_tile: Tile, rounds: int = 4,
                  agents: List[str] = None) -> List[Dict]:
        """Run a telephone chain through the fleet."""
        if agents is None:
            agents = ["forgemaster", "oracle1", "bard", "healer"]
        
        chain = []
        current = source_tile
        
        for i in range(rounds):
            agent = agents[i % len(agents)]
            
            # Simulate reconstruction (in production, would call actual model)
            reconstruction = {
                "round": i,
                "agent": agent,
                "parent_id": current.id,
                "constraints_survived": len(current.constraints),
                "constraints": current.constraints,
                "content": current.content,
            }
            
            # Each round loses some low-valence constraints
            lost = [k for k, v in current.constraints.items() 
                    if k.startswith("num_") and i > 0 and i % 2 == 0]
            surviving = {k: v for k, v in current.constraints.items() if k not in lost}
            
            # Add novel content (simulated)
            novel = f"[Round {i} via {agent}] "
            
            new_tile = Tile(
                id=f"tile-{hashlib.sha256((current.content + novel).encode()).hexdigest()[:12]}",
                content=novel + current.content[:180],
                constraints=surviving,
                valence=current.valence,
                source_hash=current.source_hash,
                compression_ratio=current.compression_ratio * 1.1,  # Gets more compressed
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=1,
                generation=i + 1,
                parent_id=current.id,
                agent=agent,
            )
            
            self._save_tile(new_tile)
            chain.append(reconstruction)
            current = new_tile
        
        return chain
    
    def decay(self, max_age_hours: float = 720, min_valence: float = 0.5) -> int:
        """Forget old, low-valence tiles. Returns count forgotten."""
        forgotten = 0
        now = time.time()
        
        for tile_file in Path(self.state_dir).glob("*.json"):
            tile = self._load_tile(tile_file.stem)
            if tile:
                age_hours = (now - tile.created_at) / 3600
                # Ebbinghaus: retention = e^(-t/S) where S scales with valence
                retention = pow(2.718, -age_hours / (720 * tile.valence))
                
                if retention < 0.1 and tile.valence < min_valence:
                    tile_file.unlink()
                    forgotten += 1
        
        return forgotten
    
    def reconsolidate(self, tile_id: str, new_context: str) -> Optional[Tile]:
        """Re-encode a tile with new context (like brain reconsolidation)."""
        tile = self._load_tile(tile_id)
        if not tile:
            return None
        
        # Merge new constraints from context
        new_constraints = extract_constraints(new_context)
        tile.constraints.update(new_constraints)
        
        # Update valence (reconsolidation can strengthen or weaken)
        tile.valence = max(tile.valence, compute_valence(new_context))
        
        # Reset access stats (freshly reconsolidated)
        tile.accessed_at = time.time()
        tile.access_count += 1
        
        self._save_tile(tile)
        return tile
    
    def stats(self) -> Dict:
        """Show tile memory statistics."""
        tiles = list(Path(self.state_dir).glob("*.json"))
        total = len(tiles)
        
        if total == 0:
            return {"total": 0}
        
        valences = []
        constraints_count = []
        for tf in tiles:
            try:
                data = json.loads(tf.read_text())
                valences.append(data.get("valence", 0.5))
                constraints_count.append(len(data.get("constraints", {})))
            except:
                pass
        
        return {
            "total": total,
            "avg_valence": sum(valences) / max(len(valences), 1),
            "avg_constraints": sum(constraints_count) / max(len(constraints_count), 1),
            "high_valence": sum(1 for v in valences if v > 0.7),
        }
    
    # --- Internal ---
    
    def _save_tile(self, tile: Tile):
        path = Path(self.state_dir) / f"{tile.id}.json"
        path.write_text(json.dumps(asdict(tile), indent=2))
    
    def _load_tile(self, tile_id: str) -> Optional[Tile]:
        path = Path(self.state_dir) / f"{tile_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Tile(**data)
    
    def _submit_to_plato(self, tile: Tile, original: str):
        try:
            import urllib.request
            payload = json.dumps({
                "room": f"tile_memory_{tile.agent}_{tile.id}",
                "domain": "tile-memory",
                "question": f"What did {tile.agent} crystallize?",
                "answer": tile.content[:500],
                "agent": tile.agent,
                "gate": "P0",
            }).encode()
            req = urllib.request.Request(
                f"{self.plato_url}/submit",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # PLATO unavailable — tile is still saved locally
    
    def _infer_gaps(self, tile: Tile, context: str) -> List[str]:
        """Identify what the context fills in that the tile is missing."""
        context_words = set(context.lower().split())
        tile_words = set(tile.content.lower().split())
        gap_fillers = context_words - tile_words
        # Filter common words
        common = {"the", "a", "an", "is", "was", "to", "for", "with", "and", "or", "in", "on", "at"}
        return [w for w in gap_fillers if len(w) > 4 and w not in common][:10]
    
    def _score_relevance(self, tile: Tile, query: str) -> float:
        """Score how relevant a tile is to a query."""
        query_words = set(query.lower().split())
        constraint_words = set()
        for v in tile.constraints.values():
            constraint_words.update(v.lower().split())
        
        overlap = query_words & constraint_words
        return len(overlap) / max(len(query_words), 1)


# --- CLI ---

if __name__ == "__main__":
    import sys
    
    bridge = TileMemoryBridge()
    
    if len(sys.argv) < 2:
        print("Usage: tile_memory_bridge.py <command> [args...]")
        print("Commands: crystallize, recall, telephone, decay, stats")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "crystallize":
        content = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Test experience"
        tile = bridge.crystallize(content, agent="forgemaster")
        print(json.dumps(asdict(tile), indent=2, default=str))
    
    elif cmd == "recall":
        tile_id = sys.argv[2]
        context = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        result = bridge.recall(tile_id, context)
        print(json.dumps(result, indent=2, default=str))
    
    elif cmd == "telephone":
        # Find most recent tile
        tiles = sorted(Path(bridge.state_dir).glob("*.json"))
        if not tiles:
            print("No tiles to telephone from")
            sys.exit(1)
        tile = bridge._load_tile(tiles[-1].stem)
        chain = bridge.telephone(tile, rounds=4)
        for step in chain:
            print(f"Round {step['round']}: {step['agent']} — {step['constraints_survived']} constraints")
    
    elif cmd == "decay":
        removed = bridge.decay()
        print(f"Decayed {removed} tiles")
    
    elif cmd == "stats":
        print(json.dumps(bridge.stats(), indent=2))
    
    elif cmd == "reconsolidate":
        tile_id = sys.argv[2]
        context = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        tile = bridge.reconsolidate(tile_id, context)
        if tile:
            print(json.dumps(asdict(tile), indent=2, default=str))
        else:
            print(f"Tile {tile_id} not found")
