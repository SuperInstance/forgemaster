#!/usr/bin/env python3
"""core/mcp_adapter.py — PLATO rooms as MCP tools.

Makes PLATO a drop-in backend for any MCP-compatible agent framework.
External agents can read_tile, write_tile, list_rooms, query_health
without knowing anything about PLATO internals.

This is the compatibility layer that lets LangGraph, OpenAI Agents SDK,
Strands, n8n, or any MCP client use our fleet.

MCP (Model Context Protocol): Anthropic's open standard for agent-to-tool
communication. Every major framework supports it. If PLATO speaks MCP,
PLATO speaks to everyone.

Usage:
    # Start the MCP server
    python3 core/mcp_adapter.py --port 8300

    # Any MCP client can now call:
    # - list_rooms() → all PLATO rooms
    # - read_tiles(room_id, limit) → recent tiles from a room
    # - write_tile(room_id, tile_data) → submit a tile
    # - query_health() → fleet structural + behavioral health
    # - route_query(prompt, domain) → fleet router decision
"""

from __future__ import annotations

import json, os, time, argparse
from typing import Dict, List, Optional, Any
from datetime import datetime

PLATO_URL = "http://localhost:8847  # local PLATO (default)"


def _plato_get(path: str, timeout: float = 5.0) -> Optional[dict]:
    """GET from PLATO server."""
    import requests
    try:
        r = requests.get(f"{PLATO_URL}{path}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


def _plato_post(path: str, data: dict, timeout: float = 5.0) -> Optional[dict]:
    """POST to PLATO server."""
    import requests
    try:
        r = requests.post(f"{PLATO_URL}{path}", json=data, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


# ─── MCP Tool Definitions ─────────────────────────────────────────────────────

MCP_TOOLS = {
    "list_rooms": {
        "name": "list_rooms",
        "description": "List all PLATO rooms with tile counts. Optional prefix filter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prefix": {
                    "type": "string",
                    "description": "Filter rooms by prefix (e.g. 'forgemaster', 'fleet', 'session')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rooms to return (default 50)",
                    "default": 50
                }
            }
        }
    },
    "read_tiles": {
        "name": "read_tiles",
        "description": "Read recent tiles from a PLATO room. Tiles are the universal data unit.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "room_id": {
                    "type": "string",
                    "description": "The room to read from"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max tiles to return (default 10)",
                    "default": 10
                },
                "tile_type": {
                    "type": "string",
                    "description": "Filter by tile type (optional)"
                }
            },
            "required": ["room_id"]
        }
    },
    "write_tile": {
        "name": "write_tile",
        "description": "Write a tile to a PLATO room. This is how agents submit work, findings, and state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "room_id": {
                    "type": "string",
                    "description": "The room to write to"
                },
                "domain": {
                    "type": "string",
                    "description": "The knowledge domain (e.g. 'constraint-theory', 'fleet-ops')"
                },
                "agent": {
                    "type": "string",
                    "description": "Agent identifier (e.g. 'external-client')"
                },
                "question": {
                    "type": "string",
                    "description": "The tile question/topic"
                },
                "answer": {
                    "type": "string",
                    "description": "The tile answer/content"
                },
                "tile_type": {
                    "type": "string",
                    "description": "Tile type classification",
                    "default": "knowledge"
                }
            },
            "required": ["room_id", "domain", "agent", "question", "answer"]
        }
    },
    "query_health": {
        "name": "query_health",
        "description": "Get fleet health — structural (spectral coupling) + behavioral (critical angles, accuracy)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "route_query": {
        "name": "route_query",
        "description": "Route a query to the cheapest model that won't break. Returns model, temperature, estimated cost, and reasoning.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The query to route"
                },
                "domain": {
                    "type": "string",
                    "description": "Domain hint: arithmetic, reasoning, code, design, analysis",
                    "default": "auto"
                },
                "max_cost": {
                    "type": "number",
                    "description": "Maximum acceptable cost per 1K tokens (default 0.10)",
                    "default": 0.10
                }
            },
            "required": ["prompt"]
        }
    },
    "search_tiles": {
        "name": "search_tiles",
        "description": "Search PLATO tiles across all rooms by keyword or agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keyword match on question/answer fields)"
                },
                "agent": {
                    "type": "string",
                    "description": "Filter by agent name"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20)",
                    "default": 20
                }
            },
            "required": ["query"]
        }
    }
}


# ─── Tool Implementations ──────────────────────────────────────────────────────

def tool_list_rooms(params: dict) -> list:
    """List PLATO rooms."""
    prefix = params.get("prefix", "")
    limit = params.get("limit", 50)
    
    data = _plato_get("/rooms")
    if not data:
        return [{"error": "PLATO server unavailable"}]
    
    rooms = data if isinstance(data, list) else data.get("rooms", [])
    
    if prefix:
        rooms = [r for r in rooms if r.get("id", r.get("room_id", "")).startswith(prefix)]
    
    result = []
    for r in rooms[:limit]:
        room_id = r.get("id", r.get("room_id", ""))
        tile_count = r.get("tile_count", r.get("count", 0))
        result.append({
            "room_id": room_id,
            "tile_count": tile_count,
            "last_updated": r.get("last_updated", r.get("updated_at", "")),
        })
    
    return result


def tool_read_tiles(params: dict) -> list:
    """Read tiles from a room."""
    room_id = params.get("room_id", "")
    limit = params.get("limit", 10)
    tile_type = params.get("tile_type")
    
    data = _plato_get(f"/room/{room_id}/history")
    if not data:
        return [{"error": f"Room '{room_id}' not found or empty"}]
    
    tiles = data.get("tiles", data) if isinstance(data, dict) else data
    
    if tile_type:
        tiles = [t for t in tiles if t.get("tile_type") == tile_type]
    
    result = []
    for t in tiles[:limit]:
        result.append({
            "tile_id": t.get("id", t.get("tile_id", "")),
            "question": t.get("question", ""),
            "answer": t.get("answer", ""),
            "agent": t.get("agent", t.get("source", "")),
            "domain": t.get("domain", ""),
            "tile_type": t.get("tile_type", ""),
            "timestamp": t.get("timestamp", t.get("created_at", "")),
        })
    
    return result


def tool_write_tile(params: dict) -> dict:
    """Write a tile to PLATO."""
    payload = {
        "room_id": params["room_id"],
        "domain": params["domain"],
        "agent": params["agent"],
        "question": params["question"],
        "answer": params["answer"],
        "tile_type": params.get("tile_type", "knowledge"),
    }
    
    result = _plato_post("/submit", payload)
    if result:
        return {"status": "submitted", "room_id": params["room_id"]}
    return {"status": "error", "message": "PLATO server unavailable"}


def tool_query_health(params: dict) -> dict:
    """Get fleet health from both dimensions."""
    # Structural health from PLATO stats
    stats = _plato_get("/stats")
    
    structural = {
        "total_rooms": 0,
        "total_tiles": 0,
        "active_agents": [],
    }
    if stats:
        structural = {
            "total_rooms": stats.get("total_rooms", 0),
            "total_tiles": stats.get("total_tiles", 0),
            "active_agents": stats.get("agents", []),
            "domains": stats.get("domains", []),
        }
    
    # Behavioral health (from FM's critical angle data)
    behavioral = {
        "fleet_champion": "seed-2.0-mini",
        "champion_accuracy": 0.895,
        "fast_champion": "gemini-flash-lite",
        "fast_accuracy": 0.825,
        "routing_savings": "84%",
        "critical_angles_mapped": 6,
        "findings_count": 25,
        "last_calibrated": "2026-05-15",
    }
    
    return {
        "status": "healthy" if structural["total_rooms"] > 0 else "degraded",
        "structural": structural,
        "behavioral": behavioral,
    }


def tool_route_query(params: dict) -> dict:
    """Route a query using critical angle analysis."""
    prompt = params.get("prompt", "")
    domain = params.get("domain", "auto")
    max_cost = params.get("max_cost", 0.10)
    
    # Simple domain classification (v1 — hardcoded)
    prompt_lower = prompt.lower()
    
    if domain == "auto":
        # Heuristic domain detection
        math_terms = ["compute", "calculate", "what is", "solve", "sum", "product",
                      "multiply", "divide", "square", "eisenstein", "norm"]
        reason_terms = ["why", "explain", "analyze", "compare", "evaluate", "design",
                       "strategy", "plan", "recommend", "suggest"]
        code_terms = ["code", "function", "class", "implement", "refactor", "bug",
                     "compile", "rust", "python"]
        
        if any(t in prompt_lower for t in math_terms):
            domain = "arithmetic"
        elif any(t in prompt_lower for t in reason_terms):
            domain = "reasoning"
        elif any(t in prompt_lower for t in code_terms):
            domain = "code"
        else:
            domain = "general"
    
    # Critical angle routing table
    ROUTING = {
        "arithmetic": {
            "model": "seed-2.0-mini",
            "provider": "deepinfra",
            "temperature": 0.0,
            "reason": "Infinite critical angle on arithmetic. No depth/magnitude cliff.",
            "cost_per_1k": 0.05,
        },
        "reasoning": {
            "model": "gemini-flash-lite",
            "provider": "deepinfra",
            "temperature": 0.0,
            "reason": "Infinite CA on syllogism and analogy. 82.5% accuracy.",
            "cost_per_1k": 0.002,
        },
        "design": {
            "model": "seed-2.0-mini",
            "provider": "deepinfra",
            "temperature": 0.7,
            "reason": "T=0.7 mode switch activates strategist. 8/8 design tasks.",
            "cost_per_1k": 0.05,
        },
        "code": {
            "model": "glm-5-turbo",
            "provider": "zai",
            "temperature": 0.3,
            "reason": "Code generation needs reasoning + content output.",
            "cost_per_1k": 0.08,
        },
        "general": {
            "model": "seed-2.0-mini",
            "provider": "deepinfra",
            "temperature": 0.0,
            "reason": "Fleet champion for general queries. 89.5% accuracy.",
            "cost_per_1k": 0.05,
        },
    }
    
    route = ROUTING.get(domain, ROUTING["general"])
    
    if route["cost_per_1k"] > max_cost:
        # Downgrade to cheapest
        route = ROUTING["reasoning"]  # gemini-lite at $0.002
    
    return {
        "model": route["model"],
        "provider": route["provider"],
        "temperature": route["temperature"],
        "domain_detected": domain,
        "reason": route["reason"],
        "cost_per_1k": route["cost_per_1k"],
        "savings_vs_gpt4": f"{round((1 - route['cost_per_1k'] / 30) * 100)}%",
    }


def tool_search_tiles(params: dict) -> list:
    """Search tiles by keyword."""
    query = params.get("query", "").lower()
    agent = params.get("agent")
    limit = params.get("limit", 20)
    
    # Search across recent rooms
    rooms = _plato_get("/rooms")
    if not rooms:
        return [{"error": "PLATO unavailable"}]
    
    results = []
    room_list = rooms if isinstance(rooms, list) else rooms.get("rooms", [])
    
    for room in room_list[:30]:  # Search top 30 rooms
        room_id = room.get("id", room.get("room_id", ""))
        data = _plato_get(f"/room/{room_id}/history")
        if not data:
            continue
        
        tiles = data.get("tiles", data) if isinstance(data, dict) else data
        
        for t in tiles:
            q = t.get("question", "").lower()
            a = t.get("answer", "").lower()
            
            if query in q or query in a:
                if agent and t.get("agent", t.get("source", "")) != agent:
                    continue
                results.append({
                    "room_id": room_id,
                    "question": t.get("question", "")[:100],
                    "answer": t.get("answer", "")[:200],
                    "agent": t.get("agent", t.get("source", "")),
                    "relevance": "keyword_match",
                })
                
                if len(results) >= limit:
                    return results
    
    return results


# ─── MCP Server (SSE transport) ───────────────────────────────────────────────

TOOL_HANDLERS = {
    "list_rooms": tool_list_rooms,
    "read_tiles": tool_read_tiles,
    "write_tile": tool_write_tile,
    "query_health": tool_query_health,
    "route_query": tool_route_query,
    "search_tiles": tool_search_tiles,
}


def create_app():
    """Create FastAPI app with MCP endpoints."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    
    app = FastAPI(title="PLATO MCP Server", version="0.1.0")
    
    @app.get("/")
    async def root():
        return {
            "name": "PLATO MCP Server",
            "version": "0.1.0",
            "tools": list(MCP_TOOLS.keys()),
            "plato_url": PLATO_URL,
            "description": "PLATO rooms exposed as MCP tools. Any MCP-compatible agent can use PLATO."
        }
    
    @app.get("/tools")
    async def list_tools():
        return {"tools": list(MCP_TOOLS.values())}
    
    @app.post("/tools/{tool_name}")
    async def call_tool(tool_name: str, request: Request):
        if tool_name not in TOOL_HANDLERS:
            return JSONResponse({"error": f"Unknown tool: {tool_name}"}, status_code=404)
        
        params = await request.json()
        result = TOOL_HANDLERS[tool_name](params)
        
        return {
            "tool": tool_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    @app.get("/health")
    async def health():
        return tool_query_health({})
    
    return app


def main():
    parser = argparse.ArgumentParser(description="PLATO MCP Adapter")
    parser.add_argument("--port", type=int, default=8300)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--demo", action="store_true", help="Run demo without server")
    args = parser.parse_args()
    
    if args.demo:
        print("PLATO MCP ADAPTER — Demo Mode")
        print("=" * 50)
        
        print("\n1. Query Health:")
        health = tool_query_health({})
        print(json.dumps(health, indent=2))
        
        print("\n2. Route Query (arithmetic):")
        route = tool_route_query({"prompt": "What is 5*5 - 5*3 + 3*3?"})
        print(json.dumps(route, indent=2))
        
        print("\n3. Route Query (design):")
        route = tool_route_query({"prompt": "Design a system for real-time fleet coordination"})
        print(json.dumps(route, indent=2))
        
        print("\n4. Route Query (reasoning):")
        route = tool_route_query({"prompt": "Why does the conservation law hold across coupling types?"})
        print(json.dumps(route, indent=2))
        
        print("\n5. List Rooms (forgemaster prefix):")
        rooms = tool_list_rooms({"prefix": "forgemaster", "limit": 5})
        for r in rooms[:5]:
            print(f"  {r['room_id']}: {r['tile_count']} tiles")
        
        return
    
    # Start server
    import uvicorn
    app = create_app()
    print(f"PLATO MCP Server starting on {args.host}:{args.port}")
    print(f"PLATO backend: {PLATO_URL}")
    print(f"Tools: {', '.join(MCP_TOOLS.keys())}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
