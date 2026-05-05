#!/usr/bin/env bash
# Run differential tests locally
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Running differential tests..."
python3 tests/differential_test.py "$@"
