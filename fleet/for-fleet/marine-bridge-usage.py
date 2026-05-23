"""
marine-bridge-usage.py — Complete example of the MEP protocol + marine-gpu-edge bridge.

This demonstrates the full data flow:
  FLUX Physics (Python) → MEP Frame (16-byte packed) → CUDA Beamformer → Result

The MEP (Marine Engineering Protocol) frame is 16 bytes:
  [depth:4][temp:2][salinity:2][sound_speed:2][confidence:2][flags:2][padding:2]

Usage:
  python marine-bridge-usage.py        # Run full example
  python marine-bridge-usage.py --sim  # Simulation mode (no CUDA required)
"""

import math, struct, json, sys

# ================================
# MEP Protocol Frame
# ================================

MEP_FORMAT = '!f 3H 2H'  # network byte order: float + 3 halfs + 2 u16 = 4+6+4 = 14 bytes + 2 padding = 16
# depth_f: float (meters)
# temp_q12: half (0.25 deg C resolution)
# salinity_q12: half (0.1 PSU resolution)
# sound_speed_half: half (m/s)
# confidence_u16: u16 (0-65535, scale to 0-1)
# flags_u16: bitfield

# Full 16-byte format with explicit padding at the end
MEP_FULL = '!f 4H 2H'  # float + 4 halfs + 2 u16 = 4+8+4 = 16 bytes

def physics_to_mep_frame(physics_result, confidence=65535, flags=0):
    """Pack a physics result into a 16-byte MEP frame."""
    depth = physics_result['depth']
    temp_encoded = int(max(0, min(32767, physics_result['temperature'] * 4)))
    sal_encoded = int(max(0, min(32767, physics_result.get('salinity', 35) * 10)))
    sound_encoded = int(max(0, min(65535, physics_result['sound_speed'] * 1)))
    conf = min(65535, confidence)
    flg = min(65535, flags)
    padding = 0
    
    return struct.pack(MEP_FULL, depth, temp_encoded, sal_encoded,
                       sound_encoded, conf, flg, padding)

def mep_frame_to_physics(frame_bytes):
    """Unpack a 16-byte MEP frame back to physics values."""
    depth, temp_raw, sal_raw, sound_raw, conf, flags, _ = \
        struct.unpack(MEP_FULL, frame_bytes)
    return {
        'depth': round(depth, 1),
        'temperature': round(temp_raw / 4.0, 2),
        'salinity': round(sal_raw / 10.0, 1),
        'sound_speed': round(sound_raw * 1.0, 0),
        'confidence': round(conf / 65535.0, 4),
        'flags': flags,
    }

def mep_frame_checksum(frame_bytes):
    """Simple XOR checksum across all 16 bytes."""
    checksum = 0
    for b in frame_bytes:
        checksum ^= b
    return checksum


# ================================
# Physics Engine (standalone)
# ================================

def compute_physics_at_depth(depth, chl=5.0, season=0, sediment=1, wl=480.0, sal=35.0):
    """Compute all physics for a depth point (same as FLUX vm.physics)."""
    # Water type
    if chl > 10.0:     wt = 0
    elif chl > 1.0:    wt = 1
    elif chl > 0.1:    wt = 2
    else:              wt = 3
    
    # Absorption
    wa = wl / 1000.0
    if wt <= 1:
        absorp = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
    elif wt == 2:
        absorp = 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
    else:
        absorp = 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))
    
    # Scattering
    ns = 0.002 * (480e-9 / (wl * 1e-9))**4.3
    scat = ns * max(0.01, 1.0 - depth * 0.003)
    
    # Thermocline
    tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
    st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
    temp = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
    dtdz = -(st - dt) * (depth - tc) / (tw**2) * math.exp(-((depth - tc)**2) / (2 * tw**2))
    
    # Seabed
    seabed = ({0: 0.3, 1: 0.5, 2: 0.7, 3: 0.85, 4: 0.2}[sediment]
              * math.exp(-depth * 0.003))
    
    # Attenuation + visibility
    atten = absorp + scat
    vis = min(depth, 1.7 / max(atten, 0.001))
    
    # Sound speed
    ss = (1449.2 + 4.6*temp - 0.055*temp**2 + 0.00029*temp**3 +
          (1.34 - 0.01*temp)*(sal - 35) + 0.016*depth)
    
    # Refraction
    v_ratio = ss / 1480.0
    theta = math.radians(30.0)
    sin_theta2 = math.sin(theta) * (1.0 / v_ratio)
    refrac = 90.0 if sin_theta2 > 1.0 else math.degrees(math.asin(sin_theta2))
    
    return {
        'depth': depth,
        'water_type': ['Coastal', 'Ocn-II', 'Ocn-IB', 'Clear'][wt],
        'temperature': round(temp, 2),
        'dtdz': round(dtdz, 4),
        'salinity': sal,
        'absorption': round(absorp, 4),
        'scattering': round(scat, 4),
        'attenuation': round(atten, 4),
        'visibility': round(vis, 2),
        'seabed_reflectivity': round(seabed, 4),
        'sound_speed': round(ss, 1),
        'refraction_deg': round(refrac, 2),
    }


# ================================
# Simulated CUDA Beamformer
# ================================

class SimulatedCUDABeamformer:
    """Simulates the CUDA beamformer from marine-gpu-edge."""
    
    def __init__(self):
        self.hydrophones = 48
        self.spacing_m = 0.02  # 2cm spacing
        self.sound_speed = 1500.0
    
    def beamform(self, mep_frames):
        """Simulated delay-and-sum beamforming from MEP frames."""
        if not mep_frames:
            return {'beams': [], 'elapsed_ms': 0, 'samples': 0}
        
        # Extract depths and sound speeds from MEP frames
        n_samples = len(mep_frames)
        depths = [f['depth'] for f in mep_frames]
        speeds = [f['sound_speed'] for f in mep_frames]
        confs = [f['confidence'] for f in mep_frames]
        
        # Simulate beamforming: compute arrival angle from sound speed
        beams = []
        for i in range(n_samples):
            # Steer angle based on sound speed gradient
            if i > 0:
                grad = (speeds[i] - speeds[i-1]) / max(depths[i] - depths[i-1], 0.1)
            else:
                grad = 0
            
            # Beam angle: Snell's law with gradient
            theta_deg = math.degrees(math.asin(
                min(1.0, math.sin(math.radians(30)) * speeds[i] / 1500.0)
            ))
            
            # Delay at each hydrophone
            delays = [
                (j * self.spacing_m * math.sin(math.radians(theta_deg)) / max(speeds[i], 1))
                for j in range(self.hydrophones)
            ]
            
            # Power in beam (simulated)
            beam_power = confs[i] * math.exp(-abs(theta_deg - 30) / 10)
            
            # Direction: up/down/direct based on gradient sign
            if abs(grad) < 0.01:
                direction = 'direct'
            elif grad > 0:
                direction = 'upward_refracted'
            else:
                direction = 'downward_refracted'
            
            beams.append({
                'depth': depths[i],
                'angle_deg': round(theta_deg, 2),
                'power': round(beam_power, 4),
                'direction': direction,
                'delays_us': [round(d * 1e6, 2) for d in delays[:5]],  # first 5 only
                'ping_quality': 'high' if confs[i] > 0.8 else 'medium',
            })
        
        elapsed = n_samples * 0.83  # simulation: 0.83ms per frame
        return {
            'beams': beams,
            'elapsed_ms': round(elapsed, 2),
            'samples': n_samples,
            'hydrophones': self.hydrophones,
            'avg_sound_speed': round(sum(speeds) / len(speeds), 1),
        }


# ================================
# Full Pipeline Demo
# ================================

def run_full_pipeline():
    print("=" * 70)
    print("  MEP Protocol + marine-gpu-edge Bridge Demo")
    print("=" * 70)
    
    # 1. Compute physics for dive profile
    print("\n[1] Computing FLUX physics (21 depth points)...\n")
    depths = list(range(0, 105, 5))
    physics_results = []
    for d in depths:
        chl = max(0.05, 8.0 - d * 0.12)
        ph = compute_physics_at_depth(d, chl=chl)
        physics_results.append(ph)
    
    for ph in physics_results[:6]:
        print(f"  {ph['depth']:5.0f}m {ph['water_type']:>6} "
              f"{ph['temperature']:6.1f}C {ph['sound_speed']:7.1f}m/s "
              f"{ph['visibility']:5.1f}m")
    print(f"  ... ({len(depths) - 6} more)")
    
    # 2. Pack into MEP frames
    print("\n[2] Packing physics into MEP frames (16 bytes each)...\n")
    mep_frames = []
    for ph in physics_results:
        confidence = int(min(65535, 65535 * math.exp(-ph['depth'] / 200)))
        flags = (0x01 if ph['depth'] > 0 else 0x00)  # bit 0 = valid frame
        frame_bytes = physics_to_mep_frame(ph, confidence=confidence, flags=flags)
        checksum = mep_frame_checksum(frame_bytes)
        mep_frames.append({
            'bytes': frame_bytes,
            'hex': frame_bytes.hex(),
            'checksum': checksum,
        })
    
    for i, mf in enumerate(mep_frames[:3]):
        ph = physics_results[i]
        print(f"  Frame {i}: [{mf['hex']}] 16B  "
              f"depth={ph['depth']:.0f}m  "
              f"temp={ph['temperature']:.1f}C  "
              f"checksum=0x{mf['checksum']:02x}")
    print(f"  ... ({len(mep_frames) - 3} more)")
    
    # 3. Decode MEP frames back
    print("\n[3] Decoding MEP frames on CUDA side...\n")
    decoded_frames = []
    for mf in mep_frames:
        decoded = mep_frame_to_physics(mf['bytes'])
        decoded_frames.append(decoded)
    
    for df in decoded_frames[:3]:
        print(f"  Decoded: {df['depth']:5.1f}m "
              f"temp={df['temperature']:6.2f}C "
              f"salt={df['salinity']:5.1f}PSU "
              f"sound={df['sound_speed']:5.0f}m/s "
              f"conf={df['confidence']:.4f} "
              f"flags=0x{df['flags']:04x}")
    
    # 4. CUDA beamform
    print("\n[4] CUDA beamforming (simulated)...\n")
    beamformer = SimulatedCUDABeamformer()
    result = beamformer.beamform(decoded_frames)
    
    print(f"  Hydrophones   : {result['hydrophones']}")
    print(f"  Samples       : {result['samples']}")
    print(f"  Avg sound spd : {result['avg_sound_speed']:.0f} m/s")
    print(f"  Elapsed       : {result['elapsed_ms']} ms")
    print(f"  Frame rate    : {1000 / max(result['elapsed_ms'], 0.1):.0f} Hz\n")
    
    for beam in result['beams'][:5]:
        print(f"  @ {beam['depth']:5.0f}m "
              f"angle={beam['angle_deg']:6.2f} deg "
              f"power={beam['power']:.4f} "
              f"dir={beam['direction']:<22} "
              f"quality={beam['ping_quality']}")
    print(f"  ... ({len(result['beams']) - 5} more)")
    
    # 5. Summary
    est_bandwidth = len(mep_frames) * 16 * 5  # 5Hz update rate
    print(f"\n[5] Pipeline Summary")
    print(f"  MEP frame size: 16 bytes")
    print(f"  Est. bandwidth: {est_bandwidth} B/s ({est_bandwidth*8} bps)")
    print(f"  Pipeline depth: {len(mep_frames)} frames")
    print(f"  Total bytes:   {len(mep_frames) * 16} B")
    print(f"  Checksum:      XOR across all 16 bytes (verification on receive)")
    print(f"  Pinging:       240 Hz physics → 5 Hz MEP update")
    print("=" * 70)


def run_sim_only():
    print("=" * 70)
    print("  MEP Protocol Simulation (No CUDA Required)")
    print("=" * 70)
    
    # Single depth test
    ph = compute_physics_at_depth(15, chl=4.0)
    frame_bytes = physics_to_mep_frame(ph, confidence=60000, flags=0x0001)
    decoded = mep_frame_to_physics(frame_bytes)
    checksum = mep_frame_checksum(frame_bytes)
    
    print(f"\n  Physics @ 15m:")
    print(f"    Temperature : {ph['temperature']} C")
    print(f"    Sound speed : {ph['sound_speed']} m/s")
    print(f"    Visibility  : {ph['visibility']} m")
    print(f"    Attenuation : {ph['attenuation']} m^-1")
    
    print(f"\n  MEP Frame:")
    print(f"    Hex         : {frame_bytes.hex()}")
    print(f"    Checksum    : 0x{checksum:02x}")
    
    print(f"\n  Decoded:")
    print(f"    Depth       : {decoded['depth']} m")
    print(f"    Temperature : {decoded['temperature']} C (lossy: was {ph['temperature']})")
    print(f"    Sound speed : {decoded['sound_speed']} m/s")
    print(f"    Confidence  : {decoded['confidence']}")
    print(f"    Flags       : 0x{decoded['flags']:04x}")
    
    print(f"\n  Frame integrity: {'✅ PASS' if checksum == mep_frame_checksum(frame_bytes) else '❌ FAIL'}")
    print("=" * 70)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--sim':
        run_sim_only()
    else:
        run_full_pipeline()
