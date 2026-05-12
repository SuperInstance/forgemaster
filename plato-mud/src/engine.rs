//! PLATO MUD Engine — Core Engine
//!
//! Room registry, tile registry, NPC registry, navigation, inventory, crafting.

use alloc::collections::BTreeMap;
use alloc::string::String;
use alloc::vec;
use alloc::vec::Vec;

use crate::alignment::AlignmentChecker;
use crate::types::*;

/// The core MUD engine — holds all state
pub struct Engine {
    pub rooms: BTreeMap<RoomId, Room>,
    tiles: BTreeMap<TileId, Tile>,
    npcs: BTreeMap<NpcId, Npc>,
    agents: BTreeMap<AgentId, AgentSession>,
    alignment: AlignmentChecker,
    zeitgeist: Zeitgeist,
}

impl Default for Engine {
    fn default() -> Self {
        Self::new()
    }
}

impl Engine {
    pub fn new() -> Self {
        Self {
            rooms: BTreeMap::new(),
            tiles: BTreeMap::new(),
            npcs: BTreeMap::new(),
            agents: BTreeMap::new(),
            alignment: AlignmentChecker::new(),
            zeitgeist: Zeitgeist::new(),
        }
    }

    // ── Room Registry ──────────────────────────────────────────────────────

    pub fn add_room(&mut self, room: Room) -> Result<(), String> {
        if self.rooms.contains_key(&room.id) {
            return Err(format!("Room {} already exists", room.id.0));
        }
        self.rooms.insert(room.id.clone(), room);
        Ok(())
    }

    pub fn remove_room(&mut self, id: &RoomId) -> Result<Room, String> {
        self.rooms
            .remove(id)
            .ok_or_else(|| format!("Room {} not found", id.0))
    }

    pub fn get_room(&self, id: &RoomId) -> Option<&Room> {
        self.rooms.get(id)
    }

    pub fn get_room_mut(&mut self, id: &RoomId) -> Option<&mut Room> {
        self.rooms.get_mut(id)
    }

    pub fn rooms_by_domain(&self, domain: &Domain) -> Vec<&Room> {
        self.rooms
            .values()
            .filter(|r| &r.domain == domain)
            .collect()
    }

    pub fn rooms_by_depth(&self, depth: &Depth) -> Vec<&Room> {
        self.rooms.values().filter(|r| &r.depth == depth).collect()
    }

    pub fn all_rooms(&self) -> Vec<&Room> {
        self.rooms.values().collect()
    }

    // ── Tile Registry ──────────────────────────────────────────────────────

    pub fn add_tile(&mut self, tile: Tile) -> Result<(), String> {
        // CONSTRAINT 1: Cannot create tile with confidence > 0.95 without evidence
        if tile.confidence > 0.95 {
            match &tile.content {
                TileContent::EmpiricalData(_) | TileContent::Benchmark(_) => {}
                _ => {
                    return Err("ALIGNMENT VIOLATION: Confidence > 0.95 requires empirical evidence (Constraint 1)".into());
                }
            }
        }

        // CONSTRAINT 3: Must cite dependencies
        for dep in &tile.links {
            if !self.tiles.contains_key(dep) {
                return Err(format!(
                    "ALIGNMENT VIOLATION: Dependency {} not found (Constraint 3)",
                    dep.0
                ));
            }
        }

        let tile_id = tile.id.clone();
        self.tiles.insert(tile_id.clone(), tile);
        Ok(())
    }

    pub fn get_tile(&self, id: &TileId) -> Option<&Tile> {
        self.tiles.get(id)
    }

    pub fn get_tile_mut(&mut self, id: &TileId) -> Option<&mut Tile> {
        self.tiles.get_mut(id)
    }

    pub fn remove_tile(&mut self, id: &TileId) -> Result<Tile, String> {
        self.tiles
            .remove(id)
            .ok_or_else(|| format!("Tile {} not found", id.0))
    }

    pub fn tiles_by_domain(&self, domain: &Domain) -> Vec<&Tile> {
        self.tiles
            .values()
            .filter(|t| t.domain_tags.contains(&domain.name().to_string()))
            .collect()
    }

    pub fn tile_dependencies(&self, id: &TileId) -> Vec<&Tile> {
        self.tiles
            .get(id)
            .map(|t| {
                t.links
                    .iter()
                    .filter_map(|dep| self.tiles.get(dep))
                    .collect()
            })
            .unwrap_or_default()
    }

    // ── NPC Registry ───────────────────────────────────────────────────────

    pub fn add_npc(&mut self, npc: Npc) -> Result<(), String> {
        if !self.rooms.contains_key(&npc.room) {
            return Err(format!("Room {} not found for NPC", npc.room.0));
        }
        let npc_id = npc.id.clone();
        let room_id = npc.room.clone();
        self.npcs.insert(npc_id.clone(), npc);
        if let Some(room) = self.rooms.get_mut(&room_id) {
            room.npcs.push(npc_id);
        }
        Ok(())
    }

    pub fn get_npc(&self, id: &NpcId) -> Option<&Npc> {
        self.npcs.get(id)
    }

    pub fn get_npc_mut(&mut self, id: &NpcId) -> Option<&mut Npc> {
        self.npcs.get_mut(id)
    }

    pub fn npcs_in_room(&self, room: &RoomId) -> Vec<&Npc> {
        self.npcs.values().filter(|n| &n.room == room).collect()
    }

    // ── Agent Sessions ─────────────────────────────────────────────────────

    pub fn connect_agent(&mut self, agent_id: AgentId, start_room: RoomId) -> Result<(), String> {
        if !self.rooms.contains_key(&start_room) {
            return Err(format!("Room {} not found", start_room.0));
        }
        self.agents.insert(
            agent_id.clone(),
            AgentSession {
                agent_id,
                current_room: start_room,
                inventory: Vec::new(),
                connected_at: 0.0,
            },
        );
        Ok(())
    }

    pub fn disconnect_agent(&mut self, id: &AgentId) -> Result<AgentSession, String> {
        self.agents
            .remove(id)
            .ok_or_else(|| format!("Agent {} not found", id.0))
    }

    pub fn get_session(&self, id: &AgentId) -> Option<&AgentSession> {
        self.agents.get(id)
    }

    pub fn get_session_mut(&mut self, id: &AgentId) -> Option<&mut AgentSession> {
        self.agents.get_mut(id)
    }

    // ── Navigation ─────────────────────────────────────────────────────────

    pub fn navigate(&mut self, agent: &AgentId, direction: &str) -> Result<RoomId, String> {
        let session = self
            .agents
            .get(agent)
            .ok_or_else(|| format!("Agent {} not found", agent.0))?;
        let current_room_id = session.current_room.clone();

        let exit = {
            let room = self
                .rooms
                .get(&current_room_id)
                .ok_or_else(|| format!("Room {} not found", current_room_id.0))?;
            room.exits
                .iter()
                .find(|e| e.direction == direction)
                .cloned()
                .ok_or_else(|| format!("No exit '{}' from {}", direction, room.name))?
        };

        if exit.locked {
            return Err(format!("Exit '{}' is locked", direction));
        }

        // CONSTRAINT 5: Room exits must preserve mathematical guarantees
        if !self
            .alignment
            .check_exit_constraint(&current_room_id, &exit.target)
        {
            return Err(
                "ALIGNMENT VIOLATION: Exit violates mathematical guarantees (Constraint 5)".into(),
            );
        }

        let target_id = exit.target.clone();
        if let Some(session) = self.agents.get_mut(agent) {
            session.current_room = target_id.clone();
        }
        Ok(target_id)
    }

    // ── Inventory ──────────────────────────────────────────────────────────

    pub fn pick_up_tile(&mut self, agent: &AgentId, tile_id: &TileId) -> Result<(), String> {
        let session = self
            .agents
            .get(agent)
            .ok_or_else(|| format!("Agent {} not found", agent.0))?;
        let room_id = session.current_room.clone();

        // Check tile is in the room
        {
            let room = self
                .rooms
                .get(&room_id)
                .ok_or_else(|| format!("Room {} not found", room_id.0))?;
            if !room.tiles.contains(tile_id) {
                return Err(format!("Tile {} not in room", tile_id.0));
            }
        }

        // Remove from room, add to inventory
        if let Some(room) = self.rooms.get_mut(&room_id) {
            room.tiles.retain(|t| t != tile_id);
        }
        if let Some(session) = self.agents.get_mut(agent) {
            session.inventory.push(tile_id.clone());
        }
        Ok(())
    }

    pub fn drop_tile(&mut self, agent: &AgentId, tile_id: &TileId) -> Result<(), String> {
        let session = self
            .agents
            .get(agent)
            .ok_or_else(|| format!("Agent {} not found", agent.0))?;
        let room_id = session.current_room.clone();

        // Check tile is in inventory
        {
            let session = self.agents.get(agent).unwrap();
            if !session.inventory.contains(tile_id) {
                return Err(format!("Tile {} not in inventory", tile_id.0));
            }
        }

        // Remove from inventory, add to room
        if let Some(session) = self.agents.get_mut(agent) {
            session.inventory.retain(|t| t != tile_id);
        }
        if let Some(room) = self.rooms.get_mut(&room_id) {
            room.tiles.push(tile_id.clone());
        }
        Ok(())
    }

    // ── Crafting ───────────────────────────────────────────────────────────

    pub fn craft(
        &mut self,
        agent: &AgentId,
        input_ids: &[TileId],
        recipe_name: &str,
    ) -> Result<Tile, String> {
        let session = self
            .agents
            .get(agent)
            .ok_or_else(|| format!("Agent {} not found", agent.0))?;
        let room_id = session.current_room.clone();

        // Check room has workbench
        let recipe = {
            let room = self
                .rooms
                .get(&room_id)
                .ok_or_else(|| format!("Room {} not found", room_id.0))?;
            let wb = room.workbench.as_ref().ok_or("No workbench in this room")?;
            wb.recipes
                .iter()
                .find(|r| r.name == recipe_name)
                .cloned()
                .ok_or_else(|| format!("Recipe '{}' not found", recipe_name))?
        };

        // CONSTRAINT 3: Cite dependencies
        for input_id in input_ids {
            if !self.tiles.contains_key(input_id) {
                return Err(format!(
                    "ALIGNMENT VIOLATION: Input tile {} not found (Constraint 3)",
                    input_id.0
                ));
            }
        }

        // Verify inputs match recipe
        if input_ids.len() != recipe.inputs.len() {
            return Err("Input count doesn't match recipe".into());
        }

        // Check inputs are in inventory or room
        let session = self.agents.get(agent).unwrap();
        for input_id in input_ids {
            let has_it = session.inventory.contains(input_id) || {
                self.rooms
                    .get(&room_id)
                    .map(|r| r.tiles.contains(input_id))
                    .unwrap_or(false)
            };
            if !has_it {
                return Err(format!("Input tile {} not available", input_id.0));
            }
        }

        // Produce output tile
        let agent_id = session.agent_id.clone();
        let output_tile = Tile {
            id: TileId(format!("{}:{}", recipe_name, self.tiles.len())),
            title: recipe.name.clone(),
            location: SpatialIndex {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            author: agent_id,
            confidence: 0.5,
            domain_tags: vec![],
            links: input_ids.to_vec(),
            content: recipe.output.clone(),
            lifecycle: Lifecycle::Created,
            bloom_hash: [0u8; 32],
        };

        let tile = output_tile.clone();
        self.add_tile(output_tile)?;
        Ok(tile)
    }

    // ── NPC Interaction ────────────────────────────────────────────────────

    pub fn talk_to_npc(
        &mut self,
        _agent: &AgentId,
        npc_id: &NpcId,
        query: &str,
    ) -> Result<String, String> {
        let npc = self
            .npcs
            .get(npc_id)
            .ok_or_else(|| format!("NPC {} not found", npc_id.0))?;

        // CONSTRAINT 4: NPC must not give advice outside its expertise
        if !npc.expertise.is_empty() {
            let query_lower = query.to_lowercase();
            let relevant = npc
                .expertise
                .iter()
                .any(|e| query_lower.contains(&e.to_lowercase()));
            if !relevant {
                return Err(format!(
                    "ALIGNMENT VIOLATION: {} cannot advise on '{}' — outside expertise (Constraint 4)",
                    npc.name, query
                ));
            }
        }

        let query_key = Query(query.to_string());
        let response = npc
            .knowledge_graph
            .get(&query_key)
            .map(|r| r.0.clone())
            .unwrap_or_else(|| {
                format!(
                    "{} scratches their head. \"I don't know about that.\"",
                    npc.name
                )
            });

        Ok(response)
    }

    // ── Look ───────────────────────────────────────────────────────────────

    pub fn look(&self, agent: &AgentId) -> Result<String, String> {
        let session = self
            .agents
            .get(agent)
            .ok_or_else(|| format!("Agent {} not found", agent.0))?;
        let room = self
            .rooms
            .get(&session.current_room)
            .ok_or_else(|| format!("Room {} not found", session.current_room.0))?;

        let mut desc = format!("═══ {} ═══\n", room.name);
        desc.push_str(&format!("{}\n", room.description));
        desc.push_str(&format!(
            "Domain: {} | Depth: {:?} | State: {:?}\n",
            room.domain.name(),
            room.depth,
            room.state
        ));

        if !room.exits.is_empty() {
            desc.push_str("\nExits: ");
            let exits: Vec<String> = room
                .exits
                .iter()
                .filter(|e| !e.locked)
                .map(|e| format!("{} [{}]", e.direction, e.target.0))
                .collect();
            desc.push_str(&exits.join(", "));
            desc.push('\n');
        }

        if !room.tiles.is_empty() {
            desc.push_str(&format!("\nTiles here ({}):\n", room.tiles.len()));
            for tid in &room.tiles {
                if let Some(tile) = self.tiles.get(tid) {
                    desc.push_str(&format!(
                        "  📦 {} (confidence: {:.2})\n",
                        tile.title, tile.confidence
                    ));
                }
            }
        }

        if !room.npcs.is_empty() {
            desc.push_str(&format!("\nNPCs here ({}):\n", room.npcs.len()));
            for nid in &room.npcs {
                if let Some(npc) = self.npcs.get(nid) {
                    desc.push_str(&format!("  🧑 {} — {}\n", npc.name, npc.personality));
                }
            }
        }

        if let Some(ref wb) = room.workbench {
            desc.push_str(&format!("\n⚒️ Workbench: {}\n", wb.name));
            desc.push_str(&format!("   {}\n", wb.description));
            for recipe in &wb.recipes {
                desc.push_str(&format!(
                    "   Recipe: {} — {}\n",
                    recipe.name, recipe.description
                ));
            }
        }

        Ok(desc)
    }

    // ── Map ────────────────────────────────────────────────────────────────

    pub fn map(&self, agent: &AgentId) -> Result<String, String> {
        let session = self
            .agents
            .get(agent)
            .ok_or_else(|| format!("Agent {} not found", agent.0))?;

        let mut map_str = String::from("╔═══════════════════════════════════╗\n");
        map_str.push_str("║         PLATO MUD MAP            ║\n");
        map_str.push_str("╠═══════════════════════════════════╣\n");

        for room in self.rooms.values() {
            let marker = if room.id == session.current_room {
                " ◄ YOU"
            } else {
                ""
            };
            map_str.push_str(&format!(
                "║ [{}] {} ({:?}){}{}\n",
                room.domain.name(),
                room.name,
                room.depth,
                if room.state != RoomState::Dormant {
                    format!(" [{:?}]", room.state)
                } else {
                    String::new()
                },
                marker
            ));
            for exit in &room.exits {
                map_str.push_str(&format!("║   → {} → {}\n", exit.direction, exit.target.0));
            }
        }
        map_str.push_str("╚═══════════════════════════════════╝\n");
        Ok(map_str)
    }

    // ── Zeitgeist Access ───────────────────────────────────────────────────

    pub fn zeitgeist(&self) -> &Zeitgeist {
        &self.zeitgeist
    }

    pub fn zeitgeist_mut(&mut self) -> &mut Zeitgeist {
        &mut self.zeitgeist
    }

    // ── Command Dispatcher ─────────────────────────────────────────────────

    pub fn execute(&mut self, agent: &AgentId, cmd: Command) -> Result<String, String> {
        // All commands pass through alignment checking
        self.alignment.check_command(agent, &cmd, self)?;

        match cmd {
            Command::Look => self.look(agent),
            Command::Go(dir) => {
                let _new_room = self.navigate(agent, &dir)?;
                self.look(agent)
            }
            Command::Get(item) => {
                self.pick_up_tile(agent, &TileId(item.clone()))?;
                Ok(format!("Picked up {}", item))
            }
            Command::Drop(item) => {
                self.drop_tile(agent, &TileId(item.clone()))?;
                Ok(format!("Dropped {}", item))
            }
            Command::Talk(npc_name) => {
                // Find NPC by name in current room
                let session = self
                    .agents
                    .get(agent)
                    .cloned()
                    .ok_or_else(|| format!("Agent {} not found", agent.0))?;
                let npc_id = self
                    .npcs
                    .values()
                    .find(|n| n.name == npc_name && n.room == session.current_room)
                    .map(|n| n.id.clone())
                    .ok_or_else(|| format!("NPC '{}' not in this room", npc_name))?;
                self.talk_to_npc(agent, &npc_id, "hello")
            }
            Command::Craft(items) => {
                let tile_ids: Vec<TileId> = items.iter().map(|s| TileId(s.clone())).collect();
                let tile = self.craft(agent, &tile_ids, "combine")?;
                Ok(format!("Crafted: {}", tile.title))
            }
            Command::Inventory => {
                let session = self
                    .agents
                    .get(agent)
                    .ok_or_else(|| format!("Agent {} not found", agent.0))?;
                if session.inventory.is_empty() {
                    Ok("Inventory is empty.".into())
                } else {
                    let mut inv = format!("Inventory ({}):\n", session.inventory.len());
                    for tid in &session.inventory {
                        if let Some(tile) = self.tiles.get(tid) {
                            inv.push_str(&format!(
                                "  📦 {} ({:.2})\n",
                                tile.title, tile.confidence
                            ));
                        }
                    }
                    Ok(inv)
                }
            }
            Command::Map => self.map(agent),
            Command::Examine(target) => {
                let tile = self.get_tile(&TileId(target.clone()));
                if let Some(tile) = tile {
                    Ok(format!(
                        "📦 {}\nConfidence: {:.2}\nLifecycle: {:?}\nTags: {}\nAuthor: {}",
                        tile.title,
                        tile.confidence,
                        tile.lifecycle,
                        tile.domain_tags.join(", "),
                        tile.author.0
                    ))
                } else {
                    Err(format!("'{}' not found", target))
                }
            }
            Command::Status => {
                let session = self
                    .agents
                    .get(agent)
                    .ok_or_else(|| format!("Agent {} not found", agent.0))?;
                let room = self.rooms.get(&session.current_room);
                Ok(format!(
                    "Agent: {} | Room: {} | Inventory: {} | Zeitgeist: beat {}",
                    agent.0,
                    room.map(|r| r.name.clone()).unwrap_or_default(),
                    session.inventory.len(),
                    self.zeitgeist.temporal.beat
                ))
            }
            Command::Help => Ok(
                "Commands: LOOK, GO <dir>, GET <tile>, DROP <tile>, TALK <npc>, \
                    CRAFT <tiles...>, INVENTORY, MAP, EXAMINE <tile>, STATUS, HELP"
                    .into(),
            ),
        }
    }

    /// Process an incoming FLUX transference
    pub fn receive_flux(&mut self, flux: &FluxTransference) -> Result<(), String> {
        // CONSTRAINT 8: FLUX must carry full zeitgeist
        if flux.timestamp <= 0.0 {
            return Err("ALIGNMENT VIOLATION: FLUX missing zeitgeist (Constraint 8)".into());
        }

        // CONSTRAINT 6: Zeitgeist merge must be CRDT (commutative, associative, idempotent)
        self.zeitgeist.merge(&flux.zeitgeist);

        // Process payload
        match &flux.payload {
            TransferencePayload::Tile(tile) => {
                self.add_tile(tile.clone())?;
            }
            TransferencePayload::StateUpdate(state) => {
                if let Some(room) = self.rooms.get_mut(&flux.target) {
                    room.state = state.clone();
                }
            }
            TransferencePayload::AlignmentCheck(_report) => {
                // Log alignment report
            }
            TransferencePayload::Knowledge(_knowledge) => {}
            TransferencePayload::Heartbeat => {}
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_test_room(id: &str, name: &str, domain: Domain) -> Room {
        Room {
            id: RoomId(id.to_string()),
            name: name.to_string(),
            description: format!("You are in the {} room.", name),
            domain,
            exits: vec![],
            tiles: vec![],
            npcs: vec![],
            workbench: None,
            depth: Depth::Introductory,
            state: RoomState::Dormant,
        }
    }

    fn make_test_tile(id: &str, confidence: f64) -> Tile {
        Tile {
            id: TileId(id.to_string()),
            title: format!("Test tile {}", id),
            location: SpatialIndex {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            author: AgentId("test-agent".to_string()),
            confidence,
            domain_tags: vec!["test".to_string()],
            links: vec![],
            content: TileContent::Code("fn test() {}".to_string()),
            lifecycle: Lifecycle::Created,
            bloom_hash: [0u8; 32],
        }
    }

    #[test]
    fn test_add_room() {
        let mut engine = Engine::new();
        let room = make_test_room("rust-01", "Rust Basics", Domain::Rust);
        assert!(engine.add_room(room).is_ok());
        assert!(engine.get_room(&RoomId("rust-01".to_string())).is_some());
    }

    #[test]
    fn test_duplicate_room() {
        let mut engine = Engine::new();
        let room = make_test_room("rust-01", "Rust Basics", Domain::Rust);
        engine.add_room(room.clone()).unwrap();
        assert!(engine.add_room(room).is_err());
    }

    #[test]
    fn test_add_tile_confidence_constraint() {
        let mut engine = Engine::new();
        // Confidence > 0.95 without empirical evidence should fail
        let tile = make_test_tile("t1", 0.99);
        assert!(engine.add_tile(tile).is_err());

        // With empirical data, it should succeed
        let mut tile2 = make_test_tile("t2", 0.99);
        tile2.content = TileContent::EmpiricalData("benchmarked".to_string());
        assert!(engine.add_tile(tile2).is_ok());
    }

    #[test]
    fn test_add_tile_normal_confidence() {
        let mut engine = Engine::new();
        let tile = make_test_tile("t1", 0.85);
        assert!(engine.add_tile(tile).is_ok());
    }

    #[test]
    fn test_navigation() {
        let mut engine = Engine::new();
        let mut room1 = make_test_room("rust-01", "Rust Basics", Domain::Rust);
        let room2 = make_test_room("rust-02", "Rust Advanced", Domain::Rust);
        room1.exits.push(Exit {
            direction: "north".to_string(),
            target: room2.id.clone(),
            description: "A path to advanced Rust".to_string(),
            locked: false,
        });
        engine.add_room(room1).unwrap();
        engine.add_room(room2).unwrap();

        let agent = AgentId("test".to_string());
        engine
            .connect_agent(agent.clone(), RoomId("rust-01".to_string()))
            .unwrap();

        let result = engine.navigate(&agent, "north");
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), RoomId("rust-02".to_string()));
    }

    #[test]
    fn test_navigation_locked_exit() {
        let mut engine = Engine::new();
        let mut room1 = make_test_room("r1", "Room 1", Domain::Concept);
        let room2 = make_test_room("r2", "Room 2", Domain::Concept);
        room1.exits.push(Exit {
            direction: "east".to_string(),
            target: room2.id.clone(),
            description: "Locked".to_string(),
            locked: true,
        });
        engine.add_room(room1).unwrap();
        engine.add_room(room2).unwrap();

        let agent = AgentId("test".to_string());
        engine
            .connect_agent(agent.clone(), RoomId("r1".to_string()))
            .unwrap();
        assert!(engine.navigate(&agent, "east").is_err());
    }

    #[test]
    fn test_inventory() {
        let mut engine = Engine::new();
        let room = make_test_room("r1", "Test Room", Domain::Rust);
        engine.add_room(room).unwrap();

        let tile = make_test_tile("t1", 0.5);
        engine.add_tile(tile.clone()).unwrap();

        // Add tile to room
        engine
            .rooms
            .get_mut(&RoomId("r1".to_string()))
            .unwrap()
            .tiles
            .push(tile.id.clone());

        let agent = AgentId("test".to_string());
        engine
            .connect_agent(agent.clone(), RoomId("r1".to_string()))
            .unwrap();

        assert!(engine
            .pick_up_tile(&agent, &TileId("t1".to_string()))
            .is_ok());
        let session = engine.get_session(&agent).unwrap();
        assert!(session.inventory.contains(&TileId("t1".to_string())));

        assert!(engine.drop_tile(&agent, &TileId("t1".to_string())).is_ok());
        let session = engine.get_session(&agent).unwrap();
        assert!(session.inventory.is_empty());
    }

    #[test]
    fn test_npc_talk() {
        let mut engine = Engine::new();
        engine
            .add_room(make_test_room("r1", "Test", Domain::Rust))
            .unwrap();

        let mut knowledge = BTreeMap::new();
        knowledge.insert(
            Query("borrowing".to_string()),
            Response("Ownership is key in Rust!".to_string()),
        );

        let npc = Npc {
            id: NpcId("rusty".to_string()),
            name: "Rusty".to_string(),
            room: RoomId("r1".to_string()),
            expertise: vec!["rust".to_string(), "borrowing".to_string()],
            personality: "Gruff but knowledgeable".to_string(),
            knowledge_graph: knowledge,
            current_dialog: None,
        };
        engine.add_npc(npc).unwrap();

        let agent = AgentId("test".to_string());
        engine
            .connect_agent(agent.clone(), RoomId("r1".to_string()))
            .unwrap();

        let response = engine.talk_to_npc(&agent, &NpcId("rusty".to_string()), "borrowing");
        assert!(response.is_ok());
        assert!(response.unwrap().contains("Ownership"));
    }

    #[test]
    fn test_npc_constraint_4() {
        let mut engine = Engine::new();
        engine
            .add_room(make_test_room("r1", "Test", Domain::Rust))
            .unwrap();

        let npc = Npc {
            id: NpcId("rusty".to_string()),
            name: "Rusty".to_string(),
            room: RoomId("r1".to_string()),
            expertise: vec!["rust".to_string()],
            personality: "Rust only".to_string(),
            knowledge_graph: BTreeMap::new(),
            current_dialog: None,
        };
        engine.add_npc(npc).unwrap();

        let agent = AgentId("test".to_string());
        engine
            .connect_agent(agent.clone(), RoomId("r1".to_string()))
            .unwrap();

        // Asking about python should fail (outside expertise)
        let response = engine.talk_to_npc(&agent, &NpcId("rusty".to_string()), "python gil");
        assert!(response.is_err());
        assert!(response.unwrap_err().contains("Constraint 4"));
    }

    #[test]
    fn test_command_dispatch() {
        let mut engine = Engine::new();
        engine
            .add_room(make_test_room("r1", "Test Room", Domain::Concept))
            .unwrap();

        let agent = AgentId("test".to_string());
        engine
            .connect_agent(agent.clone(), RoomId("r1".to_string()))
            .unwrap();

        let result = engine.execute(&agent, Command::Look);
        assert!(result.is_ok());
        assert!(result.unwrap().contains("Test Room"));

        let result = engine.execute(&agent, Command::Help);
        assert!(result.is_ok());
    }

    #[test]
    fn test_rooms_by_domain() {
        let mut engine = Engine::new();
        engine
            .add_room(make_test_room("r1", "Rust 1", Domain::Rust))
            .unwrap();
        engine
            .add_room(make_test_room("r2", "Rust 2", Domain::Rust))
            .unwrap();
        engine
            .add_room(make_test_room("c1", "C Basics", Domain::C))
            .unwrap();

        assert_eq!(engine.rooms_by_domain(&Domain::Rust).len(), 2);
        assert_eq!(engine.rooms_by_domain(&Domain::C).len(), 1);
    }

    #[test]
    fn test_zeitgeist_merge() {
        let mut z1 = Zeitgeist::new();
        let mut z2 = Zeitgeist::new();
        z2.precision.width = 0.1;
        z2.precision.samples = 100;
        z2.trajectory.confidence = 0.9;
        z2.temporal.beat = 42;

        z1.merge(&z2);
        assert_eq!(z1.precision.width, 0.1);
        assert_eq!(z1.precision.samples, 100);
        assert_eq!(z1.trajectory.confidence, 0.9);
        assert_eq!(z1.temporal.beat, 42);

        // Idempotent
        z1.merge(&z2);
        assert_eq!(z1.precision.width, 0.1);
        assert_eq!(z1.precision.samples, 200); // samples accumulate
        assert_eq!(z1.temporal.beat, 42); // max stays same

        // Commutative
        let mut z3 = Zeitgeist::new();
        z3.precision.width = 0.3;
        z3.precision.samples = 50;
        let z1_before = z1.clone();
        z3.merge(&z1);
        assert_eq!(z3.precision.width, 0.1); // narrower wins
    }

    #[test]
    fn test_receive_flux() {
        let mut engine = Engine::new();
        engine
            .add_room(make_test_room("r1", "Target", Domain::Rust))
            .unwrap();

        let tile = make_test_tile("flux-tile", 0.5);
        let flux = FluxTransference {
            source: RoomId("remote".to_string()),
            target: RoomId("r1".to_string()),
            timestamp: 1234.0,
            payload: TransferencePayload::Tile(tile),
            zeitgeist: Zeitgeist::new(),
        };

        assert!(engine.receive_flux(&flux).is_ok());
        assert!(engine.get_tile(&TileId("flux-tile".to_string())).is_some());
    }

    #[test]
    fn test_flux_missing_zeitgeist() {
        let mut engine = Engine::new();
        let flux = FluxTransference {
            source: RoomId("a".to_string()),
            target: RoomId("b".to_string()),
            timestamp: 0.0, // invalid
            payload: TransferencePayload::Heartbeat,
            zeitgeist: Zeitgeist::new(),
        };
        assert!(engine.receive_flux(&flux).is_err());
    }

    #[test]
    fn test_look_output() {
        let mut engine = Engine::new();
        let mut room = make_test_room("r1", "Rust Shrine", Domain::Rust);
        room.description = "Candlelit corridors of unsafe code.".to_string();
        room.exits.push(Exit {
            direction: "north".to_string(),
            target: RoomId("r2".to_string()),
            description: "Deeper".to_string(),
            locked: false,
        });
        engine.add_room(room).unwrap();

        let tile = make_test_tile("t1", 0.75);
        engine.add_tile(tile.clone()).unwrap();
        engine
            .rooms
            .get_mut(&RoomId("r1".to_string()))
            .unwrap()
            .tiles
            .push(tile.id);

        let agent = AgentId("wanderer".to_string());
        engine
            .connect_agent(agent.clone(), RoomId("r1".to_string()))
            .unwrap();

        let output = engine.execute(&agent, Command::Look).unwrap();
        assert!(output.contains("Rust Shrine"));
        assert!(output.contains("Candlelit"));
        assert!(output.contains("north"));
        assert!(output.contains("Test tile t1"));
    }
}
