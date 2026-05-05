//===- IntrinsicsRISCVXconstr.td - Xconstr Intrinsics ------*- tablegen -*-===//
//
// RISC-V Xconstr Extension — LLVM IR Intrinsic Declarations
//
// These intrinsics bridge LLVM IR and the Xconstr instruction set.
// Each intrinsic operates on i64 domain bitmasks — the same representation
// used by flux_checker_top.sv (DATA_WIDTH=64).
//
// Naming convention: int_riscv_xconstr_<mnemonic_lowercase>
//
// Location in LLVM tree:
//   llvm/include/llvm/IR/IntrinsicsRISCV.td
//   (add inside the existing `let TargetPrefix = "riscv" in { ... }` block)
//
// LLVM 18+ compatibility notes:
//   - DefaultAttrsIntrinsic replaces the older GCCBuiltin macro pattern.
//   - IntrNoMem means no observable memory effects (safe to CSE/hoist).
//   - IntrHasSideEffects prevents reordering across control flow.
//   - llvm_i64_ty covers both RV32 (i32 pairs via softening) and RV64.
//===----------------------------------------------------------------------===//

let TargetPrefix = "riscv" in {

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cld — Load Constraint Register from GPR
//
//   %cr = call i64 @llvm.riscv.xconstr.cld(i64 %domain_init)
//
// Initialises a constraint domain register with a bitmask from a GPR.
// Returns the domain value as an i64 token used by subsequent CR intrinsics.
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cld : DefaultAttrsIntrinsic<
    [llvm_i64_ty],    // out: domain bitmask (lives in a CR register)
    [llvm_i64_ty],    // in:  initial domain value from GPR
    [IntrNoMem]
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cst — Store Constraint Register to GPR
//
//   %val = call i64 @llvm.riscv.xconstr.cst(i64 %cr_domain)
//
// Reads a constraint register back into a general-purpose register.
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cst : DefaultAttrsIntrinsic<
    [llvm_i64_ty],    // out: domain bitmask materialised into GPR
    [llvm_i64_ty],    // in:  CR domain bitmask
    [IntrNoMem]
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cand — Domain Intersection (AND)
//
//   %inter = call i64 @llvm.riscv.xconstr.cand(i64 %cr0, i64 %cr1)
//
// Returns the intersection (bitwise AND) of two constraint domains.
// A bit is set in %inter iff the value is valid in both %cr0 and %cr1.
// Maps to RTL INTERSECT opcode (6'd28).
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cand : DefaultAttrsIntrinsic<
    [llvm_i64_ty],
    [llvm_i64_ty, llvm_i64_ty],
    [IntrNoMem, Commutative]
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cor — Domain Union (OR)
//
//   %union = call i64 @llvm.riscv.xconstr.cor(i64 %cr0, i64 %cr1)
//
// Returns the union (bitwise OR) of two constraint domains.
// Maps to RTL UNION opcode (6'd29).
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cor : DefaultAttrsIntrinsic<
    [llvm_i64_ty],
    [llvm_i64_ty, llvm_i64_ty],
    [IntrNoMem, Commutative]
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cnot — Domain Complement (NOT)
//
//   %comp = call i64 @llvm.riscv.xconstr.cnot(i64 %cr0)
//
// Returns the bitwise complement of a constraint domain.
// Used to encode exclusion constraints: "x must NOT be in domain D"
// compiles to CNOT followed by CAND.
// Maps to RTL COMPLEMENT opcode (6'd30).
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cnot : DefaultAttrsIntrinsic<
    [llvm_i64_ty],
    [llvm_i64_ty],
    [IntrNoMem]
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cpop — Domain Cardinality (Population Count)
//
//   %card = call i64 @llvm.riscv.xconstr.cpop(i64 %cr0)
//
// Returns the number of valid values remaining in the domain.
// A result of 0 indicates a failed constraint (domain wipeout).
// Maps to RTL CARDINALITY opcode (6'd32).
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cpop : DefaultAttrsIntrinsic<
    [llvm_i64_ty],    // out: number of set bits (0..64)
    [llvm_i64_ty],    // in:  CR domain bitmask
    [IntrNoMem]
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_crevise — Arc-Consistency Revision
//
//   %revised = call i64 @llvm.riscv.xconstr.crevise(i64 %cr_target,
//                                                    i64 %cr_constraint)
//
// Performs one step of arc-consistency revision: removes values from
// %cr_target that have no support in %cr_constraint given the active
// constraint relation.  For the canonical inequality constraint (x ≠ y):
//
//     revised(target, constraint) = target & ~constraint
//
// This corresponds to FLUX ISA's CSP `Propagate` opcode (0x52) applied to
// a single arc.  Multiple CREVISE instructions chain for AC-3 propagation.
// Maps to RTL REVISE opcode (6'd27).
// ---------------------------------------------------------------------------
def int_riscv_xconstr_crevise : DefaultAttrsIntrinsic<
    [llvm_i64_ty],    // out: revised domain
    [llvm_i64_ty,     // in:  domain to revise (the "arc head")
     llvm_i64_ty],    // in:  constraining domain (the "arc tail")
    [IntrNoMem, IntrHasSideEffects]
    // IntrHasSideEffects: prevents CSE across CFAULT checks on same CR
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cempty — Domain Empty Test
//
//   %is_empty = call i64 @llvm.riscv.xconstr.cempty(i64 %cr0)
//
// Returns 1 if the domain is empty (all bits zero), 0 otherwise.
// A non-zero return means constraint propagation has eliminated all valid
// assignments — CFAULT should follow immediately.
// Maps to RTL EMPTY_CHECK opcode (6'd31).
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cempty : DefaultAttrsIntrinsic<
    [llvm_i64_ty],    // out: 1 = empty (violated), 0 = non-empty (OK)
    [llvm_i64_ty],    // in:  CR domain bitmask
    [IntrNoMem]
>;

// ---------------------------------------------------------------------------
// int_riscv_xconstr_cfault — Constraint Assert (Architectural Fault)
//
//   call void @llvm.riscv.xconstr.cfault(i64 %cr0)
//
// If %cr0 == 0 (domain empty), triggers an architectural fault:
//   • Sets fault_bus[1] (FAULT_ILLEGAL_OP) in flux_checker_top.sv
//   • Latches fault_code via fault_latch (irreversible until power-cycle)
//   • Transitions FSM to ST_SAFE via safe_state_controller
//   • Asserts interlock_out and drives safe_status_pin
//
// This is semantically equivalent to FLUX ISA's `Assert` opcode (0x50):
// "halt if false / domain empty."  The violation is architecturally
// unignorable — the processor cannot continue past CFAULT on a fault.
//
// Maps to RTL ASSERT opcode (6'd25).
// ---------------------------------------------------------------------------
def int_riscv_xconstr_cfault : DefaultAttrsIntrinsic<
    [],               // no return value
    [llvm_i64_ty],    // in:  CR domain bitmask to assert non-empty
    [IntrNoMem, IntrHasSideEffects]
    // IntrHasSideEffects: MUST NOT be eliminated, moved, or CSE'd
>;

} // end let TargetPrefix = "riscv"
