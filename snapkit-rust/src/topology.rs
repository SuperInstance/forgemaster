//! Snap topologies — the Platonic classification of attention shapes.
//!
//! Each topology defines a different "flavor of randomness" and a different
//! lattice structure for compressing information. The finite classification
//! (ADE types) means the space of possible attention topologies is explorable.
//!
//! The topology is the INVARIANT that transfers across domains. When two
//! domains have the same snap topology, calibrated tolerances transfer directly.

/// The type of a snap function's topology — each a different "flavor of randomness."
///
/// These correspond directly to the Platonic solid / ADE classification:
/// - Binary: A₁, coin flip, true/false
/// - Hexagonal: A₂, Eisenstein lattice, densest 2D packing
/// - Cubic: ℤⁿ standard grid
/// - Octahedral: 8 directions, ±axes
/// - Tetrahedral: A₃, 4 categories
/// - Dodecahedral: rich combinatorial
/// - Icosahedral: golden-ratio clusters
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SnapTopology {
    /// Binary (A₁) — coin flip, 2 outcomes
    Binary,
    /// Categorical (tetrahedral) — 4 categories
    Categorical,
    /// Hexagonal (A₂, Eisenstein) — 6-fold, densest 2D, PID
    Hexagonal,
    /// Cubic (ℤⁿ) — standard grid
    Cubic,
    /// Octahedral — 8 directions
    Octahedral,
    /// Uniform — dN spread
    Uniform,
    /// Bell — 2d6 peaked distribution
    Bell,
    /// Gradient — near-continuous
    Gradient,
}

impl SnapTopology {
    /// Human-readable name of this topology.
    pub fn name(&self) -> &'static str {
        match self {
            SnapTopology::Binary => "Binary",
            SnapTopology::Categorical => "Categorical",
            SnapTopology::Hexagonal => "Hexagonal",
            SnapTopology::Cubic => "Cubic",
            SnapTopology::Octahedral => "Octahedral",
            SnapTopology::Uniform => "Uniform",
            SnapTopology::Bell => "Bell",
            SnapTopology::Gradient => "Gradient",
        }
    }

    /// Number of symmetry axes / fold symmetry.
    pub fn fold_symmetry(&self) -> u32 {
        match self {
            SnapTopology::Binary => 2,
            SnapTopology::Categorical => 4,
            SnapTopology::Hexagonal => 6,
            SnapTopology::Cubic => 6,  // cube axis symmetry
            SnapTopology::Octahedral => 8,
            SnapTopology::Uniform => 1,
            SnapTopology::Bell => 1,
            SnapTopology::Gradient => 1,
        }
    }

    /// Whether this topology is provably optimal for its dimension.
    ///
    /// Only A₂ (Hexagonal) in 2D and E₈ in 8D are provably optimal
    /// for densest packing. Here we just report A₂.
    pub fn is_provably_optimal(&self) -> bool {
        matches!(self, SnapTopology::Hexagonal)
    }

    /// The ADE root system type if applicable.
    pub fn ade_type(&self) -> Option<&'static str> {
        match self {
            SnapTopology::Binary => Some("A₁"),
            SnapTopology::Hexagonal => Some("A₂"),
            SnapTopology::Categorical => Some("A₃"),
            _ => None,
        }
    }

    /// Recommended default tolerance for this topology.
    ///
    /// For Hexagonal (A₂), the covering radius is ~0.577, so
    /// a tolerance of 0.1 is a good default that captures
    /// ~17% of the Voronoi cell.
    pub fn default_tolerance(&self) -> f64 {
        match self {
            SnapTopology::Binary => 0.25,
            SnapTopology::Categorical => 0.2,
            SnapTopology::Hexagonal => 0.1,
            SnapTopology::Cubic => 0.15,
            SnapTopology::Octahedral => 0.2,
            SnapTopology::Uniform => 0.1,
            SnapTopology::Bell => 0.3,
            SnapTopology::Gradient => 0.05,
        }
    }
}

/// ADE root system data.
///
/// Each ADE type defines a finite reflection group with specific
/// properties used in constraint topology and snap theory.
#[derive(Debug, Clone)]
pub struct ADEData {
    /// ADE type name (e.g. "A₂", "E₈")
    pub name: &'static str,
    /// Rank of the root system
    pub rank: usize,
    /// Number of roots
    pub num_roots: usize,
    /// Coxeter number
    pub coxeter_number: u32,
    /// Associated Platonic solid, if any
    pub platonic_solid: Option<&'static str>,
    /// Description
    pub description: &'static str,
}

/// Metadata for all ADE root systems.
pub const ADE_SYSTEMS: &[ADEData] = &[
    ADEData { name: "A₁", rank: 1, num_roots: 2, coxeter_number: 2, platonic_solid: None, description: "Binary (coin flip)" },
    ADEData { name: "A₂", rank: 2, num_roots: 6, coxeter_number: 3, platonic_solid: None, description: "Hexagonal (Eisenstein lattice)" },
    ADEData { name: "A₃", rank: 3, num_roots: 12, coxeter_number: 4, platonic_solid: Some("Tetrahedron"), description: "Tetrahedral (4 categories)" },
    ADEData { name: "A₄", rank: 4, num_roots: 20, coxeter_number: 5, platonic_solid: None, description: "5-chain" },
    ADEData { name: "D₄", rank: 4, num_roots: 24, coxeter_number: 6, platonic_solid: None, description: "Triality (D₄ symmetry)" },
    ADEData { name: "D₅", rank: 5, num_roots: 40, coxeter_number: 8, platonic_solid: None, description: "5-fork" },
    ADEData { name: "E₆", rank: 6, num_roots: 72, coxeter_number: 12, platonic_solid: Some("Tetrahedron"), description: "Binary tetrahedral group" },
    ADEData { name: "E₇", rank: 7, num_roots: 126, coxeter_number: 18, platonic_solid: Some("Cube/Octahedron"), description: "Binary octahedral group" },
    ADEData { name: "E₈", rank: 8, num_roots: 240, coxeter_number: 30, platonic_solid: Some("Dodecahedron/Icosahedron"), description: "Binary icosahedral group — the 'noble gas'" },
];

/// Look up ADE data by type name.
pub fn ade_lookup(name: &str) -> Option<&'static ADEData> {
    ADE_SYSTEMS.iter().find(|d| d.name == name)
}

/// Recommend the best snap topology for given requirements.
///
/// # Examples
///
/// ```
/// use snapkit::{recommend_topology, SnapTopology};
///
/// let topo = recommend_topology(None, Some(2), None);
/// assert_eq!(topo, SnapTopology::Hexagonal); // A₂ optimal in 2D
/// ```
pub fn recommend_topology(
    num_categories: Option<usize>,
    dimension: Option<usize>,
) -> SnapTopology {
    match num_categories {
        Some(2) => return SnapTopology::Binary,
        Some(4) => return SnapTopology::Categorical,
        _ => {}
    }
    if dimension == Some(2) {
        return SnapTopology::Hexagonal; // A₂ is provably optimal in 2D
    }
    // Default to Hexagonal — the universal solvent
    SnapTopology::Hexagonal
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ade_systems() {
        assert_eq!(ADE_SYSTEMS.len(), 9);
        assert_eq!(ADE_SYSTEMS[0].name, "A₁");
        assert_eq!(ADE_SYSTEMS[8].name, "E₈");
    }

    #[test]
    fn test_ade_lookup() {
        let a2 = ade_lookup("A₂").unwrap();
        assert_eq!(a2.rank, 2);
        assert_eq!(a2.num_roots, 6);
        assert_eq!(a2.coxeter_number, 3);
    }

    #[test]
    fn test_recommend_binary() {
        assert_eq!(recommend_topology(Some(2), None), SnapTopology::Binary);
    }

    #[test]
    fn test_recommend_2d() {
        assert_eq!(recommend_topology(None, Some(2)), SnapTopology::Hexagonal);
    }

    #[test]
    fn test_default_tolerance() {
        assert!((SnapTopology::Hexagonal.default_tolerance() - 0.1).abs() < 1e-10);
        assert!((SnapTopology::Binary.default_tolerance() - 0.25).abs() < 1e-10);
    }

    #[test]
    fn test_provably_optimal() {
        assert!(SnapTopology::Hexagonal.is_provably_optimal());
        assert!(!SnapTopology::Cubic.is_provably_optimal());
    }
}
