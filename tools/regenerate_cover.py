#!/usr/bin/env python3
"""Regenerate episode cover background and/or composed typography."""

from __future__ import annotations

import argparse
import json
import sys

from cover_styles import (
    compose_cover,
    default_style_for_template,
    list_styles,
    resolve_cover_style_id,
)
from generate_episode_assets import EXPORTS_DIR, configure_episode, configure_series, generate_cover
from pipeline_config import episode_output_slug, get_series_dir, load_local_env, load_series_config, resolve_episode_path


def _pick_style_interactive(styles: list[dict], default_id: str) -> str:
    print("Cover styles:")
    for index, item in enumerate(styles, start=1):
        rec = " [recommended]" if item.get("recommended") else ""
        print(f"  {index}. {item['id']} — {item['name']}{rec}")
    choice = input(f"Select style [default {default_id}]: ").strip()
    if not choice:
        return default_id
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(styles):
            return styles[idx]["id"]
    if any(item["id"] == choice for item in styles):
        return choice
    raise SystemExit(f"Invalid style selection: {choice}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate an episode cover.")
    parser.add_argument("--series", default=None, help="Series directory (default PIPELINE_SERIES_DIR).")
    parser.add_argument("--episode", default="episode_01", help="Episode folder name.")
    parser.add_argument("--list-styles", action="store_true", help="List cover styles for this series template.")
    parser.add_argument("--style", metavar="STYLE_ID", help="Cover design style id.")
    parser.add_argument("--compose-only", action="store_true", help="Compose typography onto existing cover base.")
    parser.add_argument("--force-background", action="store_true", help="Regenerate cover background before composing.")
    parser.add_argument("--save-style", action="store_true", help="Persist chosen style to scenes.json cover.design_style.")
    parser.add_argument(
        "--cover-provider",
        choices=("fal", "openai", "local"),
        default="openai",
        help="Cover background provider when generating base image.",
    )
    parser.add_argument("--openai-cover", action="store_true", help="Use OpenAI for cover background.")
    args = parser.parse_args()

    load_local_env()
    series_dir = get_series_dir(args.series)
    episode_dir = resolve_episode_path(args.episode, series_dir)
    scenes_path = episode_dir / "scenes.json"
    if not scenes_path.exists():
        raise SystemExit(f"Missing scenes.json: {scenes_path}")

    config = load_series_config(series_dir)
    template_name = str(config.get("style_template", "thriller_mystery"))
    styles = list_styles(template_name)

    if args.list_styles:
        for item in styles:
            rec = " (template default)" if item.get("recommended") else ""
            print(f"{item['id']}: {item['name']}{rec}")
            if item.get("description"):
                print(f"  {item['description']}")
        return 0

    scenes_data = json.loads(scenes_path.read_text(encoding="utf-8"))
    default_id = default_style_for_template(template_name)
    style_id = args.style
    if not style_id and sys.stdin.isatty():
        style_id = _pick_style_interactive(styles, resolve_cover_style_id(scenes_data, series_dir) or default_id)
    if not style_id:
        style_id = resolve_cover_style_id(scenes_data, series_dir)

    if args.save_style:
        scenes_data.setdefault("cover", {})["design_style"] = style_id
        scenes_path.write_text(json.dumps(scenes_data, indent=2) + "\n", encoding="utf-8")
        print(f"Saved cover.design_style={style_id} to {scenes_path}")

    configure_series(args.series)
    configure_episode(args.episode)
    slug = episode_output_slug(episode_dir)
    base_path = EXPORTS_DIR / f"{slug}_cover_base.png"
    out_path = EXPORTS_DIR / f"{slug}_cover.png"

    if args.compose_only:
        if not base_path.exists():
            raise SystemExit(f"Missing cover base image: {base_path}")
        compose_cover(base_path, out_path, scenes_data, style_id=style_id, series_dir=series_dir)
        return 0

    cover_provider = args.cover_provider
    if args.openai_cover:
        cover_provider = "openai"
    generate_cover(
        force_cover=args.force_background,
        provider=cover_provider,
        cover_style=style_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
