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

Use `templates/series/series_bible.template.md` or run `init_series.py` to scaffold one.

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
  "series_title": "Your Series Title",
  "episode_number": 1,
  "part_number": 1,
  "hook_lines": ["DON'T", "OPEN", "IT"],
  "hook_highlight": "OPEN",
  "title_lines": ["THE DOOR", "IS LOCKED"],
  "background_prompt": "dark rainy hallway, glowing phone in wet foreground, amber light behind door"
}
```

See `docs/COVER_STYLE.md` for the full cover design system.

The cover displays for `EPISODE_COVER_INTRO_SECONDS` (default 2.5s) before narration begins.

## Step 5: Episode folder checklist

Before running the pipeline:

- [ ] `scenes.json` exists and validates as JSON
- [ ] Every scene has `id`, `duration`, `caption`, `prompt`
- [ ] `voiceover_text.txt` is complete and matches the script
- [ ] `continuity_notes` or `characters[]` is filled in
- [ ] `cover` section has title lines and hook
- [ ] `output_slug` matches your naming convention

## Step 6: Scaffold new episodes

For Episode 2+, copy the previous episode folder structure:

```bash
cp -R series/my_series/episode_01 series/my_series/episode_02
rm -rf series/my_series/episode_02/assets/*
# Re-create asset dirs or run init and copy content files only
```

Update in `episode_02/scenes.json`:

- `episode_title`
- `output_slug` → `episode_02`
- `cover.episode_number` → `2`
- All scenes for the new story

## AI-assisted writing

Use `docs/AI_BATCH_PROMPT.md` as a system prompt for Claude, ChatGPT, or similar tools to generate episode batches.

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

## Quality bar before publishing

From `weekly_pipeline.md` — ask before posting:

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
