"""Platonic solid vertices and snap functions."""
import numpy as np

PHI = (1 + np.sqrt(5)) / 2  # golden ratio

# ── Tetrahedron (4 vertices) ──
TETRA_VERTS = np.array([
    [1, 1, 1],
    [1, -1, -1],
    [-1, 1, -1],
    [-1, -1, 1],
], dtype=np.float64)
TETRA_VERTS /= np.linalg.norm(TETRA_VERTS[0])

# ── Cube → 6 axis-aligned directions ──
CUBE_DIRS = np.array([
    [1, 0, 0], [-1, 0, 0],
    [0, 1, 0], [0, -1, 0],
    [0, 0, 1], [0, 0, -1],
], dtype=np.float64)

# ── Octahedron (8 vertices = cube corners) ──
OCTA_VERTS = np.array([
    [s1, s2, s3]
    for s1 in (1, -1) for s2 in (1, -1) for s3 in (1, -1)
], dtype=np.float64)
OCTA_VERTS /= np.linalg.norm(OCTA_VERTS[0])

# ── Icosahedron (12 vertices, involves φ) ──
ICO_VERTS = np.array([
    [0, 1, PHI], [0, -1, PHI], [0, 1, -PHI], [0, -1, -PHI],
    [1, PHI, 0], [-1, PHI, 0], [1, -PHI, 0], [-1, -PHI, 0],
    [PHI, 0, 1], [-PHI, 0, 1], [PHI, 0, -1], [-PHI, 0, -1],
], dtype=np.float64)
ICO_VERTS /= np.linalg.norm(ICO_VERTS[0])

# ── Dodecahedron (20 vertices, involves φ) ──
# Vertices: (±1, ±1, ±1) and cyclic permutations of (0, ±1/φ, ±φ)
DODEC_VERTS = np.array(
    [[s1, s2, s3] for s1 in (1, -1) for s2 in (1, -1) for s3 in (1, -1)]
    + [[0, s1 / PHI, s2 * PHI] for s1 in (1, -1) for s2 in (1, -1)]
    + [[s1 * PHI, 0, s2 / PHI] for s1 in (1, -1) for s2 in (1, -1)]
    + [[s1 / PHI, s2 * PHI, 0] for s1 in (1, -1) for s2 in (1, -1)],
    dtype=np.float64,
)
DODEC_VERTS /= np.linalg.norm(DODEC_VERTS[0])

ALL_SOLIDS = {
    "tetrahedron": TETRA_VERTS,
    "cube": CUBE_DIRS,
    "octahedron": OCTA_VERTS,
    "dodecahedron": DODEC_VERTS,
    "icosahedron": ICO_VERTS,
}


def snap_to_nearest(vecs: np.ndarray, vertices: np.ndarray) -> np.ndarray:
    """Snap unit vectors to nearest vertex. vecs: (N, 3), vertices: (K, 3)."""
    # Normalize input
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    unit = vecs / norms
    # Dot product with all vertices → closest
    dots = unit @ vertices.T  # (N, K)
    nearest = np.argmax(dots, axis=1)
    return vertices[nearest]


def snap_preserve_magnitude(vecs: np.ndarray, vertices: np.ndarray) -> np.ndarray:
    """Snap direction but preserve original magnitude."""
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms_safe = np.where(norms < 1e-12, 1.0, norms)
    unit = vecs / norms_safe
    dots = unit @ vertices.T
    nearest = np.argmax(dots, axis=1)
    return vertices[nearest] * norms
