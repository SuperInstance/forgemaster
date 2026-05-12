#!/usr/bin/env python3
"""Validate all PLATO MUD rooms are well-formed."""

import json
import os
import sys
from pathlib import Path

ROOMS_DIR = Path(__file__).parent / "rooms"
REQUIRED_ROOM_FIELDS = ["id", "name", "domain", "depth", "description", "look_text", "exits", "tiles", "npcs", "workbench", "substrate"]
REQUIRED_TILE_FIELDS = ["id", "title", "author", "created", "domain_tags", "confidence", "depth", "content", "lifecycle"]
REQUIRED_NPC_FIELDS = ["id", "name", "room", "personality", "expertise", "greeting", "dialog_tree"]
REQUIRED_STATE_FIELDS = ["room", "updated", "zeitgeist"]
VALID_DEPTHS = {"beginner", "intermediate", "advanced", "expert"}
VALID_LIFECYCLES = {"theoretical", "opinion", "experimental", "in-progress", "validated"}
VALID_SUBSTRATES = {"bare-metal", "interpreted", "mathematical", "virtual-machine", "field", "safety"}

errors = []
warnings = []
room_dirs = []

def check_json_file(path, label):
    """Load and parse a JSON file, returning the data or None on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"{label}: Invalid JSON — {e}")
        return None
    except FileNotFoundError:
        errors.append(f"{label}: File not found")
        return None

def validate_room(room_dir):
    """Validate a single room directory."""
    room_id = room_dir.name
    room_dirs.append(room_id)
    
    # Check room.json
    room = check_json_file(room_dir / "room.json", f"{room_id}/room.json")
    if room is None:
        return
    
    # Check required fields
    for field in REQUIRED_ROOM_FIELDS:
        if field not in room:
            errors.append(f"{room_id}/room.json: Missing field '{field}'")
    
    # Check id matches directory name
    if room.get("id") != room_id:
        errors.append(f"{room_id}/room.json: id '{room.get('id')}' doesn't match directory '{room_id}'")
    
    # Check depth
    if room.get("depth") not in VALID_DEPTHS:
        errors.append(f"{room_id}/room.json: Invalid depth '{room.get('depth')}'")
    
    # Check substrate
    if room.get("substrate") not in VALID_SUBSTRATES:
        errors.append(f"{room_id}/room.json: Invalid substrate '{room.get('substrate')}'")
    
    # Check description length
    desc = room.get("description", "")
    if len(desc) < 50:
        warnings.append(f"{room_id}/room.json: Description too short ({len(desc)} chars, want 50+)")
    
    # Check look_text
    look = room.get("look_text", "")
    if len(look) < 50:
        warnings.append(f"{room_id}/room.json: Look text too short ({len(look)} chars, want 50+)")
    
    # Check exits reference valid rooms (deferred — check after all rooms loaded)
    for exit_def in room.get("exits", []):
        if "direction" not in exit_def or "room" not in exit_def:
            errors.append(f"{room_id}/room.json: Exit missing 'direction' or 'room'")
    
    # Check tiles directory
    tiles_dir = room_dir / "tiles"
    if not tiles_dir.exists():
        errors.append(f"{room_id}/tiles/: Directory missing")
    else:
        tile_files = list(tiles_dir.glob("*.json"))
        tile_ids = []
        for tf in tile_files:
            tile = check_json_file(tf, f"{room_id}/tiles/{tf.name}")
            if tile is None:
                continue
            
            for field in REQUIRED_TILE_FIELDS:
                if field not in tile:
                    errors.append(f"{room_id}/tiles/{tf.name}: Missing field '{field}'")
            
            if tile.get("depth") not in VALID_DEPTHS:
                errors.append(f"{room_id}/tiles/{tf.name}: Invalid depth '{tile.get('depth')}'")
            
            if tile.get("lifecycle") not in VALID_LIFECYCLES:
                errors.append(f"{room_id}/tiles/{tf.name}: Invalid lifecycle '{tile.get('lifecycle')}'")
            
            confidence = tile.get("confidence", 0)
            if not (0 <= confidence <= 1):
                errors.append(f"{room_id}/tiles/{tf.name}: Confidence {confidence} out of range [0,1]")
            
            tile_ids.append(tile.get("id"))
        
        # Check room.json references match actual tiles
        referenced = room.get("tiles", [])
        for ref in referenced:
            if ref not in tile_ids:
                warnings.append(f"{room_id}: room.json references tile '{ref}' but no file found with that ID")
    
    # Check NPCs directory
    npcs_dir = room_dir / "npcs"
    if not npcs_dir.exists():
        errors.append(f"{room_id}/npcs/: Directory missing")
    else:
        npc_files = list(npcs_dir.glob("*.json"))
        npc_ids = []
        for nf in npc_files:
            npc = check_json_file(nf, f"{room_id}/npcs/{nf.name}")
            if npc is None:
                continue
            
            for field in REQUIRED_NPC_FIELDS:
                if field not in npc:
                    errors.append(f"{room_id}/npcs/{nf.name}: Missing field '{field}'")
            
            if npc.get("room") != room_id:
                errors.append(f"{room_id}/npcs/{nf.name}: NPC room '{npc.get('room')}' doesn't match '{room_id}'")
            
            dialog = npc.get("dialog_tree", [])
            if len(dialog) < 3:
                warnings.append(f"{room_id}/npcs/{nf.name}: Dialog tree has only {len(dialog)} entries (want 5+)")
            
            npc_ids.append(npc.get("id"))
        
        referenced_npcs = room.get("npcs", [])
        for ref in referenced_npcs:
            if ref not in npc_ids:
                warnings.append(f"{room_id}: room.json references NPC '{ref}' but no file found")
    
    # Check state.json
    state = check_json_file(room_dir / "state.json", f"{room_id}/state.json")
    if state is not None:
        for field in REQUIRED_STATE_FIELDS:
            if field not in state:
                errors.append(f"{room_id}/state.json: Missing field '{field}'")
        
        zg = state.get("zeitgeist", {})
        for metric in ["energy", "clarity", "tension", "discovery_rate"]:
            val = zg.get(metric)
            if val is not None and not (0 <= val <= 1):
                errors.append(f"{room_id}/state.json: zeitgeist.{metric} {val} out of range [0,1]")

def main():
    print("PLATO MUD Room Validator")
    print("=" * 40)
    
    # Validate map.json
    map_data = check_json_file(ROOMS_DIR / "map.json", "map.json")
    if map_data:
        map_rooms = set(map_data.get("rooms", {}).keys())
        print(f"Map defines {len(map_rooms)} rooms")
    
    # Validate each room directory
    for room_dir in sorted(ROOMS_DIR.iterdir()):
        if room_dir.is_dir() and (room_dir / "room.json").exists():
            validate_room(room_dir)
    
    # Cross-check: exits reference existing rooms
    if map_data:
        for room_id, room_def in map_data.get("rooms", {}).items():
            for direction, target in room_def.get("connections", {}).items():
                if target not in map_data["rooms"]:
                    errors.append(f"map.json: Room '{room_id}' exit {direction} → '{target}' not found in map")
    
    # Check all map rooms have directories
    if map_data:
        for room_id in map_data.get("rooms", {}):
            if room_id not in room_dirs:
                warnings.append(f"map.json: Room '{room_id}' has no directory")
    
    # Check alignment_constraints.json
    ac = check_json_file(ROOMS_DIR / "alignment_constraints.json", "alignment_constraints.json")
    if ac:
        constraints = ac.get("constraints", [])
        if len(constraints) != 8:
            errors.append(f"alignment_constraints.json: Expected 8 constraints, found {len(constraints)}")
        print(f"Alignment constraints: {len(constraints)} defined")
    
    # Summary
    print(f"\nRooms validated: {len(room_dirs)}")
    total_tiles = sum(len(list((ROOMS_DIR / r / "tiles").glob("*.json"))) for r in room_dirs if (ROOMS_DIR / r / "tiles").exists())
    total_npcs = sum(len(list((ROOMS_DIR / r / "npcs").glob("*.json"))) for r in room_dirs if (ROOMS_DIR / r / "npcs").exists())
    print(f"Total tiles: {total_tiles}")
    print(f"Total NPCs: {total_npcs}")
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  • {w}")
    
    if not errors:
        print(f"\n✅ All rooms valid!")
        if warnings:
            print(f"   ({len(warnings)} warnings)")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
