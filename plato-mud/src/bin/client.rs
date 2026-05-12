//! PLATO MUD Client binary

fn main() {
    let mut client = plato_mud::client::PlatoClient::new("localhost:7777");
    if let Err(e) = client.run_interactive() {
        eprintln!("Client error: {}", e);
        std::process::exit(1);
    }
}
