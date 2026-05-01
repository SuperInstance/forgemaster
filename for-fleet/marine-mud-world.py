"""
Marine MUD World — 15-room underwater dive chain.
Generated from FLUX physics parameters. Each room has:
- Depth-based description (clear vs murky)
- Sediment type for PHY_SEABED physics
- Hazards list for damage/threat modeling
- Exit connections for traversal

Usage:
  from world import marine_mud_world as world
  world.ROOMS[id] to access room data
  world.SONAR_CONFIG to get physics params
"""

ROOMS = [
    {
        "id": 0,
        "name": "Harbor Shore",
        "depth": 0,
        "sediment": 1,
        "hazards": [],
        "exits": {"south": 1},
        "description_clear": """
Sunlight glints off gentle waves. Fishing boats bob at anchor. The seabed is sandy with scattered shells.
        """,
        "description_murky": """
Harbor waters are stirred with silt. Visibility drops to a few meters.
        """
    },
    {
        "id": 1,
        "name": "Shallow Flats",
        "depth": 2,
        "sediment": 1,
        "hazards": [],
        "exits": {"north": 0, "south": 2, "east": 1},
        "description_clear": """
Crystal-clear water over white sand. Schools of silversides dart past. Sea grass waves in the current.
        """,
        "description_murky": """
Sediment clouds obscure the bottom. You feel rather than see the sea grass.
        """
    },
    {
        "id": 2,
        "name": "Tidal Channel",
        "depth": 5,
        "sediment": 1,
        "hazards": ["current +1"],
        "exits": {"north": 1, "south": 3},
        "description_clear": """
A narrow channel between sandbars. The current is brisk but manageable. Starfish cling to rocks.
        """,
        "description_murky": """
The channel runs fast and murky. You can barely see your hand in front of you.
        """
    },
    {
        "id": 3,
        "name": "Kelp Forest",
        "depth": 8,
        "sediment": 2,
        "hazards": ["kelp_tangle"],
        "exits": {"north": 2, "south": 4, "west": 2},
        "description_clear": """
Towering stalks of bull kelp rise from the seabed, swaying in the surge. Sunlight filters through in golden shafts. A harbor seal watches from the edge.
        """,
        "description_murky": """
The kelp forms a dense, dark thicket. Visibility is poor among the stalks.
        """
    },
    {
        "id": 4,
        "name": "Thermocline Layer",
        "depth": 15,
        "sediment": 1,
        "hazards": ["temperature_shock"],
        "exits": {"north": 3, "south": 5},
        "description_clear": """
You feel a sudden temperature shift — the thermocline. The water above is noticeably warmer. Strange shimmering patterns dance as light refracts through the density gradient.
        """,
        "description_murky": """
The temperature boundary creates a blurry, wavering vision. Shapes distort.
        """
    },
    {
        "id": 5,
        "name": "Midwater Reef",
        "depth": 20,
        "sediment": 3,
        "hazards": ["sharp_rock"],
        "exits": {"north": 4, "south": 6, "east": 4},
        "description_clear": """
A rocky outcropping teeming with life. Anemones wave their tentacles. A lingcod lurks in a crevice. The reef drops off steeply to the south.
        """,
        "description_murky": """
The reef is a shadowy mass. You bump into rock before you see it.
        """
    },
    {
        "id": 6,
        "name": "Open Water",
        "depth": 30,
        "sediment": 1,
        "hazards": [],
        "exits": {"north": 5, "south": 7},
        "description_clear": """
The seabed slopes away into blue darkness. A school of salmon passes overhead. You feel very small in this vast space.
        """,
        "description_murky": """
You are suspended in grey gloom. The bottom is barely visible as a darker shadow below.
        """
    },
    {
        "id": 7,
        "name": "Canyon Rim",
        "depth": 40,
        "sediment": 3,
        "hazards": ["depth_pressure"],
        "exits": {"north": 6, "south": 8, "east": 7},
        "description_clear": """
The sea floor drops away sharply into a submarine canyon. Glowing jellies pulse in the depths below. The wall is covered in ancient coral.
        """,
        "description_murky": """
The canyon is a black void. You sense rather than see the drop-off.
        """
    },
    {
        "id": 8,
        "name": "Canyon Wall",
        "depth": 50,
        "sediment": 3,
        "hazards": ["cold_seep"],
        "exits": {"north": 7, "south": 9},
        "description_clear": """
You descend along a near-vertical rock face. Strange bioluminescent organisms glow from crevices. The pressure is noticeable but manageable.
        """,
        "description_murky": """
The wall vanishes into darkness below. Your sonar shows it continues for another 30 meters.
        """
    },
    {
        "id": 9,
        "name": "Deep Shelf",
        "depth": 60,
        "sediment": 0,
        "hazards": ["cold +2"],
        "exits": {"north": 8, "south": 10},
        "description_clear": """
A flat, silty plain stretches in all directions. A few brittle stars crawl across the bottom. The water is cold and clear.
        """,
        "description_murky": """
The silt plain is monochrome and featureless. Your senses feel muted.
        """
    },
    {
        "id": 10,
        "name": "Anemone Garden",
        "depth": 65,
        "sediment": 0,
        "hazards": [],
        "exits": {"north": 9, "south": 11, "west": 10},
        "description_clear": """
Hundreds of anemones cover the seafloor in a carpet of pink and white. A giant Pacific octopus peers from a den. The sight is breathtaking.
        """,
        "description_murky": """
The anemones are grey shadows in the murk. You nearly step on the octopus's den.
        """
    },
    {
        "id": 11,
        "name": "Seabed Canyon",
        "depth": 75,
        "sediment": 0,
        "hazards": ["pressure +3"],
        "exits": {"north": 10, "south": 12},
        "description_clear": """
The deep canyon floor. Sediment is fine and soft. A glass sponge reef rises like an alien cathedral. The pressure is constant.
        """,
        "description_murky": """
You stand on the floor of a vast, dark canyon. Nothing stirs. The silence is absolute.
        """
    },
    {
        "id": 12,
        "name": "Hydrothermal Vent Field",
        "depth": 80,
        "sediment": 3,
        "hazards": ["heat_damage", "toxic_water"],
        "exits": {"north": 11, "south": 13},
        "description_clear": """
A field of black smokers billows superheated water. The contrast between freezing ambient and boiling vents creates wild thermal gradients. Tubeworms cluster around the chimneys.
        """,
        "description_murky": """
The vents are detected as heat blooms on your sonar. Visibility is zero — you navigate by thermal gradient alone.
        """
    },
    {
        "id": 13,
        "name": "Abyssal Plain",
        "depth": 90,
        "sediment": 0,
        "hazards": ["cold +4"],
        "exits": {"north": 12},
        "description_clear": """
The true deep. Water temperature hovers near freezing. The seabed is fine clay peppered with manganese nodules. A gulper eel drifts past.
        """,
        "description_murky": """
Absolute darkness. Your sonar pings return faint echoes from the flat plain.
        """
    },
    {
        "id": 14,
        "name": "The Drop",
        "depth": 100,
        "sediment": 3,
        "hazards": ["pressure_lethal"],
        "exits": {"north": 13},
        "description_clear": """
The sea floor falls away into the hadal zone. You stand at the edge of the continental slope. The darkness below is absolute. Your pressure readings are critical.
        """,
        "description_murky": """
The abyss yawns before you. Your instruments warn: do not descend further without upgrades.
        """
    },
]

SONAR_CONFIG = {
    "wavelength_nm": 480,
    "frequency_hz": 200000,
    "season": 0,  # 0=summer, 1=winter
    "pulse_width_ms": 10,
    "beam_angle_deg": 30,
    "absorption_model": "francois-garrison",
    "scattering_model": "rayleigh",
    "sound_speed_model": "mackenzie",
    "visibility_model": "secchi",
    "attenuation_model": "total",
    "refraction_model": "snell",
}


def get_room_by_depth(depth_m):
    """Find the closest room to a given depth."""
    closest = None
    min_diff = float("inf")
    for room in ROOMS:
        diff = abs(room["depth"] - depth_m)
        if diff < min_diff:
            min_diff = diff
            closest = room
    return closest


def render_room_description(room, visibility_m):
    """Choose clear or murky description based on visibility."""
    if visibility_m < 5.0:
        return room["description_murky"]
    return room["description_clear"]


if __name__ == "__main__":
    print(f"Marine MUD World: {len(ROOMS)} rooms")
    for r in ROOMS:
        h = ", ".join(r["hazards"]) if r["hazards"] else "none"
        print(f'  [{r["id"]:>2}] {r["depth"]:>4}m {r["name"]:<20} hazards: {h}')