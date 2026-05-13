#!/usr/bin/env bash
# Run all linters and tests. Exit non-zero if anything fails.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "── ruff check"
uv run ruff check app tests

echo "── ruff format --check"
uv run ruff format --check app tests

echo "── mypy"
uv run mypy app

echo "── pytest"
uv run pytest -q

echo "all checks passed"
