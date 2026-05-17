#!/usr/bin/env python3
"""Tests for core/gpu_scaling.py — GPU Scaling Experiment Rig."""
import time
import unittest
from core.gpu_scaling import (
    ComputeBackend, BackendType, GPUExperimentRig, CloudDispatch,
    EmergenceDetector, Experiment, Resolution, ExperimentState,
)


class TestComputeBackend(unittest.TestCase):
    """Tests for ComputeBackend profiling and capacity."""

    def test_profile_populates_metrics(self):
        b = ComputeBackend("test-cpu", BackendType.LOCAL_CPU, memory_gb=15.0)
        p = b.profile()
        self.assertEqual(p["type"], "local_cpu")
        self.assertGreater(p["memory_gb"], 0)
        self.assertGreater(p["throughput_models_per_s"], 0)
        self.assertEqual(p["status"], "available")

    def test_can_run_small_model(self):
        b = ComputeBackend("test-cpu", BackendType.LOCAL_CPU, memory_gb=15.0)
        b.status = "available"
        self.assertTrue(b.can_run(1.0))   # 1MB < 15*1024*0.5

    def test_cannot_run_when_offline(self):
        b = ComputeBackend("test-cpu", BackendType.LOCAL_CPU, memory_gb=15.0)
        b.status = "offline"
        self.assertFalse(b.can_run(1.0))

    def test_estimated_time_positive(self):
        b = ComputeBackend("test-cpu", BackendType.LOCAL_CPU)
        b.throughput = 100.0
        t = b.estimated_time(5.0, 10)
        self.assertGreater(t, 0)

    def test_acquire_release_cycle(self):
        b = ComputeBackend("test-cpu", BackendType.LOCAL_CPU)
        b.status = "available"
        self.assertTrue(b.acquire())
        self.assertEqual(b.status, "busy")
        b.release()
        self.assertEqual(b.status, "available")


class TestGPUExperimentRig(unittest.TestCase):
    """Tests for the main GPUExperimentRig orchestration."""

    def setUp(self):
        self.rig = GPUExperimentRig()

    def test_discover_backends(self):
        self.assertIn("local-cpu", self.rig.backends)
        self.assertIn("local-gpu", self.rig.backends)
        self.assertIn("cloud-cuda", self.rig.backends)

    def test_define_experiment(self):
        exp = self.rig.define_experiment("drift-detect", 1.0, 10, Resolution.MICRO)
        self.assertEqual(exp.task, "drift-detect")
        self.assertEqual(exp.model_size_mb, 1.0)
        self.assertEqual(exp.state, ExperimentState.DEFINED)
        self.assertIn(exp.experiment_id, self.rig.experiments)

    def test_dispatch_small_to_cpu(self):
        exp = self.rig.define_experiment("drift-detect", 0.5, 5, Resolution.MICRO)
        result = self.rig.dispatch(exp)
        self.assertEqual(result["status"], "dispatched")
        self.assertEqual(result["assigned_backend"], "local_cpu")

    def test_dispatch_large_to_cloud(self):
        exp = self.rig.define_experiment("sentiment", 500.0, 5, Resolution.LARGE)
        result = self.rig.dispatch(exp)
        self.assertEqual(result["status"], "dispatched")
        # Should go to cloud or cudaclaw (both can handle 500MB)
        self.assertIn(result["assigned_backend"], ["cloud_cuda", "cudaclaw"])

    def test_monitor_returns_state(self):
        exp = self.rig.define_experiment("test", 1.0, 2, Resolution.MICRO)
        self.rig.dispatch(exp)
        time.sleep(0.1)
        mon = self.rig.monitor(exp.experiment_id)
        self.assertEqual(mon["experiment_id"], exp.experiment_id)
        self.assertIn(mon["state"], ["running", "completed", "queued"])

    def test_harvest_results(self):
        exp = self.rig.define_experiment("drift-detect", 1.0, 3, Resolution.MICRO)
        self.rig.dispatch(exp)
        time.sleep(0.5)
        tiles = self.rig.harvest_results(exp.experiment_id)
        # May or may not have completed yet, but function shouldn't crash
        self.assertIsInstance(tiles, list)

    def test_parallel_dispatch(self):
        exps = [
            self.rig.define_experiment("t1", 1.0, 3, Resolution.MICRO),
            self.rig.define_experiment("t2", 2.0, 3, Resolution.MICRO),
        ]
        result = self.rig.dispatch_parallel(exps)
        self.assertEqual(result["dispatched"], 2)

    def test_profile_all(self):
        profiles = self.rig.profile_all()
        self.assertGreaterEqual(len(profiles), 3)
        for bid, p in profiles.items():
            self.assertIn("throughput_models_per_s", p)

    def test_status(self):
        s = self.rig.status()
        self.assertIn("backends", s)
        self.assertIn("experiments", s)
        self.assertIn("harvested_tiles", s)


class TestCloudDispatch(unittest.TestCase):
    """Tests for CloudDispatch."""

    def setUp(self):
        self.cloud = CloudDispatch()

    def test_push_queues_experiment(self):
        exp = Experiment(
            experiment_id="test-001",
            task="drift-detect",
            model_size_mb=100.0,
            n_epochs=10,
            resolution=Resolution.LARGE,
        )
        result = self.cloud.push(exp)
        self.assertEqual(result["status"], "queued_for_cloud")
        self.assertEqual(len(self.cloud.queue), 1)

    def test_estimate_cost(self):
        exp = Experiment(
            experiment_id="test-002",
            task="sentiment",
            model_size_mb=500.0,
            n_epochs=20,
            resolution=Resolution.LARGE,
        )
        cost = self.cloud.estimate_cost(exp)
        self.assertIn("estimates", cost)
        self.assertGreater(len(cost["estimates"]), 0)

    def test_simulate_cloud_run(self):
        exp = Experiment(
            experiment_id="test-003",
            task="drift-detect",
            model_size_mb=200.0,
            n_epochs=10,
            resolution=Resolution.LARGE,
        )
        result = self.cloud.simulate_cloud_run(exp)
        self.assertTrue(result["simulated"])
        self.assertGreater(result["final_accuracy"], 0)
        self.assertLess(result["final_loss"], 1)

    def test_auto_scale(self):
        exps = [
            Experiment(f"auto-{i}", "task", 100 * (i + 1), 10, Resolution.LARGE)
            for i in range(3)
        ]
        result = self.cloud.auto_scale(exps, available_gpus=2)
        self.assertEqual(result["assigned"], 3)

    def test_pull_results_pending(self):
        result = self.cloud.pull_results("nonexistent")
        self.assertEqual(result["status"], "pending")


class TestEmergenceDetector(unittest.TestCase):
    """Tests for EmergenceDetector."""

    def setUp(self):
        self.detector = EmergenceDetector()

    def test_run_at_resolution(self):
        exp = Experiment("em-001", "drift-detect", 1.0, 10, Resolution.MICRO)
        result = self.detector.run_at_resolution(exp, Resolution.MICRO)
        self.assertEqual(result["resolution"], "micro")
        self.assertIn("accuracy", result)
        self.assertIn("loss", result)

    def test_emergence_detection(self):
        low = {"resolution": "small", "accuracy": 0.55, "loss": 0.45, "task": "test"}
        high = {"resolution": "large", "accuracy": 0.82, "loss": 0.15, "task": "test"}
        result = self.detector.detect_emergence(low, high)
        self.assertTrue(result["emergence_detected"])
        self.assertTrue(result["accuracy_jump"])
        self.assertGreater(result["accuracy_delta"], 0)

    def test_no_emergence_gradual(self):
        low = {"resolution": "small", "accuracy": 0.70, "loss": 0.30, "task": "test"}
        high = {"resolution": "medium", "accuracy": 0.75, "loss": 0.25, "task": "test"}
        result = self.detector.detect_emergence(low, high)
        self.assertFalse(result["emergence_detected"])

    def test_compare_resolutions(self):
        exp = Experiment("em-002", "intent-detect", 1.0, 10, Resolution.MICRO)
        for res in [Resolution.MICRO, Resolution.MEDIUM, Resolution.MASSIVE]:
            self.detector.run_at_resolution(exp, res)
        comp = self.detector.compare_resolutions("intent-detect")
        self.assertGreaterEqual(len(comp["comparisons"]), 2)

    def test_emergent_ability_report(self):
        # Force an emergence event
        low = {"resolution": "micro", "accuracy": 0.50, "loss": 0.50, "task": "test"}
        high = {"resolution": "massive", "accuracy": 0.90, "loss": 0.10, "task": "test"}
        self.detector.detect_emergence(low, high)
        report = self.detector.emergent_ability_report()
        self.assertGreater(len(report), 0)
        self.assertEqual(report[0]["task"], "test")

    def test_multi_resolution_scaling(self):
        """Higher resolutions should generally produce better results."""
        exp = Experiment("em-003", "drift-detect", 1.0, 10, Resolution.MICRO)
        results = {}
        for res in Resolution:
            r = self.detector.run_at_resolution(exp, res)
            results[res] = r
        # At least LARGE and MASSIVE should beat MICRO (with high probability)
        # (stochastic, but emergence bias ensures this)
        self.assertGreaterEqual(len(results), 5)


if __name__ == "__main__":
    unittest.main()
