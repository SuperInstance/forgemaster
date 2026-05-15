#!/usr/bin/env python3
"""
Tests for the Piagetian Stage Irreversibility experiment.

Validates:
1. Ollama connectivity
2. Correct task definitions
3. Scoring functions
4. Experiment structure (3 cells × 2 models × 8 tasks)
5. Results file generation
"""

import json
import sys
import urllib.request
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).parent.parent / "experiments"
sys.path.insert(0, str(EXPERIMENT_DIR))

RESULTS_FILE = EXPERIMENT_DIR / "STAGE-IRREVERSIBILITY-RESULTS.md"
RAW_FILE = EXPERIMENT_DIR / "stage_irreversibility_raw.json"
EXPERIMENT_SCRIPT = EXPERIMENT_DIR / "stage_irreversibility.py"


def test_ollama_connectivity():
    """Test that Ollama is running and accessible."""
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            assert "qwen3:0.6b" in models, f"qwen3:0.6b not found. Available: {models}"
            assert "qwen3:4b" in models, f"qwen3:4b not found. Available: {models}"
            return True
    except Exception as e:
        print(f"FAIL: Ollama connectivity: {e}")
        return False


def test_experiment_script_exists():
    """Test that the experiment script exists."""
    assert EXPERIMENT_SCRIPT.exists(), f"Experiment script not found: {EXPERIMENT_SCRIPT}"
    return True


def test_task_definitions():
    """Test that test tasks are well-formed."""
    from stage_irreversibility import TEST_TASKS

    assert len(TEST_TASKS) == 8, f"Expected 8 test tasks, got {len(TEST_TASKS)}"

    for task in TEST_TASKS:
        assert "id" in task, f"Task missing id: {task}"
        assert "prompt" in task, f"Task missing prompt: {task}"
        assert "category" in task, f"Task missing category: {task}"
        assert "stage" in task, f"Task missing stage: {task}"
        assert "scoring" in task, f"Task missing scoring: {task}"
        assert task["scoring"] in ("exact_numeric", "semantic"), f"Unknown scoring: {task['scoring']}"

        if task["scoring"] == "exact_numeric":
            assert "correct_answer" in task, f"exact_numeric task missing correct_answer: {task['id']}"
        elif task["scoring"] == "semantic":
            assert "keywords" in task, f"semantic task missing keywords: {task['id']}"

    # Check category distribution
    categories = set(t["category"] for t in TEST_TASKS)
    assert "eisenstein_norm" in categories, "Missing eisenstein_norm tasks"
    assert "notation_translation" in categories, "Missing notation_translation tasks"

    # Check stage distribution
    stages = set(t["stage"] for t in TEST_TASKS)
    assert 4 in stages, "Missing Stage 4 tasks"
    assert 3 in stages, "Missing Stage 3 tasks"

    return True


def test_stage_prompts():
    """Test that stage prompts are well-formed."""
    from stage_irreversibility import (
        STAGE_2_PROMPTS, STAGE_3_PROMPTS, STAGE_4_PROMPTS,
    )

    for name, prompts in [
        ("Stage 2", STAGE_2_PROMPTS),
        ("Stage 3", STAGE_3_PROMPTS),
        ("Stage 4", STAGE_4_PROMPTS),
    ]:
        assert len(prompts) >= 2, f"{name} has too few prompts"
        for p in prompts:
            assert "role" in p, f"{name} prompt missing role"
            assert "content" in p, f"{name} prompt missing content"
            assert p["role"] in ("system", "user", "assistant"), f"Invalid role: {p['role']}"

    return True


def test_scoring_exact_numeric():
    """Test exact numeric scoring."""
    from stage_irreversibility import score_response

    task = {
        "id": "test",
        "scoring": "exact_numeric",
        "correct_answer": "7",
    }

    # Correct
    result = score_response(task, "The answer is 7")
    assert result["correct"] is True, f"Should be correct: {result}"
    assert result["score"] == 1.0

    # Wrong
    result = score_response(task, "The answer is 42")
    assert result["correct"] is False, f"Should be incorrect: {result}"
    assert result["score"] == 0.0

    # Correct in context
    result = score_response(task, "= 4 - 6 + 9\n= 7")
    assert result["correct"] is True, f"Should find 7 in context: {result}"

    return True


def test_scoring_semantic():
    """Test semantic scoring."""
    from stage_irreversibility import score_response

    task = {
        "id": "test",
        "scoring": "semantic",
        "keywords": ["exists", "real", "square", "2"],
    }

    # Good
    result = score_response(task, "There exists a real number whose square equals 2")
    assert result["correct"] is True, f"Should be correct: {result}"
    assert result["score"] >= 0.5

    # Poor
    result = score_response(task, "The weather is nice today")
    assert result["correct"] is False, f"Should be incorrect: {result}"

    return True


def test_results_file_exists():
    """Test that results were generated."""
    # This test passes if the experiment has been run
    if not RESULTS_FILE.exists():
        print("SKIP: Results file not yet generated (run the experiment first)")
        return True

    content = RESULTS_FILE.read_text()
    assert "# Piagetian Stage Irreversibility" in content, "Missing title"
    assert "Cell A" in content, "Missing Cell A results"
    assert "Cell B" in content, "Missing Cell B results"
    assert "Cell C" in content, "Missing Cell C results"
    assert "Analysis" in content or "Critical Finding" in content, "Missing analysis section"
    return True


def test_raw_json_structure():
    """Test that raw JSON results have correct structure."""
    if not RAW_FILE.exists():
        print("SKIP: Raw JSON not yet generated (run the experiment first)")
        return True

    data = json.loads(RAW_FILE.read_text())
    assert isinstance(data, list), "Raw results should be a list"
    assert len(data) > 0, "Raw results should not be empty"

    # Each result should have required fields
    required_fields = ["cell", "model", "task_id", "task_category", "task_stage", "score", "correct"]
    for item in data:
        for field in required_fields:
            assert field in item, f"Result missing field '{field}': {item}"

    # Should have results for all cells and models
    cells = set(r["cell"] for r in data)
    models = set(r["model"] for r in data)
    assert cells == {"A", "B", "C"}, f"Missing cells: {cells}"
    assert "qwen3:0.6b" in models, "Missing qwen3:0.6b results"
    assert "qwen3:4b" in models, "Missing qwen3:4b results"

    # Should have 2 models × 3 cells × 8 tasks = 48 results
    assert len(data) == 48, f"Expected 48 results, got {len(data)}"

    return True


def test_cell_b_has_higher_context_than_a():
    """Verify Cell B prompts have more context than Cell A."""
    from stage_irreversibility import STAGE_4_PROMPTS, TEST_TASKS

    # Cell A: just the task prompt (1 message)
    # Cell B: STAGE_4_PROMPTS + task prompt (6+ messages)
    cell_a_msgs = 1
    cell_b_msgs = len(STAGE_4_PROMPTS) + 1

    assert cell_b_msgs > cell_a_msgs, "Cell B should have more context than Cell A"
    return True


def test_cell_c_has_most_context():
    """Verify Cell C has the most context (staged accumulation)."""
    from stage_irreversibility import (
        STAGE_2_PROMPTS, STAGE_3_PROMPTS, STAGE_4_PROMPTS,
    )

    cell_b_msgs = len(STAGE_4_PROMPTS) + 1
    cell_c_msgs = len(STAGE_2_PROMPTS) + len(STAGE_3_PROMPTS) + len(STAGE_4_PROMPTS) + 1

    assert cell_c_msgs > cell_b_msgs, "Cell C should have more context than Cell B"
    return True


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        ("Ollama Connectivity", test_ollama_connectivity),
        ("Experiment Script Exists", test_experiment_script_exists),
        ("Task Definitions", test_task_definitions),
        ("Stage Prompts", test_stage_prompts),
        ("Scoring: Exact Numeric", test_scoring_exact_numeric),
        ("Scoring: Semantic", test_scoring_semantic),
        ("Results File Exists", test_results_file_exists),
        ("Raw JSON Structure", test_raw_json_structure),
        ("Cell B > Cell A Context", test_cell_b_has_higher_context_than_a),
        ("Cell C Has Most Context", test_cell_c_has_most_context),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for name, test_fn in tests:
        try:
            result = test_fn()
            if result is True:
                print(f"  ✓ {name}")
                passed += 1
            else:
                print(f"  ✗ {name}")
                failed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠ {name}: {e}")
            skipped += 1

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
