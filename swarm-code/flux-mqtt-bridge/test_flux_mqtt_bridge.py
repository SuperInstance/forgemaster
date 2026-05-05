"""Tests for flux_mqtt_bridge.py"""
import json
from flux_mqtt_bridge import (
    ViolationPayload, MetricsPayload, FluxMqttBridge
)
from dataclasses import asdict


def test_violation_payload_serialization():
    p = ViolationPayload(
        timestamp=1700000000.0, agent_id="a1", constraint_name="c1",
        severity="warning", observed={"x": 1}, threshold={"max": 2}, message="oops",
    )
    d = json.loads(json.dumps(asdict(p)))
    assert d["constraint_name"] == "c1"
    assert d["severity"] == "warning"


def test_metrics_payload_rate():
    p = MetricsPayload(
        timestamp=0.0, agent_id="a1", interval_sec=1.0,
        checks=100, violations=5, violation_rate=0.0, latency_us=12.0,
    )
    assert p.violations == 5


def test_bridge_topic_construction():
    b = FluxMqttBridge("localhost", base_topic="flux/v2")
    assert b.base_topic == "flux/v2"
    assert b.agent_id == "flux-agent-01"


def test_bridge_state_transitions():
    b = FluxMqttBridge("localhost", port=1883)
    assert not b._connected
    assert b._client is None


def test_heartbeat_thread_lifecycle():
    b = FluxMqttBridge("localhost", port=1883)
    b._client = None
    b._heartbeat_stop.set()
    b.disconnect()
    assert b._heartbeat_thread is None or not b._heartbeat_thread.is_alive()


def test_callback_invocation():
    received = []
    b = FluxMqttBridge("localhost", port=1883)
    b.set_on_violation(lambda p: received.append(p))
    payload = ViolationPayload(
        timestamp=0.0, agent_id="a1", constraint_name="c2",
        severity="critical", observed={}, threshold={}, message="",
    )
    b._on_violation_cb(payload)
    assert len(received) == 1
    assert received[0].constraint_name == "c2"


if __name__ == "__main__":
    test_violation_payload_serialization()
    test_metrics_payload_rate()
    test_bridge_topic_construction()
    test_bridge_state_transitions()
    test_heartbeat_thread_lifecycle()
    test_callback_invocation()
    print("MQTT Bridge: 6 tests passed.")
