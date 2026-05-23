//! Cocapn Fleet CLI Theme — The Abyssal Terminal
//!
//! Consistent output formatting for fleet tools.
//! Dark background, cyan/magenta accents, amber warnings.
//! Standardized `[TAG  ]` prefix format for agent-parseable output.

pub mod theme;
pub mod tide;
pub mod format;

pub use theme::*;
pub use tide::*;
pub use format::*;
