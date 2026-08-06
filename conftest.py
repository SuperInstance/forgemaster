"""Root conftest for Forgemaster monorepo.

Adds all subproject source directories to sys.path so pytest can
collect tests across the entire monorepo without requiring each
subproject to be pip-installed.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

# (subpath, package_dir_relative_to_subpath)
#   - subpath is the project directory under forgemaster/
#   - package_dir is the directory containing the importable package
_SUBPROJECTS = [
    # products
    ("products/clock-sync-probe",       "."),
    ("products/metronome-dashboard",    "."),
    ("products/metronome-sync",         "."),
    # fleet
    ("fleet/fleet-math-py",             "."),
    # constraint-theory core library
    ("libs/constraint-theory-py",        "."),
    # sunset ecosystem
    ("libs/sunset-ecosystem",            "."),
    # demo (imports from project root)
    ("demo/three-agent-demo",           "."),
    ("demo/three-agent-demo/distributed", "."),
]

for _sub, _pkg in _SUBPROJECTS:
    _p = _ROOT / _sub / _pkg
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
