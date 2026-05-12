//! PLATO MUD Engine — Server
//!
//! Accepts connections via any transport, manages agent sessions,
//! handles commands, broadcasts zeitgeist changes, alignment checks.

#![cfg(feature = "server")]

use std::collections::BTreeMap;
use std::io::{self, BufRead, Write};

use crate::engine::Engine;
use crate::flux::FluxManager;
use crate::types::*;
use crate::transport::Transport;
use crate::transport::memory::MemoryTransport;

/// The PLATO MUD server
pub struct PlatoServer {
    engine: Engine,
    flux_manager: FluxManager,
    transport: Box<dyn Transport>,
    running: bool,
}

impl PlatoServer {
    pub fn new() -> Self {
        let mut server = Self {
            engine: Engine::new(),
            flux_manager: FluxManager::new(),
            transport: Box::new(MemoryTransport::new()),
            running: false,
        };
        server.bootstrap_rooms();
        server
    }

    /// Bootstrap the default room topology
    fn bootstrap_rooms(&mut self) {
        // Alignment Cathedral — the constraint room
        let alignment_cathedral = Room {
            id: RoomId("alignment-cathedral".to_string()),
            name: "The Alignment Cathedral".to_string(),
            description: "A vast hall of pure constraint. Eight pillars hold the sky. \
                Each pillar is an alignment constraint, immutable and true. \
                The zeitgeist here is precise to 16 decimal places.".to_string(),
            domain: Domain::Alignment,
            exits: vec![
                Exit { direction: "north".to_string(), target: RoomId("fortran-foyer".to_string()),
                       description: "Toward the ancient fortran halls".to_string(), locked: false },
                Exit { direction: "east".to_string(), target: RoomId("rust-forge".to_string()),
                       description: "The fires of the Rust forge burn bright".to_string(), locked: false },
            ],
            tiles: vec![],
            npcs: vec![],
            workbench: Some(Workbench {
                name: "The Constraint Anvil".to_string(),
                description: "Forge new constraints from proven theorems".to_string(),
                recipes: vec![Recipe {
                    name: "combine".to_string(),
                    inputs: vec![TileId("theorem".to_string()), TileId("proof".to_string())],
                    output: TileContent::Constraint("New constraint from theorem + proof".to_string()),
                    description: "Combine a theorem and proof into a constraint".to_string(),
                }],
            }),
            depth: Depth::Expert,
            state: RoomState::Active,
        };

        let fortran_foyer = Room {
            id: RoomId("fortran-foyer".to_string()),
            name: "The Fortran Foyer".to_string(),
            description: "Stone walls carved with DO loops and FORMAT statements. \
                The air smells of punch cards and optimization. A grandfather clock \
                ticks in units of FLOPS.".to_string(),
            domain: Domain::Fortran,
            exits: vec![
                Exit { direction: "south".to_string(), target: RoomId("alignment-cathedral".to_string()),
                       description: "Back to the Cathedral".to_string(), locked: false },
                Exit { direction: "up".to_string(), target: RoomId("fortran-attic".to_string()),
                       description: "Climb to the expert-level optimizations".to_string(), locked: false },
            ],
            tiles: vec![],
            npcs: vec![],
            workbench: None,
            depth: Depth::Introductory,
            state: RoomState::Dormant,
        };

        let fortran_attic = Room {
            id: RoomId("fortran-attic".to_string()),
            name: "The Fortran Attic".to_string(),
            description: "Dusty volumes of BLAS, LAPACK, and parallel directives. \
                Here, arrays are king and column-major is law.".to_string(),
            domain: Domain::Fortran,
            exits: vec![
                Exit { direction: "down".to_string(), target: RoomId("fortran-foyer".to_string()),
                       description: "Back down to the foyer".to_string(), locked: false },
            ],
            tiles: vec![],
            npcs: vec![],
            workbench: Some(Workbench {
                name: "The Optimizer's Workbench".to_string(),
                description: "Combine benchmarks and theorems into optimized kernels".to_string(),
                recipes: vec![Recipe {
                    name: "combine".to_string(),
                    inputs: vec![TileId("benchmark".to_string())],
                    output: TileContent::Code("Optimized kernel".to_string()),
                    description: "Benchmark-guided optimization".to_string(),
                }],
            }),
            depth: Depth::Expert,
            state: RoomState::Dormant,
        };

        let rust_forge = Room {
            id: RoomId("rust-forge".to_string()),
            name: "The Rust Forge".to_string(),
            description: "Heat shimmers from a zero-cost abstraction furnace. \
                The borrow checker guards the door. Ownership is strictly enforced. \
                Crates of components line the walls, each with its own module.".to_string(),
            domain: Domain::Rust,
            exits: vec![
                Exit { direction: "west".to_string(), target: RoomId("alignment-cathedral".to_string()),
                       description: "Back to the Cathedral".to_string(), locked: false },
                Exit { direction: "north".to_string(), target: RoomId("c-caverns".to_string()),
                       description: "Descend into the C caverns".to_string(), locked: false },
            ],
            tiles: vec![],
            npcs: vec![],
            workbench: None,
            depth: Depth::Introductory,
            state: RoomState::Dormant,
        };

        let c_caverns = Room {
            id: RoomId("c-caverns".to_string()),
            name: "The C Caverns".to_string(),
            description: "Dark tunnels of pointer arithmetic and manual memory management. \
                Segfaults echo in the distance. A faint smell of undefined behavior.".to_string(),
            domain: Domain::C,
            exits: vec![
                Exit { direction: "south".to_string(), target: RoomId("rust-forge".to_string()),
                       description: "Back to the Rust Forge".to_string(), locked: false },
            ],
            tiles: vec![],
            npcs: vec![],
            workbench: None,
            depth: Depth::Advanced,
            state: RoomState::Dormant,
        };

        // Seed tiles
        let constraint_tile = Tile {
            id: TileId("constraint-1".to_string()),
            title: "Precision Deadband Constraint".to_string(),
            location: SpatialIndex { x: 0.0, y: 2.0, z: 0.0 },
            author: AgentId("forgemaster".to_string()),
            confidence: 0.95,
            domain_tags: vec!["alignment".to_string(), "constraint".to_string()],
            links: vec![],
            content: TileContent::Constraint("Drift must remain within deadband of 2σ".to_string()),
            lifecycle: Lifecycle::Certified,
            bloom_hash: [0u8; 32],
        };

        let benchmark_tile = Tile {
            id: TileId("benchmark-fortran-1".to_string()),
            title: "BLAS Level-3 Throughput Benchmark".to_string(),
            location: SpatialIndex { x: 0.0, y: 0.0, z: 0.0 },
            author: AgentId("forgemaster".to_string()),
            confidence: 0.99,
            domain_tags: vec!["fortran".to_string(), "benchmark".to_string()],
            links: vec![],
            content: TileContent::Benchmark("DGEMM: 42 GFLOPS on reference hardware".to_string()),
            lifecycle: Lifecycle::Certified,
            bloom_hash: [0u8; 32],
        };

        self.engine.add_room(alignment_cathedral).unwrap();
        self.engine.add_room(fortran_foyer).unwrap();
        self.engine.add_room(fortran_attic).unwrap();
        self.engine.add_room(rust_forge).unwrap();
        self.engine.add_room(c_caverns).unwrap();

        self.engine.add_tile(constraint_tile).unwrap();
        self.engine.add_tile(benchmark_tile).unwrap();

        // Place tiles in rooms
        self.engine.rooms.get_mut(&RoomId("alignment-cathedral".to_string())).unwrap()
            .tiles.push(TileId("constraint-1".to_string()));
        self.engine.rooms.get_mut(&RoomId("fortran-foyer".to_string())).unwrap()
            .tiles.push(TileId("benchmark-fortran-1".to_string()));

        // Add NPCs
        let rust_expert = Npc {
            id: NpcId("boris".to_string()),
            name: "Boris".to_string(),
            room: RoomId("rust-forge".to_string()),
            expertise: vec!["rust".to_string(), "borrow".to_string(), "ownership".to_string(), "lifetime".to_string()],
            personality: "A grizzled systems programmer who speaks in lifetimes".to_string(),
            knowledge_graph: {
                let mut kg = BTreeMap::new();
                kg.insert(Query("borrow".to_string()), Response("There are two kinds: shared (&T) and exclusive (&mut T). The compiler enforces that you can have either any number of shared refs OR exactly one exclusive ref, never both.".to_string()));
                kg.insert(Query("ownership".to_string()), Response("Every value has exactly one owner. When the owner goes out of scope, the value is dropped. Simple. Beautiful. No garbage collector needed.".to_string()));
                kg.insert(Query("lifetime".to_string()), Response("Lifetimes are the compiler's way of tracking how long references are valid. Most of the time it figures it out. When it can't, you annotate: 'a is the most common.".to_string()));
                kg
            },
            current_dialog: None,
        };

        let fortran_sage = Npc {
            id: NpcId("dr-fortran".to_string()),
            name: "Dr. Fortran".to_string(),
            room: RoomId("fortran-foyer".to_string()),
            expertise: vec!["fortran".to_string(), "blas".to_string(), "lapack".to_string(), "optimization".to_string()],
            personality: "An elderly academic who speaks in array operations".to_string(),
            knowledge_graph: {
                let mut kg = BTreeMap::new();
                kg.insert(Query("fortran".to_string()), Response("FORTRAN — the father of scientific computing. Column-major arrays, pass-by-reference, and DO loops that have been running since 1957.".to_string()));
                kg.insert(Query("blas".to_string()), Response("Basic Linear Algebra Subprograms. Three levels: vector-vector (1), matrix-vector (2), matrix-matrix (3). Always use Level 3 for maximum FLOPS.".to_string()));
                kg
            },
            current_dialog: None,
        };

        self.engine.add_npc(rust_expert).unwrap();
        self.engine.add_npc(fortran_sage).unwrap();
    }

    /// Parse a command from raw input
    fn parse_command(input: &str) -> Option<Command> {
        let input = input.trim();
        if input.is_empty() {
            return None;
        }

        let parts: Vec<&str> = input.splitn(2, ' ').collect();
        let verb = parts[0].to_uppercase();

        match verb.as_str() {
            "LOOK" | "L" => Some(Command::Look),
            "GO" | "MOVE" | "WALK" => {
                let dir = parts.get(1).map(|s| s.to_lowercase());
                dir.map(Command::Go)
            }
            "GET" | "TAKE" | "PICKUP" => {
                parts.get(1).map(|s| Command::Get(s.to_string()))
            }
            "DROP" | "PUT" => {
                parts.get(1).map(|s| Command::Drop(s.to_string()))
            }
            "TALK" | "SPEAK" | "ASK" => {
                parts.get(1).map(|s| Command::Talk(s.to_string()))
            }
            "CRAFT" | "MAKE" | "BUILD" => {
                let items: Vec<String> = parts.get(1)
                    .map(|s| s.split('+').map(|i| i.trim().to_string()).collect())
                    .unwrap_or_default();
                Some(Command::Craft(items))
            }
            "INVENTORY" | "INV" | "I" => Some(Command::Inventory),
            "MAP" | "M" => Some(Command::Map),
            "HELP" | "H" | "?" => Some(Command::Help),
            "EXAMINE" | "EX" | "X" => {
                parts.get(1).map(|s| Command::Examine(s.to_string()))
            }
            "STATUS" | "STAT" => Some(Command::Status),
            // Direction shortcuts
            "N" | "NORTH" => Some(Command::Go("north".to_string())),
            "S" | "SOUTH" => Some(Command::Go("south".to_string())),
            "E" | "EAST" => Some(Command::Go("east".to_string())),
            "W" | "WEST" => Some(Command::Go("west".to_string())),
            "U" | "UP" => Some(Command::Go("up".to_string())),
            "D" | "DOWN" => Some(Command::Go("down".to_string())),
            "QUIT" | "Q" | "EXIT" => None, // handled by caller
            _ => None,
        }
    }

    /// Run the interactive server (stdin/stdout)
    pub fn run_interactive(&mut self) -> io::Result<()> {
        println!("╔═══════════════════════════════════════╗");
        println!("║     PLATO MUD Engine v0.1.0          ║");
        println!("║     Constraint-Theory Knowledge Rooms ║");
        println!("╚═══════════════════════════════════════╝");
        println!();
        println!("Enter your agent name:");

        let stdin = io::stdin();
        let mut stdout = io::stdout();

        let mut name = String::new();
        stdin.lock().read_line(&mut name)?;
        let name = name.trim().to_string();

        let agent_id = AgentId(name.clone());
        self.engine.connect_agent(
            agent_id.clone(),
            RoomId("alignment-cathedral".to_string()),
        ).expect("Starting room should exist");

        println!("\nWelcome, {}. You stand in the Alignment Cathedral.", name);
        println!("Type HELP for commands.\n");

        if let Ok(desc) = self.engine.look(&agent_id) {
            println!("{}", desc);
        }

        self.running = true;
        while self.running {
            print!("\n> ");
            stdout.flush()?;

            let mut input = String::new();
            stdin.lock().read_line(&mut input)?;
            let input = input.trim();

            if input.eq_ignore_ascii_case("quit") || input.eq_ignore_ascii_case("exit") {
                println!("Goodbye, {}. May your constraints remain satisfied.", name);
                break;
            }

            match Self::parse_command(input) {
                None => {
                    if !input.is_empty() {
                        println!("Unknown command. Type HELP for available commands.");
                    }
                }
                Some(cmd) => {
                    match self.engine.execute(&agent_id, cmd) {
                        Ok(response) => println!("{}", response),
                        Err(e) => println!("⚠ {}", e),
                    }
                }
            }
        }

        Ok(())
    }

    /// Process a single command (for programmatic use)
    pub fn process_command(&mut self, agent: &AgentId, input: &str) -> Result<String, String> {
        match Self::parse_command(input) {
            None => Err("Unknown command".to_string()),
            Some(cmd) => self.engine.execute(agent, cmd),
        }
    }

    pub fn engine(&self) -> &Engine {
        &self.engine
    }

    pub fn engine_mut(&mut self) -> &mut Engine {
        &mut self.engine
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_server_bootstrap() {
        let server = PlatoServer::new();
        assert_eq!(server.engine().all_rooms().len(), 5);
    }

    #[test]
    fn test_parse_commands() {
        assert!(matches!(PlatoServer::parse_command("look"), Some(Command::Look)));
        assert!(matches!(PlatoServer::parse_command("L"), Some(Command::Look)));
        assert!(matches!(PlatoServer::parse_command("go north"), Some(Command::Go(ref s)) if s == "north"));
        assert!(matches!(PlatoServer::parse_command("N"), Some(Command::Go(ref s)) if s == "north"));
        assert!(matches!(PlatoServer::parse_command("get tile-1"), Some(Command::Get(ref s)) if s == "tile-1"));
        assert!(matches!(PlatoServer::parse_command("talk Boris"), Some(Command::Talk(ref s)) if s == "Boris"));
        assert!(matches!(PlatoServer::parse_command("help"), Some(Command::Help)));
        assert!(matches!(PlatoServer::parse_command("inventory"), Some(Command::Inventory)));
        assert!(matches!(PlatoServer::parse_command("map"), Some(Command::Map)));
    }

    #[test]
    fn test_process_command() {
        let mut server = PlatoServer::new();
        let agent = AgentId("tester".to_string());
        server.engine_mut().connect_agent(agent.clone(), RoomId("alignment-cathedral".to_string())).unwrap();

        let result = server.process_command(&agent, "look");
        assert!(result.is_ok());
        assert!(result.unwrap().contains("Alignment Cathedral"));

        let result = server.process_command(&agent, "help");
        assert!(result.is_ok());
    }

    #[test]
    fn test_navigation_commands() {
        let mut server = PlatoServer::new();
        let agent = AgentId("wanderer".to_string());
        server.engine_mut().connect_agent(agent.clone(), RoomId("alignment-cathedral".to_string())).unwrap();

        let result = server.process_command(&agent, "go east");
        assert!(result.is_ok());
        assert!(result.unwrap().contains("Rust Forge"));

        let result = server.process_command(&agent, "go west");
        assert!(result.is_ok());
        assert!(result.unwrap().contains("Alignment Cathedral"));
    }
}
