#!/usr/bin/env bash
# Optional manual step-by-step runner. Prefer tools/run_episode_pipeline.py for full runs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERIES="${PIPELINE_SERIES_DIR:-examples/phone_from_tomorrow}"
EP="${1:-episode_01}"

cd "$ROOT"

OPENAI_IMAGE_STRICT=1 python3 tools/generate_episode_assets.py \
  --series "$SERIES" --episode "$EP" --voice

OPENAI_IMAGE_STRICT=1 python3 tools/generate_episode_assets.py \
  --series "$SERIES" --episode "$EP" --images --openai-images --force-images

OPENAI_IMAGE_STRICT=1 python3 tools/generate_episode_assets.py \
  --series "$SERIES" --episode "$EP" --cover --openai-cover --force-cover

python3 tools/generate_episode_assets.py \
  --series "$SERIES" --episode "$EP" --videos --local-videos --force-videos

python3 tools/render_episode.py --series "$SERIES" --episode "$EP"
