//! Capability bitmask for fleet discovery.

use serde::{Serialize, Deserialize};

/// Individual capabilities a peer may advertise.
#[repr(u32)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Capability {
    NoStd = 1 << 0,
    Async = 1 << 1,
    Cuda  = 1 << 2,
    Plato = 1 << 3,
    Ffi   = 1 << 4,
    Python = 1 << 5,
}

/// Bitmask of capabilities.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Capabilities(pub u32);

impl Capabilities {
    pub fn none() -> Self {
        Capabilities(0)
    }

    pub fn all() -> Self {
        Capabilities(0x3F)
    }

    pub fn set(&mut self, cap: Capability) {
        self.0 |= cap as u32;
    }

    pub fn clear(&mut self, cap: Capability) {
        self.0 &= !(cap as u32);
    }

    pub fn has(&self, cap: Capability) -> bool {
        (self.0 & cap as u32) != 0
    }

    pub fn raw(&self) -> u32 {
        self.0
    }
}

impl From<u32> for Capabilities {
    fn from(v: u32) -> Self {
        Capabilities(v)
    }
}

impl From<Capabilities> for u32 {
    fn from(c: Capabilities) -> Self {
        c.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn capability_set_clear() {
        let mut caps = Capabilities::none();
        assert!(!caps.has(Capability::NoStd));
        caps.set(Capability::NoStd);
        assert!(caps.has(Capability::NoStd));
        caps.set(Capability::Cuda);
        assert!(caps.has(Capability::Cuda));
        assert!(!caps.has(Capability::Async));
        caps.clear(Capability::NoStd);
        assert!(!caps.has(Capability::NoStd));
    }

    #[test]
    fn capability_all() {
        let caps = Capabilities::all();
        assert!(caps.has(Capability::NoStd));
        assert!(caps.has(Capability::Cuda));
        assert!(caps.has(Capability::Python));
    }
}
