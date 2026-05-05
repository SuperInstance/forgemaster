#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/phoenix/.openclaw/workspace/.keeper/grimoire')
from spellwright import main_loop

print("=== Running spellwright with 1 iteration ===")
main_loop(iterations=1)