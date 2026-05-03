//! # cocapn-glue-core
//!
//! Cross-tier wire protocol unifying all FLUX ISA packages (mini/std/edge/thor).
//! `#![no_std]` by default. Enable `std` feature for heap types, `async` for tokio transports.

#![no_std]

extern crate alloc;

pub mod config;
pub mod discovery;
pub mod plato;
pub mod provenance;
pub mod wire;

pub use wire::TierId;
