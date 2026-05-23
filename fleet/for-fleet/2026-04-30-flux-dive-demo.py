#!/usr/bin/env python3
"""FLUX Marine Physics Dive Demo — all 9 opcodes, 21 depths, deterministic output."""
import sys, math
sys.path.insert(0, '/tmp/flux-runtime/src')
from flux.bytecode.opcodes import Op
from flux.vm.interpreter import Interpreter

def emit(code, op, rd, rs1, rs2):
    code.extend([op, rd, rs1, rs2])

LABELS = {0: 'Coastal', 1: 'Ocn-II', 2: 'Ocn-IB', 3: 'Clear'}

def run_dive(depths=None, season=0, sediment=1):
    if depths is None:
        depths = list(range(0, 105, 5))
    
    profiles = []
    for depth in depths:
        code = bytearray()
        emit(code, Op.PHY_JERLOV, 9, 1, 2)
        emit(code, Op.PHY_ABSORB, 10, 0, 9)
        emit(code, Op.PHY_SCATTER, 11, 0, 1)
        emit(code, Op.PHY_THERMO, 12, 1, 3)
        emit(code, Op.PHY_ATTEN, 13, 10, 11)
        emit(code, Op.PHY_VISIB, 14, 13, 1)
        emit(code, Op.PHY_SEABED, 15, 1, 4)
        emit(code, Op.PHY_SOUNDV, 16, 5, 6)
        emit(code, Op.PHY_REFRAC, 17, 7, 8)
        code.append(Op.HALT)
        
        st, dt, tc, tw = 22.0 if season == 0 else 8.0, 4.0, 15.0 if season == 0 else 40.0, 5.0 if season == 0 else 15.0
        temp = dt + (st - dt) * math.exp(-((depth - tc)**2)/(2*tw**2))
        
        vm = Interpreter(bytearray(code))
        vm.regs.write_fp(0, 480.0)
        vm.regs.write_fp(1, float(depth))
        vm.regs.write_fp(2, max(0.05, 8.0 - depth * 0.12))
        vm.regs.write_fp(3, float(season))
        vm.regs.write_fp(4, float(sediment))
        vm.regs.write_fp(5, temp)
        vm.regs.write_fp(6, 35.0)
        vm.regs.write_fp(7, math.radians(30))
        vm.regs.write_fp(8, 1500.0/1480.0)
        vm.execute()
        
        profiles.append({
            'depth': depth,
            'water_type': int(vm.regs.read_fp(9)),
            'absorption': round(vm.regs.read_fp(10), 4),
            'scattering': round(vm.regs.read_fp(11), 4),
            'thermocline': round(vm.regs.read_fp(12), 4),
            'attenuation': round(vm.regs.read_fp(13), 4),
            'visibility': round(vm.regs.read_fp(14), 2),
            'seabed': round(vm.regs.read_fp(15), 4),
            'sound_speed': round(vm.regs.read_fp(16), 1),
            'refraction_deg': round(math.degrees(vm.regs.read_fp(17)), 2),
        })
    
    return profiles

if __name__ == '__main__':
    profiles = run_dive()
    print(f"{'Depth':>5} {'Type':>7} {'Absorb':>7} {'Scatter':>8} {'dT/dz':>8} {'Atten':>7} {'Visib':>6} {'Seabed':>7} {'Sound':>8} {'Refrac':>6}")
    print('-'*90)
    for p in profiles:
        print(f"{p['depth']:5.0f}m {LABELS[p['water_type']]:>7} {p['absorption']:7.3f} {p['scattering']:8.4f} {p['thermocline']:8.4f} {p['attenuation']:7.3f} {p['visibility']:6.2f}m {p['seabed']:7.3f} {p['sound_speed']:8.1f} {p['refraction_deg']:6.2f}°")
    print(f"\n{len(profiles)} profiles, 9 physics opcodes per profile")
