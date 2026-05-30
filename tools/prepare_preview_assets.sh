#!/usr/bin/env bash
# Maintainer utility: refresh committed sample videos in preview/example/ from pipeline exports.
# End users do not need to run this — preview/example/ is a static demo shipped with the repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERIES="${1:-examples/phone_from_tomorrow}"
DEST="$ROOT/preview/example"
SERIES_PATH="$ROOT/$SERIES"

mkdir -p "$DEST"

copied=0
copied_slugs=()

for episode_dir in "$SERIES_PATH"/episode_*; do
  [ -d "$episode_dir" ] || continue
  slug="$(basename "$episode_dir")"
  src="$episode_dir/assets/exports/${slug}_vertical.mp4"
  if [ -f "$src" ]; then
    cp "$src" "$DEST/${slug}.mp4"
    echo "Copied $slug"
    copied=$((copied + 1))
    copied_slugs+=("$slug")
  fi
done

if [ "$copied" -eq 0 ]; then
  echo "No episode exports found under $SERIES." >&2
  echo "Run the pipeline first, e.g.:" >&2
  echo "  python3 tools/run_episode_pipeline.py --series $SERIES --episode episode_01" >&2
  exit 1
fi

python3 - "$SERIES_PATH" "$DEST" "${copied_slugs[@]}" <<'PY'
import json
import re
import sys
from pathlib import Path

series_path = Path(sys.argv[1])
dest = Path(sys.argv[2])
slugs = sys.argv[3:]

DEFAULT_DESCRIPTION = (
    "Example output from the Storyforge pipeline — Afro-futurist mystery thriller."
)

series_title = "Storyforge Preview"
series_description = DEFAULT_DESCRIPTION

episodes = []
for slug in sorted(slugs, key=lambda s: int(re.search(r"(\d+)$", s).group(1)) if re.search(r"(\d+)$", s) else s):
    scenes_path = series_path / slug / "scenes.json"
    title = slug.replace("_", " ").title()
    number = int(re.search(r"(\d+)$", slug).group(1)) if re.search(r"(\d+)$", slug) else len(episodes) + 1

    if scenes_path.is_file():
        with scenes_path.open(encoding="utf-8") as f:
            data = json.load(f)
        title = data.get("episode_title") or title
        cover = data.get("cover") or {}
        if episodes == [] and cover.get("series_title"):
            series_title = cover["series_title"]

    episodes.append(
        {
            "id": slug,
            "number": number,
            "title": title,
            "file": f"{slug}.mp4",
        }
    )

catalog = {
    "series_title": series_title,
    "series_description": series_description,
    "episodes": episodes,
}

out = dest / "episodes.json"
with out.open("w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2)
    f.write("\n")

print(f"Wrote {out} ({len(episodes)} episode(s))")
PY

echo "Done. $copied episode(s) ready in preview/example/"

python3 "$ROOT/tools/generate_readme_player.py"
