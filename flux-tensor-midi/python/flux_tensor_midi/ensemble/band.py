"""
Band: An ensemble of RoomMusicians with a conductor.

Coordinates multiple PLATO rooms as a musical band.
Manages clock synchronization, side-channel routing,
and collective state.
"""

from __future__ import annotations
from typing import Sequence
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.harmony.chord import HarmonyState


class Band:
    """An ensemble of RoomMusicians.

    Parameters
    ----------
    name : str
        Band name.
    conductor : RoomMusician | None
        Optional conductor (provides the master clock).
    bpm : float, default=120.0
        Tempo for the band.
    """

    def __init__(
        self,
        name: str,
        conductor: RoomMusician | None = None,
        bpm: float = 120.0,
    ):
        self._name = name
        self._conductor = conductor
        self._bpm = bpm
        self._members: dict[str, RoomMusician] = {}

        # Add conductor as first member if provided
        if conductor is not None:
            self._members[conductor.room_id] = conductor

        # Auto-listening map
        self._listen_matrix: dict[str, set[str]] = {}

    # ---- properties ----

    @property
    def name(self) -> str:
        return self._name

    @property
    def conductor(self) -> RoomMusician | None:
        return self._conductor

    @property
    def bpm(self) -> float:
        return self._bpm

    @property
    def members(self) -> dict[str, RoomMusician]:
        return dict(self._members)

    @property
    def member_count(self) -> int:
        return len(self._members)

    # ---- membership ----

    def add_musician(self, musician: RoomMusician) -> None:
        """Add a musician to the band.

        If a conductor exists, auto-listen and sync clock.
        """
        self._members[musician.room_id] = musician
        if self._conductor is not None:
            musician.join_ensemble(self._conductor)
            musician.clock.set_bpm(self._bpm)

    def remove_musician(self, musician: RoomMusician) -> None:
        """Remove a musician from the band."""
        self._members.pop(musician.room_id, None)
        musician.leave_ensemble()

    def get_musician(self, name: str) -> RoomMusician | None:
        """Find a musician by name."""
        for m in self._members.values():
            if m.name == name:
                return m
        return None

    # ---- listening matrix ----

    def everyone_listens_to_conductor(self) -> None:
        """All members listen to the conductor."""
        if self._conductor is None:
            return
        for m in self._members.values():
            if m.room_id != self._conductor.room_id:
                m.listen_to(self._conductor)

    def everyone_listens_to_everyone(self) -> None:
        """All members listen to each other."""
        members = list(self._members.values())
        for m in members:
            for n in members:
                if m.room_id != n.room_id:
                    m.listen_to(n)

    def set_listen(self, from_musician: RoomMusician, to_musician: RoomMusician) -> None:
        """Set a specific listening connection."""
        if from_musician.room_id in self._members and to_musician.room_id in self._members:
            from_musician.listen_to(to_musician)

    # ---- performance ----

    def tick_all(self) -> dict[str, tuple[float, FluxVector]]:
        """Advance all musicians by one tick.

        Returns dict mapping musician name to (timestamp, vector).
        """
        results: dict[str, tuple[float, FluxVector]] = {}
        for m in self._members.values():
            ts, vec = m.emit()
            results[m.name] = (ts, vec)
        return results

    def get_all_events(self) -> list[tuple[str, float, FluxVector]]:
        """Get the latest event from each musician."""
        return [(m.name, m.event_history[-1][0], m.event_history[-1][1]) for m in self._members.values() if m.event_history]

    def set_bpm(self, bpm: float) -> None:
        """Set BPM for all band members."""
        self._bpm = bpm
        for m in self._members.values():
            m.clock.set_bpm(bpm)

    # ---- harmony ----

    def harmony(self) -> HarmonyState:
        """Current harmonic state of the band."""
        latest = [m.state for m in self._members.values()]
        return HarmonyState(latest)

    def mean_coherence(self) -> float:
        """Mean pairwise coherence among band members."""
        members_list = list(self._members.values())
        if len(members_list) < 2:
            return 1.0

        total = 0.0
        pairs = 0
        for i in range(len(members_list)):
            for j in range(i + 1, len(members_list)):
                total += members_list[i].coherence_with(members_list[j])
                pairs += 1

        return total / pairs

    def get_roles(self) -> dict[str, RhythmicRole]:
        """Get the role of each member."""
        return {m.name: m.role for m in self._members.values()}

    def __repr__(self) -> str:
        return (
            f"Band(name={self._name!r}, "
            f"members={len(self._members)}, "
            f"bpm={self._bpm}, "
            f"conductor={self._conductor.name if self._conductor else 'None'})"
        )
