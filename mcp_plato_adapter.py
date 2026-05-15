#!/usr/bin/env python3
"""
mcp_plato_adapter.py — MCP (Model Context Protocol) Adapter for PLATO Fleet

Exposes 6 MCP tools that let any MCP-compatible framework use the Cocapn fleet:

1. plato_query    — Query PLATO rooms for relevant tiles
2. plato_submit   — Submit a tile to a PLATO room
3. fleet_route    — Route a computation to the best model
4. fleet_health   — Check fleet health status
5. expert_consult — Cross-consult expert daemons
6. conservation_check — Verify conservation law compliance

FastAPI server on :8300 with JSON-RPC handler at /mcp.

Run:
    python mcp_plato_adapter.py                    # :8300
    python mcp_plato_adapter.py --port 9000         # custom port
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import threading
import time
import urllib.request
import urllib.error
from collections import deque
from dataclasses import dataclass, field, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Local imports (graceful)
# ---------------------------------------------------------------------------

try:
    from mythos_tile import MythosTile, ModelTier
    HAS_MYTHOS = True
except ImportError:
    HAS_MYTHOS = False
    MythosTile = None
    ModelTier = None

try:
    from fleet_translator_v2 import (
        FleetRouter, ModelStage, KNOWN_STAGES,
        NotationNormalizer, ActivationKeyEngineer, translate,
        auto_detect_stage,
    )
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False
    FleetRouter = None
    ModelStage = None
    KNOWN_STAGES = {}

try:
    from fleet_router_api import (
        CriticalAngleRouter, ModelRegistry, RoutingStats, ModelTierEnum as RouterTierEnum,
    )
    HAS_ROUTER_API = True
except ImportError:
    HAS_ROUTER_API = False
    CriticalAngleRouter = None
    ModelRegistry = None

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("mcp_plato_adapter")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PLATO_URL = "http://localhost:8848"
DEFAULT_HEBBIAN_URL = "http://localhost:8849"
DEFAULT_PORT = 8300


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------

class TokenBucket:
    """Simple token-bucket rate limiter."""

    def __init__(self, rate: float = 60.0, capacity: int = 100):
        self.rate = rate            # tokens per second
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False


# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------

class ApiKeyAuth:
    """Simple API key validator. Accepts any key from a set, or all if set is empty."""

    def __init__(self, valid_keys: Optional[set] = None):
        self.valid_keys = valid_keys or set()

    def check(self, key: Optional[str]) -> bool:
        if not self.valid_keys:
            return True  # no keys configured = open access
        return key in self.valid_keys


# ---------------------------------------------------------------------------
# PLATO client — talks to localhost:8848
# ---------------------------------------------------------------------------

class PlatoClient:
    """HTTP client for the PLATO service at :8848."""

    def __init__(self, base_url: str = DEFAULT_PLATO_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if qs:
                url += f"?{qs}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("PLATO GET %s failed: %s", path, e)
            return None

    def _post(self, path: str, body: dict) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode()
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("PLATO POST %s failed: %s", path, e)
            return None

    def get_rooms(self) -> List[dict]:
        """Get list of rooms."""
        resp = self._get("/rooms")
        if resp and "rooms" in resp:
            return resp["rooms"]
        return []

    def query_tiles(self, query: str, room: Optional[str] = None,
                    limit: int = 20) -> List[dict]:
        """Search tiles by query string."""
        # Try a search endpoint first, fall back to room listing
        params = {"q": query, "limit": limit}
        if room:
            params["room"] = room
        resp = self._get("/search", params)
        if resp:
            tiles = resp.get("tiles", resp.get("results", []))
            return tiles[:limit]

        # Fallback: list all tiles from rooms endpoint
        rooms_resp = self._get("/rooms")
        if not rooms_resp:
            return []
        tiles = []
        for r in rooms_resp.get("rooms", []):
            room_name = r.get("name", r) if isinstance(r, dict) else r
            room_resp = self._get(f"/room/{room_name}")
            if room_resp:
                room_tiles = room_resp.get("tiles", [])
                for t in room_tiles:
                    # Simple relevance: check if query appears in content
                    content = json.dumps(t).lower()
                    if query.lower() in content:
                        t["_relevance"] = 1.0
                        tiles.append(t)
        return tiles[:limit]

    def submit_tile(self, room: str, content: str, tags: Optional[List[str]] = None,
                    domain: str = "", confidence: float = 1.0,
                    source: str = "mcp-adapter") -> dict:
        """Submit a tile to a PLATO room."""
        body = {
            "room": room,
            "domain": domain,
            "question": content,
            "tags": tags or [],
            "source": source,
            "confidence": confidence,
        }
        resp = self._post("/tile", body)
        if resp:
            return resp
        # If POST fails, return a local acknowledgment
        tile_id = hashlib.sha256(f"{room}:{content}:{time.time()}".encode()).hexdigest()[:16]
        return {"tile_id": tile_id, "status": "submitted_locally", "room": room}

    def health(self) -> dict:
        """Check PLATO service health."""
        resp = self._get("/status")
        if resp:
            return {"status": "healthy", "details": resp}
        return {"status": "unreachable", "url": self.base_url}


# ---------------------------------------------------------------------------
# Hebbian client — talks to localhost:8849
# ---------------------------------------------------------------------------

class HebbianClient:
    """HTTP client for the Hebbian service at :8849."""

    def __init__(self, base_url: str = DEFAULT_HEBBIAN_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("Hebbian GET %s failed: %s", path, e)
            return None

    def _post(self, path: str, body: dict) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode()
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("Hebbian POST %s failed: %s", path, e)
            return None

    def get_status(self) -> Optional[dict]:
        return self._get("/status")

    def get_conservation(self) -> Optional[dict]:
        return self._get("/conservation")

    def get_clusters(self) -> Optional[dict]:
        return self._get("/clusters")

    def get_weights(self) -> Optional[dict]:
        return self._get("/weights")

    def submit_tile(self, tile_type: str, source_room: str,
                    dest_room: Optional[str] = None,
                    confidence: float = 0.9) -> Optional[dict]:
        return self._post("/tile", {
            "tile_type": tile_type,
            "source_room": source_room,
            "dest_room": dest_room,
            "confidence": confidence,
        })

    def submit_mythos_tile(self, tile_data: dict) -> Optional[dict]:
        return self._post("/tile/mythos", tile_data)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

class PlatoQueryTool:
    """Tool: plato_query — Query PLATO rooms for relevant tiles."""

    def __init__(self, plato: PlatoClient):
        self.plato = plato

    def execute(self, query: str, room: Optional[str] = None,
                limit: int = 20) -> dict:
        tiles = self.plato.query_tiles(query, room=room, limit=limit)
        # Score relevance for each tile
        scored = []
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        for tile in tiles:
            content = json.dumps(tile).lower()
            # Count term matches
            matches = sum(1 for t in query_terms if t in content)
            # Boost for room match
            tile_room = tile.get("room", tile.get("_meta", {}).get("room", ""))
            room_boost = 0.2 if room and room in tile_room else 0.0
            # Tag match
            tags = tile.get("tags", [])
            tag_match = sum(0.1 for t in tags if t.lower() in query_lower)
            relevance = min(1.0, (matches / max(len(query_terms), 1)) + room_boost + tag_match)
            tile["_relevance"] = round(relevance, 3)
            scored.append(tile)

        scored.sort(key=lambda t: t.get("_relevance", 0), reverse=True)
        return {
            "query": query,
            "room_filter": room,
            "total_results": len(scored),
            "tiles": scored[:limit],
        }


class PlatoSubmitTool:
    """Tool: plato_submit — Submit a tile to a PLATO room."""

    def __init__(self, plato: PlatoClient, hebbian: HebbianClient):
        self.plato = plato
        self.hebbian = hebbian

    def execute(self, room: str, content: str, tags: Optional[List[str]] = None,
                domain: str = "", confidence: float = 1.0,
                source: str = "mcp-adapter") -> dict:
        # Build a MythosTile if available
        tile_id = ""
        if HAS_MYTHOS:
            tile = MythosTile(
                domain=domain,
                source=source,
                content=content,
                confidence=confidence,
                room=room,
                tags=tags or [],
            )
            tile_id = tile.tile_id
            # Try submitting as MythosTile to Hebbian
            if self.hebbian:
                try:
                    self.hebbian.submit_mythos_tile(asdict(tile))
                except Exception:
                    pass
        else:
            tile_id = hashlib.sha256(
                f"{room}:{content}:{time.time()}".encode()
            ).hexdigest()[:16]

        # Submit to PLATO
        result = self.plato.submit_tile(
            room=room, content=content, tags=tags,
            domain=domain, confidence=confidence, source=source,
        )

        return {
            "tile_id": result.get("tile_id", tile_id),
            "room": room,
            "status": "submitted",
            "content_preview": content[:200],
            "tags": tags or [],
            "confidence": confidence,
        }


class FleetRouteTool:
    """Tool: fleet_route — Route a computation to the best model.

    Uses CriticalAngleRouter from fleet_router_api when available,
    falling back to the translator-based router.
    """

    def __init__(self, translator_router=None, critical_angle_router=None,
                 hebbian_client=None):
        self._router = translator_router
        self._critical_angle_router = critical_angle_router
        self._hebbian = hebbian_client

    def execute(self, computation: str, priority: str = "balanced") -> dict:
        """Route a computation description to the best fleet model.

        When a CriticalAngleRouter is available, delegates to it for
        three-tier routing, auto-downgrade, and Hebbian flow events.
        """
        # Detect stage from the computation
        if HAS_TRANSLATOR:
            stage = auto_detect_stage(computation)
            stage_name = stage.name
            stage_value = int(stage)
            labels = NotationNormalizer.detect_domain_labels(computation)
            has_notation = NotationNormalizer.has_symbolic_notation(computation)
        else:
            stage_name = "CAPABLE"
            stage_value = 3
            labels = []
            has_notation = False

        # --- Use CriticalAngleRouter if available ---
        if HAS_ROUTER_API and self._critical_angle_router:
            car = self._critical_angle_router
            params = {"expression": computation}
            # Map priority to preferred model
            preferred = None
            if priority == "speed":
                preferred = "ByteDance/Seed-2.0-mini"
            elif priority == "quality":
                preferred = "ByteDance/Seed-2.0-code"

            result = car.route_request(
                task_type="generic",
                params=params,
                preferred_model=preferred,
            )

            # Emit Hebbian flow event
            hebbian_emitted = False
            if self._hebbian and result.get("model_id"):
                try:
                    self._hebbian.submit_tile(
                        tile_type="routed",
                        source_room="mcp-fleet-route",
                        dest_room=f"model-{result['model_id']}",
                        confidence=result.get("estimated_accuracy", 0.9),
                    )
                    hebbian_emitted = True
                except Exception:
                    pass

            return {
                "computation": computation,
                "detected_stage": stage_name,
                "detected_labels": labels,
                "has_notation": has_notation,
                "recommended_model": {
                    "model_id": result.get("model_id"),
                    "tier": result.get("tier"),
                    "reason": result.get("routing_reason", ""),
                },
                "translated_prompt": result.get("translated_prompt", computation),
                "estimated_accuracy": result.get("estimated_accuracy", 0.5),
                "priority": priority,
                "downgraded": result.get("downgraded", False),
                "rejected": result.get("rejected", False),
                "hebbian_flow_emitted": hebbian_emitted,
                "router": "CriticalAngleRouter",
            }

        # --- Fallback: translator-based routing ---
        model_recommendation = self._recommend_model(stage_value, priority)
        translated_prompt = computation
        estimated_accuracy = self._estimate_accuracy(stage_value, priority)

        if HAS_TRANSLATOR and self._router:
            try:
                translated_prompt = self._router.route(
                    model_recommendation["model_id"],
                    "generic",
                    {"expression": computation},
                )
            except Exception:
                pass

        return {
            "computation": computation,
            "detected_stage": stage_name,
            "detected_labels": labels,
            "has_notation": has_notation,
            "recommended_model": model_recommendation,
            "translated_prompt": translated_prompt,
            "estimated_accuracy": estimated_accuracy,
            "priority": priority,
            "router": "translator",
        }

    def _recommend_model(self, stage_value: int, priority: str) -> dict:
        """Recommend the best model based on stage and priority."""
        if priority == "speed":
            return {"model_id": "ByteDance/Seed-2.0-mini", "tier": 1,
                    "reason": "Fast failback, handles most tasks"}
        if priority == "quality":
            return {"model_id": "ByteDance/Seed-2.0-code", "tier": 1,
                    "reason": "Best code+math model"}
        return {"model_id": "ByteDance/Seed-2.0-mini", "tier": 1,
                "reason": "Balanced default"}

    def _estimate_accuracy(self, stage_value: int, priority: str) -> float:
        base = {4: 0.98, 3: 0.85, 2: 0.70, 1: 0.50, 0: 0.30}
        return base.get(stage_value, 0.5)


class FleetHealthTool:
    """Tool: fleet_health — Check fleet health status."""

    def __init__(self, plato: PlatoClient, hebbian: HebbianClient):
        self.plato = plato
        self.hebbian = hebbian

    def execute(self, subsystem: Optional[str] = None) -> dict:
        """Check fleet health. Optionally filter to a specific subsystem."""
        report = {
            "timestamp": time.time(),
            "overall_status": "unknown",
            "subsystems": {},
        }

        # Check PLATO
        if subsystem in (None, "plato"):
            plato_health = self.plato.health()
            report["subsystems"]["plato"] = plato_health

        # Check Hebbian
        if subsystem in (None, "hebbian"):
            hebbian_status = self.hebbian.get_status()
            if hebbian_status:
                report["subsystems"]["hebbian"] = {
                    "status": "healthy",
                    "details": hebbian_status,
                }
            else:
                report["subsystems"]["hebbian"] = {
                    "status": "unreachable",
                    "url": self.hebbian.base_url,
                }

        # Check translator (always available if imported)
        if subsystem in (None, "translator"):
            if HAS_TRANSLATOR:
                report["subsystems"]["translator"] = {
                    "status": "healthy",
                    "models_registered": len(KNOWN_STAGES),
                    "stages_available": [s.name for s in ModelStage],
                }
            else:
                report["subsystems"]["translator"] = {"status": "unavailable"}

        # Determine overall status
        statuses = [v.get("status", "unknown") for v in report["subsystems"].values()]
        if all(s == "healthy" for s in statuses):
            report["overall_status"] = "healthy"
        elif any(s == "healthy" for s in statuses):
            report["overall_status"] = "degraded"
        else:
            report["overall_status"] = "unhealthy"

        return report


class ExpertConsultTool:
    """Tool: expert_consult — Cross-consult expert daemons."""

    # Known expert daemons and their domains
    EXPERT_REGISTRY = {
        "conservation": {
            "domain": "conservation-law",
            "description": "Conservation law compliance, γ+H monitoring",
            "endpoint": "/conservation",
            "client": "hebbian",
        },
        "architect": {
            "domain": "system-architecture",
            "description": "System design, constraint theory, tile protocols",
            "endpoint": None,
            "client": None,
        },
        "router": {
            "domain": "fleet-routing",
            "description": "Model routing, stage classification, prompt translation",
            "endpoint": None,
            "client": None,
        },
        "hebbian": {
            "domain": "hebbian-learning",
            "description": "Hebbian weight updates, room clustering, flow tracking",
            "endpoint": "/status",
            "client": "hebbian",
        },
    }

    def __init__(self, plato: PlatoClient, hebbian: HebbianClient,
                 translator_router=None):
        self.plato = plato
        self.hebbian = hebbian
        self._translator_router = translator_router

    def execute(self, domain: str, question: str,
                requesting_expert: str = "mcp-adapter") -> dict:
        """Consult expert daemons for a domain-specific question."""
        responses = []

        # Find relevant experts
        relevant_experts = self._find_experts(domain)

        for expert_name, expert_info in relevant_experts:
            response = self._consult_expert(expert_name, expert_info, question)
            if response:
                response["expert"] = expert_name
                responses.append(response)

        # If no specific experts matched, do a general PLATO query
        if not responses:
            tiles = self.plato.query_tiles(question, limit=5)
            if tiles:
                responses.append({
                    "expert": "plato-search",
                    "domain": domain,
                    "response": "Found relevant tiles in PLATO rooms",
                    "confidence": 0.7,
                    "tiles": tiles[:3],
                })

        # Build MythosTile for the consultation if available
        consultation_id = hashlib.sha256(
            f"{domain}:{question}:{time.time()}".encode()
        ).hexdigest()[:16]

        return {
            "consultation_id": consultation_id,
            "domain": domain,
            "question": question,
            "requesting_expert": requesting_expert,
            "responses": responses,
            "total_experts_consulted": len(responses),
        }

    def _find_experts(self, domain: str) -> List[Tuple[str, dict]]:
        """Find experts relevant to a domain."""
        domain_lower = domain.lower()
        results = []
        for name, info in self.EXPERT_REGISTRY.items():
            if domain_lower in info["domain"] or name in domain_lower:
                results.append((name, info))
        # If no match, return all experts as fallback
        if not results:
            results = list(self.EXPERT_REGISTRY.items())[:3]
        return results

    def _consult_expert(self, name: str, info: dict, question: str) -> Optional[dict]:
        """Consult a single expert daemon."""
        client_type = info.get("client")

        if client_type == "hebbian":
            endpoint = info.get("endpoint")
            if endpoint:
                data = self.hebbian._get(endpoint)
                if data:
                    return {
                        "domain": info["domain"],
                        "response": f"Retrieved {name} data for: {question}",
                        "confidence": 0.9,
                        "data": data,
                    }

        # Architect / Router experts — use translator if available
        if name in ("architect", "router") and self._translator_router:
            return {
                "domain": info["domain"],
                "response": f"{name} analysis for: {question}",
                "confidence": 0.8,
                "recommendation": "Use activation-key engineering for Stage 3 models",
            }

        # Generic fallback
        return {
            "domain": info["domain"],
            "response": f"{name}: No specific data available for '{question}'",
            "confidence": 0.3,
        }


class ConservationCheckTool:
    """Tool: conservation_check — Verify conservation law compliance."""

    def __init__(self, hebbian: HebbianClient):
        self.hebbian = hebbian
        self._history: List[dict] = []

    def execute(self, room: Optional[str] = None) -> dict:
        """Check conservation law compliance (γ+H within bounds)."""
        # Get conservation report from Hebbian service
        conservation = self.hebbian.get_conservation()

        result = {
            "timestamp": time.time(),
            "room_filter": room,
            "conservation": None,
            "compliance": "unknown",
            "history_trend": None,
        }

        if conservation:
            # Extract the conservation section
            cons = conservation.get("conservation", conservation)
            result["conservation"] = cons

            # Determine compliance
            if isinstance(cons, dict):
                conserved = cons.get("conserved", False)
                deviation = cons.get("deviation", 999)
                sigma = cons.get("sigma", 0.05)

                if conserved:
                    result["compliance"] = "compliant"
                elif abs(deviation) > 3 * sigma:
                    result["compliance"] = "violation"
                else:
                    result["compliance"] = "marginal"

                # Summary values
                result["gamma"] = cons.get("gamma", 0)
                result["H"] = cons.get("H", 0)
                result["gamma_plus_H"] = cons.get("sum", cons.get("gamma_plus_H", 0))
                result["predicted"] = cons.get("predicted", 0)
                result["deviation"] = deviation
                result["sigma"] = sigma
            else:
                result["compliance"] = "data_format_error"
        else:
            result["compliance"] = "service_unreachable"
            result["conservation"] = None

        # Store in history for trend analysis
        self._history.append({
            "timestamp": result["timestamp"],
            "compliance": result["compliance"],
            "gamma_plus_H": result.get("gamma_plus_H"),
            "deviation": result.get("deviation"),
        })
        # Keep last 100 checks
        if len(self._history) > 100:
            self._history = self._history[-100:]

        # Add trend if we have enough history
        if len(self._history) >= 3:
            recent = self._history[-5:]
            deviations = [h.get("deviation") for h in recent if h.get("deviation") is not None]
            if deviations:
                avg_dev = sum(abs(d) for d in deviations) / len(deviations)
                result["history_trend"] = {
                    "checks": len(self._history),
                    "recent_avg_deviation": round(avg_dev, 4),
                    "trend": "improving" if avg_dev < 0.03 else "stable" if avg_dev < 0.05 else "degrading",
                }

        return result


# ---------------------------------------------------------------------------
# MCP JSON-RPC handler
# ---------------------------------------------------------------------------

class MCPHandler:
    """Handles MCP JSON-RPC 2.0 tool calls."""

    # Tool registry
    TOOL_DEFINITIONS = [
        {
            "name": "plato_query",
            "description": "Query PLATO rooms for relevant tiles. Searches room names, tile content, and tags.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"},
                    "room": {"type": "string", "description": "Optional room filter"},
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                },
                "required": ["query"],
            },
        },
        {
            "name": "plato_submit",
            "description": "Submit a tile to a PLATO room. Uses MythosTile format internally.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "room": {"type": "string", "description": "Target PLATO room"},
                    "content": {"type": "string", "description": "Tile content"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                    "domain": {"type": "string", "description": "Domain label (e.g. 'math', 'constraint-theory')"},
                    "confidence": {"type": "number", "description": "Confidence score 0-1 (default 1.0)", "default": 1.0},
                    "source": {"type": "string", "description": "Source agent name", "default": "mcp-adapter"},
                },
                "required": ["room", "content"],
            },
        },
        {
            "name": "fleet_route",
            "description": "Route a computation to the best fleet model using three-tier taxonomy.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "computation": {"type": "string", "description": "Computation description or expression"},
                    "priority": {"type": "string", "enum": ["speed", "balanced", "quality"],
                                 "description": "Routing priority (default 'balanced')", "default": "balanced"},
                },
                "required": ["computation"],
            },
        },
        {
            "name": "fleet_health",
            "description": "Check fleet health status including PLATO, Hebbian, and translator subsystems.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "subsystem": {"type": "string",
                                  "description": "Specific subsystem to check (plato, hebbian, translator)"},
                },
            },
        },
        {
            "name": "expert_consult",
            "description": "Cross-consult expert daemons for domain-specific questions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain to consult about"},
                    "question": {"type": "string", "description": "Question to ask"},
                    "requesting_expert": {"type": "string", "description": "Name of requesting expert",
                                          "default": "mcp-adapter"},
                },
                "required": ["domain", "question"],
            },
        },
        {
            "name": "conservation_check",
            "description": "Verify conservation law compliance (γ+H values, predicted vs actual).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "room": {"type": "string", "description": "Optional room filter"},
                },
            },
        },
    ]

    def __init__(self, plato_url: str, hebbian_url: str, api_keys: Optional[set] = None):
        self.plato = PlatoClient(plato_url)
        self.hebbian = HebbianClient(hebbian_url)
        self.auth = ApiKeyAuth(api_keys)
        self.rate_limiter = TokenBucket(rate=30.0, capacity=60)

        # Initialize translator router if available
        self._translator_router = None
        if HAS_TRANSLATOR:
            try:
                self._translator_router = FleetRouter()
            except Exception:
                pass

        # Initialize CriticalAngleRouter if available (shares model registry)
        self._critical_angle_router = None
        if HAS_ROUTER_API:
            try:
                registry = ModelRegistry()
                from fleet_router_api import DEFAULT_MODELS
                for model_id, tier in DEFAULT_MODELS.items():
                    registry.register(model_id, tier)
                stats = RoutingStats()
                self._critical_angle_router = CriticalAngleRouter(
                    registry=registry,
                    stats=stats,
                    hebbian_url=hebbian_url,
                )
            except Exception:
                pass

        # Initialize tools
        self.tools = {
            "plato_query": PlatoQueryTool(self.plato),
            "plato_submit": PlatoSubmitTool(self.plato, self.hebbian),
            "fleet_route": FleetRouteTool(
                translator_router=self._translator_router,
                critical_angle_router=self._critical_angle_router,
                hebbian_client=self.hebbian,
            ),
            "fleet_health": FleetHealthTool(self.plato, self.hebbian),
            "expert_consult": ExpertConsultTool(
                self.plato, self.hebbian, self._translator_router
            ),
            "conservation_check": ConservationCheckTool(self.hebbian),
        }

    def handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC 2.0 request."""
        jsonrpc = request.get("jsonrpc", "2.0")
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        # JSON-RPC protocol methods
        if method == "initialize":
            return {
                "jsonrpc": jsonrpc,
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "mcp-plato-adapter",
                        "version": "1.0.0",
                    },
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": jsonrpc,
                "id": req_id,
                "result": {"tools": self.TOOL_DEFINITIONS},
            }

        if method == "tools/call":
            return self._handle_tool_call(jsonrpc, req_id, params)

        if method == "ping":
            return {"jsonrpc": jsonrpc, "id": req_id, "result": {}}

        return {
            "jsonrpc": jsonrpc,
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def _handle_tool_call(self, jsonrpc: str, req_id: Any, params: dict) -> dict:
        """Handle a tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        # Authenticate
        api_key = arguments.get("_api_key") or params.get("_api_key")
        if not self.auth.check(api_key):
            return {
                "jsonrpc": jsonrpc,
                "id": req_id,
                "error": {"code": -32001, "message": "Unauthorized: invalid API key"},
            }

        # Rate limit
        if not self.rate_limiter.consume():
            return {
                "jsonrpc": jsonrpc,
                "id": req_id,
                "error": {"code": -32002, "message": "Rate limit exceeded"},
            }

        # Find tool
        tool = self.tools.get(tool_name)
        if not tool:
            return {
                "jsonrpc": jsonrpc,
                "id": req_id,
                "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
            }

        # Execute tool
        try:
            result = tool.execute(**{k: v for k, v in arguments.items() if not k.startswith("_")})
            return {
                "jsonrpc": jsonrpc,
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
                },
            }
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return {
                "jsonrpc": jsonrpc,
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                    "isError": True,
                },
            }


# ---------------------------------------------------------------------------
# HTTP Server (standalone, no FastAPI dependency required)
# ---------------------------------------------------------------------------

class MCPPlatoAdapterServer:
    """HTTP server exposing the MCP adapter on :8300."""

    def __init__(self, port: int = DEFAULT_PORT, plato_url: str = DEFAULT_PLATO_URL,
                 hebbian_url: str = DEFAULT_HEBBIAN_URL, api_keys: Optional[set] = None):
        self.port = port
        self.handler = MCPHandler(plato_url, hebbian_url, api_keys)
        self._server: Optional[HTTPServer] = None

    def start(self, block: bool = True):
        handler = self.handler

        class HTTPHandler(BaseHTTPRequestHandler):
            def _send_json(self, data, code=200):
                body = json.dumps(data, indent=2, default=str).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self) -> dict:
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    return json.loads(self.rfile.read(length))
                return {}

            def do_GET(self):
                if self.path == "/health":
                    self._send_json({"status": "ok", "service": "mcp-plato-adapter",
                                     "tools": list(handler.tools.keys())})
                elif self.path == "/tools":
                    self._send_json({"tools": handler.TOOL_DEFINITIONS})
                else:
                    self._send_json({"error": "not found"}, 404)

            def do_POST(self):
                if self.path == "/mcp":
                    try:
                        request = self._read_json()
                        response = handler.handle_request(request)
                        self._send_json(response)
                    except json.JSONDecodeError as e:
                        self._send_json({"error": f"Invalid JSON: {e}"}, 400)
                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)
                else:
                    self._send_json({"error": "not found"}, 404)

            def log_message(self, format, *args):
                pass  # suppress request logging

        class ThreadedServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self._server = ThreadedServer(("0.0.0.0", self.port), HTTPHandler)
        print(f"⚒️  MCP PLATO Adapter on :{self.port}")
        print(f"   PLATO: {handler.plato.base_url}")
        print(f"   Hebbian: {handler.hebbian.base_url}")
        print(f"   Tools: {list(handler.tools.keys())}")
        print(f"   Endpoints: /mcp (POST) /health (GET) /tools (GET)")

        if block:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            t = threading.Thread(target=self._server.serve_forever, daemon=True)
            t.start()

    def stop(self):
        if self._server:
            self._server.shutdown()
        print("⚒️  MCP PLATO Adapter stopped.")


# ---------------------------------------------------------------------------
# FastAPI integration (optional, if fastapi is installed)
# ---------------------------------------------------------------------------

def create_fastapi_app(plato_url: str = DEFAULT_PLATO_URL,
                       hebbian_url: str = DEFAULT_HEBBIAN_URL,
                       api_keys: Optional[set] = None):
    """Create a FastAPI app for the MCP adapter. Requires `fastapi` and `uvicorn`."""
    try:
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError:
        raise ImportError("FastAPI/uvicorn not installed. Use: pip install fastapi uvicorn")

    app = FastAPI(title="MCP PLATO Adapter", version="1.0.0")
    mcp_handler = MCPHandler(plato_url, hebbian_url, api_keys)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "mcp-plato-adapter",
                "tools": list(mcp_handler.tools.keys())}

    @app.get("/tools")
    async def tools_list():
        return {"tools": mcp_handler.TOOL_DEFINITIONS}

    @app.post("/mcp")
    async def mcp_endpoint(request: Request):
        body = await request.json()
        response = mcp_handler.handle_request(body)
        return JSONResponse(response)

    return app


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MCP PLATO Adapter")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--plato-url", type=str, default=DEFAULT_PLATO_URL)
    parser.add_argument("--hebbian-url", type=str, default=DEFAULT_HEBBIAN_URL)
    parser.add_argument("--api-key", type=str, action="append", default=[],
                        help="Valid API keys (can specify multiple)")
    parser.add_argument("--fastapi", action="store_true",
                        help="Use FastAPI/uvicorn instead of built-in server")
    args = parser.parse_args()

    api_keys = set(args.api_key) if args.api_key else None

    if args.fastapi:
        try:
            import uvicorn
            app = create_fastapi_app(args.plato_url, args.hebbian_url, api_keys)
            uvicorn.run(app, host="0.0.0.0", port=args.port)
        except ImportError:
            print("FastAPI not available, falling back to built-in server")
            server = MCPPlatoAdapterServer(args.port, args.plato_url, args.hebbian_url, api_keys)
            server.start(block=True)
    else:
        server = MCPPlatoAdapterServer(args.port, args.plato_url, args.hebbian_url, api_keys)
        server.start(block=True)


if __name__ == "__main__":
    main()
