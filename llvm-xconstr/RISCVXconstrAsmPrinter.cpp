//===- RISCVXconstrAsmPrinter.cpp - Xconstr Assembly Printer --------------===//
//
// RISC-V Xconstr Extension — Assembly Printer Support
//
// LLVM 18 auto-generates most of the assembly printer from the AsmString
// fields in RISCVXconstrInstrInfo.td.  This file provides the two pieces
// that TableGen cannot generate automatically:
//
//   1. printXconstrRegName() — prints CRN register names in operand context
//   2. Subtarget feature accessor — the C++ method HasStdExtXconstr
//
// Location in LLVM tree:
//   llvm/lib/Target/RISCV/RISCVInstPrinter.cpp  (extend existing file)
//   llvm/lib/Target/RISCV/RISCVSubtarget.h       (add accessor)
//
//===----------------------------------------------------------------------===//

// ─── Patch for RISCVInstPrinter.cpp ──────────────────────────────────────────
//
// Add the following method to class RISCVInstPrinter.  The auto-generated
// RISCVGenAsmWriter.inc calls printRegName() for every register operand;
// this method dispatches on the register class.
//
// #include "MCTargetDesc/RISCVMCTargetDesc.h"
// #include "RISCVXconstrRegisterInfo.td"  // for RISCV::CR0 .. CR7

#include "RISCVInstPrinter.h"
#include "llvm/MC/MCExpr.h"
#include "llvm/MC/MCInst.h"
#include "llvm/MC/MCRegisterInfo.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

// ---------------------------------------------------------------------------
// printXconstrRegName — emit "crN" for constraint register operands.
//
// Called by the auto-generated printInstruction() when the operand's
// register class is CRRegs.  The encoding is simply the low 3 bits of
// the physical register number (CR0 = 0 .. CR7 = 7).
// ---------------------------------------------------------------------------
void RISCVInstPrinter::printXconstrRegName(const MCInst *MI, unsigned OpNo,
                                            raw_ostream &O) {
  unsigned Reg = MI->getOperand(OpNo).getReg();
  // RISCV::CR0 through RISCV::CR7 are defined in the generated
  // RISCVGenRegisterInfo.inc.  We identify them by range.
  if (Reg >= RISCV::CR0 && Reg <= RISCV::CR7) {
    O << "cr" << (Reg - RISCV::CR0);
    return;
  }
  // Fallback: standard register name (should never reach here for CRRegs).
  O << getRegisterName(Reg);
}

// ---------------------------------------------------------------------------
// Subtarget accessor patch — add to RISCVSubtarget.h
//
// Inside class RISCVSubtarget : public RISCVGenSubtargetInfo {
//   ...
//   // Xconstr extension
//   bool HasStdExtXconstr = false;
//   bool hasStdExtXconstr() const { return HasStdExtXconstr; }
//   ...
// }
//
// The LLVM TableGen SubtargetEmitter auto-generates the initialisation of
// HasStdExtXconstr from FeatureStdExtXconstr in RISCVSubtarget.cpp when
// the SubtargetFeature is listed in the feature table.
// ---------------------------------------------------------------------------

// ─── Integration checklist ───────────────────────────────────────────────────
//
// To wire Xconstr into the LLVM 18 RISC-V backend, make the following edits:
//
// 1. llvm/lib/Target/RISCV/RISCVRegisterInfo.td
//      Add at the bottom:
//        include "RISCVXconstrRegisterInfo.td"
//
// 2. llvm/lib/Target/RISCV/RISCVInstrInfo.td
//      Add at the bottom:
//        include "RISCVXconstrInstrInfo.td"
//
// 3. llvm/include/llvm/IR/IntrinsicsRISCV.td
//      Inside `let TargetPrefix = "riscv" in { ... }`, add:
//        include "IntrinsicsRISCVXconstr.td"
//      (or paste the intrinsic defs directly)
//
// 4. llvm/lib/Target/RISCV/RISCVSubtarget.h
//      Add the HasStdExtXconstr field + accessor (see above).
//
// 5. llvm/lib/Target/RISCV/RISCVInstPrinter.h
//      Declare: void printXconstrRegName(const MCInst *, unsigned, raw_ostream &);
//
// 6. llvm/lib/Target/RISCV/RISCVInstPrinter.cpp
//      Add the printXconstrRegName definition (above).
//
// 7. llvm/lib/Target/RISCV/CMakeLists.txt
//      No change needed — RISCVXconstrAsmPrinter.cpp hooks into existing files.
//
// 8. Build and test:
//      cmake --build . --target llc
//      llc -march=riscv64 -mattr=+xconstr \
//          test/xconstr-guard.ll -o test/xconstr-guard.s
//      # Verify output matches expected assembly in xconstr-guard.ll
// ─────────────────────────────────────────────────────────────────────────────
