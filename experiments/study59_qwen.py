#!/usr/bin/env python3
"""Run qwen3:0.6b only for Study 59."""
import json, requests, time, sys, re, os

OLLAMA_URL = "http://localhost:11434/api/chat"
RESULTS_FILE = "/home/phoenix/.openclaw/workspace/experiments/study59_results.json"

TASKS = [
    {"id": "reverse_list", "difficulty": "easy",
     "prompt": "Write a Python function called reverse_list that takes a list and returns it reversed. Do not use the built-in reverse() or [::-1]. Implement the logic manually.",
     "test": "assert reverse_list([1,2,3]) == [3,2,1] and reverse_list([]) == [] and reverse_list([5]) == [5]"},
    {"id": "find_max", "difficulty": "easy",
     "prompt": "Write a Python function called find_max that takes a list of numbers and returns the maximum value. Do not use the built-in max(). Implement the logic manually.",
     "test": "assert find_max([3,1,4,1,5]) == 5 and find_max([-1,-2]) == -1 and find_max([7]) == 7"},
    {"id": "count_chars", "difficulty": "easy",
     "prompt": "Write a Python function called count_chars that takes a string and returns a dictionary with the count of each character.",
     "test": "assert count_chars('hello') == {'h':1,'e':1,'l':2,'o':1} and count_chars('') == {}"},
    {"id": "binary_search", "difficulty": "medium",
     "prompt": "Write a Python function called binary_search that takes a sorted list and a target value. Return the index of the target if found, or -1 if not found.",
     "test": "assert binary_search([1,3,5,7,9], 5) == 2 and binary_search([1,3,5,7,9], 4) == -1 and binary_search([], 1) == -1"},
    {"id": "fibonacci_memo", "difficulty": "medium",
     "prompt": "Write a Python function called fibonacci that takes an integer n and returns the nth Fibonacci number. Use memoization. fibonacci(0)=0, fibonacci(1)=1.",
     "test": "assert fibonacci(0) == 0 and fibonacci(1) == 1 and fibonacci(10) == 55 and fibonacci(20) == 6765"},
    {"id": "merge_sorted", "difficulty": "medium",
     "prompt": "Write a Python function called merge_sorted that takes two sorted lists and returns a single merged sorted list.",
     "test": "assert merge_sorted([1,3,5],[2,4,6]) == [1,2,3,4,5,6] and merge_sorted([], [1,2]) == [1,2] and merge_sorted([1,2], []) == [1,2]"},
    {"id": "validate_bst", "difficulty": "medium",
     "prompt": "Write a Python function called is_valid_bst that takes the root of a binary tree and returns True if it is a valid Binary Search Tree, False otherwise.\nUse this class definition:\nclass TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right",
     "test_code": True, "test_harness": "bst"},
    {"id": "lru_cache", "difficulty": "hard",
     "prompt": "Implement an LRU Cache in Python with the following API:\n- __init__(self, capacity: int): initialize with given capacity\n- get(self, key: int) -> int: return value if key exists (and mark recently used), else return -1\n- put(self, key: int, value: int) -> None: insert/update key. If at capacity, evict least recently used.\nDo NOT use OrderedDict or any built-in LRU. Use a doubly-linked list + hashmap.",
     "test_code": True, "test_harness": "lru"},
    {"id": "a_star", "difficulty": "hard",
     "prompt": "Implement the A* pathfinding algorithm in Python. Function signature: def astar(grid, start, end) where grid is a 2D list (0=walkable, 1=blocked), start and end are (row,col) tuples. Return the path as a list of (row,col) tuples from start to end, or None if no path exists. Use Manhattan distance as heuristic.",
     "test_code": True, "test_harness": "astar"},
    {"id": "topological_sort", "difficulty": "hard",
     "prompt": "Implement topological sort in Python. Function signature: def topological_sort(num_nodes, edges) where edges is a list of (from, to) pairs. Return a topological ordering as a list of node IDs, or None if a cycle exists. Nodes are numbered 0 to num_nodes-1.",
     "test_code": True, "test_harness": "topo"},
]

TEST_HARNESSES = {
    "bst": "root = None\nassert is_valid_bst(root) == True\nroot = TreeNode(2, TreeNode(1), TreeNode(3))\nassert is_valid_bst(root) == True\nroot2 = TreeNode(5, TreeNode(1), TreeNode(4, TreeNode(3), TreeNode(6)))\nassert is_valid_bst(root2) == False",
    "lru": "cache = LRUCache(2)\ncache.put(1, 1)\ncache.put(2, 2)\nassert cache.get(1) == 1\ncache.put(3, 3)\nassert cache.get(2) == -1\nassert cache.get(3) == 3\ncache.put(4, 4)\nassert cache.get(1) == -1\nassert cache.get(3) == 3\nassert cache.get(4) == 4",
    "astar": "grid = [[0,0,0],[0,1,0],[0,0,0]]\npath = astar(grid, (0,0), (2,2))\nassert path is not None\nassert path[0] == (0,0)\nassert path[-1] == (2,2)\ngrid2 = [[0,1],[1,0]]\npath2 = astar(grid2, (0,0), (1,1))\nassert path2 is None",
    "topo": "result = topological_sort(4, [(0,1),(0,2),(1,3),(2,3)])\nassert result is not None\nassert result.index(0) < result.index(1)\nassert result.index(0) < result.index(2)\nassert result.index(1) < result.index(3)\nassert result.index(2) < result.index(3)\nresult2 = topological_sort(3, [(0,1),(1,2),(2,0)])\nassert result2 is None\nresult3 = topological_sort(1, [])\nassert result3 == [0]",
}

def extract_code(response):
    if not response:
        return ""
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip()
    lines = response.split('\n')
    code_lines = []
    in_code = False
    for line in lines:
        if line.strip().startswith(('def ', 'class ', 'import ', 'from ')) or in_code:
            in_code = True
            code_lines.append(line)
        elif in_code and (line.strip() == '' or line.startswith(' ') or line.startswith('\t')):
            code_lines.append(line)
        elif in_code:
            in_code = False
    return '\n'.join(code_lines).strip() if code_lines else ""

def score_code(task, code):
    if not code or len(code.strip()) < 10:
        return "fail", "No code generated"
    if task.get("test_code"):
        harness = TEST_HARNESSES.get(task["test_harness"], "")
        try:
            ns = {}
            exec(code, ns)
            exec(harness, ns)
            return "pass", "All assertions passed"
        except AssertionError as e:
            return "fail", f"Assertion: {e}"
        except Exception as e:
            func_map = {"validate_bst":"is_valid_bst","a_star":"astar","lru_cache":"LRUCache"}
            fn = func_map.get(task["id"], task["id"])
            if fn in code:
                return "partial", f"Structure present, error: {type(e).__name__}: {str(e)[:80]}"
            return "fail", f"{type(e).__name__}: {str(e)[:80]}"
    try:
        ns = {}
        exec(code, ns)
        exec(task["test"], ns)
        return "pass", "All assertions passed"
    except AssertionError as e:
        return "fail", f"Assertion: {e}"
    except Exception as e:
        if task["id"] in code:
            return "partial", f"Function present, error: {type(e).__name__}: {str(e)[:80]}"
        return "fail", f"{type(e).__name__}: {str(e)[:80]}"

# Run qwen3:0.6b
all_results = json.load(open(RESULTS_FILE))
model_id = "qwen3-0.6b"
model_name = "qwen3:0.6b"
tier = 3

print(f"=== {model_id} (Tier {tier}) ===")
for task in TASKS:
    print(f"  {task['id']} ({task['difficulty']})...", end=" ", flush=True)
    try:
        resp = requests.post(OLLAMA_URL,
            json={"model": model_name, "messages": [{"role": "user", "content": task["prompt"]}],
                   "stream": False, "options": {"temperature": 0.1, "num_predict": 2048}},
            timeout=120)
        response = resp.json().get("message", {}).get("content")
    except Exception as e:
        response = None
        print(f"Error: {e}")
    
    code = extract_code(response)
    score, detail = score_code(task, code)
    all_results.append({
        "model": model_id, "model_full": model_name, "tier": tier,
        "task": task["id"], "difficulty": task["difficulty"],
        "score": score, "detail": detail,
        "code_length": len(code), "response_length": len(response) if response else 0,
    })
    icon = "✅" if score == "pass" else ("🔶" if score == "partial" else "❌")
    print(f"{icon} {score}")
    time.sleep(0.5)

with open(RESULTS_FILE, "w") as f:
    json.dump(all_results, f, indent=2)
print(f"Saved {len(all_results)} results")
