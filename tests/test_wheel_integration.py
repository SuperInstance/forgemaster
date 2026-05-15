#!/usr/bin/env python3
"""
Integration tests for the Wheel of Improvements.

Tests:
1. GL9 → health → router → MCP round trip
2. Conservation monitoring affects routing decisions
3. Hebbian flow events from all services
4. GL9 consensus in MythosPipeline
"""
import sys, os, time, json, math, threading

# Ensure workspace is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from gl9_consensus import (
    GL9HolonomyConsensus, GL9Agent, GL9ConsensusResult,
    IntentVector, GL9Matrix, DEFAULT_TOLERANCE,
)
from fleet_unified_health import (
    GL9AlignmentTracker, BehavioralHealth, StructuralHealth,
    ConservationMonitor, HealthEndpoint,
)
from fleet_router_api import (
    CriticalAngleRouter, ModelRegistry, RoutingStats, ModelTierEnum,
    create_app,
)
from mythos_tile import MythosTile, MythosPipeline, ModelTier
from fleet_hebbian_service import FleetHebbianService
from mcp_plato_adapter import MCPHandler

# ──────────────────────────────────────────────────────────────
passed = 0
failed = 0

def _assert(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}  {detail}")


# ──────────────────────────────────────────────────────────────
# 1. GL9 → Health → Router round trip
# ──────────────────────────────────────────────────────────────
print("\n=== 1. GL9 → Health → Router Round Trip ===")

# 1a. Build a GL9 consensus with aligned agents
gl9 = GL9HolonomyConsensus(tolerance=0.5)
for i in range(5):
    iv = IntentVector([0.3 + i * 0.01] * 9)  # similar intents
    agent = GL9Agent(
        id=i, intent=iv, transform=GL9Matrix.identity(),
        neighbors=[j for j in range(5) if j != i],
    )
    gl9.add_agent(agent)

result = gl9.check_consensus()
_assert("GL9 consensus reached", result.consensus, f"dev={result.deviation}")
_assert("GL9 alignment high", result.alignment > 0.9, f"align={result.alignment}")

# 1b. Feed alignment into health tracker
tracker = GL9AlignmentTracker()
for i in range(5):
    tracker.record_intent(f"agent-{i}", [0.3 + i * 0.01] * 9)

align_report = tracker.compute_alignment()
_assert("Health tracker sees aligned agents", align_report["alignment"] > 0.9,
        f"align={align_report.get('alignment')}")
_assert("Health tracker consensus", align_report.get("consensus", True))

# 1c. Feed health state into router
registry = ModelRegistry()
registry.register("ByteDance/Seed-2.0-mini", ModelTierEnum.TIER_1_DIRECT)
registry.register("Qwen/Qwen3-235B-A22B-Instruct-2507", ModelTierEnum.TIER_2_SCAFFOLDED)
stats = RoutingStats()
router = CriticalAngleRouter(registry, stats, hebbian_url="http://localhost:99999")

# Set healthy conservation state
router.set_conservation_state(compliance_rate=0.95, alignment_score=0.95)
route = router.route_request("eisenstein_norm", {"a": 3, "b": 5})
_assert("Healthy route succeeds", not route["rejected"])
_assert("Healthy route picks Tier 1", route["tier"] == 1, f"got tier={route['tier']}")
_assert("Route includes compliance", "conservation_compliance" in route)
_assert("Route compliance high", route["conservation_compliance"] >= 0.85)
_assert("Route cross_consultation False (aligned)", not route["cross_consultation"])

# 1d. MCP adapter uses CriticalAngleRouter
handler = MCPHandler(
    plato_url="http://localhost:8848",
    hebbian_url="http://localhost:8849",
)
_assert("MCP handler has fleet_route tool", "fleet_route" in handler.tools)
fleet_route_tool = handler.tools["fleet_route"]
_assert("MCP fleet_route has CriticalAngleRouter",
        fleet_route_tool._critical_angle_router is not None)

# Execute MCP fleet_route
mcp_result = fleet_route_tool.execute("Compute Eisenstein norm of a=3, b=5")
_assert("MCP fleet_route returns result", mcp_result.get("recommended_model") is not None)
_assert("MCP fleet_route uses CriticalAngleRouter", mcp_result.get("router") == "CriticalAngleRouter")

# JSON-RPC round trip
rpc_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "fleet_route",
        "arguments": {"computation": "a^2 - a*b + b^2 where a=3, b=5"},
    },
}
rpc_response = handler.handle_request(rpc_request)
_assert("JSON-RPC returns result", "result" in rpc_response)
rpc_content = json.loads(rpc_response["result"]["content"][0]["text"])
_assert("JSON-RPC route not rejected", not rpc_content.get("rejected", True))


# ──────────────────────────────────────────────────────────────
# 2. Conservation monitoring affects routing
# ──────────────────────────────────────────────────────────────
print("\n=== 2. Conservation-Aware Routing ===")

# 2a. High compliance → all tiers available
router2 = CriticalAngleRouter(ModelRegistry(), RoutingStats())
for mid, tier in [
    ("Seed-mini", ModelTierEnum.TIER_1_DIRECT),
    ("Qwen-235B", ModelTierEnum.TIER_2_SCAFFOLDED),
    ("BadModel", ModelTierEnum.TIER_3_INCOMPETENT),
]:
    router2.registry.register(mid, tier)

router2.set_conservation_state(compliance_rate=0.95)
route_high = router2.route_request("generic", {"expression": "test"})
_assert("High compliance routes normally", not route_high["rejected"])

# 2b. Low compliance → only Tier 1 models
router2.set_conservation_state(compliance_rate=0.50)
route_low = router2.route_request("generic", {"expression": "test"})
_assert("Low compliance still routes", not route_low.get("rejected", True))
_assert("Low compliance picks Tier 1", route_low.get("tier") == 1,
        f"got tier={route_low.get('tier')}")
_assert("Low compliance shows compliance", route_low.get("conservation_compliance", 0) < 0.85)

# 2c. Explicitly request Tier 2 when compliance is low
route_explicit = router2.route_request(
    "generic", {"expression": "test"},
    preferred_model="Qwen-235B",
)
_assert("Low compliance filters Tier 2", route_explicit.get("downgraded", False),
        f"reason={route_explicit.get('routing_reason')}")

# 2d. Low alignment triggers cross-consultation flag
router2.set_conservation_state(compliance_rate=0.95, alignment_score=0.50)
route_align = router2.route_request("generic", {"expression": "test"})
_assert("Low alignment triggers cross_consultation", route_align.get("cross_consultation"))


# ──────────────────────────────────────────────────────────────
# 3. Hebbian flow events from all services
# ──────────────────────────────────────────────────────────────
print("\n=== 3. Hebbian Flow Events ===")

# 3a. FleetHebbianService emits flow events on tile submission
import fleet_hebbian_service as fhs

svc = FleetHebbianService.__new__(FleetHebbianService)
svc.port = 99999
svc._rooms = ["room-a", "room-b", "room-c"]
svc._room_index = {"room-a": 0, "room-b": 1, "room-c": 2}
svc._room_domains = {"room-a": "test", "room-b": "test", "room-c": "test"}
svc.tracker = fhs.TileFlowTracker()
svc.kernel = fhs.ConservationHebbianKernel(n_rooms=3)
svc.stage_classifier = fhs.EmergentStageClassifier()
svc.cluster_detector = fhs.RoomClusterDetector()
svc.router = fhs.HebbianRouter(
    svc.tracker, svc._rooms, svc._room_index, svc.kernel
)
svc._recent_flow = __import__('collections').deque(maxlen=500)
svc._lock = threading.Lock()
svc._running = False
svc._http_server = None
svc.persist_dir = "/tmp/test-hebbian"

result_hebbian = svc.submit_tile(
    tile_type="model",
    source_room="room-a",
    dest_room="room-b",
    confidence=0.9,
)
_assert("Hebbian tile submission routed", result_hebbian["total_routed"] >= 1)
_assert("Hebbian flow events logged", len(svc._recent_flow) >= 1)

flow_event = list(svc._recent_flow)[0]
_assert("Flow event has source", flow_event["source"] == "room-a")
_assert("Flow event has dest", flow_event["dest"] == "room-b")
_assert("Flow event has conservation", flow_event.get("conserved") is not None)

# 3b. MythosPipeline track_hebbian produces hebbian events
pipe = MythosPipeline()
tile1 = pipe.accept_expert_output("expert-1", {
    "domain": "math", "output": "result=7", "confidence": 0.9, "tags": ["eisenstein"]
})
hebbian_event = pipe.track_hebbian(tile1)
_assert("MythosPipeline Hebbian event has source_room", "source_room" in hebbian_event)
_assert("MythosPipeline Hebbian event has domain", hebbian_event.get("domain") == "math")

# 3c. MythosTile.to_hebbian_event() works
tile2 = MythosTile(domain="test", source="forgemaster", content="test", room="forge")
hevt = tile2.to_hebbian_event()
_assert("MythosTile hebbian event has tile_id", "tile_id" in hevt)
_assert("MythosTile hebbian event has domain", hevt["domain"] == "test")


# ──────────────────────────────────────────────────────────────
# 4. GL9 consensus in MythosPipeline
# ──────────────────────────────────────────────────────────────
print("\n=== 4. GL9 Consensus in MythosPipeline ===")

# 4a. Pipeline with aligned experts → consensus
pipe2 = MythosPipeline()
for i in range(4):
    pipe2.accept_expert_output(f"expert-{i}", {
        "domain": "math", "output": f"result={7+i*0.01}",
        "confidence": 0.85 + i * 0.02,
        "tags": ["eisenstein", "norm"],
    })

consensus = pipe2.check_gl9_consensus()
_assert("GL9 consensus result has alignment", "alignment" in consensus)
_assert("GL9 consensus result has faulty_experts", "faulty_experts" in consensus)
_assert("GL9 consensus expert_count", consensus["expert_count"] == 4)

# 4b. Aligned experts should reach consensus
_assert("Aligned experts reach consensus", consensus["consensus"],
        f"align={consensus.get('alignment')}, dev={consensus.get('deviation')}")

# 4c. Divergent expert → potential misalignment
pipe3 = MythosPipeline()
# 3 aligned experts
for i in range(3):
    pipe3.accept_expert_output(f"good-expert-{i}", {
        "domain": "math", "output": "result=7",
        "confidence": 0.9, "tags": ["eisenstein"],
    })
# 1 divergent expert (different domain, low confidence)
pipe3.accept_expert_output("rogue-expert", {
    "domain": "totally-different-domain-with-long-name",
    "output": "WRONG ANSWER",
    "confidence": 0.1,
    "tags": ["unrelated", "bad"],
})

consensus3 = pipe3.check_gl9_consensus()
_assert("Divergent pipeline has alignment < 1.0", consensus3["alignment"] < 1.0,
        f"align={consensus3['alignment']}")

# 4d. Single expert → trivial consensus
pipe_single = MythosPipeline()
pipe_single.accept_expert_output("solo", {
    "domain": "math", "output": "42", "confidence": 0.95,
})
consensus_single = pipe_single.check_gl9_consensus()
_assert("Single expert trivially consensual", consensus_single["consensus"])
_assert("Single expert alignment = 1.0", consensus_single["alignment"] == 1.0)

# 4e. Zero experts
pipe_empty = MythosPipeline()
consensus_empty = pipe_empty.check_gl9_consensus()
_assert("Empty pipeline trivially consensual", consensus_empty["consensus"])


# ──────────────────────────────────────────────────────────────
# 5. Full wheel integration: health → router → MCP
# ──────────────────────────────────────────────────────────────
print("\n=== 5. Full Wheel Integration ===")

# Build a health endpoint (no HTTP server, just the logic)
health = HealthEndpoint.__new__(HealthEndpoint)
health.port = 99999
health.structural = StructuralHealth("localhost", 99999)  # unreachable, that's fine
health.behavioral = BehavioralHealth()
health.gl9_alignment = GL9AlignmentTracker()
health.conservation_monitor = ConservationMonitor()
health.diagnostics = None
health._running = False
health._http_server = None
health._last_report = None
health._lock = threading.Lock()

# Record some behavioral data
health.behavioral.record_query("Seed-2.0-mini", correct=True, tier=1, provider="deepinfra")
health.behavioral.record_query("Seed-2.0-mini", correct=True, tier=1, provider="deepinfra")
health.behavioral.record_query("Qwen3-235B", correct=False, tier=2, provider="deepinfra")

# Record GL9 intents
health.gl9_alignment.record_intent("forgemaster", [0.5, 0.3, 0.4, 0.9, 0.2, 0.1, 0.8, 0.3, 0.7])
health.gl9_alignment.record_intent("oracle1", [0.5, 0.3, 0.4, 0.9, 0.2, 0.1, 0.8, 0.3, 0.7])
health.gl9_alignment.record_intent("captain", [0.5, 0.3, 0.4, 0.9, 0.2, 0.1, 0.8, 0.3, 0.7])

# Record conservation deviation
health.conservation_monitor.record(0.01)
health.conservation_monitor.record(0.015)
health.conservation_monitor.record(0.012)

# Build report
report = health.build_report()
_assert("Health report has overall_score", "overall_score" in report.to_dict())
_assert("Health report has structural", "structural" in report.to_dict())
_assert("Health report has behavioral", "behavioral" in report.to_dict())
_assert("Health report has GL9 diagnostics", "gl9_alignment" in (report.diagnostics or {}))

# Feed health into router
reg = ModelRegistry()
for mid, tier in [
    ("Seed-mini", ModelTierEnum.TIER_1_DIRECT),
    ("Qwen-235B", ModelTierEnum.TIER_2_SCAFFOLDED),
]:
    reg.register(mid, tier)

rtr = CriticalAngleRouter(reg, RoutingStats())
gl9_align = report.diagnostics["gl9_alignment"]["alignment"]
rtr.set_conservation_state(
    compliance_rate=report.structural.get("compliance_rate", 1.0),
    alignment_score=gl9_align,
)
route_final = rtr.route_request("eisenstein_norm", {"a": 3, "b": 5})
_assert("Full wheel route succeeds", not route_final["rejected"])
_assert("Full wheel route includes compliance", "conservation_compliance" in route_final)
_assert("Full wheel route includes alignment", "alignment_score" in route_final)

# Test alignment endpoint behavior
align_data = health.gl9_alignment.compute_alignment()
_assert("Alignment endpoint returns aligned", align_data["status"] == "aligned")
_assert("Alignment endpoint has agents_tracked", align_data["agents_tracked"] == 3)

# Test misaligned agents
health.gl9_alignment.record_intent("rogue", [0.99, 0.01, 0.99, 0.01, 0.99, 0.01, 0.99, 0.01, 0.99])
align_rogue = health.gl9_alignment.compute_alignment()
_assert("Rogue agent reduces alignment", align_rogue["alignment"] < gl9_align,
        f"before={gl9_align}, after={align_rogue['alignment']}")


# ──────────────────────────────────────────────────────────────
# 6. Extra edge cases
# ──────────────────────────────────────────────────────────────
print("\n=== 6. Edge Cases ===")

# 6a. Router with no models registered
empty_reg = ModelRegistry()
empty_stats = RoutingStats()
empty_router = CriticalAngleRouter(empty_reg, empty_stats)
empty_route = empty_router.route_request("generic", {"expression": "test"})
_assert("Empty registry rejects route", empty_route["rejected"])

# 6b. GL9 with 1 agent (trivial)
single_gl9 = GL9HolonomyConsensus(tolerance=0.5)
single_gl9.add_agent(GL9Agent(0, IntentVector.uniform(), GL9Matrix.identity(), []))
single_result = single_gl9.check_consensus()
_assert("Single agent trivially consensual", single_result.consensus)
_assert("Single agent alignment 1.0", single_result.alignment == 1.0)

# 6c. Conservation monitor with few samples
cm = ConservationMonitor(min_samples=10)
for i in range(5):
    cm.record(0.01 * i)
trend = cm.analyze()
_assert("Conservation trend insufficient_data", trend.direction == "insufficient_data")

# 6d. MythosTile format_for_model across tiers
t = MythosTile(
    domain="math", source="test", content="Compute f(a,b)",
    confidence=0.9, activation_key="Eisenstein norm",
)
_assert("Tier 1 passthrough", t.format_for_model(ModelTier(1)) == "Compute f(a,b)")
_assert("Tier 2 scaffolding", "Eisenstein" in t.format_for_model(ModelTier(2)))
_assert("Tier 3 fallback", "Compute" in t.format_for_model(ModelTier(3)))


# ──────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed:
    print("❌ SOME TESTS FAILED")
    sys.exit(1)
else:
    print("✅ ALL TESTS PASSED")
