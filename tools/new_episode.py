#!/usr/bin/env python3
"""Scaffold the next episode folder in an existing series.

Finds the highest ``episode_NN`` folder in the series and creates the next one
from templates, so you can build a series episode by episode.

  python3 tools/new_episode.py --series series/the_last_signal
  python3 tools/new_episode.py --series series/the_last_signal --episode 7
"""

from __future__ import annotations

import argparse
import re

from pipeline_config import ROOT, get_series_dir, load_series_config, load_style_template
from scaffold import create_episode, episode_folder_name, load_story_context


def next_episode_number(series_dir) -> int:
    numbers = []
    for path in series_dir.glob("episode_*"):
        match = re.match(r"episode_(\d+)$", path.name)
        if match and path.is_dir():
            numbers.append(int(match.group(1)))
    return (max(numbers) + 1) if numbers else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold the next episode in a series.")
    parser.add_argument(
        "--series",
        default=None,
        help="Series directory relative to repo root. Defaults to PIPELINE_SERIES_DIR.",
    )
    parser.add_argument(
        "--episode",
        type=int,
        default=None,
        help="Explicit episode number. Defaults to the next available number.",
    )
    args = parser.parse_args()

    series_dir = get_series_dir(args.series)
    if not series_dir.exists():
        raise SystemExit(f"Series directory not found: {series_dir}. Run tools/init_series.py first.")

    config = load_series_config(series_dir)
    series_meta = config.get("series", {}) if isinstance(config, dict) else {}
    series_title = series_meta.get("title", series_dir.name.replace("_", " ").title())
    logline = series_meta.get("logline", "Describe your series premise in one sentence.")

    style_name = config.get("style_template", "thriller_mystery") if isinstance(config, dict) else "thriller_mystery"
    style = load_style_template(style_name) or {}

    number = args.episode or next_episode_number(series_dir)
    episode_dir = series_dir / episode_folder_name(number)
    if episode_dir.exists() and any(episode_dir.glob("scenes.json")):
        raise SystemExit(f"Episode already exists: {episode_dir}")

    story_context = load_story_context(series_dir)
    result = create_episode(
        series_dir,
        number,
        series_title,
        logline,
        style,
        story_context=story_context,
        style_name=style_name,
    )

    try:
        series_rel = series_dir.relative_to(ROOT)
    except ValueError:
        series_rel = series_dir

    print(f"Created {episode_folder_name(number)} in {series_dir}")
    print("\nAuthor these files, then render:")
    for filename in ("scenes.json", "voiceover_text.txt", "upload_package.md"):
        target = episode_dir / filename
        if target.exists():
            print(f"  {target.as_uri()}")
    print(
        f"\n  python3 tools/run_episode_pipeline.py --series {series_rel} "
        f"--episode {episode_folder_name(number)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
