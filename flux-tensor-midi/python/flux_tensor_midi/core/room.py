"""
RoomMusician: PLATO rooms as musicians.

Each RoomMusician has a TZeroClock, produces FluxVector events,
listens to other rooms, and coordinates via side-channels and
Eisenstein rhythm snapping.
"""

from __future__ import annotations
import uuid
from typing import Callable
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.snap import EisensteinSnap, EisensteinRatio, RhythmicRole
from flux_tensor_midi.sidechannel.nod import Nod
from flux_tensor_midi.sidechannel.smile import Smile
from flux_tensor_midi.sidechannel.frown import Frown


class RoomMusician:
    """A PLATO room represented as a musician in the ensemble.

    Parameters
    ----------
    name : str
        Room/musician name.
    role : RhythmicRole, default=RhythmicRole.ROOT
        Rhythmic role for Eisenstein snapping.
    clock : TZeroClock | None
        Optional custom clock.  A default 120 BPM clock is created.
    """

    def __init__(
        self,
        name: str,
        role: RhythmicRole = RhythmicRole.ROOT,
        clock: TZeroClock | None = None,
    ):
        self._id = str(uuid.uuid4())[:8]
        self._name = name
        self._role = role
        self._clock = clock or TZeroClock(bpm=120.0)
        self._snap = EisensteinSnap()

        # Listeners (other rooms this room pays attention to)
        self._listeners: dict[str, "RoomMusician"] = {}

        # Event history for harmony computation
        self._event_history: list[tuple[float, FluxVector]] = []

        # Side-channel state
        self._nod: Nod = Nod()
        self._smile: Smile = Smile()
        self._frown: Frown = Frown()

        # Room state vector
        self._state: FluxVector = FluxVector.zero()

    # ---- properties ----

    @property
    def name(self) -> str:
        return self._name

    @property
    def room_id(self) -> str:
        return self._id

    @property
    def role(self) -> RhythmicRole:
        return self._role

    @role.setter
    def role(self, value: RhythmicRole) -> None:
        self._role = value

    @property
    def clock(self) -> TZeroClock:
        return self._clock

    @property
    def state(self) -> FluxVector:
        return self._state

    @state.setter
    def state(self, value: FluxVector) -> None:
        self._state = value

    @property
    def event_history(self) -> list[tuple[float, FluxVector]]:
        return list(self._event_history)

    @property
    def nod(self) -> Nod:
        return self._nod

    @property
    def smile(self) -> Smile:
        return self._smile

    @property
    def frown(self) -> Frown:
        return self._frown

    # ---- listeners ----

    def listen_to(self, other: RoomMusician) -> None:
        """Start listening to another room's events."""
        self._listeners[other.room_id] = other

    def stop_listening(self, other: RoomMusician) -> None:
        """Stop listening to another room."""
        self._listeners.pop(other.room_id, None)

    @property
    def listeners(self) -> dict[str, RoomMusician]:
        return dict(self._listeners)

    # ---- events ----

    def emit(self, vector: FluxVector | None = None) -> tuple[float, FluxVector]:
        """Produce a timestamped event.

        Advances the clock by one tick, applies Eisenstein snap,
        stores the event, and returns (timestamp_ms, vector).

        If no vector is given, uses the current room state.
        """
        raw_ts = self._clock.tick()
        snapped_ts = self._snap.snap(raw_ts, role=self._role)
        vec = self._state if vector is None else vector
        self._event_history.append((snapped_ts, vec))
        return snapped_ts, vec

    def listen(self) -> list[tuple[str, float, FluxVector]]:
        """Listen to all tracked rooms.  Returns [(name, ts, vector), ...]."""
        events = []
        for rid, musician in self._listeners.items():
            if musician.event_history:
                ts, vec = musician.event_history[-1]
                events.append((musician.name, ts, vec))
        return events

    # ---- side-channels ----

    def send_nod(self, target: RoomMusician, intensity: float = 0.5) -> None:
        """Send a nod to another musician (agreement/acknowledgment)."""
        self._nod.send(target)

    def send_smile(self, target: RoomMusician, intensity: float = 0.5) -> None:
        """Send a smile to another musician (positive affect)."""
        self._smile.send(target)

    def send_frown(self, target: RoomMusician, intensity: float = 0.5) -> None:
        """Send a frown to another musician (disagreement/concern)."""
        self._frown.send(target)

    def receive_sidechannels(self) -> dict[str, list[str]]:
        """Collect all side-channel messages addressed to this room."""
        messages: dict[str, list[str]] = {
            "nods": [],
            "smiles": [],
            "frowns": [],
        }
        for rid, musician in self._listeners.items():
            if self._id in musician.nod._sent_to:
                messages["nods"].append(musician.name)
            if self._id in musician.smile._sent_to:
                messages["smiles"].append(musician.name)
            if self._id in musician.frown._sent_to:
                messages["frowns"].append(musician.name)
        return messages

    # ---- state ----

    def update_state(self, vector: FluxVector) -> None:
        """Set the room's state vector."""
        self._state = vector

    def coherence_with(self, other: RoomMusician) -> float:
        """Cosine similarity between this room's state and another's."""
        return self._state.cosine_similarity(other._state)

    # ---- ensemble ----

    def join_ensemble(self, conductor: RoomMusician) -> None:
        """Listen to the conductor and sync clock drift."""
        self.listen_to(conductor)
        self._clock.synchronize_to(conductor._clock)

    def leave_ensemble(self) -> None:
        """Stop listening to all rooms."""
        self._listeners.clear()

    # ---- display ----

    def __repr__(self) -> str:
        return (
            f"RoomMusician(name={self._name!r}, id={self._id!r}, "
            f"role={self._role.name}, ticks={self._clock.ticks})"
        )
