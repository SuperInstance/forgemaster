"""Additional forgemaster tests — edge cases and integration scenarios."""

import pytest
from forgemaster.artifact import Artifact, ArtifactState
from forgemaster.forge import Forge, ForgeConfig
from forgemaster.monitor import BuildMonitor, EventKind
from forgemaster.queue import BuildQueue, Priority
from forgemaster.recipe import Recipe, Step, StepStatus


def _ok_step(name, depends_on=None):
    return Step(name=name, action=lambda: True, depends_on=depends_on or [])


def _fail_step(name, depends_on=None):
    def _boom():
        raise RuntimeError("boom")
    return Step(name=name, action=_boom, depends_on=depends_on or [])


# ---------------------------------------------------------------------------
# Artifact edge cases
# ---------------------------------------------------------------------------

class TestArtifactEdgeCases:
    def test_age_seconds_positive(self):
        a = Artifact(name="x", path="/tmp/x", recipe_name="r")
        age = a.age_seconds(now=a.created_at + 10)
        assert age == pytest.approx(10.0, abs=0.01)

    def test_is_valid_building(self):
        a = Artifact(name="x", path="/tmp/x", recipe_name="r")
        a.state = ArtifactState.BUILDING
        assert a.is_valid() is True

    def test_is_valid_stale(self):
        a = Artifact(name="x", path="/tmp/x", recipe_name="r")
        a.state = ArtifactState.STALE
        assert a.is_valid() is False

    def test_to_dict_has_all_fields(self):
        a = Artifact(name="x", path="/tmp/x", recipe_name="r", tags=["a", "b"])
        d = a.to_dict()
        required = {"name", "path", "recipe_name", "tags", "state", "digest",
                    "size_bytes", "build_time_ms", "created_at", "metadata"}
        assert required.issubset(d.keys())

    def test_compute_digest_empty_bytes(self):
        a = Artifact(name="x", path="/tmp/x", recipe_name="r")
        digest = a.compute_digest(b"")
        assert len(digest) == 40
        assert a.size_bytes == 0
        assert a.state == ArtifactState.READY


# ---------------------------------------------------------------------------
# Queue edge cases
# ---------------------------------------------------------------------------

class TestQueueEdgeCases:
    def test_priority_background_is_lowest(self):
        q = BuildQueue()
        q.submit(Recipe(name="bg"), Priority.BACKGROUND)
        q.submit(Recipe(name="normal"), Priority.NORMAL)
        assert q.pop().recipe.name == "normal"
        assert q.pop().recipe.name == "bg"

    def test_priority_critical_beats_high(self):
        q = BuildQueue()
        q.submit(Recipe(name="high"), Priority.HIGH)
        q.submit(Recipe(name="critical"), Priority.CRITICAL)
        assert q.pop().recipe.name == "critical"

    def test_submit_with_submitted_by(self):
        q = BuildQueue()
        entry_recipe = Recipe(name="attributed")
        ticket = q.submit(entry_recipe, Priority.NORMAL, submitted_by="alice")
        assert ticket == "attributed"
        entry = q.pop()
        assert entry.submitted_by == "alice"

    def test_cancel_nonexistent(self):
        q = BuildQueue()
        assert q.cancel("ghost") is False

    def test_drain_empty(self):
        q = BuildQueue()
        results = q.drain()
        assert results == []

    def test_retries_exhausted(self):
        q = BuildQueue()
        r = Recipe(name="exhaust")
        flaky = _fail_step("boom")
        flaky.retries = 2
        r.add_step(flaky)
        q.submit(r)
        result = q.execute_one()
        assert result["success"] is False
        assert r.steps[0].attempts == 3  # 1 + 2 retries

    def test_failed_step_marks_downstream_skipped(self):
        q = BuildQueue()
        r = Recipe(name="skip-downstream")
        r.add_step(_ok_step("a"))
        r.add_step(_fail_step("b", depends_on=["a"]))
        r.add_step(_ok_step("c", depends_on=["b"]))
        q.submit(r)
        result = q.execute_one()
        assert result["success"] is False
        assert "a" in result["completed_steps"]
        assert "c" not in result["completed_steps"]

    def test_running_and_failed_counts(self):
        q = BuildQueue()
        r = Recipe(name="fail", steps=[_fail_step("x")])
        q.submit(r)
        q.execute_one()
        stats = q.stats()
        assert stats["failed"] == 1
        assert stats["completed"] == 0


# ---------------------------------------------------------------------------
# Recipe edge cases
# ---------------------------------------------------------------------------

class TestRecipeEdgeCases:
    def test_empty_recipe_topological_order(self):
        r = Recipe(name="empty")
        order = r.topological_order()
        assert order == []

    def test_step_fingerprint_differs_by_name(self):
        s1 = Step(name="alpha", action=lambda: True)
        s2 = Step(name="beta", action=lambda: True)
        assert s1.fingerprint() != s2.fingerprint()

    def test_step_fingerprint_same_for_same_deps(self):
        s1 = Step(name="x", action=lambda: True, depends_on=["a", "b"])
        s2 = Step(name="x", action=lambda: True, depends_on=["b", "a"])
        assert s1.fingerprint() == s2.fingerprint()

    def test_ready_steps_with_no_deps(self):
        r = Recipe(name="parallel", steps=[
            _ok_step("a"),
            _ok_step("b"),
            _ok_step("c"),
        ])
        ready = r.ready_steps(set())
        assert len(ready) == 3

    def test_recipe_fingerprint_includes_tags(self):
        r1 = Recipe(name="r", tags=["gpu"])
        r2 = Recipe(name="r", tags=["cpu"])
        assert r1.fingerprint() != r2.fingerprint()

    def test_recipe_fingerprint_includes_constraints(self):
        r1 = Recipe(name="r", constraint_profile={"mem": "8G"})
        r2 = Recipe(name="r", constraint_profile={"mem": "4G"})
        assert r1.fingerprint() != r2.fingerprint()

    def test_self_cycle_detected(self):
        r = Recipe(name="self-cycle")
        r.add_step(Step("a", lambda: True, depends_on=["a"]))
        with pytest.raises(ValueError, match="cycle"):
            r.topological_order()


# ---------------------------------------------------------------------------
# Monitor edge cases
# ---------------------------------------------------------------------------

class TestMonitorEdgeCases:
    def test_summary_with_no_events(self):
        m = BuildMonitor()
        s = m.summary("nonexistent")
        assert s["events"] == 0
        assert s["build_completed"] is False

    def test_record_step_end_without_start(self):
        """Should not crash if step_end is called without step_start."""
        m = BuildMonitor()
        duration = m.record_step_end("r1", "orphan", True)
        assert duration >= 0.0

    def test_all_event_kinds(self):
        """Ensure every EventKind is recordable."""
        m = BuildMonitor()
        for kind in EventKind:
            m.record(kind, "test-recipe")
        events = m.events_for("test-recipe")
        assert len(events) == len(EventKind)

    def test_ring_buffer_drops_oldest(self):
        m = BuildMonitor(max_events=3)
        m.record(EventKind.SUBMITTED, "r1")
        m.record(EventKind.SUBMITTED, "r2")
        m.record(EventKind.SUBMITTED, "r3")
        m.record(EventKind.SUBMITTED, "r4")
        assert m.total_events == 3
        # r1 should have been dropped
        assert len(m.events_for("r1")) == 0
        assert len(m.events_for("r4")) == 1


# ---------------------------------------------------------------------------
# Forge integration edge cases
# ---------------------------------------------------------------------------

class TestForgeEdgeCases:
    def test_build_all_empty(self):
        forge = Forge()
        results = forge.build_all()
        assert results == []

    def test_artifact_for_recipe_filtering(self):
        forge = Forge()
        a1 = Artifact(name="a1", path="/p1", recipe_name="r1")
        a2 = Artifact(name="a2", path="/p2", recipe_name="r2")
        a3 = Artifact(name="a3", path="/p3", recipe_name="r1")
        forge.register_artifact(a1)
        forge.register_artifact(a2)
        forge.register_artifact(a3)
        r1_arts = forge.artifact_for_recipe("r1")
        assert len(r1_arts) == 2
        r2_arts = forge.artifact_for_recipe("r2")
        assert len(r2_arts) == 1

    def test_reset_steps_nonexistent(self):
        forge = Forge()
        assert forge.reset_steps("ghost") is False

    def test_get_artifact_nonexistent(self):
        forge = Forge()
        assert forge.get_artifact("ghost") is None

    def test_custom_config(self):
        config = ForgeConfig(max_workers=8, artifact_ttl_seconds=3600, retry_default=2)
        forge = Forge(config=config)
        assert forge.queue.max_workers == 8

    def test_submit_with_priority(self):
        forge = Forge()
        r1 = Recipe(name="low", steps=[_ok_step("s")])
        r2 = Recipe(name="high", steps=[_ok_step("s")])
        forge.submit(r1, Priority.LOW)
        forge.submit(r2, Priority.HIGH)
        # High should be built first
        result = forge.build_one()
        assert result["name"] == "high"

    def test_monitoring_step_timing_recorded(self):
        forge = Forge()
        r = Recipe(name="timed", steps=[_ok_step("fast")])
        forge.submit(r)
        forge.build_one()
        events = forge.monitor.events_for("timed")
        has_start = any(e.kind == EventKind.STEP_STARTED for e in events)
        has_end = any(e.kind == EventKind.STEP_COMPLETED for e in events)
        assert has_start and has_end

    def test_failed_build_recorded_in_monitor(self):
        forge = Forge()
        r = Recipe(name="failed")
        r.add_step(_fail_step("boom"))
        forge.submit(r)
        forge.build_one()
        summary = forge.monitor.summary("failed")
        assert summary["build_failed"] is True
