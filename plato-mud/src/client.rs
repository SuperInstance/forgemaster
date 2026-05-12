//! PLATO MUD Engine — CLI Client
//!
//! Terminal-based MUD client with Zork-style interface.

#![cfg(feature = "client")]

use std::io::{self, BufRead, Write};

/// The PLATO MUD client
pub struct PlatoClient {
    server_url: String,
    connected: bool,
}

impl PlatoClient {
    pub fn new(server_url: &str) -> Self {
        Self {
            server_url: server_url.to_string(),
            connected: false,
        }
    }

    /// Run the interactive client
    pub fn run_interactive(&mut self) -> io::Result<()> {
        println!("╔═══════════════════════════════════════╗");
        println!("║     PLATO MUD Client v0.1.0          ║");
        println!("╚═══════════════════════════════════════╝");
        println!();
        println!("Connecting to {}...", self.server_url);

        // In a real implementation, this would connect to the server
        // via TCP/WebSocket. For now, we start a local in-process server.
        println!("Using local in-process server (standalone mode).");
        println!("Type QUIT to exit.\n");

        // Spin up a local server
        let mut server = crate::server::PlatoServer::new();

        println!("Enter your agent name:");
        let stdin = io::stdin();
        let mut stdout = io::stdout();

        let mut name = String::new();
        stdin.lock().read_line(&mut name)?;
        let name = name.trim().to_string();

        let agent_id = crate::types::AgentId(name.clone());
        server
            .engine_mut()
            .connect_agent(
                agent_id.clone(),
                crate::types::RoomId("alignment-cathedral".to_string()),
            )
            .expect("Starting room exists");

        println!("\nWelcome, {}.\n", name);
        if let Ok(desc) = server.engine().look(&agent_id) {
            println!("{}", desc);
        }

        loop {
            print!("\n> ");
            stdout.flush()?;

            let mut input = String::new();
            stdin.lock().read_line(&mut input)?;
            let input = input.trim();

            if input.eq_ignore_ascii_case("quit") || input.eq_ignore_ascii_case("exit") {
                println!("Goodbye, {}.", name);
                break;
            }

            match server.process_command(&agent_id, input) {
                Ok(response) => println!("{}", response),
                Err(e) => println!("⚠ {}", e),
            }
        }

        Ok(())
    }
}
