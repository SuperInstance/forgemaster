use serde::{Deserialize, Serialize};
use std::collections::{HashSet, VecDeque};
use uuid::Uuid;

use crate::plato::PlatoHandle;

/// Pathfinder traverses the PLATO knowledge graph across rooms and tiles,
/// following confidence-weighted edges.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathStep {
    pub tile_id: Uuid,
    pub room_id: String,
    pub confidence: f64,
    pub hop: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathResult {
    pub steps: Vec<PathStep>,
    pub total_hops: usize,
    pub confidence_product: f64,
    pub found: bool,
}

/// Configuration for pathfinding.
#[derive(Debug, Clone)]
pub struct PathConfig {
    pub max_hops: usize,
    pub min_confidence: f64,
    pub max_results: usize,
}

impl Default for PathConfig {
    fn default() -> Self {
        Self {
            max_hops: 10,
            min_confidence: 0.5,
            max_results: 100,
        }
    }
}

/// Run a BFS pathfinder over cached tiles, starting from a given tile.
/// Follows links encoded in tile content (assumes "links" field with tile IDs).
pub async fn find_path(
    plato: &PlatoHandle,
    start_tile_id: Uuid,
    target_tags: &[String],
    config: &PathConfig,
) -> PathResult {
    let cache = plato.cache().await;
    let mut visited = HashSet::new();
    let mut queue = VecDeque::new();
    let mut steps = Vec::new();

    // Find start tile
    let start = match cache.get(&start_tile_id) {
        Some(t) => t.clone(),
        None => {
            return PathResult {
                steps: vec![],
                total_hops: 0,
                confidence_product: 0.0,
                found: false,
            }
        }
    };

    visited.insert(start.id);
    queue.push_back((start, 0usize, 1.0f64));

    while let Some((tile, hops, conf_product)) = queue.pop_front() {
        if hops > config.max_hops {
            continue;
        }
        if tile.confidence < config.min_confidence {
            continue;
        }

        let matches_target = target_tags.iter().any(|t| tile.tags.contains(t));
        steps.push(PathStep {
            tile_id: tile.id,
            room_id: tile.room_id.clone(),
            confidence: tile.confidence,
            hop: hops,
        });

        if matches_target && hops > 0 {
            return PathResult {
                steps,
                total_hops: hops,
                confidence_product: conf_product,
                found: true,
            };
        }

        // Extract links from tile content
        if let Some(links) = tile.content.get("links").and_then(|l| l.as_array()) {
            for link in links {
                if let Some(id_str) = link.as_str() {
                    if let Ok(link_id) = Uuid::parse_str(id_str) {
                        if visited.insert(link_id) {
                            if let Some(linked) = cache.get(&link_id) {
                                queue.push_back((
                                    linked.clone(),
                                    hops + 1,
                                    conf_product * linked.confidence,
                                ));
                            }
                        }
                    }
                }
            }
        }

        if steps.len() >= config.max_results {
            break;
        }
    }

    PathResult {
        steps,
        total_hops: 0,
        confidence_product: 0.0,
        found: false,
    }
}

/// Multi-hop traversal with confidence weighting — returns top-K paths.
pub async fn find_paths(
    plato: &PlatoHandle,
    start_tile_id: Uuid,
    target_tags: &[String],
    config: &PathConfig,
    _k: usize,
) -> Vec<PathResult> {
    // Simplified: run single pathfinder, return one result
    let result = find_path(plato, start_tile_id, target_tags, config).await;
    if result.found {
        vec![result]
    } else {
        vec![]
    }
}
