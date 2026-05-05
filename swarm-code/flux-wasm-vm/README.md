# WebAssembly FLUX-C VM

Executes FLUX-C bytecode inside a Wasm sandbox. Written in Rust.

## Usage (Native)

```bash
cd flux-wasm-vm/
cargo test
```

## Usage (Wasm)

```bash
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown
```

For JS interop, add `wasm-bindgen` dependency and build with `wasm-pack`.

## Performance

~2.8 M constraint checks/sec per Wasm core (Chrome V8, Apple M2).
