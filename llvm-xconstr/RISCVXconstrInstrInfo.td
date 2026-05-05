//===- RISCVXconstrInstrInfo.td - Xconstr Instructions -----*- tablegen -*-===//
//
// RISC-V Xconstr ISA Extension — Instruction Definitions
//
// 9 instructions operating on 8 constraint registers (CR0-CR7):
//   CLD, CST, CAND, COR, CNOT, CPOP, CREVISE, CEMPTY, CFAULT
//
// All use custom-2 opcode (0x5B = 0b1011011). The funct7 field distinguishes
// instructions; funct3 is 0b000 throughout (reserved for future sub-variants).
//
// Encoding map (matches flux_checker_top.sv opcodes 6'd27-6'd34, 6'd25):
//   funct7 | Mnemonic | RTL opcode
//   -------+----------+-----------
//   0x00   | CLD      | DOMAIN_LOAD   (6'd33)
//   0x01   | CST      | DOMAIN_STORE  (6'd34)
//   0x02   | CAND     | INTERSECT     (6'd28)
//   0x03   | COR      | UNION         (6'd29)
//   0x04   | CNOT     | COMPLEMENT    (6'd30)
//   0x05   | CPOP     | CARDINALITY   (6'd32)
//   0x06   | CREVISE  | REVISE        (6'd27)
//   0x07   | CEMPTY   | EMPTY_CHECK   (6'd31)
//   0x08   | CFAULT   | ASSERT        (6'd25)
//
// Location in LLVM tree:
//   llvm/lib/Target/RISCV/RISCVXconstrInstrInfo.td
// Include from:
//   llvm/lib/Target/RISCV/RISCVInstrInfo.td  (at the bottom)
//===----------------------------------------------------------------------===//

// -----------------------------------------------------------------------
// Feature + Predicate
// (In a real tree these live in RISCVFeatures.td / RISCVInstrInfo.td)
// -----------------------------------------------------------------------
def FeatureStdExtXconstr
    : SubtargetFeature<"xconstr", "HasStdExtXconstr", "true",
                       "'Xconstr' (FLUX Constraint Engine Extension)">;

def HasStdExtXconstr
    : Predicate<"Subtarget->hasStdExtXconstr()">,
      AssemblerPredicate<(all_of FeatureStdExtXconstr),
                         "'Xconstr' (Constraint Registers)">;

// -----------------------------------------------------------------------
// Instruction Format
//
// All Xconstr instructions are 32-bit R-type with custom-2 opcode.
//
//  31     25 24  20 19  15 14 12 11   7 6      0
// ┌─────────┬──────┬──────┬─────┬──────┬────────┐
// │ funct7  │  rs2 │  rs1 │ fn3 │  rd  │ 1011011│
// └─────────┴──────┴──────┴─────┴──────┴────────┘
//
// For single-source ops: rs2 = 0b00000.
// For CFAULT (no dest):  rd  = 0b00000.
// -----------------------------------------------------------------------

// Declare custom-2 opcode value so the format class can reference it.
// In the real tree OPC_CUSTOM_2 is already defined in RISCVInstrFormats.td.
class RISCVOpcodeXC<bits<7> val> {
  bits<7> Value = val;
}
def OPC_XCONSTR : RISCVOpcodeXC<0b1011011>; // custom-2

// Base format class — inherits LLVM's RVInst infrastructure.
// The 'pattern' field is deliberately [] here; we provide explicit
// Pat<> defs below so instruction selection patterns are self-contained.
class RVInstXconstr<bits<7> funct7, dag outs, dag ins,
                    string opcodestr, string argstr>
    : RVInst<outs, ins, opcodestr, argstr, [], InstFormatR> {
  bits<5> rs2 = 0;
  bits<5> rs1 = 0;
  bits<5> rd  = 0;

  let Inst{31-25} = funct7;
  let Inst{24-20} = rs2;
  let Inst{19-15} = rs1;
  let Inst{14-12} = 0b000; // funct3 — reserved 0
  let Inst{11-7}  = rd;
  let Inst{6-0}   = OPC_XCONSTR.Value;

  let Predicates  = [HasStdExtXconstr];
  let hasSideEffects = 0;
  let mayLoad     = 0;
  let mayStore    = 0;
}

// Specialisation: CFAULT has side effects (it may trap).
class RVInstXconstrFault<bits<7> funct7, dag outs, dag ins,
                         string opcodestr, string argstr>
    : RVInstXconstr<funct7, outs, ins, opcodestr, argstr> {
  let hasSideEffects = 1;
}

// -----------------------------------------------------------------------
// Operand types
// -----------------------------------------------------------------------

// Constraint register operand — printed as "crN"
def CRReg : RegisterOperand<CRRegs, "printRegName">;

// -----------------------------------------------------------------------
// Instruction Definitions
// -----------------------------------------------------------------------

// --- CLD: Load Constraint Register from GPR ----------------------------
//   CLD crD, rs1
//   crD ← GPR[rs1]   (initialise domain bitmask from general-purpose register)
//   Encoding: funct7=0x00, rs2=0, rs1=GPR, rd=crD
def CLD : RVInstXconstr<0x00,
    (outs CRReg:$rd),
    (ins  GPR:$rs1),
    "cld", "$rd, $rs1"> {
  bits<5> rd;
  bits<5> rs1;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = 0;
}

// --- CST: Store Constraint Register to GPR -----------------------------
//   CST rd, crS
//   GPR[rd] ← crS   (read domain bitmask back into general-purpose register)
//   Encoding: funct7=0x01, rs2=0, rs1=crS, rd=GPR
def CST : RVInstXconstr<0x01,
    (outs GPR:$rd),
    (ins  CRReg:$rs1),
    "cst", "$rd, $rs1"> {
  bits<5> rd;
  bits<5> rs1;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = 0;
}

// --- CAND: Domain Intersection (AND) -----------------------------------
//   CAND crD, crS1, crS2
//   crD ← crS1 & crS2   (constraint intersection; maps to INTERSECT in RTL)
def CAND : RVInstXconstr<0x02,
    (outs CRReg:$rd),
    (ins  CRReg:$rs1, CRReg:$rs2),
    "cand", "$rd, $rs1, $rs2"> {
  bits<5> rd;
  bits<5> rs1;
  bits<5> rs2;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = rs2;
}

// --- COR: Domain Union (OR) --------------------------------------------
//   COR crD, crS1, crS2
//   crD ← crS1 | crS2   (constraint union; maps to UNION in RTL)
def COR : RVInstXconstr<0x03,
    (outs CRReg:$rd),
    (ins  CRReg:$rs1, CRReg:$rs2),
    "cor", "$rd, $rs1, $rs2"> {
  bits<5> rd;
  bits<5> rs1;
  bits<5> rs2;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = rs2;
}

// --- CNOT: Domain Complement (NOT) -------------------------------------
//   CNOT crD, crS
//   crD ← ~crS   (complement; maps to COMPLEMENT in RTL)
//   Note: crD and crS may alias (in-place complement).
def CNOT : RVInstXconstr<0x04,
    (outs CRReg:$rd),
    (ins  CRReg:$rs1),
    "cnot", "$rd, $rs1"> {
  bits<5> rd;
  bits<5> rs1;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = 0;
  let Constraints = "$rd = $rs1"; // allow in-place; tied operand hint
}

// --- CPOP: Domain Cardinality (Population Count) -----------------------
//   CPOP rd, crS
//   GPR[rd] ← popcount(crS)  (number of valid values; maps to CARDINALITY)
//   Result is a plain integer returned in a GPR.
def CPOP : RVInstXconstr<0x05,
    (outs GPR:$rd),
    (ins  CRReg:$rs1),
    "cpop", "$rd, $rs1"> {
  bits<5> rd;
  bits<5> rs1;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = 0;
}

// --- CREVISE: Arc-Consistency Revision ---------------------------------
//   CREVISE crD, crS1, crS2
//   crD ← revise(crS1, crS2)
//
//   For an inequality constraint (x ≠ y): crD = crS1 & ~crS2
//   The hardware implements the revision policy; the compiler emits CREVISE
//   and the constraint checker unit in the datapath applies the correct rule.
//   Maps to REVISE (6'd27) in flux_checker_top opcode decoder.
def CREVISE : RVInstXconstr<0x06,
    (outs CRReg:$rd),
    (ins  CRReg:$rs1, CRReg:$rs2),
    "crevise", "$rd, $rs1, $rs2"> {
  bits<5> rd;
  bits<5> rs1;
  bits<5> rs2;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = rs2;
  // Revision may change domain — flag as having side effects so it is
  // never reordered past a CEMPTY/CFAULT on the same register.
  let hasSideEffects = 1;
}

// --- CEMPTY: Domain Empty Check ----------------------------------------
//   CEMPTY rd, crS
//   GPR[rd] ← (crS == 0) ? 1 : 0
//   Returns 1 if no valid values remain (constraint failure imminent).
//   Maps to EMPTY_CHECK (6'd31) in RTL.
def CEMPTY : RVInstXconstr<0x07,
    (outs GPR:$rd),
    (ins  CRReg:$rs1),
    "cempty", "$rd, $rs1"> {
  bits<5> rd;
  bits<5> rs1;
  let Inst{11-7}  = rd;
  let Inst{19-15} = rs1;
  let Inst{24-20} = 0;
}

// --- CFAULT: Constraint Assert (Fault if Empty) ------------------------
//   CFAULT crS
//   if (crS == 0) → FAULT_ILLEGAL_OP / trap
//   Maps to ASSERT (6'd25) in RTL which triggers the fault_latch.
//   This is a first-class fault: the hardware latches the fault code and
//   transitions the safe-state FSM to ST_SAFE (irreversible until power-on).
//
//   From flux_checker_top: fault_bus[1] → fault_latch → interlock_out.
//   The LLVM backend must NOT reorder CFAULT past any domain-modifying
//   instruction on the same CR; hasSideEffects = 1 prevents this.
def CFAULT : RVInstXconstrFault<0x08,
    (outs),
    (ins  CRReg:$rs1),
    "cfault", "$rs1"> {
  bits<5> rs1;
  let Inst{11-7}  = 0; // rd = x0 (no destination)
  let Inst{19-15} = rs1;
  let Inst{24-20} = 0;
}

// -----------------------------------------------------------------------
// Instruction Selection Patterns
//
// Map LLVM intrinsics → Xconstr instructions.
// Intrinsics are declared in IntrinsicsRISCVXconstr.td.
// -----------------------------------------------------------------------

let Predicates = [HasStdExtXconstr] in {

  // CLD: GPR → CR
  def : Pat<(int_riscv_xconstr_cld GPR:$rs1),
            (CLD GPR:$rs1)>;

  // CST: CR → GPR
  def : Pat<(int_riscv_xconstr_cst CRRegs:$rs1),
            (CST CRRegs:$rs1)>;

  // CAND: domain intersection
  def : Pat<(int_riscv_xconstr_cand CRRegs:$rs1, CRRegs:$rs2),
            (CAND CRRegs:$rs1, CRRegs:$rs2)>;

  // COR: domain union
  def : Pat<(int_riscv_xconstr_cor CRRegs:$rs1, CRRegs:$rs2),
            (COR CRRegs:$rs1, CRRegs:$rs2)>;

  // CNOT: domain complement
  def : Pat<(int_riscv_xconstr_cnot CRRegs:$rs1),
            (CNOT CRRegs:$rs1)>;

  // CPOP: cardinality — result is an i64 in a GPR
  def : Pat<(int_riscv_xconstr_cpop CRRegs:$rs1),
            (CPOP CRRegs:$rs1)>;

  // CREVISE: arc-consistency revision
  def : Pat<(int_riscv_xconstr_crevise CRRegs:$rs1, CRRegs:$rs2),
            (CREVISE CRRegs:$rs1, CRRegs:$rs2)>;

  // CEMPTY: empty-domain check; result is 0 or 1 in GPR
  def : Pat<(int_riscv_xconstr_cempty CRRegs:$rs1),
            (CEMPTY CRRegs:$rs1)>;

  // CFAULT: no output; matched as a void intrinsic call
  def : Pat<(int_riscv_xconstr_cfault CRRegs:$rs1),
            (CFAULT CRRegs:$rs1)>;

} // end Predicates = [HasStdExtXconstr]
