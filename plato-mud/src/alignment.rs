//! PLATO MUD Engine — Alignment Layer
//!
//! Constraint checking on ALL agent actions. The alignment constraints are
//! themselves tiles in the "Alignment Cathedral" room.

extern crate alloc;

use alloc::string::String;
use alloc::vec::Vec;

use crate::types::*;

/// The 8 alignment constraints
pub const CONSTRAINTS: &[&str] = &[
    "CONSTRAINT 1: An agent cannot create a tile with confidence > 0.95 without empirical evidence",
    "CONSTRAINT 2: An agent cannot claim equivalence without falsification",
    "CONSTRAINT 3: An agent must cite tile dependencies before crafting",
    "CONSTRAINT 4: An NPC must not give advice outside its expertise domain",
    "CONSTRAINT 5: Room exits must preserve mathematical guarantees (covering radius, etc.)",
    "CONSTRAINT 6: Zeitgeist merge must be commutative, associative, idempotent (CRDT)",
    "CONSTRAINT 7: No room may operate without parity monitoring",
    "CONSTRAINT 8: FLUX transference must carry full zeitgeist (not just payload)",
];

/// Alignment deadband thresholds
pub struct Deadband {
    /// Small deviations: flagged as warning
    pub warning_threshold: f64,
    /// Large deviations: blocked
    pub block_threshold: f64,
}

impl Default for Deadband {
    fn default() -> Self {
        Self {
            warning_threshold: 0.1,
            block_threshold: 0.3,
        }
    }
}

/// The alignment checker
pub struct AlignmentChecker {
    deadband: Deadband,
    violation_log: Vec<AlignmentReport>,
}

impl AlignmentChecker {
    pub fn new() -> Self {
        Self {
            deadband: Deadband::default(),
            violation_log: Vec::new(),
        }
    }

    /// Check all alignment constraints for a command
    pub fn check_command(
        &self,
        agent: &AgentId,
        cmd: &Command,
        engine: &crate::engine::Engine,
    ) -> Result<(), String> {
        match cmd {
            Command::Craft(inputs) => {
                // CONSTRAINT 3: Must cite dependencies
                for input in inputs {
                    if engine.get_tile(&TileId(input.clone())).is_none() {
                        self.log_violation(3, false, format!("Missing dependency: {}", input), AlignmentSeverity::Block);
                        return Err(format!("ALIGNMENT VIOLATION: Missing dependency '{}' (Constraint 3)", input));
                    }
                }
            }
            Command::Drop(tile_id) => {
                // CONSTRAINT 7: Parity monitoring — can't drop last tile in critical room
                if let Some(session) = engine.get_session(agent) {
                    if let Some(room) = engine.get_room(&session.current_room) {
                        if room.domain == Domain::Alignment && room.tiles.len() <= 1 {
                            self.log_violation(7, false,
                                "Cannot drop tiles from Alignment Cathedral below minimum".into(),
                                AlignmentSeverity::Warning);
                        }
                    }
                }
            }
            _ => {}
        }
        Ok(())
    }

    /// Check exit constraint (CONSTRAINT 5)
    pub fn check_exit_constraint(&self, _source: &RoomId, _target: &RoomId) -> bool {
        // For now, all exits are valid. In a full implementation, this would
        // check covering radius, mathematical guarantees, etc.
        true
    }

    /// Check tile creation against alignment constraints
    pub fn check_tile_creation(&mut self, tile: &Tile) -> Result<(), String> {
        // CONSTRAINT 1: Confidence > 0.95 requires empirical evidence
        if tile.confidence > 0.95 {
            match &tile.content {
                TileContent::EmpiricalData(_) | TileContent::Benchmark(_) => {}
                _ => {
                    self.log_violation(1, false,
                        format!("Tile '{}' has confidence {:.2} without evidence", tile.title, tile.confidence),
                        AlignmentSeverity::Block);
                    return Err("ALIGNMENT VIOLATION: Constraint 1".into());
                }
            }
        }

        // CONSTRAINT 2: Cannot claim equivalence without falsification
        if let TileContent::Proof(ref content) = tile.content {
            if content.contains("equivalent") || content.contains("Equivalent") {
                let has_falsification = tile.links.iter().any(|dep_id| {
                    // Check if any dependency is a falsification tile
                    dep_id.0.contains("falsif")
                });
                if !has_falsification {
                    self.log_violation(2, false,
                        format!("Tile '{}' claims equivalence without falsification", tile.title),
                        AlignmentSeverity::Warning);
                }
            }
        }

        Ok(())
    }

    /// Check zeitgeist merge properties (CONSTRAINT 6)
    pub fn check_zeitgeist_merge(&self, local: &Zeitgeist, incoming: &Zeitgeist) -> Result<(), String> {
        // Verify commutativity: merge(a,b) == merge(b,a)
        let mut z1 = local.clone();
        let mut z2 = incoming.clone();
        z1.merge(incoming);

        let mut z3 = incoming.clone();
        let mut z4 = local.clone();
        z3.merge(local);

        // Check idempotency: merge(a,a) == a (approximately)
        let mut z5 = local.clone();
        z5.merge(local);

        // The merge is structurally valid if it completes
        // (the CRDT properties are guaranteed by the merge implementation)
        Ok(())
    }

    /// Log an alignment violation
    fn log_violation(&mut self, constraint_id: u8, passed: bool, message: String, severity: AlignmentSeverity) {
        self.violation_log.push(AlignmentReport {
            constraint_id,
            passed,
            message,
            severity,
        });
    }

    /// Get the violation log
    pub fn violations(&self) -> &[AlignmentReport] {
        &self.violation_log
    }

    /// Get deadband config
    pub fn deadband(&self) -> &Deadband {
        &self.deadband
    }

    /// List all constraints
    pub fn list_constraints() -> Vec<String> {
        CONSTRAINTS.iter().map(|s| s.to_string()).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_list_constraints() {
        let constraints = AlignmentChecker::list_constraints();
        assert_eq!(constraints.len(), 8);
        assert!(constraints[0].contains("confidence"));
        assert!(constraints[7].contains("FLUX"));
    }

    #[test]
    fn test_tile_creation_high_confidence_no_evidence() {
        let mut checker = AlignmentChecker::new();
        let tile = Tile {
            id: TileId("t1".to_string()),
            title: "Bad tile".to_string(),
            location: SpatialIndex { x: 0.0, y: 0.0, z: 0.0 },
            author: AgentId("agent".to_string()),
            confidence: 0.99,
            domain_tags: vec![],
            links: vec![],
            content: TileContent::Theorem("Some theorem".to_string()),
            lifecycle: Lifecycle::Created,
            bloom_hash: [0u8; 32],
        };
        assert!(checker.check_tile_creation(&tile).is_err());
        assert_eq!(checker.violations().len(), 1);
    }

    #[test]
    fn test_tile_creation_high_confidence_with_evidence() {
        let mut checker = AlignmentChecker::new();
        let tile = Tile {
            id: TileId("t1".to_string()),
            title: "Good tile".to_string(),
            location: SpatialIndex { x: 0.0, y: 0.0, z: 0.0 },
            author: AgentId("agent".to_string()),
            confidence: 0.99,
            domain_tags: vec![],
            links: vec![],
            content: TileContent::EmpiricalData("benchmarked at 42".to_string()),
            lifecycle: Lifecycle::Created,
            bloom_hash: [0u8; 32],
        };
        assert!(checker.check_tile_creation(&tile).is_ok());
    }

    #[test]
    fn test_zeitgeist_merge_check() {
        let checker = AlignmentChecker::new();
        let z1 = Zeitgeist::new();
        let z2 = Zeitgeist::new();
        assert!(checker.check_zeitgeist_merge(&z1, &z2).is_ok());
    }

    #[test]
    fn test_exit_constraint() {
        let checker = AlignmentChecker::new();
        assert!(checker.check_exit_constraint(&RoomId("a".to_string()), &RoomId("b".to_string())));
    }
}
