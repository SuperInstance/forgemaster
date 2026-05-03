//===- RISCVXconstrRegisterInfo.td - RISC-V Xconstr Registers ---*- tablegen -*-===//
//
// RISC-V Xconstr ISA Extension — Constraint Register File
//
// Registers CR0-CR7 hold 64-bit domain bitmasks. Bit i = 1 means value i is a
// member of the constraint domain. This matches flux_checker_top.sv:
//   localparam int COMP_COUNT = 8;
//   localparam int DATA_WIDTH = 64;
//
// Location in LLVM tree:
//   llvm/lib/Target/RISCV/RISCVXconstrRegisterInfo.td
// Include from:
//   llvm/lib/Target/RISCV/RISCVRegisterInfo.td  (after GPR/FPR definitions)
//===----------------------------------------------------------------------===//

// DWARF register numbers 64-71 are in the "experimental" space; a real
// extension should coordinate with the RISC-V DWARF committee.
let Namespace = "RISCV" in {

  // -----------------------------------------------------------------------
  // Physical Constraint Registers
  // HWEncoding occupies bits [2:0] of the 5-bit rs/rd field.
  // Bits [4:3] are always 0 in the custom-2 encoding.
  // -----------------------------------------------------------------------
  def CR0 : Register<"cr0"> {
    let HWEncoding{4-0} = 0;
    let DwarfNumbers   = [64];
  }
  def CR1 : Register<"cr1"> {
    let HWEncoding{4-0} = 1;
    let DwarfNumbers   = [65];
  }
  def CR2 : Register<"cr2"> {
    let HWEncoding{4-0} = 2;
    let DwarfNumbers   = [66];
  }
  def CR3 : Register<"cr3"> {
    let HWEncoding{4-0} = 3;
    let DwarfNumbers   = [67];
  }
  def CR4 : Register<"cr4"> {
    let HWEncoding{4-0} = 4;
    let DwarfNumbers   = [68];
  }
  def CR5 : Register<"cr5"> {
    let HWEncoding{4-0} = 5;
    let DwarfNumbers   = [69];
  }
  def CR6 : Register<"cr6"> {
    let HWEncoding{4-0} = 6;
    let DwarfNumbers   = [70];
  }
  def CR7 : Register<"cr7"> {
    let HWEncoding{4-0} = 7;
    let DwarfNumbers   = [71];
  }

} // end Namespace = "RISCV"

// -----------------------------------------------------------------------
// CRRegs — Register Class
//
// All 8 constraint registers. Type i64 (domain bitmask, 64 valid-value bits).
// 64-bit alignment matches DATA_WIDTH in flux_pkg.
//
// Allocation order: CR0 first (prefer low-numbered CRs for readability).
// Mark isAllocatable = 1 so the register allocator can spill/restore CRs
// across calls (caller-saved by convention; callee may use any CR freely).
// -----------------------------------------------------------------------
def CRRegs : RegisterClass<"RISCV", [i64], 64,
  (add CR0, CR1, CR2, CR3, CR4, CR5, CR6, CR7)> {
  let isAllocatable = 1;
}
