//! PLATO MUD Engine — Constraint-Theory Knowledge Rooms with FLUX Transference
//!
//! A Rust MUD engine where rooms are computational domains, tiles are
//! structured knowledge objects, and FLUX carries zeitgeist between rooms.
//! All actions pass through alignment constraints.

#![cfg_attr(not(feature = "std"), no_std)]

extern crate alloc;

pub mod alignment;
pub mod engine;
pub mod flux;
pub mod transport;
pub mod types;

#[cfg(feature = "server")]
pub mod server;

#[cfg(feature = "client")]
pub mod client;

pub use alignment::AlignmentChecker;
pub use engine::Engine;
pub use flux::FluxManager;
pub use types::*;
