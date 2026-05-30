#!/usr/bin/env python3
"""Scaffold a new fiction series from templates."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from pipeline_config import ROOT, load_style_template


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_") or "my_series"


def render_template(path: Path, replacements: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"Skipping existing file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Created {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a new fiction series folder.")
    parser.add_argument("--name", required=True, help="Human-readable series title.")
    parser.add_argument(
        "--style",
        default="thriller_mystery",
        choices=("thriller_mystery", "romance_drama", "sci_fi"),
        help="Built-in style template to seed visual style and platform defaults.",
    )
    parser.add_argument(
        "--output-dir",
        default="series",
        help="Parent directory under the repo root, e.g. series or examples.",
    )
    parser.add_argument(
        "--slug",
        help="Optional folder slug. Defaults to a slugified version of --name.",
    )
    args = parser.parse_args()

    style = load_style_template(args.style)
    if not style:
        raise SystemExit(f"Unknown or missing style template: {args.style}")

    slug = args.slug or slugify(args.name)
    series_dir = (ROOT / args.output_dir / slug).resolve()
    if series_dir.exists() and any(series_dir.iterdir()):
        raise SystemExit(f"Series directory already exists and is not empty: {series_dir}")

    episode_dir = series_dir / "episode_01"
    asset_dirs = [
        episode_dir / "assets" / "voiceover",
        episode_dir / "assets" / "images",
        episode_dir / "assets" / "video",
        episode_dir / "assets" / "music",
        episode_dir / "assets" / "exports",
        episode_dir / "assets" / "work",
        series_dir / "notifications",
    ]
    for directory in asset_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    replacements = {
        "SERIES_TITLE": args.name,
        "LOGLINE": "Describe your series premise in one sentence.",
        "GENRE": style.get("genre", args.style),
    }

    write_if_missing(
        series_dir / "series_config.yaml",
        render_template(ROOT / "templates" / "series" / "series_config.template.yaml", replacements),
    )
    write_if_missing(
        series_dir / "series_bible.md",
        render_template(ROOT / "templates" / "series" / "series_bible.template.md", replacements),
    )
    write_if_missing(series_dir / "season_outline.md", "# Season Outline\n\nList episode hooks here.\n")

    scenes_template = json.loads(
        (ROOT / "templates" / "episode" / "scenes.template.json").read_text(encoding="utf-8")
    )
    scenes_template["style"] = style.get("visual_style", scenes_template["style"])
    scenes_template["cover"]["series_title"] = args.name
    scenes_template["cover"]["hook_lines"] = style.get("cover", {}).get("hook_lines", ["DON'T", "MISS", "THIS"])
    scenes_template["cover"]["hook_highlight"] = style.get("cover", {}).get("hook_highlight", "THIS")
    scenes_template["cover"]["background_prompt"] = style.get("cover", {}).get(
        "background_prompt",
        scenes_template["cover"].get("background_prompt", ""),
    )
    write_if_missing(episode_dir / "scenes.json", json.dumps(scenes_template, indent=2) + "\n")

    for filename, default in {
        "script.md": "# Episode 1 Script\n\nWrite the full narration script here.\n",
        "voiceover_text.txt": "Write the exact narration text that ElevenLabs should speak.\n",
        "voice_direction.md": "# Voice Direction\n\nDescribe pacing, emphasis, and emotional beats.\n",
        "visual_prompts.md": "# Visual Prompts\n\nOptional human-readable notes for each scene.\n",
        "upload_package.md": render_template(
            ROOT / "templates" / "episode" / "upload_package.template.md",
            {
                "EPISODE_NUMBER": "1",
                "SERIES_TITLE": args.name,
                "SERIES_LOGLINE": replacements["LOGLINE"],
                "HOOK_LINE": "Opening hook line for social captions.",
                "DISCLOSURE_TIKTOK": style.get("platforms", {}).get("tiktok", {}).get(
                    "disclosure", "This is a fictional story."
                ),
                "DISCLOSURE_YOUTUBE": style.get("platforms", {}).get("youtube_shorts", {}).get(
                    "disclosure",
                    "This is an original fictional story made with human creative direction and AI-assisted visuals.",
                ),
                "DISCLOSURE_INSTAGRAM": style.get("platforms", {}).get("instagram_reels", {}).get(
                    "disclosure", "Fictional story. Created for entertainment."
                ),
                "HASHTAGS_TIKTOK": " ".join(
                    f"#{tag}" for tag in style.get("platforms", {}).get("tiktok", {}).get("hashtags", [])
                ),
                "HASHTAGS_INSTAGRAM": " ".join(
                    f"#{tag}" for tag in style.get("platforms", {}).get("instagram_reels", {}).get("hashtags", [])
                ),
                "YOUTUBE_TITLE": f"{args.name} | Episode 1",
                "CLIFFHANGER_TEASE": "Tease the next episode here.",
                "OUTPUT_SLUG": "episode_01",
            },
        ),
    }.items():
        write_if_missing(episode_dir / filename, default)

    config_path = series_dir / "series_config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    if "style_template:" in config_text:
        config_text = re.sub(r"style_template:\s*\S+", f"style_template: {args.style}", config_text)
        config_path.write_text(config_text, encoding="utf-8")

    print("\nSeries scaffold created.")
    print(f"Series directory: {series_dir}")
    print("\nNext steps:")
    print("1. Copy .env.story.example to .env.story.local and add your API keys.")
    print(f"2. Set PIPELINE_SERIES_DIR={args.output_dir}/{slug} in .env.story.local")
    print("3. Edit episode_01/scenes.json, voiceover_text.txt, and script.md")
    print("4. Run: python3 tools/run_episode_pipeline.py --series", f"{args.output_dir}/{slug}", "--episode episode_01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
