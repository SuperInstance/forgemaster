"""
Forgemaster Quick Example — Build a simple recipe.

This example creates a Recipe with dependency-aware steps, submits it
to the Forge, and monitors the build. It's the minimal "hello world"
for constraint-aware agentic compilation.

Run: python examples/quick_start.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build', 'lib'))

from forgemaster import (
    Artifact, ArtifactState,
    BuildMonitor,
    BuildQueue, Priority,
    Forge,
    Recipe, Step,
)


def build_a_boat():
    """A demo recipe: build a boat from parts, test it, deploy it."""

    # ── Define steps with dependencies ──────────────────────────

    cut_wood = Step(
        name="cut-wood",
        action=lambda: True,
    )

    forge_nails = Step(
        name="forge-nails",
        action=lambda: True,
    )

    assemble_hull = Step(
        name="assemble-hull",
        action=lambda: True,
        depends_on=["cut-wood", "forge-nails"],
    )

    waterproof = Step(
        name="waterproof-seams",
        action=lambda: True,
        depends_on=["assemble-hull"],
    )

    sea_trial = Step(
        name="sea-trial",
        action=lambda: True,
        depends_on=["waterproof-seams"],
    )

    # ── Create the recipe ───────────────────────────────────────

    recipe = Recipe(
        name="build-skiff-v1",
        steps=[cut_wood, forge_nails, assemble_hull, waterproof, sea_trial],
        tags=["boat", "era-1", "demo"],
        constraint_profile={"max_memory_mb": 128},
    )

    # ── Verify dependency ordering ──────────────────────────────

    order = recipe.topological_order()
    print("Build order:")
    for i, step in enumerate(order, 1):
        deps = ", ".join(step.depends_on) or "(none)"
        print(f"  {i}. {step.name} ← depends: {deps}")

    # ── Simulate execution ──────────────────────────────────────

    completed = set()
    print("\nExecuting:")
    for step in order:
        deps_ok = all(d in completed for d in step.depends_on)
        print(f"  → {step.name} (deps satisfied: {deps_ok})")
        step.status = StepStatus.SUCCEEDED
        completed.add(step.name)

    print(f"\n✅ Recipe '{recipe.name}' completed: {len(completed)} steps")
    print(f"   Fingerprint: {recipe.fingerprint()}")

    # ── Show ready_steps mechanic ───────────────────────────────

    # Reset and simulate partial completion
    fresh = Recipe(
        name="build-skiff-v2",
        steps=[
            Step(name="a", action=lambda: True),
            Step(name="b", action=lambda: True, depends_on=["a"]),
            Step(name="c", action=lambda: True, depends_on=["a"]),
            Step(name="d", action=lambda: True, depends_on=["b", "c"]),
        ],
    )

    print(f"\nPartial execution simulation for '{fresh.name}':")
    ready = fresh.ready_steps(set())
    print(f"  Initially ready: {[s.name for s in ready]}")

    ready = fresh.ready_steps({"a"})
    print(f"  After 'a' completes: {[s.name for s in ready]}")

    ready = fresh.ready_steps({"a", "b", "c"})
    print(f"  After 'a','b','c': {[s.name for s in ready]}")


if __name__ == "__main__":
    from forgemaster.recipe import StepStatus  # local import for demo
    build_a_boat()
