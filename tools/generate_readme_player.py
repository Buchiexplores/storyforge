#!/usr/bin/env python3
"""Maintainer utility: regenerate the in-README episode player block from preview/example/episodes.json."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODES_JSON = ROOT / "preview" / "example" / "episodes.json"
README = ROOT / "README.md"
START = "<!-- README-PLAYER-START -->"
END = "<!-- README-PLAYER-END -->"
DEFAULT_GITHUB = {
    "owner": "Buchiexplores",
    "repo": "storyforge",
    "branch": "main",
    "preview_path": "preview/example",
}


def badge(label: str, color: str) -> str:
    from urllib.parse import quote

    return (
        f"https://img.shields.io/badge/{quote(label, safe='')}"
        f"-{color}?style=for-the-badge"
    )


def nav_button(href: str, label: str, color: str) -> str:
    return f'<a href="{href}"><img src="{badge(label, color)}" alt="{label}"></a>'


def pages_episode_url(pages_player: str, number: int) -> str:
    base = pages_player.rstrip("/")
    return f"{base}/?ep={number}"


def github_blob_video_url(file_name: str, catalog: dict) -> str:
    """GitHub's file viewer plays MP4 inline — works without GitHub Pages."""
    github = {**DEFAULT_GITHUB, **(catalog.get("github") or {})}
    owner = os.getenv("STORYFORGE_GITHUB_OWNER", github["owner"])
    repo = os.getenv("STORYFORGE_GITHUB_REPO", github["repo"])
    branch = os.getenv("STORYFORGE_GITHUB_BRANCH", github["branch"])
    preview_path = github["preview_path"].strip("/")
    return f"https://github.com/{owner}/{repo}/blob/{branch}/{preview_path}/{file_name}"


def poster_src(ep: dict, catalog: dict) -> str:
    github = {**DEFAULT_GITHUB, **(catalog.get("github") or {})}
    preview_path = github["preview_path"].strip("/")
    if ep.get("poster"):
        return f"{preview_path}/{ep['poster'].lstrip('/')}"
    stem = Path(ep.get("file", f"episode_{ep['number']:02d}.mp4")).stem
    return f"{preview_path}/posters/{stem}.jpg"


def build_player_block(catalog: dict) -> str:
    episodes = catalog.get("episodes", [])
    series_title = catalog.get("series_title", "Storyforge Preview")
    series_description = catalog.get(
        "series_description",
        "Example output from the Storyforge pipeline.",
    )
    pages_player = catalog.get(
        "pages_player_url",
        "https://Buchiexplores.github.io/storyforge/preview/example/",
    )

    if not episodes:
        return (
            f"{START}\n\n"
            "_No preview episodes in `preview/example/`._\n\n"
            f"{END}"
        )

    picker = " · ".join(
        f'<a href="#ep{ep["number"]}">{ep["number"]}</a>' for ep in episodes
    )

    lines = [
        START,
        "",
        f"**{series_title}** — {series_description}",
        "",
        "**Click any poster below to watch** that episode (opens GitHub's built-in video player). "
        f"For sidebar navigation, keyboard shortcuts, and auto-advance, use the "
        f"[interactive player on GitHub Pages]({pages_player}) "
        "(enable Pages under repo Settings → Pages → branch `main`, folder `/`).",
        "",
        "> GitHub README cannot embed in-page video players for repo-hosted MP4s. "
        "Posters link to each episode's MP4 on GitHub where you can press play.",
        "",
        f'<p align="center">Jump to episode: {picker}</p>',
        "",
    ]

    for index, ep in enumerate(episodes):
        number = ep["number"]
        title = ep["title"]
        file_name = ep.get("file", f"episode_{number:02d}.mp4")
        anchor = f"ep{number}"
        watch_url = github_blob_video_url(file_name, catalog)
        img_src = poster_src(ep, catalog)
        alt = f"Episode {number} · {title} — click to watch"
        prev_href = f"#ep{episodes[index - 1]['number']}" if index > 0 else None
        next_href = f"#ep{episodes[index + 1]['number']}" if index < len(episodes) - 1 else None

        nav_parts = []
        if prev_href:
            nav_parts.append(nav_button(prev_href, "← Previous", "555555"))
        nav_parts.append(
            nav_button(watch_url, "▶ Watch this episode", "238636")
        )
        if next_href:
            nav_parts.append(nav_button(next_href, "Next episode →", "238636"))

        nav_html = " &nbsp; ".join(nav_parts)

        lines.extend(
            [
                f'<p align="center" id="{anchor}">',
                f"  <strong>Episode {number} · {title}</strong><br><br>",
                f'  <a href="{watch_url}">',
                f'    <img src="{img_src}" width="270" alt="{alt}">',
                "  </a>",
                "  <br><br>",
                f"  {nav_html}",
                "</p>",
                "",
            ]
        )

    lines.append(END)
    return "\n".join(lines)


def patch_readme(block: str) -> None:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(text):
        text = pattern.sub(block, text)
    else:
        raise SystemExit(
            f"Could not find {START} … {END} markers in README.md. "
            "Add them in the Example output section first."
        )
    README.write_text(text, encoding="utf-8")


def main() -> int:
    if not EPISODES_JSON.exists():
        raise SystemExit(f"Missing {EPISODES_JSON}.")

    catalog = json.loads(EPISODES_JSON.read_text(encoding="utf-8"))
    block = build_player_block(catalog)

    if "--stdout" in sys.argv:
        print(block)
        return 0

    patch_readme(block)
    print(f"Updated README player block ({len(catalog.get('episodes', []))} episodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
