#!/usr/bin/env python3
"""Maintainer utility: regenerate the in-README episode player block from preview/example/episodes.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODES_JSON = ROOT / "preview" / "example" / "episodes.json"
README = ROOT / "README.md"
START = "<!-- README-PLAYER-START -->"
END = "<!-- README-PLAYER-END -->"


def badge(label: str, color: str) -> str:
    from urllib.parse import quote

    return (
        f"https://img.shields.io/badge/{quote(label, safe='')}"
        f"-{color}?style=for-the-badge"
    )


def nav_button(href: str, label: str, color: str) -> str:
    return f'<a href="{href}"><img src="{badge(label, color)}" alt="{label}"></a>'


def build_player_block(catalog: dict) -> str:
    episodes = catalog.get("episodes", [])
    series_title = catalog.get("series_title", "Storyforge Preview")
    series_description = catalog.get(
        "series_description",
        "Example output from the Storyforge pipeline.",
    )

    if not episodes:
        return (
            f"{START}\n\n"
            "_No preview episodes found. Run `./tools/prepare_preview_assets.sh`._\n\n"
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
        "Watch in the README (play below, then use **Next episode** to jump to the following part). "
        "For sidebar navigation, keyboard shortcuts, and auto-advance, open the "
        "[full interactive player](https://Buchiexplores.github.io/storyforge/preview/example/) on GitHub Pages.",
        "",
        f'<p align="center">Jump to episode: {picker}</p>',
        "",
    ]

    for index, ep in enumerate(episodes):
        number = ep["number"]
        title = ep["title"]
        file_name = ep.get("file", f"episode_{number:02d}.mp4")
        anchor = f"ep{number}"
        prev_href = f"#ep{episodes[index - 1]['number']}" if index > 0 else None
        next_href = f"#ep{episodes[index + 1]['number']}" if index < len(episodes) - 1 else None

        nav_parts = []
        if prev_href:
            nav_parts.append(nav_button(prev_href, "← Previous", "555555"))
        if next_href:
            nav_parts.append(nav_button(next_href, "Next episode →", "238636"))

        nav_html = " &nbsp; ".join(nav_parts) if nav_parts else ""

        lines.extend(
            [
                f'<p align="center" id="{anchor}">',
                f"  <strong>Episode {number} · {title}</strong><br><br>",
                f'  <video src="preview/example/{file_name}" controls width="270" playsinline preload="metadata"></video>',
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
        raise SystemExit(f"Missing {EPISODES_JSON}. Run tools/prepare_preview_assets.sh first.")

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
