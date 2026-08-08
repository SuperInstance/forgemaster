"""Forge — Top-level orchestrator binding recipes, queue, artifacts, and monitoring."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .artifact import Artifact, ArtifactState
from .monitor import BuildMonitor, EventKind
from .queue import BuildQueue, Priority
from .recipe import Recipe, Step, StepStatus


@dataclass
class ForgeConfig:
    max_workers: int = 4
    artifact_ttl_seconds: float = 86400 * 7
    retry_default: int = 0
    monitor_max_events: int = 10_000


class Forge:
    """The Forgemaster orchestrator.

    Coordinates recipe submission, queue scheduling, step execution,
    artifact tracking, and build monitoring.
    """

    def __init__(self, config: ForgeConfig | None = None) -> None:
        self.config = config or ForgeConfig()
        self.queue = BuildQueue(max_workers=self.config.max_workers)
        self.monitor = BuildMonitor(max_events=self.config.monitor_max_events)
        self._artifacts: dict[str, Artifact] = {}
        self._recipes: dict[str, Recipe] = {}

    def submit(
        self,
        recipe: Recipe,
        priority: Priority = Priority.NORMAL,
        submitted_by: str = "",
    ) -> str:
        self._recipes[recipe.name] = recipe
        ticket = self.queue.submit(recipe, priority, submitted_by)
        self.monitor.record(EventKind.SUBMITTED, recipe.name, detail=submitted_by or "anonymous")
        return ticket

    def build_one(self) -> dict[str, Any]:
        if self.queue.pending_count == 0:
            return {"name": None, "success": False, "error": "no pending recipes"}

        entry = self.queue.pop()
        if entry is None:
            return {"name": None, "success": False, "error": "queue empty"}

        recipe = entry.recipe
        self.queue._running[recipe.name] = entry

        try:
            ordered = recipe.topological_order()
        except ValueError as exc:
            self.queue._running.pop(recipe.name, None)
            self.queue._failed[recipe.name] = entry
            self.monitor.record(EventKind.BUILD_FAILED, recipe.name, detail=str(exc))
            return {"name": recipe.name, "success": False, "error": str(exc)}

        completed: set[str] = set()
        errors: list[str] = []
        build_start = time.time()

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

            self.monitor.record_step_start(recipe.name, step.name)
            ok = self.queue._execute_step(step)
            self.monitor.record_step_end(recipe.name, step.name, ok, step.error)

            if ok:
                completed.add(step.name)
            else:
                errors.append(f"Step '{step.name}' failed: {step.error}")

        build_time_ms = (time.time() - build_start) * 1000
        success = len(errors) == 0

        self.queue._running.pop(recipe.name, None)
        if success:
            self.queue._completed[recipe.name] = entry
            self.monitor.record(EventKind.BUILD_COMPLETED, recipe.name)
        else:
            self.queue._failed[recipe.name] = entry
            self.monitor.record(EventKind.BUILD_FAILED, recipe.name, detail="; ".join(errors))

        return {
            "name": recipe.name,
            "success": success,
            "completed_steps": sorted(completed),
            "errors": errors,
            "build_time_ms": round(build_time_ms, 2),
        }

    def build_all(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        while self.queue.pending_count > 0:
            results.append(self.build_one())
        return results

    def register_artifact(self, artifact: Artifact) -> None:
        self._artifacts[artifact.name] = artifact
        self.monitor.record(EventKind.ARTIFACT_READY, artifact.recipe_name, detail=artifact.name)

    def get_artifact(self, name: str) -> Artifact | None:
        return self._artifacts.get(name)

    def artifact_for_recipe(self, recipe_name: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if a.recipe_name == recipe_name]

    def cancel(self, recipe_name: str) -> bool:
        return self.queue.cancel(recipe_name)

    def stats(self) -> dict[str, Any]:
        return {
            "queue": self.queue.stats(),
            "artifacts": len(self._artifacts),
            "monitor_events": self.monitor.total_events,
        }

    def reset_steps(self, recipe_name: str) -> bool:
        recipe = self._recipes.get(recipe_name)
        if recipe is None:
            return False
        for step in recipe.steps:
            step.status = StepStatus.PENDING
            step.error = None
            step.attempts = 0
        return True
