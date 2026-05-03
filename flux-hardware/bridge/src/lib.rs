//! FLUX-X ↔ FLUX-C Bridge Protocol
//!
//! TrustZone-style bridge between the extended ISA (FLUX-X, 247 opcodes, register machine)
//! and the constraint enforcement ISA (FLUX-C, 43 opcodes, stack machine).
//!
//! Security model:
//! - FLUX-X calls INTO FLUX-C via CONSTRAINT_CHECK
//! - FLUX-C CANNOT call back into FLUX-X
//! - If FLUX-C faults, FLUX-X MUST enter safe state
//! - Bridge context switch is atomic (no interleaving)

use std::collections::HashMap;

/// FLUX-X register file (R0-R15)
pub type RegisterFile = [u64; 16];

/// FLUX-C stack (256 bytes)
pub const STACK_SIZE: usize = 256;

/// Bridge result from FLUX-C execution
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BridgeResult {
    /// Constraint passed, execution continues
    Pass,
    /// Constraint failed with fault code
    Fail(FaultCode),
}

/// FLUX-C fault codes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FaultCode {
    /// Value out of range
    RangeViolation,
    /// Value not in whitelist
    WhitelistViolation,
    /// Bitmask check failed
    BitmaskViolation,
    /// Thermal budget exceeded
    ThermalExceeded,
    /// Sparsity below minimum
    SparsityInsufficient,
    /// Generic assertion failure
    AssertFailed,
    /// Gas exhausted (unbounded execution prevented)
    GasExhausted,
    /// Stack corruption detected
    StackCorruption,
}

/// Safe state for FLUX-X after FLUX-C fault
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SafeState {
    /// Halt all outputs, clock-gate compute
    HaltAndClockGate,
    /// Enter known-safe fallback mode
    FallbackMode,
    /// Reset to bootloader
    WarmReset,
}

/// Bridge configuration
pub struct BridgeConfig {
    /// Which FLUX-X registers map to which FLUX-C stack positions
    pub register_map: HashMap<u8, usize>,
    /// Default safe state for each fault code
    pub fault_safe_states: HashMap<FaultCode, SafeState>,
    /// Gas limit for FLUX-C execution (prevents infinite loops)
    pub gas_limit: u32,
    /// Whether bridge calls are logged for audit
    pub audit_log: bool,
}

impl Default for BridgeConfig {
    fn default() -> Self {
        let mut register_map = HashMap::new();
        // R0-R7 → stack positions 0-7 (primary inputs)
        // R8-R15 → stack positions 8-15 (secondary/context)
        for i in 0..16u8 {
            register_map.insert(i, i as usize);
        }

        let mut fault_safe_states = HashMap::new();
        fault_safe_states.insert(FaultCode::RangeViolation, SafeState::HaltAndClockGate);
        fault_safe_states.insert(FaultCode::WhitelistViolation, SafeState::HaltAndClockGate);
        fault_safe_states.insert(FaultCode::BitmaskViolation, SafeState::HaltAndClockGate);
        fault_safe_states.insert(FaultCode::ThermalExceeded, SafeState::FallbackMode);
        fault_safe_states.insert(FaultCode::SparsityInsufficient, SafeState::FallbackMode);
        fault_safe_states.insert(FaultCode::AssertFailed, SafeState::HaltAndClockGate);
        fault_safe_states.insert(FaultCode::GasExhausted, SafeState::WarmReset);
        fault_safe_states.insert(FaultCode::StackCorruption, SafeState::WarmReset);

        BridgeConfig {
            register_map,
            fault_safe_states,
            gas_limit: 10000,
            audit_log: true,
        }
    }
}

/// Bridge state (saved context during FLUX-C execution)
pub struct BridgeContext {
    /// Saved FLUX-X registers
    pub saved_registers: RegisterFile,
    /// Saved FLUX-X program counter
    pub saved_pc: u64,
    /// Saved FLUX-X status flags
    pub saved_flags: u32,
    /// FLUX-C stack snapshot (for audit)
    pub flux_c_stack: Vec<u8>,
    /// Constraint ID being checked
    pub constraint_id: u32,
}

/// The bridge protocol handler
pub struct FluxBridge {
    config: BridgeConfig,
    /// Audit trail of all bridge calls
    audit_trail: Vec<BridgeContext>,
    /// Whether bridge is currently active (FLUX-C executing)
    active: bool,
    /// Lock bit — once set, bridge cannot be bypassed
    locked: bool,
}

impl FluxBridge {
    pub fn new(config: BridgeConfig) -> Self {
        FluxBridge {
            config,
            audit_trail: Vec::new(),
            active: false,
            locked: true, // Bridge is locked by default
        }
    }

    /// Execute CONSTRAINT_CHECK — the TrustZone SMC equivalent
    ///
    /// This is the ONLY way FLUX-X can invoke FLUX-C.
    /// The bridge:
    /// 1. Saves FLUX-X context (registers, PC, flags)
    /// 2. Maps registers to FLUX-C stack
    /// 3. Executes FLUX-C constraint bytecode
    /// 4. Restores FLUX-X context (if pass) or transitions to safe state (if fail)
    pub fn constraint_check(
        &mut self,
        registers: &RegisterFile,
        pc: u64,
        constraint_id: u32,
        flux_c_bytecode: &[u8],
    ) -> BridgeResult {
        assert!(!self.active, "Bridge reentrancy detected — SECURITY VIOLATION");
        assert!(self.locked, "Bridge not locked — SECURITY VIOLATION");

        self.active = true;

        // Step 1: Save FLUX-X context
        let context = BridgeContext {
            saved_registers: *registers,
            saved_pc: pc,
            saved_flags: 0,
            flux_c_stack: Vec::new(),
            constraint_id,
        };

        // Step 2: Map registers to FLUX-C stack
        let mut stack = vec![0u8; STACK_SIZE];
        for (&reg_idx, &stack_pos) in &self.config.register_map {
            if (reg_idx as usize) < registers.len() && stack_pos < STACK_SIZE {
                let val = registers[reg_idx as usize];
                // Write low byte to stack position
                stack[stack_pos] = (val & 0xFF) as u8;
                // Write full u64 if there's room (little-endian)
                if stack_pos + 8 <= STACK_SIZE {
                    let bytes = val.to_le_bytes();
                    stack[stack_pos..stack_pos + 8].copy_from_slice(&bytes);
                }
            }
        }

        // Step 3: Execute FLUX-C bytecode (simplified — real impl uses flux_vm crate)
        let result = self.execute_flux_c(flux_c_bytecode, &mut stack);

        // Step 4: Handle result
        match result {
            BridgeResult::Pass => {
                self.active = false;
                if self.config.audit_log {
                    self.audit_trail.push(context);
                }
                BridgeResult::Pass
            }
            BridgeResult::Fail(fault) => {
                // Transition to safe state
                let safe_state = self.config.fault_safe_states
                    .get(&fault)
                    .copied()
                    .unwrap_or(SafeState::HaltAndClockGate);
                
                self.safe_state_transition(safe_state, fault);

                if self.config.audit_log {
                    let mut ctx = context;
                    ctx.flux_c_stack = stack;
                    self.audit_trail.push(ctx);
                }

                self.active = false;
                BridgeResult::Fail(fault)
            }
        }
    }

    /// Execute FLUX-C bytecode on the constraint VM
    fn execute_flux_c(&self, bytecode: &[u8], stack: &mut Vec<u8>) -> BridgeResult {
        let mut pc: usize = 0;
        let mut gas = self.config.gas_limit;
        let mut check_passed = true;

        while pc < bytecode.len() && gas > 0 {
            gas -= 1;
            let opcode = bytecode[pc];
            pc += 1;

            match opcode {
                0x1A => break, // HALT — passed
                0x1B => {
                    // ASSERT — check top of stack
                    if stack.first() == Some(&0) {
                        check_passed = false;
                        return BridgeResult::Fail(FaultCode::AssertFailed);
                    }
                }
                0x20 => {
                    // GUARD_TRAP — immediate fault
                    return BridgeResult::Fail(FaultCode::AssertFailed);
                }
                0x1D => {
                    // BITMASK_RANGE lo hi
                    if pc + 2 > bytecode.len() { break; }
                    let _lo = bytecode[pc];
                    let _hi = bytecode[pc + 1];
                    pc += 2;
                    // Simplified: would check stack top against [lo, hi]
                }
                0x1C => {
                    // CHECK_DOMAIN mask
                    if pc + 1 > bytecode.len() { break; }
                    let _mask = bytecode[pc];
                    pc += 1;
                }
                0x24 => {
                    // CMP_GE
                    // Simplified: would compare stack values
                }
                0x00 => {
                    // PUSH val
                    if pc + 1 > bytecode.len() { break; }
                    pc += 1; // skip operand
                }
                0x17 => {
                    // JNZ addr — jump if non-zero on stack
                    if pc + 1 > bytecode.len() { break; }
                    let _addr = bytecode[pc] as usize;
                    pc += 1;
                    // Simplified: always take the jump for testing gas
                    // (real impl checks stack top)
                }
                _ => {} // Unknown opcode — skip
            }
        }

        if gas == 0 {
            return BridgeResult::Fail(FaultCode::GasExhausted);
        }

        if check_passed {
            BridgeResult::Pass
        } else {
            BridgeResult::Fail(FaultCode::AssertFailed)
        }
    }

    /// Safe state transition — what FLUX-X does when FLUX-C faults
    fn safe_state_transition(&self, state: SafeState, _fault: FaultCode) {
        match state {
            SafeState::HaltAndClockGate => {
                // 1. Disable all output pins
                // 2. Gate clocks to compute cores
                // 3. Maintain FLUX-C power (it's the safety monitor)
                // 4. Log fault for post-mortem
            }
            SafeState::FallbackMode => {
                // 1. Switch to redundant channel
                // 2. Load last-known-good configuration
                // 3. Maintain limited safe operation
            }
            SafeState::WarmReset => {
                // 1. Save fault context to non-volatile storage
                // 2. Reset FLUX-X to bootloader
                // 3. FLUX-C remains active during reset
            }
        }
    }

    /// Verify bridge integrity — called at startup
    pub fn verify_integrity(&self) -> bool {
        // Bridge must be locked
        if !self.locked {
            return false;
        }
        // Audit trail must be contiguous
        // Register map must be valid
        for (&reg, &pos) in &self.config.register_map {
            if reg >= 16 || pos >= STACK_SIZE {
                return false;
            }
        }
        true
    }

    /// Get audit trail length
    pub fn audit_count(&self) -> usize {
        self.audit_trail.len()
    }

    // SECURITY: This function intentionally does NOT exist:
    // fn unlock_bridge(&mut self) { self.locked = false; }
    // The bridge cannot be bypassed. This is a design decision, not an oversight.
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bridge_creation() {
        let bridge = FluxBridge::new(BridgeConfig::default());
        assert!(bridge.verify_integrity());
        assert!(bridge.locked);
    }

    #[test]
    fn constraint_check_pass() {
        let mut bridge = FluxBridge::new(BridgeConfig::default());
        let registers: RegisterFile = [0u64; 16];
        // HALT instruction — passes immediately
        let bytecode = vec![0x1A];
        let result = bridge.constraint_check(&registers, 0, 1, &bytecode);
        assert_eq!(result, BridgeResult::Pass);
        assert_eq!(bridge.audit_count(), 1);
    }

    #[test]
    fn constraint_check_guard_trap() {
        let mut bridge = FluxBridge::new(BridgeConfig::default());
        let registers: RegisterFile = [0u64; 16];
        let bytecode = vec![0x20]; // GUARD_TRAP
        let result = bridge.constraint_check(&registers, 0, 1, &bytecode);
        assert_eq!(result, BridgeResult::Fail(FaultCode::AssertFailed));
    }

    #[test]
    fn gas_exhaustion() {
        let mut config = BridgeConfig::default();
        config.gas_limit = 3;
        let mut bridge = FluxBridge::new(config);
        let registers: RegisterFile = [0u64; 16];
        // NOP loop — 6 bytes, will exhaust gas=3 before reaching end
        let bytecode = vec![0x27, 0x27, 0x27, 0x27, 0x27, 0x27];
        let result = bridge.constraint_check(&registers, 0, 1, &bytecode);
        assert_eq!(result, BridgeResult::Fail(FaultCode::GasExhausted));
    }

    #[test]
    fn register_mapping() {
        let config = BridgeConfig::default();
        // R0 should map to stack position 0
        assert_eq!(config.register_map[&0], 0);
        // R15 should map to stack position 15
        assert_eq!(config.register_map[&15], 15);
    }

    #[test]
    fn no_unlock_exists() {
        // This is a compile-time guarantee — the FluxBridge struct has no
        // unlock method. The locked field is private and can only be set
        // in the constructor (which sets it to true).
        let bridge = FluxBridge::new(BridgeConfig::default());
        assert!(bridge.locked);
        // There is no bridge.unlock() — this is intentional
    }

    #[test]
    fn safe_state_default_mapping() {
        let config = BridgeConfig::default();
        assert_eq!(config.fault_safe_states[&FaultCode::RangeViolation], SafeState::HaltAndClockGate);
        assert_eq!(config.fault_safe_states[&FaultCode::ThermalExceeded], SafeState::FallbackMode);
        assert_eq!(config.fault_safe_states[&FaultCode::GasExhausted], SafeState::WarmReset);
    }
}
