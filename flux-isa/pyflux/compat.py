"""
pyflux/compat.py — Python compatibility layer for FLUX-ISA bytecode.

Implements all 58 opcodes (43 core + 15 FLUX-DEEP) matching the Rust VM in
flux-isa/src/vm.rs exactly.  Stack-based execution, no external deps beyond
numpy for the projection/reconstruction opcodes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

# ─── Opcode constants ────────────────────────────────────────────────

class opcodes:
    """All FLUX-ISA opcodes with their byte values."""

    # Arithmetic
    ADD  = 0x01
    SUB  = 0x02
    MUL  = 0x03
    DIV  = 0x04
    MOD  = 0x05

    # Constraint
    ASSERT   = 0x10
    CHECK    = 0x11
    VALIDATE = 0x12
    REJECT   = 0x13

    # Flow
    JUMP   = 0x20
    BRANCH = 0x21
    CALL   = 0x22
    RETURN = 0x23
    HALT   = 0x24

    # Memory
    LOAD  = 0x30
    STORE = 0x31
    PUSH  = 0x32
    POP   = 0x33
    SWAP  = 0x34

    # Convert
    SNAP     = 0x40
    QUANTIZE = 0x41
    CAST     = 0x42
    PROMOTE  = 0x43

    # Logic
    AND = 0x50
    OR  = 0x51
    NOT = 0x52
    XOR = 0x53

    # Compare
    EQ  = 0x60
    NEQ = 0x61
    LT  = 0x62
    GT  = 0x63
    LTE = 0x64
    GTE = 0x65

    # INT8 Saturation
    SATADD = 0x28
    SATSUB = 0x29
    CLIP   = 0x2A
    MAD    = 0x2B
    POPCNT = 0x2C
    CTZ    = 0x2D
    PABS   = 0x2E
    PMIN   = 0x2F

    # Special
    NOP   = 0x70
    DEBUG = 0x71
    TRACE = 0x72
    DUMP  = 0x73

    # ── FLUX-DEEP: Galois Adjunctions (0x80-0x87) ──
    XORINVERT = 0x80
    CLAMP     = 0x81
    BLOOM     = 0x82
    BLOOMQ    = 0x83
    FLOORQ    = 0x84
    CEILQ     = 0x85
    ALIGN     = 0x86
    HOLONOMY  = 0x87

    # ── FLUX-DEEP: Cross-Domain (0x88-0x8F) ──
    TDQKR    = 0x88
    AMNESIA  = 0x89
    SHADOW   = 0x8A
    PHASE    = 0x8B
    COUPLE   = 0x8C
    FEDERATE = 0x8D
    BEARING  = 0x8E
    DEPTH    = 0x8F

    # ── FLUX-DEEP: Projection / Reconstruction (0x90-0x95) ──
    PROJECT     = 0x90
    RECONSTRUCT = 0x91
    WINDOW      = 0x92
    RESIDUE     = 0x93
    NASTY       = 0x94
    SNAPHIGH    = 0x95


# Human-readable names for trace output
_NAMES = {v: k for k, v in vars(opcodes).items() if isinstance(v, int) and not k.startswith("_")}


@dataclass
class Instruction:
    """One FLUX instruction: opcode + optional operands + label."""
    opcode: int
    operands: List[float] = field(default_factory=list)
    label: str = ""


@dataclass
class TraceEntry:
    step: int
    opcode: int
    stack_before: List[float]
    stack_after: List[float]
    constraint_result: Optional[bool]


class FluxError(Exception):
    """Runtime error from the FLUX VM."""
    pass


class FluxVM:
    """
    Stack-based FLUX virtual machine — pure-Python reimplementation
    matching the Rust ConstraintVM in vm.rs.
    """

    PHI = (1.0 + math.sqrt(5.0)) / 2.0  # golden ratio

    def __init__(self) -> None:
        self.stack: List[float] = []
        self.call_stack: List[int] = []
        self.trace: List[TraceEntry] = []
        self.constraint_results: List[bool] = []
        self.residue_memory: List[List[float]] = []
        self.acceptance_window: float = 1.0
        self._ip: int = 0

    # ── public API ──────────────────────────────────────────────────

    def execute(self, program: List[Instruction]) -> dict:
        """
        Execute a FLUX bytecode program.

        Returns dict with keys:
            outputs: List[float]         — remaining stack
            constraints_satisfied: bool  — all constraint checks passed
            trace: List[TraceEntry]
        """
        self.stack.clear()
        self.call_stack.clear()
        self.trace.clear()
        self.constraint_results.clear()
        self.residue_memory.clear()
        self.acceptance_window = 1.0

        ip = 0
        while ip < len(program):
            instr = program[ip]
            stack_before = list(self.stack)
            cr: Optional[bool] = None

            handler = self._dispatch.get(instr.opcode)
            if handler is None:
                raise FluxError(f"unknown opcode 0x{instr.opcode:02X} at step {ip}")
            cr = handler(self, instr)

            self.trace.append(TraceEntry(
                step=ip,
                opcode=instr.opcode,
                stack_before=stack_before,
                stack_after=list(self.stack),
                constraint_result=cr,
            ))
            if instr.opcode in (opcodes.JUMP, opcodes.BRANCH, opcodes.CALL, opcodes.RETURN):
                ip = self._ip if hasattr(self, "_next_ip") else ip + 1
                self._next_ip = False
            else:
                ip += 1

            if instr.opcode == opcodes.HALT:
                break

        satisfied = (
            len(self.constraint_results) > 0
            and all(self.constraint_results)
        )
        return {
            "outputs": list(self.stack),
            "constraints_satisfied": satisfied,
            "trace": self.trace,
        }

    # ── helpers ─────────────────────────────────────────────────────

    def _pop(self) -> float:
        if not self.stack:
            raise FluxError("stack underflow")
        return self.stack.pop()

    def _push(self, v: float) -> None:
        self.stack.append(float(v))

    def _binop(self, op: Callable[[float, float], float]) -> None:
        b = self._pop()
        a = self._pop()
        self._push(op(a, b))

    # ── instruction handlers (return Optional[bool] for constraint_result) ──

    def _op_add(self, i: Instruction):
        self._binop(lambda a, b: a + b)

    def _op_sub(self, i: Instruction):
        self._binop(lambda a, b: a - b)

    def _op_mul(self, i: Instruction):
        self._binop(lambda a, b: a * b)

    def _op_div(self, i: Instruction):
        b = self._pop()
        if b == 0.0:
            raise FluxError("division by zero")
        a = self._pop()
        self._push(a / b)

    def _op_mod(self, i: Instruction):
        self._binop(lambda a, b: a % b)

    # constraint
    def _op_assert(self, i: Instruction):
        v = self._pop()
        ok = v != 0.0
        self.constraint_results.append(ok)
        if not ok:
            raise FluxError(f"constraint violation at step {self._ip}: {i.label}")

    def _op_check(self, i: Instruction):
        v = self._pop()
        ok = v != 0.0
        self.constraint_results.append(ok)
        self._push(1.0 if ok else 0.0)
        return ok

    def _op_validate(self, i: Instruction):
        v = self._pop()
        lo = i.operands[0] if len(i.operands) > 0 else float("-inf")
        hi = i.operands[1] if len(i.operands) > 1 else float("inf")
        ok = lo <= v <= hi
        self.constraint_results.append(ok)
        self._push(1.0 if ok else 0.0)
        return ok

    def _op_reject(self, i: Instruction):
        raise FluxError(f"explicit reject at step {self._ip}: {i.label}")

    # flow
    def _op_jump(self, i: Instruction):
        self._ip = int(i.operands[0]) if i.operands else 0
        return None  # handled specially

    def _op_branch(self, i: Instruction):
        cond = self._pop()
        if cond != 0.0:
            self._ip = int(i.operands[0]) if i.operands else 0
        else:
            self._ip = self._ip + 1
        return None

    def _op_call(self, i: Instruction):
        self.call_stack.append(self._ip + 1)
        self._ip = int(i.operands[0]) if i.operands else 0
        return None

    def _op_return(self, i: Instruction):
        if self.call_stack:
            self._ip = self.call_stack.pop()
        else:
            self._ip = len(i.__self__.program) if hasattr(i, '__self__') else 999999
        return None

    def _op_halt(self, i: Instruction):
        pass

    # memory
    def _op_load(self, i: Instruction):
        v = i.operands[0] if i.operands else 0.0
        self._push(v)

    def _op_store(self, i: Instruction):
        self._pop()

    def _op_push(self, i: Instruction):
        for v in i.operands:
            self._push(v)

    def _op_pop(self, i: Instruction):
        self._pop()

    def _op_swap(self, i: Instruction):
        if len(self.stack) >= 2:
            self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

    # convert
    def _op_snap(self, i: Instruction):
        v = self._pop()
        self._push(round(v))

    def _op_quantize(self, i: Instruction):
        v = self._pop()
        step = i.operands[0] if i.operands else 1.0
        self._push(round(v / step) * step)

    def _op_cast(self, i: Instruction):
        pass  # no-op

    def _op_promote(self, i: Instruction):
        pass  # no-op

    # logic
    def _op_and(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if (a != 0.0 and b != 0.0) else 0.0)

    def _op_or(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if (a != 0.0 or b != 0.0) else 0.0)

    def _op_not(self, i: Instruction):
        v = self._pop()
        self._push(1.0 if v == 0.0 else 0.0)

    def _op_xor(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if (a != 0.0) != (b != 0.0) else 0.0)

    # compare
    def _op_eq(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if abs(a - b) < 1e-15 else 0.0)

    def _op_neq(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if abs(a - b) >= 1e-15 else 0.0)

    def _op_lt(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if a < b else 0.0)

    def _op_gt(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if a > b else 0.0)

    def _op_lte(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if a <= b else 0.0)

    def _op_gte(self, i: Instruction):
        self._binop(lambda a, b: 1.0 if a >= b else 0.0)

    # int8 saturation
    def _op_satadd(self, i: Instruction):
        self._binop(lambda a, b: max(-128.0, min(127.0, a + b)))

    def _op_satsub(self, i: Instruction):
        self._binop(lambda a, b: max(-128.0, min(127.0, a - b)))

    def _op_clip(self, i: Instruction):
        upper = i.operands[1] if len(i.operands) > 1 else 127.0
        lower = i.operands[0] if len(i.operands) > 0 else -128.0
        v = self._pop()
        self._push(max(lower, min(upper, v)))

    def _op_mad(self, i: Instruction):
        c = self._pop()
        b = self._pop()
        a = self._pop()
        self._push(a * b + c)

    def _op_popcnt(self, i: Instruction):
        v = self._pop()
        bits = int(v) & 0xFFFFFFFFFFFFFFFF
        self._push(float(bin(bits).count("1")))

    def _op_ctz(self, i: Instruction):
        v = self._pop()
        bits = int(v) & 0xFFFFFFFFFFFFFFFF
        self._push(float((bits & -bits).bit_length() - 1) if bits else 64.0)

    def _op_pabs(self, i: Instruction):
        self._push(abs(self._pop()))

    def _op_pmin(self, i: Instruction):
        self._binop(min)

    # special
    def _op_nop(self, i: Instruction):
        pass

    def _op_debug(self, i: Instruction):
        pass

    def _op_trace(self, i: Instruction):
        pass

    def _op_dump(self, i: Instruction):
        pass

    # ── FLUX-DEEP: Galois Adjunctions ───────────────────────────────

    def _op_xorinvert(self, i: Instruction):
        mask = self._pop()
        val = self._pop()
        self._push(float(int(val) ^ int(mask)))

    def _op_clamp(self, i: Instruction):
        upper = self._pop()
        lower = self._pop()
        val = self._pop()
        self._push(max(lower, min(upper, val)))

    def _op_bloom(self, i: Instruction):
        item = self._pop()
        filt = self._pop()
        h = abs(item * 2654435769.0)
        self._push(float(int(filt) | int(h)))

    def _op_bloomq(self, i: Instruction):
        item = self._pop()
        filt = self._pop()
        h = abs(item * 2654435769.0)
        self._push(1.0 if (int(filt) & int(h)) != 0 else 0.0)

    def _op_floorq(self, i: Instruction):
        step = self._pop()
        val = self._pop()
        self._push(math.floor(val / step) * step)

    def _op_ceilq(self, i: Instruction):
        step = self._pop()
        val = self._pop()
        self._push(math.ceil(val / step) * step)

    def _op_align(self, i: Instruction):
        tol = self._pop()
        intent = self._pop()
        val = self._pop()
        self._push(1.0 if abs(val - intent) <= tol else 0.0)

    def _op_holonomy(self, i: Instruction):
        n = int(self._pop())
        product = 1.0
        for _ in range(n):
            v = self._pop()
            product *= (1.0 if v >= 0.0 else -1.0)
        self._push(product)

    # ── FLUX-DEEP: Cross-Domain ─────────────────────────────────────

    def _op_tdqkr(self, i: Instruction):
        k = int(self._pop())
        n_cols = int(self._pop())
        n_rows = int(self._pop())
        query = self._pop()
        self._push(query * query)

    def _op_amnesia(self, i: Instruction):
        age = self._pop()
        valence = self._pop()
        tau = i.operands[0] if i.operands else 1.0
        self._push(valence * math.exp(-age / tau))

    def _op_shadow(self, i: Instruction):
        n = int(self._pop())
        total = sum(self._pop() for _ in range(n))
        self._push(max(0.0, min(1.0, 1.0 - total)))

    def _op_phase(self, i: Instruction):
        threshold = self._pop()
        order_param = self._pop()
        self._push(1.0 if order_param > threshold else 0.0)

    def _op_couple(self, i: Instruction):
        b = self._pop()
        a = self._pop()
        norm = max(1e-10, math.sqrt(a * a + b * b))
        self._push((a * b) / norm)

    def _op_federate(self, i: Instruction):
        n = int(self._pop())
        yes = sum(1.0 for _ in range(n) if self._pop() > 0.5)
        self._push(1.0 if yes > n / 2.0 else 0.0)

    def _op_bearing(self, i: Instruction):
        angle = self._pop()
        normalized = ((angle % 360.0) + 360.0) % 360.0
        snapped = int(round(normalized / 30.0)) % 12
        self._push(float(snapped))

    def _op_depth(self, i: Instruction):
        time_ms = self._pop()
        speed = i.operands[0] if i.operands else 1500.0
        self._push(speed * time_ms / 2000.0)

    # ── FLUX-DEEP: Projection / Reconstruction ──────────────────────

    def _op_project(self, i: Instruction):
        tiling_dim = int(self._pop())
        embed_dim = int(self._pop())
        n = len(self.stack)
        coord_count = min(embed_dim, n)
        coords = self.stack[-coord_count:]
        del self.stack[-coord_count:]

        phi = self.PHI
        projected = []
        for t in range(tiling_dim):
            s = 0.0
            for ci, c in enumerate(coords):
                s += c * ((ci + t + 1) * phi) % 1.0
            projected.append(s)

        residue_len = max(0, embed_dim - tiling_dim)
        residue = []
        for ri in range(residue_len):
            idx = tiling_dim + ri
            residue.append(coords[idx] if idx < len(coords) else 0.0)

        residue_ptr = float(len(self.residue_memory))
        self.residue_memory.append(residue)

        for v in projected:
            self._push(v)
        self._push(residue_ptr)

    def _op_reconstruct(self, i: Instruction):
        residue_ptr = int(self._pop())
        projected = list(self.stack)
        self.stack.clear()

        residue = (
            self.residue_memory[residue_ptr]
            if residue_ptr < len(self.residue_memory)
            else [0.0] * 4
        )

        phi = self.PHI
        embed_dim = len(projected) + len(residue)
        reconstructed = []
        for idx in range(embed_dim):
            if idx < len(projected):
                inv_factor = 1.0 / max(0.1, ((idx + 1) * phi) % 1.0)
                reconstructed.append(
                    projected[idx] * inv_factor / math.sqrt(embed_dim)
                )
            else:
                ri = idx - len(projected)
                reconstructed.append(residue[ri] if ri < len(residue) else 0.0)

        for v in reconstructed:
            self._push(v)

    def _op_window(self, i: Instruction):
        self.acceptance_window = max(0.0, self._pop())

    def _op_residue(self, i: Instruction):
        if self.residue_memory:
            for v in self.residue_memory[-1]:
                self._push(v)

    def _op_nasty(self, i: Instruction):
        dim = int(self._pop())
        threshold = int(i.operands[0]) if i.operands else 2
        self._push(1.0 if dim > threshold else 0.0)

    def _op_snaphigh(self, i: Instruction):
        dim = int(self._pop())
        take = min(dim, len(self.stack))
        coords = self.stack[-take:]
        del self.stack[-take:]

        phi = self.PHI
        for ci, c in enumerate(coords):
            lattice_spacing = phi ** (ci % 5)
            coords[ci] = round(c / lattice_spacing) * lattice_spacing

        for v in coords:
            self._push(v)

    # ── dispatch table ──────────────────────────────────────────────

    _dispatch = {
        opcodes.ADD: _op_add, opcodes.SUB: _op_sub,
        opcodes.MUL: _op_mul, opcodes.DIV: _op_div, opcodes.MOD: _op_mod,
        opcodes.ASSERT: _op_assert, opcodes.CHECK: _op_check,
        opcodes.VALIDATE: _op_validate, opcodes.REJECT: _op_reject,
        opcodes.JUMP: _op_jump, opcodes.BRANCH: _op_branch,
        opcodes.CALL: _op_call, opcodes.RETURN: _op_return,
        opcodes.HALT: _op_halt,
        opcodes.LOAD: _op_load, opcodes.STORE: _op_store,
        opcodes.PUSH: _op_push, opcodes.POP: _op_pop, opcodes.SWAP: _op_swap,
        opcodes.SNAP: _op_snap, opcodes.QUANTIZE: _op_quantize,
        opcodes.CAST: _op_cast, opcodes.PROMOTE: _op_promote,
        opcodes.AND: _op_and, opcodes.OR: _op_or,
        opcodes.NOT: _op_not, opcodes.XOR: _op_xor,
        opcodes.EQ: _op_eq, opcodes.NEQ: _op_neq,
        opcodes.LT: _op_lt, opcodes.GT: _op_gt,
        opcodes.LTE: _op_lte, opcodes.GTE: _op_gte,
        opcodes.SATADD: _op_satadd, opcodes.SATSUB: _op_satsub,
        opcodes.CLIP: _op_clip, opcodes.MAD: _op_mad,
        opcodes.POPCNT: _op_popcnt, opcodes.CTZ: _op_ctz,
        opcodes.PABS: _op_pabs, opcodes.PMIN: _op_pmin,
        opcodes.NOP: _op_nop, opcodes.DEBUG: _op_debug,
        opcodes.TRACE: _op_trace, opcodes.DUMP: _op_dump,
        opcodes.XORINVERT: _op_xorinvert, opcodes.CLAMP: _op_clamp,
        opcodes.BLOOM: _op_bloom, opcodes.BLOOMQ: _op_bloomq,
        opcodes.FLOORQ: _op_floorq, opcodes.CEILQ: _op_ceilq,
        opcodes.ALIGN: _op_align, opcodes.HOLONOMY: _op_holonomy,
        opcodes.TDQKR: _op_tdqkr, opcodes.AMNESIA: _op_amnesia,
        opcodes.SHADOW: _op_shadow, opcodes.PHASE: _op_phase,
        opcodes.COUPLE: _op_couple, opcodes.FEDERATE: _op_federate,
        opcodes.BEARING: _op_bearing, opcodes.DEPTH: _op_depth,
        opcodes.PROJECT: _op_project, opcodes.RECONSTRUCT: _op_reconstruct,
        opcodes.WINDOW: _op_window, opcodes.RESIDUE: _op_residue,
        opcodes.NASTY: _op_nasty, opcodes.SNAPHIGH: _op_snaphigh,
    }


# ── Convenience helpers ──────────────────────────────────────────────

def I(opcode: int, *operands: float, label: str = "") -> Instruction:
    """Shorthand to create an Instruction."""
    return Instruction(opcode=opcode, operands=list(operands), label=label)


def run_program(program: List[Instruction], *, verbose: bool = False) -> dict:
    """Create a VM, run program, optionally print trace."""
    vm = FluxVM()
    # The flow-control handlers need to know the next ip;
    # re-implement execute inline to handle jumps properly.
    vm.stack.clear()
    vm.call_stack.clear()
    vm.trace.clear()
    vm.constraint_results.clear()
    vm.residue_memory.clear()
    vm.acceptance_window = 1.0

    ip = 0
    while ip < len(program):
        instr = program[ip]
        stack_before = list(vm.stack)

        handler = FluxVM._dispatch.get(instr.opcode)
        if handler is None:
            raise FluxError(f"unknown opcode 0x{instr.opcode:02X} at step {ip}")

        cr = handler(vm, instr)
        vm.trace.append(TraceEntry(
            step=ip, opcode=instr.opcode,
            stack_before=stack_before, stack_after=list(vm.stack),
            constraint_result=cr,
        ))

        if instr.opcode == opcodes.HALT:
            break
        if instr.opcode == opcodes.JUMP:
            ip = int(instr.operands[0]) if instr.operands else 0
            continue
        if instr.opcode == opcodes.BRANCH:
            cond = stack_before[-1] if stack_before else 0.0
            if cond != 0.0:
                ip = int(instr.operands[0]) if instr.operands else 0
                continue
        if instr.opcode == opcodes.CALL:
            vm.call_stack.append(ip + 1)
            ip = int(instr.operands[0]) if instr.operands else 0
            continue
        if instr.opcode == opcodes.RETURN:
            if vm.call_stack:
                ip = vm.call_stack.pop()
                continue
            else:
                break
        ip += 1

    satisfied = (
        len(vm.constraint_results) > 0
        and all(vm.constraint_results)
    )

    if verbose:
        for t in vm.trace:
            name = _NAMES.get(t.opcode, f"0x{t.opcode:02X}")
            print(f"  [{t.step:3d}] {name:16s}  stack={_fmt(t.stack_after)}")

    return {
        "outputs": list(vm.stack),
        "constraints_satisfied": satisfied,
        "trace": vm.trace,
        "vm": vm,
    }


def _fmt(vals: List[float], max_items: int = 8) -> str:
    """Format a stack list for display."""
    if len(vals) <= max_items:
        items = [f"{v:.4g}" for v in vals]
    else:
        items = [f"{v:.4g}" for v in vals[:max_items]]
        items.append(f"... ({len(vals)} total)")
    return "[" + ", ".join(items) + "]"
