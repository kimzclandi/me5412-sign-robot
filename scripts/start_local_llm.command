#!/bin/zsh
set -euo pipefail
cd -- "$(dirname "$0")/.."
exec .venv/bin/python scripts/start_local_llm.py
