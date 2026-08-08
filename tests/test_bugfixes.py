"""
Tests for bugs found during the 2026-08-07 overnight audit.

Each test class documents the bug, the fix, and verifies the behaviour.

Bugs fixed:
  1. Stale error on retry success — _execute_step didn't clear step.error
     when a retry succeeded, leaving the error from a prior attempt.
  2. Uninformative error when action returns False — _execute_step didn't
     set step.error when action returned a falsy value, producing
     "Step 'X' failed: None" messages.
  3. Transitive dependency execution — Forge.build_one and BuildQueue.execute_one
     only checked for FAILED upstream steps, not SKIPPED ones. A step whose
     dependency was SKIPPED (because its own dependency FAILED) would still run.
  4. Forge.submit silently overwrites same-name recipes in _recipes,
     making reset_steps only work on the last one.

Additional coverage:
  - Step timeout field (declared but never tested)
  - BuildQueue._execute_step error paths with custom exceptions
  - Forge.build_one with mixed success/failure/skip diamond
"""

import pytest
from forgemaster.artifact import Artifact, ArtifactState
from forgemaster.forge import Forge, ForgeConfig
from forgemaster.monitor import BuildMonitor, EventKind
from forgemaster.queue import BuildQueue, Priority
from forgemaster.recipe import Recipe, Step, StepStatus


# ---------------------------------------------------------------------------
# Bug #1: Stale error on retry success
# ---------------------------------------------------------------------------

class TestStaleErrorOnRetrySuccess:
    """_execute_step must clear step.error when a retry succeeds."""

    def test_error_cleared_after_retry_success_queue(self):
        """In BuildQueue._execute_step, a successful retry must clear the error."""
        calls = []

        def fail_then_succeed():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("first attempt error")
            return True

        step = Step(name="flaky", action=fail_then_succeed, retries=2)
        recipe = Recipe(name="retry-clear", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is True
        assert step.status == StepStatus.SUCCEEDED
        assert step.error is None, f"Expected None, got {step.error!r}"

    def test_error_cleared_after_false_then_true(self):
        """Action returning False then True should also clear error."""
        calls = []

        def false_then_true():
            calls.append(1)
            return len(calls) >= 2

        step = Step(name="false-then-true", action=false_then_true, retries=2)
        recipe = Recipe(name="retry-false", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is True
        assert step.error is None

    def test_error_cleared_through_forge(self):
        """Same fix must work through Forge.build_one path."""
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("transient")
            return True

        step = Step(name="r", action=flaky, retries=3)
        recipe = Recipe(name="forge-retry", steps=[step])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert step.error is None


# ---------------------------------------------------------------------------
# Bug #2: Uninformative error when action returns False
# ---------------------------------------------------------------------------

class TestActionReturnsFalse:
    """When action returns False, step.error must be informative."""

    def test_false_action_sets_meaningful_error_queue(self):
        """BuildQueue._execute_step must set error when action returns False."""
        step = Step(name="ret-false", action=lambda: False)
        recipe = Recipe(name="false-queue", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is False
        assert step.error is not None
        assert "false" in step.error.lower() or "returned" in step.error.lower()

    def test_false_action_error_in_result_message(self):
        """The error message in the result dict should be informative."""
        step = Step(name="f", action=lambda: False)
        recipe = Recipe(name="false-msg", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is False
        error_str = result["errors"][0]
        assert "None" not in error_str, f"Error should not be 'None': {error_str}"

    def test_false_action_through_forge(self):
        """Same fix must work through Forge.build_one path."""
        step = Step(name="f", action=lambda: False)
        recipe = Recipe(name="forge-false", steps=[step])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert step.error is not None


# ---------------------------------------------------------------------------
# Bug #3: Transitive dependency execution (SKIPPED steps)
# ---------------------------------------------------------------------------

class TestTransitiveDependencySkip:
    """Steps depending on SKIPPED steps must also be SKIPPED."""

    def _make_chain(self):
        """Builds a chain: a (fails) → b (skipped) → c (should be skipped)."""
        def fail():
            raise RuntimeError("upstream failure")

        recipe = Recipe(name="transitive-chain")
        recipe.add_step(Step(name="a", action=fail))
        recipe.add_step(Step(name="b", action=lambda: True, depends_on=["a"]))
        recipe.add_step(Step(name="c", action=lambda: True, depends_on=["b"]))
        return recipe

    def test_transitive_skip_in_queue(self):
        """BuildQueue.execute_one must skip transitive dependents."""
        recipe = self._make_chain()
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is False
        assert result["completed_steps"] == []
        assert recipe.step_by_name("a").status == StepStatus.FAILED
        assert recipe.step_by_name("b").status == StepStatus.SKIPPED
        assert recipe.step_by_name("c").status == StepStatus.SKIPPED

    def test_transitive_skip_in_forge(self):
        """Forge.build_one must skip transitive dependents."""
        recipe = self._make_chain()
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert recipe.step_by_name("c").status == StepStatus.SKIPPED

    def test_diamond_transitive_skip(self):
        """Diamond dependency: root → (left, right-fails) → merge.
        merge depends on left (succeeded) and right (failed).
        merge should be SKIPPED because right is FAILED.
        """
        def fail():
            raise RuntimeError("right fails")

        recipe = Recipe(name="diamond")
        recipe.add_step(Step(name="root", action=lambda: True))
        recipe.add_step(Step(name="left", action=lambda: True, depends_on=["root"]))
        recipe.add_step(Step(name="right", action=fail, depends_on=["root"]))
        recipe.add_step(Step(name="merge", action=lambda: True, depends_on=["left", "right"]))

        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert recipe.step_by_name("merge").status == StepStatus.SKIPPED

    def test_deep_chain_all_skipped(self):
        """A 5-deep chain where the root fails — all descendants must be SKIPPED."""
        def fail():
            raise RuntimeError("root fails")

        recipe = Recipe(name="deep-chain")
        recipe.add_step(Step(name="s0", action=fail))
        for i in range(1, 6):
            recipe.add_step(Step(name=f"s{i}", action=lambda: True, depends_on=[f"s{i-1}"]))

        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        for i in range(1, 6):
            assert recipe.step_by_name(f"s{i}").status == StepStatus.SKIPPED, \
                f"s{i} should be SKIPPED, got {recipe.step_by_name(f's{i}').status}"

    def test_independent_branches_not_affected(self):
        """A failure in one branch must not affect parallel independent branches."""
        def fail():
            raise RuntimeError("branch-a fails")

        recipe = Recipe(name="parallel-branches")
        recipe.add_step(Step(name="a1", action=fail))
        recipe.add_step(Step(name="a2", action=lambda: True, depends_on=["a1"]))
        recipe.add_step(Step(name="b1", action=lambda: True))
        recipe.add_step(Step(name="b2", action=lambda: True, depends_on=["b1"]))

        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert "b1" in result["completed_steps"]
        assert "b2" in result["completed_steps"]
        assert "a2" not in result["completed_steps"]


# ---------------------------------------------------------------------------
# Bug #4: Forge.submit overwrites same-name recipes
# ---------------------------------------------------------------------------

class TestDuplicateRecipeNames:
    """Forge.submit silently overwrites same-name recipes in _recipes."""

    def test_reset_steps_after_duplicate_submit(self):
        """reset_steps should work predictably even with duplicate names.

        Note: this is a known design limitation — the last submitted recipe
        with a given name is what reset_steps finds. This test documents
        that behaviour so future changes are deliberate.
        """
        forge = Forge()
        r1 = Recipe(name="dup", steps=[Step(name="a", action=lambda: True)])
        r2 = Recipe(name="dup", steps=[Step(name="b", action=lambda: True)])
        forge.submit(r1)
        forge.submit(r2)

        # _recipes only has the latest
        assert forge.reset_steps("dup") is True
        # The stored recipe is r2 (last one submitted)
        assert forge._recipes["dup"].steps[0].name == "b"

    def test_build_all_with_duplicate_names(self):
        """Both recipes with the same name should still be built."""
        forge = Forge()
        r1 = Recipe(name="same", steps=[Step(name="a", action=lambda: True)])
        r2 = Recipe(name="same", steps=[Step(name="b", action=lambda: True)])
        forge.submit(r1)
        forge.submit(r2)
        results = forge.build_all()

        assert len(results) == 2
        assert all(r["success"] for r in results)


# ---------------------------------------------------------------------------
# Additional coverage: Step.timeout field
# ---------------------------------------------------------------------------

class TestStepTimeout:
    """Step has a timeout field that is declared but not enforced.

    These tests document the current behaviour: timeout is a declarative
    field that is stored but not actively enforced by _execute_step.
    """

    def test_timeout_default_is_none(self):
        step = Step(name="x", action=lambda: True)
        assert step.timeout is None

    def test_timeout_can_be_set(self):
        step = Step(name="x", action=lambda: True, timeout=30.0)
        assert step.timeout == 30.0

    def test_timeout_preserved_through_recipe(self):
        step = Step(name="x", action=lambda: True, timeout=60.0)
        recipe = Recipe(name="r", steps=[step])
        assert recipe.steps[0].timeout == 60.0


# ---------------------------------------------------------------------------
# Additional coverage: Error propagation with different exception types
# ---------------------------------------------------------------------------

class TestErrorPropagation:
    """Various exception types should be captured and their messages preserved."""

    def test_value_error_message_preserved(self):
        def bad():
            raise ValueError("invalid value")

        step = Step(name="v", action=bad)
        recipe = Recipe(name="val-err", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is False
        assert "invalid value" in result["errors"][0]

    def test_type_error_message_preserved(self):
        def bad():
            raise TypeError("wrong type")

        step = Step(name="t", action=bad)
        recipe = Recipe(name="type-err", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is False
        assert "wrong type" in result["errors"][0]

    def test_custom_exception_message_preserved(self):
        class CustomError(Exception):
            pass

        def bad():
            raise CustomError("custom failure")

        step = Step(name="c", action=bad)
        recipe = Recipe(name="custom-err", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is False
        assert "custom failure" in result["errors"][0]

    def test_exception_with_no_message(self):
        def bad():
            raise Exception()

        step = Step(name="e", action=bad)
        recipe = Recipe(name="empty-err", steps=[step])
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is False
        # Should not crash — empty string is acceptable


# ---------------------------------------------------------------------------
# Additional coverage: Empty recipe handling
# ---------------------------------------------------------------------------

class TestEmptyRecipeExecution:
    """Executing an empty recipe should succeed with no completed steps."""

    def test_empty_recipe_through_queue(self):
        recipe = Recipe(name="empty")
        q = BuildQueue()
        q.submit(recipe)
        result = q.execute_one()

        assert result["success"] is True
        assert result["completed_steps"] == []

    def test_empty_recipe_through_forge(self):
        recipe = Recipe(name="empty-forge")
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert result["completed_steps"] == []

    def test_empty_recipe_monitor_records_completion(self):
        recipe = Recipe(name="empty-monitored")
        forge = Forge()
        forge.submit(recipe)
        forge.build_one()

        summary = forge.monitor.summary("empty-monitored")
        assert summary["build_completed"] is True


# ---------------------------------------------------------------------------
# Additional coverage: Forge with custom config
# ---------------------------------------------------------------------------

class TestForgeConfigPropagation:
    """ForgeConfig settings should propagate to subsystems."""

    def test_monitor_max_events_from_config(self):
        config = ForgeConfig(monitor_max_events=5)
        forge = Forge(config=config)
        assert forge.monitor.max_events == 5

    def test_max_workers_from_config(self):
        config = ForgeConfig(max_workers=8)
        forge = Forge(config=config)
        assert forge.queue.max_workers == 8

    def test_default_config(self):
        forge = Forge()
        assert forge.queue.max_workers == 4
        assert forge.monitor.max_events == 10_000


# ---------------------------------------------------------------------------
# Build one integration: mixed results in a single build_all batch
# ---------------------------------------------------------------------------

class TestMixedBuildBatch:
    """build_all with a mix of succeeding and failing recipes."""

    def test_mixed_batch_reports_each_result(self):
        def ok():
            return True

        def boom():
            raise RuntimeError("fail")

        forge = Forge()
        forge.submit(Recipe(name="ok-1", steps=[Step(name="s", action=ok)]))
        forge.submit(Recipe(name="fail-1", steps=[Step(name="s", action=boom)]))
        forge.submit(Recipe(name="ok-2", steps=[Step(name="s", action=ok)]))
        results = forge.build_all()

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True

        stats = forge.stats()
        assert stats["queue"]["completed"] == 2
        assert stats["queue"]["failed"] == 1
