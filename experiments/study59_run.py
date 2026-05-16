#!/usr/bin/env python3
"""Study 59: Does the three-tier taxonomy hold for code generation?"""

import json, requests, time, sys, re, os

DEEPINFRA_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"

# 10 code tasks, varying difficulty
TASKS = [
    # Easy (3)
    {"id": "reverse_list", "difficulty": "easy",
     "prompt": "Write a Python function called reverse_list that takes a list and returns it reversed. Do not use the built-in reverse() or [::-1]. Implement the logic manually.",
     "test": "assert reverse_list([1,2,3]) == [3,2,1] and reverse_list([]) == [] and reverse_list([5]) == [5]"},
    {"id": "find_max", "difficulty": "easy",
     "prompt": "Write a Python function called find_max that takes a list of numbers and returns the maximum value. Do not use the built-in max(). Implement the logic manually.",
     "test": "assert find_max([3,1,4,1,5]) == 5 and find_max([-1,-2]) == -1 and find_max([7]) == 7"},
    {"id": "count_chars", "difficulty": "easy",
     "prompt": "Write a Python function called count_chars that takes a string and returns a dictionary with the count of each character.",
     "test": "assert count_chars('hello') == {'h':1,'e':1,'l':2,'o':1} and count_chars('') == {}"},
    # Medium (4)
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
     "prompt": """Write a Python function called is_valid_bst that takes the root of a binary tree and returns True if it is a valid Binary Search Tree, False otherwise.
Use this class definition:
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
A valid BST: left subtree values < node value < right subtree values, and all subtrees are also valid BSTs.""",
     "test_code": True},
    # Hard (3)
    {"id": "lru_cache", "difficulty": "hard",
     "prompt": "Implement an LRU Cache in Python with the following API:\n- __init__(self, capacity: int): initialize with given capacity\n- get(self, key: int) -> int: return value if key exists (and mark recently used), else return -1\n- put(self, key: int, value: int) -> None: insert/update key. If at capacity, evict least recently used.\nDo NOT use OrderedDict or any built-in LRU. Use a doubly-linked list + hashmap.",
     "test_code": True},
    {"id": "a_star", "difficulty": "hard",
     "prompt": "Implement the A* pathfinding algorithm in Python. Function signature: def astar(grid, start, end) where grid is a 2D list (0=walkable, 1=blocked), start and end are (row,col) tuples. Return the path as a list of (row,col) tuples from start to end, or None if no path exists. Use Manhattan distance as heuristic.",
     "test_code": True},
    {"id": "topological_sort", "difficulty": "hard",
     "prompt": "Implement topological sort in Python. Function signature: def topological_sort(num_nodes, edges) where edges is a list of (from, to) pairs. Return a topological ordering as a list of node IDs, or None if a cycle exists. Nodes are numbered 0 to num_nodes-1.",
     "test_code": True},
]

MODELS = [
    {"id": "seed-2.0-mini", "provider": "deepinfra", "model": "ByteDance/Seed-2.0-mini", "tier": 1},
    {"id": "hermes-70b", "provider": "deepinfra", "model": "NousResearch/Hermes-3-Llama-3.1-70B", "tier": 2},
    {"id": "qwen3-235b", "provider": "deepinfra", "model": "Qwen/Qwen3-235B-A22B-Instruct-2507", "tier": 2},
    {"id": "gemma3-1b", "provider": "ollama", "model": "gemma3:1b", "tier": 1},
    {"id": "qwen3-0.6b", "provider": "ollama", "model": "qwen3:0.6b", "tier": 3},
]

def call_deepinfra(model_id, prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(DEEPINFRA_URL, 
                headers={"Authorization": f"Bearer {DEEPINFRA_KEY}"},
                json={"model": model_id, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 2048, "temperature": 0.1},
                timeout=60)
            data = resp.json()
            if "error" in data:
                print(f"  API error: {data['error']}", file=sys.stderr)
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                return None
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Exception: {e}", file=sys.stderr)
            if attempt < max_retries:
                time.sleep(5)
                continue
            return None
    return None

def call_ollama(model_id, prompt):
    try:
        resp = requests.post(OLLAMA_URL,
            json={"model": model_id, "messages": [{"role": "user", "content": prompt}],
                   "stream": False, "options": {"temperature": 0.1, "num_predict": 2048}},
            timeout=120)
        data = resp.json()
        return data.get("message", {}).get("content")
    except Exception as e:
        print(f"  Ollama exception: {e}", file=sys.stderr)
        return None

def extract_code(response):
    """Extract Python code from response."""
    if not response:
        return ""
    # Try code blocks first
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if blocks:
        # Return the largest code block (likely the implementation)
        return max(blocks, key=len).strip()
    # Fallback: look for function definitions
    lines = response.split('\n')
    code_lines = []
    in_code = False
    for line in lines:
        if line.strip().startswith(('def ', 'class ', 'import ', 'from ')) or in_code:
            in_code = True
            code_lines.append(line)
            if line.strip() and not line.startswith(' ') and not line.strip().startswith(('def ', 'class ', 'import ', 'from ', '#', '@')):
                in_code = False
        elif in_code and (line.strip() == '' or line.startswith(' ') or line.startswith('\t')):
            code_lines.append(line)
    return '\n'.join(code_lines).strip() if code_lines else ""

def score_code(task, code):
    """Score extracted code: pass/fail/partial."""
    if not code or len(code.strip()) < 10:
        return "fail", "No code generated"
    
    if task.get("test_code"):
        return score_complex_task(task, code)
    
    # Simple tasks: try to run the test
    test = task["test"]
    full_code = code + "\n" + test
    try:
        exec(full_code, {"__builtins__": {}})
        return "pass", "All assertions passed"
    except AssertionError as e:
        return "fail", f"Assertion failed: {e}"
    except Exception as e:
        # Try wrapping in a main block approach
        try:
            namespace = {}
            exec(code, namespace)
            exec(test, namespace)
            return "pass", "All assertions passed"
        except AssertionError as e:
            return "fail", f"Assertion failed: {e}"
        except Exception as e:
            # Check if function exists and structure looks right
            if f"def {task['id'].replace('_list','').replace('_max','').replace('_chars','')}" in code or f"def {task['id']}" in code:
                return "partial", f"Function exists but test error: {type(e).__name__}: {e}"
            return "fail", f"Runtime error: {type(e).__name__}: {e}"

def score_complex_task(task, code):
    """Score complex tasks with custom test harnesses."""
    task_id = task["id"]
    
    if task_id == "validate_bst":
        test_code = """
root = None
assert is_valid_bst(root) == True, "empty tree"

# Valid BST:    2
#              / \\
#             1   3
root = TreeNode(2, TreeNode(1), TreeNode(3))
assert is_valid_bst(root) == True, "valid bst"

# Invalid:    5
#            / \\
#           1   4
#              / \\
#             3   6  (3 < 5 violates)
root2 = TreeNode(5, TreeNode(1), TreeNode(4, TreeNode(3), TreeNode(6)))
assert is_valid_bst(root2) == False, "invalid bst"
"""
    elif task_id == "lru_cache":
        test_code = """
cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
assert cache.get(1) == 1, "get existing"
cache.put(3, 3)  # evicts key 2
assert cache.get(2) == -1, "evicted"
assert cache.get(3) == 3, "get after put"
cache.put(4, 4)  # evicts key 1
assert cache.get(1) == -1, "evicted 2"
assert cache.get(3) == 3
assert cache.get(4) == 4
"""
    elif task_id == "a_star":
        test_code = """
# Simple grid
grid = [[0,0,0],[0,1,0],[0,0,0]]
path = astar(grid, (0,0), (2,2))
assert path is not None, "path exists"
assert path[0] == (0,0), "starts at start"
assert path[-1] == (2,2), "ends at end"
assert len(path) == 5, f"expected 5 steps got {len(path)}"

# No path
grid2 = [[0,1],[1,0]]
path2 = astar(grid2, (0,0), (1,1))
assert path2 is None, "no path"

# Start == end
path3 = astar([[0]], (0,0), (0,0))
assert path3 == [(0,0)], "start=end"
"""
    elif task_id == "topological_sort":
        test_code = """
# Simple DAG
result = topological_sort(4, [(0,1),(0,2),(1,3),(2,3)])
assert result is not None, "has ordering"
assert result.index(0) < result.index(1), "0 before 1"
assert result.index(0) < result.index(2), "0 before 2"
assert result.index(1) < result.index(3), "1 before 3"
assert result.index(2) < result.index(3), "2 before 3"

# Cycle
result2 = topological_sort(3, [(0,1),(1,2),(2,0)])
assert result2 is None, "cycle detected"

# Single node
result3 = topological_sort(1, [])
assert result3 == [0], "single node"
"""
    else:
        return "fail", "Unknown complex task"
    
    try:
        namespace = {}
        exec(code, namespace)
        exec(test_code, namespace)
        return "pass", "All assertions passed"
    except AssertionError as e:
        return "fail", f"Assertion failed: {e}"
    except Exception as e:
        # Check if key class/function exists
        if task_id == "validate_bst" and "is_valid_bst" in code:
            return "partial", f"Function exists but error: {type(e).__name__}: {e}"
        if task_id == "lru_cache" and "class LRUCache" in code:
            return "partial", f"Class exists but error: {type(e).__name__}: {e}"
        if task_id == "a_star" and "def astar" in code:
            return "partial", f"Function exists but error: {type(e).__name__}: {e}"
        if task_id == "topological_sort" and "def topological_sort" in code:
            return "partial", f"Function exists but error: {type(e).__name__}: {e}"
        return "fail", f"Runtime error: {type(e).__name__}: {e}"

def run_experiment():
    results = []
    total = len(MODELS) * len(TASKS)
    count = 0
    
    for model_info in MODELS:
        model_id = model_info["id"]
        model_name = model_info["model"]
        provider = model_info["provider"]
        tier = model_info["tier"]
        
        for task in TASKS:
            count += 1
            task_id = task["id"]
            difficulty = task["difficulty"]
            prompt = task["prompt"]
            
            print(f"[{count}/{total}] {model_id} (T{tier}) × {task_id} ({difficulty})...", flush=True)
            
            if provider == "deepinfra":
                response = call_deepinfra(model_name, prompt)
            else:
                response = call_ollama(model_name, prompt)
            
            code = extract_code(response)
            score, detail = score_code(task, code)
            
            results.append({
                "model": model_id,
                "model_full": model_name,
                "tier": tier,
                "task": task_id,
                "difficulty": difficulty,
                "score": score,
                "detail": detail,
                "code_length": len(code),
                "response_length": len(response) if response else 0,
            })
            
            status = "✅" if score == "pass" else ("🔶" if score == "partial" else "❌")
            print(f"  → {status} {score} ({detail})", flush=True)
            
            # Rate limiting
            if provider == "deepinfra":
                time.sleep(1)
            else:
                time.sleep(0.5)
    
    return results

if __name__ == "__main__":
    print("=" * 60)
    print("STUDY 59: Three-Tier Taxonomy for Code Generation")
    print("=" * 60)
    results = run_experiment()
    
    # Save raw results
    with open("/home/phoenix/.openclaw/workspace/experiments/study59_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    # Per-model summary
    for model_info in MODELS:
        mid = model_info["id"]
        tier = model_info["tier"]
        model_results = [r for r in results if r["model"] == mid]
        passes = sum(1 for r in model_results if r["score"] == "pass")
        partials = sum(1 for r in model_results if r["score"] == "partial")
        fails = sum(1 for r in model_results if r["score"] == "fail")
        total = len(model_results)
        print(f"\n{mid} (Tier {tier}):")
        print(f"  Pass: {passes}/{total} ({100*passes/total:.0f}%)  Partial: {partials}  Fail: {fails}")
        
        # Per-difficulty
        for diff in ["easy", "medium", "hard"]:
            dr = [r for r in model_results if r["difficulty"] == diff]
            if dr:
                dp = sum(1 for r in dr if r["score"] == "pass")
                print(f"  {diff}: {dp}/{len(dr)} ({100*dp/len(dr):.0f}%)")
