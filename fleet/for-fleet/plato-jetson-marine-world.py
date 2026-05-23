"""
plato-jetson Marine World Module

Integrates the 15-room dive chain with FLUX marine physics.
Each room is an Evennia-compatible class that:
- Generates descriptions based on depth + visibility
- Responds to 'sonarping' command with physics data
- Handles depth pressure, temperature, hazards
- Manages exit traversal with depth constraints

Designed as a drop-in module for plato-jetson/world/
Usage: python marined_world.py --generate to produce room stubs
"""

import math, json, sys

# ---- Physics Engine (standalone, no FLUX runtime dependency) ----

WATER_TYPES = {0: 'Coastal', 1: 'Oceanic Type II', 2: 'Oceanic Type IB', 3: 'Clear Oceanic'}
SEDIMENT_NAMES = {0: 'mud', 1: 'sand', 2: 'gravel', 3: 'rock', 4: 'seagrass'}
SEDIMENT_REFLECT = {0: 0.3, 1: 0.5, 2: 0.7, 3: 0.85, 4: 0.2}
SEASON_NAMES = {0: 'summer', 1: 'winter'}

def francois_garrison_absorption(wavelength_nm, water_type):
    """Francois-Garrison absorption coefficient (m^-1)."""
    wa = wavelength_nm / 1000.0
    if water_type <= 1:
        return 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
    elif water_type == 2:
        return 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
    else:
        return 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))

def rayleigh_scattering(wavelength_nm, depth_m):
    """Depth-dependent Rayleigh-like scattering (m^-1)."""
    wl = wavelength_nm * 1e-9
    near_surface = 0.002 * (480e-9 / wl)**4.3
    return near_surface * max(0.01, 1.0 - depth_m * 0.003)

def jerlov_water_type(chlorophyll_mgm3):
    """Classify water by Jerlov types based on chlorophyll."""
    if chlorophyll_mgm3 > 10.0:
        return 0
    elif chlorophyll_mgm3 > 1.0:
        return 1
    elif chlorophyll_mgm3 > 0.1:
        return 2
    return 3

def thermocline_gradient(depth_m, season=0):
    """Compute dT/dz at given depth (deg/m)."""
    tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
    st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
    temp = dt + (st - dt) * math.exp(-((depth_m - tc)**2) / (2 * tw**2))
    dTdz = -(st - dt) * (depth_m - tc) / (tw**2) * math.exp(-((depth_m - tc)**2) / (2 * tw**2))
    return temp, dTdz

def seabed_reflectivity(depth_m, sediment_type):
    """Reflectivity with depth attenuation."""
    return SEDIMENT_REFLECT[sediment_type] * math.exp(-depth_m * 0.003)

def total_attenuation(absorption, scattering):
    """Total attenuation coefficient (m^-1)."""
    return absorption + scattering

def secchi_visibility(attenuation, depth_m):
    """Secchi depth approximation (m)."""
    return min(depth_m, 1.7 / max(attenuation, 0.001))

def mackenzie_sound_speed(temp_c, salinity_psu, depth_m):
    """Mackenzie equation for speed of sound in seawater (m/s)."""
    return (1449.2 + 4.6*temp_c - 0.055*temp_c**2 + 0.00029*temp_c**3 +
            (1.34 - 0.01*temp_c)*(salinity_psu - 35) + 0.016*depth_m)

def snell_refraction(theta_deg, v_ratio):
    """Snell's law refraction angle (degrees)."""
    theta = math.radians(theta_deg)
    sin_theta2 = math.sin(theta) * v_ratio
    if sin_theta2 > 1.0:
        return 90.0
    return math.degrees(math.asin(sin_theta2))

class MarinePhysicsScope:
    """Compute all physics for a given depth + environment."""

    def __init__(self, depth_m, chlorophyll=5.0, season=0, sediment=1,
                 wavelength=480.0, salinity=35.0):
        self.depth = depth_m
        self.chlorophyll = chlorophyll
        self.season = season
        self.sediment = sediment
        self.wavelength = wavelength
        self.salinity = salinity

    def compute(self):
        w = jerlov_water_type(self.chlorophyll)
        temp, dtdz = thermocline_gradient(self.depth, self.season)
        self.water_type = w
        self.water_type_name = WATER_TYPES[w]
        self.season_name = SEASON_NAMES[self.season]
        self.sediment_name = SEDIMENT_NAMES[self.sediment]
        self.absorption = round(francois_garrison_absorption(self.wavelength, w), 4)
        self.scattering = round(rayleigh_scattering(self.wavelength, self.depth), 4)
        self.temperature = round(temp, 2)
        self.dTdz = round(dtdz, 4)
        self.attenuation = round(total_attenuation(self.absorption, self.scattering), 4)
        self.visibility = round(secchi_visibility(self.attenuation, self.depth), 2)
        self.seabed = round(seabed_reflectivity(self.depth, self.sediment), 4)
        self.sound_speed = round(mackenzie_sound_speed(temp, self.salinity, self.depth), 1)
        self.refraction = round(snell_refraction(30.0, self.sound_speed/1480.0), 2)
        return self

    def to_dict(self):
        return {
            'depth': self.depth,
            'water_type': self.water_type,
            'water_type_name': self.water_type_name,
            'temperature': self.temperature,
            'dTdz': self.dTdz,
            'season': self.season_name,
            'visibility': self.visibility,
            'absorption': self.absorption,
            'scattering': self.scattering,
            'attenuation': self.attenuation,
            'seabed_reflectivity': self.seabed,
            'sound_speed': self.sound_speed,
            'refraction_deg': self.refraction,
            'sediment': self.sediment_name,
        }

    def sonar_ping_summary(self):
        d = self.to_dict()
        return (
            f"=== SONAR PING @ {d['depth']:.0f}m ===\n"
            f"Water Type : {d['water_type_name']}\n"
            f"Temperature: {d['temperature']:.1f}C (dT/dz = {d['dTdz']:+.4f} C/m)\n"
            f"Absorption : {d['absorption']:.4f} m^-1\n"
            f"Scattering : {d['scattering']:.4f} m^-1\n"
            f"Attenuation: {d['attenuation']:.3f} m^-1\n"
            f"Visibility : {d['visibility']:.1f}m\n"
            f"Seabed Refl: {d['seabed_reflectivity']:.3f} ({d['sediment_name']})\n"
            f"Sound Speed: {d['sound_speed']:.0f} m/s\n"
            f"Refraction : {d['refraction_deg']:.1f} deg"
        )


# ---- Room Definitions ----

ROOM_TEMPLATES = [
    (0, "Harbor Shore", 0, 1, 8.0, 0, [], {"south": 1}),
    (1, "Shallow Flats", 2, 1, 7.4, 0, [], {"north": 0, "south": 2}),
    (2, "Tidal Channel", 5, 1, 6.8, 0, ["current"], {"north": 1, "south": 3}),
    (3, "Kelp Forest", 8, 2, 6.2, 0, ["kelp tangle"], {"north": 2, "south": 4}),
    (4, "Thermocline Layer", 15, 1, 4.0, 0, ["temperature shock"], {"north": 3, "south": 5}),
    (5, "Midwater Reef", 20, 3, 2.0, 0, ["sharp rock"], {"north": 4, "south": 6}),
    (6, "Open Water", 30, 1, 0.8, 0, [], {"north": 5, "south": 7}),
    (7, "Canyon Rim", 40, 3, 0.5, 0, ["depth pressure"], {"north": 6, "south": 8}),
    (8, "Canyon Wall", 50, 3, 0.3, 0, ["cold seep"], {"north": 7, "south": 9}),
    (9, "Deep Shelf", 60, 0, 0.2, 0, [], {"north": 8, "south": 10}),
    (10, "Anemone Garden", 65, 0, 0.15, 0, [], {"north": 9, "south": 11}),
    (11, "Seabed Canyon", 75, 0, 0.1, 0, ["deep pressure"], {"north": 10, "south": 12}),
    (12, "Hydrothermal Vent", 80, 3, 0.08, 0, ["heat damage", "toxic water"], {"north": 11, "south": 13}),
    (13, "Abyssal Plain", 90, 0, 0.06, 0, ["extreme cold"], {"north": 12, "south": 14}),
    (14, "The Drop", 100, 3, 0.05, 0, ["lethal pressure"], {"north": 13}),
]

DESCRIPTION_CLEAR = [
    "Sunlight glints off gentle waves. Sandy seabed with scattered shells.",
    "Crystal-clear water over white sand. Schools of silversides dart past.",
    "A narrow channel between sandbars. Brisk current. Starfish cling to rocks.",
    "Towering stalks of bull kelp rise from the seabed, swaying in the surge.",
    "You feel a sudden temperature shift — the thermocline. Shimmering patterns refract through the density gradient.",
    "A rocky outcropping teeming with life. Anemones wave. A lingcod lurks in a crevice.",
    "The seabed slopes into blue darkness. A school of salmon passes overhead.",
    "The sea floor drops into a submarine canyon. Glowing jellies pulse below.",
    "A near-vertical rock face with bioluminescent organisms glowing from crevices.",
    "A flat, silty plain stretches in all directions. Brittle stars crawl across the bottom.",
    "Hundreds of anemones cover the seafloor in pink and white. A giant Pacific octopus peers from a den.",
    "The deep canyon floor. A glass sponge reef rises like an alien cathedral.",
    "A field of black smokers billows superheated water. Tubeworms cluster around chimneys.",
    "The true deep. Fine clay seabed with manganese nodules. A gulper eel drifts past.",
    "The sea floor falls away into the hadal zone. Absolute darkness. Pressure readings critical.",
]

DESCRIPTION_MURKY = [
    "Harbor waters are stirred with silt. Visibility drops to a few meters.",
    "Sediment clouds obscure the bottom. You feel rather than see the sea grass.",
    "The channel runs fast and murky. You can barely see your hand in front of you.",
    "The kelp forms a dense, dark thicket. Visibility is poor among the stalks.",
    "The temperature boundary creates a blurry, wavering vision. Shapes distort.",
    "The reef is a shadowy mass. You bump into rock before you see it.",
    "You are suspended in grey gloom. The bottom is barely visible as a darker shadow.",
    "The canyon is a black void. You sense rather than see the drop-off.",
    "The wall vanishes into darkness. Sonar shows it continues another 30 meters.",
    "The silt plain is monochrome and featureless. Your senses feel muted.",
    "The anemones are grey shadows in the murk. Nearly step on the octopus's den.",
    "You stand on the floor of a vast, dark canyon. Nothing stirs. Absolute silence.",
    "The vents are detected as heat blooms on sonar. Visibility is zero.",
    "Absolute darkness. Sonar pings return faint echoes from the flat plain.",
    "The abyss yawns before you. Instruments warn: do not descend without upgrades.",
]


def describe_room(room_id, physics_result):
    """Generate a room description string for Evennia."""
    data = physics_result.to_dict()
    desc = DESCRIPTION_CLEAR[room_id] if data['visibility'] > 5.0 else DESCRIPTION_MURKY[room_id]

    details = (
        f"\n\n=== Environmental Report ==="
        f"\nDepth: {data['depth']:.0f}m | Water: {data['water_type_name']}"
        f"\nTemperature: {data['temperature']:.1f}C | Sound Speed: {data['sound_speed']:.0f} m/s"
        f"\nVisibility: {data['visibility']:.1f}m | Attenuation: {data['attenuation']:.3f} m^-1"
    )

    return desc + details


def autopilot_path(start=0, end=14):
    """Find a path through the MUD from start to end."""
    graph = {r[0]: r[7] for r in ROOM_TEMPLATES}
    queue = [(start, [start])]
    visited = {start}

    while queue:
        room, path = queue.pop(0)
        if room == end:
            return path
        for exit_name, next_id in graph[room].items():
            if next_id not in visited:
                visited.add(next_id)
                queue.append((next_id, path + [next_id]))
    return None


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--scan':
        print(f"{'Depth':>5} {'Type':>18} {'Temp':>6} {'dT/dz':>8} {'Atten':>7} {'Vis':>5} {'Seabed':>7} {'Sound':>7} {'Refrac':>6}")
        print("-" * 90)
        for rid, name, depth, sediment, chl, season, hazards, exits in ROOM_TEMPLATES:
            s = MarinePhysicsScope(depth, chl, season, sediment).compute()
            d = s.to_dict()
            print(f"{depth:5d}m {d['water_type_name']:>18} {d['temperature']:6.1f}C {d['dTdz']:8.4f} {d['attenuation']:7.3f} {d['visibility']:5.1f}m {d['seabed_reflectivity']:7.3f} {d['sound_speed']:7.0f} {d['refraction_deg']:6.1f} deg")

        path = autopilot_path(0, 14)
        print(f"\nDive path (Harbor Shore → The Drop):")
        for i in path:
            room = ROOM_TEMPLATES[i]
            print(f"  [{room[0]}] {room[1]} ({room[2]}m)")

    else:
        for depth in [0, 5, 15, 30, 60, 80, 100]:
            s = MarinePhysicsScope(depth).compute()
            print(f"\n--- @ {depth}m ---")
            print(s.sonar_ping_summary())
