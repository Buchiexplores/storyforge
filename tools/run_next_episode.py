#!/usr/bin/env python3
"""Render the next authored-but-unrendered episode in a series.

Designed for daily automation (cron): it scans the active series for the
lowest-numbered episode that has a ``scenes.json`` but no final vertical export
yet, and runs the full pipeline on it. Notifications (email or queued file) are
handled by ``run_episode_pipeline.py`` based on your ``.env.story.local``.

  python3 tools/run_next_episode.py
  python3 tools/run_next_episode.py --series series/the_last_signal --force

Exit codes:
  0  an episode was rendered, or there was nothing to do
  1  the pipeline failed (a failure notification is sent if notifications are on)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from pipeline_config import (
    ROOT,
    episode_output_slug,
    get_series_dir,
    load_local_env,
)

PIPELINE = ROOT / "tools" / "run_episode_pipeline.py"


def episode_number(path: Path) -> int:
    match = re.match(r"episode_(\d+)$", path.name)
    return int(match.group(1)) if match else 0


def find_next_episode(series_dir: Path) -> Path | None:
    """Lowest-numbered episode with scenes.json but no final export."""
    episodes = sorted(
        (p for p in series_dir.glob("episode_*") if p.is_dir() and (p / "scenes.json").exists()),
        key=episode_number,
    )
    for episode_dir in episodes:
        slug = episode_output_slug(episode_dir)
        export = episode_dir / "assets" / "exports" / f"{slug}_vertical.mp4"
        if not export.exists():
            return episode_dir
    return None


def main() -> int:
    load_local_env()
    parser = argparse.ArgumentParser(description="Render the next pending episode in a series.")
    parser.add_argument("--series", default=None, help="Series dir (defaults to PIPELINE_SERIES_DIR).")
    parser.add_argument(
        "passthrough",
        nargs=argparse.REMAINDER,
        help="Extra flags forwarded to run_episode_pipeline.py (e.g. --force).",
    )
    args = parser.parse_args()

    series_dir = get_series_dir(args.series)
    if not series_dir.exists():
        print(f"Series directory not found: {series_dir}")
        return 0

    next_episode = find_next_episode(series_dir)
    if next_episode is None:
        print(f"Nothing to render — every authored episode in {series_dir.name} already has an export.")
        return 0

    try:
        series_rel = series_dir.relative_to(ROOT)
    except ValueError:
        series_rel = series_dir

    cmd = [
        sys.executable,
        str(PIPELINE),
        "--series",
        str(series_rel),
        "--episode",
        next_episode.name,
        *[arg for arg in args.passthrough if arg != "--"],
    ]
    print("Rendering next episode:", next_episode.name)
    print(" ".join(str(part) for part in cmd))
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
