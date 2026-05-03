use crate::types::*;
use gds21::{GdsLibrary, GdsStructure, GdsElement, GdsBoundary, GdsPath, GdsStrans};
use gds21::units::GdsUnits;

// ------------------------------
// Via Pattern Generator
// ------------------------------
pub struct ViaGeneratorConfig {
    pub x_pitch: u32, // Nanometers
    pub y_pitch: u32,
    pub via_size: u32,
}

impl Default for ViaGeneratorConfig {
    fn default() -> Self {
        Self {
            x_pitch: 200, // 200nm pitch
            y_pitch: 200,
            via_size: 100, // 100nm via
        }
    }
}

pub fn generate_vias(
    assignment: &Assignment,
    config: &ViaGeneratorConfig,
) -> Vec<ViaPattern> {
    assignment.0.iter()
        .filter_map(|(&(x, y), &weight)| match weight {
            TernaryWeight::PlusOne => Some(ViaPattern { x, y, polarity: ViaPolarity::Positive }),
            TernaryWeight::MinusOne => Some(ViaPattern { x, y, polarity: ViaPolarity::Negative }),
            TernaryWeight::Zero => None,
        })
        .collect()
}

// ------------------------------
// GDSII Export
// ------------------------------
pub struct GdsExportConfig {
    pub positive_via_layer: u32,
    pub negative_via_layer: u32,
    pub units: GdsUnits,
}

impl Default for GdsExportConfig {
    fn default() -> Self {
        Self {
            positive_via_layer: 10,
            negative_via_layer: 11,
            units: GdsUnits::Nanometer,
        }
    }
}

pub fn export_gds(
    vias: &[ViaPattern],
    via_config: &ViaGeneratorConfig,
    gds_config: &GdsExportConfig,
    output_path: &std::path::Path,
) -> Result<(), Guard2MaskError> {
    // Create GDSII library
    let mut lib = GdsLibrary::new("GUARD2MASK_MASK", gds_config.units);
    let mut top = GdsStructure::new("CROSSBAR_TOP");

    for via in vias {
        // Calculate via position (center)
        let x_center = (via.x * via_config.x_pitch) as i32;
        let y_center = (via.y * via_config.y_pitch) as i32;
        let half_size = (via_config.via_size / 2) as i32;

        // Create via boundary (square)
        let layer = match via.polarity {
            ViaPolarity::Positive => gds_config.positive_via_layer,
            ViaPolarity::Negative => gds_config.negative_via_layer,
        };

        let via_shape = GdsBoundary::from_xy(
            vec![
                (x_center - half_size, y_center - half_size),
                (x_center + half_size, y_center - half_size),
                (x_center + half_size, y_center + half_size),
                (x_center - half_size, y_center + half_size),
                (x_center - half_size, y_center - half_size), // Close path
            ],
            layer,
            0, // Datatype
        );

        top.elements.push(GdsElement::Boundary(via_shape));
    }

    lib.structures.push(top);
    lib.save(output_path)
        .map_err(|e| Guard2MaskError::GdsExportError(e.to_string()))?;

    Ok(())
}
