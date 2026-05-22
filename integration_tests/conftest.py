import sys
from pathlib import Path

# Ensure constraint-theory-core package is importable from workspace root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "constraint-theory-core"))
