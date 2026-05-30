# Cover Style Guide

Every episode cover should look like a new poster from the same series, not a
one-off thumbnail template.

## Required visual language

- Vertical 9:16 thriller poster, dark rainy background, wet reflections, amber doorway light, neon accent glow.
- Huge stacked title at the top: white condensed words plus one neon green glitch word.
- Handwritten warning callout on the left with one green emphasis word and a white arrow.
- Red episode badge above the episode title.
- Distressed white episode title with a green brush-style final line.
- Green outlined part label near the bottom.
- Background composition should preserve depth: ominous doorway and story figure in the middle, cracked glowing phone or key prop large in the wet foreground, clean dark space behind the top title.
- Do not ask the image model to render cover text. The generated image is only the cinematic scene plate; all words, badges, arrow, glitch, rain, and distress effects are added by the compositor.

The image model generates only the cinematic background. Typography is composed locally in `tools/generate_episode_assets.py` so titles stay readable and consistent.

## Per-episode editable values

These live in each episode's `scenes.json` under `cover`:

- `series_title`
- `episode_number`
- `part_number`
- `hook_lines`
- `hook_highlight`
- `title_lines`
- `background_prompt` (optional scene-specific background plate)

## Customizing for your series

1. Edit `background_prompt` in each episode's `scenes.json`.
2. Override cover defaults in your `series_config.yaml` or style template under `config/style_templates/`.
3. See `docs/STORY_AUTHORING.md` for the full authoring workflow.
