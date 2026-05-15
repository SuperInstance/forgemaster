#!/usr/bin/env python3
"""
Tests for MCP PLATO Adapter — 15+ tests covering all 6 tools, JSON-RPC protocol,
rate limiting, authentication, and edge cases.

Run:
    python -m pytest tests/test_mcp_plato_adapter.py -v
    # or standalone:
    python tests/test_mcp_plato_adapter.py
"""

import json
import os
import sys
import threading
import time
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from unittest.mock import MagicMock, patch

# Ensure workspace is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_plato_adapter import (
    MCPHandler, MCPPlatoAdapterServer,
    PlatoClient, HebbianClient,
    PlatoQueryTool, PlatoSubmitTool, FleetRouteTool,
    FleetHealthTool, ExpertConsultTool, ConservationCheckTool,
    TokenBucket, ApiKeyAuth,
)


# ---------------------------------------------------------------------------
# Mock servers for integration-like tests
# ---------------------------------------------------------------------------

class MockPLATOHandler(BaseHTTPRequestHandler):
    """Minimal mock PLATO server."""
    def do_GET(self):
        if self.path == "/status":
            self._json({"status": "running", "rooms": 6})
        elif self.path == "/rooms":
            self._json({"rooms": [
                {"name": "forgemaster-local", "domain": "constraint-theory"},
                {"name": "fleet-ops", "domain": "ops"},
            ]})
        elif self.path.startswith("/room/"):
            room = self.path.split("/room/")[1].split("?")[0]
            self._json({"tiles": [
                {"domain": "math", "question": "Eisenstein norm a=3 b=5",
                 "tags": ["eisenstein"], "confidence": 0.95,
                 "_meta": {"room": room}},
            ]})
        else:
            self._json({"tiles": []})

    def do_POST(self):
        if self.path == "/tile":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            self._json({"tile_id": "mock-tile-123", "status": "ok", "room": body.get("room")}, 201)
        else:
            self._json({"error": "not found"}, 404)

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class MockHebbianHandler(BaseHTTPRequestHandler):
    """Minimal mock Hebbian server."""
    def do_GET(self):
        if self.path == "/status":
            self._json({"service": "fleet-hebbian", "status": "running", "rooms": 6})
        elif self.path == "/conservation":
            self._json({
                "n_rooms": 6, "V": 6,
                "update_count": 200,
                "compliance_rate": "95.0%",
                "conservation": {
                    "gamma": 0.15, "H": 1.12,
                    "sum": 1.27, "predicted": 1.28,
                    "deviation": -0.01, "sigma": 0.05,
                    "conserved": True,
                },
            })
        else:
            self._json({})

    def do_POST(self):
        if self.path == "/tile":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            self._json({
                "tile_type": body.get("tile_type"),
                "source_room": body.get("source_room"),
                "tile_hash": "mock-hash",
                "destinations": [],
                "total_routed": 0,
            }, 201)
        elif self.path == "/tile/mythos":
            self._json({"mythos_tile_id": "mock-mythos-123", "total_routed": 0}, 201)
        else:
            self._json({"error": "not found"}, 404)

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _start_mock_server(handler_cls, port):
    """Start a mock HTTP server in a background thread."""
    server = HTTPServer(("127.0.0.1", port), handler_cls)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestTokenBucket(unittest.TestCase):
    """Test rate limiter."""

    def test_consume_within_capacity(self):
        bucket = TokenBucket(rate=10, capacity=5)
        self.assertTrue(bucket.consume(1))

    def test_consume_exhaust(self):
        bucket = TokenBucket(rate=1, capacity=3)
        self.assertTrue(bucket.consume(1))
        self.assertTrue(bucket.consume(1))
        self.assertTrue(bucket.consume(1))
        self.assertFalse(bucket.consume(1))  # exhausted

    def test_refill_over_time(self):
        bucket = TokenBucket(rate=1000, capacity=5)
        bucket.consume(5)
        time.sleep(0.01)  # small wait
        self.assertTrue(bucket.consume(1))  # should have refilled


class TestApiKeyAuth(unittest.TestCase):
    """Test authentication."""

    def test_no_keys_allows_all(self):
        auth = ApiKeyAuth()
        self.assertTrue(auth.check("anything"))
        self.assertTrue(auth.check(None))

    def test_valid_key(self):
        auth = ApiKeyAuth({"secret123", "key456"})
        self.assertTrue(auth.check("secret123"))
        self.assertFalse(auth.check("wrong"))
        self.assertFalse(auth.check(None))


class TestMCPHandlerProtocol(unittest.TestCase):
    """Test JSON-RPC protocol handling."""

    def setUp(self):
        self.handler = MCPHandler(
            plato_url="http://localhost:18848",  # unreachable = ok for protocol tests
            hebbian_url="http://localhost:18849",
        )

    def test_initialize(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 1,
            "method": "initialize",
        })
        self.assertEqual(resp["id"], 1)
        self.assertIn("protocolVersion", resp["result"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "mcp-plato-adapter")

    def test_tools_list(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 2,
            "method": "tools/list",
        })
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        self.assertIn("plato_query", names)
        self.assertIn("plato_submit", names)
        self.assertIn("fleet_route", names)
        self.assertIn("fleet_health", names)
        self.assertIn("expert_consult", names)
        self.assertIn("conservation_check", names)
        self.assertEqual(len(tools), 6)

    def test_ping(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 3,
            "method": "ping",
        })
        self.assertIn("result", resp)

    def test_unknown_method(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 4,
            "method": "nonexistent",
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_unknown_tool(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 5,
            "method": "tools/call",
            "params": {"name": "bogus_tool", "arguments": {}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)


class TestFleetRouteTool(unittest.TestCase):
    """Test fleet routing tool."""

    def setUp(self):
        self.tool = FleetRouteTool(translator_router=None)

    def test_basic_route(self):
        result = self.tool.execute("Compute Eisenstein norm of a=3, b=5")
        self.assertIn("recommended_model", result)
        self.assertIn("model_id", result["recommended_model"])
        self.assertIn("detected_stage", result)
        self.assertIn("estimated_accuracy", result)

    def test_speed_priority(self):
        result = self.tool.execute("simple addition", priority="speed")
        self.assertEqual(result["priority"], "speed")
        # Speed should pick Seed-2.0-mini
        self.assertIn("Seed", result["recommended_model"]["model_id"])

    def test_quality_priority(self):
        result = self.tool.execute("complex constraint theory proof", priority="quality")
        self.assertEqual(result["priority"], "quality")

    def test_notation_detection(self):
        result = self.tool.execute("a²-ab+b²")
        self.assertTrue(result.get("has_notation"))

    def test_accuracy_range(self):
        result = self.tool.execute("compute something")
        acc = result["estimated_accuracy"]
        self.assertGreater(acc, 0)
        self.assertLessEqual(acc, 1.0)


class TestConservationCheckTool(unittest.TestCase):
    """Test conservation checking with mock server."""

    @classmethod
    def setUpClass(cls):
        cls.hebbian_port = 18749
        cls.hebbian_server = _start_mock_server(MockHebbianHandler, cls.hebbian_port)
        time.sleep(0.2)

    def test_conservation_check_with_mock(self):
        client = HebbianClient(f"http://127.0.0.1:{self.hebbian_port}")
        tool = ConservationCheckTool(client)
        result = tool.execute()
        self.assertEqual(result["compliance"], "compliant")
        self.assertIn("gamma", result)
        self.assertIn("H", result)

    def test_history_trend(self):
        client = HebbianClient(f"http://127.0.0.1:{self.hebbian_port}")
        tool = ConservationCheckTool(client)
        # Run multiple checks to build history
        for _ in range(5):
            tool.execute()
        result = tool.execute()
        self.assertIsNotNone(result.get("history_trend"))
        self.assertEqual(result["history_trend"]["checks"], 6)

    def test_room_filter(self):
        client = HebbianClient(f"http://127.0.0.1:{self.hebbian_port}")
        tool = ConservationCheckTool(client)
        result = tool.execute(room="forgemaster-local")
        self.assertEqual(result["room_filter"], "forgemaster-local")


class TestFleetHealthTool(unittest.TestCase):
    """Test health checking with mock servers."""

    @classmethod
    def setUpClass(cls):
        cls.plato_port = 18748
        cls.hebbian_port = 18750
        cls.plato_server = _start_mock_server(MockPLATOHandler, cls.plato_port)
        cls.hebbian_server = _start_mock_server(MockHebbianHandler, cls.hebbian_port)
        time.sleep(0.2)

    def test_overall_health(self):
        plato = PlatoClient(f"http://127.0.0.1:{self.plato_port}")
        hebbian = HebbianClient(f"http://127.0.0.1:{self.hebbian_port}")
        tool = FleetHealthTool(plato, hebbian)
        result = tool.execute()
        self.assertEqual(result["overall_status"], "healthy")
        self.assertIn("plato", result["subsystems"])
        self.assertIn("hebbian", result["subsystems"])
        self.assertIn("translator", result["subsystems"])

    def test_subsystem_filter(self):
        plato = PlatoClient(f"http://127.0.0.1:{self.plato_port}")
        hebbian = HebbianClient(f"http://127.0.0.1:{self.hebbian_port}")
        tool = FleetHealthTool(plato, hebbian)
        result = tool.execute(subsystem="plato")
        self.assertIn("plato", result["subsystems"])
        self.assertNotIn("hebbian", result["subsystems"])


class TestExpertConsultTool(unittest.TestCase):
    """Test expert consultation."""

    @classmethod
    def setUpClass(cls):
        cls.hebbian_port = 18751
        cls.hebbian_server = _start_mock_server(MockHebbianHandler, cls.hebbian_port)
        time.sleep(0.2)

    def test_conservation_expert(self):
        plato = PlatoClient("http://localhost:19999")  # unreachable ok
        hebbian = HebbianClient(f"http://127.0.0.1:{self.hebbian_port}")
        tool = ExpertConsultTool(plato, hebbian)
        result = tool.execute(domain="conservation-law", question="Is γ+H within bounds?")
        self.assertGreater(result["total_experts_consulted"], 0)
        self.assertIn("consultation_id", result)

    def test_unknown_domain(self):
        plato = PlatoClient("http://localhost:19999")
        hebbian = HebbianClient(f"http://127.0.0.1:{self.hebbian_port}")
        tool = ExpertConsultTool(plato, hebbian)
        result = tool.execute(domain="quantum-mechanics", question="wave function collapse")
        # Should still return results (fallback experts or plato search)
        self.assertIn("responses", result)


class TestMCPToolCallIntegration(unittest.TestCase):
    """Integration test: JSON-RPC tool calls with mock servers."""

    @classmethod
    def setUpClass(cls):
        cls.plato_port = 18752
        cls.hebbian_port = 18753
        cls.plato_server = _start_mock_server(MockPLATOHandler, cls.plato_port)
        cls.hebbian_server = _start_mock_server(MockHebbianHandler, cls.hebbian_port)
        time.sleep(0.2)

    def setUp(self):
        self.handler = MCPHandler(
            plato_url=f"http://127.0.0.1:{self.plato_port}",
            hebbian_url=f"http://127.0.0.1:{self.hebbian_port}",
        )

    def test_fleet_route_tool_call(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 10,
            "method": "tools/call",
            "params": {
                "name": "fleet_route",
                "arguments": {"computation": "Eisenstein norm a=3 b=5"},
            },
        })
        self.assertIn("result", resp)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertIn("recommended_model", data)

    def test_fleet_health_tool_call(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 11,
            "method": "tools/call",
            "params": {
                "name": "fleet_health",
                "arguments": {},
            },
        })
        self.assertIn("result", resp)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertIn("overall_status", data)

    def test_conservation_check_tool_call(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 12,
            "method": "tools/call",
            "params": {
                "name": "conservation_check",
                "arguments": {},
            },
        })
        self.assertIn("result", resp)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertIn("compliance", data)

    def test_expert_consult_tool_call(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 13,
            "method": "tools/call",
            "params": {
                "name": "expert_consult",
                "arguments": {
                    "domain": "conservation-law",
                    "question": "Is the system conserved?",
                },
            },
        })
        self.assertIn("result", resp)

    def test_plato_submit_tool_call(self):
        resp = self.handler.handle_request({
            "jsonrpc": "2.0", "id": 14,
            "method": "tools/call",
            "params": {
                "name": "plato_submit",
                "arguments": {
                    "room": "forgemaster-local",
                    "content": "Test tile from MCP adapter",
                    "tags": ["test", "mcp"],
                    "domain": "testing",
                    "confidence": 0.9,
                },
            },
        })
        self.assertIn("result", resp)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertEqual(data["status"], "submitted")

    def test_rate_limiting(self):
        handler = MCPHandler(
            plato_url=f"http://127.0.0.1:{self.plato_port}",
            hebbian_url=f"http://127.0.0.1:{self.hebbian_port}",
        )
        handler.rate_limiter = TokenBucket(rate=0, capacity=2)  # 2 calls max

        # First two should succeed
        for i in range(2):
            resp = handler.handle_request({
                "jsonrpc": "2.0", "id": i,
                "method": "tools/call",
                "params": {"name": "fleet_health", "arguments": {}},
            })
            self.assertIn("result", resp)

        # Third should be rate limited
        resp = handler.handle_request({
            "jsonrpc": "2.0", "id": 99,
            "method": "tools/call",
            "params": {"name": "fleet_health", "arguments": {}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32002)

    def test_authentication_with_keys(self):
        handler = MCPHandler(
            plato_url=f"http://127.0.0.1:{self.plato_port}",
            hebbian_url=f"http://127.0.0.1:{self.hebbian_port}",
            api_keys={"valid-key"},
        )
        # Without key → reject
        resp = handler.handle_request({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"name": "fleet_health", "arguments": {}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32001)

        # With valid key → allow
        resp = handler.handle_request({
            "jsonrpc": "2.0", "id": 2,
            "method": "tools/call",
            "params": {"name": "fleet_health", "arguments": {"_api_key": "valid-key"}},
        })
        self.assertIn("result", resp)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
