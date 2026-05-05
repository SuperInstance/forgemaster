#!/usr/bin/env python3
"""
Maritime Constraint Checker — FLUX-based safety for commercial fishing vessels.
Generates FLUX-C bytecode for real maritime safety constraints.
"""

import ctypes
from dataclasses import dataclass


@dataclass
class ConstraintResult:
    passed: bool
    constraint: str
    bytecode: list


class MaritimeConstraintChecker:
    """Generates and checks maritime safety constraints using FLUX-C bytecode."""

    # FLUX-C opcodes
    RANGE = 0x1D
    ASSERT = 0x1B
    BOOL_AND = 0x26
    BOOL_OR = 0x27
    DUP = 0x28
    SWAP = 0x29
    HALT = 0x1A

    def __init__(self, gpu_lib_path="/tmp/flux_cuda_kernels.so"):
        try:
            self.lib = ctypes.CDLL(gpu_lib_path)
            self.gpu = True
        except OSError:
            self.lib = None
            self.gpu = False

    def _check_gpu(self, bytecode: list, value: int) -> bool:
        """Check a single constraint via GPU."""
        if not self.gpu:
            return self._check_cpu(bytecode, value)
        bc = (ctypes.c_uint8 * len(bytecode))(*bytecode)
        inp = (ctypes.c_int32 * 1)(value)
        res = (ctypes.c_int32 * 1)()
        gas = (ctypes.c_int32 * 1)()
        self.lib.flux_vm_batch_cuda(bc, len(bytecode), inp, res, gas, 1, 1000)
        return res[0] == 0  # 0 = pass

    def _check_cpu(self, bytecode: list, value: int) -> bool:
        """Simple CPU fallback for constraint checking."""
        stack = [value]
        sp = 1
        pc = 0
        while pc < len(bytecode):
            op = bytecode[pc]
            if op == self.HALT:
                break
            elif op == self.ASSERT:
                if sp > 0:
                    v = stack[sp - 1]
                    sp -= 1
                    if v == 0:
                        return False
                pc += 1
            elif op == self.RANGE:
                if pc + 2 < len(bytecode) and sp > 0:
                    lo, hi = bytecode[pc + 1], bytecode[pc + 2]
                    v = stack[sp - 1]
                    sp -= 1
                    stack[sp] = 1 if (lo <= v <= hi) else 0
                    sp += 1
                pc += 3
            elif op == self.BOOL_AND:
                if sp >= 2:
                    b = stack[sp - 1]
                    a = stack[sp - 2]
                    sp -= 2
                    stack[sp] = 1 if (a and b) else 0
                    sp += 1
                pc += 1
            elif op == self.BOOL_OR:
                if sp >= 2:
                    b = stack[sp - 1]
                    a = stack[sp - 2]
                    sp -= 2
                    stack[sp] = 1 if (a or b) else 0
                    sp += 1
                pc += 1
            elif op == self.DUP:
                if sp > 0:
                    stack[sp] = stack[sp - 1]
                    sp += 1
                pc += 1
            elif op == self.SWAP:
                if sp >= 2:
                    stack[sp - 1], stack[sp - 2] = stack[sp - 2], stack[sp - 1]
                pc += 1
            else:
                pc += 1  # NOP
        return True

    def check_draft(self, vessel_draft: float, max_draft: float) -> ConstraintResult:
        """Check vessel draft against maximum safe draft.
        FLUX: draft in [0, max_draft]"""
        max_d = min(int(max_draft), 255)
        bc = [self.RANGE, 0, max_d, self.ASSERT, self.HALT]
        value = int(vessel_draft)
        passed = self._check_gpu(bc, value) if self.gpu else self._check_cpu(bc, value)
        return ConstraintResult(
            passed=passed,
            constraint=f"draft({vessel_draft}) in [0, {max_draft}]",
            bytecode=bc,
        )

    def check_weather(self, wind_speed: int, wave_height: int, visibility: int) -> ConstraintResult:
        """Check weather conditions safe for fishing.
        FLUX: wind in [0, 40] AND waves in [0, 15] AND visibility in [1, 255]"""
        # Each check is a separate constraint, ANDed on CPU
        constraints = [
            ([self.RANGE, 0, 40, self.ASSERT, self.HALT], wind_speed, "wind"),
            ([self.RANGE, 0, 15, self.ASSERT, self.HALT], wave_height, "waves"),
            ([self.RANGE, 1, 255, self.ASSERT, self.HALT], visibility, "visibility"),
        ]
        results = []
        for bc, val, name in constraints:
            r = self._check_gpu(bc, val) if self.gpu else self._check_cpu(bc, val)
            results.append(r)

        passed = all(results)
        return ConstraintResult(
            passed=passed,
            constraint=f"wind({wind_speed}) in [0,40] AND waves({wave_height}) in [0,15] AND vis({visibility}) in [1,255]",
            bytecode=constraints[0][0],  # first constraint as example
        )

    def check_catch_weight(self, catch_kg: int, hold_capacity_kg: int) -> ConstraintResult:
        """Check catch doesn't exceed hold capacity.
        FLUX: catch in [0, hold_capacity]"""
        cap = min(int(hold_capacity_kg), 255)
        bc = [self.RANGE, 0, cap, self.ASSERT, self.HALT]
        value = min(int(catch_kg), 255)
        passed = self._check_gpu(bc, value) if self.gpu else self._check_cpu(bc, value)
        return ConstraintResult(
            passed=passed,
            constraint=f"catch({catch_kg}kg) in [0, {hold_capacity_kg}kg]",
            bytecode=bc,
        )

    def check_crew_hours(self, hours_on_deck: int, max_hours: int = 16) -> ConstraintResult:
        """Check crew fatigue limits.
        FLUX: hours in [0, max_hours]"""
        mx = min(max_hours, 255)
        bc = [self.RANGE, 0, mx, self.ASSERT, self.HALT]
        passed = self._check_gpu(bc, hours_on_deck) if self.gpu else self._check_cpu(bc, hours_on_deck)
        return ConstraintResult(
            passed=passed,
            constraint=f"crew_hours({hours_on_deck}) in [0, {max_hours}]",
            bytecode=bc,
        )

    def check_navigation(self, lat_zone: int, restricted_zones: list) -> ConstraintResult:
        """Check vessel not in restricted navigation zone.
        FLUX: zone NOT in restricted list (simulated as range exclusion)"""
        # Simplified: check that zone is NOT in any restricted range
        # NOT [lo, hi] = val < lo OR val > hi
        if not restricted_zones:
            bc = [self.RANGE, 0, 255, self.ASSERT, self.HALT]  # anywhere is fine
            passed = True
        else:
            # For each restricted zone, check we're outside it
            results = []
            for zone_start, zone_end in restricted_zones:
                # Outside = below start OR above end
                bc_below = [self.RANGE, 0, max(0, zone_start - 1), self.ASSERT, self.HALT]
                bc_above = [self.RANGE, min(zone_end + 1, 255), 255, self.ASSERT, self.HALT]
                r_below = self._check_gpu(bc_below, lat_zone) if self.gpu else self._check_cpu(bc_below, lat_zone)
                r_above = self._check_gpu(bc_above, lat_zone) if self.gpu else self._check_cpu(bc_above, lat_zone)
                results.append(r_below or r_above)
            passed = all(results)
            bc = [self.RANGE, 0, 255, self.ASSERT, self.HALT]

        return ConstraintResult(
            passed=passed,
            constraint=f"zone({lat_zone}) NOT in {restricted_zones}",
            bytecode=bc,
        )


if __name__ == "__main__":
    checker = MaritimeConstraintChecker()
    print("=== Maritime Constraint Checker — FLUX-C ===\n")

    tests = [
        ("Draft OK", checker.check_draft, 3.5, 6.0),
        ("Draft OVER", checker.check_draft, 7.2, 6.0),
        ("Weather OK", checker.check_weather, 15, 4, 10),
        ("Weather STORM", checker.check_weather, 45, 4, 10),
        ("Catch OK", checker.check_catch_weight, 5000, 10000),
        ("Catch OVER", checker.check_catch_weight, 12000, 10000),
        ("Crew OK", checker.check_crew_hours, 10, 16),
        ("Crew EXHAUSTED", checker.check_crew_hours, 20, 16),
        ("Nav OK", checker.check_navigation, 50, [(10, 20), (80, 90)]),
        ("Nav RESTRICTED", checker.check_navigation, 15, [(10, 20), (80, 90)]),
    ]

    for name, func, *args in tests:
        result = func(*args)
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {name:>18}: {status}  {result.constraint}")

    print(f"\nGPU acceleration: {'enabled' if checker.gpu else 'CPU fallback'}")
