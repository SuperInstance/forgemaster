"""Allow running the package as a module: python -m sim_pipeline ..."""

import sys
from .cli import main

sys.exit(main())
