#!/usr/bin/env python3
"""Differential test harness for constraint guard test vectors.

Loads test-vectors.json, parses guard_source expressions, evaluates them
against the provided inputs, and compares results with expected outputs.

Focus categories: boundary_values, type_confusion (safety-critical).
"""

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

# ── Expression parser / evaluator ──────────────────────────────────────────

class EvalError(Exception):
    """Raised when an expression cannot be parsed or evaluated."""


def _tokenize(expr: str):
    """Tokenize a constraint expression into a list of tokens."""
    tokens = []
    i = 0
    while i < len(expr):
        if expr[i].isspace():
            i += 1
            continue
        # Two-char operators
        if i + 1 < len(expr):
            two = expr[i:i+2]
            if two in ('<=', '>=', '==', '!='):
                tokens.append(two)
                i += 2
                continue
        # Single-char operators / punctuation
        if expr[i] in '<>+-*/%()':
            tokens.append(expr[i])
            i += 1
            continue
        # Number (int or float, possibly negative — handled as unary minus)
        if expr[i].isdigit() or (expr[i] == '.' and i + 1 < len(expr) and expr[i+1].isdigit()):
            j = i
            while j < len(expr) and (expr[j].isdigit() or expr[j] == '.'):
                j += 1
            # Scientific notation
            if j < len(expr) and expr[j] in ('e', 'E'):
                j += 1
                if j < len(expr) and expr[j] in ('+', '-'):
                    j += 1
                while j < len(expr) and expr[j].isdigit():
                    j += 1
            num_str = expr[i:j]
            tokens.append(float(num_str) if '.' in num_str or 'e' in num_str.lower() else int(num_str))
            i = j
            continue
        # Keywords and identifiers
        if expr[i].isalpha() or expr[i] == '_':
            j = i
            while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            word = expr[i:j]
            tokens.append(word)
            i = j
            continue
        # Skip unknown chars
        i += 1
    return tokens


class _Parser:
    """Recursive-descent parser for guard expressions.

    Precedence (low → high):
        OR
        AND
        comparison: == != < > <= >=
        additive: + -
        multiplicative: * / %
        unary: - NOT
        atom: number | variable | ( expr )
    """

    def __init__(self, tokens, env):
        self.tokens = tokens
        self.pos = 0
        self.env = env

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, val):
        tok = self.peek()
        if tok != val:
            raise EvalError(f"Expected {val!r}, got {tok!r} at pos {self.pos}")
        return self.advance()

    def parse(self):
        result = self.expr_or()
        if self.pos < len(self.tokens):
            raise EvalError(f"Trailing tokens at pos {self.pos}: {self.tokens[self.pos:]}")
        return result

    def expr_or(self):
        left = self.expr_and()
        while self.peek() == 'OR':
            self.advance()
            right = self.expr_and()
            left = bool(left) or bool(right)
        return left

    def expr_and(self):
        left = self.expr_comparison()
        while self.peek() == 'AND':
            self.advance()
            right = self.expr_comparison()
            left = bool(left) and bool(right)
        return left

    def expr_comparison(self):
        left = self.expr_additive()
        while self.peek() in ('==', '!=', '<', '>', '<=', '>='):
            op = self.advance()
            right = self.expr_additive()
            if op == '==':
                left = left == right
            elif op == '!=':
                left = left != right
            elif op == '<':
                left = left < right
            elif op == '>':
                left = left > right
            elif op == '<=':
                left = left <= right
            elif op == '>=':
                left = left >= right
        return left

    def expr_additive(self):
        left = self.expr_multiplicative()
        while self.peek() in ('+', '-'):
            op = self.advance()
            right = self.expr_multiplicative()
            if op == '+':
                left = left + right
            else:
                left = left - right
        return left

    def expr_multiplicative(self):
        left = self.expr_unary()
        while self.peek() in ('*', '/', '%'):
            op = self.advance()
            right = self.expr_unary()
            if op == '*':
                left = left * right
            elif op == '/':
                left = left / right if right != 0 else float('inf')
            else:
                left = left % right if right != 0 else 0
        return left

    def expr_unary(self):
        if self.peek() == '-':
            self.advance()
            return -self.expr_unary()
        if self.peek() == 'NOT':
            self.advance()
            return not self.expr_unary()
        return self.expr_atom()

    def expr_atom(self):
        tok = self.peek()
        if tok == '(':
            self.advance()
            result = self.expr_or()
            self.expect(')')
            return result
        if tok is None:
            raise EvalError("Unexpected end of expression")
        self.advance()
        # Number literal
        if isinstance(tok, (int, float)):
            return tok
        # Variable lookup
        if isinstance(tok, str) and tok in self.env:
            return self.env[tok]
        # Boolean / special literals
        if tok == 'true' or tok == 'True':
            return True
        if tok == 'false' or tok == 'False':
            return False
        if tok == 'null' or tok == 'None':
            return None
        # Unknown identifier — treat as 0 (type-confusion vectors may use unknown vars)
        if isinstance(tok, str):
            return 0
        raise EvalError(f"Unexpected token: {tok!r}")


def evaluate(expr: str, env: dict):
    """Evaluate a guard expression string with the given variable bindings."""
    tokens = _tokenize(expr)
    parser = _Parser(tokens, env)
    return parser.parse()


def parse_guard_source(gs: str):
    """Extract expression and input var names from guard_source string.

    Format: constraint name { expr: <expr>, inputs: [x, y, ...] }
    """
    m = re.search(r'expr:\s*(.+?)\s*,\s*inputs:\s*\[([^\]]*)\]', gs)
    if not m:
        raise EvalError(f"Cannot parse guard_source: {gs[:100]}")
    expr = m.group(1).strip()
    inputs_str = m.group(2).strip()
    var_names = [v.strip() for v in inputs_str.split(',') if v.strip()] if inputs_str else []
    return expr, var_names


# ── Test runner ────────────────────────────────────────────────────────────

PRIORITY_CATEGORIES = ['boundary_values', 'type_confusion']


def run_tests(vectors_path: Path, categories_filter=None):
    """Run differential tests and return results dict."""
    with open(vectors_path) as f:
        vectors = json.load(f)

    total = len(vectors)
    passed = 0
    failed = 0
    errors = 0
    skipped = 0
    failures = []
    category_stats = Counter()

    # Filter by category if requested
    if categories_filter:
        vectors = [v for v in vectors if v['category'] in categories_filter]

    priority_vectors = [v for v in vectors if v['category'] in PRIORITY_CATEGORIES]
    other_vectors = [v for v in vectors if v['category'] not in PRIORITY_CATEGORIES]

    ordered = priority_vectors + other_vectors

    start = time.time()

    for vec in ordered:
        name = vec['name']
        category = vec['category']
        guard_source = vec['guard_source']
        inputs = vec['inputs']
        expected_list = vec['expected']

        try:
            expr, var_names = parse_guard_source(guard_source)

            # Build environment: map var names to input values
            # If fewer inputs than vars, pad with 0; if more, ignore extras
            env = {}
            for i, vn in enumerate(var_names):
                env[vn] = inputs[i] if i < len(inputs) else 0

            # Evaluate
            result = evaluate(expr, env)

            # Compare — expected is always a list of one bool
            expected = expected_list[0] if expected_list else None

            if expected is None:
                skipped += 1
                category_stats[f'{category}:skipped'] += 1
                continue

            # Coerce result to bool for comparison
            result_bool = bool(result) if not isinstance(result, bool) else result

            if result_bool == expected:
                passed += 1
                category_stats[f'{category}:pass'] += 1
            else:
                failed += 1
                category_stats[f'{category}:fail'] += 1
                failures.append({
                    'name': name,
                    'category': category,
                    'expr': expr[:120],
                    'inputs': inputs[:8],
                    'expected': expected,
                    'got': result_bool,
                })

        except Exception as e:
            errors += 1
            category_stats[f'{category}:error'] += 1
            failures.append({
                'name': name,
                'category': category,
                'expr': guard_source[:80],
                'inputs': inputs[:4],
                'expected': expected_list[0] if expected_list else None,
                'got': f'ERROR: {e}',
            })

    elapsed = time.time() - start

    return {
        'total': len(ordered),
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'skipped': skipped,
        'elapsed_sec': round(elapsed, 2),
        'failures': failures[:50],  # cap reported failures
        'category_stats': category_stats,
    }


def print_results(results):
    """Print formatted results to stdout."""
    r = results
    print(f"\n{'='*60}")
    print(f"  DIFFERENTIAL TEST RESULTS")
    print(f"{'='*60}")
    print(f"  Total:    {r['total']}")
    print(f"  Passed:   {r['passed']}  ✅")
    print(f"  Failed:   {r['failed']}  ❌")
    print(f"  Errors:   {r['errors']}  ⚠️")
    print(f"  Skipped:  {r['skipped']}  ⏭️")
    print(f"  Time:     {r['elapsed_sec']}s")
    print(f"{'='*60}")

    # Category breakdown
    cats = {}
    for k, v in r['category_stats'].items():
        cat, status = k.rsplit(':', 1)
        if cat not in cats:
            cats[cat] = {}
        cats[cat][status] = v

    print(f"\n  CATEGORY BREAKDOWN:")
    for cat in sorted(cats):
        stats = cats[cat]
        total_cat = sum(stats.values())
        p = stats.get('pass', 0)
        f_ = stats.get('fail', 0)
        e = stats.get('error', 0)
        s = stats.get('skipped', 0)
        marker = '🔴' if (f_ + e) > 0 else '🟢'
        priority = ' ⭐' if cat in PRIORITY_CATEGORIES else ''
        print(f"  {marker} {cat}: {p}/{total_cat} pass{priority}")
        if f_ or e or s:
            extra = []
            if f_: extra.append(f'{f_} fail')
            if e: extra.append(f'{e} error')
            if s: extra.append(f'{s} skip')
            print(f"     ({', '.join(extra)})")

    # Show first failures
    if r['failures']:
        print(f"\n  FIRST FAILURES (up to 20):")
        for i, fail in enumerate(r['failures'][:20]):
            got_str = fail['got'] if isinstance(fail['got'], str) else str(fail['got'])
            print(f"  {i+1}. [{fail['category']}] {fail['name']}")
            print(f"     expr: {fail['expr']}")
            print(f"     inputs: {fail['inputs']}")
            print(f"     expected: {fail['expected']}, got: {got_str}")

    print(f"\n{'='*60}")

    # Pass rate
    runnable = r['passed'] + r['failed'] + r['errors']
    if runnable > 0:
        rate = r['passed'] / runnable * 100
        print(f"  PASS RATE: {rate:.1f}%")
    print(f"{'='*60}\n")

    return r['failed'] == 0 and r['errors'] == 0


def main():
    vectors_path = Path(__file__).parent.parent / 'test-vectors.json'
    if not vectors_path.exists():
        print(f"ERROR: {vectors_path} not found", file=sys.stderr)
        sys.exit(1)

    categories = None
    if '--priority' in sys.argv:
        categories = PRIORITY_CATEGORIES
        print("Running priority categories only: " + ", ".join(PRIORITY_CATEGORIES))

    results = run_tests(vectors_path, categories)
    all_pass = print_results(results)

    # Write JSON results for CI
    results_path = Path(__file__).parent / 'test_results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results written to {results_path}")

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
