//! Binary wire format — zero-copy decode, 2-byte magic.
//!
//! Wire layout:
//!   [0..2]   magic 0x464C ("FL")
//!   [2..4]   instruction count (u16 LE)
//!   [4..]    instruction array (24 bytes each)

use crate::instruction::{FluxInstruction, FLUX_INSTRUCTION_SIZE};
use crate::vm::FluxError;

/// Wire magic: "FL" = 0x464C.
const MAGIC: [u8; 2] = [0x46, 0x4C];

/// Encode instructions into a byte buffer. Returns bytes written.
///
/// Panics if buffer is too small (need at least 4 + count × 24 bytes).
pub fn encode(instructions: &[FluxInstruction], buf: &mut [u8]) -> usize {
    let needed = 4 + instructions.len() * FLUX_INSTRUCTION_SIZE;
    assert!(buf.len() >= needed, "encode buffer too small");

    buf[0] = MAGIC[0];
    buf[1] = MAGIC[1];
    let count = instructions.len() as u16;
    buf[2] = count as u8;
    buf[3] = (count >> 8) as u8;

    let src = unsafe {
        core::slice::from_raw_parts(
            instructions.as_ptr() as *const u8,
            instructions.len() * FLUX_INSTRUCTION_SIZE,
        )
    };
    buf[4..4 + src.len()].copy_from_slice(src);
    needed
}

/// Decode a byte buffer as FLUX instructions — zero-copy.
///
/// Returns a slice of `FluxInstruction` pointing into the original buffer.
/// The buffer must be 4-byte aligned for correct f64 access on ARM.
pub fn decode(buf: &[u8]) -> Result<&[FluxInstruction], FluxError> {
    if buf.len() < 4 { return Err(FluxError::InvalidInstruction(0)); }
    if buf[0] != MAGIC[0] || buf[1] != MAGIC[1] {
        return Err(FluxError::InvalidInstruction(buf[0]));
    }
    let count = u16::from_le_bytes([buf[2], buf[3]]) as usize;
    let data_start = 4;
    let data_len = count * FLUX_INSTRUCTION_SIZE;
    if buf.len() < data_start + data_len {
        return Err(FluxError::InvalidInstruction(0));
    }

    // Safety: we're reinterpreting bytes as FluxInstruction.
    // Caller must ensure buf outlives the returned slice and alignment is OK.
    let ptr = buf[data_start..].as_ptr() as *const FluxInstruction;
    Ok(unsafe { core::slice::from_raw_parts(ptr, count) })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::opcode::FluxOpcode;

    #[test]
    fn roundtrip() {
        let instrs = [
            FluxInstruction::new(FluxOpcode::Load, 42.0, 0.0),
            FluxInstruction::new(FluxOpcode::Halt, 0.0, 0.0),
        ];
        let mut buf = [0u8; 128];
        let n = encode(&instrs, &mut buf);
        assert_eq!(n, 4 + 2 * FLUX_INSTRUCTION_SIZE);

        let decoded = decode(&buf[..n]).unwrap();
        assert_eq!(decoded.len(), 2);
    }
}
