#!/usr/bin/env python3
"""
Game Engine Puppeteering Demo — NPCs as Musicians

Each NPC is a RoomMusician with their own T-0 clock and personality tempo.
They don't use behavior trees — they LISTEN and SNAP to each other.

Demo: A tavern scene with 4 NPCs in conversation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.flux import FluxVector, FluxChannel
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.snap import eisenstein_snap
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.sidechannel.nod import Nod
from flux_tensor_midi.sidechannel.smile import Smile
from flux_tensor_midi.sidechannel.frown import Frown
from flux_tensor_midi.ensemble.band import Band
from flux_tensor_midi.ensemble.score import Score
from flux_tensor_midi.harmony.jaccard import jaccard_similarity
import math

# ── NPC Definitions ──────────────────────────────────────────────────────────

class NPC:
    """A game character that IS a musician."""
    
    def __init__(self, name, role, tempo_bpm, personality):
        self.name = name
        self.role = role
        self.personality = personality
        self.room = RoomMusician(
            room_id=name,
            instrument=role,
            tempo_bpm=tempo_bpm,
        )
        self.dialogue = []
        self.energy = 0.5
        self.mood = "neutral"
        
    def speak(self, text, beat, velocity=80, duration=2):
        """NPC speaks = plays a note."""
        event = MidiEvent(
            event_type="note_on",
            channel=self.room.midi_channel,
            timestamp=beat,
            pitch={"bard": 60, "guard": 48, "innkeeper": 55, "thief": 72}[self.role],
            velocity=velocity,
            duration=duration,
        )
        self.dialogue.append({
            "beat": beat,
            "text": text,
            "velocity": velocity,
            "mood": self.mood,
        })
        self.room.midi_events.append(event)
        return event
    
    def react(self, trigger_beat, trigger_velocity, reaction_delay=0.5):
        """React to another NPC — snap to their beat, not a frame counter."""
        # Snap reaction to the NPC's own tempo grid
        own_interval = 60.0 / self.room.tempo_bpm
        snapped_beat = round(trigger_beat / own_interval) * own_interval + reaction_delay
        
        # The snap delta IS the reaction time
        reaction_time = snapped_beat - trigger_beat
        
        # Personality affects velocity response
        if self.personality == "nervous":
            velocity = min(127, trigger_velocity + 20)  # overreacts
        elif self.personality == "stoic":
            velocity = max(30, trigger_velocity - 20)   # underreacts
        elif self.personality == "friendly":
            velocity = trigger_velocity                  # matches energy
        else:
            velocity = int(trigger_velocity * 0.8)
        
        return snapped_beat, velocity, reaction_time


def simulate_tavern_scene():
    """Run a tavern conversation as a musical performance."""
    
    print("=" * 70)
    print("  🍺 THE HARMONIOUS TAVERN — NPCs as Musicians")
    print("=" * 70)
    print()
    
    # ── Create NPCs ──
    bard = NPC("Lyria", "bard", tempo_bpm=80, personality="friendly")
    guard = NPC("Bron", "guard", tempo_bpm=40, personality="stoic")
    innkeeper = NPC("Marta", "innkeeper", tempo_bpm=60, personality="friendly")
    thief = NPC("Shade", "thief", tempo_bpm=120, personality="nervous")
    
    npcs = [bard, guard, innkeeper, thief]
    
    print("NPCs (musicians in the band):")
    for npc in npcs:
        print(f"  {npc.name:12} ({npc.role:10}) ♩={npc.room.tempo_bpm:3} BPM  personality={npc.personality}")
    print()
    
    # ── Create the band ──
    band = Band("tavern_scene")
    for npc in npcs:
        band.add_musician(npc.room)
        # Each NPC listens to all others
        for other in npcs:
            if other.name != npc.name:
                npc.room.listening_to.append(other.name)
    
    # ── Scene as MIDI Score ──
    score = Score(
        name="tavern_conversation",
        tempo_bpm=60,  # Scene tempo (1 beat = 1 second)
        lattice_divisions=24,  # Fine grid for dialogue timing
    )
    
    print("─" * 70)
    print("  SCENE: The tavern is quiet. Lyria (bard) begins a song.")
    print("─" * 70)
    print()
    
    # Beat 0: Bard opens with a line
    bard.mood = "melancholy"
    bard.speak("🎵 *plays a slow melody on the lute*", beat=0, velocity=60, duration=4)
    score.add_event(bard.room.midi_events[-1])
    print(f"  Beat 0.0 │ Lyria  (vel=60) │ 🎵 *plays a slow melody on the lute*")
    
    # Beat 2: Innkeeper reacts (snaps to her own tempo)
    react_beat, react_vel, reaction_time = innkeeper.react(0, 60, reaction_delay=2.0)
    innkeeper.mood = "warm"
    innkeeper.speak("That's a sad one, dear. Something on your mind?", beat=react_beat, velocity=react_vel, duration=3)
    score.add_event(innkeeper.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Marta  (vel={react_vel}) │ That's a sad one, dear. Something on your mind? [reaction: {reaction_time:.1f}s]")
    
    # Beat 4: Bard responds
    bard.mood = "wistful"
    react_beat, react_vel, _ = bard.react(react_beat, react_vel, reaction_delay=1.0)
    bard.speak("Just thinking about the road north. Strange reports...", beat=react_beat, velocity=react_vel, duration=3)
    score.add_event(bard.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Lyria  (vel={react_vel}) │ Just thinking about the road north. Strange reports...")
    
    # Beat 5: Guard snaps to attention (his tempo is slow — he thinks, THEN speaks)
    guard.mood = "alert"
    react_beat, react_vel, reaction_time = guard.react(react_beat, react_vel, reaction_delay=2.0)
    guard.speak("What kind of reports?", beat=react_beat, velocity=react_vel, duration=2)
    score.add_event(guard.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Bron   (vel={react_vel}) │ What kind of reports? [reaction: {reaction_time:.1f}s, stoic delay]")
    
    # Side-channel: Guard nods to Bard (I'm listening, go on)
    guard_nod = Nod(from_room="Bron", to_room="Lyria", timestamp=react_beat + 0.5, context="interested")
    print(f"  Beat {react_beat + 0.5:.1f} │ Bron   → Lyria │ *nods* (I'm listening, continue)")
    
    # Beat 7.5: Thief overhears, nervous, fast reaction
    thief.mood = "nervous"
    react_beat, react_vel, reaction_time = thief.react(react_beat, react_vel, reaction_delay=0.3)
    thief.speak("I... heard things too. In the market. People disappearing.", beat=react_beat, velocity=react_vel, duration=2)
    score.add_event(thief.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Shade  (vel={react_vel}) │ I... heard things too. In the market. People disappearing. [reaction: {reaction_time:.1f}s, nervous]")
    
    # Side-channel: Innkeeper frowns (this is getting dark)
    innkeeper_frown = Frown(from_room="Marta", to_room="Shade", timestamp=react_beat + 0.2, delta=0.3)
    print(f"  Beat {react_beat + 0.2:.1f} │ Marta  → Shade │ *frowns* (this is getting dark)")
    
    # Beat 10: Guard's slow response (his tempo=40, he's processing)
    guard.mood = "grave"
    react_beat, react_vel, reaction_time = guard.react(react_beat, react_vel, reaction_delay=2.5)
    guard.speak("Disappearing. How many?", beat=react_beat, velocity=min(127, react_vel + 30), duration=2)
    score.add_event(guard.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Bron   (vel={react_vel}) │ Disappearing. How many? [reaction: {reaction_time:.1f}s, grave]")
    
    # Beat 11: Thief overreacts (nervous personality)
    thief.mood = "panicked"
    react_beat, react_vel, reaction_time = thief.react(react_beat, react_vel, reaction_delay=0.2)
    thief.speak("THREE! Three this week alone! And the guards don't—", beat=react_beat, velocity=min(127, react_vel + 20), duration=1.5)
    score.add_event(thief.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Shade  (vel={react_vel}) │ THREE! Three this week alone! And the guards don't— [reaction: {reaction_time:.1f}s, panicked]")
    
    # Side-channel: Guard frowns at "the guards don't"
    guard_frown = Frown(from_room="Bron", to_room="Shade", timestamp=react_beat + 0.3, delta=0.5)
    print(f"  Beat {react_beat + 0.3:.1f} │ Bron   → Shade │ *frowns* (watch your tone)")
    
    # Beat 13: Innkeeper diffuses (friendly personality, matches energy)
    innkeeper.mood = "calm"
    react_beat, react_vel, reaction_time = innkeeper.react(react_beat, react_vel, reaction_delay=1.0)
    innkeeper.speak("Now now, let's not panic. More ale?", beat=react_beat, velocity=60, duration=2)
    score.add_event(innkeeper.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Marta  (vel={react_vel}) │ Now now, let's not panic. More ale?")
    
    # Side-channel: Innkeeper smiles at everyone (de-escalation)
    innkeeper_smile = Smile(from_room="Marta", to_room="everyone", timestamp=react_beat + 0.5)
    print(f"  Beat {react_beat + 0.5:.1f} │ Marta  → all   │ *smiles* (de-escalation)")
    
    # Beat 15: Bard closes the scene (callback to opening)
    bard.mood = "resolute"
    react_beat, react_vel, _ = bard.react(react_beat, react_vel, reaction_delay=1.5)
    bard.speak("🎵 *shifts to a minor key — the melody resolves*", beat=react_beat, velocity=50, duration=3)
    score.add_event(bard.room.midi_events[-1])
    print(f"  Beat {react_beat:.1f} │ Lyria  (vel={react_vel}) │ 🎵 *shifts to a minor key — the melody resolves*")
    
    # ── Analysis ──
    print()
    print("=" * 70)
    print("  TEMPORAL ANALYSIS")
    print("=" * 70)
    print()
    
    # Reaction time by personality
    print("Reaction Time by Personality:")
    for npc in npcs:
        intervals = []
        for i in range(1, len(npc.dialogue)):
            intervals.append(npc.dialogue[i]["beat"] - npc.dialogue[i-1]["beat"])
        if intervals:
            mean_interval = sum(intervals) / len(intervals)
            print(f"  {npc.name:12} ({npc.personality:8}): mean interval = {mean_interval:.1f} beats, tempo = {npc.room.tempo_bpm} BPM")
        else:
            print(f"  {npc.name:12} ({npc.personality:8}): only spoke once")
    
    print()
    
    # Dialogue density (notes per minute)
    print("Dialogue Density (speaking rate):")
    total_beats = max(d["beat"] for npc in npcs for d in npc.dialogue)
    for npc in npcs:
        rate = len(npc.dialogue) / (total_beats / 60) * 60  # lines per minute of scene
        print(f"  {npc.name:12}: {len(npc.dialogue)} lines, {rate:.1f} lines/minute")
    
    print()
    
    # Velocity profile (emotional arc)
    print("Emotional Arc (velocity over time):")
    all_events = []
    for npc in npcs:
        for d in npc.dialogue:
            all_events.append({"beat": d["beat"], "velocity": d["velocity"], "who": npc.name, "mood": d["mood"]})
    all_events.sort(key=lambda e: e["beat"])
    
    for e in all_events:
        bar = "█" * (e["velocity"] // 5)
        print(f"  Beat {e['beat']:5.1f} │ {e['who']:8} vel={e['velocity']:3} {bar} ({e['mood']})")
    
    print()
    
    # Harmony analysis
    print("Pairwise Harmony (Jaccard overlap of speaking beats):")
    for i, a in enumerate(npcs):
        for b in npcs[i+1:]:
            beats_a = set(round(d["beat"]) for d in a.dialogue)
            beats_b = set(round(d["beat"]) for d in b.dialogue)
            harmony = jaccard_similarity(beats_a, beats_b)
            bar = "█" * int(harmony * 30)
            print(f"  {a.name:8} ↔ {b.name:8}: Jaccard = {harmony:.3f} {bar}")
    
    print()
    print("─" * 70)
    print("  Key: NPCs don't use behavior trees. They have T-0 clocks")
    print("  and snap to each other's rhythm. The bard improvises, the")
    print("  guard thinks before speaking, the thief overreacts fast.")
    print("  No central controller. No shared clock. Just listening.")
    print("─" * 70)
    
    # Save score
    score_path = os.path.join(os.path.dirname(__file__), "tavern_scene.vms")
    score.save(score_path)
    print(f"\n✓ Score saved to {score_path}")
    
    return score


if __name__ == "__main__":
    simulate_tavern_scene()
