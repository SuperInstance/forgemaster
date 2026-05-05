use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet, VecDeque};

use crate::engine::PlatoEngine;

/// A hop between rooms in a path.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoomHop {
    pub from: String,
    pub to: String,
    pub strength: f64, // confidence-weighted connection strength
    pub shared_tags: Vec<String>,
}

/// Build an adjacency graph from room tile cross-references.
/// Two rooms are connected if they share tags or domain.
fn build_adjacency(engine: &PlatoEngine) -> HashMap<String, Vec<(String, f64, Vec<String>)>> {
    let rooms: Vec<(String, Vec<String>, String)> = engine
        .list_rooms(None)
        .into_iter()
        .filter_map(|id| {
            let room = engine.get_room(&id)?;
            let tags = room.all_tags();
            Some((id, tags, room.domain.clone()))
        })
        .collect();

    let mut graph: HashMap<String, Vec<(String, f64, Vec<String>)>> = HashMap::new();

    // O(n²) pairwise comparison — fine for typical PLATO room counts
    for i in 0..rooms.len() {
        for j in (i + 1)..rooms.len() {
            let (ref id_a, ref tags_a, ref domain_a) = rooms[i];
            let (ref id_b, ref tags_b, ref domain_b) = rooms[j];

            // Find shared tags
            let set_a: HashSet<&str> = tags_a.iter().map(|s| s.as_str()).collect();
            let set_b: HashSet<&str> = tags_b.iter().map(|s| s.as_str()).collect();
            let shared: Vec<String> = set_a
                .intersection(&set_b)
                .map(|s| s.to_string())
                .collect();

            // Also connect if same domain
            let same_domain = domain_a == domain_b;

            if !shared.is_empty() || same_domain {
                // Strength = shared tags + domain bonus, normalized
                let strength = (shared.len() as f64) + if same_domain { 0.5 } else { 0.0 };

                graph.entry(id_a.clone())
                    .or_default()
                    .push((id_b.clone(), strength, shared.clone()));
                graph.entry(id_b.clone())
                    .or_default()
                    .push((id_a.clone(), strength, shared));
            }
        }
    }

    graph
}

/// Pathfinder — finds paths between rooms through tile cross-references.
pub struct Pathfinder<'a> {
    engine: &'a PlatoEngine,
    graph: HashMap<String, Vec<(String, f64, Vec<String>)>>,
}

impl<'a> Pathfinder<'a> {
    pub fn new(engine: &'a PlatoEngine) -> Self {
        let graph = build_adjacency(engine);
        Self { engine, graph }
    }

    /// Get neighboring rooms (connected by shared tags/domain).
    pub fn neighbors(&self, room_id: &str) -> Vec<String> {
        self.graph
            .get(room_id)
            .map(|edges| edges.iter().map(|(id, _, _)| id.clone()).collect())
            .unwrap_or_default()
    }

    /// Find a path between two rooms using BFS (shortest path).
    pub fn find_path(&self, from: &str, to: &str, max_hops: usize) -> Vec<RoomHop> {
        if from == to {
            return Vec::new();
        }

        let mut visited: HashSet<String> = HashSet::new();
        visited.insert(from.to_string());

        // BFS queue: (current_room, path_so_far)
        let mut queue: VecDeque<(String, Vec<RoomHop>)> = VecDeque::new();
        queue.push_back((from.to_string(), Vec::new()));

        while let Some((current, path)) = queue.pop_front() {
            if path.len() >= max_hops {
                continue;
            }

            if let Some(edges) = self.graph.get(&current) {
                for (neighbor, strength, shared_tags) in edges {
                    if visited.contains(neighbor) {
                        continue;
                    }

                    let hop = RoomHop {
                        from: current.clone(),
                        to: neighbor.clone(),
                        strength: *strength,
                        shared_tags: shared_tags.clone(),
                    };

                    let mut new_path = path.clone();
                    new_path.push(hop);

                    if neighbor == to {
                        return new_path;
                    }

                    visited.insert(neighbor.clone());
                    queue.push_back((neighbor.clone(), new_path));
                }
            }
        }

        Vec::new() // No path found
    }

    /// DFS traversal from a starting room up to a given depth.
    pub fn traverse(&self, from: &str, max_depth: usize) -> Vec<RoomHop> {
        let mut visited: HashSet<String> = HashSet::new();
        visited.insert(from.to_string());
        let mut result = Vec::new();
        self._dfs(from, 0, max_depth, &mut visited, &mut result);
        result
    }

    fn _dfs(
        &self,
        current: &str,
        depth: usize,
        max_depth: usize,
        visited: &mut HashSet<String>,
        result: &mut Vec<RoomHop>,
    ) {
        if depth >= max_depth {
            return;
        }

        if let Some(edges) = self.graph.get(current) {
            // Sort by strength descending for DFS (explore strongest connections first)
            let mut edges: Vec<_> = edges.iter().collect();
            edges.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

            for (neighbor, strength, shared_tags) in edges {
                if visited.contains(neighbor) {
                    continue;
                }

                let hop = RoomHop {
                    from: current.to_string(),
                    to: neighbor.clone(),
                    strength: *strength,
                    shared_tags: shared_tags.clone(),
                };
                result.push(hop);
                visited.insert(neighbor.clone());

                self._dfs(neighbor, depth + 1, max_depth, visited, result);
            }
        }
    }
}
