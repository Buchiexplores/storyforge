#!/usr/bin/env python3
"""Shared scaffolding helpers for series and episode creation.

Used by both ``init_series.py`` (create a new series) and ``new_episode.py``
(append the next episode to an existing series). Keeping the logic here avoids
duplication and keeps the two entry-point scripts thin.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline_config import ROOT

STYLE_CHOICES = ("thriller_mystery", "romance_drama", "sci_fi")

ASSET_SUBDIRS = ("voiceover", "images", "video", "music", "exports", "work")

EPISODE_DEFAULTS = {
    "script.md": "# Episode {n} Script\n\nWrite the full narration script here.\n",
    "voiceover_text.txt": "Write the exact narration text that ElevenLabs should speak.\n",
    "voice_direction.md": "# Voice Direction\n\nDescribe pacing, emphasis, and emotional beats.\n",
    "visual_prompts.md": "# Visual Prompts\n\nOptional human-readable notes for each scene.\n",
}


@dataclass(frozen=True)
class ScaffoldResult:
    """Outcome of a scaffold operation, used to print review links."""

    target_dir: Path
    created_files: tuple[Path, ...]


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_") or "my_series"


def episode_folder_name(number: int) -> str:
    return f"episode_{number:02d}"


def render_template(path: Path, replacements: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def _write_if_missing(path: Path, content: str, created: list[Path]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(path)


def make_asset_dirs(episode_dir: Path) -> None:
    for name in ASSET_SUBDIRS:
        directory = episode_dir / "assets" / name
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")


def build_upload_package(
    episode_number: int, series_title: str, logline: str, style: dict[str, Any]
) -> str:
    platforms = style.get("platforms", {})
    return render_template(
        ROOT / "templates" / "episode" / "upload_package.template.md",
        {
            "EPISODE_NUMBER": str(episode_number),
            "SERIES_TITLE": series_title,
            "SERIES_LOGLINE": logline,
            "HOOK_LINE": "Opening hook line for social captions.",
            "DISCLOSURE_TIKTOK": platforms.get("tiktok", {}).get(
                "disclosure", "This is a fictional story."
            ),
            "DISCLOSURE_YOUTUBE": platforms.get("youtube_shorts", {}).get(
                "disclosure",
                "This is an original fictional story made with human creative "
                "direction and AI-assisted visuals.",
            ),
            "DISCLOSURE_INSTAGRAM": platforms.get("instagram_reels", {}).get(
                "disclosure", "Fictional story. Created for entertainment."
            ),
            "HASHTAGS_TIKTOK": " ".join(
                f"#{tag}" for tag in platforms.get("tiktok", {}).get("hashtags", [])
            ),
            "HASHTAGS_INSTAGRAM": " ".join(
                f"#{tag}" for tag in platforms.get("instagram_reels", {}).get("hashtags", [])
            ),
            "YOUTUBE_TITLE": f"{series_title} | Episode {episode_number}",
            "CLIFFHANGER_TEASE": "Tease the next episode here.",
            "OUTPUT_SLUG": episode_folder_name(episode_number),
        },
    )


def create_episode(
    series_dir: Path,
    episode_number: int,
    series_title: str,
    logline: str,
    style: dict[str, Any],
) -> ScaffoldResult:
    """Create one episode folder from templates. Skips files that already exist."""
    episode_dir = series_dir / episode_folder_name(episode_number)
    make_asset_dirs(episode_dir)
    created: list[Path] = []

    scenes = json.loads(
        (ROOT / "templates" / "episode" / "scenes.template.json").read_text(encoding="utf-8")
    )
    scenes["output_slug"] = episode_folder_name(episode_number)
    scenes["style"] = style.get("visual_style", scenes["style"])
    scenes["cover"]["series_title"] = series_title
    scenes["cover"]["episode_number"] = episode_number
    cover = style.get("cover", {})
    scenes["cover"]["hook_lines"] = cover.get("hook_lines", scenes["cover"]["hook_lines"])
    scenes["cover"]["hook_highlight"] = cover.get("hook_highlight", scenes["cover"]["hook_highlight"])
    scenes["cover"]["background_prompt"] = cover.get(
        "background_prompt", scenes["cover"].get("background_prompt", "")
    )
    _write_if_missing(episode_dir / "scenes.json", json.dumps(scenes, indent=2) + "\n", created)

    for filename, default in EPISODE_DEFAULTS.items():
        _write_if_missing(episode_dir / filename, default.format(n=episode_number), created)

    _write_if_missing(
        episode_dir / "upload_package.md",
        build_upload_package(episode_number, series_title, logline, style),
        created,
    )

    return ScaffoldResult(episode_dir, tuple(created))


def create_series(
    series_dir: Path,
    series_title: str,
    logline: str,
    style_name: str,
    style: dict[str, Any],
    episode_count: int,
) -> ScaffoldResult:
    """Create the series-level files plus ``episode_count`` episode folders."""
    created: list[Path] = []
    series_dir.mkdir(parents=True, exist_ok=True)
    (series_dir / "notifications").mkdir(parents=True, exist_ok=True)
    keep = series_dir / "notifications" / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")

    replacements = {
        "SERIES_TITLE": series_title,
        "LOGLINE": logline,
        "GENRE": style.get("genre", style_name),
    }
    _write_if_missing(
        series_dir / "series_config.yaml",
        render_template(
            ROOT / "templates" / "series" / "series_config.template.yaml", replacements
        ),
        created,
    )
    _write_if_missing(
        series_dir / "series_bible.md",
        render_template(
            ROOT / "templates" / "series" / "series_bible.template.md", replacements
        ),
        created,
    )
    _write_if_missing(
        series_dir / "season_outline.md",
        "# Season Outline\n\nList one hook line per episode here.\n",
        created,
    )

    config_path = series_dir / "series_config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    if "style_template:" in config_text:
        config_text = re.sub(r"style_template:\s*\S+", f"style_template: {style_name}", config_text)
        config_text = config_text.replace('title: "Your Series Title"', f'title: "{series_title}"')
        config_text = config_text.replace(
            'logline: "One sentence describing the core premise."', f'logline: "{logline}"'
        )
        config_path.write_text(config_text, encoding="utf-8")

    for number in range(1, episode_count + 1):
        result = create_episode(series_dir, number, series_title, logline, style)
        created.extend(result.created_files)

    return ScaffoldResult(series_dir, tuple(created))
