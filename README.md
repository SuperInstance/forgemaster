# forgemaster

Build pipeline coordinator for multi-crate projects.

**Status:** Early stage — scaffolded, building, tests passing.

## What it does

Orchestrates build and packaging steps across crates that make up a larger
agent system. Handles dependency ordering, artifact collection, and
reproducible builds so you don't have to wire it yourself.

## Building

```sh
cargo build
cargo test
```

## License

Licensed under either of [Apache License, Version 2.0](LICENSE-APACHE) or
[MIT license](LICENSE-MIT) at your option.
