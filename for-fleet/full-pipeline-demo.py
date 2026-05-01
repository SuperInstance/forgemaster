"""
full-pipeline-demo.py — End-to-end SonarVision + FLUX + MUD + JEPA pipeline.

This file demonstrates the full circular pipeline:

  FLUX Physics (deterministic) → Marine MUD World → Sonar Pinging
       ↓                                                    ↓
  JEPA Perception (latent space) ← marine-gpu-edge (CUDA) ←┘

The pipeline is circular because Jetson runs all components and
output from any stage can feed any other stage.
"""

import math, json, sys, os

# ===========================
# STAGE 1: FLUX Marine Physics
# ===========================

WATER_TYPES = {0: 'Coastal', 1: 'Oceanic Type II', 2: 'Oceanic Type IB', 3: 'Clear Oceanic'}
SEDIMENT_REFLECT = {0: 0.3, 1: 0.5, 2: 0.7, 3: 0.85, 4: 0.2}

def flux_physics(depth, chl=5.0, season=0, sediment=1, wl=480.0, sal=35.0):
    """Execute all 9 FLUX physics opcodes for a given depth/environment."""
    # Op B2: PHY_JERLOV
    if chl > 10.0:     water_type = 0
    elif chl > 1.0:    water_type = 1
    elif chl > 0.1:    water_type = 2
    else:              water_type = 3

    # Op B0: PHY_ABSORB (Francois-Garrison)
    wa = wl / 1000.0
    if water_type <= 1:
        absorption = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
    elif water_type == 2:
        absorption = 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
    else:
        absorption = 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))

    # Op B1: PHY_SCATTER
    near_surface = 0.002 * (480e-9 / (wl * 1e-9))**4.3
    scattering = near_surface * max(0.01, 1.0 - depth * 0.003)

    # Op B3: PHY_THERMO
    tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
    st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
    temp = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
    dtdz = -(st - dt) * (depth - tc) / (tw**2) * math.exp(-((depth - tc)**2) / (2 * tw**2))

    # Op B4: PHY_SEABED
    seabed = SEDIMENT_REFLECT[sediment] * math.exp(-depth * 0.003)

    # Op B5: PHY_ATTEN
    attenuation = absorption + scattering

    # Op B6: PHY_VISIB
    visibility = min(depth, 1.7 / max(attenuation, 0.001))

    # Op B7: PHY_SOUNDV (Mackenzie)
    sound_speed = (1449.2 + 4.6*temp - 0.055*temp**2 + 0.00029*temp**3 +
                   (1.34 - 0.01*temp)*(sal - 35) + 0.016*depth)

    # Op B8: PHY_REFRAC
    v_ratio = sound_speed / 1480.0
    theta = math.radians(30.0)
    sin_theta2 = math.sin(theta) * (1.0 / v_ratio)
    if sin_theta2 > 1.0:
        refraction = 90.0
    else:
        refraction = math.degrees(math.asin(sin_theta2))

    return {
        'depth': depth,
        'water_type': water_type,
        'water_type_name': WATER_TYPES[water_type],
        'chlorophyll': chl,
        'absorption': round(absorption, 4),
        'scattering': round(scattering, 4),
        'temperature': round(temp, 2),
        'dtdz': round(dtdz, 4),
        'seabed_reflectivity': round(seabed, 4),
        'attenuation': round(attenuation, 4),
        'visibility': round(visibility, 3),
        'sound_speed': round(sound_speed, 1),
        'refraction_deg': round(refraction, 2),
        'season': 'summer' if season == 0 else 'winter',
    }


# ===========================
# STAGE 2: Marine MUD Room
# ===========================

MUD_ROOMS = [
    (0, "Harbor Shore", 0, "Sandy seabed with scattered shells."),
    (1, "Shallow Flats", 2, "White sand, silversides, sea grass."),
    (2, "Tidal Channel", 5, "Narrow channel, brisk current, starfish."),
    (3, "Kelp Forest", 8, "Bull kelp stalks swaying in surge."),
    (4, "Thermocline Layer", 15, "Sharp temperature gradient, shimmering refraction."),
    (5, "Midwater Reef", 20, "Rocky outcropping, lingcod, anemones."),
    (6, "Open Water", 30, "Vast blue darkness, salmon passing overhead."),
    (7, "Canyon Rim", 40, "Sea floor drops into submarine canyon."),
    (8, "Canyon Wall", 50, "Vertical rock face, bioluminescent organisms."),
    (9, "Deep Shelf", 60, "Flat silty plain, brittle stars."),
    (10, "Anemone Garden", 65, "Hundreds of anemones, giant octopus."),
    (11, "Seabed Canyon", 75, "Deep canyon floor, glass sponge reef."),
    (12, "Hydrothermal Vent", 80, "Black smokers, tubeworms, extreme heat."),
    (13, "Abyssal Plain", 90, "Near-freezing water, manganese nodules, gulper eel."),
    (14, "The Drop", 100, "Edge of continental slope. Absolute darkness."),
]

MUD_EXITS = {
    0: {"south": 1},
    1: {"north": 0, "south": 2},
    2: {"north": 1, "south": 3},
    3: {"north": 2, "south": 4},
    4: {"north": 3, "south": 5},
    5: {"north": 4, "south": 6},
    6: {"north": 5, "south": 7},
    7: {"north": 6, "south": 8},
    8: {"north": 7, "south": 9},
    9: {"north": 8, "south": 10},
    10: {"north": 9, "south": 11},
    11: {"north": 10, "south": 12},
    12: {"north": 11, "south": 13},
    13: {"north": 12, "south": 14},
    14: {"north": 13},
}


# ===========================
# STAGE 3: JEPA Latent Space
#   Simplified model: depth profile → latent vector
# ===========================

def jepa_encode(depths, physics_results):
    """Encode a depth profile into JEPA latent space.
    
    Simplfied: latent dimensions represent:
      [avg_absorption, avg_scattering, peak_temperature, max_dtdz, 
       deep_vis, surface_sound, water_type_transition_count, seabed_dropoff]
    """
    avgs = {k: sum(r[k] for r in physics_results) / len(physics_results)
            for k in ['absorption', 'scattering']}
    temps = [r['temperature'] for r in physics_results]
    dtdzs = [abs(r['dtdz']) for r in physics_results]
    deep = physics_results[-1] if len(physics_results) > 4 else physics_results[-1]
    surface = physics_results[0]

    # Count water type transitions
    transitions = 0
    for i in range(1, len(physics_results)):
        if physics_results[i]['water_type'] != physics_results[i-1]['water_type']:
            transitions += 1

    # Seabed dropoff (deep vs shallow)
    seabed_ratio = (physics_results[-1]['seabed_reflectivity'] /
                    max(physics_results[0]['seabed_reflectivity'], 0.001))

    latent = [
        round(avgs['absorption'] * 10, 4),     # L0: absorption magnitude
        round(avgs['scattering'] * 100, 4),     # L1: scattering magnitude
        round(max(temps), 4),                    # L2: peak temperature
        round(max(dtdzs), 4),                    # L3: max thermocline gradient
        round(deep['visibility'], 4),            # L4: deep visibility
        round(surface['sound_speed'], 4),        # L5: surface sound speed
        transitions,                              # L6: water type transitions
        round(seabed_ratio, 4),                   # L7: seabed reflectivity ratio
    ]

    return latent


# ===========================
# STAGE 4: SonarPing Command
#   The "sonarping" command for the MUD
# ===========================

def sonar_ping(depth, chl=5.0, verbose=True):
    """Simulate the /sonarping command from the MUD."""
    result = flux_physics(depth, chl=chl)
    if verbose:
        print(f"=== SONAR PING @ {depth:.0f}m ===")
        print(f"  Water Type : {result['water_type_name']}")
        print(f"  Temperature: {result['temperature']:.1f}C (dT/dz = {result['dtdz']:+.4f} C/m)")
        print(f"  Absorption : {result['absorption']:.4f} m^-1")
        print(f"  Scattering : {result['scattering']:.4f} m^-1")
        print(f"  Attenuation: {result['attenuation']:.3f} m^-1")
        print(f"  Visibility : {result['visibility']:.1f}m")
        print(f"  Seabed Refl: {result['seabed_reflectivity']:.3f}")
        print(f"  Sound Speed: {result['sound_speed']:.0f} m/s")
        print(f"  Refraction : {result['refraction_deg']:.1f} deg")
    return result


# ===========================
# FULL PIPELINE RUN
# ===========================

if __name__ == '__main__':
    print("=" * 70)
    print("  SonarVision + FLUX + MUD + JEPA Full Pipeline Demo")
    print("=" * 70)

    # --- Stage 1: Physics scan ---
    print("\n[STAGE 1] FLUX Marine Physics (21 depths, all 9 opcodes)\n")
    depths = list(range(0, 105, 5))
    physics_results = []
    for depth in depths:
        chl = max(0.05, 8.0 - depth * 0.12)
        result = flux_physics(depth, chl=chl)
        physics_results.append(result)

    header = f"{'Depth':>5} {'Type':>7} {'Abs':>6} {'Scat':>6} {'dT/dz':>8} {'Att':>6} {'Vis':>6} {'Seabed':>7}"
    print(header)
    print("-" * 65)
    for result in physics_results:
        print(f"{result['depth']:5.0f}m "
              f"{result['water_type_name'][:7]:>7} "
              f"{result['absorption']:6.3f} "
              f"{result['scattering']:6.4f} "
              f"{result['dtdz']:8.4f} "
              f"{result['attenuation']:6.3f} "
              f"{result['visibility']:5.2f}m "
              f"{result['seabed_reflectivity']:7.3f}")

    # --- Stage 2: MUD room lookup ---
    print("\n[STAGE 2] Marine MUD Room Lookup\n")
    for depth in [0, 15, 30, 50, 100]:
        closest_room = min(MUD_ROOMS, key=lambda r: abs(r[2] - depth))
        result = next(r for r in physics_results if r['depth'] == closest_room[2])
        desc = ("Clear waters reveal: " if result['visibility'] > 5.0
                else "Murky depths obscure: ")
        print(f"  @ {depth:3d}m → Room [{closest_room[0]}] {closest_room[1]:<20} "
              f"({closest_room[2]:3d}m)")
        print(f"               {desc}{closest_room[3]}")

    # --- Stage 3: Sonar ping demo ---
    print("\n[STAGE 3] Sonar Ping Command\n")
    for depth in [5, 25, 60, 95]:
        print(f"  > sonarping @{depth}m")
        result = sonar_ping(depth, chl=max(0.05, 8.0 - depth * 0.12))
        print()

    # --- Stage 4: JEPA latent space encoding ---
    print("\n[STAGE 4] JEPA Latent Space Encoding\n")
    latent = jepa_encode(depths, physics_results)
    print(f"  Latent vector ({len(latent)} dimensions):")
    labels = ['absorption', 'scattering', 'peak_temp', 'max_dtdz',
              'deep_vis', 'surface_sound', 'transitions', 'seabed_ratio']
    for label, val in zip(labels, latent):
        print(f"    {label:<20} = {val}")
    print()

    # --- Summary ---
    n_depths = len(depths)
    n_ops = 9
    n_rooms = len(MUD_ROOMS)
    n_latent = len(latent)
    print(f"\nPipeline summary: {n_depths} depths × {n_ops} ops → "
          f"{n_rooms} rooms → {n_latent}-dim latent space")
    print("Circular pipeline: Jetson runs all components")
    print("  FLUX → MUD → SonarPing → marine-gpu-edge → JEPA → FLUX")
