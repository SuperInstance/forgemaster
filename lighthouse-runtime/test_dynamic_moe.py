#!/usr/bin/env python3
"""
Test dynamic MoE routing in ExpertRouter + Lighthouse orient().

Tests:
  1. Create router with 5 custom routes
  2. orient() returns correct model for each task type
  3. Fallback for unknown task types
  4. Learned routing via embeddings
  5. add_route / remove_route / list_routes
  6. Integration with lighthouse.orient()
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path

# Add lighthouse-runtime to path
sys.path.insert(0, str(Path(__file__).parent))

from expert_router import ExpertRouter


def test_basic_routing():
    """Test that orient() returns correct model for known task types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Path(tmpdir) / "router_config.json"
        router = ExpertRouter(config_path=config)
        
        # Register 5 routes
        router.add_route("math", "deepseek")
        router.add_route("code", "glm")
        router.add_route("analysis", "seed")
        router.add_route("adversarial", "hermes")
        router.add_route("synthesis", "claude")
        
        # Test each route
        result = router.orient("solve equation", "math")
        assert result["model"] == "deepseek", f"Expected deepseek, got {result['model']}"
        assert result["routing_method"] == "static"
        
        result = router.orient("build module", "code")
        assert result["model"] == "glm", f"Expected glm, got {result['model']}"
        
        result = router.orient("analyze data", "analysis")
        assert result["model"] == "seed", f"Expected seed, got {result['model']}"
        
        result = router.orient("red team this", "adversarial")
        assert result["model"] == "hermes", f"Expected hermes, got {result['model']}"
        
        result = router.orient("synthesize findings", "synthesis")
        assert result["model"] == "claude", f"Expected claude, got {result['model']}"
        
        print("  ✅ Basic routing: all 5 task types route correctly")


def test_fallback():
    """Test fallback to default model for unknown task types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Path(tmpdir) / "router_config.json"
        router = ExpertRouter(config_path=config)
        
        # Unknown task type should fall back to seed (default)
        result = router.orient("do something weird", "quantum_genomics")
        assert result["model"] == "seed", f"Expected seed fallback, got {result['model']}"
        assert result["routing_method"] == "fallback"
        assert result["fallback_used"] is True
        
        # Override fallback
        router.set_fallback("deepseek")
        result = router.orient("still unknown", "mars_rover_navigation")
        assert result["model"] == "deepseek"
        
        print("  ✅ Fallback: unknown task types route to default model")


def test_learned_routing():
    """Test that embeddings enable learned routing that overrides static."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Path(tmpdir) / "router_config.json"
        router = ExpertRouter(config_path=config)
        
        router.add_route("code", "glm")
        
        # First call with embedding: static route wins, but learned route is recorded
        emb = [0.1, 0.2, 0.3, 0.4]
        result = router.orient("refactor module", "code", embedding=emb)
        assert result["model"] == "glm"
        assert result["routing_method"] == "static"
        
        # Second call with same embedding: learned route should now match
        result = router.orient("refactor module v2", "code", embedding=emb)
        assert result["model"] == "glm"
        assert result["routing_method"] == "learned"
        
        # Different embedding, same task_type: static route again
        emb2 = [0.9, 0.8, 0.7, 0.6]
        result = router.orient("new refactor", "code", embedding=emb2)
        assert result["routing_method"] == "static"  # new embedding, not learned yet
        
        print("  ✅ Learned routing: embeddings enable learned route lookup")


def test_add_remove_list():
    """Test add_route, remove_route, list_routes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Path(tmpdir) / "router_config.json"
        router = ExpertRouter(config_path=config)
        
        router.add_route("math", "deepseek")
        router.add_route("code", "glm")
        
        routes = router.list_routes()
        assert routes["static_routes"]["math"] == "deepseek"
        assert routes["static_routes"]["code"] == "glm"
        assert routes["fallback"] == "seed"
        
        # Remove a route
        removed = router.remove_route("math")
        assert removed is True
        
        removed = router.remove_route("nonexistent")
        assert removed is False
        
        # Verify removed
        routes = router.list_routes()
        assert "math" not in routes["static_routes"]
        assert "code" in routes["static_routes"]
        
        # Fallback kicks in for removed route
        result = router.orient("solve", "math")
        assert result["model"] == "seed"
        assert result["routing_method"] == "fallback"
        
        print("  ✅ Add/remove/list: route management works correctly")


def test_config_persistence():
    """Test that routes persist across router instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Path(tmpdir) / "router_config.json"
        
        # Create router, add routes
        r1 = ExpertRouter(config_path=config)
        r1.add_route("math", "deepseek")
        r1.add_route("code", "glm")
        r1.clear_learned()
        
        # Create new router from same config
        r2 = ExpertRouter(config_path=config)
        result = r2.orient("solve", "math")
        assert result["model"] == "deepseek"
        
        result = r2.orient("build", "code")
        assert result["model"] == "glm"
        
        print("  ✅ Config persistence: routes survive restart")


def test_lighthouse_orient_integration():
    """Test that lighthouse.orient() uses ExpertRouter under the hood."""
    # Import lighthouse (it imports ExpertRouter)
    import lighthouse
    
    # Reset global router so it picks up our routes
    lighthouse._router = None
    router = lighthouse._get_router()
    
    # Add our test routes
    router.add_route("math", "deepseek")
    router.add_route("code", "glm")
    
    # Call lighthouse orient — should use ExpertRouter
    result = lighthouse.orient("solve equation", "math")
    assert result["model"] == "deepseek", f"Expected deepseek, got {result['model']}"
    assert "routing_method" in result
    assert result["routing_method"] == "static"
    
    result = lighthouse.orient("build module", "code")
    assert result["model"] == "glm"
    
    # Unknown type → fallback
    result = lighthouse.orient("unknown task", "quantum_genomics")
    assert result["model"] == "seed"
    assert result["routing_method"] == "fallback"
    
    # With embedding
    result = lighthouse.orient("refactor", "code", embedding=[0.5, 0.5])
    assert result["model"] == "glm"
    
    print("  ✅ Lighthouse integration: orient() uses ExpertRouter")
    
    # Clean up created rooms
    lighthouse_dir = Path(__file__).parent / "state" / "agents"
    if lighthouse_dir.exists():
        for d in lighthouse_dir.iterdir():
            if d.is_dir() and d.name.startswith("agent-"):
                shutil.rmtree(d, ignore_errors=True)


def test_cost_estimates():
    """Test that cost estimates are returned correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Path(tmpdir) / "router_config.json"
        router = ExpertRouter(config_path=config)
        
        router.add_route("math", "deepseek")
        router.add_route("synthesis", "claude")
        router.add_route("discovery", "seed")
        
        r1 = router.orient("solve", "math")
        assert r1["cost_estimate"] == 0.2  # deepseek
        
        r2 = router.orient("think big", "synthesis")
        assert r2["cost_estimate"] == 50.0  # claude
        
        r3 = router.orient("explore", "discovery")
        assert r3["cost_estimate"] == 0.1  # seed
        
        print("  ✅ Cost estimates: correct per-model costs")


if __name__ == "__main__":
    print("\n🧪 Testing Dynamic MoE Routing\n")
    
    test_basic_routing()
    test_fallback()
    test_learned_routing()
    test_add_remove_list()
    test_config_persistence()
    test_lighthouse_orient_integration()
    test_cost_estimates()
    
    print("\n✅ All 7 tests passed\n")
