use std::env;
use std::path::PathBuf;

fn main() {
    let bridge_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    cc::Build::new()
        .file(PathBuf::from(&bridge_dir).join("eisenstein_bridge.c"))
        .include(&bridge_dir)
        .opt_level(3)
        .flag("-march=native")
        .flag("-std=c11")
        .compile("eisenstein_bridge");
}
