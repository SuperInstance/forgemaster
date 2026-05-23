use rayon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::tile::{Tile, TileHash};

/// A PLATO room — a named collection of tiles within a domain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Room {
    pub id: String,
    pub domain: String,
    pub tiles: Vec<Tile>,
    pub created_at: i64,
    /// Map of content hash -> tile index for dedup lookups
    #[serde(skip)]
    pub hash_index: Vec<(TileHash, usize)>,
}

impl Room {
    pub fn new(id: impl Into<String>, domain: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            domain: domain.into(),
            tiles: Vec::new(),
            created_at: chrono::Utc::now().timestamp(),
            hash_index: Vec::new(),
        }
    }

    /// Number of tiles in this room.
    pub fn tile_count(&self) -> usize {
        self.tiles.len()
    }

    /// Check if a tile with the given content hash already exists.
    pub fn has_tile_hash(&self, hash: &str) -> bool {
        self.hash_index.par_iter().any(|(h, _)| h == hash)
    }

    /// Insert a tile. Returns false if duplicate (same content hash).
    pub fn insert_tile(&mut self, tile: Tile) -> bool {
        let hash = tile.content_hash();
        if self.has_tile_hash(&hash) {
            return false;
        }
        let idx = self.tiles.len();
        self.hash_index.push((hash, idx));
        self.tiles.push(tile);
        true
    }

    /// Find tile by content hash.
    pub fn find_by_hash(&self, hash: &str) -> Option<&Tile> {
        self.hash_index
            .par_iter()
            .find_map_any(|(h, idx)| {
                if h == hash {
                    Some(*idx)
                } else {
                    None
                }
            })
            .map(|idx| &self.tiles[idx])
    }

    /// Query tiles by tag (case-insensitive substring match).
    pub fn query_by_tag(&self, tag: &str) -> Vec<&Tile> {
        let tag_lower = tag.to_lowercase();
        self.tiles
            .par_iter()
            .filter(|t| {
                t.tags
                    .iter()
                    .any(|t_tag| t_tag.to_lowercase().contains(&tag_lower))
            })
            .collect()
    }

    /// Get all unique tags in this room.
    pub fn all_tags(&self) -> Vec<String> {
        let mut tags: Vec<String> = self
            .tiles
            .par_iter()
            .flat_map(|t| t.tags.clone())
            .collect();
        tags.sort();
        tags.dedup();
        tags
    }

    /// Room statistics.
    pub fn stats(&self) -> RoomStats {
        let avg_confidence = if self.tiles.is_empty() {
            0.0
        } else {
            self.tiles.par_iter().map(|t| t.confidence).sum::<f64>() / self.tiles.len() as f64
        };
        RoomStats {
            id: self.id.clone(),
            domain: self.domain.clone(),
            tile_count: self.tiles.len(),
            tag_count: self.all_tags().len(),
            avg_confidence,
            created_at: self.created_at,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoomStats {
    pub id: String,
    pub domain: String,
    pub tile_count: usize,
    pub tag_count: usize,
    pub avg_confidence: f64,
    pub created_at: i64,
}
