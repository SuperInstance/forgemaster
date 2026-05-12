//! PLATO MUD Engine — Constraint-Theory Knowledge Rooms with FLUX Transference
//!
//! A Rust MUD engine where rooms are computational domains, tiles are
//! structured knowledge objects, and FLUX carries zeitgeist between rooms.
//! All actions pass through alignment constraints.

#![cfg_attr(not(feature = "std"), no_std)]

extern crate alloc;

pub mod types;
pub mod engine;
pub mod alignment;
pub mod flux;
pub mod transport;

#[cfg(feature = "server")]
pub mod server;

#[cfg(feature = "client")]
pub mod client;

pub use types::*;
pub use engine::Engine;
pub use alignment::AlignmentChecker;
pub use flux::FluxManager;
