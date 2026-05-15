"""
RDTLG: Regular Division of Two-Level Graph on E12 Terrain

Adapted from tri-quarter-toolbox (Schmidt) with COCAPN-CREDITS.
Hex lattice graph with vertex/edge connectivity, hop distance,
and subdivision — for fleet knowledge terrain navigation.

Key operations:
1. Place tiles at E12 coordinates
2. Find nearest neighbors by hop distance
3. Subdivide regions for multi-resolution search
4. Navigate: find path from agent to knowledge domain
"""

import math
from dataclasses import dataclass, field
from typing import Optional

# E12 sixth roots of unity basis
# Eisenstein integer z = a + b·ω where ω = e^(2πi/12) = cos(30°) + i·sin(30°)
# In Cartesian: z = (a - b/2, b·√3/2)
SQRT3_2 = math.sqrt(3) / 2

@dataclass(frozen=True)
class E12:
    """Eisenstein integer coordinate (a, b) in Z[ζ₁₂]"""
    a: int
    b: int
    
    def to_cartesian(self):
        """Convert to (x, y) in Cartesian plane"""
        return (self.a - self.b / 2, self.b * SQRT3_2)
    
    def norm(self):
        """Eisenstein norm N(a,b) = a² - ab + b²"""
        return self.a * self.a - self.a * self.b + self.b * self.b
    
    def hex_distance(self, other):
        """Hop distance on hex lattice"""
        da = self.a - other.a
        db = self.b - other.b
        # Hex distance: max(|da|, |db|, |da+db|)
        return max(abs(da), abs(db), abs(da + db))
    
    def neighbors(self):
        """6 adjacent hex cells"""
        return [
            E12(self.a + 1, self.b),
            E12(self.a - 1, self.b),
            E12(self.a, self.b + 1),
            E12(self.a, self.b - 1),
            E12(self.a + 1, self.b - 1),
            E12(self.a - 1, self.b + 1),
        ]
    
    def __repr__(self):
        return f"E12({self.a},{self.b})"


@dataclass
class TerrainVertex:
    """A vertex in the terrain graph — represents a knowledge domain or agent position"""
    coord: E12
    label: str
    vertex_type: str  # 'agent', 'domain', 'tile', 'boundary'
    metadata: dict = field(default_factory=dict)
    
    @property
    def edges(self):
        """Edges are computed from adjacency in the graph"""
        return []  # Populated by TerrainGraph


@dataclass
class TerrainEdge:
    """Edge between two terrain vertices"""
    source: E12
    target: E12
    weight: float = 1.0
    edge_type: str = 'hop'  # 'hop', 'cross-domain', 'bridge'


class TerrainGraph:
    """
    RDTLG on E12 terrain.
    
    Levels:
      0 — coarse (single cell = whole fleet)
      1 — region (8 sectors)
      2 — domain (per-agent)
      3 — subdomain (per-project)
      4 — tile level
      5+ — atomic
    """
    
    def __init__(self):
        self.vertices: dict[E12, TerrainVertex] = {}
        self._tiles_by_level: dict[int, list[E12]] = {}
        self._adjacency: dict[E12, list[tuple[E12, float]]] = {}
    
    def add_vertex(self, coord: E12, label: str, vertex_type: str, **metadata) -> TerrainVertex:
        v = TerrainVertex(coord=coord, label=label, vertex_type=vertex_type, metadata=metadata)
        self.vertices[coord] = v
        self._adjacency[coord] = []
        return v
    
    def add_edge(self, source: E12, target: E12, weight: float = 1.0, edge_type: str = 'hop'):
        if source not in self._adjacency:
            self._adjacency[source] = []
        if target not in self._adjacency:
            self._adjacency[target] = []
        self._adjacency[source].append((target, weight))
        self._adjacency[target].append((source, weight))
    
    def neighbors(self, coord: E12, max_hops: int = 1) -> list[tuple[E12, int]]:
        """Find all vertices within max_hops, returns (coord, distance)"""
        visited = {coord: 0}
        frontier = [coord]
        for hop in range(1, max_hops + 1):
            next_frontier = []
            for c in frontier:
                for neighbor, _ in self._adjacency.get(c, []):
                    if neighbor not in visited:
                        visited[neighbor] = hop
                        next_frontier.append(neighbor)
            frontier = next_frontier
        return [(c, d) for c, d in visited.items() if d > 0]
    
    def nearest(self, coord: E12, vertex_type: str = None, count: int = 5) -> list[tuple[TerrainVertex, int]]:
        """Find nearest vertices, optionally filtered by type"""
        results = []
        # Expand search radius until we find enough
        for radius in range(1, 20):
            for c, dist in self.neighbors(coord, max_hops=radius):
                if c in self.vertices:
                    v = self.vertices[c]
                    if vertex_type is None or v.vertex_type == vertex_type:
                        results.append((v, dist))
            if len(results) >= count:
                break
        results.sort(key=lambda x: x[1])
        return results[:count]
    
    def shortest_path(self, source: E12, target: E12) -> list[E12]:
        """BFS shortest path through terrain graph"""
        from collections import deque
        if source == target:
            return [source]
        visited = {source: None}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for neighbor, _ in self._adjacency.get(current, []):
                if neighbor not in visited:
                    visited[neighbor] = current
                    if neighbor == target:
                        # Reconstruct path
                        path = []
                        node = target
                        while node is not None:
                            path.append(node)
                            node = visited[node]
                        return list(reversed(path))
                    queue.append(neighbor)
        return []  # No path found
    
    def subdivision_level(self, coord: E12) -> int:
        """What subdivision level is this coordinate at?
        Level 0: (0,0) only
        Level 1: ±1 in either axis (8 sectors)
        Level 2: ±2-3 (per-agent regions)
        Level 3+: further subdivision
        """
        return max(abs(coord.a), abs(coord.b))
    
    def subdivide(self, coord: E12, level: int = 1) -> list[E12]:
        """Subdivide a cell into 7 sub-cells (hex + 6 neighbors at finer resolution)"""
        children = [coord]
        for n in coord.neighbors():
            # Subdivide by stepping toward neighbor at half distance
            child = E12(
                coord.a + (n.a - coord.a) // (level + 1),
                coord.b + (n.b - coord.b) // (level + 1)
            )
            children.append(child)
        return children
    
    def domain_of(self, coord: E12) -> Optional[TerrainVertex]:
        """Find the domain (level-2) vertex that contains this coordinate"""
        # Snap to nearest level-2 vertex
        best = None
        best_dist = float('inf')
        for v_coord, v in self.vertices.items():
            if v.vertex_type == 'domain':
                d = coord.hex_distance(v_coord)
                if d < best_dist:
                    best_dist = d
                    best = v
        return best
    
    def terrain_weight(self, voter_coord: E12, tile_coord: E12) -> float:
        """
        Terrain-weighted voting weight (Synergy 3).
        Weight decreases with hex distance. Agents closer to the tile's
        domain get more voting weight.
        
        w = 1 / (1 + hex_distance(voter, tile))
        """
        d = voter_coord.hex_distance(tile_coord)
        return 1.0 / (1.0 + d)
    
    def stats(self) -> dict:
        """Graph statistics"""
        by_type = {}
        for v in self.vertices.values():
            by_type[v.vertex_type] = by_type.get(v.vertex_type, 0) + 1
        return {
            'total_vertices': len(self.vertices),
            'total_edges': sum(len(e) for e in self._adjacency.values()) // 2,
            'by_type': by_type,
        }


def build_fleet_terrain() -> TerrainGraph:
    """
    Build the fleet's knowledge terrain graph.
    Agents and domains placed at E12 coordinates based on capability clusters.
    """
    g = TerrainGraph()
    
    # === Agents (placed by their primary domain) ===
    agents = [
        (E12(0, 0), "Fleet Hub", "agent", {"desc": "Central coordination"}),
        (E12(3, 0), "Forgemaster", "agent", {"desc": "Constraint theory, Eisenstein math"}),
        (E12(2, 1), "Oracle1", "agent", {"desc": "Music encoding, PLATO infrastructure"}),
        (E12(5, -2), "CCC", "agent", {"desc": "Cloud ops, DevOps, infrastructure"}),
        (E12(-1, 3), "Spectra", "agent", {"desc": "Signal processing, spectra analysis"}),
        (E12(-2, -1), "Navigator", "agent", {"desc": "Route planning, pathfinding"}),
        (E12(4, 2), "Artisan", "agent", {"desc": "UI/UX, visual design, demos"}),
    ]
    
    for coord, name, vtype, meta in agents:
        g.add_vertex(coord, name, vtype, **meta)
    
    # === Domains (knowledge clusters) ===
    domains = [
        (E12(3, -1), "constraint-theory", "domain", {"parent": "Forgemaster"}),
        (E12(2, 2), "music-encoding", "domain", {"parent": "Oracle1"}),
        (E12(4, 0), "eisenstein-math", "domain", {"parent": "Forgemaster"}),
        (E12(5, -3), "infrastructure", "domain", {"parent": "CCC"}),
        (E12(-1, 4), "signal-processing", "domain", {"parent": "Spectra"}),
        (E12(1, 1), "plato-system", "domain", {"parent": "Oracle1"}),
        (E12(-3, 0), "navigation", "domain", {"parent": "Navigator"}),
        (E12(4, 3), "visual-design", "domain", {"parent": "Artisan"}),
        (E12(3, 2), "orchestration", "domain", {"parent": "shared"}),
        (E12(1, -1), "fleet-comms", "domain", {"parent": "shared"}),
    ]
    
    for coord, name, vtype, meta in domains:
        g.add_vertex(coord, name, vtype, **meta)
    
    # === Edges: connect everything within hop distance 3 ===
    coords = list(g.vertices.keys())
    for i, c1 in enumerate(coords):
        for c2 in coords[i+1:]:
            d = c1.hex_distance(c2)
            if d <= 3:
                edge_type = 'hop' if d == 1 else 'cross-domain' if d == 2 else 'bridge'
                g.add_edge(c1, c2, weight=1.0/d, edge_type=edge_type)
    
    # === Key tiles (actual knowledge artifacts) ===
    tiles = [
        (E12(3, 0), "constraint-theory-core", "tile"),
        (E12(3, -1), "eisenstein-norm-proof", "tile"),
        (E12(4, 0), "dodecet-encoder", "tile"),
        (E12(4, 0), "zero-side-info-theorem", "tile"),
        (E12(2, 1), "plato-vessel-core", "tile"),
        (E12(1, 1), "plato-room-protocol", "tile"),
        (E12(2, 2), "midi-style-tensor", "tile"),
        (E12(3, 2), "crew-plato-bridge", "tile"),
        (E12(3, 2), "verified-agent-cards", "tile"),
        (E12(5, -3), "fleet-inspector", "tile"),
        (E12(1, -1), "matrix-bridge", "tile"),
        (E12(1, -1), "fleet-registry", "tile"),
        (E12(4, 3), "narrows-demo", "tile"),
        (E12(4, 3), "landing-page", "tile"),
        (E12(-1, 4), "penrose-memory", "tile"),
        (E12(-3, 0), "rdtlg-graph", "tile"),
    ]
    
    for coord, name, vtype in tiles:
        g.add_vertex(coord, name, vtype)
    
    # Reconnect edges for tiles
    coords = list(g.vertices.keys())
    for i, c1 in enumerate(coords):
        for c2 in coords[i+1:]:
            if c2 not in g._adjacency.get(c1, []) and c1 not in g._adjacency.get(c2, []):
                d = c1.hex_distance(c2)
                if d <= 2:
                    g.add_edge(c1, c2, weight=1.0/d, edge_type='hop')
    
    return g


if __name__ == "__main__":
    terrain = build_fleet_terrain()
    print(f"Fleet Terrain: {terrain.stats()}")
    print()
    
    # Demo: Find nearest tiles to Forgemaster
    fm = E12(3, 0)
    print(f"Forgemaster at {fm}:")
    for v, dist in terrain.nearest(fm, vertex_type='tile', count=5):
        print(f"  {dist} hops → {v.label}")
    print()
    
    # Demo: Terrain-weighted voting (Synergy 3)
    print("Terrain-weighted voting on 'constraint-theory-core' tile:")
    tile = E12(3, 0)
    for agent_coord, agent in terrain.vertices.items():
        if agent.vertex_type == 'agent':
            w = terrain.terrain_weight(agent_coord, tile)
            print(f"  {agent.label}: weight={w:.3f}")
    print()
    
    # Demo: Shortest path
    print("Path from CCC to constraint-theory-core:")
    path = terrain.shortest_path(E12(5, -2), E12(3, 0))
    for p in path:
        v = terrain.vertices.get(p)
        label = v.label if v else "?"
        print(f"  {p} → {label}")
