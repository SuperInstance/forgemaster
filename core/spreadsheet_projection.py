#!/usr/bin/env python3
"""
PLATO Spreadsheet Projection — 3rd Person Rendering
=====================================================
PLATO rooms are first-class citizens. The spreadsheet is the
human's 3rd-person rendering layer. Each cell can be a tile,
room, application, folder, file, string, value — or its own
array you zoom into.

Deckboss adds flowchart projection for when maintenance on
interconnections is needed. The spreadsheet gives us group
mathematics for discovering bottlenecks and break points.

Built on the insights from SuperInstance-papers and
spreadsheet-moment: cells as instances, origin-centric math,
confidence cascades.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional, List, Tuple, Dict


# ── Cell Types ──
# Each cell can be any of these. A tile is a cell.
# A room is a cell. A value is a cell. An array is a cell.

CELL_TYPE_TILE = "tile"
CELL_TYPE_ROOM = "room"
CELL_TYPE_APPLICATION = "application"
CELL_TYPE_FOLDER = "folder"
CELL_TYPE_FILE = "file"
CELL_TYPE_STRING = "string"
CELL_TYPE_VALUE = "value"
CELL_TYPE_ARRAY = "array"
CELL_TYPE_INSTANCE = "instance"  # running micro model
CELL_TYPE_GRAPH_NODE = "graph_node"


@dataclass
class SpreadsheetCell:
    """One cell in the PLATO spreadsheet projection.
    
    Any PLATO entity can be rendered as a cell.
    Every cell carries its origin (room, author, timestamp)
    and its current state (value, confidence, dependencies).
    
    A cell can be its own array — zoom in to see sub-cells.
    """
    cell_id: str
    cell_type: str
    value: Any = None
    formula: str = ""  # the expression that produces this cell's value
    dependencies: List[str] = field(default_factory=list)  # cells this depends on
    dependents: List[str] = field(default_factory=list)  # cells that depend on this
    room_origin: str = ""  # which PLATO room this cell renders
    tile_origin: str = ""  # which PLATO tile (if applicable)
    confidence: float = 0.0
    last_updated: float = field(default_factory=time.time)
    children: List[str] = field(default_factory=list)  # sub-cells (for arrays/rooms)
    metadata: dict = field(default_factory=dict)
    error: str = ""
    
    def zoom_in(self) -> List['SpreadsheetCell']:
        """If this cell is an array or room, return its sub-cells."""
        if self.cell_type in (CELL_TYPE_ARRAY, CELL_TYPE_ROOM, CELL_TYPE_FOLDER):
            # Return children as cells
            return [SpreadsheetCell(child_id, CELL_TYPE_TILE)
                    for child_id in self.children]
        return [self]
    
    def recalculate(self) -> Any:
        """Recalculate this cell's value from its dependencies."""
        if not self.formula:
            return self.value
        # Formula evaluation would happen here
        return self.value


@dataclass
class SpreadsheetProjection:
    """A 2D grid of cells projecting PLATO rooms.
    
    The spreadsheet IS the human interface to PLATO.
    Rooms become sheets. Tiles become cells. Values become formulas.
    Inter-room connections become dependency graphs.
    
    Deckboss adds flowchart projection for when maintenance
    on interconnections is needed — toggle between 'sheet view'
    and 'graph view' for any set of cells.
    """
    name: str
    cells: Dict[str, SpreadsheetCell] = field(default_factory=dict)
    rows: int = 100
    cols: int = 26
    view_mode: str = "spreadsheet"  # or "flowchart" (Deckboss mode)
    created: float = field(default_factory=time.time)
    
    def place_cell(self, cell: SpreadsheetCell, row: int, col: int):
        """Place a cell at a grid position."""
        pos = f"{row}:{col}"
        self.cells[cell.cell_id] = cell
        setattr(self, pos, cell.cell_id)
    
    def cells_from_room(self, room_name: str, tiles: list) -> List[SpreadsheetCell]:
        """Convert a PLATO room's tiles into spreadsheet cells."""
        cells = []
        for i, tile in enumerate(tiles):
            cell = SpreadsheetCell(
                cell_id=f"{room_name}:tile:{i}",
                cell_type=CELL_TYPE_TILE,
                value=tile.get("answer", tile.get("content", "")),
                formula=f"=TILE({room_name}, {i})",
                room_origin=room_name,
                tile_origin=tile.get("hash", tile.get("id", f"tile-{i}")),
                confidence=tile.get("confidence", 0.0),
                metadata={
                    "source": tile.get("source", ""),
                    "type": tile.get("type", "knowledge"),
                }
            )
            cells.append(cell)
            row = len(cells)
            self.place_cell(cell, row, 0)
        
        return cells
    
    def dependency_graph(self) -> Dict[str, List[str]]:
        """Build the dependency graph from all cells.
        
        Deckboss mode: render as flow chart for maintenance.
        Each edge is a dependency. Bottlenecks are cells with
        many dependents. Break points are cells with many
        dependencies but LOW confidence.
        """
        graph = {}
        for cid, cell in self.cells.items():
            graph[cid] = cell.dependencies
        
        return graph
    
    def find_bottlenecks(self) -> List[Tuple[str, int]]:
        """Find bottleneck cells: cells with the most dependents."""
        bottleneck_scores = []
        for cid, cell in self.cells.items():
            score = len(cell.dependents)
            if score > 0:
                bottleneck_scores.append((cid, score))
        bottleneck_scores.sort(key=lambda x: -x[1])
        return bottleneck_scores[:10]
    
    def find_break_points(self) -> List[Tuple[str, float]]:
        """Find break points: cells with many dependencies but low confidence."""
        break_points = []
        for cid, cell in self.cells.items():
            if len(cell.dependencies) > 3 and cell.confidence < 0.5:
                break_points.append((cid, cell.confidence))
        break_points.sort(key=lambda x: x[1])  # lowest confidence first
        return break_points[:10]
    
    def cascade_from(self, cell_id: str) -> List[str]:
        """Simulate what happens if cell_id changes.
        
        Returns all cells that would need recalculation.
        Like a spreadsheet: change one cell, all dependents recalculate.
        """
        affected = []
        to_process = [cell_id]
        processed = set()
        
        while to_process:
            current = to_process.pop(0)
            if current in processed:
                continue
            processed.add(current)
            
            cell = self.cells.get(current)
            if cell:
                affected.append(current)
                for dep_id in cell.dependents:
                    if dep_id not in processed:
                        to_process.append(dep_id)
        
        return affected
    
    def group_statistics(self) -> dict:
        """Spreadsheet-style group math on the cell population."""
        values = [c.value for c in self.cells.values() 
                  if isinstance(c.value, (int, float))]
        
        stats = {}
        if values:
            stats["count"] = len(values)
            stats["sum"] = sum(values)
            stats["mean"] = sum(values) / len(values)
            stats["min"] = min(values)
            stats["max"] = max(values)
        
        # Group by cell type
        by_type = {}
        for cid, cell in self.cells.items():
            t = cell.cell_type
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(cid)
        
        stats["by_type"] = {k: len(v) for k, v in by_type.items()}
        stats["total_cells"] = len(self.cells)
        stats["dependency_edges"] = sum(len(c.dependencies) for c in self.cells.values())
        
        return stats


class PLATOSpreadsheet:
    """The bridge between PLATO rooms and spreadsheet projection.
    
    PLATO rooms are first-class citizens.
    The spreadsheet is the human's 3rd-person rendering layer.
    
    Each room → sheet. Each tile → row. Each value → formula.
    Inter-room connections → cross-sheet references.
    """
    
    def __init__(self):
        self.projections = {}  # room_name -> SpreadsheetProjection
        self.live_rooms = {}   # room_name -> [tile_dicts]
    
    def sync_room(self, room_name: str, tiles: list) -> SpreadsheetProjection:
        """Sync a PLATO room to a spreadsheet projection."""
        proj = SpreadsheetProjection(name=f"PLATO: {room_name}")
        proj.cells_from_room(room_name, tiles)
        self.projections[room_name] = proj
        self.live_rooms[room_name] = tiles
        return proj
    
    def sync_all_rooms(self, all_rooms: dict):
        """Sync all PLATO rooms to projections."""
        for room_name, tiles in all_rooms.items():
            self.sync_room(room_name, tiles)
    
    def cross_room_dependencies(self) -> Dict[str, List[str]]:
        """Find cells that reference other rooms.
        
        Tiles from forge that reference flux-engine tiles.
        Probing across rooms creates cross-sheet references.
        """
        cross_refs = {}
        for room_name, proj in self.projections.items():
            room_refs = []
            for cid, cell in proj.cells.items():
                # Any cell that references data from another room
                for dep_id in cell.dependencies:
                    for other_name in self.projections:
                        if other_name != room_name and dep_id.startswith(other_name):
                            room_refs.append((cell.cell_id, other_name, dep_id))
            if room_refs:
                cross_refs[room_name] = room_refs
        return cross_refs
    
    def master_spreadsheet(self) -> SpreadsheetProjection:
        """The master view: all rooms in one spreadsheet."""
        master = SpreadsheetProjection(name="PLATO Master", 
                                        rows=1000, cols=100)
        master.cells["__summary__"] = SpreadsheetCell(
            cell_id="__summary__",
            cell_type=CELL_TYPE_ROOM,
            value={"rooms": len(self.projections), 
                   "total_tiles": sum(len(p.cells) for p in self.projections.values())},
        )
        
        row = 1
        for room_name, proj in self.projections.items():
            # Room as a row
            room_cell = SpreadsheetCell(
                cell_id=f"room:{room_name}",
                cell_type=CELL_TYPE_ROOM,
                value=room_name,
                children=list(proj.cells.keys()),
            )
            master.place_cell(room_cell, row, 0)
            
            # Tile count as a column
            count_cell = SpreadsheetCell(
                cell_id=f"room:{room_name}:count",
                cell_type=CELL_TYPE_VALUE,
                value=len(proj.cells),
                formula=f"=COUNT({room_name})",
            )
            master.place_cell(count_cell, row, 1)
            
            # Average confidence in another column
            confs = [c.confidence for c in proj.cells.values() if c.confidence > 0]
            avg_conf = sum(confs) / len(confs) if confs else 0
            conf_cell = SpreadsheetCell(
                cell_id=f"room:{room_name}:avg_conf",
                cell_type=CELL_TYPE_VALUE,
                value=round(avg_conf, 3),
                formula=f"=AVERAGE({room_name}:confidence)",
            )
            master.place_cell(conf_cell, row, 2)
            
            row += 1
        
        return master
    
    def to_deckboss_flowchart(self) -> dict:
        """Deckboss mode: render as flow chart.
        
        Toggle between sheet view and graph view.
        For maintenance: see all interconnections, find bottlenecks.
        """
        nodes = []
        edges = []
        
        for room_name, proj in self.projections.items():
            nodes.append({
                "id": room_name,
                "type": "room",
                "cells": len(proj.cells),
                "bottlenecks": [b[0] for b in proj.find_bottlenecks()[:3]],
            })
            
            # Cross-room edges
            for cid, cell in proj.cells.items():
                for dep_id in cell.dependencies:
                    for other_name in self.projections:
                        if other_name != room_name and dep_id.startswith(other_name):
                            edges.append({
                                "from": f"{room_name}:{cid}",
                                "to": dep_id,
                                "weight": cell.confidence,
                            })
        
        return {
            "view_mode": "flowchart",
            "nodes": nodes,
            "edges": edges,
            "bottlenecks": self._global_bottlenecks(),
            "break_points": self._global_break_points(),
        }
    
    def _global_bottlenecks(self) -> list:
        """Global bottleneck analysis across all rooms."""
        all_bottlenecks = []
        for room_name, proj in self.projections.items():
            for cid, score in proj.find_bottlenecks():
                all_bottlenecks.append((f"{room_name}:{cid}", score))
        all_bottlenecks.sort(key=lambda x: -x[1])
        return all_bottlenecks[:10]
    
    def _global_break_points(self) -> list:
        """Global break point analysis."""
        all_breaks = []
        for room_name, proj in self.projections.items():
            for cid, conf in proj.find_break_points():
                all_breaks.append((f"{room_name}:{cid}", conf))
        all_breaks.sort(key=lambda x: x[1])
        return all_breaks[:10]


def demo():
    """Demonstrate PLATO as spreadsheet projection."""
    print("=" * 70)
    print("  PLATO SPREADSHEET PROJECTION")
    print("  3rd-Person Rendering — Human Interface to Room Architecture")
    print("=" * 70)
    
    # Create some PLATO room data
    rooms = {
        "forge": [
            {"answer": "constraint alpha=0.05 converges", "hash": "t1", "confidence": 0.9, "source": "forgemaster"},
            {"answer": "drift detected at cycle 847", "hash": "t2", "confidence": 0.85, "source": "servo-mind"},
            {"answer": "disproof gate accepted 12/15", "hash": "t3", "confidence": 0.95, "source": "gate"},
        ],
        "flux": [
            {"answer": "β₁ attractor at 666", "hash": "t4", "confidence": 0.8, "source": "oracle1"},
            {"answer": "step delta = 31", "hash": "t5", "confidence": 0.75, "source": "oracle1"},
            {"answer": "conservation law holds at V=50", "hash": "t6", "confidence": 0.9, "source": "flux-engine"},
        ],
    }
    
    # Sync to spreadsheet
    bridge = PLATOSpreadsheet()
    bridge.sync_all_rooms(rooms)
    
    master = bridge.master_spreadsheet()
    
    print(f"\n  MASTER SPREADSHEET:")
    print(f"  {len(rooms)} rooms synced to sheets")
    for room_name in rooms:
        proj = bridge.projections[room_name]
        print(f"  • Sheet '{room_name}': {len(proj.cells)} cells/tiles")
    
    print(f"\n  📊 GROUP STATISTICS:")
    stats = master.group_statistics()
    print(f"  Total cells: {stats['total_cells']}")
    print(f"  Dependency edges: {stats['dependency_edges']}")
    print(f"  By type: {stats['by_type']}")
    
    print(f"\n  🔍 BOTTLENECK ANALYSIS:")
    print(f"  (Cells with most dependents — high load)")
    bottlenecks = master.find_bottlenecks()
    for cid, score in bottlenecks[:3]:
        print(f"  • {cid}: {score} dependents")
    
    breakpoints = master.find_break_points()
    print(f"\n  💥 BREAK POINT ANALYSIS:")
    print(f"  (Cells with many deps but low confidence)")
    for cid, conf in breakpoints[:3]:
        print(f"  • {cid}: confidence={conf}")
    
    print(f"\n  🗺️ CASCADE ANALYSIS:")
    print(f"  (If forge:tile:1 changes, these cells recalculate:)")
    if "forge" in bridge.projections:
        proj = bridge.projections["forge"]
        affected = proj.cascade_from("forge:tile:1")
        for a in affected[:5]:
            print(f"  • {a}")
    
    print(f"\n  🛩️ DECKBOSS FLOWCHART MODE:")
    flowchart = bridge.to_deckboss_flowchart()
    print(f"  Nodes: {len(flowchart['nodes'])}")
    print(f"  Edges: {len(flowchart['edges'])}")
    print(f"  View: {flowchart['view_mode']}")
    
    print(f"\n  Cross-room dependencies:")
    cross = bridge.cross_room_dependencies()
    if cross:
        for room, refs in cross.items():
            print(f"  • {room} references {len(refs)} external cells")
    
    print(f"\n{'='*70}")
    print("  PLATO rooms are first-class citizens.")
    print("  The spreadsheet is the human's 3rd-person rendering layer.")
    print("  Toggle between sheet view (spreadsheet) and graph view (Deckboss).")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
