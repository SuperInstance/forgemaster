"""Coverage gap tests — targeting uncovered lines in forge.py and queue.py."""

import pytest
from forgemaster.artifact import Artifact, ArtifactState
from forgemaster.forge import Forge, ForgeConfig
from forgemaster.monitor import BuildMonitor, EventKind
from forgemaster.queue import BuildQueue, Priority
from forgemaster.recipe import Recipe, Step, StepStatus


class TestForgeBuildOneQueueEmpty:
    """forge.py:54 — build_one when pop returns None after pending check."""

    def test_build_one_queue_empty_after_pending_check(self):
        """If pending_count > 0 but pop somehow returns None, get queue empty error."""
        forge = Forge()
        # Manually put something in _heap length but corrupt it
        # Actually, let's test the direct path where queue is truly empty
        result = forge.build_one()
        assert result == {"name": None, "success": False, "error": "no pending recipes"}

    def test_build_one_pop_returns_none(self):
        """Force the defensive path where pending_count > 0 but pop returns None.

        This can happen if the heap is corrupted or items are consumed between
        the check and pop in a concurrent scenario.
        """
        forge = Forge()
        # Monkey-patch the queue to have inconsistent state
        # pending_count returns > 0 but pop returns None
        original_pop = forge.queue.pop
        forge.queue.pop = lambda: None
        # pending_count uses len(self._heap), so put something in it
        forge.queue._heap = ["fake_entry"]  # not a real QueueEntry

        result = forge.build_one()
        assert result["success"] is False
        assert result["error"] == "queue empty"
        assert result["name"] is None


class TestForgeCycleDetection:
    """forge.py:61-65 — ValueError from topological_order during build_one."""

    def test_build_one_with_cycle_records_build_failed(self):
        """A recipe with a dependency cycle should be caught and recorded in monitor."""
        forge = Forge()

        step_a = Step(name="a", action=lambda: True, depends_on=["b"])
        step_b = Step(name="b", action=lambda: True, depends_on=["a"])
        recipe = Recipe(name="cyclic", steps=[step_a, step_b])

        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert "cycle" in result["error"].lower()
        assert result["name"] == "cyclic"

        # Monitor should have recorded BUILD_FAILED
        events = forge.monitor.events_for("cyclic")
        failed_events = [e for e in events if e.kind == EventKind.BUILD_FAILED]
        assert len(failed_events) >= 1
        assert "cycle" in failed_events[0].detail.lower()

    def test_build_one_with_cycle_moves_to_failed(self):
        """Cyclic recipe should be moved to queue._failed."""
        forge = Forge()

        step_a = Step(name="x", action=lambda: True, depends_on=["y"])
        step_b = Step(name="y", action=lambda: True, depends_on=["x"])
        recipe = Recipe(name="cyclic2", steps=[step_a, step_b])

        forge.submit(recipe)
        forge.build_one()

        assert "cyclic2" in forge.queue._failed
        assert "cyclic2" not in forge.queue._running


class TestQueueCycleDetection:
    """queue.py:102-105 — ValueError from topological_order during execute_one."""

    def test_execute_one_with_cycle_returns_error(self):
        """execute_one should catch the cycle and return error dict."""
        queue = BuildQueue()

        step_a = Step(name="a", action=lambda: True, depends_on=["b"])
        step_b = Step(name="b", action=lambda: True, depends_on=["a"])
        recipe = Recipe(name="cyc", steps=[step_a, step_b])

        queue.submit(recipe)
        result = queue.execute_one()

        assert result["success"] is False
        assert "cycle" in result["error"].lower()
        assert result["name"] == "cyc"

    def test_execute_one_with_cycle_moves_to_failed(self):
        """Cyclic recipe should move to _failed, not stay in _running."""
        queue = BuildQueue()

        step_a = Step(name="a", action=lambda: True, depends_on=["b"])
        step_b = Step(name="b", action=lambda: True, depends_on=["a"])
        recipe = Recipe(name="cyc", steps=[step_a, step_b])

        queue.submit(recipe)
        queue.execute_one()

        assert "cyc" in queue._failed
        assert "cyc" not in queue._running

    def test_execute_one_with_missing_dependency(self):
        """Recipe with a step depending on nonexistent step should fail."""
        queue = BuildQueue()

        step = Step(name="lonely", action=lambda: True, depends_on=["ghost"])
        recipe = Recipe(name="missing", steps=[step])

        queue.submit(recipe)
        result = queue.execute_one()

        assert result["success"] is False
        assert "ghost" in result["error"] or "unknown" in result["error"].lower()


class TestForgeBuildOneStepErrorPropagation:
    """Test that step errors propagate correctly through build_one."""

    def test_build_one_step_failure_with_error_message(self):
        """Failed step should include error message in result."""
        forge = Forge()

        def boom():
            raise RuntimeError("explosion in reactor")

        step = Step(name="dangerous", action=boom)
        recipe = Recipe(name="risky", steps=[step])

        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert any("explosion" in e for e in result["errors"])
        assert result["completed_steps"] == []

    def test_build_one_success_records_completion_time(self):
        """Successful build should include build_time_ms."""
        forge = Forge()

        step = Step(name="quick", action=lambda: True)
        recipe = Recipe(name="fast", steps=[step])

        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert "build_time_ms" in result
        assert result["build_time_ms"] >= 0.0


class TestForgeRetryWithMonitor:
    """Test retry behavior integrates with monitor correctly."""

    def test_retry_step_records_multiple_attempts(self):
        """Steps with retries should eventually succeed and record attempt count."""
        forge = Forge()

        attempts = []

        def fail_then_succeed():
            attempts.append(1)
            return len(attempts) >= 3  # succeed on 3rd try

        step = Step(name="flaky", action=fail_then_succeed, retries=2)
        recipe = Recipe(name="retry-recipe", steps=[step])

        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert len(attempts) == 3

        # Monitor records step start/end once per step (not per retry)
        events = forge.monitor.events_for("retry-recipe")
        started = [e for e in events if e.kind == EventKind.STEP_STARTED]
        completed = [e for e in events if e.kind == EventKind.STEP_COMPLETED]

        assert len(started) == 1  # one STEP_STARTED
        assert len(completed) == 1  # one STEP_COMPLETED (final success)

        # Step itself should have recorded 3 attempts
        assert step.attempts == 3


class TestForgeArtifactsAdvanced:
    """Advanced artifact tracking scenarios."""

    def test_register_multiple_artifacts_for_recipe(self):
        """Multiple artifacts can be registered for the same recipe."""
        forge = Forge()

        a1 = Artifact(name="binary", path="/tmp/bin", recipe_name="build-x")
        a2 = Artifact(name="debug", path="/tmp/debug", recipe_name="build-x")
        a3 = Artifact(name="other", path="/tmp/other", recipe_name="build-y")

        forge.register_artifact(a1)
        forge.register_artifact(a2)
        forge.register_artifact(a3)

        result = forge.artifact_for_recipe("build-x")
        assert len(result) == 2
        names = {a.name for a in result}
        assert names == {"binary", "debug"}

    def test_register_artifact_records_monitor_event(self):
        """Registering an artifact should create an ARTIFACT_READY event."""
        forge = Forge()
        art = Artifact(name="output", path="/tmp/out", recipe_name="r")
        forge.register_artifact(art)

        events = forge.monitor.events_for("r")
        ready_events = [e for e in events if e.kind == EventKind.ARTIFACT_READY]
        assert len(ready_events) == 1
        assert ready_events[0].detail == "output"


class TestForgeResetStepsIntegration:
    """Reset steps through the Forge interface."""

    def test_reset_steps_then_rebuild(self):
        """Reset steps should allow rebuilding from clean state."""
        forge = Forge()

        call_count = [0]

        def count_action():
            call_count[0] += 1
            return True

        step = Step(name="s", action=count_action)
        recipe = Recipe(name="reset-test", steps=[step])

        forge.submit(recipe)
        forge.build_one()
        assert call_count[0] == 1

        # Reset and rebuild
        assert forge.reset_steps("reset-test") is True
        forge.submit(recipe)
        result = forge.build_one()
        assert result["success"] is True
        assert call_count[0] == 2

    def test_reset_steps_does_not_exist(self):
        """Reset on unknown recipe should return False."""
        forge = Forge()
        assert forge.reset_steps("nonexistent") is False


class TestForgeStatsComplete:
    """Stats should include all subsystem stats."""

    def test_stats_structure(self):
        """Stats should include queue stats, artifact count, and monitor events."""
        forge = Forge()

        step = Step(name="s", action=lambda: True)
        recipe = Recipe(name="stat-test", steps=[step])
        forge.submit(recipe)
        forge.build_one()

        art = Artifact(name="a", path="/tmp/a", recipe_name="stat-test")
        forge.register_artifact(art)

        s = forge.stats()
        assert "queue" in s
        assert "artifacts" in s
        assert "monitor_events" in s
        assert s["artifacts"] == 1
        assert s["monitor_events"] > 0
        assert s["queue"]["completed"] == 1


class TestMonitorEdgeCases:
    """Additional monitor edge cases."""

    def test_record_step_end_with_custom_detail(self):
        """Step end should store the detail/error message."""
        mon = BuildMonitor()
        mon.record_step_start("r", "s")
        mon.record_step_end("r", "s", success=False, detail="timeout exceeded")

        events = mon.events_for("r")
        failed = [e for e in events if e.kind == EventKind.STEP_FAILED]
        assert len(failed) == 1
        assert failed[0].detail == "timeout exceeded"

    def test_record_with_extra_metadata(self):
        """Record should pass through arbitrary metadata."""
        mon = BuildMonitor()
        evt = mon.record(EventKind.SUBMITTED, "r", detail="test", custom_field=42, another="val")

        assert evt.metadata["custom_field"] == 42
        assert evt.metadata["another"] == "val"

    def test_events_for_returns_copy(self):
        """events_for should return a copy, not the internal list."""
        mon = BuildMonitor()
        mon.record(EventKind.SUBMITTED, "r")
        events = mon.events_for("r")
        events.clear()
        # Original should be untouched
        assert len(mon.events_for("r")) == 1


class TestQueuePopEmptyAfterCancel:
    """Pop behavior after cancel leaves empty queue."""

    def test_cancel_all_then_pop(self):
        """After canceling all entries, pop returns None."""
        queue = BuildQueue()
        recipe = Recipe(name="doomed", steps=[Step(name="s", action=lambda: True)])
        queue.submit(recipe)
        queue.cancel("doomed")
        assert queue.pop() is None
        assert queue.pending_count == 0

    def test_cancel_preserves_other_entries(self):
        """Canceling one entry preserves others in correct priority order."""
        queue = BuildQueue()
        r1 = Recipe(name="low", steps=[Step(name="s", action=lambda: True)])
        r2 = Recipe(name="high", steps=[Step(name="s", action=lambda: True)])
        queue.submit(r1, priority=Priority.LOW)
        queue.submit(r2, priority=Priority.HIGH)

        canceled = queue.cancel("low")
        assert canceled is True
        assert queue.pop().recipe.name == "high"


class TestRecipeUnknownDependencyInQueue:
    """Unknown dependency through queue.execute_one path."""

    def test_unknown_dependency_in_execute_one(self):
        """execute_one should handle unknown dependency error from topological_order."""
        queue = BuildQueue()
        step = Step(name="a", action=lambda: True, depends_on=["nonexistent"])
        recipe = Recipe(name="bad-deps", steps=[step])
        queue.submit(recipe)
        result = queue.execute_one()

        assert result["success"] is False
        assert "nonexistent" in result["error"] or "unknown" in result["error"].lower()
