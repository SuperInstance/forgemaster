#!/usr/bin/env python3
"""Tests for Fleet Router API — 30 tests covering all endpoints and routing logic.

Run:
  python -m pytest tests/test_fleet_router_api.py -v
  # or directly:
  python tests/test_fleet_router_api.py
"""

import sys
import os
import time

# Ensure workspace is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from fleet_router_api import (
    create_app,
    ModelRegistry,
    ModelTierEnum,
    RoutingStats,
    CriticalAngleRouter,
    DEFAULT_MODELS,
    TIER_ACCURACY,
    TIER_TO_STAGE,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def assert_eq(name, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got:      {got!r}\n     expected: {expected!r}")


def assert_true(name, got):
    global passed, failed
    if got:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}")


def assert_contains(name, got, substring):
    global passed, failed
    if substring in got:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     missing: {substring!r}")


def assert_not_contains(name, got, substring):
    global passed, failed
    if substring not in got:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     unexpected: {substring!r}")


def assert_gte(name, got, threshold):
    global passed, failed
    if got >= threshold:
        passed += 1
        print(f"  ✅ {name} ({got} >= {threshold})")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r} < {threshold!r}")


def assert_key(name, d, key):
    global passed, failed
    if key in d:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     keys: {list(d.keys())}")


# =========================================================================
# Model Registry Tests (8 tests)
# =========================================================================

def test_registry():
    print("\n=== Model Registry ===")

    reg = ModelRegistry()
    entry = reg.register("test-model-1", ModelTierEnum.TIER_1_DIRECT)
    assert_eq("register returns entry", entry.model_id, "test-model-1")
    assert_eq("register tier", entry.tier, ModelTierEnum.TIER_1_DIRECT)

    # Get registered model
    got = reg.get("test-model-1")
    assert_true("get returns entry", got is not None)
    assert_eq("get tier", reg.get_tier("test-model-1"), ModelTierEnum.TIER_1_DIRECT)

    # Unknown model defaults to Tier 3
    assert_eq("unknown model tier", reg.get_tier("nonexistent"), ModelTierEnum.TIER_3_INCOMPETENT)

    # Register Tier 2 model
    reg.register("test-model-2", ModelTierEnum.TIER_2_SCAFFOLDED)
    reg.register("test-model-3", ModelTierEnum.TIER_3_INCOMPETENT)

    # Find best: prefers Tier 1
    best = reg.find_best(ModelTierEnum.TIER_1_DIRECT)
    assert_true("find best returns entry", best is not None)
    assert_eq("find best tier", best.tier, ModelTierEnum.TIER_1_DIRECT)

    # Set unavailable and find best skips it
    reg.set_available("test-model-1", False)
    best2 = reg.find_best(ModelTierEnum.TIER_1_DIRECT)
    assert_true("find best skips unavailable", best2 is None or best2.model_id != "test-model-1")

    # List models
    models = reg.list_models()
    assert_eq("list models count", len(models), 3)
    assert_eq("list models[0] has tier", models[0]["tier"], 1)


# =========================================================================
# Routing Stats Tests (4 tests)
# =========================================================================

def test_stats():
    print("\n=== Routing Stats ===")

    stats = RoutingStats()
    stats.record("model-a", ModelTierEnum.TIER_1_DIRECT, "eisenstein_norm")
    stats.record("model-b", ModelTierEnum.TIER_2_SCAFFOLDED, "mobius", downgraded=True)
    stats.record("model-a", ModelTierEnum.TIER_1_DIRECT, "legendre")

    snap = stats.snapshot()
    assert_eq("total requests", snap["total_requests"], 3)
    assert_eq("tier_1 count", snap["tier_distribution"].get("tier_1", 0), 2)
    assert_eq("downgrade count", snap["downgrade_count"], 1)
    # uptime could be 0.0 if computed instantly
    assert_true("uptime >= 0", snap["uptime_seconds"] >= 0)


# =========================================================================
# Critical Angle Router Tests (10 tests)
# =========================================================================

def test_router():
    print("\n=== Critical Angle Router ===")

    registry = ModelRegistry()
    registry.register("Seed-2.0-mini", ModelTierEnum.TIER_1_DIRECT)
    registry.register("Qwen3-235B", ModelTierEnum.TIER_2_SCAFFOLDED)
    registry.register("qwen3:0.6b", ModelTierEnum.TIER_3_INCOMPETENT)

    stats = RoutingStats()
    router = CriticalAngleRouter(registry, stats, hebbian_url="http://localhost:99999")

    # 1. Auto-select routes to Tier 1
    result = router.route_request("eisenstein_norm", {"a": 3, "b": 5})
    assert_eq("auto-select model", result["model_id"], "Seed-2.0-mini")
    assert_eq("auto-select tier", result["tier"], 1)
    assert_true("auto-select not rejected", not result["rejected"])
    assert_contains("auto-select reason", result["routing_reason"], "Auto-selected")

    # 2. Explicit Tier 1 model
    result = router.route_request("mobius", {"n": 30}, preferred_model="Seed-2.0-mini")
    assert_eq("explicit model", result["model_id"], "Seed-2.0-mini")
    assert_true("has translated prompt", result["translated_prompt"] is not None)

    # 3. Explicit Tier 2 model — gets scaffolded prompt
    result = router.route_request("eisenstein_norm", {"a": 2, "b": 3}, preferred_model="Qwen3-235B")
    assert_eq("tier 2 model", result["model_id"], "Qwen3-235B")
    assert_eq("tier 2 tier", result["tier"], 2)

    # 4. Tier 3 model auto-upgrades
    result = router.route_request("legendre", {"a": 2, "p": 7}, preferred_model="qwen3:0.6b")
    # Should auto-upgrade to a Tier 1/2 model
    assert_true("tier 3 auto-upgrade", result["model_id"] != "qwen3:0.6b")
    assert_true("tier 3 not rejected", not result.get("rejected"))

    # 5. Auto-downgrade when model unavailable
    registry.set_available("Seed-2.0-mini", False)
    result = router.route_request("mobius", {"n": 30}, preferred_model="Seed-2.0-mini")
    assert_true("downgrade happened", result["downgraded"])
    assert_eq("downgrade target", result["model_id"], "Qwen3-235B")
    registry.set_available("Seed-2.0-mini", True)  # restore

    # 6. Force tier 3 → rejection
    result = router.route_request("mobius", {"n": 30}, force_tier=3)
    assert_true("force tier 3 rejected", result["rejected"])
    assert_contains("force tier 3 reason", result["routing_reason"], "rejected")

    # 7. Generic task type
    result = router.route_request("generic", {"expression": "2+2"})
    assert_true("generic routed", result["model_id"] is not None)

    # 8. Accuracy estimation
    result = router.route_request("eisenstein_norm", {"a": 1, "b": 1}, preferred_model="Seed-2.0-mini")
    assert_true("accuracy > 0", result["estimated_accuracy"] > 0)

    # 9. All task types route
    for task in ["eisenstein_norm", "eisenstein_snap", "mobius", "legendre",
                 "modular_inverse", "cyclotomic_eval", "covering_radius"]:
        params = {"a": 3, "b": 5, "n": 6, "p": 7, "m": 11, "x": 1.5, "y": 2.0}
        result = router.route_request(task, params)
        assert_true(f"task {task} routed", result["model_id"] is not None and not result.get("rejected"))

    # 10. Batch routing
    batch = router.route_batch([
        {"task_type": "eisenstein_norm", "params": {"a": 1, "b": 2}},
        {"task_type": "mobius", "params": {"n": 30}},
        {"task_type": "legendre", "params": {"a": 2, "p": 7}},
    ])
    assert_eq("batch total", batch["total"], 3)
    assert_eq("batch routed", batch["routed"], 3)
    assert_eq("batch rejected", batch["rejected"], 0)
    assert_true("batch has groups", len(batch["groups"]) > 0)


# =========================================================================
# FastAPI Endpoint Tests (12 tests)
# =========================================================================

def test_api():
    print("\n=== FastAPI Endpoints ===")

    app = create_app(hebbian_url="http://localhost:99999")
    client = TestClient(app)

    # 1. Health endpoint
    resp = client.get("/health")
    assert_eq("health status", resp.status_code, 200)
    data = resp.json()
    assert_eq("health service", data["service"], "fleet-router-api")
    assert_key("health models_registered", data, "models_registered")
    assert_key("health routing_stats", data, "routing_stats")

    # 2. Models endpoint
    resp = client.get("/models")
    assert_eq("models status", resp.status_code, 200)
    data = resp.json()
    assert_true("models has list", len(data["models"]) > 0)

    # 3. POST /route — single computation
    resp = client.post("/route", json={
        "task_type": "eisenstein_norm",
        "params": {"a": 3, "b": 5},
    })
    assert_eq("route status", resp.status_code, 200)
    data = resp.json()
    assert_key("route model_id", data, "model_id")
    assert_key("route translated_prompt", data, "translated_prompt")
    assert_key("route estimated_accuracy", data, "estimated_accuracy")
    assert_key("route routing_reason", data, "routing_reason")

    # 4. POST /route — with preferred model
    resp = client.post("/route", json={
        "task_type": "mobius",
        "params": {"n": 30},
        "preferred_model": "ByteDance/Seed-2.0-mini",
    })
    assert_eq("route preferred status", resp.status_code, 200)
    data = resp.json()
    assert_eq("route preferred model", data["model_id"], "ByteDance/Seed-2.0-mini")

    # 5. POST /route — force tier 3 → rejection (422)
    resp = client.post("/route", json={
        "task_type": "mobius",
        "params": {"n": 30},
        "force_tier": 3,
    })
    assert_eq("route force tier3 status", resp.status_code, 422)
    data = resp.json()
    assert_true("route force tier3 rejected", data.get("rejected"))

    # 6. POST /route — unavailable model → auto-downgrade
    # First mark model unavailable
    client.post("/models/availability", json={
        "model_id": "ByteDance/Seed-2.0-mini",
        "available": False,
    })
    resp = client.post("/route", json={
        "task_type": "eisenstein_norm",
        "params": {"a": 1, "b": 2},
        "preferred_model": "ByteDance/Seed-2.0-mini",
    })
    assert_eq("route downgrade status", resp.status_code, 200)
    data = resp.json()
    assert_true("route downgrade happened", data.get("downgraded"))
    assert_true("route downgrade new model", data["model_id"] != "ByteDance/Seed-2.0-mini")

    # Restore
    client.post("/models/availability", json={
        "model_id": "ByteDance/Seed-2.0-mini",
        "available": True,
    })

    # 7. POST /route/batch
    resp = client.post("/route/batch", json={
        "items": [
            {"task_type": "eisenstein_norm", "params": {"a": 1, "b": 2}},
            {"task_type": "mobius", "params": {"n": 30}},
            {"task_type": "legendre", "params": {"a": 2, "p": 7}},
            {"task_type": "generic", "params": {"expression": "2+2"}},
        ],
    })
    assert_eq("batch status", resp.status_code, 200)
    data = resp.json()
    assert_eq("batch total", data["total"], 4)
    assert_true("batch has groups", len(data["groups"]) > 0)

    # 8. POST /models/register — new model
    resp = client.post("/models/register", json={
        "model_id": "test/new-model",
        "tier": 2,
        "available": True,
    })
    assert_eq("register status", resp.status_code, 200)
    data = resp.json()
    assert_true("register ok", data["registered"])

    # 9. POST /models/register — invalid tier
    resp = client.post("/models/register", json={
        "model_id": "test/bad-tier",
        "tier": 5,
    })
    assert_true("register invalid tier", resp.status_code in (400, 422))

    # 10. POST /models/availability
    resp = client.post("/models/availability", json={
        "model_id": "test/new-model",
        "available": False,
    })
    assert_eq("availability status", resp.status_code, 200)
    data = resp.json()
    assert_true("availability updated", data["updated"])

    # 11. POST /models/availability — unknown model
    resp = client.post("/models/availability", json={
        "model_id": "nonexistent",
        "available": True,
    })
    assert_eq("availability unknown", resp.status_code, 404)

    # 12. GET /stats
    resp = client.get("/stats")
    assert_eq("stats status", resp.status_code, 200)
    data = resp.json()
    assert_gte("stats total", data["total_requests"], 4)


# =========================================================================
# Tier Classification Tests (4 tests)
# =========================================================================

def test_tier_classification():
    print("\n=== Tier Classification ===")

    # Default models loaded
    assert_eq("Seed tier", DEFAULT_MODELS.get("ByteDance/Seed-2.0-mini"), ModelTierEnum.TIER_1_DIRECT)
    assert_eq("Qwen tier", DEFAULT_MODELS.get("Qwen/Qwen3-235B-A22B-Instruct-2507"), ModelTierEnum.TIER_2_SCAFFOLDED)
    assert_eq("small qwen tier", DEFAULT_MODELS.get("qwen3:0.6b"), ModelTierEnum.TIER_3_INCOMPETENT)

    # Accuracy ranges
    t1_lo, t1_hi = TIER_ACCURACY[ModelTierEnum.TIER_1_DIRECT]
    assert_gte("tier1 accuracy low", t1_lo, 0.94)
    assert_gte("tier1 accuracy high", t1_hi, 1.0)

    t3_lo, t3_hi = TIER_ACCURACY[ModelTierEnum.TIER_3_INCOMPETENT]
    assert_true("tier3 accuracy low", t3_lo < 0.3)


# =========================================================================
# Translation Integration Tests (4 tests)
# =========================================================================

def test_translation():
    print("\n=== Translation Integration ===")

    registry = ModelRegistry()
    registry.register("Seed-2.0-mini", ModelTierEnum.TIER_1_DIRECT)
    registry.register("Hermes-70B", ModelTierEnum.TIER_2_SCAFFOLDED)

    stats = RoutingStats()
    router = CriticalAngleRouter(registry, stats, hebbian_url="http://localhost:99999")

    # Tier 1 prompt: domain vocabulary passes through
    r1 = router.route_request("eisenstein_norm", {"a": 3, "b": 5}, preferred_model="Seed-2.0-mini")
    assert_contains("tier1 has Eisenstein", r1["translated_prompt"], "Eisenstein")

    # Tier 2 prompt: activation key + ASCII notation
    r2 = router.route_request("eisenstein_norm", {"a": 3, "b": 5}, preferred_model="Hermes-70B")
    assert_contains("tier2 has Eisenstein", r2["translated_prompt"], "Eisenstein")

    # Tier 1 accuracy > Tier 2 accuracy
    assert_true("tier1 acc >= tier2 acc", r1["estimated_accuracy"] >= r2["estimated_accuracy"])

    # All task types produce non-empty prompts
    for task in ["eisenstein_norm", "mobius", "legendre", "modular_inverse"]:
        params = {"a": 3, "b": 5, "n": 30, "p": 7, "m": 11, "x": 1.5, "y": 2.0}
        r = router.route_request(task, params)
        prompt = r.get("translated_prompt", "")
        assert_true(f"{task} prompt non-empty", len(prompt) > 0)


# =========================================================================
# Run all tests
# =========================================================================

if __name__ == "__main__":
    print("⚒️  Fleet Router API Tests\n")
    test_registry()
    test_stats()
    test_router()
    test_api()
    test_tier_classification()
    test_translation()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED")
