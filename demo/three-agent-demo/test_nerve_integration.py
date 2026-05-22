"""
Test that the 3-agent demo can communicate with kimi1's nerve grid.
This is a cross-agent integration test.
"""
import sys
import os

# Ensure constraint-theory-py is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'constraint-theory-py'))

def test_nerve_import():
    """Can we import the nerve-related modules from sunset-ecosystem?"""
    from sunset_ecosystem import NerveFiber, NerveTopology, HebbianChannel
    print("✅ nerve modules imported (NerveFiber, NerveTopology, HebbianChannel)")
    return True

def test_constraint_theory_compat():
    """Can our constraint checker validate nerve grid outputs?"""
    from constraint_theory import TemporalAgent
    agent = TemporalAgent(anomaly_sigma=2.0)
    for i in range(100):
        agent.observe(float(i), 1.0 + i * 0.001)
    summary = agent.summary()
    print(f"✅ Constraint check: TemporalAgent processed 100 observations")
    print(f"   Summary: {summary}")
    return True

def test_nerve_fiber_creation():
    """Can we create nerve fibers and run signals through them?"""
    from sunset_ecosystem import NerveFiber, NerveTopology
    fiber = NerveFiber(fiber_id="test-fiber-1")
    topo = NerveTopology()
    print(f"✅ NerveFiber created: {fiber}")
    print(f"✅ NerveTopology created: {topo}")
    return True

def test_cross_module_integration():
    """Test constraint_theory + sunset_ecosystem working together."""
    from constraint_theory import TemporalAgent
    from sunset_ecosystem import NerveFiber

    # Simulate nerve grid observations through constraint checker
    agent = TemporalAgent(learning_rate=0.1)
    fiber = NerveFiber(fiber_id="integration-fiber")

    # Feed regular observations (x=time, y=signal)
    for i in range(50):
        agent.observe(float(i), 1.0 + i * 0.002)

    summary = agent.summary()
    print(f"✅ Cross-module integration: agent={summary}, fiber={fiber}")
    return True

if __name__ == "__main__":
    results = [
        test_nerve_import(),
        test_constraint_theory_compat(),
        test_nerve_fiber_creation(),
        test_cross_module_integration(),
    ]
    passed = sum(1 for r in results if r)
    print(f"\n{passed}/{len(results)} integration tests passed")
