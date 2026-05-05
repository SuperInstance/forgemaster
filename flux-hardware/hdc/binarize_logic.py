#!/usr/bin/env python3
"""Entry point for the GitHub Actions SRAM bake workflow."""
import logging
import sys
from pathlib import Path

from binarize_logic import generate_all_outputs

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Use repository root from CLI arg or current working directory
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    output_dir = repo_root / "flux-hardware" / "hdc"

    try:
        generate_all_outputs(repo_root, output_dir)
        return 0
    except Exception as e:
        logging.critical(f"SRAM bake workflow failed: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
