"""Tests for forgemaster package."""

import time
from forgemaster.artifact import Artifact, ArtifactState
from forgemaster.forge import Forge, ForgeConfig
from forgemaster.monitor import BuildMonitor, EventKind
from forgemaster.queue import BuildQueue, Priority
from forgemaster.recipe import Recipe, Step, StepStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_step(name: str, depends_on: list[str] | None = None) -> Step:
    return Step(name=name, action=lambda: True, depends_on=depends_on or [])


def _fail_step(name: str, depends_on: list[str] | None = None) -> Step:
    def _boom():
        raise RuntimeError("boom")
    return Step(name=name, action=_boom, depends_on=depends_on or [])


def _flaky_step(name: str, succeed_on_attempt: int) -> Step:
    call_count = {"n": 0}
    def _flaky():
        call_count["n"] += 1
        return call_count["n"] >= succeed_on_attempt
    return Step(name=name, action=_flaky)


def _simple_recipe(name: str = "test-recipe") -> Recipe:
    return Recipe(name=name, steps=[
        _ok_step("step-a"),
        _ok_step("step-b", depends_on=["step-a"]),
        _ok_step("step-c", depends_on=["step-b"]),
    ])


# ===========================================================================
# Recipe tests
# ===========================================================================

class TestRecipe:
    def test_topological_order(self):
        r = _simple_recipe()
        order = r.topological_order()
        names = [s.name for s in order]
        assert names.index("step-a") < names.index("step-b")
        assert names.index("step-b") < names.index("step-c")

    def test_cycle_detection(self):
        r = Recipe(name="cycle")
        r.add_step(Step("a", lambda: True, depends_on=["b"]))
        r.add_step(Step("b", lambda: True, depends_on=["a"]))
        try:
            r.topological_order()
            assert False, "Should have raised"
        except ValueError as e:
            assert "cycle" in str(e).lower()

    def test_missing_dependency(self):
        r = Recipe(name="missing-dep")
        r.add_step(Step("a", lambda: True, depends_on=["ghost"]))
        try:
            r.topological_order()
            assert False, "Should have raised"
        except ValueError as e:
            assert "ghost" in str(e)

    def test_ready_steps(self):
        r = _simple_recipe()
        ready = r.ready_steps(set())
        assert len(ready) == 1 and ready[0].name == "step-a"

        # step-a stays PENDING so it's still "ready" — mark it succeeded
        r.step_by_name("step-a").status = StepStatus.SUCCEEDED
        ready = r.ready_steps({"step-a"})
        assert len(ready) == 1 and ready[0].name == "step-b"

    def test_fingerprint_deterministic(self):
        r1 = _simple_recipe()
        r2 = _simple_recipe()
        assert r1.fingerprint() == r2.fingerprint()

    def test_add_step_chaining(self):
        r = Recipe(name="chain")
        result = r.add_step(_ok_step("x"))
        assert result is r
        assert len(r.steps) == 1


# ===========================================================================
# Artifact tests
# ===========================================================================

class TestArtifact:
    def test_compute_digest(self):
        a = Artifact(name="bin", path="/tmp/bin", recipe_name="r")
        digest = a.compute_digest(b"hello world")
        assert len(digest) == 40
        assert a.state == ArtifactState.READY
        assert a.size_bytes == 11

    def test_compute_digest_no_content(self):
        a = Artifact(name="bin", path="/tmp/bin", recipe_name="r")
        a.compute_digest(None)
        assert a.state == ArtifactState.STALE

    def test_mark_ready(self):
        a = Artifact(name="bin", path="/tmp/bin", recipe_name="r")
        a.mark_ready("abc123", 42)
        assert a.state == ArtifactState.READY
        assert a.digest == "abc123"
        assert a.size_bytes == 42

    def test_mark_failed(self):
        a = Artifact(name="bin", path="/tmp/bin", recipe_name="r")
        a.mark_failed()
        assert a.state == ArtifactState.FAILED
        assert not a.is_valid()

    def test_to_dict(self):
        a = Artifact(name="bin", path="/tmp/bin", recipe_name="r", tags=["gpu"])
        d = a.to_dict()
        assert d["name"] == "bin"
        assert d["tags"] == ["gpu"]
        assert "state" in d


# ===========================================================================
# BuildQueue tests
# ===========================================================================

class TestBuildQueue:
    def test_submit_and_pop_fifo(self):
        q = BuildQueue()
        r1 = Recipe(name="first")
        r2 = Recipe(name="second")
        q.submit(r1, Priority.NORMAL)
        q.submit(r2, Priority.NORMAL)
        assert q.pop().recipe.name == "first"
        assert q.pop().recipe.name == "second"

    def test_priority_ordering(self):
        q = BuildQueue()
        q.submit(Recipe(name="low"), Priority.LOW)
        q.submit(Recipe(name="critical"), Priority.CRITICAL)
        q.submit(Recipe(name="normal"), Priority.NORMAL)
        assert q.pop().recipe.name == "critical"
        assert q.pop().recipe.name == "normal"
        assert q.pop().recipe.name == "low"

    def test_execute_one_success(self):
        q = BuildQueue()
        r = _simple_recipe()
        q.submit(r)
        result = q.execute_one()
        assert result["success"] is True
        assert result["completed_steps"] == ["step-a", "step-b", "step-c"]

    def test_execute_one_failure(self):
        q = BuildQueue()
        r = Recipe(name="fail-build")
        r.add_step(_ok_step("step-a"))
        r.add_step(_fail_step("step-b", depends_on=["step-a"]))
        r.add_step(_ok_step("step-c", depends_on=["step-b"]))
        q.submit(r)
        result = q.execute_one()
        assert result["success"] is False
        assert "step-a" in result["completed_steps"]
        assert "step-b" not in result["completed_steps"]

    def test_drain(self):
        q = BuildQueue()
        q.submit(Recipe(name="r1", steps=[_ok_step("a")]))
        q.submit(Recipe(name="r2", steps=[_ok_step("b")]))
        results = q.drain()
        assert len(results) == 2
        assert q.pending_count == 0

    def test_cancel(self):
        q = BuildQueue()
        q.submit(Recipe(name="cancel-me"))
        assert q.cancel("cancel-me") is True
        assert q.pending_count == 0
        assert q.cancel("nonexistent") is False

    def test_stats(self):
        q = BuildQueue()
        q.submit(Recipe(name="s", steps=[_ok_step("x")]))
        stats = q.stats()
        assert stats["pending"] == 1
        q.execute_one()
        stats = q.stats()
        assert stats["pending"] == 0
        assert stats["completed"] == 1

    def test_empty_queue_execute(self):
        q = BuildQueue()
        result = q.execute_one()
        assert result["success"] is False
        assert result["name"] is None

    def test_retry(self):
        q = BuildQueue()
        r = Recipe(name="retry")
        r.add_step(_flaky_step("flaky", succeed_on_attempt=3))
        r.steps[0].retries = 3
        q.submit(r)
        result = q.execute_one()
        assert result["success"] is True
        assert r.steps[0].attempts == 3

    def test_peek(self):
        q = BuildQueue()
        q.submit(Recipe(name="peek-me"), Priority.HIGH)
        entry = q.peek()
        assert entry.recipe.name == "peek-me"
        assert q.pending_count == 1  # peek doesn't remove


# ===========================================================================
# BuildMonitor tests
# ===========================================================================

class TestBuildMonitor:
    def test_record_and_query(self):
        m = BuildMonitor()
        m.record(EventKind.SUBMITTED, "r1")
        m.record(EventKind.BUILD_COMPLETED, "r1")
        evts = m.events_for("r1")
        assert len(evts) == 2
        assert evts[0].kind == EventKind.SUBMITTED

    def test_recent(self):
        m = BuildMonitor()
        for i in range(30):
            m.record(EventKind.SUBMITTED, f"r{i}")
        recent = m.recent(5)
        assert len(recent) == 5

    def test_step_timing(self):
        m = BuildMonitor()
        m.record_step_start("r1", "compile")
        time.sleep(0.01)
        duration = m.record_step_end("r1", "compile", True)
        assert duration >= 0.01

    def test_summary(self):
        m = BuildMonitor()
        m.record(EventKind.SUBMITTED, "r1")
        m.record(EventKind.STEP_COMPLETED, "r1", "step-a")
        m.record(EventKind.STEP_FAILED, "r1", "step-b")
        s = m.summary("r1")
        assert s["steps_completed"] == 1
        assert s["steps_failed"] == 1

    def test_ring_buffer(self):
        m = BuildMonitor(max_events=5)
        for i in range(10):
            m.record(EventKind.SUBMITTED, f"r{i}")
        assert m.total_events == 5

    def test_clear(self):
        m = BuildMonitor()
        m.record(EventKind.SUBMITTED, "r1")
        m.clear()
        assert m.total_events == 0


# ===========================================================================
# Forge integration tests
# ===========================================================================

class TestForge:
    def test_submit_and_build_one(self):
        forge = Forge()
        r = _simple_recipe("forge-basic")
        forge.submit(r)
        result = forge.build_one()
        assert result["success"] is True
        assert result["name"] == "forge-basic"

    def test_build_all(self):
        forge = Forge()
        for i in range(3):
            r = Recipe(name=f"batch-{i}", steps=[_ok_step("s")])
            forge.submit(r)
        results = forge.build_all()
        assert len(results) == 3
        assert all(r["success"] for r in results)

    def test_artifact_tracking(self):
        forge = Forge()
        r = Recipe(name="artifact-build", steps=[_ok_step("build")])
        forge.submit(r)
        forge.build_one()
        art = Artifact(name="binary", path="/out/binary", recipe_name="artifact-build")
        art.compute_digest(b"\x00\x01\x02")
        forge.register_artifact(art)
        retrieved = forge.get_artifact("binary")
        assert retrieved is not None
        assert retrieved.state == ArtifactState.READY

    def test_monitoring(self):
        forge = Forge()
        r = _simple_recipe("monitored")
        forge.submit(r)
        forge.build_one()
        summary = forge.monitor.summary("monitored")
        assert summary["build_completed"] is True
        assert summary["steps_completed"] == 3

    def test_failure_skips_downstream(self):
        forge = Forge()
        r = Recipe(name="cascade-fail")
        r.add_step(_ok_step("setup"))
        r.add_step(_fail_step("compile", depends_on=["setup"]))
        r.add_step(_ok_step("package", depends_on=["compile"]))
        forge.submit(r)
        result = forge.build_one()
        assert result["success"] is False
        assert "setup" in result["completed_steps"]
        assert "compile" not in result["completed_steps"]

    def test_cancel(self):
        forge = Forge()
        r = Recipe(name="cancel-me", steps=[_ok_step("s")])
        forge.submit(r)
        assert forge.cancel("cancel-me") is True
        result = forge.build_one()
        assert result["name"] is None

    def test_reset_steps(self):
        forge = Forge()
        r = Recipe(name="rebuild", steps=[_ok_step("s")])
        forge.submit(r)
        forge.build_one()
        assert r.steps[0].status == StepStatus.SUCCEEDED
        forge.reset_steps("rebuild")
        assert r.steps[0].status == StepStatus.PENDING

    def test_stats(self):
        forge = Forge()
        r = Recipe(name="stats-test", steps=[_ok_step("s")])
        forge.submit(r)
        stats = forge.stats()
        assert stats["queue"]["pending"] == 1
        forge.build_one()
        stats = forge.stats()
        assert stats["queue"]["completed"] == 1
        assert stats["monitor_events"] > 0

    def test_build_empty(self):
        forge = Forge()
        result = forge.build_one()
        assert result["success"] is False
