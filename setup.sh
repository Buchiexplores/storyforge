#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env.story.local ]; then
  cp .env.story.example .env.story.local
  echo "Created .env.story.local — add your API keys before running the pipeline."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  source .venv/bin/activate"
echo "  # Edit .env.story.local with your API keys"
echo "  python tools/run_episode_pipeline.py --series examples/phone_from_tomorrow --episode episode_01"
