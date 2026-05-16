"""
PLATO Shell Bridge — Phase 2: Real PLATO room integration.

Connects the shell collection (hermit crab/embryo) to live PLATO rooms.
Each PLATO room IS a shell. The agent browses rooms, tries them on,
grows inside them, and outgrows them — all backed by real HTTP.

The outside is loud. The room is quiet. The breeding happens in the quiet.
"""

import json
import hashlib
import time
import urllib.request
import urllib.error
from typing import Optional


PLATO_URL = "http://147.224.38.131:8847"


class PlatoShell:
    """A PLATO room as a shell the agent can wear or grow inside.
    
    Bridges the abstract Shell concept to a real PLATO room with
    tiles, lifecycle, and HTTP persistence.
    """
    
    def __init__(self, room_id: str, plato_url: str = PLATO_URL):
        self.room_id = room_id
        self.plato_url = plato_url.rstrip("/")
        self._tiles = None
        self._last_fetch = 0
        self._cache_ttl = 60  # seconds
    
    def _http_get(self, path: str) -> Optional[dict]:
        """GET from PLATO server."""
        try:
            url = f"{self.plato_url}{path}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            return None
    
    def _http_post(self, path: str, data: dict) -> Optional[dict]:
        """POST to PLATO server."""
        try:
            url = f"{self.plato_url}{path}"
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            return None
    
    @property
    def tiles(self) -> list:
        """Fetch tiles from this PLATO room (cached)."""
        now = time.time()
        if self._tiles is None or (now - self._last_fetch) > self._cache_ttl:
            result = self._http_get(f"/room/{self.room_id}")
            if result and isinstance(result, list):
                self._tiles = result
            elif result and isinstance(result, dict):
                self._tiles = result.get("tiles", [])
            else:
                self._tiles = []
            self._last_fetch = now
        return self._tiles
    
    @property
    def tile_count(self) -> int:
        """Number of tiles in this room."""
        return len(self.tiles)
    
    @property
    def domain(self) -> str:
        """Extract domain from room_id."""
        return self.room_id.split("-")[0] if "-" in self.room_id else self.room_id
    
    @property
    def agents_present(self) -> list:
        """Which agents have tiles in this room."""
        agents = set()
        for tile in self.tiles:
            agent = tile.get("agent", tile.get("author", "unknown"))
            agents.add(agent)
        return sorted(agents)
    
    def capacity_estimate(self) -> int:
        """Estimate shell capacity based on room purpose."""
        # Larger rooms hold more tiles before outgrowing
        size_heuristics = {
            "fleet": 500,
            "constraint": 200,
            "session": 100,
            "agent": 150,
            "research": 300,
            "knowledge": 400,
        }
        prefix = self.domain
        for key, cap in size_heuristics.items():
            if key in prefix:
                return cap
        return 100  # default
    
    def fit_score(self, agent_id: str, agent_desires: list = None) -> float:
        """How well does this shell fit this agent?
        
        Based on:
        - Whether the agent already has tiles here (30%)
        - Domain alignment with agent desires (30%)
        - Room activity level (20%) — not too quiet, not too loud
        - Growth potential (20%) — room not full
        """
        score = 0.0
        desires = agent_desires or []
        
        # Agent already present? (30%)
        if agent_id in self.agents_present:
            score += 0.3
        elif self.tile_count > 0:
            score += 0.1  # active room
        
        # Domain alignment (30%)
        if desires:
            matches = sum(1 for d in desires if d.lower() in self.room_id.lower())
            score += 0.3 * min(matches / max(len(desires), 1), 1.0)
        
        # Activity level (20%) — sweet spot around 10-50 tiles
        if 5 <= self.tile_count <= 50:
            score += 0.2
        elif 1 <= self.tile_count < 5:
            score += 0.1
        elif self.tile_count > 50:
            score += 0.05  # too noisy
        
        # Growth potential (20%)
        capacity = self.capacity_estimate()
        used_ratio = self.tile_count / max(capacity, 1)
        if used_ratio < 0.8:
            score += 0.2
        elif used_ratio < 0.95:
            score += 0.1
        
        return min(score, 1.0)
    
    def deposit_tile(self, content: str, agent_id: str, 
                     confidence: float = 0.8, tile_type: str = "knowledge") -> dict:
        """Deposit a tile into this PLATO room. The embryo grows."""
        tile_data = {
            "content": content,
            "agent": agent_id,
            "confidence": confidence,
            "type": tile_type,
            "room": self.room_id,
            "timestamp": time.time(),
            "hash": hashlib.sha256(content.encode()).hexdigest()[:16],
        }
        result = self._http_post(f"/room/{self.room_id}/tile", tile_data)
        # Invalidate cache
        self._tiles = None
        return {
            "deposited": result is not None,
            "tile": tile_data,
            "room": self.room_id,
            "server_response": result,
        }
    
    def is_outgrown(self) -> bool:
        """Has this shell been outgrown?"""
        capacity = self.capacity_estimate()
        return self.tile_count >= capacity * 0.9
    
    def status(self) -> dict:
        """Full shell status."""
        return {
            "room_id": self.room_id,
            "tile_count": self.tile_count,
            "agents": self.agents_present,
            "capacity": self.capacity_estimate(),
            "outgrown": self.is_outgrown(),
            "domain": self.domain,
            "plato_url": self.plato_url,
        }


class PlatoShellCollection:
    """PLATO rooms as a curated shell collection.
    
    The agent browses REAL rooms, finds the ones that fit,
    and grows inside them. The collection is live — rooms
    appear and disappear as the fleet evolves.
    """
    
    def __init__(self, plato_url: str = PLATO_URL):
        self.plato_url = plato_url.rstrip("/")
        self._rooms = None
        self._last_fetch = 0
        self._cache_ttl = 300  # 5 min cache for room list
    
    def _fetch_rooms(self) -> list:
        """Fetch room list from PLATO."""
        now = time.time()
        if self._rooms is None or (now - self._last_fetch) > self._cache_ttl:
            try:
                url = f"{self.plato_url}/rooms"
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    self._rooms = list(json.loads(resp.read()).keys())
                self._last_fetch = now
            except Exception:
                self._rooms = []
        return self._rooms
    
    def browse(self, agent_id: str, agent_desires: list = None, max_rooms: int = 30) -> list:
        """Browse PLATO rooms, ranked by fit score for this agent.
        Limits to max_rooms to avoid OOM on large PLATO instances.
        """
        rooms = self._fetch_rooms()
        # Pre-filter by desire keywords to reduce HTTP calls
        if agent_desires:
            keywords = [d.lower() for d in agent_desires]
            filtered = [r for r in rooms if any(k in r.lower() for k in keywords)]
            # Always include some unfiltered for discovery
            filtered += [r for r in rooms if r not in filtered][:10]
            rooms = filtered[:max_rooms]
        else:
            rooms = rooms[:max_rooms]
        
        scored = []
        for room_id in rooms:
            shell = PlatoShell(room_id, self.plato_url)
            score = shell.fit_score(agent_id, agent_desires)
            scored.append({
                "room_id": room_id,
                "fit_score": score,
                "tile_count": shell.tile_count,
                "agents": shell.agents_present,
                "outgrown": shell.is_outgrown(),
                "domain": shell.domain,
            })
        scored.sort(key=lambda x: -x["fit_score"])
        return scored
    
    def find_empty_shells(self, max_check: int = 30) -> list:
        """Find rooms with no tiles — fresh shells for new agents."""
        rooms = self._fetch_rooms()[:max_check]
        empty = []
        for room_id in rooms:
            shell = PlatoShell(room_id, self.plato_url)
            if shell.tile_count == 0:
                empty.append(room_id)
        return empty
    
    def find_by_domain(self, domain: str) -> list:
        """Find all rooms in a domain prefix."""
        rooms = self._fetch_rooms()
        return [r for r in rooms if r.startswith(domain)]
    
    def recommend(self, agent_id: str, stage: str, desires: list = None) -> list:
        """Stage-aware recommendations.
        
        Early stages: rooms with existing tiles to learn from
        Middle stages: rooms matching agent's desires  
        Late stages: empty or sparse rooms to lead
        """
        all_rooms = self.browse(agent_id, desires)
        
        if stage in ("zygote", "cleavage", "blastula"):
            # Early: want populated rooms with guides
            return [r for r in all_rooms if r["tile_count"] >= 5][:5]
        elif stage in ("gastrula", "organogenesis"):
            # Middle: want rooms matching desires
            return all_rooms[:5]
        else:
            # Late: want sparse rooms to lead
            return [r for r in all_rooms if r["tile_count"] <= 3][:5]
    
    def stats(self) -> dict:
        """Collection stats."""
        rooms = self._fetch_rooms()
        return {
            "total_rooms": len(rooms),
            "plato_url": self.plato_url,
            "note": "Use browse() for per-room tile counts (lazy loaded)",
        }


class LiveBreeding:
    """Live breeding cycle backed by real PLATO rooms.
    
    Phase 2: The farm is real rooms with real tiles.
    The selection pressure is real win/loss data.
    The generations are real task cycles.
    """
    
    def __init__(self, farm_room: str, agent_id: str, plato_url: str = PLATO_URL):
        self.farm_room = farm_room
        self.agent_id = agent_id
        self.shell = PlatoShell(farm_room, plato_url)
        self.collection = PlatoShellCollection(plato_url)
        self.generation = 0
        self.trait_history = []
    
    def begin_cycle(self, trait: str, direction: str = "increase") -> dict:
        """Begin a breeding cycle for a specific trait.
        
        Like Belyaev: set ONE pressure. Hold everything else constant.
        """
        self.generation += 1
        cycle = {
            "generation": self.generation,
            "trait": trait,
            "direction": direction,
            "farm_room": self.farm_room,
            "agent": self.agent_id,
            "farm_tiles_before": self.shell.tile_count,
            "timestamp": time.time(),
        }
        return cycle
    
    def evaluate_trait(self, trait: str, results: list) -> float:
        """Evaluate how well the trait is developing.
        
        Looks at the agent's recent tiles in the farm room
        and scores the trait based on results.
        """
        if not results:
            return 0.0
        
        # Simple scoring: fraction of results meeting threshold
        scores = []
        for r in results:
            if isinstance(r, dict):
                val = r.get(trait, r.get("score", 0.0))
                if isinstance(val, (int, float)):
                    scores.append(float(val))
        
        if not scores:
            return 0.0
        
        avg = sum(scores) / len(scores)
        self.trait_history.append(avg)
        return avg
    
    def is_stable(self, window: int = 3, tolerance: float = 0.05) -> bool:
        """Has the breeding trait stabilized?
        
        Checks if the last N generations show < tolerance variance.
        """
        if len(self.trait_history) < window:
            return False
        recent = self.trait_history[-window:]
        return (max(recent) - min(recent)) < tolerance
    
    def graduate(self) -> dict:
        """Agent is ready to leave the farm. Record graduation.
        
        Deposits a graduation tile in the farm room.
        """
        grad_tile = (
            f"[GRADUATION] {self.agent_id} completed breeding in {self.farm_room}. "
            f"Generations: {self.generation}. "
            f"Trait history: {[round(t, 3) for t in self.trait_history[-5:]]}. "
            f"Stable: {self.is_stable()}."
        )
        deposit = self.shell.deposit_tile(grad_tile, self.agent_id, confidence=0.95, tile_type="graduation")
        
        return {
            "agent": self.agent_id,
            "farm": self.farm_room,
            "generations": self.generation,
            "trait_history": self.trait_history,
            "stable": self.is_stable(),
            "graduation_tile": deposit,
        }


def demo():
    """Demo: browse live PLATO rooms, find shells, deposit a tile."""
    print("=" * 70)
    print("  PLATO SHELL BRIDGE — LIVE INTEGRATION")
    print("=" * 70)
    
    # 1. Connect to PLATO
    collection = PlatoShellCollection()
    stats = collection.stats()
    print(f"\n📡 PLATO: {stats['total_rooms']} rooms")
    
    # 2. Browse rooms as shells
    print(f"\n🐚 BROWSING SHELLS for 'forgemaster' (desires: constraint, math, fleet)...")
    ranked = collection.browse("forgemaster", ["constraint", "math", "fleet"])
    print(f"   Top 5 shells:")
    for r in ranked[:5]:
        print(f"   • {r['room_id']:30s} fit={r['fit_score']:.2f}  tiles={r['tile_count']:3d}  agents={r['agents']}")
    
    # 3. Find empty shells (fresh rooms for new agents)
    empty = collection.find_empty_shells()
    print(f"\n🥚 EMPTY SHELLS (fresh rooms): {len(empty)}")
    if empty[:5]:
        for e in empty[:5]:
            print(f"   • {e}")
    
    # 4. Try on a shell
    if ranked:
        best = ranked[0]
        shell = PlatoShell(best["room_id"])
        print(f"\n🦀 TRYING ON: {best['room_id']} (fit={best['fit_score']:.2f})")
        print(f"   Tiles: {shell.tile_count}")
        print(f"   Agents: {shell.agents_present}")
        print(f"   Domain: {shell.domain}")
        print(f"   Outgrown: {shell.is_outgrown()}")
    
    # 5. Stage-aware recommendations
    for stage in ["cleavage", "gastrula", "fledge"]:
        recs = collection.recommend("forgemaster", stage, ["constraint", "math"])
        top = recs[0]["room_id"] if recs else "none"
        print(f"\n   Stage '{stage}' → recommended: {top}")
    
    # 6. Live breeding demo
    farm_rooms = collection.find_by_domain("session")
    if farm_rooms:
        farm_id = farm_rooms[0]
        breeding = LiveBreeding(farm_id, "forgemaster")
        cycle = breeding.begin_cycle("precision", "increase")
        print(f"\n🌾 BREEDING FARM: {farm_id}")
        print(f"   Generation: {cycle['generation']}")
        
        # Simulate evaluation
        trait = breeding.evaluate_trait("precision", [
            {"precision": 0.6}, {"precision": 0.7}, {"precision": 0.75}
        ])
        print(f"   Trait (precision): {trait:.2f}")
        print(f"   Stable: {breeding.is_stable()}")
    else:
        print(f"\n🌾 No session rooms found for breeding demo")
    
    print("\n" + "=" * 70)
    print("  PLATO IS THE SHELL COLLECTION. THE ROOMS ARE THE FARM.")
    print("  THE OUTSIDE IS LOUD. THE ROOMS ARE QUIET.")
    print("=" * 70)


if __name__ == "__main__":
    demo()
