//! # FLUX Bytecode Virtual Machine
//!
//! A stack-based interpreter that encodes constraint theory as executable
//! instructions.  Each opcode represents an operation on the constraint
//! manifold or the value stack.
//!
//! ## Constraint Theory Mapping
//!
//! * **PUSH** — Injects raw flux (a continuous, unconstrained scalar) into
//!   the computation.  It is the only opcode that does not yet satisfy a
//!   geometric law.
//!
//! * **SNAP** — Projects unconstrained flux onto the Pythagorean manifold,
//!   enforcing the hard constraint a² + b² = c².  The output is a *snapped
//!   triple*: a point on the discrete constraint surface.
//!
//! * **HOLON** — Measures the holonomy (geometric discrepancy) between the
//!   last two constraint projections.  Small holonomy means the manifold is
//!   locally flat; large holonomy signals curvature or a constraint
//!   violation.
//!
//! * **ADD / SUB / MUL / DIV** — Propagate constraints through arithmetic.
//!   These operate on scalar flux values, composing new unconstrained
//!   values that may later be snapped.
//!
//! * **CMP** — Compares two scalar constraints, producing an ordering signal
//!   (-1, 0, 1).  This lets the VM make control decisions based on the
//!   relative strength of flux values.
//!
//! * **PRINT** — Observes the top of the stack, collapsing the abstract
//!   value into observable output.  In constraint-theory terms this is a
//!   measurement of the final constrained state.
//!
//! * **HALT** — Terminates the flux computation, fixing the final
//!   constraint state and preventing further evolution.

pub mod manifold;

use manifold::snap;
use std::fmt;

/// A value on the FLUX operand stack.
#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    /// A scalar flux value (unconstrained or already measured).
    Number(f64),
    /// A point on the Pythagorean manifold (a, b, c) satisfying a²+b²=c².
    Triple(f64, f64, f64),
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Value::Number(n) => write!(f, "{}", n),
            Value::Triple(a, b, c) => write!(f, "({}, {}, {})", a, b, c),
        }
    }
}

/// FLUX instruction set.
///
/// Each variant corresponds to a single bytecode operation consumed by the VM.
#[derive(Clone, Debug, PartialEq)]
pub enum OpCode {
    /// PUSH(f64) — Push a raw scalar flux value onto the stack.
    Push(f64),
    /// SNAP — Pop scalar, project onto Pythagorean manifold, push triple.
    Snap,
    /// HOLON — Measure holonomy between last two snap results, push scalar.
    Holon,
    /// ADD — Pop two scalars, push sum.
    Add,
    /// SUB — Pop two scalars, push difference (next − top).
    Sub,
    /// MUL — Pop two scalars, push product.
    Mul,
    /// DIV — Pop two scalars, push quotient (next / top).
    Div,
    /// CMP — Pop two scalars, push −1.0 if next<top, 0.0 if equal, 1.0 if next>top.
    Cmp,
    /// PRINT — Pop top value and emit it to the output buffer.
    Print,
    /// HALT — Stop execution.
    Halt,
}

/// The FLUX virtual machine.
///
/// Maintains an operand stack, a program counter, a history of snapped
/// triples for holonomy calculations, and a captured output log.
pub struct VM {
    pub stack: Vec<Value>,
    /// Record of every triple produced by SNAP, used by HOLON.
    pub snap_history: Vec<(f64, f64, f64)>,
    pub pc: usize,
    pub halted: bool,
    pub program: Vec<OpCode>,
    /// Captured output from PRINT instructions (useful for testing).
    pub output: Vec<String>,
}

impl VM {
    /// Create a new VM with empty state.
    pub fn new() -> Self {
        VM {
            stack: Vec::new(),
            snap_history: Vec::new(),
            pc: 0,
            halted: false,
            program: Vec::new(),
            output: Vec::new(),
        }
    }

    /// Load a bytecode program into the VM, resetting execution state.
    pub fn load(&mut self, program: Vec<OpCode>) {
        self.program = program;
        self.pc = 0;
        self.halted = false;
        self.stack.clear();
        self.snap_history.clear();
        self.output.clear();
    }

    /// Execute the instruction at the current program counter.
    pub fn step(&mut self) {
        if self.halted || self.pc >= self.program.len() {
            self.halted = true;
            return;
        }

        // Clone the opcode so we don't hold a borrow into self.program.
        let op = self.program[self.pc].clone();
        self.pc += 1;

        match op {
            OpCode::Push(v) => {
                self.stack.push(Value::Number(v));
            }
            OpCode::Snap => {
                if let Some(Value::Number(x)) = self.stack.pop() {
                    let triple = snap(x);
                    self.snap_history.push(triple);
                    self.stack.push(Value::Triple(triple.0, triple.1, triple.2));
                }
            }
            OpCode::Holon => {
                let h = if self.snap_history.len() >= 2 {
                    let t1 = self.snap_history[self.snap_history.len() - 2];
                    let t2 = self.snap_history[self.snap_history.len() - 1];
                    holonomy(t1, t2)
                } else {
                    0.0
                };
                self.stack.push(Value::Number(h));
            }
            OpCode::Add => {
                if let (Some(Value::Number(b)), Some(Value::Number(a))) =
                    (self.stack.pop(), self.stack.pop())
                {
                    self.stack.push(Value::Number(a + b));
                }
            }
            OpCode::Sub => {
                if let (Some(Value::Number(b)), Some(Value::Number(a))) =
                    (self.stack.pop(), self.stack.pop())
                {
                    self.stack.push(Value::Number(a - b));
                }
            }
            OpCode::Mul => {
                if let (Some(Value::Number(b)), Some(Value::Number(a))) =
                    (self.stack.pop(), self.stack.pop())
                {
                    self.stack.push(Value::Number(a * b));
                }
            }
            OpCode::Div => {
                if let (Some(Value::Number(b)), Some(Value::Number(a))) =
                    (self.stack.pop(), self.stack.pop())
                {
                    self.stack.push(Value::Number(a / b));
                }
            }
            OpCode::Cmp => {
                if let (Some(Value::Number(b)), Some(Value::Number(a))) =
                    (self.stack.pop(), self.stack.pop())
                {
                    let res = if a < b {
                        -1.0
                    } else if a > b {
                        1.0
                    } else {
                        0.0
                    };
                    self.stack.push(Value::Number(res));
                }
            }
            OpCode::Print => {
                if let Some(v) = self.stack.pop() {
                    let s = v.to_string();
                    self.output.push(s.clone());
                    println!("{}", s);
                }
            }
            OpCode::Halt => {
                self.halted = true;
            }
        }
    }

    /// Run until HALT or until the program counter passes the end of the program.
    pub fn run(&mut self) {
        while !self.halted && self.pc < self.program.len() {
            self.step();
        }
    }
}

/// Compute holonomy between two snapped triples.
///
/// Holonomy is defined as the Euclidean distance between the two points
/// when normalized onto the unit circle (a/c, b/c).  This measures the
/// geometric discrepancy between two successive constraint projections.
///
/// The result is always bounded by 2.0 (the diameter of the unit circle).
fn holonomy(t1: (f64, f64, f64), t2: (f64, f64, f64)) -> f64 {
    let (a1, b1, c1) = t1;
    let (a2, b2, c2) = t2;
    let x1 = a1 / c1;
    let y1 = b1 / c1;
    let x2 = a2 / c2;
    let y2 = b2 / c2;
    let dx = x2 - x1;
    let dy = y2 - y1;
    (dx * dx + dy * dy).sqrt()
}
