# Story Authoring Guide

How to write episodes, define visual style, and configure the pipeline for any fiction genre.

## The authoring workflow

```text
1. Define your series (bible + style template)
2. Plan episode hooks and cliffhangers
3. Write script.md and voiceover_text.txt
4. Build scenes.json with timed scenes and image prompts
5. Run the pipeline
6. Review exports and fill upload_package.md
7. Publish to TikTok → YouTube Shorts → Instagram Reels
```

## Step 1: Series bible

Run `init_series.py` (interactive wizard or flags) to scaffold a full series. It creates:

**Series level:** `series_config.yaml`, `series_bible.md`, `story_context.md`, `season_outline.md`, `ai_authoring_brief.md`

**Per episode:** `script.md`, `voiceover_text.txt`, `voice_direction.md`, `visual_prompts.md`, `scenes.json`, `upload_package.md` (pre-filled placeholders)

Or copy `templates/series/series_bible.template.md` manually.

Your series bible should define:

- **Logline** — one sentence premise
- **Main character** — want, flaw, visual description
- **World rules** — what must stay consistent
- **Tone** — how it should feel
- **Episode structure** — hook → context → escalation → cliffhanger

The example bible is at `examples/phone_from_tomorrow/series_bible.md`.

## Step 2: Choose a style template

Style templates live in `config/style_templates/`. Each template provides:

- `visual_style` — injected into every image prompt
- `image_prompt_rules` — beat-matching and composition rules
- `cover` defaults — hook lines and background prompt
- `platforms` — disclosure text and hashtag suggestions

Reference in `series_config.yaml`:

```yaml
style_template: thriller_mystery
```

Override any field in `series_config.yaml`:

```yaml
visual_style: "your custom visual style string"
image_prompt_rules: |
  Your custom rules for image generation.
```

## Step 3: Write the narration

### script.md

Human-readable script with stage directions. Use this for your own editing and AI writing workflows.

### voiceover_text.txt

**Exact text** sent to ElevenLabs. Rules:

- No markdown formatting
- No scene headings
- Write how you want it spoken, including pauses (use `...` or line breaks)
- Target **150–220 words** for a 60–90 second episode
- First line must hook immediately — viewers decide in 3 seconds

Example opening:

```text
At 2:13 AM, Maya's phone buzzed under her pillow.
The message came from her own number.
Do not open the door.
```

## Step 4: Build scenes.json

Copy `templates/episode/scenes.template.json` as your starting point.

### Resolution (keep default unless you have a reason to change)

```json
"resolution": { "width": 1080, "height": 1920, "fps": 30 }
```

This matches TikTok, Instagram Reels, and YouTube Shorts vertical specs.

### Style string

```json
"style": "cinematic mystery thriller, modern city at night, wet asphalt, amber streetlights, moody contrast, no logos"
```

Be specific about lighting, palette, and mood. This string is appended to every scene image prompt.

### Continuity

```json
"continuity_notes": "Alex is a 28-year-old paramedic with short dark hair, navy jacket, and a cracked phone with blue glow.",
"characters": [
  { "name": "Alex", "description": "28, paramedic, navy jacket, tired eyes, cracked blue-glowing phone" }
]
```

Strong continuity notes dramatically improve visual consistency across scenes and episodes.

### Scenes array

Each scene needs:

| Field | Description |
|-------|-------------|
| `id` | Unique slug, used for filenames (e.g. `01_phone_buzzes`) |
| `duration` | Seconds this scene stays on screen |
| `caption` | On-screen caption text (should match narration beat) |
| `prompt` | Image generation direction — be specific |

**Prompt tips:**

- Describe subject, location, lighting, camera angle, and mood
- Match the exact narration beat — do not describe future scenes
- Say "no logos, no readable brand names, no public figures"
- For phone-screen text, explicitly request the exact text to show

**Timing tips:**

- Total scene durations should roughly match voiceover length
- The renderer syncs captions to scene timing
- Aim for 15–25 scenes per 60–90 second episode
- Change visuals every 2–4 seconds to maintain retention

### Cover configuration

```json
"cover": {
  "design_style": "thriller_neon_rain",
  "series_title": "Your Series Title",
  "episode_number": 1,
  "part_number": 1,
  "hook_lines": ["DON'T", "OPEN", "IT"],
  "hook_highlight": "OPEN",
  "title_lines": ["THE DOOR", "IS LOCKED"],
  "background_prompt": "dark rainy hallway, glowing phone in wet foreground, amber light behind door"
}
```

Set `cover.design_style` to a preset id from `config/cover_styles.yaml` (see the catalog in [COVER_STYLE.md](COVER_STYLE.md)). After editing cover copy or style, regenerate with `python3 tools/regenerate_cover.py --series series/my_series --episode episode_01` or `python3 tools/generate_episode_assets.py --cover`. Full flags, resolution order, and all 26 styles: [COVER_STYLE.md](COVER_STYLE.md).

The cover displays for `EPISODE_COVER_INTRO_SECONDS` (default 2.5s) before narration begins.

## Step 5: Episode folder checklist

Before running the pipeline:

- [ ] `scenes.json` exists and validates as JSON
- [ ] Every scene has `id`, `duration`, `caption`, `prompt`
- [ ] `voiceover_text.txt` is complete and matches the script
- [ ] `continuity_notes` or `characters[]` is filled in
- [ ] `cover` section has `design_style`, title lines, and hook
- [ ] `output_slug` matches your naming convention

## Step 6: Scaffold new episodes

For Episode 2+, use `new_episode.py` — it reads `story_context.md` and auto-increments the episode number:

```bash
python3 tools/new_episode.py --series series/my_series
# Or specify a number:
python3 tools/new_episode.py --series series/my_series --episode 7
```

Then author the printed files (manually, via `author_series.py --from N`, or with an external AI tool).

Update in the new episode's `scenes.json`:

- `episode_title`
- `output_slug` → `episode_NN`
- `cover.episode_number`
- All scenes for the new story

## Auto-author with OpenAI (`author_series.py`)

Built-in alternative to hand-writing or external AI batch prompts. Runs after `init_series.py` or anytime placeholder episodes exist.

```bash
python3 tools/author_series.py --series series/my_series
python3 tools/author_series.py --series series/my_series --from 3 --to 5
python3 tools/author_series.py --series series/my_series --force
```

What it does:

- Reads `story_context.md`, `series_bible.md`, `season_outline.md`, and `ai_authoring_brief.md`
- Maintains continuity via `{series}/authoring_state.json` (characters, world rules, per-episode summaries)
- Enriches `series_bible.md` if template placeholders remain
- Writes all episode content files sequentially (each episode sees prior summaries)
- Skips episodes that already look authored unless `--force`

Requires `OPENAI_API_KEY`. Optional: `OPENAI_TEXT_MODEL` (default `gpt-4.1-mini`), `OPENAI_TEXT_TIMEOUT_SECONDS`.

Chain from init: `python3 tools/init_series.py --name "My Series" --style sci_fi --episodes 5 --auto-author`

Always human-review auto-authored content before publishing.

## AI-assisted writing (external AI)

Use `docs/AI_BATCH_PROMPT.md` as a system prompt for Claude, ChatGPT, or similar tools when you want custom prompts or more control than `author_series.py` provides.

Always human-review:

- Story originality and continuity
- Scene prompts match narration beats
- No real disasters presented as fact
- Fiction disclosure is included in upload copy

## Genre-specific notes

### Mystery / thriller

- Open with an impossible situation
- End every episode on a specific cliffhanger
- Use tight close-ups and phone screens for production efficiency
- Template: `thriller_mystery`

### Romance / drama

- Lead with emotional conflict, not exposition
- Visual style: soft light, expressive faces
- Template: `romance_drama`

### Sci-fi

- Ground futuristic elements in plausible detail
- One accent glow color for devices
- Template: `sci_fi`

### Anime (all ages)

- Lead with wonder, friendship, or discovery — not fear
- Visual style: expressive anime faces, painted skies, clean linework
- Keep stories family-friendly: no gore, horror, or graphic violence
- Template: `anime`

## Quality bar before publishing

From [WEEKLY_PIPELINE.md](WEEKLY_PIPELINE.md) — ask before posting:

- Did a human write or meaningfully revise the story?
- Is this episode materially different from the last one?
- Are visuals directed for this exact story?
- Does narration have emotion and pacing?
- Is there a real scene, not just text over random images?
- Does the ending create curiosity without misleading viewers?

## Related docs

- [GETTING_STARTED.md](GETTING_STARTED.md) — install and first render
- [CONFIGURATION.md](CONFIGURATION.md) — environment variables
- [PLATFORM_GUIDE.md](PLATFORM_GUIDE.md) — publishing
- [COVER_STYLE.md](COVER_STYLE.md) — cover design system
### Horror

- Suggest dread; avoid gore in visuals unless the platform audience expects it
- Use shadows, empty rooms, and off-frame threat
- Template: `horror`

### Noir / crime

- Rain, neon, case files, morally gray choices
- Template: `noir`

### Action

- One kinetic beat per scene; readable motion
- Template: `action`

### Cyberpunk

- Neon, rain, megacity layers — distinct from grounded `sci_fi`
- Template: `cyberpunk`

### Fantasy

- Epic scale, magic as accent, clear quest objects
- Template: `fantasy`

### Comedy

- Lead with the reaction or reversal
- Template: `comedy`

### Western

- Wide horizons, dust, standoffs, saloon interiors
- Template: `western`

### Period drama

- Pick one era per episode and stay consistent
- Template: `period_drama`

