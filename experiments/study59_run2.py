#!/usr/bin/env python3
"""Study 59: Batch runner - runs one model at a time, saves incrementally."""

import json, requests, time, sys, re, os

DEEPINFRA_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
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
     "prompt": "Write a Python function called is_valid_bst that takes the root of a binary tree and returns True if it is a valid Binary Search Tree, False otherwise.\nUse this class definition:\nclass TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\nA valid BST: left subtree values < node value < right subtree values, and all subtrees are also valid BSTs.",
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
                timeout=90)
            data = resp.json()
            if "error" in data:
                print(f"  API error: {data['error']}", file=sys.stderr)
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                return None
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Exception (attempt {attempt}): {e}", file=sys.stderr)
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

TEST_HARNESSES = {
    "bst": """
root = None
assert is_valid_bst(root) == True
root = TreeNode(2, TreeNode(1), TreeNode(3))
assert is_valid_bst(root) == True
root2 = TreeNode(5, TreeNode(1), TreeNode(4, TreeNode(3), TreeNode(6)))
assert is_valid_bst(root2) == False
""",
    "lru": """
cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
assert cache.get(1) == 1
cache.put(3, 3)
assert cache.get(2) == -1
assert cache.get(3) == 3
cache.put(4, 4)
assert cache.get(1) == -1
assert cache.get(3) == 3
assert cache.get(4) == 4
""",
    "astar": """
grid = [[0,0,0],[0,1,0],[0,0,0]]
path = astar(grid, (0,0), (2,2))
assert path is not None
assert path[0] == (0,0)
assert path[-1] == (2,2)
grid2 = [[0,1],[1,0]]
path2 = astar(grid2, (0,0), (1,1))
assert path2 is None
""",
    "topo": """
result = topological_sort(4, [(0,1),(0,2),(1,3),(2,3)])
assert result is not None
assert result.index(0) < result.index(1)
assert result.index(0) < result.index(2)
assert result.index(1) < result.index(3)
assert result.index(2) < result.index(3)
result2 = topological_sort(3, [(0,1),(1,2),(2,0)])
assert result2 is None
result3 = topological_sort(1, [])
assert result3 == [0]
""",
}

def score_code(task, code):
    if not code or len(code.strip()) < 10:
        return "fail", "No code generated"
    
    if task.get("test_code"):
        harness = TEST_HARNESSES.get(task["test_harness"], "")
        if not harness:
            return "fail", "No test harness"
        try:
            ns = {}
            exec(code, ns)
            exec(harness, ns)
            return "pass", "All assertions passed"
        except AssertionError as e:
            return "fail", f"Assertion: {e}"
        except Exception as e:
            # Check if function/class exists
            func_name = task["id"]
            if func_name == "validate_bst":
                func_name = "is_valid_bst"
            elif func_name == "topological_sort":
                pass
            elif func_name == "a_star":
                func_name = "astar"
            elif func_name == "lru_cache":
                func_name = "LRUCache"
            
            if func_name in code:
                return "partial", f"Structure present, error: {type(e).__name__}: {str(e)[:80]}"
            return "fail", f"{type(e).__name__}: {str(e)[:80]}"
    
    test = task["test"]
    try:
        ns = {}
        exec(code, ns)
        exec(test, ns)
        return "pass", "All assertions passed"
    except AssertionError as e:
        return "fail", f"Assertion: {e}"
    except Exception as e:
        func_name = task["id"]
        if func_name in code:
            return "partial", f"Function present, error: {type(e).__name__}: {str(e)[:80]}"
        return "fail", f"{type(e).__name__}: {str(e)[:80]}"

def main():
    model_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    # Load existing results
    all_results = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            all_results = json.load(f)
    
    completed_models = {r["model"] for r in all_results}
    
    for model_info in MODELS:
        if model_info["id"] in completed_models:
            print(f"Skipping {model_info['id']} (already done)", flush=True)
            continue
        
        mid = model_info["id"]
        model_name = model_info["model"]
        provider = model_info["provider"]
        tier = model_info["tier"]
        
        print(f"\n=== {mid} (Tier {tier}) ===", flush=True)
        
        for task in TASKS:
            task_id = task["id"]
            difficulty = task["difficulty"]
            
            print(f"  {task_id} ({difficulty})...", end=" ", flush=True)
            
            if provider == "deepinfra":
                response = call_deepinfra(model_name, task["prompt"])
            else:
                response = call_ollama(model_name, task["prompt"])
            
            code = extract_code(response)
            score, detail = score_code(task, code)
            
            all_results.append({
                "model": mid,
                "model_full": model_name,
                "tier": tier,
                "task": task_id,
                "difficulty": difficulty,
                "score": score,
                "detail": detail,
                "code_length": len(code),
                "response_length": len(response) if response else 0,
            })
            
            icon = "✅" if score == "pass" else ("🔶" if score == "partial" else "❌")
            print(f"{icon} {score}", flush=True)
            
            if provider == "deepinfra":
                time.sleep(1.5)
        
        # Save after each model
        with open(RESULTS_FILE, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"  Saved {len(all_results)} results", flush=True)
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    for model_info in MODELS:
        mid = model_info["id"]
        tier = model_info["tier"]
        mr = [r for r in all_results if r["model"] == mid]
        if not mr:
            continue
        passes = sum(1 for r in mr if r["score"] == "pass")
        partials = sum(1 for r in mr if r["score"] == "partial")
        total = len(mr)
        pct = 100 * passes / total if total else 0
        print(f"\n{mid} (Math Tier {tier}): {passes}/{total} ({pct:.0f}%) pass, {partials} partial")
        for diff in ["easy", "medium", "hard"]:
            dr = [r for r in mr if r["difficulty"] == diff]
            if dr:
                dp = sum(1 for r in dr if r["score"] == "pass")
                dpc = 100 * dp / len(dr)
                print(f"  {diff}: {dp}/{len(dr)} ({dpc:.0f}%)")

if __name__ == "__main__":
    main()
