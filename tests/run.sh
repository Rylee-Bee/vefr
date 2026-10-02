#!/usr/bin/env bash
# Run pytest the way a throwaway clone needs: link the dev-only node_modules
# (jsdom, gitignored) from the primary checkout, drop any foreign venv, stay offline.
#   usage: bash tests/run.sh tests/test_growth_engine.py
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
ln -sfn "$HOME/code/Rylee-Bee/vefr/node_modules" node_modules
exec env -u VIRTUAL_ENV uv run --offline python -m pytest -q "$@"
