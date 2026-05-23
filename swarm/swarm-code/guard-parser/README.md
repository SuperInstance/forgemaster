# GUARD Parser

Pure Python GUARD DSL parser for the FLUX constraint-safety verification ecosystem.

## Usage

```python
from guard_parser import parse_guard

ast = parse_guard("""
constraint motor_temp {
  expr: temperature < 120.0 && rpm > 0,
  inputs: [temperature: f64, rpm: u32],
  update_rate: 1000 Hz
}
""")
print(ast.to_json())
```

## Requirements

- Python 3.11+ (no external dependencies)

## Running Tests

```bash
cd guard-parser/
python test_guard_parser.py
# or: python -m pytest test_guard_parser.py
```

## Performance

~50,000 lines/sec on CPython 3.11; ~200,000 lines/sec on PyPy.
