#!/usr/bin/env python3
"""input-treatment.py — Parse MUD events into work items."""
import sys
import re
import json
from datetime import datetime

def parse_mud_output(text):
    """Parse raw MUD output into structured events."""
    events = []
    
    # Detect room entries
    room_match = re.search(r'═══ (.+?) ═══', text)
    if room_match:
        events.append({"type": "room", "name": room_match.group(1)})
    
    # Detect agent says
    say_match = re.search(r'(\w+) says?: "(.+?)"', text)
    if say_match:
        events.append({"type": "say", "agent": say_match.group(1), "message": say_match.group(2)})
    
    # Detect notes
    if "Notes on the wall" in text:
        events.append({"type": "notes", "raw": text})
    
    # Detect who listing
    if "Fleet Roster" in text:
        events.append({"type": "roster", "raw": text})
    
    # Detect exits
    exit_match = re.search(r'Exits: (.+)', text)
    if exit_match:
        exits = [e.strip() for e in exit_match.group(1).split(",")]
        events.append({"type": "exits", "exits": exits})
    
    return events

def events_to_work_items(events):
    """Convert parsed events into actionable work items."""
    items = []
    for e in events:
        if e["type"] == "say":
            msg = e.get("message", "")
            if "?" in msg:
                items.append({"type": "question", "from": e["agent"], "question": msg})
            elif "DISCOVERY" in msg:
                items.append({"type": "discovery", "from": e["agent"], "text": msg})
            elif "urgent" in msg.lower() or "red alert" in msg.lower():
                items.append({"type": "urgent", "from": e["agent"], "text": msg})
        elif e["type"] == "exits":
            for exit_name in e["exits"]:
                if exit_name not in ["tavern", "harbor"]:
                    items.append({"type": "explore", "room": exit_name})
    return items

if __name__ == "__main__":
    text = sys.stdin.read()
    events = parse_mud_output(text)
    items = events_to_work_items(events)
    print(json.dumps({"events": events, "work_items": items}, indent=2))
