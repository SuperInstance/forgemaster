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
use std::time::{Duration, Instant};

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

/// A single constraint check descriptor for batch operations
pub struct ConstraintCheckRequest<'a> {
    /// Opaque ID for this constraint (caller-defined)
    pub constraint_id: u32,
    /// FLUX-C bytecode to execute
    pub bytecode: &'a [u8],
    /// Gas limit override; None → use BridgeConfig::gas_limit
    pub gas_limit_override: Option<u32>,
}

/// Outcome of a batch constraint run
#[derive(Debug, Clone)]
pub struct BatchResult {
    /// Per-constraint results, in submission order
    pub results: Vec<(u32, BridgeResult)>,
    /// First failing constraint ID, if any
    pub first_failure: Option<u32>,
    /// Total gas consumed across all constraints
    pub total_gas_used: u32,
}

impl BatchResult {
    /// True iff every constraint passed
    pub fn all_passed(&self) -> bool {
        self.first_failure.is_none()
    }
}

/// Cumulative statistics tracked across all bridge calls
#[derive(Debug, Clone, Default)]
pub struct BridgeStats {
    /// Total calls to constraint_check (single or via batch)
    pub total_calls: u64,
    /// How many resulted in BridgeResult::Pass
    pub pass_count: u64,
    /// How many resulted in BridgeResult::Fail
    pub fail_count: u64,
    /// Cumulative gas consumed (for average calculation)
    pub total_gas_used: u64,
    /// Minimum single-constraint execution time observed
    pub min_exec_time: Option<Duration>,
    /// Maximum single-constraint execution time observed
    pub max_exec_time: Option<Duration>,
    /// Cumulative execution time (for average calculation)
    pub total_exec_time: Duration,
}

impl BridgeStats {
    /// Pass rate in [0.0, 1.0]; returns 0.0 when no calls recorded
    pub fn pass_rate(&self) -> f64 {
        if self.total_calls == 0 {
            return 0.0;
        }
        self.pass_count as f64 / self.total_calls as f64
    }

    /// Fail rate in [0.0, 1.0]; returns 0.0 when no calls recorded
    pub fn fail_rate(&self) -> f64 {
        if self.total_calls == 0 {
            return 0.0;
        }
        self.fail_count as f64 / self.total_calls as f64
    }

    /// Average gas consumed per constraint check; returns 0 when no calls recorded
    pub fn avg_gas_used(&self) -> u64 {
        if self.total_calls == 0 {
            return 0;
        }
        self.total_gas_used / self.total_calls
    }

    /// Average execution time per constraint check; returns Duration::ZERO when no calls recorded
    pub fn avg_exec_time(&self) -> Duration {
        if self.total_calls == 0 {
            return Duration::ZERO;
        }
        self.total_exec_time / self.total_calls as u32
    }

    /// Record one completed constraint check into the statistics
    fn record(&mut self, passed: bool, gas_used: u32, elapsed: Duration) {
        self.total_calls += 1;
        self.total_gas_used += gas_used as u64;
        self.total_exec_time += elapsed;
        if passed {
            self.pass_count += 1;
        } else {
            self.fail_count += 1;
        }
        self.min_exec_time = Some(match self.min_exec_time {
            None => elapsed,
            Some(prev) => prev.min(elapsed),
        });
        self.max_exec_time = Some(match self.max_exec_time {
            None => elapsed,
            Some(prev) => prev.max(elapsed),
        });
    }
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
    /// Running statistics across all constraint checks
    pub stats: BridgeStats,
}

impl FluxBridge {
    pub fn new(config: BridgeConfig) -> Self {
        FluxBridge {
            config,
            audit_trail: Vec::new(),
            active: false,
            locked: true, // Bridge is locked by default
            stats: BridgeStats::default(),
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
        let t0 = Instant::now();
        let result = self.execute_flux_c(flux_c_bytecode, &mut stack);
        let elapsed = t0.elapsed();

        // Approximate gas used: gas_limit minus remaining (execute_flux_c doesn't return it
        // directly yet, so we track at the call-site level with full limit as upper bound).
        let gas_used = self.config.gas_limit;

        // Step 4: Handle result and record stats
        match result {
            BridgeResult::Pass => {
                self.stats.record(true, gas_used, elapsed);
                self.active = false;
                if self.config.audit_log {
                    self.audit_trail.push(context);
                }
                BridgeResult::Pass
            }
            BridgeResult::Fail(fault) => {
                self.stats.record(false, gas_used, elapsed);

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

    /// Execute multiple constraint checks in sequence.
    ///
    /// Stops at the first failure (fail-fast), matching the TrustZone model where a single
    /// fault puts FLUX-X into safe state — continuing further checks would be unsound.
    ///
    /// Returns a `BatchResult` with per-constraint outcomes and aggregate gas usage.
    pub fn batch_constraint_check(
        &mut self,
        registers: &RegisterFile,
        pc: u64,
        requests: &[ConstraintCheckRequest<'_>],
    ) -> BatchResult {
        let mut results = Vec::with_capacity(requests.len());
        let mut total_gas_used: u32 = 0;
        let mut first_failure: Option<u32> = None;

        for req in requests {
            // Temporarily override gas limit if the request specifies one
            let original_gas = self.config.gas_limit;
            if let Some(limit) = req.gas_limit_override {
                self.config.gas_limit = limit;
            }

            let outcome = self.constraint_check(registers, pc, req.constraint_id, req.bytecode);

            // Restore gas limit after each check
            self.config.gas_limit = original_gas;
            total_gas_used = total_gas_used.saturating_add(self.config.gas_limit);

            let passed = outcome == BridgeResult::Pass;
            results.push((req.constraint_id, outcome));

            if !passed {
                first_failure = Some(req.constraint_id);
                break; // Fail-fast: one fault → safe state already entered
            }
        }

        BatchResult { results, first_failure, total_gas_used }
    }

    /// Return SymbiYosys-compatible formal verification hints for this bridge.
    ///
    /// Each string is a valid SystemVerilog/SVA `assert` or `assume` statement that
    /// captures the key safety properties of the bridge protocol. Feed these into a
    /// `.sby` file under the `[script]` section alongside your RTL.
    ///
    /// Properties encoded:
    /// - `locked` is an invariant — the bridge can never be unlocked at runtime
    /// - Reentrancy is impossible — `active` is false whenever `constraint_check` is called
    /// - All register-to-stack mappings are in-range
    /// - Safe-state is always reached on fault (liveness)
    pub fn formal_verification_hints(&self) -> Vec<String> {
        let mut hints = Vec::new();

        // ── Invariants (assert: must hold in all reachable states) ──────────────

        hints.push(
            "// Bridge lock invariant: locked bit is set at reset and never cleared\n\
             assert property (@(posedge clk) bridge_locked === 1'b1);"
                .to_string(),
        );

        hints.push(
            "// No reentrancy: bridge cannot be entered while already active\n\
             assert property (@(posedge clk) bridge_active |-> !constraint_check_req);"
                .to_string(),
        );

        hints.push(
            "// Context atomicity: FLUX-X registers are frozen during FLUX-C execution\n\
             assert property (@(posedge clk) bridge_active |-> $stable(flux_x_registers));"
                .to_string(),
        );

        // ── Register map bounds (one assertion per mapped register) ─────────────

        for (&reg, &pos) in &self.config.register_map {
            hints.push(format!(
                "// Register R{reg} maps to stack[{pos}] — both must be in range\n\
                 assert property (@(posedge clk) reg_idx === {reg} |-> stack_pos === {pos} && stack_pos < {STACK_SIZE});"
            ));
        }

        // ── Liveness: fault must reach safe state within bounded cycles ──────────

        for (fault, state) in &self.config.fault_safe_states {
            let state_signal = match state {
                SafeState::HaltAndClockGate => "safe_halt_clkgate",
                SafeState::FallbackMode     => "safe_fallback_mode",
                SafeState::WarmReset        => "safe_warm_reset",
            };
            let fault_signal = match fault {
                FaultCode::RangeViolation      => "fault_range",
                FaultCode::WhitelistViolation  => "fault_whitelist",
                FaultCode::BitmaskViolation    => "fault_bitmask",
                FaultCode::ThermalExceeded     => "fault_thermal",
                FaultCode::SparsityInsufficient => "fault_sparsity",
                FaultCode::AssertFailed        => "fault_assert",
                FaultCode::GasExhausted        => "fault_gas",
                FaultCode::StackCorruption     => "fault_stack",
            };
            hints.push(format!(
                "// Liveness: {fault_signal} must trigger {state_signal} within 4 cycles\n\
                 assert property (@(posedge clk) {fault_signal} |-> ##[1:4] {state_signal});"
            ));
        }

        // ── Gas bound: FLUX-C execution terminates ───────────────────────────────

        hints.push(format!(
            "// Termination: gas counter reaches zero within gas_limit={} cycles\n\
             assert property (@(posedge clk) bridge_active |-> ##[0:{}] !bridge_active);",
            self.config.gas_limit, self.config.gas_limit
        ));

        // ── Assume: environment constraints for bounded model checking ───────────

        hints.push(
            "// Assume: FLUX-C bytecode length is bounded (prevents state explosion)\n\
             assume property (@(posedge clk) bytecode_len <= 256);"
                .to_string(),
        );

        hints.push(
            "// Assume: FLUX-X only drives constraint_check when not in safe state\n\
             assume property (@(posedge clk) safe_halt_clkgate |-> !constraint_check_req);"
                .to_string(),
        );

        hints
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

    // ── BridgeStats tests ────────────────────────────────────────────────────

    #[test]
    fn stats_initially_zero() {
        let bridge = FluxBridge::new(BridgeConfig::default());
        assert_eq!(bridge.stats.total_calls, 0);
        assert_eq!(bridge.stats.pass_rate(), 0.0);
        assert_eq!(bridge.stats.fail_rate(), 0.0);
        assert_eq!(bridge.stats.avg_gas_used(), 0);
        assert_eq!(bridge.stats.avg_exec_time(), Duration::ZERO);
        assert!(bridge.stats.min_exec_time.is_none());
        assert!(bridge.stats.max_exec_time.is_none());
    }

    #[test]
    fn stats_recorded_on_pass() {
        let mut bridge = FluxBridge::new(BridgeConfig::default());
        let regs: RegisterFile = [0u64; 16];
        bridge.constraint_check(&regs, 0, 1, &[0x1A]); // HALT → pass
        assert_eq!(bridge.stats.total_calls, 1);
        assert_eq!(bridge.stats.pass_count, 1);
        assert_eq!(bridge.stats.fail_count, 0);
        assert!((bridge.stats.pass_rate() - 1.0).abs() < f64::EPSILON);
        assert!(bridge.stats.min_exec_time.is_some());
    }

    #[test]
    fn stats_recorded_on_fail() {
        let mut bridge = FluxBridge::new(BridgeConfig::default());
        let regs: RegisterFile = [0u64; 16];
        bridge.constraint_check(&regs, 0, 1, &[0x20]); // GUARD_TRAP → fail
        assert_eq!(bridge.stats.total_calls, 1);
        assert_eq!(bridge.stats.pass_count, 0);
        assert_eq!(bridge.stats.fail_count, 1);
        assert!((bridge.stats.fail_rate() - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn stats_min_max_exec_time() {
        let mut bridge = FluxBridge::new(BridgeConfig::default());
        let regs: RegisterFile = [0u64; 16];
        bridge.constraint_check(&regs, 0, 1, &[0x1A]);
        bridge.constraint_check(&regs, 0, 2, &[0x1A]);
        let min = bridge.stats.min_exec_time.unwrap();
        let max = bridge.stats.max_exec_time.unwrap();
        assert!(min <= max);
    }

    // ── batch_constraint_check tests ─────────────────────────────────────────

    #[test]
    fn batch_all_pass() {
        let mut bridge = FluxBridge::new(BridgeConfig::default());
        let regs: RegisterFile = [0u64; 16];
        let requests = vec![
            ConstraintCheckRequest { constraint_id: 1, bytecode: &[0x1A], gas_limit_override: None },
            ConstraintCheckRequest { constraint_id: 2, bytecode: &[0x1A], gas_limit_override: None },
            ConstraintCheckRequest { constraint_id: 3, bytecode: &[0x1A], gas_limit_override: None },
        ];
        let batch = bridge.batch_constraint_check(&regs, 0, &requests);
        assert!(batch.all_passed());
        assert!(batch.first_failure.is_none());
        assert_eq!(batch.results.len(), 3);
    }

    #[test]
    fn batch_stops_at_first_failure() {
        let mut bridge = FluxBridge::new(BridgeConfig::default());
        let regs: RegisterFile = [0u64; 16];
        let requests = vec![
            ConstraintCheckRequest { constraint_id: 10, bytecode: &[0x1A], gas_limit_override: None },
            ConstraintCheckRequest { constraint_id: 20, bytecode: &[0x20], gas_limit_override: None }, // GUARD_TRAP
            ConstraintCheckRequest { constraint_id: 30, bytecode: &[0x1A], gas_limit_override: None }, // never reached
        ];
        let batch = bridge.batch_constraint_check(&regs, 0, &requests);
        assert!(!batch.all_passed());
        assert_eq!(batch.first_failure, Some(20));
        // Only two results: id=10 (pass) and id=20 (fail); id=30 never executed
        assert_eq!(batch.results.len(), 2);
        assert_eq!(batch.results[0], (10, BridgeResult::Pass));
        assert_eq!(batch.results[1], (20, BridgeResult::Fail(FaultCode::AssertFailed)));
    }

    #[test]
    fn batch_gas_override_respected() {
        let mut bridge = FluxBridge::new(BridgeConfig::default()); // default gas = 10000
        let regs: RegisterFile = [0u64; 16];
        // 4 unknown-opcode bytes; with gas=3 would exhaust, with default=10000 passes
        let bytecode: &[u8] = &[0x27, 0x27, 0x27, 0x1A]; // 3 NOPs then HALT
        let requests = vec![
            ConstraintCheckRequest { constraint_id: 99, bytecode, gas_limit_override: Some(2) },
        ];
        let batch = bridge.batch_constraint_check(&regs, 0, &requests);
        assert!(!batch.all_passed());
        assert_eq!(batch.first_failure, Some(99));
    }

    // ── formal_verification_hints tests ─────────────────────────────────────

    #[test]
    fn formal_hints_non_empty() {
        let bridge = FluxBridge::new(BridgeConfig::default());
        let hints = bridge.formal_verification_hints();
        assert!(!hints.is_empty());
    }

    #[test]
    fn formal_hints_contain_lock_invariant() {
        let bridge = FluxBridge::new(BridgeConfig::default());
        let hints = bridge.formal_verification_hints();
        let has_lock = hints.iter().any(|h| h.contains("bridge_locked"));
        assert!(has_lock, "expected a lock-invariant assertion in hints");
    }

    #[test]
    fn formal_hints_contain_liveness_for_all_faults() {
        let bridge = FluxBridge::new(BridgeConfig::default());
        let hints = bridge.formal_verification_hints();
        // Every fault code defined in the config must have a liveness property
        for fault_signal in &[
            "fault_range", "fault_whitelist", "fault_bitmask",
            "fault_thermal", "fault_sparsity", "fault_assert",
            "fault_gas", "fault_stack",
        ] {
            let found = hints.iter().any(|h| h.contains(fault_signal));
            assert!(found, "missing liveness hint for {fault_signal}");
        }
    }

    #[test]
    fn formal_hints_contain_termination_bound() {
        let bridge = FluxBridge::new(BridgeConfig::default());
        let hints = bridge.formal_verification_hints();
        let has_term = hints.iter().any(|h| h.contains("bridge_active") && h.contains("gas"));
        assert!(has_term, "expected a gas-bounded termination assertion");
    }
}
