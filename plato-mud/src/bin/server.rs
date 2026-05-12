//! PLATO MUD Server binary

fn main() {
    let mut server = plato_mud::server::PlatoServer::new();
    if let Err(e) = server.run_interactive() {
        eprintln!("Server error: {}", e);
        std::process::exit(1);
    }
}
