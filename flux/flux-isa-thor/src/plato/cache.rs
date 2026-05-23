use std::collections::HashMap;
use tracing::warn;
use uuid::Uuid;

use super::Tile;

/// In-memory tile cache for offline/fallback PLATO access.
/// Production would use RocksDB or sled.
#[derive(Debug)]
pub struct TileCache {
    tiles: HashMap<Uuid, Tile>,
    room_index: HashMap<String, Vec<Uuid>>,
    max_entries: usize,
}

impl TileCache {
    pub fn new(max_entries: usize) -> Self {
        Self {
            tiles: HashMap::new(),
            room_index: HashMap::new(),
            max_entries,
        }
    }

    /// Insert a tile into the cache.
    pub fn insert(&mut self, tile: Tile) {
        if self.tiles.len() >= self.max_entries {
            // Evict oldest — simplified; production would use LRU
            if let Some(oldest_id) = self.tiles.iter().min_by_key(|(_, t)| t.created_at).map(|(id, _)| *id) {
                self.remove(&oldest_id);
            }
        }
        let id = tile.id;
        let room = tile.room_id.clone();
        self.room_index.entry(room).or_default().push(id);
        self.tiles.insert(id, tile);
    }

    /// Get a tile by ID.
    pub fn get(&self, id: &Uuid) -> Option<&Tile> {
        self.tiles.get(id)
    }

    /// Get all tiles for a room.
    pub fn get_room(&self, room_id: &str) -> Vec<&Tile> {
        self.room_index
            .get(room_id)
            .map(|ids| ids.iter().filter_map(|id| self.tiles.get(id)).collect())
            .unwrap_or_default()
    }

    /// Remove a tile.
    pub fn remove(&mut self, id: &Uuid) -> Option<Tile> {
        let tile = self.tiles.remove(id)?;
        if let Some(ids) = self.room_index.get_mut(&tile.room_id) {
            ids.retain(|i| i != id);
        }
        Some(tile)
    }

    /// Total cached tiles.
    pub fn len(&self) -> usize {
        self.tiles.len()
    }

    pub fn is_empty(&self) -> bool {
        self.tiles.is_empty()
    }

    /// Clear all cached entries.
    pub fn clear(&mut self) {
        self.tiles.clear();
        self.room_index.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_tile(id: &str, room: &str) -> Tile {
        Tile {
            id: Uuid::parse_str(id).unwrap(),
            room_id: room.to_string(),
            content: serde_json::json!({"test": true}),
            confidence: 0.9,
            tags: vec!["test".into()],
            created_at: 1000,
        }
    }

    #[test]
    fn insert_and_get() {
        let mut cache = TileCache::new(100);
        let tile = make_tile("00000000-0000-0000-0000-000000000001", "room1");
        let id = tile.id;
        cache.insert(tile);
        assert!(cache.get(&id).is_some());
        assert_eq!(cache.len(), 1);
    }

    #[test]
    fn eviction() {
        let mut cache = TileCache::new(2);
        cache.insert(make_tile("00000000-0000-0000-0000-000000000001", "r1"));
        cache.insert(make_tile("00000000-0000-0000-0000-000000000002", "r1"));
        cache.insert(make_tile("00000000-0000-0000-0000-000000000003", "r2"));
        assert_eq!(cache.len(), 2);
    }
}
