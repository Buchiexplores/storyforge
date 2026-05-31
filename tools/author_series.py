#!/usr/bin/env python3
"""OpenAI auto-authoring for scaffolded series episodes."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from pipeline_config import (
    ROOT,
    ENV_PATH,
    get_series_dir,
    load_local_env,
    load_series_config,
    merged_series_settings,
)
from scaffold import episode_folder_name, load_story_context, render_template

STATE_FILENAME = "authoring_state.json"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing {name}. Add it to {ENV_PATH}")
    return value


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def list_episode_dirs(series_dir: Path) -> list[tuple[int, Path]]:
    episodes: list[tuple[int, Path]] = []
    for child in series_dir.iterdir():
        if not child.is_dir():
            continue
        match = re.fullmatch(r"episode_(\d+)", child.name)
        if match:
            episodes.append((int(match.group(1)), child))
    episodes.sort(key=lambda item: item[0])
    return episodes


def load_authoring_state(series_dir: Path) -> dict[str, Any]:
    path = series_dir / STATE_FILENAME
    if not path.exists():
        return {"characters": [], "world_rules": [], "episodes": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Expected object in {path}")
    data.setdefault("characters", [])
    data.setdefault("world_rules", [])
    data.setdefault("episodes", {})
    return data


def save_authoring_state(series_dir: Path, state: dict[str, Any]) -> None:
    path = series_dir / STATE_FILENAME
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def series_metadata(series_dir: Path, config: dict[str, Any]) -> tuple[str, str]:
    block = config.get("series") if isinstance(config.get("series"), dict) else {}
    title = (block or {}).get("title") or series_dir.name.replace("_", " ").title()
    logline = (block or {}).get("logline") or ""
    return str(title).strip(), str(logline).strip()


def voiceover_plain_text(path: Path) -> str:
    if not path.exists():
        return ""
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def episode_is_placeholder(episode_dir: Path) -> bool:
    voice_path = episode_dir / "voiceover_text.txt"
    voice = voiceover_plain_text(voice_path)
    if word_count(voice) < 80:
        return True
    placeholder_markers = (
        "Write the exact narration",
        "Opening hook line",
        "TITLE TBD",
    )
    for marker in placeholder_markers:
        if marker in voice:
            return True
    script_path = episode_dir / "script.md"
    if script_path.exists():
        script = script_path.read_text(encoding="utf-8")
        for marker in placeholder_markers:
            if marker in script:
                return True
    scenes_path = episode_dir / "scenes.json"
    if scenes_path.exists():
        try:
            scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
            title = str(scenes.get("episode_title", ""))
            if "TITLE TBD" in title or re.search(r"Episode \d+ Title", title):
                return True
        except json.JSONDecodeError:
            return True
    return False


def bible_needs_enrichment(bible_text: str) -> bool:
    if re.search(r"-\s*\*\*Name:\*\*\s*$", bible_text, re.MULTILINE):
        return True
    if "{{SERIES_TITLE}}" in bible_text or "{{LOGLINE}}" in bible_text:
        return True
    return False

def parse_world_rules_from_bible(bible_text: str) -> list[str]:
    """Extract numbered world rules from the ## World Rules section."""
    match = re.search(
        r"## World Rules\s*\n+(.*?)(?=\n## |\Z)",
        bible_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return []
    rules: list[str] = []
    for line in match.group(1).splitlines():
        line = line.strip()
        numbered = re.match(r"\d+\.\s*(.*)", line)
        if not numbered:
            continue
        rule = numbered.group(1).strip()
        if rule:
            rules.append(rule)
    return rules


def openai_client(timeout: float):
    require_env("OPENAI_API_KEY")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "Missing openai package. Run: python3 -m pip install --user openai"
        ) from exc
    return OpenAI(timeout=timeout)


def chat_json(client, model: str, system: str, user: str) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("OpenAI response was not a JSON object")
    return data


def enrich_series_bible(
    client,
    model: str,
    series_title: str,
    logline: str,
    story_context: str,
    bible_text: str,
) -> str:
    system = (
        "You enrich series bibles for serialized vertical short-form fiction. "
        "Respond with JSON only."
    )
    user = f"""Fill in the Main Character and World Rules sections of this series bible using the story context.
Keep existing headings and markdown structure. Return JSON with key "series_bible_md" containing the full updated bible markdown.

Series title: {series_title}
Logline: {logline}

Story context:
{story_context}

Current bible:
{bible_text}
"""
    data = chat_json(client, model, system, user)
    updated = data.get("series_bible_md")
    if not isinstance(updated, str) or not updated.strip():
        raise ValueError("Bible enrichment response missing series_bible_md")
    return updated.strip() + "\n"


def build_episode_prompt(
    *,
    series_title: str,
    logline: str,
    story_context: str,
    season_outline: str,
    series_bible: str,
    style: dict[str, Any],
    episode_number: int,
    total_episodes: int,
    state: dict[str, Any],
    prior_summaries: list[str],
) -> tuple[str, str]:
    visual_style = style.get("visual_style") or style.get("style") or "Cinematic vertical 9:16 fiction."
    narrator = ""
    voice_cfg = style.get("voice")
    if isinstance(voice_cfg, dict):
        narrator = voice_cfg.get("narrator_notes") or ""
    is_finale = episode_number >= total_episodes
    system = """You write serialized vertical short-form fiction episodes for a video pipeline.
Output valid JSON only with these keys:
episode_title, episode_summary, cliffhanger, key_events (array of strings),
voiceover_text (150-220 words, plain text, no markdown),
script_md (markdown narration script),
voice_direction_md (markdown pacing and emphasis notes),
visual_prompts_md (markdown scene visual notes),
continuity_notes (string),
characters (array of {name, description}),
cover ({hook_lines, hook_highlight, title_lines, background_prompt}),
scenes (array of 15-20 items: {id, duration, caption, prompt}),
upload ({hook_line, youtube_title, cliffhanger_tease}).

Rules:
- 60-90 second episode; scene durations should sum roughly 60-90 seconds.
- Captions must align with narration beats.
- Image prompts: vertical cinematic, no logos, no public figures, no readable real brand names.
- Maintain character names and descriptions across episodes.
- First spoken line must hook within 3 seconds.
- End on a cliffhanger question unless this is the season finale (then tease next season).
- Mark clearly fictional tone in upload copy."""
    prior_block = "\n".join(prior_summaries) if prior_summaries else "(none yet)"
    user = f"""Author episode {episode_number:02d} of {total_episodes} for "{series_title}".

Logline: {logline}
Visual style: {visual_style}
Narrator notes: {narrator or "Calm, intimate, slightly urgent."}
Season finale: {is_finale}

Story context:
{story_context}

Series bible excerpt:
{series_bible[:6000]}

Season outline excerpt:
{season_outline[:4000]}

Authoring state (characters, world rules, prior episode metadata):
{json.dumps(state, indent=2)[:8000]}

Previous episode summaries:
{prior_block}

Write episode {episode_number:02d} with strong continuity from prior episodes."""
    return system, user


def write_upload_package_md(
    episode_number: int,
    series_title: str,
    logline: str,
    style: dict[str, Any],
    upload: dict[str, Any],
) -> str:
    hook = upload.get("hook_line") or "Opening hook line for social captions."
    youtube_title = upload.get("youtube_title") or f"{series_title} | Episode {episode_number}"
    tease = upload.get("cliffhanger_tease") or "Tease the next episode here."
    platforms = style.get("platforms", {}) if isinstance(style.get("platforms"), dict) else {}
    return render_template(
        ROOT / "templates" / "episode" / "upload_package.template.md",
        {
            "EPISODE_NUMBER": str(episode_number),
            "SERIES_TITLE": series_title,
            "SERIES_LOGLINE": logline,
            "HOOK_LINE": hook,
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
            "YOUTUBE_TITLE": youtube_title,
            "CLIFFHANGER_TEASE": tease,
            "OUTPUT_SLUG": episode_folder_name(episode_number),
        },
    )


def merge_scenes_json(
    episode_dir: Path,
    episode_number: int,
    series_title: str,
    style: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing: dict[str, Any] = {}
    scenes_path = episode_dir / "scenes.json"
    if scenes_path.exists():
        try:
            existing = json.loads(scenes_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    merged: dict[str, Any] = dict(existing)
    merged["episode_title"] = payload.get("episode_title") or merged.get("episode_title")
    merged["output_slug"] = episode_folder_name(episode_number)
    merged["style"] = style.get("visual_style") or merged.get("style") or ""
    merged["continuity_notes"] = payload.get("continuity_notes") or merged.get("continuity_notes", "")
    if payload.get("characters"):
        merged["characters"] = payload["characters"]
    cover = dict(merged.get("cover") or {})
    gen_cover = payload.get("cover") if isinstance(payload.get("cover"), dict) else {}
    cover["series_title"] = series_title
    cover["episode_number"] = episode_number
    for key in ("hook_lines", "hook_highlight", "title_lines", "background_prompt"):
        if key in gen_cover:
            cover[key] = gen_cover[key]
    merged["cover"] = cover
    if payload.get("scenes"):
        merged["scenes"] = payload["scenes"]
    if "resolution" not in merged:
        merged["resolution"] = {"width": 1080, "height": 1920, "fps": 30}
    return merged


def update_season_outline_hook(
    series_dir: Path,
    episode_number: int,
    hook: str,
    cliffhanger: str,
) -> None:
    path = series_dir / "season_outline.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    section_header = f"### Episode {episode_number:02d}"
    pattern = re.compile(
        rf"({re.escape(section_header)}.*?)(-\s\*\*Hook:\*\*).*?(?=\n-\s\*\*Cliffhanger:\*\*)",
        re.DOTALL,
    )
    if pattern.search(text):
        text = pattern.sub(rf"\1\2 {hook.strip()}", text, count=1)
    cliff_pattern = re.compile(
        rf"({re.escape(section_header)}.*?-\s\*\*Cliffhanger:\*\*).*?(?=\n### |\Z)",
        re.DOTALL,
    )
    if cliff_pattern.search(text):
        text = cliff_pattern.sub(rf"\1 {cliffhanger.strip()}", text, count=1)
    path.write_text(text, encoding="utf-8")


def merge_characters(state: dict[str, Any], new_chars: list[Any]) -> None:
    if not new_chars:
        return
    by_name = {
        c.get("name"): c
        for c in state.get("characters", [])
        if isinstance(c, dict) and c.get("name")
    }
    for item in new_chars:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue
        prior = by_name.get(name, {})
        by_name[name] = {
            "name": name,
            "description": item.get("description") or prior.get("description", ""),
        }
    state["characters"] = list(by_name.values())


def author_episode(
    *,
    client,
    model: str,
    series_dir: Path,
    episode_number: int,
    episode_dir: Path,
    total_episodes: int,
    series_title: str,
    logline: str,
    story_context: str,
    season_outline: str,
    series_bible: str,
    style: dict[str, Any],
    state: dict[str, Any],
    prior_summaries: list[str],
    force: bool,
) -> tuple[bool, list[Path]]:
    if not force and not episode_is_placeholder(episode_dir):
        print(f"  Skipping {episode_dir.name} (already authored; use --force to regenerate)")
        return True, []

    system, user = build_episode_prompt(
        series_title=series_title,
        logline=logline,
        story_context=story_context,
        season_outline=season_outline,
        series_bible=series_bible,
        style=style,
        episode_number=episode_number,
        total_episodes=total_episodes,
        state=state,
        prior_summaries=prior_summaries,
    )
    try:
        payload = chat_json(client, model, system, user)
    except Exception as exc:
        print(f"  ✗ OpenAI failed for {episode_dir.name}: {exc}")
        return False, []

    voiceover = str(payload.get("voiceover_text") or "").strip()
    wc = word_count(voiceover)
    if wc < 130 or wc > 240:
        print(f"  ⚠ voiceover word count {wc} outside 130-240 (writing anyway)")

    written: list[Path] = []
    script_md = payload.get("script_md") or f"# Episode {episode_number:02d}\n\n{voiceover}"
    (episode_dir / "script.md").write_text(str(script_md).strip() + "\n", encoding="utf-8")
    written.append(episode_dir / "script.md")

    (episode_dir / "voiceover_text.txt").write_text(voiceover + "\n", encoding="utf-8")
    written.append(episode_dir / "voiceover_text.txt")

    for name, key in (
        ("voice_direction.md", "voice_direction_md"),
        ("visual_prompts.md", "visual_prompts_md"),
    ):
        content = str(payload.get(key) or f"# {name}\n\n(TBD)\n")
        path = episode_dir / name
        path.write_text(content.strip() + "\n", encoding="utf-8")
        written.append(path)

    upload = payload.get("upload") if isinstance(payload.get("upload"), dict) else {}
    upload_md = write_upload_package_md(episode_number, series_title, logline, style, upload)
    (episode_dir / "upload_package.md").write_text(upload_md, encoding="utf-8")
    written.append(episode_dir / "upload_package.md")

    scenes = merge_scenes_json(episode_dir, episode_number, series_title, style, payload)
    scenes_path = episode_dir / "scenes.json"
    scenes_path.write_text(json.dumps(scenes, indent=2) + "\n", encoding="utf-8")
    written.append(scenes_path)

    ep_key = f"{episode_number:02d}"
    state["episodes"][ep_key] = {
        "title": payload.get("episode_title") or scenes.get("episode_title"),
        "summary": payload.get("episode_summary") or "",
        "cliffhanger": payload.get("cliffhanger") or "",
        "key_events": payload.get("key_events")
        if isinstance(payload.get("key_events"), list)
        else [],
    }
    merge_characters(state, payload.get("characters") or scenes.get("characters") or [])

    hook = str(
        upload.get("hook_line")
        or payload.get("episode_summary")
        or payload.get("episode_title")
        or ""
    ).strip()
    cliff = str(payload.get("cliffhanger") or upload.get("cliffhanger_tease") or "").strip()
    if hook and cliff:
        update_season_outline_hook(series_dir, episode_number, hook, cliff)

    save_authoring_state(series_dir, state)
    return True, written


def author_series(
    series_dir: Path,
    *,
    from_episode: int = 1,
    to_episode: int | None = None,
    force: bool = False,
    model: str | None = None,
) -> int:
    load_local_env()
    series_dir = series_dir.resolve()
    if not series_dir.is_dir():
        raise SystemExit(f"Series directory not found: {series_dir}")

    model = model or os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    timeout = float(os.getenv("OPENAI_TEXT_TIMEOUT_SECONDS", "180"))
    client = openai_client(timeout)

    config = load_series_config(series_dir)
    style = merged_series_settings(series_dir)
    series_title, logline = series_metadata(series_dir, config)
    story_context = load_story_context(series_dir)
    season_outline_path = series_dir / "season_outline.md"
    season_outline = (
        season_outline_path.read_text(encoding="utf-8") if season_outline_path.exists() else ""
    )
    bible_path = series_dir / "series_bible.md"
    series_bible = bible_path.read_text(encoding="utf-8") if bible_path.exists() else ""

    if bible_path.exists() and bible_needs_enrichment(series_bible):
        print("Enriching series_bible.md from story context...")
        try:
            series_bible = enrich_series_bible(
                client,
                model,
                series_title,
                logline,
                story_context,
                series_bible,
            )
            bible_path.write_text(series_bible, encoding="utf-8")
            print(f"  ✓ Updated {rel_path(bible_path)}")
            enrich_state = load_authoring_state(series_dir)
            world_rules = parse_world_rules_from_bible(series_bible)
            if world_rules:
                enrich_state["world_rules"] = world_rules
                save_authoring_state(series_dir, enrich_state)
        except Exception as exc:
            print(f"  ⚠ Bible enrichment skipped: {exc}")

    episodes = list_episode_dirs(series_dir)
    if not episodes:
        raise SystemExit(f"No episode_XX folders found under {series_dir}")

    numbers = [num for num, _ in episodes]
    max_ep = max(numbers)
    start = max(1, int(from_episode))
    end = int(to_episode) if to_episode is not None else max_ep
    selected = [(num, path) for num, path in episodes if start <= num <= end]
    if not selected:
        raise SystemExit(f"No episodes in range {start}-{end}")

    state = load_authoring_state(series_dir)
    total_episodes = max(numbers)
    failures = 0
    prior_summaries: list[str] = []

    for ep_num in range(1, start):
        ep_meta = state.get("episodes", {}).get(f"{ep_num:02d}")
        if ep_meta and ep_meta.get("summary"):
            prior_summaries.append(f"Episode {ep_num:02d}: {ep_meta['summary']}")

    print(f"Authoring {len(selected)} episode(s) sequentially with {model}...")
    for episode_number, episode_dir in selected:
        print(f"\n→ {episode_dir.name}")
        ok, paths = author_episode(
            client=client,
            model=model,
            series_dir=series_dir,
            episode_number=episode_number,
            episode_dir=episode_dir,
            total_episodes=total_episodes,
            series_title=series_title,
            logline=logline,
            story_context=story_context,
            season_outline=season_outline,
            series_bible=series_bible,
            style=style,
            state=state,
            prior_summaries=prior_summaries,
            force=force,
        )
        if not ok:
            failures += 1
            continue
        for path in paths:
            print(f"  ✓ {rel_path(path)}")
            print(f"    {file_uri(path)}")
        ep_meta = state.get("episodes", {}).get(f"{episode_number:02d}")
        if ep_meta and ep_meta.get("summary"):
            prior_summaries.append(f"Episode {episode_number:02d}: {ep_meta['summary']}")
        if season_outline_path.exists():
            season_outline = season_outline_path.read_text(encoding="utf-8")

    if failures:
        print(f"\nFinished with {failures} failure(s).")
        return 1
    print("\n✓ Auto-authoring complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-author scaffolded episodes with OpenAI.")
    parser.add_argument("--series", help="Series directory (e.g. series/my_slug).")
    parser.add_argument(
        "--from",
        dest="from_episode",
        type=int,
        default=1,
        help="First episode number.",
    )
    parser.add_argument(
        "--to",
        dest="to_episode",
        type=int,
        default=None,
        help="Last episode number.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if files look authored.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="OpenAI chat model (default: OPENAI_TEXT_MODEL).",
    )
    args = parser.parse_args()

    load_local_env()
    series_dir = get_series_dir(args.series) if args.series else get_series_dir()
    return author_series(
        series_dir,
        from_episode=args.from_episode,
        to_episode=args.to_episode,
        force=args.force,
        model=args.model,
    )


if __name__ == "__main__":
    raise SystemExit(main())
