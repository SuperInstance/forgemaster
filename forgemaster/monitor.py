"""BuildMonitor — Progress tracking and event history for builds."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventKind(Enum):
    SUBMITTED = "submitted"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    ARTIFACT_READY = "artifact_ready"


@dataclass
class BuildEvent:
    timestamp: float
    kind: EventKind
    recipe_name: str
    step_name: str | None = None
    detail: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BuildMonitor:
    def __init__(self, max_events: int = 10_000) -> None:
        self.max_events = max_events
        self._events: list[BuildEvent] = []
        self._by_recipe: dict[str, list[BuildEvent]] = defaultdict(list)
        self._durations: dict[str, dict[str, float]] = defaultdict(dict)

    def record(
        self,
        kind: EventKind,
        recipe_name: str,
        step_name: str | None = None,
        detail: str | None = None,
        **metadata: Any,
    ) -> BuildEvent:
        evt = BuildEvent(
            timestamp=time.time(),
            kind=kind,
            recipe_name=recipe_name,
            step_name=step_name,
            detail=detail,
            metadata=metadata,
        )
        self._append(evt)
        return evt

    def _append(self, evt: BuildEvent) -> None:
        self._events.append(evt)
        self._by_recipe[evt.recipe_name].append(evt)
        if len(self._events) > self.max_events:
            dropped = self._events.pop(0)
            self._by_recipe[dropped.recipe_name] = [
                e for e in self._by_recipe[dropped.recipe_name] if e is not dropped
            ]

    def events_for(self, recipe_name: str) -> list[BuildEvent]:
        return list(self._by_recipe.get(recipe_name, []))

    def recent(self, n: int = 20) -> list[BuildEvent]:
        return list(self._events[-n:])

    def record_step_start(self, recipe_name: str, step_name: str) -> None:
        self._durations[recipe_name][step_name] = time.time()
        self.record(EventKind.STEP_STARTED, recipe_name, step_name)

    def record_step_end(
        self, recipe_name: str, step_name: str, success: bool, detail: str | None = None
    ) -> float:
        start = self._durations.get(recipe_name, {}).get(step_name, time.time())
        duration = time.time() - start
        kind = EventKind.STEP_COMPLETED if success else EventKind.STEP_FAILED
        self.record(kind, recipe_name, step_name, detail, duration_s=round(duration, 3))
        return duration

    def summary(self, recipe_name: str) -> dict[str, Any]:
        evts = self._by_recipe.get(recipe_name, [])
        steps_ok = sum(1 for e in evts if e.kind == EventKind.STEP_COMPLETED)
        steps_fail = sum(1 for e in evts if e.kind == EventKind.STEP_FAILED)
        completed = any(e.kind == EventKind.BUILD_COMPLETED for e in evts)
        failed = any(e.kind == EventKind.BUILD_FAILED for e in evts)
        return {
            "recipe": recipe_name,
            "events": len(evts),
            "steps_completed": steps_ok,
            "steps_failed": steps_fail,
            "build_completed": completed,
            "build_failed": failed,
        }

    @property
    def total_events(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()
        self._by_recipe.clear()
        self._durations.clear()
