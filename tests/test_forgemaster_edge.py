"""
Edge case tests for Artifact and BuildMonitor.

Covers:
  Artifact:
    - compute_digest with None content → STALE state
    - compute_digest with empty bytes → READY, size 0
    - mark_ready sets state and digest
    - mark_failed sets state
    - is_valid logic for BUILDING and READY
    - age_seconds with and without now parameter
    - to_dict serialization
    - tags and metadata defaults

  BuildMonitor:
    - Ring buffer eviction drops oldest
    - events_for unknown recipe returns empty
    - record_step_start/end duration measurement
    - summary for unknown recipe
    - multiple recipes tracked independently
    - metadata propagation through kwargs
    - clear resets everything
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from forgemaster.artifact import Artifact, ArtifactState
from forgemaster.monitor import BuildMonitor, EventKind
from forgemaster.recipe import Recipe, Step, StepStatus
from forgemaster.queue import BuildQueue, Priority, QueueEntry
from forgemaster.forge import Forge, ForgeConfig


# ─── Artifact Edge Cases ──────────────────────────────────────

class TestArtifactComputeDigest(unittest.TestCase):

    def test_compute_digest_with_content_sets_ready(self):
        art = Artifact(name="test", path="/tmp/test", recipe_name="r1")
        content = b"hello world"
        digest = art.compute_digest(content)
        self.assertEqual(len(digest), 40)  # truncated sha256
        self.assertEqual(art.size_bytes, len(content))
        self.assertEqual(art.state, ArtifactState.READY)

    def test_compute_digest_none_content_sets_stale(self):
        art = Artifact(name="test", path="/tmp/test", recipe_name="r1")
        digest = art.compute_digest(None)
        self.assertEqual(art.state, ArtifactState.STALE)

    def test_compute_digest_empty_bytes(self):
        art = Artifact(name="test", path="/tmp/test", recipe_name="r1")
        digest = art.compute_digest(b"")
        self.assertEqual(art.size_bytes, 0)
        self.assertEqual(art.state, ArtifactState.READY)

    def test_compute_digest_deterministic(self):
        art1 = Artifact(name="a", path="/p", recipe_name="r")
        art2 = Artifact(name="b", path="/q", recipe_name="s")
        d1 = art1.compute_digest(b"same content")
        d2 = art2.compute_digest(b"same content")
        self.assertEqual(d1, d2)


class TestArtifactStates(unittest.TestCase):

    def test_mark_ready(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        art.mark_ready("abc123", 42)
        self.assertEqual(art.state, ArtifactState.READY)
        self.assertEqual(art.digest, "abc123")
        self.assertEqual(art.size_bytes, 42)

    def test_mark_failed(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        art.mark_failed()
        self.assertEqual(art.state, ArtifactState.FAILED)

    def test_is_valid_for_ready(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        art.mark_ready("d", 1)
        self.assertTrue(art.is_valid())

    def test_is_valid_for_building(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        art.state = ArtifactState.BUILDING
        self.assertTrue(art.is_valid())

    def test_is_valid_for_failed(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        art.mark_failed()
        self.assertFalse(art.is_valid())

    def test_is_valid_for_stale(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        art.state = ArtifactState.STALE
        self.assertFalse(art.is_valid())

    def test_is_valid_for_unknown(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        self.assertFalse(art.is_valid())  # default is UNKNOWN


class TestArtifactAge(unittest.TestCase):

    def test_age_seconds_with_now(self):
        art = Artifact(name="t", path="/p", recipe_name="r", created_at=1000.0)
        age = art.age_seconds(now=1010.0)
        self.assertAlmostEqual(age, 10.0)

    def test_age_seconds_without_now(self):
        art = Artifact(name="t", path="/p", recipe_name="r", created_at=time.time() - 1)
        age = art.age_seconds()
        self.assertGreaterEqual(age, 0.5)


class TestArtifactToDict(unittest.TestCase):

    def test_to_dict_has_all_fields(self):
        art = Artifact(
            name="test", path="/p", recipe_name="r",
            tags=["a", "b"], metadata={"k": "v"},
        )
        art.mark_ready("digest", 100)
        d = art.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["path"], "/p")
        self.assertEqual(d["recipe_name"], "r")
        self.assertEqual(d["tags"], ["a", "b"])
        self.assertEqual(d["state"], "ready")
        self.assertEqual(d["digest"], "digest")
        self.assertEqual(d["size_bytes"], 100)
        self.assertEqual(d["metadata"], {"k": "v"})

    def test_to_dict_state_is_string_not_enum(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        d = art.to_dict()
        self.assertIsInstance(d["state"], str)


class TestArtifactDefaults(unittest.TestCase):

    def test_default_tags_empty(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        self.assertEqual(art.tags, [])

    def test_default_metadata_empty(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        self.assertEqual(art.metadata, {})

    def test_default_state_unknown(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        self.assertEqual(art.state, ArtifactState.UNKNOWN)

    def test_default_digest_empty_string(self):
        art = Artifact(name="t", path="/p", recipe_name="r")
        self.assertEqual(art.digest, "")


# ─── BuildMonitor Edge Cases ──────────────────────────────────

class TestBuildMonitorRingBuffer(unittest.TestCase):

    def test_ring_buffer_eviction_drops_oldest(self):
        mon = BuildMonitor(max_events=3)
        mon.record(EventKind.SUBMITTED, "r1")
        mon.record(EventKind.STEP_STARTED, "r1", "step1")
        mon.record(EventKind.STEP_COMPLETED, "r1", "step1")
        mon.record(EventKind.BUILD_COMPLETED, "r1")
        # First event should have been dropped
        self.assertEqual(mon.total_events, 3)
        recent = mon.recent(10)
        kinds = [e.kind for e in recent]
        self.assertNotIn(EventKind.SUBMITTED, kinds)

    def test_ring_buffer_exact_capacity(self):
        mon = BuildMonitor(max_events=2)
        mon.record(EventKind.SUBMITTED, "r1")
        mon.record(EventKind.STEP_STARTED, "r1", "s1")
        self.assertEqual(mon.total_events, 2)
        mon.record(EventKind.STEP_COMPLETED, "r1", "s1")
        self.assertEqual(mon.total_events, 2)


class TestBuildMonitorQueries(unittest.TestCase):

    def test_events_for_unknown_recipe_empty(self):
        mon = BuildMonitor()
        self.assertEqual(mon.events_for("nonexistent"), [])

    def test_summary_unknown_recipe(self):
        mon = BuildMonitor()
        s = mon.summary("unknown")
        self.assertEqual(s["events"], 0)
        self.assertFalse(s["build_completed"])
        self.assertFalse(s["build_failed"])

    def test_multiple_recipes_independent(self):
        mon = BuildMonitor()
        mon.record(EventKind.SUBMITTED, "r1")
        mon.record(EventKind.SUBMITTED, "r2")
        mon.record(EventKind.STEP_STARTED, "r1", "s1")
        self.assertEqual(len(mon.events_for("r1")), 2)
        self.assertEqual(len(mon.events_for("r2")), 1)


class TestBuildMonitorStepTiming(unittest.TestCase):

    def test_step_start_end_measures_duration(self):
        mon = BuildMonitor()
        mon.record_step_start("r1", "s1")
        duration = mon.record_step_end("r1", "s1", success=True)
        self.assertGreaterEqual(duration, 0.0)

    def test_step_end_records_completed_on_success(self):
        mon = BuildMonitor()
        mon.record_step_start("r1", "s1")
        mon.record_step_end("r1", "s1", success=True)
        evts = mon.events_for("r1")
        kinds = [e.kind for e in evts]
        self.assertIn(EventKind.STEP_COMPLETED, kinds)

    def test_step_end_records_failed_on_failure(self):
        mon = BuildMonitor()
        mon.record_step_start("r1", "s1")
        mon.record_step_end("r1", "s1", success=False)
        evts = mon.events_for("r1")
        kinds = [e.kind for e in evts]
        self.assertIn(EventKind.STEP_FAILED, kinds)

    def test_step_duration_in_metadata(self):
        mon = BuildMonitor()
        mon.record_step_start("r1", "s1")
        mon.record_step_end("r1", "s1", success=True)
        evts = mon.events_for("r1")
        completed = [e for e in evts if e.kind == EventKind.STEP_COMPLETED]
        self.assertEqual(len(completed), 1)
        self.assertIn("duration_s", completed[0].metadata)


class TestBuildMonitorMetadata(unittest.TestCase):

    def test_record_passes_metadata_through_kwargs(self):
        mon = BuildMonitor()
        evt = mon.record(EventKind.SUBMITTED, "r1", detail="test", custom_key="custom_value")
        self.assertEqual(evt.metadata["custom_key"], "custom_value")

    def test_record_detail_stored(self):
        mon = BuildMonitor()
        evt = mon.record(EventKind.SUBMITTED, "r1", detail="user-submitted")
        self.assertEqual(evt.detail, "user-submitted")


class TestBuildMonitorClear(unittest.TestCase):

    def test_clear_resets_events(self):
        mon = BuildMonitor()
        mon.record(EventKind.SUBMITTED, "r1")
        mon.record(EventKind.STEP_STARTED, "r1", "s1")
        mon.clear()
        self.assertEqual(mon.total_events, 0)
        self.assertEqual(mon.events_for("r1"), [])

    def test_clear_resets_durations(self):
        mon = BuildMonitor()
        mon.record_step_start("r1", "s1")
        mon.clear()
        # After clearing, step end with no matching start should still work
        duration = mon.record_step_end("r1", "s1", success=True)
        self.assertGreaterEqual(duration, 0.0)


class TestBuildMonitorRecent(unittest.TestCase):

    def test_recent_returns_last_n(self):
        mon = BuildMonitor()
        for i in range(10):
            mon.record(EventKind.SUBMITTED, f"r{i}")
        recent = mon.recent(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[-1].recipe_name, "r9")

    def test_recent_returns_all_if_fewer_than_n(self):
        mon = BuildMonitor()
        mon.record(EventKind.SUBMITTED, "r1")
        recent = mon.recent(10)
        self.assertEqual(len(recent), 1)


# ─── Queue Edge Cases ─────────────────────────────────────────

class TestQueueEdgeCases(unittest.TestCase):

    def test_peek_empty_queue(self):
        q = BuildQueue()
        self.assertIsNone(q.peek())

    def test_pop_empty_queue(self):
        q = BuildQueue()
        self.assertIsNone(q.pop())

    def test_submit_same_recipe_twice(self):
        q = BuildQueue()
        recipe = Recipe(name="r1")
        recipe.add_step(Step(name="s1", action=lambda: True))
        t1 = q.submit(recipe)
        t2 = q.submit(recipe)
        # Both should return recipe name as ticket
        self.assertEqual(t1, "r1")
        self.assertEqual(t2, "r1")
        # Both in queue
        self.assertEqual(q.pending_count, 2)

    def test_priority_ordering_all_levels(self):
        q = BuildQueue()
        recipes = []
        for i, p in enumerate([Priority.BACKGROUND, Priority.LOW, Priority.NORMAL,
                               Priority.HIGH, Priority.CRITICAL]):
            r = Recipe(name=f"r{i}")
            r.add_step(Step(name="s", action=lambda: True))
            recipes.append(r)
            q.submit(r, priority=p)

        # Should pop in priority order: CRITICAL, HIGH, NORMAL, LOW, BACKGROUND
        order = []
        while q.pending_count > 0:
            entry = q.pop()
            order.append(entry.recipe.name)
        self.assertEqual(order, ["r4", "r3", "r2", "r1", "r0"])


if __name__ == "__main__":
    unittest.main()
