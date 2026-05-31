#!/usr/bin/env python3
"""Scaffold a new fiction series from templates.

Two ways to run it:

  Interactive wizard (recommended for first-timers) — just run with no flags:
      python3 tools/init_series.py

  Non-interactive (scriptable / CI) — pass everything as flags:
      python3 tools/init_series.py --name "The Last Signal" --style sci_fi --episodes 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline_config import ROOT, load_style_template
from scaffold import STYLE_CHOICES, ScaffoldResult, create_series, slugify


def prompt(question: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{question}{suffix}: ").strip()
    return answer or (default or "")


def choose_style() -> str:
    print("\nChoose a built-in style template:")
    for index, name in enumerate(STYLE_CHOICES, start=1):
        template = load_style_template(name) or {}
        description = template.get("description", "")
        suffix = f" — {description}" if description else ""
        print(f"  {index}. {name}{suffix}")
    while True:
        raw = input(f"Style [1-{len(STYLE_CHOICES)}] (1): ").strip() or "1"
        if raw.isdigit() and 1 <= int(raw) <= len(STYLE_CHOICES):
            return STYLE_CHOICES[int(raw) - 1]
        if raw in STYLE_CHOICES:
            return raw
        print("  Please enter a number from the list.")


def prompt_int(question: str, default: int, minimum: int = 1) -> int:
    while True:
        raw = input(f"{question} [{default}]: ").strip() or str(default)
        if raw.isdigit() and int(raw) >= minimum:
            return int(raw)
        print(f"  Please enter a whole number >= {minimum}.")


def run_wizard() -> argparse.Namespace:
    print("=" * 60)
    print("  Storyforge — new series wizard")
    print("=" * 60)
    name = ""
    while not name:
        name = prompt("Series title (e.g. The Last Signal)").strip()
        if not name:
            print("  A title is required.")
    style = choose_style()
    episodes = prompt_int("How many episode folders to scaffold", 5)
    logline = prompt(
        "One-sentence premise (logline)",
        "Describe your series premise in one sentence.",
    )
    output_dir = prompt("Parent folder", "series")
    slug = slugify(name)
    print(f"\nSlug folder name: {slug}  (override below or press Enter to keep)")
    slug = prompt("Folder slug", slug) or slug

    return argparse.Namespace(
        name=name,
        style=style,
        episodes=episodes,
        logline=logline,
        output_dir=output_dir,
        slug=slug,
        set_active=None,  # decided interactively after creation
    )


def print_review_links(result: ScaffoldResult, series_rel: str) -> None:
    print("\n" + "-" * 60)
    print("Review your generated templates (open these to author content):")
    print("-" * 60)
    bible = result.target_dir / "series_bible.md"
    outline = result.target_dir / "season_outline.md"
    for path in (bible, outline):
        if path.exists():
            print(f"  {path.as_uri()}")
    episodes = sorted(p for p in result.target_dir.glob("episode_*") if p.is_dir())
    for episode in episodes:
        print(f"\n  {episode.name}/")
        for filename in ("scenes.json", "voiceover_text.txt", "upload_package.md"):
            target = episode / filename
            if target.exists():
                print(f"    {target.as_uri()}")


def maybe_set_active_series(series_rel: str, decision: bool | None) -> None:
    """Optionally update PIPELINE_SERIES_DIR in .env.story.local."""
    env_path = ROOT / ".env.story.local"
    if decision is None:
        if not sys.stdin.isatty():
            decision = False
        else:
            decision = input(
                f"\nSet PIPELINE_SERIES_DIR={series_rel} in .env.story.local now? [Y/n]: "
            ).strip().lower() in {"", "y", "yes"}
    if not decision:
        print(f"\nManual step: set PIPELINE_SERIES_DIR={series_rel} in .env.story.local")
        return
    if not env_path.exists():
        print(
            "\n.env.story.local not found. Run ./setup.sh first, then set "
            f"PIPELINE_SERIES_DIR={series_rel}"
        )
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = []
    found = False
    for line in lines:
        if line.startswith("PIPELINE_SERIES_DIR="):
            updated.append(f"PIPELINE_SERIES_DIR={series_rel}")
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append(f"PIPELINE_SERIES_DIR={series_rel}")
    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"\nUpdated .env.story.local -> PIPELINE_SERIES_DIR={series_rel}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a new fiction series folder.")
    parser.add_argument("--name", help="Human-readable series title. Omit to launch the wizard.")
    parser.add_argument("--style", default="thriller_mystery", choices=STYLE_CHOICES)
    parser.add_argument("--episodes", type=int, default=1, help="Number of episode folders to create.")
    parser.add_argument("--logline", default="Describe your series premise in one sentence.")
    parser.add_argument("--output-dir", default="series", help="Parent directory under the repo root.")
    parser.add_argument("--slug", help="Optional folder slug. Defaults to a slugified --name.")
    parser.add_argument(
        "--set-active",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write PIPELINE_SERIES_DIR into .env.story.local (default: ask).",
    )
    args = parser.parse_args()

    if not args.name:
        if not sys.stdin.isatty():
            parser.error("--name is required when not running interactively.")
        args = run_wizard()
    elif not getattr(args, "slug", None):
        args.slug = slugify(args.name)

    style = load_style_template(args.style)
    if not style:
        raise SystemExit(f"Unknown or missing style template: {args.style}")

    slug = args.slug or slugify(args.name)
    series_dir = (ROOT / args.output_dir / slug).resolve()
    if series_dir.exists() and any(series_dir.iterdir()):
        raise SystemExit(f"Series directory already exists and is not empty: {series_dir}")

    episode_count = max(1, int(args.episodes))
    result = create_series(
        series_dir=series_dir,
        series_title=args.name,
        logline=args.logline,
        style_name=args.style,
        style=style,
        episode_count=episode_count,
    )

    series_rel = f"{args.output_dir}/{slug}"
    print(f"\nSeries scaffold created at: {series_dir}")
    print(f"Episodes scaffolded: {episode_count}")
    print_review_links(result, series_rel)
    maybe_set_active_series(series_rel, getattr(args, "set_active", None))

    print("\nNext steps:")
    print("  1. Add your API keys to .env.story.local (see docs/API_KEYS.md)")
    print(f"  2. Author episode_01 content in {series_rel}/episode_01/")
    print(f"  3. Render it: python3 tools/run_episode_pipeline.py --series {series_rel} --episode episode_01")
    print(f"  4. Add the next episode: python3 tools/new_episode.py --series {series_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
