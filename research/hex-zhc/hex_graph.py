"""Hexagonal lattice graph with Laman rigidity properties."""

from collections import deque
import random


class HexGraph:
    """Triangular lattice graph (hexagonal connectivity) using axial coordinates.
    
    Each vertex has 6 neighbors forming a triangular tiling.
    """

    # 6 neighbor offsets in axial coordinates (triangular lattice)
    UNITS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]

    def __init__(self, radius: int):
        self.radius = radius
        self._vertices = []
        self._edges = []
        self._faces = []
        self._adj = {}
        self._build()

    def _build(self):
        # Vertices: all axial hex coordinates within hex disk of given radius
        # Using cube distance: max(|q|, |r|, |q+r|) <= radius
        verts = set()
        for q in range(-self.radius, self.radius + 1):
            for r in range(-self.radius, self.radius + 1):
                s = -q - r
                if max(abs(q), abs(r), abs(s)) <= self.radius:
                    verts.add((q, r))
        self._vertices = sorted(verts)
        vert_set = set(self._vertices)

        # Build adjacency
        self._adj = {v: [] for v in self._vertices}
        edges = set()
        for v in self._vertices:
            for du, dv in self.UNITS:
                nb = (v[0] + du, v[1] + dv)
                if nb in vert_set:
                    self._adj[v].append(nb)
                    edge = tuple(sorted([v, nb]))
                    edges.add(edge)
        self._edges = sorted(edges)

        # Triangular faces: for each vertex, check all 6 consecutive
        # neighbor pairs (each pair forms an elementary triangle)
        faces = set()
        for v in self._vertices:
            for i in range(6):
                du1, dv1 = self.UNITS[i]
                du2, dv2 = self.UNITS[(i + 1) % 6]
                a = (v[0] + du1, v[1] + dv1)
                b = (v[0] + du2, v[1] + dv2)
                if a in vert_set and b in vert_set:
                    tri = tuple(sorted([v, a, b]))
                    faces.add(tri)
        self._faces = sorted(faces)

    def vertices(self) -> list:
        return self._vertices

    def edges(self) -> list:
        return self._edges

    def edge_count(self) -> int:
        return len(self._edges)

    def vertex_count(self) -> int:
        return len(self._vertices)

    def face_count(self) -> int:
        return len(self._faces)

    def check_laman(self) -> bool:
        """Verify Laman condition: |E| >= 2|V| - 3 for 2D rigidity."""
        return self.edge_count() >= 2 * self.vertex_count() - 3

    def faces(self) -> list:
        return self._faces

    def check_holonomy(self, edge_values: dict) -> bool:
        """Check that all face cycles close to identity.
        
        For each triangular face (a,b,c), verify:
            edge(a,b) + edge(b,c) + edge(c,a) = 0
        """
        for a, b, c in self._faces:
            val_ab = self._get_edge_value(edge_values, a, b)
            val_bc = self._get_edge_value(edge_values, b, c)
            val_ca = self._get_edge_value(edge_values, c, a)
            if abs(val_ab + val_bc + val_ca) > 1e-9:
                return False
        return True

    def _get_edge_value(self, edge_values: dict, u, v) -> float:
        """Get signed edge value: +val for (u,v), -val for (v,u)."""
        key = (u, v)
        if key in edge_values:
            return edge_values[key]
        rev = (v, u)
        if rev in edge_values:
            return -edge_values[rev]
        return 0.0

    def propagate_constraints(self, seed: dict) -> dict:
        """O(V) constraint propagation from seeds along spanning tree.
        
        Strategy: propagate potentials along BFS tree, then compute
        all edge values as potential differences. This guarantees
        face closure (holonomy = 0) for all triangles.
        
        1. Build spanning tree (BFS from root)
        2. Use seed edge values to set potential differences
        3. Propagate potentials: φ(child) = φ(parent) + edge_value(parent, child)
        4. Compute all edge values: edge(u,v) = φ(v) - φ(u)
        """
        if not self._vertices:
            return {}

        root = self._vertices[0]

        # BFS to get parent pointers and tree edge order
        visited = {root}
        parent = {root: None}
        order = [root]
        queue = deque([root])

        while queue:
            node = queue.popleft()
            for nb in self._adj[node]:
                if nb not in visited:
                    visited.add(nb)
                    parent[nb] = node
                    order.append(nb)
                    queue.append(nb)

        # Build a lookup for seed values (both directions)
        def get_seed(u, v):
            """Get seed value for edge u→v, or None."""
            if (u, v) in seed:
                return seed[(u, v)]
            if (v, u) in seed:
                return -seed[(v, u)]
            return None

        # Propagate potentials along tree
        potentials = {root: 0.0}
        for node in order:
            if node == root:
                continue
            p = parent[node]
            # edge from parent to node
            sv = get_seed(p, node)
            if sv is not None:
                potentials[node] = potentials[p] + sv
            else:
                # No seed for this tree edge; potential unchanged (edge value = 0)
                potentials[node] = potentials[p]

        # Compute all edge values from potentials
        edge_values = {}
        for u, v in self._edges:
            edge_values[(u, v)] = potentials[v] - potentials[u]

        return edge_values

    def generate_valid_assignment(self) -> dict:
        """Generate a valid edge assignment where all face cycles close.
        
        Uses potential function: edge(u,v) = φ(v) - φ(u)
        This guarantees all cycles close to 0.
        """
        potentials = {v: random.uniform(-10, 10) for v in self._vertices}
        edge_values = {}
        for u, v in self._edges:
            edge_values[(u, v)] = potentials[v] - potentials[u]
        return edge_values


if __name__ == "__main__":
    g = HexGraph(3)
    print(f"Radius 3: V={g.vertex_count()}, E={g.edge_count()}, F={g.face_count()}")
    print(f"3V vs E: {3 * g.vertex_count()} vs {g.edge_count()}")
    print(f"Laman satisfied: {g.check_laman()}")
    valid = g.generate_valid_assignment()
    print(f"Holonomy check (valid): {g.check_holonomy(valid)}")
