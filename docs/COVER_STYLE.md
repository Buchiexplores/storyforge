# Cover Style Guide

Every episode cover should look like a new poster from the same series, not a
one-off thumbnail template. Storyforge ships **26 cover design styles** in
`config/cover_styles.yaml`. The image model generates only the cinematic background;
typography, badges, hooks, grades, and effects are composed locally in
`tools/cover_styles.py` (used by `generate_episode_assets.py` and `regenerate_cover.py`).

## How style is chosen

Resolution order (first match wins):

1. `scenes.json` → `cover.design_style` (per-episode)
2. `series_config.yaml` → `cover.default_design_style` (series override)
3. Style template → `cover.default_design_style` in `config/style_templates/<template>.yaml`
4. `config/cover_styles.yaml` → `default_for_template` for the series `style_template`

List styles for your template:

```bash
python3 tools/generate_episode_assets.py --list-cover-styles
python3 tools/regenerate_cover.py --series series/my_series --episode episode_01 --list-styles
```

## Per-episode editable values (`scenes.json` → `cover`)

| Field | Purpose |
|-------|---------|
| `design_style` | Style id from `cover_styles.yaml` (e.g. `thriller_neon_rain`, `horror_frost`) |
| `series_title` | Stacked series title at top |
| `episode_number` | Episode badge |
| `part_number` | Part label |
| `hook_lines` / `hook_highlight` | Left callout (style controls layout: handwritten, block, or none) |
| `title_lines` | Bottom episode title (distressed / brush accent per style) |
| `background_prompt` | Scene-specific background plate (no text in image) |

## Style catalog

Each style defines: `grade`, `series_layout`, `title_layout`, `badge_style`, `hook_style`,
`colors` (hex), and `effects` (`rain`, `glitch`, `scratch`). Templates map to defaults:

| Style template | Default style |
|----------------|---------------|
| `thriller_mystery` | `thriller_neon_rain` |
| `horror` | `horror_frost` |
| `noir` | `noir_classic` |
| `action` | `action_fire` |
| `sci_fi` | `sci_fi_cyan` |
| `cyberpunk` | `cyberpunk_magenta` |
| `fantasy` | `fantasy_gold` |
| `anime` | `anime_pop` |
| `romance_drama` | `romance_soft` |
| `comedy` | `comedy_bright` |
| `western` | `western_dust` |
| `period_drama` | `period_drama_ivory` |

Additional styles (e.g. `thriller_cold_case`, `cross_neon_noir`) are available when
`style_templates` on the style entry includes your series template. See
`config/cover_styles.yaml` for the full list.

## Regenerating covers

```bash
# Interactive style picker (TTY) + full regen
python3 tools/regenerate_cover.py --series series/my_series --episode episode_01

# Explicit style, compose only (reuse existing base PNG)
python3 tools/regenerate_cover.py --series series/my_series --episode episode_01 \
  --style horror_frost --compose-only

# New background + compose; persist style to scenes.json
python3 tools/regenerate_cover.py --series series/my_series --episode episode_01 \
  --style sci_fi_cyan --force-background --save-style

# Pipeline flags
python3 tools/generate_episode_assets.py --cover --cover-style noir_gold
```

Background providers: `--cover-provider openai|fal|local` or `--openai-cover`.

## Customizing for your series

1. Set `default_design_style` under `cover` in your style template or `series_config.yaml`.
2. Edit per-episode `background_prompt` and `design_style` in `scenes.json`.
3. See `docs/STORY_AUTHORING.md` for the full authoring workflow.
