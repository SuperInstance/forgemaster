"""BuildQueue — Priority queue with parallel execution for build recipes."""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from .recipe import Recipe, Step, StepStatus


class Priority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(order=True)
class QueueEntry:
    priority: Priority
    submitted_at: float = field(compare=True)
    recipe: Recipe = field(compare=False)
    submitted_by: str = ""


class BuildQueue:
    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self._heap: list[QueueEntry] = []
        self._running: dict[str, QueueEntry] = {}
        self._completed: dict[str, QueueEntry] = {}
        self._failed: dict[str, QueueEntry] = {}

    def submit(
        self,
        recipe: Recipe,
        priority: Priority = Priority.NORMAL,
        submitted_by: str = "",
    ) -> str:
        entry = QueueEntry(
            priority=priority,
            submitted_at=time.time(),
            recipe=recipe,
            submitted_by=submitted_by,
        )
        heapq.heappush(self._heap, entry)
        return recipe.name

    def pop(self) -> QueueEntry | None:
        while self._heap:
            return heapq.heappop(self._heap)
        return None

    def peek(self) -> QueueEntry | None:
        return self._heap[0] if self._heap else None

    @property
    def pending_count(self) -> int:
        return len(self._heap)

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def failed_count(self) -> int:
        return len(self._failed)

    def _execute_step(self, step: Step) -> bool:
        attempts_left = 1 + step.retries
        while attempts_left > 0:
            step.attempts += 1
            try:
                result = step.action()
                if result:
                    step.status = StepStatus.SUCCEEDED
                    step.error = None  # clear stale error from earlier attempts
                    return True
                else:
                    step.error = step.error or f"Step '{step.name}' returned False"
            except Exception as exc:
                step.error = str(exc)
            attempts_left -= 1
        step.status = StepStatus.FAILED
        return False

    def execute_one(self) -> dict[str, Any]:
        entry = self.pop()
        if entry is None:
            return {"name": None, "success": False, "error": "queue empty"}

        recipe = entry.recipe
        self._running[recipe.name] = entry

        try:
            ordered = recipe.topological_order()
        except ValueError as exc:
            self._running.pop(recipe.name, None)
            self._failed[recipe.name] = entry
            return {"name": recipe.name, "success": False, "error": str(exc)}

        completed: set[str] = set()
        errors: list[str] = []

        for step in ordered:
            upstream_blocked = False
            for dep_name in step.depends_on:
                dep_step = recipe.step_by_name(dep_name)
                if dep_step is not None and dep_step.status in (StepStatus.FAILED, StepStatus.SKIPPED):
                    upstream_blocked = True
                    break
            if upstream_blocked:
                step.status = StepStatus.SKIPPED
                continue
            ok = self._execute_step(step)
            if ok:
                completed.add(step.name)
            else:
                errors.append(f"Step '{step.name}' failed: {step.error}")
                for other in recipe.steps:
                    if step.name in other.depends_on and other.status == StepStatus.PENDING:
                        other.status = StepStatus.SKIPPED

        success = len(errors) == 0
        self._running.pop(recipe.name, None)
        if success:
            self._completed[recipe.name] = entry
        else:
            self._failed[recipe.name] = entry

        return {
            "name": recipe.name,
            "success": success,
            "completed_steps": sorted(completed),
            "errors": errors,
        }

    def drain(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        while self._heap:
            results.append(self.execute_one())
        return results

    def cancel(self, recipe_name: str) -> bool:
        original = len(self._heap)
        self._heap = [e for e in self._heap if e.recipe.name != recipe_name]
        heapq.heapify(self._heap)
        return len(self._heap) < original

    def stats(self) -> dict[str, int]:
        return {
            "pending": self.pending_count,
            "running": self.running_count,
            "completed": self.completed_count,
            "failed": self.failed_count,
        }
