//! LRU tile cache for PLATO sync (std feature only).

use alloc::vec::Vec;
use crate::plato::SyncGeneration;

/// A cached tile entry.
#[derive(Clone, Debug)]
pub struct CacheEntry {
    pub generation: SyncGeneration,
    pub data: Vec<u8>,
}

/// Simple LRU tile cache backed by a HashMap.
#[cfg(feature = "std")]
use std::collections::HashMap;

#[cfg(feature = "std")]
#[derive(Debug)]
pub struct TileCache {
    entries: HashMap<Vec<u8>, CacheEntry>,
    max_entries: usize,
    access_order: Vec<Vec<u8>>,
}

#[cfg(feature = "std")]
impl TileCache {
    pub fn new(max_entries: usize) -> Self {
        TileCache {
            entries: HashMap::new(),
            max_entries,
            access_order: Vec::new(),
        }
    }

    pub fn get(&mut self, room_id: &[u8]) -> Option<&CacheEntry> {
        if self.entries.contains_key(room_id) {
            // Move to front of access order
            self.access_order.retain(|k| k != room_id);
            self.access_order.push(room_id.to_vec());
            self.entries.get(room_id)
        } else {
            None
        }
    }

    pub fn insert(&mut self, room_id: Vec<u8>, generation: SyncGeneration, data: Vec<u8>) {
        if self.entries.len() >= self.max_entries && !self.entries.contains_key(&room_id) {
            // Evict oldest
            if let Some(evict_key) = self.access_order.first().cloned() {
                self.entries.remove(&evict_key);
                self.access_order.remove(0);
            }
        }
        self.access_order.retain(|k| k != &room_id);
        self.access_order.push(room_id.clone());
        self.entries.insert(room_id, CacheEntry { generation, data });
    }

    pub fn invalidate(&mut self, room_id: &[u8]) {
        self.entries.remove(room_id);
        self.access_order.retain(|k| k != room_id);
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

#[cfg(feature = "std")]
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cache_insert_get_evict() {
        let mut cache = TileCache::new(2);
        cache.insert(vec![1], SyncGeneration(1), vec![10]);
        cache.insert(vec![2], SyncGeneration(2), vec![20]);
        assert_eq!(cache.len(), 2);

        // This should evict key [1]
        cache.insert(vec![3], SyncGeneration(3), vec![30]);
        assert_eq!(cache.len(), 2);
        assert!(cache.get(&[1]).is_none());
        assert_eq!(cache.get(&[2]).unwrap().data, vec![20]);
        assert_eq!(cache.get(&[3]).unwrap().data, vec![30]);
    }

    #[test]
    fn cache_invalidate() {
        let mut cache = TileCache::new(10);
        cache.insert(vec![1], SyncGeneration(1), vec![10]);
        cache.invalidate(&[1]);
        assert!(cache.is_empty());
    }
}
