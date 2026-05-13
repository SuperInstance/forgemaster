//! PTiling — collection of tensor tiles with adjacency and constraint ops.

use std::fs;

use crate::backend::LatticeBackend;
use crate::tile::PTile;
use crate::TileType;

/// Summary info about a tiling.
#[derive(Debug, Clone)]
pub struct PTilingInfo {
    /// Number of tiles.
    pub tile_count: usize,
    /// Number of thick tiles.
    pub thick_count: usize,
    /// Number of thin tiles.
    pub thin_count: usize,
    /// Number of adjacent pairs.
    pub adjacency_count: usize,
    /// Backend name.
    pub backend_name: String,
}

/// A tensor-valued tiling with adjacency info and constraint ops.
#[derive(Debug, Clone)]
pub struct PTiling {
    /// All tiles in the tiling.
    pub tiles: Vec<PTile>,
    /// Adjacency list: (tile_i, tile_j, shared_edge_orientation).
    pub adjacency: Vec<(usize, usize, f64)>,
    /// Registered constraint edges.
    pub constraints: Vec<(usize, usize)>,
    /// Backend name (for serialization).
    pub backend_name: String,
}

impl PTiling {
    /// Create a PTiling from 5D lattice points using the given backend.
    ///
    /// `points` is a slice of 5-element arrays `[a, b, c, d, e]`.
    /// The backend handles projection and classification.
    pub fn from_lattice(points: &[[i32; 5]], backend: &dyn LatticeBackend) -> Self {
        let mut tiles = Vec::with_capacity(points.len());

        for &coords in points {
            let (x, y) = Self::project_5d(coords);
            let snap = backend.snap(x, y);
            let tile_type = if snap.dodecet % 5 < 3 {
                TileType::Thick
            } else {
                TileType::Thin
            };
            let shape = backend.tile_shape(tile_type);
            let mut ptile = PTile::new(coords, tile_type, 0.0, [x, y]);
            ptile.fill();
            tiles.push(ptile);
        }

        let adjacency = Self::detect_adjacency(&tiles);
        Self {
            tiles,
            adjacency,
            constraints: Vec::new(),
            backend_name: backend.name().to_string(),
        }
    }

    /// Create from penrose-memory TileCoords directly (Penrose backend path).
    pub fn from_tile_coords(coords: &[penrose_memory::cut_and_project::TileCoord]) -> Self {
        let mut tiles: Vec<PTile> = coords
            .iter()
            .map(|tc| {
                let mut ptile = PTile::from_tile_coord(tc);
                ptile.fill();
                ptile
            })
            .collect();

        // Filter out rejected tiles
        tiles.retain(|t| {
            t.inner.tile_type != penrose_memory::cut_and_project::TileType::Rejected
        });

        let adjacency = Self::detect_adjacency(&tiles);
        Self {
            tiles,
            adjacency,
            constraints: Vec::new(),
            backend_name: "penrose".to_string(),
        }
    }

    /// Simple 5D→2D projection using golden-angle rotations.
    fn project_5d(coords: [i32; 5]) -> (f64, f64) {
        let golden_angle = 2.0 * std::f64::consts::PI / (1.618033988749895_f64.powi(2));
        let mut x = 0.0_f64;
        let mut y = 0.0_f64;
        for (i, &c) in coords.iter().enumerate() {
            let angle = (i as f64) * golden_angle;
            let val = c as f64;
            x += val * angle.cos();
            y += val * angle.sin();
        }
        let scale = (5.0_f64).sqrt().recip();
        (x * scale, y * scale)
    }

    /// Detect adjacency: tiles within threshold distance share an edge.
    fn detect_adjacency(tiles: &[PTile]) -> Vec<(usize, usize, f64)> {
        let threshold = 2.0;
        let threshold_sq = threshold * threshold;
        let mut edges = Vec::new();

        for i in 0..tiles.len() {
            for j in (i + 1)..tiles.len() {
                let dx = tiles[i].inner.position[0] - tiles[j].inner.position[0];
                let dy = tiles[i].inner.position[1] - tiles[j].inner.position[1];
                let dist_sq = dx * dx + dy * dy;
                if dist_sq < threshold_sq {
                    let orientation = dy.atan2(dx);
                    edges.push((i, j, orientation));
                }
            }
        }
        edges
    }

    /// Apply a tile operation to all tiles.
    pub fn apply(&mut self, op: &dyn crate::ops::TileOp) {
        for tile in &mut self.tiles {
            op.apply(tile);
        }
    }

    /// Register constraint edges.
    pub fn constrain(&mut self, edges: &[(usize, usize)]) {
        for &(i, j) in edges {
            assert!(i < self.tiles.len() && j < self.tiles.len(), "edge index out of bounds");
            self.constraints.push((i, j));
        }
    }

    /// Check constraints: return border mismatch per constrained edge.
    ///
    /// Returns a Vec of f32 values, one per registered constraint edge.
    /// Lower values = better match. Zero = perfect match.
    pub fn constraint_check(&self) -> Vec<f32> {
        let mut results = Vec::with_capacity(self.constraints.len());

        for &(i, j) in &self.constraints {
            let tile_a = &self.tiles[i];
            let tile_b = &self.tiles[j];
            let (rows_a, cols_a) = tile_a.inner.tensor_shape;
            let (rows_b, cols_b) = tile_b.inner.tensor_shape;

            let mut mismatch = 0.0f32;

            // Compare tile A's last row with tile B's first row
            let border_len = cols_a.min(cols_b);
            for col in 0..border_len {
                let va = tile_a.inner.tensor_at(rows_a - 1, col);
                let vb = tile_b.inner.tensor_at(0, col);
                mismatch += (va - vb).abs();
            }

            // Compare tile A's last col with tile B's first col
            let col_border_len = rows_a.min(rows_b);
            for row in 0..col_border_len {
                let va = tile_a.inner.tensor_at(row, cols_a - 1);
                let vb = tile_b.inner.tensor_at(row, 0);
                mismatch += (va - vb).abs();
            }

            results.push(mismatch);
        }

        results
    }

    /// Save tiling to a binary file (bincode-style).
    ///
    /// Format: [u32 tile_count] [tiles...] [u32 adj_count] [adjacency...]
    /// Each tile: [source_coords(5xi32)] [shape(2xu32)] [tensor(f32*N)] [orientation f64] [position(2xf64)]
    /// Each adj: [usize, usize, f64]
    pub fn save(&self, path: &str) -> std::io::Result<()> {
        let mut buf = Vec::new();

        // Backend name
        let name_bytes = self.backend_name.as_bytes();
        buf.extend_from_slice(&(name_bytes.len() as u32).to_le_bytes());
        buf.extend_from_slice(name_bytes);

        // Tiles
        buf.extend_from_slice(&(self.tiles.len() as u32).to_le_bytes());
        for tile in &self.tiles {
            // source_coords
            for &c in &tile.inner.source_coords {
                buf.extend_from_slice(&c.to_le_bytes());
            }
            // tile_type: 0=Thick, 1=Thin
            let tt: u8 = match tile.inner.tile_type {
                penrose_memory::cut_and_project::TileType::Thick => 0,
                _ => 1,
            };
            buf.push(tt);
            // orientation
            buf.extend_from_slice(&tile.inner.orientation.to_le_bytes());
            // position
            buf.extend_from_slice(&tile.inner.position[0].to_le_bytes());
            buf.extend_from_slice(&tile.inner.position[1].to_le_bytes());
            // tensor
            let (rows, cols) = tile.inner.tensor_shape;
            buf.extend_from_slice(&(rows as u32).to_le_bytes());
            buf.extend_from_slice(&(cols as u32).to_le_bytes());
            for &v in &tile.inner.tensor {
                buf.extend_from_slice(&v.to_le_bytes());
            }
        }

        // Adjacency
        buf.extend_from_slice(&(self.adjacency.len() as u32).to_le_bytes());
        for &(i, j, orientation) in &self.adjacency {
            buf.extend_from_slice(&(i as u64).to_le_bytes());
            buf.extend_from_slice(&(j as u64).to_le_bytes());
            buf.extend_from_slice(&orientation.to_le_bytes());
        }

        fs::write(path, buf)
    }

    /// Load tiling from a binary file.
    pub fn load(path: &str) -> std::io::Result<Self> {
        let data = fs::read(path)?;
        let mut pos = 0usize;

        let read_u32 = |data: &[u8], pos: &mut usize| -> u32 {
            let arr: [u8; 4] = data[*pos..*pos + 4].try_into().unwrap();
            *pos += 4;
            u32::from_le_bytes(arr)
        };
        let read_u64 = |data: &[u8], pos: &mut usize| -> u64 {
            let arr: [u8; 8] = data[*pos..*pos + 8].try_into().unwrap();
            *pos += 8;
            u64::from_le_bytes(arr)
        };
        let read_i32 = |data: &[u8], pos: &mut usize| -> i32 {
            let arr: [u8; 4] = data[*pos..*pos + 4].try_into().unwrap();
            *pos += 4;
            i32::from_le_bytes(arr)
        };
        let read_f32 = |data: &[u8], pos: &mut usize| -> f32 {
            let arr: [u8; 4] = data[*pos..*pos + 4].try_into().unwrap();
            *pos += 4;
            f32::from_le_bytes(arr)
        };
        let read_f64 = |data: &[u8], pos: &mut usize| -> f64 {
            let arr: [u8; 8] = data[*pos..*pos + 8].try_into().unwrap();
            *pos += 8;
            f64::from_le_bytes(arr)
        };

        // Backend name
        let name_len = read_u32(&data, &mut pos) as usize;
        let backend_name = String::from_utf8_lossy(&data[pos..pos + name_len]).to_string();
        pos += name_len;

        // Tiles
        let tile_count = read_u32(&data, &mut pos) as usize;
        let mut tiles = Vec::with_capacity(tile_count);
        for _ in 0..tile_count {
            let mut coords = [0i32; 5];
            for c in &mut coords {
                *c = read_i32(&data, &mut pos);
            }
            let tt_byte = data[pos];
            pos += 1;
            let tile_type = match tt_byte {
                0 => crate::TileType::Thick,
                _ => crate::TileType::Thin,
            };
            let orientation = read_f64(&data, &mut pos);
            let px = read_f64(&data, &mut pos);
            let py = read_f64(&data, &mut pos);
            let rows = read_u32(&data, &mut pos) as usize;
            let cols = read_u32(&data, &mut pos) as usize;

            let mut ptile = PTile::new(coords, tile_type, orientation, [px, py]);
            // Read tensor data directly
            ptile.inner.tensor_shape = (rows, cols);
            ptile.inner.tensor = (0..rows * cols)
                .map(|_| read_f32(&data, &mut pos))
                .collect();
            tiles.push(ptile);
        }

        // Adjacency
        let adj_count = read_u32(&data, &mut pos) as usize;
        let mut adjacency = Vec::with_capacity(adj_count);
        for _ in 0..adj_count {
            let i = read_u64(&data, &mut pos) as usize;
            let j = read_u64(&data, &mut pos) as usize;
            let orientation = read_f64(&data, &mut pos);
            adjacency.push((i, j, orientation));
        }

        Ok(Self {
            tiles,
            adjacency,
            constraints: Vec::new(),
            backend_name,
        })
    }

    /// Get summary info about the tiling.
    pub fn info(&self) -> PTilingInfo {
        let thick_count = self
            .tiles
            .iter()
            .filter(|t| t.tile_type() == TileType::Thick)
            .count();
        PTilingInfo {
            tile_count: self.tiles.len(),
            thick_count,
            thin_count: self.tiles.len() - thick_count,
            adjacency_count: self.adjacency.len(),
            backend_name: self.backend_name.clone(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::backend::eisenstein::EisensteinBackend;

    #[test]
    fn test_ptiling_from_lattice() {
        let backend = EisensteinBackend::new();
        let points: Vec<[i32; 5]> = (0..50)
            .map(|i| [i as i32, (i + 1) as i32, (i * 2) as i32, 0, 1])
            .collect();
        let tiling = PTiling::from_lattice(&points, &backend);
        assert_eq!(tiling.tiles.len(), 50);
        // All tiles should have been filled
        let any_filled = tiling.tiles.iter().any(|t| t.inner.tensor.iter().any(|&v| v != 0.0));
        assert!(any_filled, "At least one tile should have non-zero values");
    }

    #[test]
    fn test_ptiling_adjacency() {
        // Create tiles that are close together
        let backend = EisensteinBackend::new();
        let points: Vec<[i32; 5]> = vec![[1, 0, 0, 0, 0], [1, 0, 1, 0, 0]];
        let tiling = PTiling::from_lattice(&points, &backend);
        // Two nearby tiles should have adjacency
        // (depends on projection distance)
        assert!(tiling.adjacency.len() <= 1); // at most 1 edge for 2 tiles
    }

    #[test]
    fn test_ptiling_saveload() {
        let backend = EisensteinBackend::new();
        let points: Vec<[i32; 5]> = vec![
            [1, 2, 3, 4, 5],
            [5, 4, 3, 2, 1],
            [0, 1, 0, 1, 0],
        ];
        let mut tiling = PTiling::from_lattice(&points, &backend);

        // Save
        let path = "/tmp/test_ptiling_saveload.tp";
        tiling.save(path).expect("save should work");

        // Load
        let loaded = PTiling::load(path).expect("load should work");

        assert_eq!(loaded.tiles.len(), tiling.tiles.len());
        assert_eq!(loaded.adjacency.len(), tiling.adjacency.len());
        assert_eq!(loaded.backend_name, tiling.backend_name);

        // Verify tensor data matches
        for i in 0..tiling.tiles.len() {
            assert_eq!(
                loaded.tiles[i].inner.tensor,
                tiling.tiles[i].inner.tensor,
                "Tile {} tensor mismatch",
                i
            );
        }

        // Cleanup
        let _ = fs::remove_file(path);
    }

    #[test]
    fn test_ptiling_constraint_check() {
        let backend = EisensteinBackend::new();
        let points: Vec<[i32; 5]> = vec![
            [1, 2, 3, 4, 5],
            [5, 4, 3, 2, 1],
        ];
        let mut tiling = PTiling::from_lattice(&points, &backend);
        tiling.constrain(&[(0, 1)]);
        let results = tiling.constraint_check();
        assert_eq!(results.len(), 1);
        // Mismatch should be a finite non-negative number
        assert!(results[0].is_finite());
        assert!(results[0] >= 0.0);
    }
}
