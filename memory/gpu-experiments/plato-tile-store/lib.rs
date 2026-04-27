//! # plato-tile-store
//!
//! In-memory tile storage with room-based indexing for PLATO.

use std::collections::HashMap;

/// A stored PLATO tile.
#[derive(Debug, Clone)]
pub struct Tile {
    pub id: u64,
    pub room: String,
    pub question: String,
    pub answer: String,
    pub agent: String,
}

/// In-memory tile store with room indexing.
pub struct TileStore {
    tiles: HashMap<u64, Tile>,
    rooms: HashMap<String, Vec<u64>>,
    next_id: u64,
}

impl TileStore {
    pub fn new() -> Self {
        TileStore { tiles: HashMap::new(), rooms: HashMap::new(), next_id: 1 }
    }
    
    pub fn insert(&mut self, room: &str, question: &str, answer: &str, agent: &str) -> u64 {
        let id = self.next_id;
        self.next_id += 1;
        self.tiles.insert(id, Tile {
            id, room: room.to_string(),
            question: question.to_string(), answer: answer.to_string(),
            agent: agent.to_string(),
        });
        self.rooms.entry(room.to_string()).or_default().push(id);
        id
    }
    
    pub fn get(&self, id: u64) -> Option<&Tile> { self.tiles.get(&id) }
    
    pub fn get_room(&self, room: &str) -> Vec<&Tile> {
        self.rooms.get(room).map(|ids| ids.iter().filter_map(|&id| self.tiles.get(&id)).collect()).unwrap_or_default()
    }
    
    pub fn room_count(&self, room: &str) -> usize {
        self.rooms.get(room).map(|ids| ids.len()).unwrap_or(0)
    }
    
    pub fn room_names(&self) -> Vec<&str> {
        self.rooms.keys().map(|s| s.as_str()).collect()
    }
    
    pub fn len(&self) -> usize { self.tiles.len() }
    pub fn is_empty(&self) -> bool { self.tiles.is_empty() }
    
    /// Search tiles by keyword in question or answer.
    pub fn search(&self, keyword: &str) -> Vec<&Tile> {
        let kw = keyword.to_lowercase();
        self.tiles.values()
            .filter(|t| t.question.to_lowercase().contains(&kw) || t.answer.to_lowercase().contains(&kw))
            .collect()
    }
}

impl Default for TileStore { fn default() -> Self { Self::new() } }

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_insert_and_get() {
        let mut store = TileStore::new();
        let id = store.insert("ct", "What is snap?", "It maps angles to triples.", "forgemaster");
        let tile = store.get(id).unwrap();
        assert_eq!(tile.room, "ct");
        assert_eq!(tile.question, "What is snap?");
    }
    
    #[test]
    fn test_room_indexing() {
        let mut store = TileStore::new();
        store.insert("ct", "Q1", "A1", "agent1");
        store.insert("ct", "Q2", "A2", "agent1");
        store.insert("math", "Q3", "A3", "agent2");
        
        assert_eq!(store.room_count("ct"), 2);
        assert_eq!(store.room_count("math"), 1);
        assert_eq!(store.len(), 3);
    }
    
    #[test]
    fn test_search() {
        let mut store = TileStore::new();
        store.insert("ct", "What is Pythagorean snap?", "Maps angles to triples.", "fm");
        store.insert("ct", "What is holonomy?", "Angular deficit on manifold.", "fm");
        
        let results = store.search("Pythagorean");
        assert_eq!(results.len(), 1);
        
        let results = store.search("manifold");
        assert_eq!(results.len(), 1);
    }
}
