//! GUARD-to-FLUX compiler — translates constraint checks into FLUX bytecode
//!
//! Compilation rules:
//! - range(min, max) → PUSH val, BITMASK_RANGE min max, ASSERT
//! - whitelist(v1,v2,...) → sequential PUSH/EQ with OR chain, ASSERT
//! - bitmask(mask) → PUSH mask, CHECK_DOMAIN, ASSERT  
//! - thermal(budget) → PUSH budget, CMP_GE, ASSERT
//! - sparsity(count) → PUSH count, CMP_GE, ASSERT

use crate::parser::{Constraint, Check, Priority, GuardItem, extract_constraints};

/// FLUX opcodes used by the compiler
mod op {
    pub const PUSH: u8 = 0x00;
    pub const AND: u8 = 0x09;
    pub const EQ: u8 = 0x0F;
    pub const OR: u8 = 0x0A;
    pub const JZ: u8 = 0x16;
    pub const JNZ: u8 = 0x17;
    pub const HALT: u8 = 0x1A;
    pub const ASSERT: u8 = 0x1B;
    pub const CHECK_DOMAIN: u8 = 0x1C;
    pub const BITMASK_RANGE: u8 = 0x1D;
    pub const CMP_GE: u8 = 0x24;
    pub const GUARD_TRAP: u8 = 0x20;
    pub const NOP: u8 = 0x27;
}

/// Compilation result
pub struct CompiledProgram {
    pub bytecode: Vec<u8>,
    pub constraint_count: usize,
    pub hard_count: usize,
    pub soft_count: usize,
}

/// Compile GUARD items into FLUX bytecode
pub fn compile(items: &[GuardItem]) -> CompiledProgram {
    let constraints = extract_constraints(items);
    let mut bc = Vec::new();
    let mut hard_count = 0;
    let mut soft_count = 0;

    for constraint in &constraints {
        match constraint.priority {
            Priority::Hard => hard_count += 1,
            Priority::Soft => soft_count += 1,
            Priority::Default => {}
        }

        for check in &constraint.checks {
            compile_check(check, &mut bc);
        }
    }

    // If any check failed, GUARD_TRAP would have already fired via ASSERT
    // If we reach here, all constraints passed
    bc.push(op::HALT);

    // Append failure handler at the end (for JFAIL targets)
    let fail_addr = bc.len();
    bc.push(op::GUARD_TRAP);

    CompiledProgram {
        bytecode: bc,
        constraint_count: constraints.len(),
        hard_count,
        soft_count,
    }
}

fn compile_check(check: &Check, bc: &mut Vec<u8>) {
    match check {
        Check::Range { start, end } => {
            // Assume test value is already on stack from caller
            // BITMASK_RANGE lo hi → pushes 1 if in range, 0 if not
            let lo = *start as u8;
            let hi = *end as u8;
            // We need the value on stack — compile as self-contained test
            // PUSH test_value, BITMASK_RANGE lo, hi, ASSERT
            // For now, emit the range check that assumes value is pre-pushed
            bc.push(op::BITMASK_RANGE);
            bc.push(lo);
            bc.push(hi);
            bc.push(op::ASSERT);
        }
        Check::Whitelist(values) => {
            // For small whitelists, use sequential EQ + OR
            // Push value to test (placeholder 0xFF = match-anything for demo)
            // Then check: EQ v1, JNZ pass, EQ v2, JNZ pass, ... PUSH 0, ASSERT
            let pass_offset = values.len() * 3 + 3; // each EQ+PUSH+JNZ = 3, plus PUSH 0 + ASSERT + NOP
            for (i, val) in values.iter().enumerate() {
                let val_bytes = val.as_bytes();
                let val_byte = if val_bytes.len() == 1 { val_bytes[0] } else { (i + 1) as u8 };
                bc.push(op::PUSH);
                bc.push(val_byte);
                bc.push(op::EQ); // compare stack top with pushed value
                // If EQ returned 1, we matched — skip to pass
                let current_len = bc.len();
                let jump_target = bc.len() + 2 + (values.len() - i - 1) * 3 + 3;
                bc.push(op::JNZ);
                bc.push(jump_target as u8);
                // POP the comparison result if not matched
            }
            // No match found — push 0 and assert fail
            bc.push(op::PUSH);
            bc.push(0);
            bc.push(op::ASSERT);
            // Pass target — NOP (all good)
            bc.push(op::NOP);
        }
        Check::Bitmask(mask) => {
            // PUSH mask, CHECK_DOMAIN, ASSERT
            bc.push(op::PUSH);
            bc.push((*mask & 0xFF) as u8);
            bc.push(op::CHECK_DOMAIN);
            bc.push((*mask & 0xFF) as u8);
            bc.push(op::ASSERT);
        }
        Check::Thermal(budget) => {
            // PUSH budget, CMP_GE, ASSERT
            bc.push(op::PUSH);
            bc.push(*budget as u8);
            bc.push(op::CMP_GE);
            bc.push(op::ASSERT);
        }
        Check::Sparsity(count) => {
            // PUSH count, CMP_GE, ASSERT
            bc.push(op::PUSH);
            bc.push(*count as u8);
            bc.push(op::CMP_GE);
            bc.push(op::ASSERT);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parser::parse_guard;

    #[test]
    fn compile_empty() {
        let items = parse_guard("").unwrap();
        let result = compile(&items);
        assert_eq!(result.constraint_count, 0);
        // Should be HALT + GUARD_TRAP
        assert!(result.bytecode.contains(&op::HALT));
        assert!(result.bytecode.contains(&op::GUARD_TRAP));
    }

    #[test]
    fn compile_range() {
        let src = "constraint alt @priority(HARD) { range(0, 150) }";
        let items = parse_guard(src).unwrap();
        let result = compile(&items);
        assert_eq!(result.constraint_count, 1);
        assert_eq!(result.hard_count, 1);
        // Should contain BITMASK_RANGE with lo=0, hi=150
        let range_pos = result.bytecode.iter().position(|&b| b == op::BITMASK_RANGE).unwrap();
        assert_eq!(result.bytecode[range_pos + 1], 0); // lo
        assert_eq!(result.bytecode[range_pos + 2], 150); // hi
        assert!(result.bytecode.contains(&op::ASSERT));
    }

    #[test]
    fn compile_bitmask() {
        let src = "constraint sensor { bitmask(63) }";
        let items = parse_guard(src).unwrap();
        let result = compile(&items);
        // Should contain CHECK_DOMAIN with mask=63
        let cd_pos = result.bytecode.iter().position(|&b| b == op::CHECK_DOMAIN).unwrap();
        assert_eq!(result.bytecode[cd_pos + 1], 63);
        assert!(result.bytecode.contains(&op::PUSH));
        assert!(result.bytecode.contains(&op::ASSERT));
    }

    #[test]
    fn compile_multi_constraint() {
        let src = r#"
            constraint altitude @priority(HARD) { range(0, 150) }
            constraint power @priority(SOFT) { thermal(2) }
        "#;
        let items = parse_guard(src).unwrap();
        let result = compile(&items);
        assert_eq!(result.constraint_count, 2);
        assert_eq!(result.hard_count, 1);
        assert_eq!(result.soft_count, 1);
        // Should have BITMASK_RANGE for altitude and CMP_GE for thermal
        assert!(result.bytecode.contains(&op::BITMASK_RANGE));
        assert!(result.bytecode.contains(&op::CMP_GE));
    }

    #[test]
    fn compile_whitelist() {
        let src = "constraint cmd { whitelist(A, B, C) }";
        let items = parse_guard(src).unwrap();
        let result = compile(&items);
        // Should have EQ and JNZ for whitelist checks
        assert!(result.bytecode.contains(&op::EQ));
        assert!(result.bytecode.contains(&op::JNZ));
        assert!(result.bytecode.contains(&op::ASSERT));
    }
}


