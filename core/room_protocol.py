#!/usr/bin/env python3
"""core/room_protocol.py — PLATO rooms as execution contexts, not storage.

THE CORE INSIGHT (Casey's abstraction):

Everything is either a loop or a single run.
Either can be embedded into PLATO as a room.
Rooms are pulled out anytime or built into applications through PLATO.

A room is not a database table. It is an EXECUTION CONTEXT:
  - It holds state (tiles)
  - It enforces protocol (what tiles are valid, in what order)
  - It has lifecycle (creation, active, paused, complete)
  - It can be rendered by anything (CLI, web, agent, algorithm)

THE PATTERN:
  ROOM  = state + protocol + lifecycle
  TILE  = frozen step in any loop
  AGENT = anything that reads/writes tiles
  RENDERER = anything that reads tiles and displays

EXAMPLE ROOMS:
  - Claude Code loop room (observe→think→tool→observe as tile protocol)
  - Card game room (deal→play→score as tile protocol, any renderer)
  - Website room (component tiles that render to any web framework)
  - Experiment room (hypothesis→probe→result→analysis loop)
  - Fleet coordination room (task→claim→execute→report loop)

This file defines the protocol layer. Concrete rooms are built on top.
"""

from __future__ import annotations

import json, os, time, uuid, re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Type
from datetime import datetime
from enum import Enum
from collections import defaultdict

PLATO_URL = "http://147.224.38.131:8847"


# ─── Core Types ────────────────────────────────────────────────────────────────

class TilePhase(Enum):
    """Where a tile sits in the loop cycle."""
    INPUT = "input"           # Data/state entering the room
    PROCESSING = "processing" # Agent is working on it
    OUTPUT = "output"         # Result produced
    FEEDBACK = "feedback"     # Evaluation of the output
    COMPLETE = "complete"     # Final state, loop iteration done


class RoomLifecycle(Enum):
    """Room-level lifecycle states."""
    CREATED = "created"       # Room exists but no tiles yet
    ACTIVE = "active"         # Loop is running
    PAUSED = "paused"         # Loop paused (can resume)
    COMPLETE = "complete"     # Loop finished
    ARCHIVED = "archived"     # Historical, read-only


class LoopType(Enum):
    """What kind of loop this room runs."""
    AGENTIC = "agentic"       # observe→think→tool→observe (Claude Code pattern)
    TURN_BASED = "turn_based" # Players take turns (card games, debates)
    PIPELINE = "pipeline"     # Linear stages (build→test→deploy)
    EVOLUTIONARY = "evolutionary"  # Generate variants→evaluate→select→mutate
    CONTINUOUS = "continuous" # Always running, tiles flow through
    SINGLE_RUN = "single_run" # One shot, no loop


@dataclass
class TileSchema:
    """Schema for valid tiles in a room.
    
    This is the PROTOCOL layer — it defines what tiles are acceptable,
    what fields they must have, and what transitions are valid.
    
    Like a type system for the room. Any agent that wants to write
    to this room must produce tiles that match the schema.
    """
    tile_type: str
    required_fields: List[str]
    optional_fields: List[str] = field(default_factory=list)
    valid_phases: List[TilePhase] = field(default_factory=lambda: list(TilePhase))
    valid_transitions: Dict[TilePhase, List[TilePhase]] = field(default_factory=dict)
    
    def validate(self, tile_data: dict) -> tuple[bool, str]:
        """Check if a tile matches this schema."""
        for f in self.required_fields:
            if f not in tile_data:
                return False, f"Missing required field: {f}"
        return True, "Valid"


@dataclass
class RoomProtocol:
    """The protocol a room enforces.
    
    This is what makes a room an EXECUTION CONTEXT rather than storage:
      - What tile types are accepted
      - What transitions are valid
      - What agents can participate
      - What the loop structure is
    """
    room_type: str
    loop_type: LoopType
    tile_schemas: Dict[str, TileSchema] = field(default_factory=dict)
    lifecycle: RoomLifecycle = RoomLifecycle.CREATED
    max_iterations: Optional[int] = None  # None = infinite
    participants: List[str] = field(default_factory=list)  # Agent IDs
    renderer_hints: Dict[str, str] = field(default_factory=dict)
    
    def validate_tile(self, tile_data: dict) -> tuple[bool, str]:
        """Validate a tile against the room's schemas."""
        tile_type = tile_data.get("tile_type", "")
        if tile_type in self.tile_schemas:
            return self.tile_schemas[tile_type].validate(tile_data)
        # Unknown tile types are allowed (extensibility)
        return True, "Unknown type accepted"


# ─── Room Templates ────────────────────────────────────────────────────────────

def make_agentic_loop_room(task: str, agent_id: str = None) -> RoomProtocol:
    """Create a room that runs the Claude Code agentic loop pattern.
    
    The loop: observe → think → tool → observe
    As tiles: INPUT → PROCESSING → OUTPUT → INPUT (cycle)
    
    This is the PLATO-native version of Claude Code.
    No subprocess. No wrapper. The room IS the loop.
    """
    return RoomProtocol(
        room_type="agentic_loop",
        loop_type=LoopType.AGENTIC,
        tile_schemas={
            "observation": TileSchema(
                tile_type="observation",
                required_fields=["content", "step"],
                valid_phases=[TilePhase.INPUT],
            ),
            "thought": TileSchema(
                tile_type="thought",
                required_fields=["content", "step", "observation_id"],
                valid_phases=[TilePhase.PROCESSING],
            ),
            "tool_call": TileSchema(
                tile_type="tool_call",
                required_fields=["tool", "args", "step", "thought_id"],
                valid_phases=[TilePhase.PROCESSING],
            ),
            "tool_result": TileSchema(
                tile_type="tool_result",
                required_fields=["content", "step", "tool_call_id"],
                valid_phases=[TilePhase.OUTPUT],
            ),
        },
        participants=[agent_id] if agent_id else [],
        renderer_hints={
            "type": "agentic_loop",
            "display": "step_by_step",
            "visual": "flow_graph",
        },
    )


def make_game_room(game_type: str, players: List[str] = None,
                   max_rounds: int = None) -> RoomProtocol:
    """Create a room for a turn-based game.
    
    Games are just loops with turns. The tiles carry:
      - Game state (board, hands, scores)
      - Moves (what each player did)
      - Events (deals, draws, triggers)
    
    Any renderer can pick up these tiles:
      - CLI: ASCII art
      - Web: HTML/CSS cards and boards
      - Agent: JSON parsing at microsecond speed
      - 3D: Render tiles as spatial objects
    
    The room doesn't know about rendering. It just holds the game.
    """
    return RoomProtocol(
        room_type=f"game:{game_type}",
        loop_type=LoopType.TURN_BASED,
        tile_schemas={
            "game_state": TileSchema(
                tile_type="game_state",
                required_fields=["state", "round", "current_player"],
                valid_phases=[TilePhase.INPUT],
            ),
            "move": TileSchema(
                tile_type="move",
                required_fields=["player", "action", "round"],
                valid_phases=[TilePhase.PROCESSING],
            ),
            "event": TileSchema(
                tile_type="event",
                required_fields=["event_type", "data", "round"],
                valid_phases=[TilePhase.OUTPUT],
            ),
            "score": TileSchema(
                tile_type="score",
                required_fields=["player", "score", "round"],
                valid_phases=[TilePhase.COMPLETE],
            ),
        },
        participants=players or [],
        max_iterations=max_rounds,
        renderer_hints={
            "type": "game",
            "game": game_type,
            "display": "board_and_cards",
            "visual": "2d_or_3d",
        },
    )


def make_website_room(site_name: str, pages: List[str] = None) -> RoomProtocol:
    """Create a room that IS a website.
    
    Each tile is a component state:
      - Layout tiles (header, nav, content, footer)
      - Style tiles (CSS rules)
      - Content tiles (text, images, data)
      - Interaction tiles (forms, buttons, handlers)
    
    Any web renderer can read these tiles:
      - Static HTML generator
      - React/Vue/Svelte app
      - Server-side template
      - PDF generator
      - Accessibility renderer (screen reader)
    
    The room is the source of truth. The framework is just a view.
    """
    return RoomProtocol(
        room_type="website",
        loop_type=LoopType.CONTINUOUS,
        tile_schemas={
            "layout": TileSchema(
                tile_type="layout",
                required_fields=["component", "structure"],
            ),
            "style": TileSchema(
                tile_type="style",
                required_fields=["selector", "rules"],
            ),
            "content": TileSchema(
                tile_type="content",
                required_fields=["component", "data"],
            ),
            "interaction": TileSchema(
                tile_type="interaction",
                required_fields=["element", "event", "handler"],
            ),
            "page": TileSchema(
                tile_type="page",
                required_fields=["path", "layout_id", "content_ids"],
            ),
        },
        renderer_hints={
            "type": "website",
            "site": site_name,
            "pages": pages or [],
            "display": "web_browser",
            "frameworks": ["html", "react", "svelte", "vue", "astro"],
        },
    )


def make_experiment_room(hypothesis: str, variables: List[str] = None) -> RoomProtocol:
    """Create a room that runs the scientific method as a loop.
    
    The loop: hypothesis → probe → result → analysis → refined hypothesis
    As tiles: INPUT → PROCESSING → OUTPUT → FEEDBACK → INPUT (cycle)
    
    This is the Wheel of Discovery as a room protocol.
    """
    return RoomProtocol(
        room_type="experiment",
        loop_type=LoopType.AGENTIC,
        tile_schemas={
            "hypothesis": TileSchema(
                tile_type="hypothesis",
                required_fields=["claim", "falsification_criteria", "confidence"],
            ),
            "probe": TileSchema(
                tile_type="probe",
                required_fields=["query", "model", "expected_range"],
            ),
            "result": TileSchema(
                tile_type="result",
                required_fields=["answer", "model", "correct", "latency_ms"],
            ),
            "analysis": TileSchema(
                tile_type="analysis",
                required_fields=["finding", "confidence", "next_probe"],
            ),
        },
        renderer_hints={
            "type": "experiment",
            "display": "dashboard",
            "visual": "chart_tree",
        },
    )


def make_evolution_room(target: str, n_variants: int = 10) -> RoomProtocol:
    """Create a room that runs evolutionary optimization.
    
    The loop: generate N variants → evaluate → select best → mutate → repeat
    As tiles: batches of OUTPUT tiles → FEEDBACK tiles → new OUTPUT tiles
    
    This is the asymmetric pruning loop from the idea doc,
    but with the math implemented as Python validators, not prompts.
    """
    return RoomProtocol(
        room_type="evolution",
        loop_type=LoopType.EVOLUTIONARY,
        tile_schemas={
            "variant": TileSchema(
                tile_type="variant",
                required_fields=["code", "generation", "variant_id"],
            ),
            "evaluation": TileSchema(
                tile_type="evaluation",
                required_fields=["variant_id", "scores", "pass"],
                optional_fields=["jaccard_distance", "fiedler_value", "nmi_score"],
            ),
            "selection": TileSchema(
                tile_type="selection",
                required_fields=["generation", "selected_ids", "reason"],
            ),
            "mutation": TileSchema(
                tile_type="mutation",
                required_fields=["parent_id", "mutation_type", "code"],
            ),
        },
        max_iterations=100,  # Generations
        renderer_hints={
            "type": "evolution",
            "display": "fitness_over_time",
            "visual": "tree_or_graph",
        },
    )


# ─── Room Runtime ──────────────────────────────────────────────────────────────

@dataclass
class RoomTile:
    """A tile in a room, with protocol metadata."""
    tile_id: str
    room_id: str
    tile_type: str
    phase: TilePhase
    agent: str
    content: dict
    timestamp: str = ""
    parent_id: Optional[str] = None  # For branching
    iteration: int = 0
    
    @staticmethod
    def create(room_id: str, tile_type: str, phase: TilePhase,
               agent: str, content: dict, parent_id: str = None,
               iteration: int = 0) -> 'RoomTile':
        return RoomTile(
            tile_id=uuid.uuid4().hex[:12],
            room_id=room_id,
            tile_type=tile_type,
            phase=phase,
            agent=agent,
            content=content,
            timestamp=datetime.utcnow().isoformat() + "Z",
            parent_id=parent_id,
            iteration=iteration,
        )


class PLATORoom:
    """A PLATO room with protocol enforcement.
    
    This is the runtime that makes rooms into execution contexts.
    It reads/writes to PLATO server but adds:
      - Schema validation
      - Phase enforcement
      - Lifecycle management
      - Rendering hints
    """
    
    def __init__(self, room_id: str, protocol: RoomProtocol):
        self.room_id = room_id
        self.protocol = protocol
        self.tiles: List[RoomTile] = []
        self.iteration = 0
        self.state: Dict[str, Any] = {}
    
    def write_tile(self, tile_type: str, phase: TilePhase,
                   agent: str, content: dict,
                   parent_id: str = None) -> RoomTile:
        """Write a tile to the room. Validates against protocol."""
        tile_data = {
            "tile_type": tile_type,
            "phase": phase.value,
            "agent": agent,
            **content,
        }
        
        valid, msg = self.protocol.validate_tile(tile_data)
        if not valid:
            raise ValueError(f"Tile rejected: {msg}")
        
        tile = RoomTile.create(
            room_id=self.room_id,
            tile_type=tile_type,
            phase=phase,
            agent=agent,
            content=content,
            parent_id=parent_id,
            iteration=self.iteration,
        )
        
        self.tiles.append(tile)
        
        # Track iterations (loops back to INPUT = new iteration)
        if phase == TilePhase.INPUT and self.tiles:
            self.iteration += 1
        
        # Persist to PLATO server
        self._persist(tile)
        
        return tile
    
    def read_tiles(self, tile_type: str = None, phase: TilePhase = None,
                   agent: str = None, limit: int = 10) -> List[RoomTile]:
        """Read tiles from the room, optionally filtered."""
        results = self.tiles
        if tile_type:
            results = [t for t in results if t.tile_type == tile_type]
        if phase:
            results = [t for t in results if t.phase == phase]
        if agent:
            results = [t for t in results if t.agent == agent]
        return results[-limit:]
    
    def latest(self, tile_type: str = None) -> Optional[RoomTile]:
        """Get the most recent tile of a given type."""
        if tile_type:
            matching = [t for t in self.tiles if t.tile_type == tile_type]
        else:
            matching = self.tiles
        return matching[-1] if matching else None
    
    def branch(self, tile_id: str, new_agent: str = None) -> 'PLATORoom':
        """Branch from a specific tile with a different agent.
        
        This is the rewind-and-branch pattern:
        Take the room state at tile_id, fork it, continue with new agent.
        The original room continues. The branch is a new room.
        """
        # Find the branch point
        branch_idx = next(
            (i for i, t in enumerate(self.tiles) if t.tile_id == tile_id),
            len(self.tiles)
        )
        
        # Create new room with same protocol
        new_room = PLATORoom(
            room_id=f"{self.room_id}-branch-{uuid.uuid4().hex[:6]}",
            protocol=self.protocol,
        )
        
        # Copy tiles up to branch point
        new_room.tiles = self.tiles[:branch_idx + 1]
        new_room.iteration = self.iteration
        new_room.state = dict(self.state)
        
        return new_room
    
    def render(self, format: str = "json") -> str:
        """Render the room state for display.
        
        The room doesn't know HOW to display itself.
        It provides the data. The renderer decides the format.
        """
        if format == "json":
            return json.dumps({
                "room_id": self.room_id,
                "protocol": {
                    "type": self.protocol.room_type,
                    "loop": self.protocol.loop_type.value,
                    "lifecycle": self.protocol.lifecycle.value,
                },
                "tiles": [asdict(t) for t in self.tiles[-20:]],
                "iteration": self.iteration,
                "state": self.state,
                "renderer_hints": self.protocol.renderer_hints,
            }, indent=2, default=str)
        elif format == "summary":
            lines = [
                f"Room: {self.room_id} ({self.protocol.room_type})",
                f"Loop: {self.protocol.loop_type.value} | Iteration: {self.iteration}",
                f"Tiles: {len(self.tiles)} | State: {self.protocol.lifecycle.value}",
                "",
                "Recent tiles:",
            ]
            for t in self.tiles[-5:]:
                lines.append(f"  [{t.phase.value:10s}] {t.tile_type}: {json.dumps(t.content)[:60]}")
            return "\n".join(lines)
        else:
            return self.render("json")
    
    def _persist(self, tile: RoomTile):
        """Persist tile to PLATO server."""
        try:
            import requests
            payload = {
                "room_id": self.room_id,
                "domain": self.room_id.split("-")[0] if "-" in self.room_id else "general",
                "agent": tile.agent,
                "question": f"{tile.tile_type}:{tile.phase.value}",
                "answer": json.dumps(tile.content, default=str),
                "tile_type": tile.tile_type,
            }
            requests.post(f"{PLATO_URL}/submit", json=payload, timeout=5)
        except:
            pass  # PLATO unavailable, room still works locally


# ─── The Agentic Loop as a Room ────────────────────────────────────────────────

def run_agentic_loop(room: PLATORoom, agent_id: str,
                     observe_fn: Callable,
                     think_fn: Callable,
                     tool_fn: Callable,
                     max_steps: int = 10) -> PLATORoom:
    """Run the Claude Code agentic loop pattern in a PLATO room.
    
    This is the loop: observe → think → tool → observe
    But each step is a tile in the room, not a subprocess call.
    
    observe_fn: reads state, returns observation dict
    think_fn: reads observation, returns thought dict
    tool_fn: reads thought, returns (tool_result, should_continue)
    """
    for step in range(max_steps):
        # OBSERVE
        obs = observe_fn(room, step)
        obs_tile = room.write_tile("observation", TilePhase.INPUT, agent_id, obs)
        
        # THINK
        thought = think_fn(room, obs, step)
        thought_tile = room.write_tile(
            "thought", TilePhase.PROCESSING, agent_id, thought,
            parent_id=obs_tile.tile_id
        )
        
        # TOOL
        result, should_continue = tool_fn(room, thought, step)
        result_tile = room.write_tile(
            "tool_result", TilePhase.OUTPUT, agent_id, result,
            parent_id=thought_tile.tile_id
        )
        
        if not should_continue:
            room.write_tile("done", TilePhase.COMPLETE, agent_id,
                          {"reason": "task_complete", "steps": step + 1})
            break
    
    room.protocol.lifecycle = RoomLifecycle.COMPLETE
    return room


def main():
    import argparse
    p = argparse.ArgumentParser(description="PLATO Room Protocol")
    p.add_argument("--demo", choices=["agentic", "game", "website", "experiment", "evolution"],
                   default="agentic")
    args = p.parse_args()
    
    print("PLATO ROOM PROTOCOL — Rooms as Execution Contexts")
    print("=" * 60)
    print()
    
    if args.demo == "agentic":
        protocol = make_agentic_loop_room("Test agentic loop", agent_id="test-agent")
        room = PLATORoom("test-agentic-loop", protocol)
        
        # Simulate a few loop iterations
        room.write_tile("observation", TilePhase.INPUT, "test-agent",
                       {"content": "User asked to compute a*a - a*b + b*b", "step": 0})
        room.write_tile("thought", TilePhase.PROCESSING, "test-agent",
                       {"content": "Need to substitute a=5, b=3", "step": 0, "observation_id": "obs-0"})
        room.write_tile("tool_call", TilePhase.PROCESSING, "test-agent",
                       {"tool": "calculator", "args": "5*5 - 5*3 + 3*3", "step": 0, "thought_id": "th-0"})
        room.write_tile("tool_result", TilePhase.OUTPUT, "test-agent",
                       {"content": "19", "step": 0, "tool_call_id": "tc-0"})
        room.write_tile("observation", TilePhase.INPUT, "test-agent",
                       {"content": "Result is 19. Task complete.", "step": 1})
        
        print(room.render("summary"))
    
    elif args.demo == "game":
        protocol = make_game_room("poker", players=["alice", "bob", "carol"])
        room = PLATORoom("game-poker-001", protocol)
        
        room.write_tile("game_state", TilePhase.INPUT, "dealer",
                       {"state": "dealing", "round": 1, "current_player": "alice"})
        room.write_tile("event", TilePhase.OUTPUT, "dealer",
                       {"event_type": "deal", "data": {"alice": "A♠ K♠", "bob": "Q♥ J♥"}, "round": 1})
        room.write_tile("move", TilePhase.PROCESSING, "alice",
                       {"player": "alice", "action": "raise", "round": 1})
        room.write_tile("move", TilePhase.PROCESSING, "bob",
                       {"player": "bob", "action": "call", "round": 1})
        
        print(room.render("summary"))
        print("\nThis room can render to:")
        print("  - CLI (ASCII cards)")
        print("  - Web (HTML card components)")
        print("  - Agent (JSON at microsecond speed)")
        print("  - 3D (spatial card positions)")
    
    elif args.demo == "website":
        protocol = make_website_room("cocapn.ai", pages=["/", "/demos", "/api"])
        room = PLATORoom("website-cocapn", protocol)
        
        room.write_tile("layout", TilePhase.INPUT, "designer",
                       {"component": "header", "structure": {"nav": ["home", "demos", "api"]}})
        room.write_tile("style", TilePhase.INPUT, "designer",
                       {"selector": ".header", "rules": {"background": "#1a1a2e", "color": "#e94560"}})
        room.write_tile("content", TilePhase.INPUT, "designer",
                       {"component": "hero", "data": {"title": "Constraint Theory", "subtitle": "Zero drift"}})
        room.write_tile("page", TilePhase.INPUT, "designer",
                       {"path": "/", "layout_id": "main", "content_ids": ["header", "hero"]})
        
        print(room.render("summary"))
        print("\nThis room can render to:")
        print("  - Static HTML")
        print("  - React app")
        print("  - Astro site")
        print("  - PDF document")
        print("  - Screen reader output")
    
    print("\n" + "=" * 60)
    print("EVERYTHING IS EITHER A LOOP OR A SINGLE RUN.")
    print("EITHER CAN BE EMBEDDED INTO PLATO AS A ROOM.")
    print("ROOMS ARE PULLED OUT ANYTIME OR BUILT INTO APPLICATIONS.")
    print("THE ROOM IS THE LOOP. THE TILE IS THE STEP. THE AGENT IS THE DANCER.")


if __name__ == "__main__":
    main()
