/**
 * FLUX ISA — Opcodes and instruction types for Constraint Theory bytecode.
 *
 * FLUX is the intermediate representation used by the constraint-theory solver.
 * Each instruction is a tagged tuple: [opcode, ...operands].
 */
export enum FluxOpcode {
  // ── Control flow ──────────────────────────────────────────
  NOP = 0x00,
  HALT = 0x01,
  JMP = 0x02,
  JZ = 0x03,       // jump if accumulator zero
  JNZ = 0x04,      // jump if accumulator non-zero
  CALL = 0x05,
  RET = 0x06,

  // ── Stack / data ──────────────────────────────────────────
  PUSH = 0x10,
  POP = 0x11,
  DUP = 0x12,
  SWAP = 0x13,
  LOAD = 0x14,     // load variable value
  STORE = 0x15,    // store variable assignment

  // ── Domain ops ────────────────────────────────────────────
  DOMAIN_INIT = 0x20,
  DOMAIN_RESTRICT = 0x21,
  DOMAIN_UNION = 0x22,
  DOMAIN_INTERSECT = 0x23,
  DOMAIN_DIFF = 0x24,
  DOMAIN_CARDINALITY = 0x25,
  DOMAIN_IS_EMPTY = 0x26,

  // ── Constraint evaluation ─────────────────────────────────
  CONSTRAINT_LOAD = 0x30,
  CONSTRAINT_EVAL = 0x31,
  CONSTRAINT_PROPAGATE = 0x32,
  CONSTRAINT_ARC_CONSIST = 0x33,

  // ── Arithmetic / logic ────────────────────────────────────
  ADD = 0x40,
  SUB = 0x41,
  MUL = 0x42,
  DIV = 0x43,
  MOD = 0x44,
  EQ = 0x50,
  NEQ = 0x51,
  LT = 0x52,
  LTE = 0x53,
  GT = 0x54,
  GTE = 0x55,
  AND = 0x56,
  OR = 0x57,
  NOT = 0x58,

  // ── Solver strategy ───────────────────────────────────────
  BACKTRACK = 0x60,
  FORWARD_CHECK = 0x61,
  LOOKAHEAD = 0x62,
  SELECT_VARIABLE = 0x63,
  SELECT_VALUE = 0x64,

  // ── Solution ──────────────────────────────────────────────
  SOLUTION_EMIT = 0x70,
  SOLUTION_COUNT = 0x71,
  VERIFY = 0x72,
}

/** A single FLUX instruction: opcode + variable-length operands. */
export interface FluxInstruction {
  opcode: FluxOpcode;
  operands: number[];
  /** Optional source annotation for debugging. */
  label?: string;
}

/** Full FLUX bytecode: ordered instruction list with metadata. */
export interface FLUXBytecode {
  instructions: FluxInstruction[];
  /** Map of variable name → register/slot index. */
  variableMap: Record<string, number>;
  /** Map of constraint id → instruction offset. */
  constraintOffsets: Record<string, number>;
  /** Total number of instructions. */
  count: number;
  /** Source hash for cache invalidation. */
  sourceHash: string;
}
