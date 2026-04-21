"""Stylistic features from AST / source code."""

import os
import re
import ast


def _find_source_files(repo_path: str, exts):
    for root, _, files in os.walk(repo_path):
        if ".git" in root:
            continue
        for f in files:
            if any(f.endswith(e) for e in exts):
                yield os.path.join(root, f)


def _is_snake_case(name: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9_]*$", name))


def _is_camel_case(name: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9]*$", name)) and any(c.isupper() for c in name[1:])


def _analyze_python_file(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return None

    func_lengths = []
    snake = 0
    camel = 0
    doc_comments = 0
    total_funcs = 0
    type_annotated = 0
    total_params = 0
    unwrap_count = 0
    result_count = 0
    magic_numbers = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_funcs += 1
            body_lines = node.end_lineno - node.lineno if node.end_lineno else 1
            func_lengths.append(body_lines)
            if ast.get_docstring(node):
                doc_comments += 1
            for arg in node.args.args + node.args.kwonlyargs + node.args.posonlyargs:
                total_params += 1
                if arg.annotation:
                    type_annotated += 1
                name = arg.arg
                if _is_snake_case(name):
                    snake += 1
                elif _is_camel_case(name):
                    camel += 1

        if isinstance(node, ast.Name):
            if node.id in ("unwrap", "expect"):
                unwrap_count += 1
            if node.id == "Result":
                result_count += 1

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value not in (0, 1, -1, 2):
                magic_numbers += 1

    return {
        "func_lengths": func_lengths,
        "snake": snake,
        "camel": camel,
        "doc_comments": doc_comments,
        "total_funcs": total_funcs,
        "type_annotated": type_annotated,
        "total_params": total_params,
        "unwrap_count": unwrap_count,
        "result_count": result_count,
        "magic_numbers": magic_numbers,
    }


def _analyze_rust_file(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except Exception:
        return None

    lines = source.splitlines()
    func_lengths = []
    snake = 0
    camel = 0
    doc_comments = 0
    total_funcs = 0
    unwrap_count = source.count(".unwrap()") + source.count(".expect(")
    result_count = source.count("Result<") + source.count("-> Result")
    magic_numbers = 0

    in_fn = False
    fn_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("fn ") or stripped.startswith("pub fn "):
            in_fn = True
            fn_start = i
            total_funcs += 1
            if i > 0 and lines[i - 1].strip().startswith("///"):
                doc_comments += 1
            m = re.search(r"fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", stripped)
            if m:
                name = m.group(1)
                if _is_snake_case(name):
                    snake += 1
                elif _is_camel_case(name):
                    camel += 1
        elif in_fn:
            if stripped == "}":
                func_lengths.append(i - fn_start + 1)
                in_fn = False

    for token in re.findall(r"\b\d+\.?\d*\b", source):
        try:
            val = float(token)
            if val not in (0, 1, -1, 2):
                magic_numbers += 1
        except ValueError:
            pass

    return {
        "func_lengths": func_lengths,
        "snake": snake,
        "camel": camel,
        "doc_comments": doc_comments,
        "total_funcs": total_funcs,
        "type_annotated": 0,
        "total_params": 0,
        "unwrap_count": unwrap_count,
        "result_count": result_count,
        "magic_numbers": magic_numbers,
    }


def _analyze_c_file(path: str):
    """Analyze C/C++ source files for stylistic features."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except Exception:
        return None

    lines = source.splitlines()
    func_lengths = []
    snake = 0
    camel = 0
    doc_comments = 0
    total_funcs = 0
    magic_numbers = 0
    assert_count = source.count("assert(") + source.count("ASSERT(")

    # Function detection via regex (handles most C/C++ patterns)
    fn_pattern = re.compile(
        r"^(?:static\s+|inline\s+|extern\s+)*(?:void|int|char|long|short|unsigned|signed|"
        r"float|double|bool|size_t|ssize_t|struct\s+\w+|enum\s+\w+|"
        r"\w+_t|\w+\*|\w+\s+\*)?\s*"
        r"(\w+)\s*\([^)]*\)\s*(?:\{|$)",
        re.MULTILINE
    )

    # Brace-based function length measurement
    brace_depth = 0
    fn_start_line = -1
    fn_names_found = set()

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track doc comments (/** */ and /// style)
        if stripped.startswith("/**") or stripped.startswith("/*"):
            doc_comments += 1
        elif stripped.startswith("///"):
            doc_comments += 1

        # Function name detection
        m = fn_pattern.match(stripped)
        if m:
            name = m.group(1)
            # Skip control flow and type keywords
            if name not in ("if", "while", "for", "switch", "return", "sizeof",
                           "typedef", "enum", "struct", "union", "do", "case",
                           "define", "ifdef", "ifndef", "endif", "include",
                           "pragma", "undef"):
                total_funcs += 1
                if name not in fn_names_found:
                    fn_names_found.add(name)
                    if _is_snake_case(name):
                        snake += 1
                    elif _is_camel_case(name):
                        camel += 1
                if "{" in stripped:
                    fn_start_line = i
                    brace_depth = 1
        elif fn_start_line >= 0 and brace_depth > 0:
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth == 0:
                func_lengths.append(i - fn_start_line + 1)
                fn_start_line = -1

    for token in re.findall(r"\b\d+\.?\d*\b", source):
        try:
            val = float(token)
            if val not in (0, 1, -1, 2):
                magic_numbers += 1
        except ValueError:
            pass

    return {
        "func_lengths": func_lengths,
        "snake": snake,
        "camel": camel,
        "doc_comments": doc_comments,
        "total_funcs": total_funcs,
        "type_annotated": 0,
        "total_params": 0,
        "unwrap_count": assert_count,
        "result_count": 0,
        "magic_numbers": magic_numbers,
    }


def extract_stylistic_features(repo_path: str) -> dict:
    features = {}
    py_results = [_analyze_python_file(p) for p in _find_source_files(repo_path, (".py",))]
    rs_results = [_analyze_rust_file(p) for p in _find_source_files(repo_path, (".rs",))]
    c_results = [_analyze_c_file(p) for p in _find_source_files(repo_path, (".c", ".h", ".cpp", ".hpp"))]
    all_results = [r for r in py_results + rs_results + c_results if r is not None]

    if not all_results:
        features["function_length_mean"] = 0.0
        features["function_length_std"] = 0.0
        features["function_length_median"] = 0.0
        features["naming_convention_score"] = 0.0
        features["doc_comment_frequency"] = 0.0
        features["error_handling_style"] = 0.0
        features["type_annotation_density"] = 0.0
        features["magic_number_frequency"] = 0.0
        return features

    all_lengths = []
    for r in all_results:
        all_lengths.extend(r["func_lengths"])

    if all_lengths:
        n = len(all_lengths)
        mean_len = sum(all_lengths) / n
        var_len = sum((x - mean_len) ** 2 for x in all_lengths) / n
        features["function_length_mean"] = mean_len
        features["function_length_std"] = var_len ** 0.5
        sorted_len = sorted(all_lengths)
        features["function_length_median"] = sorted_len[n // 2] if n % 2 else (sorted_len[n // 2 - 1] + sorted_len[n // 2]) / 2
    else:
        features["function_length_mean"] = 0.0
        features["function_length_std"] = 0.0
        features["function_length_median"] = 0.0

    total_snake = sum(r["snake"] for r in all_results)
    total_camel = sum(r["camel"] for r in all_results)
    features["naming_convention_score"] = total_snake / max(total_camel, 1.0)

    total_funcs = sum(r["total_funcs"] for r in all_results)
    total_docs = sum(r["doc_comments"] for r in all_results)
    features["doc_comment_frequency"] = total_docs / max(total_funcs, 1.0)

    total_unwrap = sum(r["unwrap_count"] for r in all_results)
    total_result = sum(r["result_count"] for r in all_results)
    features["error_handling_style"] = total_unwrap / max(total_result, 1.0)

    total_annotated = sum(r["type_annotated"] for r in all_results)
    total_params = sum(r["total_params"] for r in all_results)
    features["type_annotation_density"] = total_annotated / max(total_params, 1.0)

    total_magic = sum(r["magic_numbers"] for r in all_results)
    total_lines = 0
    for p in _find_source_files(repo_path, (".py", ".rs")):
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                total_lines += len(fh.readlines())
        except Exception:
            pass
    features["magic_number_frequency"] = total_magic / max(total_lines, 1.0)

    return features
