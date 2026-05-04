**Theorem.**  
For any bytecode \(B\) of arbitrary length and any input \(I\), the CUDA constraint checker terminates after at most \(\mathit{max\_gas}\) steps and returns one of three results: 0 (pass), 1 (fault), or gas‑exhausted. No undefined behavior (crashes, memory corruption, invalid results) can occur.

*Proof.*  

We formalise the execution as a deterministic state machine.

**State definition.**  
A state is a tuple \((pc, sp, \mathit{gas}, \mathit{fault})\), where  

* \(pc \in \mathbb{N}\) is the program counter (byte index within \(B\)),  
* \(sp \in \mathbb{N}\) is the stack pointer (number of elements on the stack, \(0 \le sp \le 64\)),  
* \(\mathit{gas} \in \mathbb{N}\), initially \(\mathit{max\_gas}\),  
* \(\mathit{fault} \in \{0,1\}\), initially \(0\).  

The stack is an array \(S[0..63]\) of integers; only the first \(sp\) entries are defined.  
The input \(I\) is placed on the stack before execution (or treated as a pre‑state that respects \(sp \le 64\)). All subsequent transitions respect the invariants below.

**Transition rules.**  
Let \(L = |B|\). The machine executes one instruction per step, consuming at least one unit of gas. The following cases define the next state:

1. **Gas exhaustion:** If \(\mathit{gas} = 0\), the machine halts and outputs “gas‑exhausted”.  
2. **Fault already set:** If \(\mathit{fault} = 1\), the machine already halted; no further action.  
3. **Normal termination:** If \(pc \ge L\) (no more bytes), the machine halts and outputs “pass” (0).  
4. **Opcode fetch:** Otherwise, let \(op = B[pc]\). The machine decodes \(op\) and performs the corresponding operation.  

   All defined opcodes (e.g., PUSH, POP, ADD, JUMP, etc.) are implemented with explicit bounds checks:  
   * **PUSH:** If \(sp = 64\), set \(\mathit{fault} = 1\) and halt. Otherwise, increment \(sp\) and push the operand.  
   * **POP:** If \(sp = 0\), set \(\mathit{fault} = 1\) and halt. Otherwise, decrement \(sp\).  
   * **JUMP / conditional jump:** Compute target address \(t\). If \(t < 0\) or \(t \ge L\), set \(\mathit{fault} = 1\) and halt. Otherwise, set \(pc = t\).  
   * **Arithmetic:** For division or modulo, if divisor is zero, set \(\mathit{fault} = 1\) and halt.  
   * **Unknown opcodes:** Treated as NOP – no change to stack or \(pc\) except that \(pc\) is incremented by 1 (or left unchanged? The standard semantic for a NOP is to advance to the next instruction; we assume \(pc\) increments by 1).  

   After any operation that does not set \(\mathit{fault}\), we set \(pc \leftarrow pc + 1\) (for non‑jump instructions), decrement \(\mathit{gas}\) by at least 1, and proceed.

**Invariants.**  
We prove by induction on the number of steps that every reachable state satisfies:

* (I1) \(0 \le sp \le 64\),  
* (I2) \(0 \le pc \le L\) (with \(pc = L\) only in a terminal state),  
* (I3) \(\mathit{gas} \ge 0\),  
* (I4) \(\mathit{fault} \in \{0,1\}\).

**Base case (initial state).**  
\(pc = 0\) (so \(0 \le pc < L\) because \(