"""CLI entry point for galois_retrieval."""

import sys
from .engine import main_cli

if __name__ == "__main__":
    sys.exit(main_cli())
