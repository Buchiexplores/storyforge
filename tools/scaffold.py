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

STYLE_CHOICES = (
    "thriller_mystery",
    "horror",
    "noir",
    "action",
    "sci_fi",
    "cyberpunk",
    "fantasy",
    "anime",
    "romance_drama",
    "comedy",
    "western",
    "period_drama",
)

ASSET_SUBDIRS = ("voiceover", "images", "video", "music", "exports", "work")


@dataclass(frozen=True)
class ScaffoldResult:
    """Outcome of a scaffold operation, used to print review links."""

    target_dir: Path
    created_files: tuple[Path, ...]


MAX_SLUG_LENGTH = 48
MAX_SLUG_WORDS = 6


def slugify(value: str, *, max_length: int = MAX_SLUG_LENGTH) -> str:
    words = value.strip().split()
    if len(words) > MAX_SLUG_WORDS:
        words = words[:MAX_SLUG_WORDS]
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", " ".join(words).lower())
    cleaned = cleaned.strip("_") or "my_series"
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip("_")
    return cleaned or "my_series"


def episode_folder_name(number: int) -> str:
    return f"episode_{number:02d}"


def yaml_quote(value: str) -> str:
    """Escape a string for use in double-quoted YAML values."""
    escaped = value.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))
    return chr(34) + escaped + chr(34)




def truncate(text: str, max_length: int = 280) -> str:
    """Collapse whitespace and trim to max_length characters."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 3].rstrip() + "..."


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


def load_story_context(series_dir: Path) -> str:
    """Load story context from story_context.md or the series bible."""
    context_path = series_dir / "story_context.md"
    if context_path.exists():
        text = context_path.read_text(encoding="utf-8").strip()
        if text:
            return text
    bible_path = series_dir / "series_bible.md"
    if bible_path.exists():
        bible = bible_path.read_text(encoding="utf-8")
        match = re.search(
            r"## Story Context \(authoring brief\)\s*\n\n(.*?)(?=\n## |\Z)",
            bible,
            re.DOTALL,
        )
        if match:
            excerpt = match.group(1).strip()
            if excerpt and excerpt != "{{STORY_CONTEXT}}":
                return excerpt
    return ""


def build_season_outline(series_title, logline, story_context, episode_count):
    context_block = story_context.strip() if story_context.strip() else "_Expand character bios, world rules, and arc notes in `story_context.md`._"
    lines = [f"# Season Outline — {series_title}", "", "## Logline", "", logline, "", "## Story Context", "", context_block, "", "## Episode Hooks", "", "One hook line per episode. Replace placeholders as you publish.", ""]
    for number in range(1, episode_count + 1):
        nxt = f"episode {number + 1:02d}" if number < episode_count else "the next season"
        lines += [f"### Episode {number:02d}", "", f"- **Hook:** Opening beat for episode {number}.", f"- **Cliffhanger:** Question that pulls viewers to {nxt}.", ""]
    return "\n".join(lines)


def build_story_context_file(series_title: str, logline: str, story_context: str, style_name: str) -> str:
    body = story_context.strip() or "_Describe characters, world rules, and season arc for AI assistants._"
    return f"""# Story Context — {series_title}

**Style:** {style_name}

**Logline:** {logline}

## Authoring Notes

{body}

## Characters

- **Name:**
- **Role:**
- **Want / flaw:**

## World Rules

1.
2.
3.

## Season Arc

- Act 1:
- Mid-season turn:
- Finale payoff:
"""


def build_ai_authoring_brief(series_title: str, logline: str, story_context: str, style_name: str, episode_count: int) -> str:
    context_block = story_context.strip() or "_No extended story description provided yet._"
    return f"""# AI Authoring Brief — {series_title}

Use this file with Claude, ChatGPT, or similar tools when drafting episodes.
Keep output aligned with `series_bible.md`, `story_context.md`, and `season_outline.md`.

## Series

- **Title:** {series_title}
- **Style template:** {style_name}
- **Planned episodes:** {episode_count}

## Logline

{logline}

## Story Context

{context_block}

## Episode Checklist

Each episode folder should contain:

- `script.md` — human-readable narration draft
- `voiceover_text.txt` — exact ElevenLabs narration (150–220 words)
- `voice_direction.md` — pacing and emotional beats
- `visual_prompts.md` — scene-by-scene visual notes
- `scenes.json` — timed scenes, prompts, cover config
- `upload_package.md` — platform captions and disclosures

## Continuity Rules

- First spoken line must hook within 3 seconds.
- End every episode on a specific cliffhanger question.
- Keep character appearance and props consistent across episodes.
- Mark all posts as fictional in upload copy.
"""


def build_episode_script(episode_number: int, series_title: str, logline: str, story_context: str) -> str:
    reminder = truncate(story_context, 400) if story_context.strip() else logline
    return f"""# Episode {episode_number:02d} Script

**Series:** {series_title}

**Logline:** {logline}

## Story Context Reminder

{reminder}

## Narration Script

Write the full narration script here (150–220 words target for 60–90 seconds).

Opening hook line...
"""


def build_episode_voice_direction(episode_number: int, series_title: str, logline: str, story_context: str, style_name: str) -> str:
    tone_hint = story_context.strip() or logline
    return f"""# Voice Direction — Episode {episode_number:02d}

**Series:** {series_title}
**Style:** {style_name}

## Narrator Tone

Calm, intimate, slightly urgent. Pause before cliffhangers.

## Story Beat Notes

{truncate(tone_hint, 320)}

## Pacing

- **0–3s:** Hook — deliver the impossible or emotional opening line cleanly.
- **3–20s:** Context — who, where, and why we care.
- **20–45s:** Escalation — choice, deadline, or reveal.
- **45–90s:** Cliffhanger — land on a specific question.

## Emphasis

- Mark words to stress with *italics* in this file only (not in voiceover_text.txt).
- Use line breaks in voiceover_text.txt to suggest pauses.
"""


def build_episode_visual_prompts(episode_number: int, series_title: str, logline: str, story_context: str, style: dict) -> str:
    visual_style = style.get("visual_style", "Match the series style template.")
    continuity = truncate(story_context, 400) if story_context.strip() else logline
    return f"""# Visual Prompts — Episode {episode_number:02d}

**Series:** {series_title}

## Series Visual Style

{visual_style}

## Continuity

{continuity}

## Scene Notes

### Scene 01 — Opening hook

- **Narration beat:** Opening hook line.
- **Visual:** One clear cinematic moment; vertical 9:16 composition.

### Scene 02 — Rising tension

- **Narration beat:** Context or escalation beat.
- **Visual:** Match subject, location, lighting, and mood to the narration.

### Scene 03 — Cliffhanger

- **Narration beat:** Final question or reveal.
- **Visual:** Emotionally readable subject; strong depth and mood.
"""


def build_voiceover_placeholder(episode_number: int, series_title: str, logline: str, story_context: str) -> str:
    seed = truncate(story_context, 200) if story_context.strip() else logline
    return (
        f"# Episode {episode_number:02d} — {series_title}\n"
        f"# Logline: {logline}\n"
        f"# Context: {seed}\n"
        "\n"
        "Write the exact narration text that ElevenLabs should speak.\n"
        "No markdown. Target 150–220 words. First line must hook immediately.\n"
        "\n"
        "Opening hook line...\n"
    )


def _build_scenes_json(episode_number: int, series_title: str, logline: str, story_context: str, style: dict[str, Any]):
    import json
    scenes = json.loads((ROOT / "templates" / "episode" / "scenes.template.json").read_text(encoding="utf-8"))
    scenes["episode_title"] = f"Episode {episode_number:02d} Title"
    scenes["output_slug"] = episode_folder_name(episode_number)
    scenes["style"] = style.get("visual_style", scenes["style"])
    continuity = story_context.strip() or logline
    scenes["continuity_notes"] = truncate(continuity, 500)
    scenes["cover"]["series_title"] = series_title
    scenes["cover"]["episode_number"] = episode_number
    cover = style.get("cover", {})
    scenes["cover"]["hook_lines"] = cover.get("hook_lines", scenes["cover"]["hook_lines"])
    scenes["cover"]["hook_highlight"] = cover.get("hook_highlight", scenes["cover"]["hook_highlight"])
    scenes["cover"]["background_prompt"] = cover.get("background_prompt", scenes["cover"].get("background_prompt", ""))
    hook_seed = truncate(logline, 120)
    if scenes.get("scenes"):
        scenes["scenes"][0]["caption"] = f"Opening hook tied to: {hook_seed}"
    return scenes


def make_asset_dirs(episode_dir: Path, created: list[Path] | None = None) -> None:
    for name in ASSET_SUBDIRS:
        directory = episode_dir / "assets" / name
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
            if created is not None:
                created.append(gitkeep)


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
    *,
    story_context: str = "",
    style_name: str = "",
) -> ScaffoldResult:
    """Create one episode folder from templates. Skips files that already exist."""
    episode_dir = series_dir / episode_folder_name(episode_number)
    created: list[Path] = []
    make_asset_dirs(episode_dir, created)

    scenes = _build_scenes_json(episode_number, series_title, logline, story_context, style)
    _write_if_missing(episode_dir / "scenes.json", json.dumps(scenes, indent=2) + "\n", created)

    _write_if_missing(
        episode_dir / "script.md",
        build_episode_script(episode_number, series_title, logline, story_context),
        created,
    )
    _write_if_missing(
        episode_dir / "voiceover_text.txt",
        build_voiceover_placeholder(episode_number, series_title, logline, story_context),
        created,
    )
    _write_if_missing(
        episode_dir / "voice_direction.md",
        build_episode_voice_direction(
            episode_number, series_title, logline, story_context, style_name or "thriller_mystery"
        ),
        created,
    )
    _write_if_missing(
        episode_dir / "visual_prompts.md",
        build_episode_visual_prompts(episode_number, series_title, logline, story_context, style),
        created,
    )
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
    story_context: str = "",
) -> ScaffoldResult:
    """Create the series-level files plus ``episode_count`` episode folders."""
    created: list[Path] = []
    series_dir.mkdir(parents=True, exist_ok=True)
    (series_dir / "notifications").mkdir(parents=True, exist_ok=True)
    keep = series_dir / "notifications" / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
        created.append(keep)

    context_for_files = story_context.strip() or logline
    replacements = {
        "SERIES_TITLE": series_title,
        "LOGLINE": logline,
        "GENRE": style.get("genre", style_name),
        "STORY_CONTEXT": context_for_files,
    }
    _write_if_missing(
        series_dir / "series_config.yaml",
        render_template(ROOT / "templates" / "series" / "series_config.template.yaml", replacements),
        created,
    )
    _write_if_missing(
        series_dir / "series_bible.md",
        render_template(ROOT / "templates" / "series" / "series_bible.template.md", replacements),
        created,
    )
    _write_if_missing(
        series_dir / "season_outline.md",
        build_season_outline(series_title, logline, story_context, episode_count),
        created,
    )
    _write_if_missing(
        series_dir / "story_context.md",
        build_story_context_file(series_title, logline, story_context, style_name),
        created,
    )
    _write_if_missing(
        series_dir / "ai_authoring_brief.md",
        build_ai_authoring_brief(series_title, logline, story_context, style_name, episode_count),
        created,
    )

    config_path = series_dir / "series_config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    if "style_template:" in config_text:
        config_text = re.sub(r"style_template:\s*\S+", f"style_template: {style_name}", config_text)
        config_text = config_text.replace('title: "Your Series Title"', f"title: {yaml_quote(series_title)}")
        config_text = config_text.replace(
            'logline: "One sentence describing the core premise."',
            f"logline: {yaml_quote(logline)}",
        )
        config_path.write_text(config_text, encoding="utf-8")

    for number in range(1, episode_count + 1):
        result = create_episode(
            series_dir,
            number,
            series_title,
            logline,
            style,
            story_context=story_context,
            style_name=style_name,
        )
        created.extend(result.created_files)

    return ScaffoldResult(series_dir, tuple(created))
