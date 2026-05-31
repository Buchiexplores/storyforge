# Getting Started

This guide walks you from zero to a finished vertical episode video. For deeper reference, see:

- [API_KEYS.md](API_KEYS.md) — how to obtain every API key, step by step
- [CONFIGURATION.md](CONFIGURATION.md) — environment variables, series config, CLI flags
- [STORY_AUTHORING.md](STORY_AUTHORING.md) — scripts, `scenes.json`, style templates
- [COVER_STYLE.md](COVER_STYLE.md) — episode cover poster system
- [PLATFORM_GUIDE.md](PLATFORM_GUIDE.md) — TikTok, Instagram Reels, YouTube Shorts
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — common failures and fixes
- [AI_BATCH_PROMPT.md](AI_BATCH_PROMPT.md) — AI-assisted batch episode writing
- [WEEKLY_PIPELINE.md](WEEKLY_PIPELINE.md) — weekly production cadence

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| **Python 3.10+** | Run pipeline scripts |
| **ffmpeg + ffprobe** | Video rendering and verification (auto-detected by `./setup.sh`) |
| **OpenAI API key** | Scene images and cover backgrounds |
| **ElevenLabs API key + voice ID** | Narrator voiceover |

Optional: fal.ai key (AI motion clips), SMTP (email notifications).

```bash
cd storyforge
./setup.sh   # venv + deps + ffmpeg/ffprobe detection (offers Homebrew install on macOS)
```

---

## 1. Clone and configure

```bash
git clone <your-repo-url>
cd storyforge
./setup.sh
```

`setup.sh` creates `.env.story.local`, locates `ffmpeg`/`ffprobe`, and writes `FFMPEG_PATH` / `FFPROBE_PATH` into that file (useful for cron jobs with a minimal `PATH`).

Edit `.env.story.local` with your API keys. Never commit this file.
**Don't have keys yet? Follow [API_KEYS.md](API_KEYS.md)** for step-by-step instructions on getting each one.

```text
# Your series (set after init_series.py). examples/ is for published demos only.
PIPELINE_SERIES_DIR=series/the_last_signal
OPENAI_API_KEY=sk-...
OPENAI_IMAGE_STRICT=1
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
```

List ElevenLabs voices (after `ELEVENLABS_API_KEY` is set): `python3 tools/generate_episode_assets.py --list-voices` — see [API_KEYS.md](API_KEYS.md#2-elevenlabs-voiceover--required) for full steps.

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

Render the **published demo** under `examples/` (does not require changing `PIPELINE_SERIES_DIR`):

```bash
python3 tools/run_episode_pipeline.py --series examples/phone_from_tomorrow --episode episode_01
```

Output: `examples/phone_from_tomorrow/episode_01/assets/exports/episode_01_vertical.mp4`

---

## 4. Create your own series

The interactive wizard prompts for your story name, style, episode count, and logline, then prints links to every file it scaffolds:

```bash
python3 tools/init_series.py
```

Prefer flags (scriptable / CI)?

```bash
python3 tools/init_series.py --name "The Last Signal" --style sci_fi --episodes 5 --output-dir series
```

Styles: `thriller_mystery`, `romance_drama`, `sci_fi`

The wizard offers to set `PIPELINE_SERIES_DIR` for you. After authoring `episode_01`:

```bash
python3 tools/run_episode_pipeline.py --series series/the_last_signal --episode episode_01
```

### Add the next episode

Scaffold episodes one at a time — the slug auto-increments:

```bash
python3 tools/new_episode.py --series series/the_last_signal
# Author the printed files, then:
python3 tools/run_episode_pipeline.py --series series/the_last_signal --episode episode_02
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

Use [AI_BATCH_PROMPT.md](AI_BATCH_PROMPT.md) to write episodes with AI, then pipeline each one. Verify with `ffprobe`. Notify with `tools/send_pipeline_update.py`. See [WEEKLY_PIPELINE.md](WEEKLY_PIPELINE.md) for weekly rhythm.

---

## 7. Automate it (daily cron + email)

Let the pipeline render a new episode for you every morning and email you when it's done.

### Step 1 — turn on email notifications

In `.env.story.local`, set your recipient and SMTP details (see [API_KEYS.md](API_KEYS.md#4-smtp-optional--email-notifications)):

```bash
PIPELINE_NOTIFY_ON_RUN=true
PIPELINE_NOTIFY_EMAIL=you@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=your-app-password   # Gmail: use an App Password, not your login
SMTP_FROM_EMAIL=you@example.com
SMTP_USE_TLS=true
```

Without SMTP, notifications are still written to your series `notifications/` folder — you just won't get email.

### Step 2 — use the auto-runner

`tools/run_next_episode.py` finds the **lowest-numbered episode that has content but no final video yet**, and renders it. Pre-author several episodes' `scenes.json` + `voiceover_text.txt`, and each daily run picks up the next one automatically.

```bash
python3 tools/run_next_episode.py                    # uses PIPELINE_SERIES_DIR
python3 tools/run_next_episode.py --series series/the_last_signal --force
```

When every authored episode is rendered, it exits cleanly with "nothing to render."

### Step 3 — schedule it

Edit your crontab (`crontab -e`) and add a daily 7:00 AM run:

```cron
# Render the next pending episode every morning at 7:00 and log output
0 7 * * * cd /absolute/path/to/storyforge && /absolute/path/to/storyforge/.venv/bin/python tools/run_next_episode.py >> /tmp/storyforge.log 2>&1
```

Cron tips:
- **Use absolute paths** for both the repo and the Python interpreter (cron has a minimal environment).
- If `ffmpeg`/`ffprobe` aren't on cron's `PATH`, set `FFMPEG_PATH` and `FFPROBE_PATH` in `.env.story.local`.
- The email notification (success or failure) is sent automatically because `PIPELINE_NOTIFY_ON_RUN=true`.
- Check `/tmp/storyforge.log` if a morning run is missing.

> **macOS:** grant `cron` Full Disk Access (System Settings → Privacy & Security) or run the job under `launchd` if it can't read your repo folder.

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
