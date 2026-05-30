# Getting Started

This guide walks you from zero to a finished vertical episode video. For deeper reference, see:

- [CONFIGURATION.md](CONFIGURATION.md) — environment variables, series config, CLI flags
- [STORY_AUTHORING.md](STORY_AUTHORING.md) — scripts, `scenes.json`, style templates
- [COVER_STYLE.md](COVER_STYLE.md) — episode cover poster system
- [PLATFORM_GUIDE.md](PLATFORM_GUIDE.md) — TikTok, Instagram Reels, YouTube Shorts
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — common failures and fixes
- [AI_BATCH_PROMPT.md](AI_BATCH_PROMPT.md) — AI-assisted batch episode writing

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| **Python 3.10+** | Run pipeline scripts |
| **ffmpeg + ffprobe** | Video rendering and verification |
| **OpenAI API key** | Scene images and cover backgrounds |
| **ElevenLabs API key + voice ID** | Narrator voiceover |

Optional: fal.ai key (AI motion clips), SMTP (email notifications).

```bash
cd storyforge
python3 -m pip install -r requirements.txt
brew install ffmpeg   # macOS
```

---

## 1. Clone and configure

```bash
git clone <your-repo-url>
cd storyforge
cp .env.story.example .env.story.local
```

Edit `.env.story.local` with your keys. Never commit this file.

```text
PIPELINE_SERIES_DIR=examples/phone_from_tomorrow
OPENAI_API_KEY=sk-...
OPENAI_IMAGE_STRICT=1
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
```

List ElevenLabs voices: `python3 tools/generate_episode_assets.py --list-voices`

---

## 2. Episode content package

Each episode folder (e.g. `examples/phone_from_tomorrow/episode_01/`) needs:

| Required | Optional authoring |
|----------|-------------------|
| `scenes.json` | `script.md` |
| `voiceover_text.txt` | `voice_direction.md`, `visual_prompts.md`, `upload_package.md` |

Pipeline output: `assets/exports/{slug}_vertical.mp4`, cover, preview grid, contact sheet.

See [STORY_AUTHORING.md](STORY_AUTHORING.md).

---

## 3. Run the example

```bash
python3 tools/run_episode_pipeline.py --episode episode_01
```

Output: `examples/phone_from_tomorrow/episode_01/assets/exports/episode_01_vertical.mp4`

---

## 4. Create your own series

```bash
python3 tools/init_series.py --name "The Last Signal" --style sci_fi --output-dir series
```

Styles: `thriller_mystery`, `romance_drama`, `sci_fi`

Then set `PIPELINE_SERIES_DIR=series/the_last_signal` and run:

```bash
python3 tools/run_episode_pipeline.py --series series/the_last_signal --episode episode_01
```

---

## 5. Partial pipeline flags

| Flag | Effect |
|------|--------|
| `--skip-voice` | Skip ElevenLabs |
| `--skip-images` | Skip scene images |
| `--skip-cover` | Skip cover |
| `--skip-videos` | Skip motion clips |
| `--skip-render` | Skip final render |
| `--force` | Regenerate images, cover, videos |
| `--no-notify` | Disable notifications |
| `--video-mode fal` | Use fal.ai for motion (needs `FAL_KEY`) |

Render only (no API calls): `--skip-voice --skip-images --skip-cover --skip-videos`

---

## 6. Batch workflow

Use [AI_BATCH_PROMPT.md](AI_BATCH_PROMPT.md) to write episodes with AI, then pipeline each one. Verify with `ffprobe`. Notify with `tools/send_pipeline_update.py`. See `weekly_pipeline.md` for weekly rhythm.

---

## 7. Cron

```cron
0 2 * * * cd /path/to/storyforge && python3 tools/run_episode_pipeline.py --episode episode_07 >> /tmp/story_pipeline.log 2>&1
```

Use absolute paths; set `FFMPEG_PATH` if ffmpeg is not on cron PATH.

---

## 8. Cost controls

- Keep `OPENAI_IMAGE_STRICT=1` so billing failures stop the batch (no silent fallbacks)
- Default `PIPELINE_VIDEO_MODE=local` avoids fal video credits
- Use skip flags and `--image-ids` for selective regeneration
- Batch 1–3 episodes; verify before continuing

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 9. Verify before publishing

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of csv=p=0 \
  examples/phone_from_tomorrow/episode_01/assets/exports/episode_01_vertical.mp4
```

Expected: `1080,1920,30/1,h264`. Then [PLATFORM_GUIDE.md](PLATFORM_GUIDE.md).
