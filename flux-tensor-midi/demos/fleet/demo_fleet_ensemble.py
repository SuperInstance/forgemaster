#!/usr/bin/env python3
"""Fleet Ensemble Demo — PLATO rooms as a band."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.prerender import PreRenderBuffer
from flux_tensor_midi.ensemble.band import Band


def fv(salience):
    return FluxVector(values=[0.5]*9, salience=salience, tolerance=[0.3]*9)


def dominant(flux):
    """Get dominant channel index and value."""
    s = flux.salience
    idx = max(range(9), key=lambda i: s[i])
    return idx, s[idx]


def main():
    print("=" * 70)
    print("  🎵 FLEET ENSEMBLE — PLATO Rooms as a Band")
    print("=" * 70)
    
    band = Band(name="cocapn_fleet", bpm=72.0)
    
    rooms = [
        RoomMusician(name="sonar", clock=TZeroClock(bpm=40)),
        RoomMusician(name="engine", clock=TZeroClock(bpm=60)),
        RoomMusician(name="nav", clock=TZeroClock(bpm=80)),
        RoomMusician(name="helm", clock=TZeroClock(bpm=120)),
    ]
    for m in rooms:
        band.add_musician(m)
    
    print(f"\nBand: {band.name} at {band.bpm} BPM, {band.member_count} musicians")
    for name in band.members:
        print(f"  {name}")
    
    band.everyone_listens_to_everyone()
    print("\n✓ Everyone listening to everyone\n")
    
    # Set states
    rooms[0].state = fv([0.9, 0.2, 0.8, 0.1, 0.3, 0.0, 0.0, 0.0, 0.5])
    rooms[1].state = fv([0.1, 0.3, 0.0, 0.9, 0.8, 0.5, 0.0, 0.0, 0.4])
    rooms[2].state = fv([0.5, 0.3, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.7])
    rooms[3].state = fv([0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.9])
    print("✓ FLUX states set\n")
    
    # Pre-render buffers
    sonar_buf = PreRenderBuffer("sonar", depth=6)
    print("✓ Pre-render buffers\n")
    
    # ── Scenario ──
    print("─" * 70)
    print("  SCENARIO: Submarine approaches contact area")
    print("─" * 70)
    
    print("\n[Tick 1] Sonar emits: CONTACT BEARING 045")
    rooms[0].emit(fv([0.9, 0.2, 1.0, 0.1, 0.3, 0.0, 0.0, 0.0, 0.8]))
    rooms[0].send_nod(rooms[1], intensity=0.8)
    print("  Sonar → Engine: *nods* (contact detected)")
    
    print("\n[Tick 2] Engine emits: PRESSURE NOMINAL")
    rooms[1].emit(fv([0.1, 0.3, 0.0, 0.9, 0.7, 0.5, 0.0, 0.0, 0.6]))
    rooms[1].send_smile(rooms[0], intensity=0.7)
    print("  Engine → Sonar: *smiles* (ready)")
    
    print("\n[Tick 3] Nav emits: COURSE 090")
    rooms[2].emit(fv([0.5, 0.3, 0.5, 0.0, 1.0, 0.0, 0.0, 0.0, 0.7]))
    rooms[2].send_nod(rooms[3], intensity=0.9)
    print("  Nav → Helm: *nods* (execute course 090)")
    
    print("\n[Tick 4] Band tick all:")
    events = band.tick_all()
    for name, (ts, flux) in events.items():
        ch, val = dominant(flux)
        print(f"  {name:8}: dominant=ch{ch} ({val:.2f})")
    
    print("\n[Listen] Cross-room awareness:")
    for m in rooms:
        heard = m.listen
        if callable(heard):
            heard = heard()
        if heard:
            for src, ts, flux in heard:
                ch, val = dominant(flux)
                print(f"  {m.name:8} ← {src:8}: ch{ch}={val:.2f}")
        else:
            print(f"  {m.name:8}: (no events heard)")
    
    sonar_buf.advance(4)
    print(f"\n{sonar_buf.visualize(4)}")
    
    print("─" * 70)
    print("  No central controller. No shared clock. The band plays.")
    print("─" * 70)


if __name__ == "__main__":
    main()
