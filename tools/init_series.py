#!/usr/bin/env python3
"""Scaffold a new fiction series from templates.

Two ways to run it:

  Interactive wizard (recommended for first-timers) — just run with no flags:
      python3 tools/init_series.py

  Non-interactive (scriptable / CI) — pass everything as flags:
      python3 tools/init_series.py --name "The Last Signal" --style sci_fi --episodes 5 --auto-author
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline_config import ROOT, load_style_template
from scaffold import STYLE_CHOICES, ScaffoldResult, create_series, slugify

MAX_SERIES_TITLE_CHARS = 80
MAX_SERIES_TITLE_WORDS = 10


def print_section(title: str) -> None:
    width = max(len(title) + 4, 50)
    print()
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│ {title:<{width - 4}} │")
    print("└" + "─" * (width - 2) + "┘")


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def validate_title(title: str) -> str | None:
    stripped = title.strip()
    if not stripped:
        return "A title is required."
    if len(stripped) > MAX_SERIES_TITLE_CHARS:
        return (
            f"Title must be at most {MAX_SERIES_TITLE_CHARS} characters "
            f"(got {len(stripped)})."
        )
    word_count = len(stripped.split())
    if word_count > MAX_SERIES_TITLE_WORDS:
        return (
            f"Title must be at most {MAX_SERIES_TITLE_WORDS} words "
            f"(got {word_count})."
        )
    return None


def prompt(question: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{question}{suffix}: ").strip()
    return answer or (default or "")


def prompt_multiline(intro: str, default: str | None = None) -> str:
    print(intro)
    print("  (Paste paragraphs freely. Press Enter on a blank line when done.)")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            if lines:
                break
            if default:
                return default
            continue
        lines.append(line)
    return "\n".join(lines).strip() or (default or "")


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


def print_plan(
    *,
    name: str,
    style: str,
    episodes: int,
    logline: str,
    story_context: str,
    series_rel: str,
) -> None:
    print_section("Plan summary")
    print(f"  Title:               {name}")
    print(f"  Style:               {style}")
    print(f"  Episodes:            {episodes}")
    print(f"  Logline:             {logline}")
    context_preview = story_context.replace("\n", " ")
    if len(context_preview) > 72:
        context_preview = context_preview[:69] + "..."
    print(f"  Story context:       {context_preview or '(none)'}")
    print(f"  Folder:              {series_rel}/")
    print(f"  PIPELINE_SERIES_DIR: {series_rel}")


def confirm_create() -> bool:
    answer = input("\nCreate this series? [Y/n]: ").strip().lower()
    return answer in {"", "y", "yes"}


def run_wizard() -> argparse.Namespace | None:
    print("=" * 60)
    print("  Storyforge — new series wizard")
    print("=" * 60)

    print_section("Step 1 of 6 — Series title")
    print(
        f"  Enter a short title only (max {MAX_SERIES_TITLE_CHARS} chars, "
        f"{MAX_SERIES_TITLE_WORDS} words)."
    )
    print("  Long story notes belong in Step 5 — they will NOT become the folder name.")
    name = ""
    while True:
        name = prompt("Series title (e.g. The Last Signal)").strip()
        error = validate_title(name)
        if error:
            print(f"  {error}")
            continue
        break

    print_section("Step 2 of 6 — Visual style")
    style = choose_style()

    print_section("Step 3 of 6 — Episode count")
    episodes = prompt_int("How many episode folders to scaffold", 5)

    print_section("Step 4 of 6 — Logline")
    print("  One sentence that captures the core premise.")
    logline = prompt(
        "Logline",
        "Describe your series premise in one sentence.",
    )

    print_section("Step 5 of 6 — Story description for AI")
    print("  Saved to story_context.md and ai_authoring_brief.md.")
    print("  Paste character notes, world rules, or season arc details.")
    story_context = prompt_multiline(
        "\nStory description for AI assistants:",
        "",
    )

    print_section("Step 6 of 6 — Folder location")
    slug = slugify(name)
    default_series_rel = f"series/{slug}"
    print(f"  Folder slug (from title): {slug}")
    print(f"  Default path:             {default_series_rel}/")
    output_dir = prompt("Parent folder", "series")
    slug = slugify(prompt("Folder slug (override)", slug) or slug)
    series_rel = f"{output_dir}/{slug}"

    print_plan(
        name=name,
        style=style,
        episodes=episodes,
        logline=logline,
        story_context=story_context,
        series_rel=series_rel,
    )
    if not confirm_create():
        print("\nCancelled — no series created.")
        return None

    return argparse.Namespace(
        name=name,
        style=style,
        episodes=episodes,
        logline=logline,
        story_context=story_context,
        output_dir=output_dir,
        slug=slug,
        set_active=None,
    )


def print_review_links(result: ScaffoldResult, series_rel: str) -> None:
    print("\n" + "-" * 60)
    print("Review your generated templates (open these to author content):")
    print("-" * 60)
    for path in result.created_files:
        if path.exists():
            print(f"  {rel_path(path)}")
            print(f"    {path.as_uri()}")


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
    print(f"\n✓ Updated .env.story.local → PIPELINE_SERIES_DIR={series_rel}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a new fiction series folder.")
    parser.add_argument("--name", help="Human-readable series title. Omit to launch the wizard.")
    parser.add_argument("--style", default="thriller_mystery", choices=STYLE_CHOICES)
    parser.add_argument("--episodes", type=int, default=1, help="Number of episode folders to create.")
    parser.add_argument("--logline", default="Describe your series premise in one sentence.")
    parser.add_argument(
        "--story-context",
        default="",
        help="Extended story description for AI assistants (characters, world, arc).",
    )
    parser.add_argument("--output-dir", default="series", help="Parent directory under the repo root.")
    parser.add_argument("--slug", help="Optional folder slug. Defaults to a slugified --name.")
    parser.add_argument(
        "--set-active",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write PIPELINE_SERIES_DIR into .env.story.local (default: ask).",
    )
    parser.add_argument(
        "--auto-author",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run OpenAI author_series after scaffold (default: ask when interactive).",
    )
    args = parser.parse_args()

    auto_author_pref = getattr(args, "auto_author", None)
    if not args.name:
        if not sys.stdin.isatty():
            parser.error("--name is required when not running interactively.")
        wizard_args = run_wizard()
        if wizard_args is None:
            return 1
        args = wizard_args
        args.auto_author = auto_author_pref
    else:
        title_error = validate_title(args.name)
        if title_error:
            parser.error(title_error)
        args.slug = slugify(args.slug or args.name)

    style = load_style_template(args.style)
    if not style:
        raise SystemExit(f"Unknown or missing style template: {args.style}")

    slug = args.slug or slugify(args.name)
    series_dir = (ROOT / args.output_dir / slug).resolve()
    if series_dir.exists() and any(series_dir.iterdir()):
        raise SystemExit(f"Series directory already exists and is not empty: {series_dir}")

    episode_count = max(1, int(args.episodes))
    story_context = getattr(args, "story_context", "") or ""
    result = create_series(
        series_dir=series_dir,
        series_title=args.name,
        logline=args.logline,
        style_name=args.style,
        style=style,
        episode_count=episode_count,
        story_context=story_context,
    )

    series_rel = f"{args.output_dir}/{slug}"
    print(f"\n✓ Series scaffold created at: {series_rel}/")
    print(f"✓ Episodes scaffolded: {episode_count}")
    print_review_links(result, series_rel)
    maybe_set_active_series(series_rel, getattr(args, "set_active", None))

    auto_author = getattr(args, "auto_author", None)
    if auto_author is None:
        if sys.stdin.isatty():
            auto_author = (
                input("\nAuto-author all episodes with OpenAI now? [y/N]: ").strip().lower()
                in {"y", "yes"}
            )
        else:
            auto_author = False
    if auto_author:
        from author_series import author_series

        code = author_series(series_dir)
        if code != 0:
            return code

    print("\nNext steps:")
    print("  1. Add your API keys to .env.story.local (see docs/API_KEYS.md)")
    print(f"  2. Auto-author episodes (optional): python3 tools/author_series.py --series {series_rel}")
    print(f"     Or hand-author episode_01 in {series_rel}/episode_01/")
    print(f"  3. Render it: python3 tools/run_episode_pipeline.py --series {series_rel} --episode episode_01")
    print(f"  4. Add the next episode: python3 tools/new_episode.py --series {series_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
