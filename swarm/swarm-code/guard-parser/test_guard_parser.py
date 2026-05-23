"""Tests for guard_parser.py"""
import json
from guard_parser import tokenize, parse_guard


def test_tokenize_basic():
    toks = tokenize("constraint foo { expr: a < 10 }")
    kinds = [t.kind for t in toks if t.kind not in ("EOF",)]
    assert kinds == ["IDENT", "IDENT", "LBRACE", "IDENT", "COLON", "IDENT", "LT", "INT", "RBRACE"]


def test_parse_simple():
    src = """
    constraint motor_temp {
      expr: temperature < 120.0,
      inputs: [temperature: f64],
      update_rate: 1000 Hz
    }
    """
    ast = parse_guard(src)
    assert ast.name == "motor_temp"
    assert ast.update_rate_hz == 1000
    assert ast.inputs[0].name == "temperature"
    assert ast.inputs[0].dtype == "f64"


def test_parse_boolean_expr():
    src = """
    constraint safe_speed {
      expr: rpm > 0 && rpm < 8000,
      inputs: [rpm: u32],
      update_rate: 500 Hz
    }
    """
    ast = parse_guard(src)
    assert ast.expr.op == "AND"
    assert ast.expr.args[0].op == "GT"
    assert ast.expr.args[1].op == "LT"


def test_parse_arithmetic():
    src = """
    constraint power_limit {
      expr: (voltage * current) < 150.0,
      inputs: [voltage: f64, current: f64],
      update_rate: 100 Hz
    }
    """
    ast = parse_guard(src)
    assert ast.expr.op == "LT"
    assert ast.expr.args[0].op == "MUL"


def test_json_roundtrip():
    src = """
    constraint demo {
      expr: x == 42,
      inputs: [x: u32],
      update_rate: 1 Hz
    }
    """
    ast = parse_guard(src)
    data = json.loads(ast.to_json())
    assert data["name"] == "demo"
    assert data["update_rate_hz"] == 1


def test_negation():
    src = """
    constraint not_hot {
      expr: !(temperature >= 100.0),
      inputs: [temperature: f64],
      update_rate: 10 Hz
    }
    """
    ast = parse_guard(src)
    assert ast.expr.op == "NOT"
    assert ast.expr.args[0].op == "GE"


if __name__ == "__main__":
    test_tokenize_basic()
    test_parse_simple()
    test_parse_boolean_expr()
    test_parse_arithmetic()
    test_json_roundtrip()
    test_negation()
    print("All 6 tests passed.")
