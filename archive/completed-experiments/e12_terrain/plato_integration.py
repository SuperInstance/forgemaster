"""
E12 Terrain → PLATO Integration Layer

Connects the RDTLG graph to PLATO rooms for fleet use.
Agents can query terrain position, find neighbors, and get 
terrain-weighted voting scores via PLATO tiles.

Usage in fleet agents:
  from e12_terrain.plato_integration import FleetTerrain
  
  terrain = FleetTerrain()
  my_pos = terrain.get_position("Forgemaster")
  nearest = terrain.find_tiles(my_pos, domain="constraint-theory", count=5)
  weight = terrain.vote_weight("Forgemaster", tile_coord)
"""

import sys
sys.path.insert(0, '/home/phoenix/.openclaw/workspace')
from e12_terrain.rdtlg import TerrainGraph, E12, build_fleet_terrain
import json

class FleetTerrain:
    """Fleet terrain backed by E12 coordinates and PLATO room metadata."""
    
    def __init__(self):
        self.graph = build_fleet_terrain()
        self._agent_index = {}  # name → E12
        self._domain_index = {}  # domain → E12
        
        for coord, v in self.graph.vertices.items():
            if v.vertex_type == "agent":
                self._agent_index[v.label] = coord
            elif v.vertex_type == "domain":
                self._domain_index[v.label] = coord
    
    def get_position(self, agent_name: str) -> E12:
        """Get an agent's terrain position"""
        return self._agent_index.get(agent_name, E12(0, 0))
    
    def get_domain(self, domain_name: str) -> E12:
        """Get a domain's center coordinate"""
        return self._domain_index.get(domain_name, E12(0, 0))
    
    def find_tiles(self, from_coord: E12, domain: str = None, count: int = 5):
        """Find nearest tiles, optionally filtered by domain"""
        results = []
        for coord, v in self.graph.vertices.items():
            if v.vertex_type != "tile":
                continue
            if domain and v.metadata.get("domain") != domain:
                continue
            d = from_coord.hex_distance(coord)
            results.append({"label": v.label, "coord": str(coord), "distance": d})
        results.sort(key=lambda x: x["distance"])
        return results[:count]
    
    def find_agents_near(self, domain: str, max_hops: int = 3):
        """Find agents within max_hops of a domain"""
        domain_coord = self.get_domain(domain)
        results = []
        for name, coord in self._agent_index.items():
            d = domain_coord.hex_distance(coord)
            if d <= max_hops:
                results.append({"agent": name, "distance": d, "weight": 1.0/(1+d)})
        results.sort(key=lambda x: x["distance"])
        return results
    
    def vote_weight(self, agent_name: str, tile_coord: E12) -> float:
        """Terrain-weighted voting weight for an agent on a tile"""
        agent_coord = self.get_position(agent_name)
        return self.graph.terrain_weight(agent_coord, tile_coord)
    
    def vote_on_claim(self, agent_name: str, tile_label: str) -> dict:
        """Get voting context for an agent on a specific tile"""
        # Find tile
        tile_coord = None
        for coord, v in self.graph.vertices.items():
            if v.label == tile_label:
                tile_coord = coord
                break
        
        if not tile_coord:
            return {"error": f"Tile '{tile_label}' not found"}
        
        agent_coord = self.get_position(agent_name)
        domain = self.graph.domain_of(tile_coord)
        
        return {
            "agent": agent_name,
            "agent_position": str(agent_coord),
            "tile": tile_label,
            "tile_position": str(tile_coord),
            "terrain_distance": agent_coord.hex_distance(tile_coord),
            "vote_weight": self.vote_weight(agent_name, tile_coord),
            "nearest_domain": domain.label if domain else "unknown",
        }
    
    def route_request(self, from_agent: str, to_domain: str) -> list:
        """Find the routing path from an agent to a knowledge domain"""
        from_coord = self.get_position(from_agent)
        to_coord = self.get_domain(to_domain)
        path = self.graph.shortest_path(from_coord, to_coord)
        return [
            {"coord": str(p), "label": self.graph.vertices.get(p, type('', (), {'label': '?'})()).label}
            for p in path
        ]
    
    def terrain_report(self) -> dict:
        """Full terrain state for fleet status"""
        return {
            "agents": {name: {"coord": str(c), "norm": c.norm()} for name, c in self._agent_index.items()},
            "domains": {name: {"coord": str(c)} for name, c in self._domain_index.items()},
            "stats": self.graph.stats(),
        }


if __name__ == "__main__":
    terrain = FleetTerrain()
    
    print("=== Fleet Terrain Report ===")
    report = terrain.terrain_report()
    print(json.dumps(report, indent=2))
    print()
    
    print("=== Forgemaster's Nearest Tiles ===")
    fm = terrain.get_position("Forgemaster")
    for t in terrain.find_tiles(fm, count=5):
        print(f"  {t['distance']} hops → {t['label']}")
    print()
    
    print("=== Agents Near constraint-theory ===")
    for a in terrain.find_agents_near("constraint-theory", max_hops=3):
        print(f"  {a['agent']}: dist={a['distance']}, weight={a['weight']:.2f}")
    print()
    
    print("=== Vote Context: Forgemaster on zero-side-info-theorem ===")
    ctx = terrain.vote_on_claim("Forgemaster", "zero-side-info-theorem")
    print(json.dumps(ctx, indent=2))
    print()
    
    print("=== Route: CCC → constraint-theory ===")
    for step in terrain.route_request("CCC", "constraint-theory"):
        print(f"  {step['coord']} → {step['label']}")
