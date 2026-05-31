# Configuration Reference

Complete reference for environment variables, series configuration, style templates, and CLI flags.

- [GETTING_STARTED.md](GETTING_STARTED.md) — onboarding
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — failures and fixes

---

## Environment file

Copy `.env.story.example` to `.env.story.local` at the repo root. Never commit `.env.story.local`.

---

## Provider architecture (contributions welcome)

Each pipeline stage maps to a tool module and supports one or more backends today. **Alternative providers (open-source, local, or hosted) are welcome** — see [README.md → Contributing AI provider integrations](../README.md#contributing-ai-provider-integrations).

| Stage | File / function | Providers today | CLI / env switch |
|-------|-----------------|-----------------|------------------|
| Text authoring | `tools/author_series.py` → OpenAI chat | OpenAI only | `--model` / `OPENAI_TEXT_MODEL` |
| Scene images | `tools/generate_episode_assets.py` → `generate_images()` | `openai`, `fal`, `local` | `--image-provider`, `--openai-images`, `--local-images` |
| Cover background | `generate_episode_assets.py` → `generate_cover()` | `openai`, `fal`, `local` | `--cover-provider`, `--openai-cover` |
| Voice | `generate_episode_assets.py` → `generate_voice()` | ElevenLabs only | `--voice` (no provider flag yet) |
| Video motion | `generate_episode_assets.py` → `generate_videos()` | `local` (ffmpeg Ken Burns), `fal` | `--local-videos`, `--video-mode {local,fal}`, `PIPELINE_VIDEO_MODE` |
| Final render | `tools/render_episode.py` | ffmpeg only | No API keys |

### Environment variables by provider

| Provider | Variables |
|----------|-----------|
| **OpenAI** (images + text) | `OPENAI_API_KEY`, `OPENAI_IMAGE_MODEL`, `OPENAI_IMAGE_SIZE`, `OPENAI_IMAGE_QUALITY`, `OPENAI_IMAGE_STRICT`, `OPENAI_IMAGE_TIMEOUT_SECONDS`, `OPENAI_TEXT_MODEL`, `OPENAI_TEXT_TIMEOUT_SECONDS` |
| **ElevenLabs** (voice) | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID`, `ELEVENLABS_OUTPUT_FORMAT` |
| **fal.ai** (optional images + motion) | `FAL_KEY`, `FAL_VIDEO_MODEL`, `FAL_VIDEO_RESOLUTION`, `FAL_VIDEO_TIMEOUT_SECONDS`, `FAL_VIDEO_GENERATE_AUDIO` |
| **Local motion** (default) | `FFMPEG_PATH`, `FFPROBE_PATH` — no API key |
| **Local images** (`--image-provider local`) | None — generates storyboard placeholders |

Default motion is **local ffmpeg** (`PIPELINE_VIDEO_MODE=local`): zero API cost. fal motion is opt-in via `--video-mode fal` or env override.

### Adding a provider (contributor checklist)

1. **Find the stage** in the table above and read the existing branch (e.g. `generate_images()` provider switch).
2. **Add a provider value** to the relevant argparse choices (`--image-provider`, `--cover-provider`, etc.) or introduce a new flag if the stage has none (e.g. voice).
3. **Implement** the backend in an isolated function; reuse download/save helpers where possible.
4. **Keep defaults unchanged** — OpenAI for images/text, ElevenLabs for voice, local for motion.
5. **Optional deps** — add commented lines to `requirements.txt`; fail with a clear install message when the package is missing.
6. **Env vars** — extend `.env.story.example` and document them in this file.
7. **Test** — smoke-test with `--skip-voice --skip-images --skip-cover --skip-videos` for tooling changes; document which key is needed for your provider.
8. **Update README** Contributing section if you add a major new backend.

---

## Environment variables (from `.env.story.example`)

### Active series

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_SERIES_DIR` | *(empty)* | Active series folder (relative or absolute). Set to `series/<slug>` after `init_series.py`. Use `--series examples/...` for published demos without changing this. |

### OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | GPT Image API key |
| `OPENAI_IMAGE_STRICT` | `1` | Stop on image failures; no local fallback when `1` |
| `OPENAI_IMAGE_MODEL` | `gpt-image-1.5` | Image model |
| `OPENAI_IMAGE_SIZE` | `1024x1536` | Generation size |
| `OPENAI_IMAGE_QUALITY` | `high` | Quality setting |
| `OPENAI_IMAGE_TIMEOUT_SECONDS` | `180` | Request timeout |
| `OPENAI_TEXT_MODEL` | `gpt-4.1-mini` | Chat model for `author_series.py` |
| `OPENAI_TEXT_TIMEOUT_SECONDS` | `180` | Chat request timeout for `author_series.py` |

### ElevenLabs

| Variable | Default | Description |
|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | *(required for voice)* | API key |
| `ELEVENLABS_VOICE_ID` | *(required for voice)* | From `--list-voices` |
| `ELEVENLABS_MODEL_ID` | `eleven_multilingual_v2` | TTS model |
| `ELEVENLABS_OUTPUT_FORMAT` | `mp3_44100_128` | Audio format |

### fal.ai (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `FAL_KEY` | *(empty)* | fal.ai API key |
| `PIPELINE_VIDEO_MODE` | `local` | `local` or `fal` for motion clips |
| `FAL_VIDEO_MODEL` | `bytedance/seedance-2.0/image-to-video` | fal video model |
| `FAL_VIDEO_RESOLUTION` | `720p` | fal resolution |
| `FAL_VIDEO_TIMEOUT_SECONDS` | `480` | fal timeout |
| `FAL_VIDEO_GENERATE_AUDIO` | `false` | fal clip audio |

### Video render

| Variable | Default | Description |
|----------|---------|-------------|
| `EPISODE_COVER_INTRO_SECONDS` | `2.5` | Cover shown before narration |
| `FFMPEG_PATH` | auto (`setup.sh`) | ffmpeg binary path — written by `./setup.sh` when found |
| `FFPROBE_PATH` | auto (`setup.sh`) | ffprobe binary path — written by `./setup.sh` when found |

### Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_NOTIFY_ON_RUN` | `true` | Notify after pipeline run |
| `PIPELINE_NOTIFY_EMAIL` | *(empty)* | Recipient(s), comma-separated |
| `PIPELINE_NOTIFY_EMAILS` | *(empty)* | Alias for recipients |
| `EMAIL_RECEIVER` | *(empty)* | Legacy alias for `PIPELINE_NOTIFY_EMAIL` |

### SMTP

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | *(empty)* | SMTP server |
| `SMTP_PORT` | `587` | Port |
| `SMTP_USERNAME` | *(empty)* | SMTP login |
| `SMTP_PASSWORD` | *(empty)* | SMTP password or app password |
| `SMTP_FROM_EMAIL` | *(empty)* | From address |
| `SMTP_USE_TLS` | `true` | STARTTLS |

Legacy aliases still read by `send_pipeline_update.py`: `EMAIL_SENDER` → `SMTP_USERNAME`/`SMTP_FROM_EMAIL`, `EMAIL_PASSWORD` → `SMTP_PASSWORD`. Prefer `SMTP_*` in new configs.

Without SMTP, pending files go to `{series}/notifications/`.

---

## `series_config.yaml` schema

Optional YAML at `{series}/series_config.yaml`. Merged with `style_template` from `config/style_templates/`.

```yaml
series:
  title: "Your Series Title"
  channel_name: "Your Channel Name"
  logline: "One sentence premise."

style_template: thriller_mystery   # thriller_mystery | horror | noir | action | sci_fi | cyberpunk | fantasy | anime | romance_drama | comedy | western | period_drama

# Optional overrides:
# visual_style: "custom style string"
# image_prompt_rules: |
#   Multi-line rules for image prompts.

voice:
  narrator_notes: "Pacing guidance for authors."

platforms:
  default_disclosure: "This is a fictional story."
  publish_order:
    - tiktok
    - youtube_shorts
    - instagram_reels

production:
  target_duration_seconds: "60-90"
  scene_count: "15-25"
  cover_intro_seconds: 2.5
```

Episode-level overrides: `scenes.json` (`style`, `image_prompt_rules`, `cover`, etc.).

---

## Style templates

| Template | Genre |
|----------|-------|
| `thriller_mystery` | Suspense, cliffhangers, moody lighting |
| `horror` | Supernatural dread, shadows, implied threat |
| `noir` | Crime noir, rain, detectives, neon reflections |
| `action` | Blockbuster chases, standoffs, high energy |
| `sci_fi` | Near-future tech, discovery, consequence |
| `cyberpunk` | Neon dystopia, megacity rain, hackers |
| `fantasy` | Epic quests, magic, mythic worlds |
| `anime` | All-ages anime adventure — wonder and heart |
| `romance_drama` | Relationships, emotional close-ups |
| `comedy` | Lighthearted humor, bright reactions |
| `western` | Frontier dust, duels, wide horizons |
| `period_drama` | Historical costume drama, elegant interiors |

Each provides `visual_style`, `image_prompt_rules`, `cover` defaults, and `platforms` disclosures/hashtags.

`init_series.py --style {name}` seeds a new series from a template.

---

## CLI: `run_episode_pipeline.py`

| Flag | Description |
|------|-------------|
| `--series PATH` | Series dir (default: `PIPELINE_SERIES_DIR`) |
| `--episode NAME` | Episode folder **(required)** |
| `--force` | Regenerate images, cover, videos |
| `--skip-voice` / `--skip-images` / `--skip-cover` / `--skip-videos` / `--skip-render` | Skip steps |
| `--video-mode {local,fal}` | Motion provider |
| `--notify` / `--no-notify` | Completion notification |

---

## CLI: `generate_episode_assets.py`

| Flag | Description |
|------|-------------|
| `--series`, `--episode` | Target series/episode |
| `--list-voices` | Print ElevenLabs voice IDs |
| `--voice` | Generate voiceover |
| `--images` | Generate scene images |
| `--force-images` | Overwrite existing images |
| `--image-provider {openai,fal,local}` | Image backend |
| `--openai-images` / `--local-images` | Provider shortcuts |
| `--image-ids IDS` | Comma-separated scene IDs only |
| `--videos` | Generate motion clips |
| `--force-videos` | Overwrite existing videos |
| `--local-videos` | ffmpeg zoom-pan (no fal) |
| `--video-ids IDS` | Comma-separated video scene IDs |
| `--cover` | Generate cover |
| `--force-cover` | Regenerate cover background |
| `--cover-provider {openai,fal,local}` | Cover background provider |
| `--openai-cover` | OpenAI cover shortcut |

---

## CLI: `render_episode.py`

| Flag | Description |
|------|-------------|
| `--series`, `--episode` | Target series/episode |
| `--intro-duration SECONDS` | Cover intro (default: `EPISODE_COVER_INTRO_SECONDS`) |

Re-render only; does not call OpenAI or ElevenLabs.

---

## CLI: `init_series.py`

Run with no flags to launch the 6-step interactive wizard (title → style → episode count → logline → story description → folder).

| Flag | Description |
|------|-------------|
| *(no flags)* | Launch interactive wizard |
| `--name TITLE` | Series title **(required for non-interactive)** |
| `--style TEMPLATE` | Style template (default: `thriller_mystery`) |
| `--episodes N` | Number of episode folders to scaffold (default: `1`) |
| `--logline TEXT` | One-sentence premise |
| `--story-context TEXT` | Extended AI context (characters, world, arc) |
| `--output-dir DIR` | Parent folder (default: `series`) |
| `--slug SLUG` | Folder slug (default: slugified name) |
| `--set-active` / `--no-set-active` | Write `PIPELINE_SERIES_DIR` to `.env.story.local` (default: ask) |
| `--auto-author` / `--no-auto-author` | Run `author_series.py` after scaffold (default: ask when interactive) |

---

## CLI: `author_series.py`

OpenAI auto-authors scaffolded episodes sequentially for continuity. Requires `OPENAI_API_KEY`.

| Flag | Description |
|------|-------------|
| `--series PATH` | Series dir (default: `PIPELINE_SERIES_DIR`) |
| `--from N` | First episode number (default: `1`) |
| `--to N` | Last episode number (default: highest scaffolded) |
| `--force` | Regenerate even if episode looks authored |
| `--model NAME` | OpenAI chat model (default: `OPENAI_TEXT_MODEL`) |

Writes per episode: `script.md`, `voiceover_text.txt`, `voice_direction.md`, `visual_prompts.md`, `scenes.json`, `upload_package.md`. Creates/updates `{series}/authoring_state.json` for character and plot continuity. Enriches `series_bible.md` if placeholders remain.

---

## CLI: `new_episode.py`

Scaffold the next episode folder in an existing series. Reads `story_context.md` for template pre-fill.

| Flag | Description |
|------|-------------|
| `--series PATH` | Series dir (default: `PIPELINE_SERIES_DIR`) |
| `--episode N` | Explicit episode number (default: next available) |

---

## Series folder layout

After `init_series.py`, a typical series looks like:

```text
series/my_series/
  series_config.yaml       # Title, logline, style_template, voice notes
  series_bible.md          # Characters, world rules, tone
  story_context.md         # Extended AI context (from wizard step 5)
  season_outline.md        # Per-episode hook/cliffhanger placeholders
  ai_authoring_brief.md    # Instructions for AI assistants
  authoring_state.json     # Created by author_series.py — continuity state
  notifications/           # Pipeline notification files (when SMTP not set)
  episode_01/
    script.md
    voiceover_text.txt
    voice_direction.md
    visual_prompts.md
    scenes.json            # Required to render
    upload_package.md
    assets/                # Created by pipeline (gitignored)
  episode_02/
    ...
```

| File | Purpose |
|------|---------|
| `story_context.md` | Characters, world rules, season arc — fed to `author_series.py` and `new_episode.py` |
| `ai_authoring_brief.md` | System-level instructions for external AI tools |
| `authoring_state.json` | Character list, world rules, per-episode summaries — updated after each `author_series.py` run |
