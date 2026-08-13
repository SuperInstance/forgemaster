"""Integration tests covering Forge orchestration paths.

These tests exercise the Forge class as the top-level orchestrator,
focusing on paths that unit tests on individual components miss:
- reset_steps and its interaction with build_one
- register_artifact and artifact_for_recipe
- stats aggregation across subsystems
- Step retries through the Forge.build_one pipeline
- Deep dependency chains with mixed success/failure
- ForgeConfig customization
"""

import pytest

from forgemaster import (
    Artifact,
    ArtifactState,
    BuildMonitor,
    Forge,
    Priority,
    Recipe,
    Step,
)
from forgemaster.forge import ForgeConfig
from forgemaster.recipe import StepStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_step(name: str, succeeds: bool = True, depends_on: list[str] | None = None,
              retries: int = 0, fail_times: int = 0):
    """Create a Step with a configurable action.

    If fail_times > 0, the action fails that many times before succeeding
    (requires retries >= fail_times for the step to ultimately succeed).
    """
    calls = {"n": 0}

    def action():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            return False
        return succeeds

    return Step(name=name, action=action, depends_on=depends_on or [], retries=retries)


def make_recipe(name: str, steps: list[Step]) -> Recipe:
    r = Recipe(name=name)
    for s in steps:
        r.add_step(s)
    return r


# ---------------------------------------------------------------------------
# Forge.reset_steps
# ---------------------------------------------------------------------------

class TestResetSteps:
    def test_reset_after_build_allows_rebuild(self):
        step = make_step("a", succeeds=True)
        recipe = make_recipe("r1", [step])
        forge = Forge()
        forge.submit(recipe)
        forge.build_all()
        assert step.status == StepStatus.SUCCEEDED

        assert forge.reset_steps("r1") is True
        assert step.status == StepStatus.PENDING
        assert step.error is None
        assert step.attempts == 0

    def test_reset_unknown_recipe_returns_false(self):
        forge = Forge()
        assert forge.reset_steps("nonexistent") is False

    def test_reset_clears_failed_status(self):
        step = make_step("a", succeeds=False)
        recipe = make_recipe("r1", [step])
        forge = Forge()
        forge.submit(recipe)
        forge.build_all()
        assert step.status == StepStatus.FAILED

        forge.reset_steps("r1")
        assert step.status == StepStatus.PENDING
        assert step.error is None

    def test_reset_clears_skipped_status(self):
        s1 = make_step("a", succeeds=False)
        s2 = make_step("b", succeeds=True, depends_on=["a"])
        recipe = make_recipe("chain", [s1, s2])
        forge = Forge()
        forge.submit(recipe)
        forge.build_all()
        assert s2.status == StepStatus.SKIPPED

        forge.reset_steps("chain")
        assert s1.status == StepStatus.SUCCEEDED or s1.status == StepStatus.PENDING
        assert s2.status == StepStatus.PENDING


# ---------------------------------------------------------------------------
# Step retries through Forge.build_one
# ---------------------------------------------------------------------------

class TestForgeStepRetries:
    def test_retry_succeeds_on_second_attempt(self):
        # Step fails once, then succeeds. retries=1 means 2 total attempts.
        step = make_step("flaky", succeeds=True, retries=1, fail_times=1)
        recipe = make_recipe("retry-rbp", [step])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert result["name"] == "retry-rbp"
        assert step.status == StepStatus.SUCCEEDED
        assert step.attempts == 2

    def test_retry_exhausted_marks_failed(self):
        step = make_step("always-fails", succeeds=False, retries=2)
        recipe = make_recipe("doomed", [step])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert step.status == StepStatus.FAILED
        assert step.attempts == 3  # 1 + 2 retries

    def test_no_retry_fails_on_first_attempt(self):
        step = make_step("no-retry", succeeds=False, retries=0, fail_times=1)
        recipe = make_recipe("single-shot", [step])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert step.attempts == 1


# ---------------------------------------------------------------------------
# Artifact management
# ---------------------------------------------------------------------------

class TestForgeArtifacts:
    def test_register_artifact_records_monitor_event(self):
        forge = Forge()
        artifact = Artifact(name="binary-1", path="/tmp/binary", recipe_name="r1")
        forge.register_artifact(artifact)

        events = forge.monitor.events_for("r1")
        kinds = [e.kind.value for e in events]
        assert "artifact_ready" in kinds

    def test_get_artifact_returns_registered(self):
        forge = Forge()
        art = Artifact(name="img-1", path="/imgs/1.png", recipe_name="build-img")
        forge.register_artifact(art)

        retrieved = forge.get_artifact("img-1")
        assert retrieved is art

    def test_get_artifact_unknown_returns_none(self):
        forge = Forge()
        assert forge.get_artifact("nope") is None

    def test_artifact_for_recipe_filters_correctly(self):
        forge = Forge()
        a1 = Artifact(name="a1", path="/a1", recipe_name="build-x")
        a2 = Artifact(name="a2", path="/a2", recipe_name="build-y")
        a3 = Artifact(name="a3", path="/a3", recipe_name="build-x")
        forge.register_artifact(a1)
        forge.register_artifact(a2)
        forge.register_artifact(a3)

        results = forge.artifact_for_recipe("build-x")
        assert len(results) == 2
        names = {a.name for a in results}
        assert names == {"a1", "a3"}

    def test_artifact_for_recipe_no_matches(self):
        forge = Forge()
        assert forge.artifact_for_recipe("nobody") == []


# ---------------------------------------------------------------------------
# Forge.stats
# ---------------------------------------------------------------------------

class TestForgeStats:
    def test_stats_empty_forge(self):
        forge = Forge()
        s = forge.stats()
        assert s["queue"]["pending"] == 0
        assert s["queue"]["running"] == 0
        assert s["queue"]["completed"] == 0
        assert s["queue"]["failed"] == 0
        assert s["artifacts"] == 0
        assert s["monitor_events"] == 0

    def test_stats_after_submit(self):
        step = make_step("a")
        recipe = make_recipe("stat-r", [step])
        forge = Forge()
        forge.submit(recipe)

        s = forge.stats()
        assert s["queue"]["pending"] == 1
        assert s["monitor_events"] == 1  # SUBMITTED event

    def test_stats_after_build(self):
        step = make_step("a")
        recipe = make_recipe("stat-built", [step])
        forge = Forge()
        forge.submit(recipe)
        forge.build_one()

        s = forge.stats()
        assert s["queue"]["pending"] == 0
        assert s["queue"]["completed"] == 1
        # Events: SUBMITTED, STEP_STARTED, STEP_COMPLETED, BUILD_COMPLETED
        assert s["monitor_events"] >= 3

    def test_stats_with_artifacts(self):
        forge = Forge()
        forge.register_artifact(Artifact(name="x", path="/x", recipe_name="r"))
        s = forge.stats()
        assert s["artifacts"] == 1


# ---------------------------------------------------------------------------
# Deep dependency chains
# ---------------------------------------------------------------------------

class TestDependencyChains:
    def test_four_step_chain_all_succeed(self):
        s1 = make_step("fetch")
        s2 = make_step("build", depends_on=["fetch"])
        s3 = make_step("test", depends_on=["build"])
        s4 = make_step("deploy", depends_on=["test"])
        recipe = make_recipe("pipeline", [s1, s2, s3, s4])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert len(result["completed_steps"]) == 4
        assert all(s.status == StepStatus.SUCCEEDED for s in [s1, s2, s3, s4])

    def test_middle_failure_cascades_skip(self):
        s1 = make_step("fetch", succeeds=True)
        s2 = make_step("compile", succeeds=False)
        s3 = make_step("test", succeeds=True, depends_on=["compile"])
        s4 = make_step("deploy", succeeds=True, depends_on=["test"])
        recipe = make_recipe("broken-pipeline", [s1, s2, s3, s4])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert s1.status == StepStatus.SUCCEEDED
        assert s2.status == StepStatus.FAILED
        # s3 and s4 should be skipped because upstream failed
        assert s3.status == StepStatus.SKIPPED
        assert s4.status == StepStatus.SKIPPED

    def test_diamond_dependency(self):
        r"""    A
               / \
              B   C
               \ /
                D
        """
        s1 = make_step("A")
        s2 = make_step("B", depends_on=["A"])
        s3 = make_step("C", depends_on=["A"])
        s4 = make_step("D", depends_on=["B", "C"])
        recipe = make_recipe("diamond", [s1, s2, s3, s4])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert all(s.status == StepStatus.SUCCEEDED for s in [s1, s2, s3, s4])


# ---------------------------------------------------------------------------
# ForgeConfig
# ---------------------------------------------------------------------------

class TestForgeConfig:
    def test_custom_max_workers(self):
        cfg = ForgeConfig(max_workers=8)
        forge = Forge(cfg)
        assert forge.queue.max_workers == 8

    def test_custom_monitor_max_events(self):
        cfg = ForgeConfig(monitor_max_events=50)
        forge = Forge(cfg)
        assert forge.monitor.max_events == 50

    def test_default_config_values(self):
        cfg = ForgeConfig()
        assert cfg.max_workers == 4
        assert cfg.artifact_ttl_seconds == 86400 * 7
        assert cfg.retry_default == 0
        assert cfg.monitor_max_events == 10_000


# ---------------------------------------------------------------------------
# Cancel through Forge
# ---------------------------------------------------------------------------

class TestForgeCancel:
    def test_cancel_pending_recipe(self):
        step = make_step("a")
        recipe = make_recipe("cancel-me", [step])
        forge = Forge()
        forge.submit(recipe)

        assert forge.cancel("cancel-me") is True
        assert forge.queue.pending_count == 0

    def test_cancel_nonexistent(self):
        forge = Forge()
        assert forge.cancel("ghost") is False


# ---------------------------------------------------------------------------
# build_all with multiple recipes
# ---------------------------------------------------------------------------

class TestForgeBuildAll:
    def test_build_all_processes_in_priority_order(self):
        r1 = make_recipe("low", [make_step("a")])
        r2 = make_recipe("high", [make_step("b")])
        r3 = make_recipe("critical", [make_step("c")])
        forge = Forge()
        forge.submit(r1, priority=Priority.LOW)
        forge.submit(r2, priority=Priority.HIGH)
        forge.submit(r3, priority=Priority.CRITICAL)

        results = forge.build_all()
        names = [r["name"] for r in results]
        assert names == ["critical", "high", "low"]
        assert all(r["success"] for r in results)

    def test_build_all_mixed_success(self):
        good = make_recipe("good", [make_step("a", succeeds=True)])
        bad = make_recipe("bad", [make_step("b", succeeds=False)])
        forge = Forge()
        forge.submit(good)
        forge.submit(bad)

        results = forge.build_all()
        success_map = {r["name"]: r["success"] for r in results}
        assert success_map["good"] is True
        assert success_map["bad"] is False


# ---------------------------------------------------------------------------
# Exception handling in steps
# ---------------------------------------------------------------------------

class TestStepExceptions:
    def test_step_raises_exception_is_caught(self):
        def boom():
            raise RuntimeError("explosion in the forge")

        step = Step(name="dangerous", action=boom)
        recipe = make_recipe("exploder", [step])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is False
        assert "explosion in the forge" in result["errors"][0]
        assert step.status == StepStatus.FAILED

    def test_step_exception_with_retry_then_success(self):
        calls = {"n": 0}

        def flaky_boom():
            calls["n"] += 1
            if calls["n"] == 1:
                raise ValueError("first attempt fails")
            return True

        step = Step(name="phoenix", action=flaky_boom, retries=1)
        recipe = make_recipe("risen", [step])
        forge = Forge()
        forge.submit(recipe)
        result = forge.build_one()

        assert result["success"] is True
        assert step.attempts == 2


# ---------------------------------------------------------------------------
# Monitor integration through Forge
# ---------------------------------------------------------------------------

class TestForgeMonitorIntegration:
    def test_build_one_records_step_timings(self):
        s1 = make_step("first")
        s2 = make_step("second", depends_on=["first"])
        recipe = make_recipe("timed", [s1, s2])
        forge = Forge()
        forge.submit(recipe)
        forge.build_one()

        summary = forge.monitor.summary("timed")
        assert summary["steps_completed"] == 2
        assert summary["build_completed"] is True

    def test_failed_build_summary(self):
        step = make_step("doomed", succeeds=False)
        recipe = make_recipe("doomed-build", [step])
        forge = Forge()
        forge.submit(recipe)
        forge.build_one()

        summary = forge.monitor.summary("doomed-build")
        assert summary["build_failed"] is True
        assert summary["steps_failed"] == 1

    def test_submit_records_submitted_event(self):
        step = make_step("a")
        recipe = make_recipe("evt-test", [step])
        forge = Forge()
        forge.submit(recipe, submitted_by="tester")

        events = forge.monitor.events_for("evt-test")
        assert any(e.kind.value == "submitted" for e in events)
        submitted_evt = next(e for e in events if e.kind.value == "submitted")
        assert submitted_evt.detail == "tester"
