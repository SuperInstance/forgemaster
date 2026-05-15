"""Tic-tac-toe room — PLATO room that plays games using the router."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from officer import route_and_query, write_tile

def play_move(board_str):
    """Route a move through the fleet router."""
    prompt = f"""You are playing tic-tac-toe. The board is:
{board_str}

You are X. Give ONLY the position number (1-9) for your next move.
Positions:
1|2|3
4|5|6
7|8|9"""
    answer, meta = route_and_query(prompt, max_tokens=5)
    # Extract number
    import re
    nums = re.findall(r'\d', answer)
    move = int(nums[0]) if nums else 5  # default to center
    write_tile("game-ttt", f"move/X/{meta.get('domain','?')}",
              json.dumps({"board": board_str, "move": move, "model": meta.get("model","?")}),
              domain="game")
    return move, meta

if __name__ == "__main__":
    board = sys.argv[1] if len(sys.argv) > 1 else " | | \n-+-+-\n | | \n-+-+-\n | | "
    move, meta = play_move(board)
    print(f"Move: {move} (via {meta.get('model','?')}, ${meta.get('cost','?')}/1K)")
