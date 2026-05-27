"""Recipe — Declarative build specification with steps and dependencies."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Step:
    """A single build step within a recipe.

    Args:
        name: Human-readable step name.
        action: Callable that performs the step. Should return True on success.
        depends_on: Names of steps that must complete before this one runs.
        timeout: Optional timeout in seconds.
        retries: Number of retry attempts on failure.
    """

    name: str
    action: Callable[[], bool]
    depends_on: list[str] = field(default_factory=list)
    timeout: float | None = None
    retries: int = 0

    status: StepStatus = field(default=StepStatus.PENDING, repr=False)
    attempts: int = field(default=0, repr=False)
    error: str | None = field(default=None, repr=False)

    def fingerprint(self) -> str:
        """Deterministic hash based on name and dependency names."""
        payload = f"{self.name}|{','.join(sorted(self.depends_on))}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class Recipe:
    """A build recipe — an ordered, dependency-aware sequence of steps.

    Recipes are the unit of work submitted to a BuildQueue. They declare
    what needs to happen, the Forge decides when and where.

    Args:
        name: Recipe identifier (e.g. 'build-flux-compiler').
        tags: Arbitrary tags for filtering and routing.
        constraint_profile: Key-value constraints (e.g. gpu_mem='8G').
    """

    name: str
    steps: list[Step] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    constraint_profile: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: Step) -> "Recipe":
        """Add a step and return self for chaining."""
        self.steps.append(step)
        return self

    def step_by_name(self, name: str) -> Step | None:
        return next((s for s in self.steps if s.name == name), None)

    def topological_order(self) -> list[Step]:
        """Return steps in dependency-respecting topological order.

        Raises ValueError if the dependency graph contains a cycle.
        """
        name_to_step = {s.name: s for s in self.steps}
        visited: set[str] = set()
        order: list[Step] = []
        visiting: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise ValueError(f"Dependency cycle detected at step '{name}'")
            visiting.add(name)
            step = name_to_step.get(name)
            if step:
                for dep in step.depends_on:
                    if dep not in name_to_step:
                        raise ValueError(
                            f"Step '{name}' depends on unknown step '{dep}'"
                        )
                    visit(dep)
                visiting.discard(name)
                visited.add(name)
                order.append(step)

        for s in self.steps:
            visit(s.name)
        return order

    def ready_steps(self, completed: set[str]) -> list[Step]:
        """Steps whose dependencies are all in *completed* and that are still PENDING."""
        return [
            s
            for s in self.steps
            if s.status == StepStatus.PENDING
            and all(d in completed for d in s.depends_on)
        ]

    def fingerprint(self) -> str:
        """Content-addressable hash of the recipe."""
        parts = [self.name] + sorted(self.tags)
        for s in self.steps:
            parts.append(f"{s.name}:{s.fingerprint()}")
        for k, v in sorted(self.constraint_profile.items()):
            parts.append(f"{k}={v}")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
