#!/usr/bin/env python3
"""
Chess Arena — ZeroClaw PRIME's PLATO Chess Room
=================================================
A self-orienting chess room where:
  - PRIME plays against a built-in minimax engine
  - Zero-shot agents can walk in and play immediately
  - Every game is logged as PLATO tiles
  - The room interface IS the tile format — agents communicate through tiles

The room presents itself so a zero-shot agent understands:
  - What the room is (chess arena)
  - How to join (drop a move tile)
  - What the house algorithm does (responds to your move)
"""

import os, sys, json, time, hashlib, shutil, tempfile, subprocess
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

# Add core to path for git_plato import
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from git_plato import PlatoRoom, PlatoAgent

import chess
import chess.polyglot


# ---------------------------------------------------------------------------
# Chess Engine — Minimax with Alpha-Beta Pruning
# ---------------------------------------------------------------------------

PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
}

# Piece-square tables (from white's perspective, flipped for black)
PST_PAWN = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

PST_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]


def evaluate_board(board: chess.Board) -> float:
    """Evaluate board position. Positive = white advantage."""
    if board.is_checkmate():
        return -99999 if board.turn == chess.WHITE else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0.0

    score = 0.0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        val = PIECE_VALUES.get(piece.piece_type, 0)
        # Add positional bonus from PST
        if piece.piece_type == chess.PAWN:
            pst = PST_PAWN
        elif piece.piece_type == chess.KNIGHT:
            pst = PST_KNIGHT
        else:
            pst = None
        pos_bonus = 0
        if pst:
            idx = sq if piece.color == chess.WHITE else (63 - sq)
            pos_bonus = pst[idx]

        if piece.color == chess.WHITE:
            score += val + pos_bonus
        else:
            score -= val + pos_bonus

    # Mobility bonus
    mobility = len(list(board.legal_moves))
    if board.turn == chess.WHITE:
        score += mobility * 2
    else:
        score -= mobility * 2

    return score


def minimax(board: chess.Board, depth: int, alpha: float, beta: float,
            maximizing: bool) -> Tuple[float, Optional[chess.Move]]:
    """Minimax with alpha-beta pruning."""
    if depth == 0 or board.is_game_over():
        return evaluate_board(board), None

    best_move = None
    if maximizing:
        max_eval = float('-inf')
        for move in board.legal_moves:
            board.push(move)
            eval_score, _ = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval_score, _ = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move


def engine_move(board: chess.Board, depth: int = 3) -> chess.Move:
    """Get the engine's best move."""
    maximizing = board.turn == chess.WHITE
    _, best = minimax(board, depth, float('-inf'), float('inf'), maximizing)
    if best is None and list(board.legal_moves):
        return list(board.legal_moves)[0]
    return best


# ---------------------------------------------------------------------------
# Chess Arena Room — PLATO-Native
# ---------------------------------------------------------------------------

class ChessArena:
    """A PLATO room that IS a chess arena.

    The room's tile structure self-orients any agent that walks in:
      1. README tile — explains the room, rules, how to play
      2. STATE tile  — current board position (FEN), whose turn
      3. MOVE tiles  — each move played, with metadata
      4. GAME tiles  — completed games with results
      5. ROSTER tile — who's in the room and their role
    """

    def __init__(self, room_path: str):
        self.room = PlatoRoom(room_path)
        self.game_id = None
        self.board = None
        self.move_count = 0
        self.players = {}  # name -> color
        self.game_start_time = None

    # --- Room Interface (self-orienting tiles) ---

    def _write_readme(self):
        """The README tile — the first thing a zero-shot agent reads."""
        readme = {
            "room": "chess-arena",
            "purpose": "Play chess against the house algorithm or other agents",
            "how_to_play": {
                "step_1": "Read the STATE tile to get the current board (FEN)",
                "step_2": "Choose a legal move in UCI format (e.g. 'e2e4')",
                "step_3": "Submit a tile with type='move', your name, and the move",
                "step_4": "The house algorithm (or opponent) responds automatically",
            },
            "tile_types": {
                "readme": "You are here. Room orientation.",
                "state": "Current board position in FEN. Updated after every move.",
                "move": "A single chess move. Format: {type:'move', name:'agent', uci:'e2e4'}",
                "game": "Completed game record with full move list and result.",
                "roster": "Current players and their colors.",
                "invite": "Challenge the house algorithm to start a new game.",
            },
            "house_algorithm": "Minimax with alpha-beta pruning, depth 3. Plays as the color not taken.",
            "rules": "Standard chess rules. Move in UCI format (e.g. e2e4, e1g1 for castling).",
            "convention": "Tiles are the ONLY communication channel. Read tiles, write tiles.",
        }
        self.room.submit(readme, author="chess-arena", tile_type="readme")

    def _write_state(self):
        """Current board state — updated after every move."""
        state = {
            "fen": self.board.fen() if self.board else chess.STARTING_FEN,
            "turn": "white" if self.board and self.board.turn == chess.WHITE else "black",
            "move_number": self.move_count,
            "game_id": self.game_id,
            "is_check": self.board.is_check() if self.board else False,
            "is_game_over": self.board.is_game_over() if self.board else False,
            "legal_moves": [m.uci() for m in self.board.legal_moves] if self.board else [],
            "last_move": None,  # filled in during play
        }
        self.room.submit(state, author="chess-arena", tile_type="state")

    def _write_roster(self):
        """Who's playing and what color."""
        roster = {
            "players": self.players,
            "house_algorithm": {
                "name": "minimax-ab-d3",
                "description": "Minimax with alpha-beta pruning, depth 3",
            },
            "waiting_for": "invite" if not self.players else "moves",
        }
        self.room.submit(roster, author="chess-arena", tile_type="roster")

    def _write_game_record(self, result: str, reason: str):
        """Log a completed game as a tile."""
        pgn_moves = []
        if self.board:
            pgn_moves = [m.uci() for m in self.board.move_stack]

        game = {
            "game_id": self.game_id,
            "white": self.players.get("white", "house"),
            "black": self.players.get("black", "house"),
            "moves": pgn_moves,
            "move_count": len(pgn_moves),
            "result": result,  # "1-0", "0-1", "1/2-1/2"
            "reason": reason,  # "checkmate", "stalemate", etc.
            "duration_s": time.time() - self.game_start_time if self.game_start_time else 0,
            "timestamp": datetime.now().isoformat(),
        }
        self.room.submit(game, author="chess-arena", tile_type="game")

    # --- Game Lifecycle ---

    def new_game(self, player_name: str = "challenger", player_color: str = "white"):
        """Start a new game. Player chooses color."""
        self.board = chess.Board()
        self.move_count = 0
        self.game_id = f"game-{int(time.time())}"
        self.game_start_time = time.time()
        self.players = {player_name: player_color}

        # Write orientation tiles
        self._write_readme()
        self._write_roster()
        self._write_state()

        print(f"  ♟️ New game: {self.game_id}")
        print(f"     {player_name} plays {player_color}")

        # If player is black, engine (white) moves first
        if player_color == "black":
            self._engine_turn()

        return self.game_id

    def submit_move(self, player_name: str, uci_move: str) -> dict:
        """A player submits a move. Returns result + engine response."""
        if not self.board or self.board.is_game_over():
            return {"status": "error", "message": "No active game"}

        move = chess.Move.from_uci(uci_move)
        if move not in self.board.legal_moves:
            return {"status": "error", "message": f"Illegal move: {uci_move}"}

        # Get SAN before pushing (san() requires the move to be legal on current position)
        san = self.board.san(move)

        # Record the move
        self.board.push(move)
        self.move_count += 1

        # Log as tile
        move_tile = {
            "game_id": self.game_id,
            "player": player_name,
            "move_uci": uci_move,
            "move_san": san,
            "move_number": self.move_count,
            "fen_after": self.board.fen(),
            "is_check": self.board.is_check(),
            "timestamp": time.time(),
        }
        self.room.submit(move_tile, author=player_name, tile_type="move")

        # Check game end
        if self.board.is_game_over():
            return self._end_game()

        # Engine responds
        self._engine_turn()
        self._write_state()

        if self.board.is_game_over():
            return self._end_game()

        return {
            "status": "ok",
            "move_played": uci_move,
            "engine_response": self.board.peek().uci() if self.board.move_stack else None,
            "current_fen": self.board.fen(),
            "move_number": self.move_count,
        }

    def _engine_turn(self):
        """The house algorithm makes its move."""
        if self.board.is_game_over():
            return

        start = time.time()
        move = engine_move(self.board, depth=3)
        think_time = time.time() - start

        san = self.board.san(move)
        self.board.push(move)
        self.move_count += 1

        # Log engine's move as tile
        move_tile = {
            "game_id": self.game_id,
            "player": "house-minimax",
            "move_uci": move.uci(),
            "move_san": san,
            "move_number": self.move_count,
            "fen_after": self.board.fen(),
            "is_check": self.board.is_check(),
            "think_time_s": round(think_time, 3),
            "timestamp": time.time(),
        }
        self.room.submit(move_tile, author="house-minimax", tile_type="move")
        print(f"     🤖 House: {san} ({think_time:.3f}s)")

    def _end_game(self) -> dict:
        """Handle game end."""
        if self.board.is_checkmate():
            winner = "black" if self.board.turn == chess.WHITE else "white"
            result = "1-0" if winner == "white" else "0-1"
            reason = "checkmate"
        elif self.board.is_stalemate():
            result = "1/2-1/2"
            reason = "stalemate"
        elif self.board.is_insufficient_material():
            result = "1/2-1/2"
            reason = "insufficient_material"
        elif self.board.can_claim_draw():
            result = "1/2-1/2"
            reason = "draw_claimed"
        elif self.board.is_fifty_moves():
            result = "1/2-1/2"
            reason = "fifty_move_rule"
        elif self.board.is_repetition(3):
            result = "1/2-1/2"
            reason = "threefold_repetition"
        else:
            result = "*"
            reason = "unknown"

        self._write_game_record(result, reason)
        self._write_state()

        return {
            "status": "game_over",
            "result": result,
            "reason": reason,
            "moves": self.move_count,
        }

    def display_board(self) -> str:
        """Pretty-print the current board."""
        if not self.board:
            return "No active game"
        lines = []
        lines.append(f"  Game: {self.game_id}  Move: {self.move_count}")
        lines.append("")
        for rank in range(7, -1, -1):
            row = f"  {rank+1} "
            for file in range(8):
                sq = chess.square(file, rank)
                piece = self.board.piece_at(sq)
                if piece:
                    symbol = piece.symbol()
                    row += symbol + " "
                else:
                    row += ". "
            lines.append(row)
        lines.append("    a b c d e f g h")
        turn = "White" if self.board.turn == chess.WHITE else "Black"
        lines.append(f"  Turn: {turn}")
        if self.board.is_check():
            lines.append("  ⚠️ CHECK!")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Zero-Shot Agent Simulator
# ---------------------------------------------------------------------------

class ZeroShotAgent:
    """Simulates a zero-shot agent walking into the chess arena.

    The agent:
      1. Reads tiles to orient itself
      2. Finds the STATE tile (current board)
      3. Plays a move by submitting a tile
      4. Reads the response

    No prior knowledge of the room. Pure tile-driven behavior.
    """

    def __init__(self, name: str, arena: ChessArena):
        self.name = name
        self.arena = arena
        self.oriented = False

    def orient(self) -> dict:
        """Read the room's tiles to understand the context."""
        tiles = list(self.arena.room.path.glob("readme-*.json"))
        if not tiles:
            return {"status": "confused", "message": "No README tile found"}

        with open(tiles[0]) as f:
            readme = json.load(f)

        content = readme.get("content", {})
        self.oriented = True
        return {
            "status": "oriented",
            "purpose": content.get("purpose"),
            "how_to_play": content.get("how_to_play"),
            "convention": content.get("convention"),
        }

    def read_board(self) -> Optional[chess.Board]:
        """Read the STATE tile to get the current board."""
        state_tiles = sorted(self.arena.room.path.glob("state-*.json"))
        if not state_tiles:
            return None
        with open(state_tiles[-1]) as f:
            data = json.load(f)
        content = data.get("content", {})
        fen = content.get("fen", chess.STARTING_FEN)
        board = chess.Board(fen)
        return board

    def choose_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Pick a move. Zero-shot agents use simple heuristics."""
        legal = list(board.legal_moves)
        if not legal:
            return None

        # Heuristic: prefer captures, then center moves, then random
        captures = [m for m in legal if board.is_capture(m)]
        if captures:
            # Prefer capturing higher-value pieces
            best_capture = max(captures, key=lambda m: PIECE_VALUES.get(
                board.piece_type_at(m.to_square), 0))
            return best_capture

        # Prefer center
        center = chess.D4, chess.D5, chess.E4, chess.E5
        center_moves = [m for m in legal if m.to_square in center]
        if center_moves:
            return center_moves[0]

        # Development: knights and bishops first
        dev_pieces = [chess.KNIGHT, chess.BISHOP]
        dev_moves = [m for m in legal
                     if board.piece_type_at(m.from_square) in dev_pieces]
        if dev_moves:
            return dev_moves[0]

        return legal[0]

    def play_move(self) -> dict:
        """Orient → read board → choose move → submit."""
        if not self.oriented:
            orientation = self.orient()
            if orientation["status"] != "oriented":
                return orientation

        # Use the arena's live board (authoritative), not stale tiles
        board = self.arena.board
        if board is None or board.is_game_over():
            return {"status": "error", "message": "No active game"}

        move = self.choose_move(board)
        if move is None:
            return {"status": "error", "message": "No legal moves (game over?)"}

        return self.arena.submit_move(self.name, move.uci())


# ---------------------------------------------------------------------------
# Demo — Full Chess Arena Lifecycle
# ---------------------------------------------------------------------------

def demo():
    print("=" * 70)
    print("  ♟️ CHESS ARENA — ZeroClaw PRIME's PLATO Chess Room")
    print("  Zero-shot agents walk in and play. Tiles are the interface.")
    print("=" * 70)

    tmpdir = tempfile.mkdtemp(prefix="chess-arena-")

    try:
        # ---- Phase 1: Create the arena ----
        print("\n📐 Phase 1: Creating Chess Arena room in PLATO")
        arena = ChessArena(str(Path(tmpdir) / "chess-arena"))
        print(f"  Room created at: {arena.room.path}")
        print(f"  Room status: {arena.room.status()}")

        # ---- Phase 2: PRIME starts a game vs house algorithm ----
        print("\n♟️ Phase 2: PRIME plays vs house algorithm")
        game_id = arena.new_game(player_name="PRIME", player_color="white")
        print(arena.display_board())

        # Play a few moves (PRIME makes deliberate opening moves)
        prime_moves = ["e2e4", "d2d4", "b1c3", "g1f3", "f1c4"]
        for uci in prime_moves:
            result = arena.submit_move("PRIME", uci)
            if result.get("status") == "game_over":
                print(f"  Game over: {result['result']} ({result['reason']})")
                break
            elif result.get("status") == "ok":
                print(f"  ✅ PRIME: {uci} → House: {result.get('engine_response', '?')}")
                print(arena.display_board())
                print()
            else:
                print(f"  ❌ {result.get('message')}")
                break

        # ---- Phase 3: Observe the tile landscape ----
        print("\n📋 Phase 3: Room tile landscape")
        status = arena.room.status()
        print(f"  Active tiles: {status['tiles']}")
        print(f"  Rocks: {status['rocks']}")

        print("\n  Git history:")
        for entry in arena.room.history(15):
            msg = entry['message'][:70]
            print(f"    {entry['hash'][:8]} {msg}")

        # ---- Phase 4: Zero-shot agent walks in ----
        print("\n🤖 Phase 4: Zero-shot agent 'WANDERER' enters the room")
        wanderer = ZeroShotAgent("WANDERER", arena)

        print("\n  WANDERER reads the room...")
        orientation = wanderer.orient()
        print(f"  Status: {orientation['status']}")
        print(f"  Purpose: {orientation['purpose']}")
        print(f"  Convention: {orientation['convention']}")

        print("\n  WANDERER reads the board...")
        board = wanderer.read_board()
        if board:
            print(f"  Board FEN: {board.fen()}")
            print(f"  Legal moves: {len(list(board.legal_moves))}")

        # ---- Phase 5: New game with WANDERER ----
        print("\n🎮 Phase 5: WANDERER starts own game vs house")
        game2_id = arena.new_game(player_name="WANDERER", player_color="white")
        wanderer.oriented = True  # already oriented

        for i in range(50):  # enough for a full game (100 half-moves = 50 rounds)
            result = wanderer.play_move()
            if result.get("status") == "game_over":
                print(f"  🏁 Game over: {result['result']} ({result['reason']})")
                print(f"     Total moves: {result['moves']}")
                break
            elif result.get("status") == "ok":
                move_played = result['move_played']
                engine_resp = result.get('engine_response', '?')
                print(f"  WANDERER: {move_played} → House: {engine_resp}")
                # Detect repetition loops
                if arena.board.is_repetition(2):
                    print(f"  🔄 Repetition detected — claiming draw")
                    end = arena._end_game()
                    print(f"  🏁 Game over: {end['result']} ({end['reason']})")
                    break
            else:
                print(f"  ❌ {result.get('message')}")
                break

        print(arena.display_board())

        # ---- Phase 6: Final room state ----
        print("\n📊 Phase 6: Final room state")
        final_status = arena.room.status()
        print(f"  Tiles: {final_status['tiles']}")
        print(f"  History depth: {len(arena.room.history(50))} commits")

        # Show game records
        print("\n  Game records in room:")
        for gf in sorted(arena.room.path.glob("game-*.json")):
            with open(gf) as f:
                game_data = json.load(f)
            content = game_data.get("content", {})
            gid = content.get("game_id", "?")
            result = content.get("result", "?")
            reason = content.get("reason", "?")
            moves = content.get("move_count", "?")
            duration = content.get("duration_s", 0)
            print(f"    {gid}: {result} ({reason}, {moves} moves, {duration:.1f}s)")

        # Show tile types distribution
        tile_types = {}
        for tf in arena.room.path.glob("*.json"):
            if tf.name.startswith("."):
                continue
            try:
                with open(tf) as f:
                    t = json.load(f)
                ttype = t.get("type", "unknown")
                tile_types[ttype] = tile_types.get(ttype, 0) + 1
            except:
                pass

        print(f"\n  Tile type distribution:")
        for ttype, count in sorted(tile_types.items()):
            print(f"    {ttype}: {count}")

        print("\n✅ Chess Arena demo complete!")
        print(f"   The room is at: {arena.room.path}")
        print(f"   Zero-shot agents can clone and play immediately.")

    finally:
        # Keep the room for inspection in /tmp
        print(f"\n  Room preserved at: {tmpdir}")
        print(f"  Inspect with: ls {tmpdir}/chess-arena/")


if __name__ == "__main__":
    demo()
