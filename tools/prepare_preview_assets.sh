#!/usr/bin/env bash
# Copy generated vertical exports into docs/preview/episodes/ for README and GitHub Pages.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERIES="${1:-examples/phone_from_tomorrow}"
DEST="$ROOT/docs/preview/episodes"

mkdir -p "$DEST"

copied=0
for episode_dir in "$ROOT/$SERIES"/episode_*; do
  [ -d "$episode_dir" ] || continue
  slug="$(basename "$episode_dir")"
  src="$episode_dir/assets/exports/${slug}_vertical.mp4"
  if [ -f "$src" ]; then
    cp "$src" "$DEST/${slug}.mp4"
    echo "Copied $slug"
    copied=$((copied + 1))
  fi
done

if [ "$copied" -eq 0 ]; then
  echo "No episode exports found under $SERIES." >&2
  echo "Run the pipeline first, e.g.:" >&2
  echo "  python3 tools/run_episode_pipeline.py --series $SERIES --episode episode_01" >&2
  exit 1
fi

echo "Done. $copied episode(s) ready in docs/preview/episodes/"
