# Troubleshooting

Common failures and fixes. See [CONFIGURATION.md](CONFIGURATION.md) for env vars.

---

## OpenAI billing / quota (`OPENAI_IMAGE_STRICT=1`)

**Symptoms:** billing/quota errors; pipeline stops on `--images` or `--cover`; `{series}/notifications/*_openai_generation_blocked.md`

**Fix:** Add OpenAI credits; verify `OPENAI_API_KEY`; rerun failed steps:

```bash
python3 tools/generate_episode_assets.py --episode episode_05 --images --openai-images
python3 tools/generate_episode_assets.py --episode episode_05 --cover --openai-cover
```

**Draft mode only:** `OPENAI_IMAGE_STRICT=0` allows local storyboard fallback (not for published episodes).

---

## Missing API keys

| Error | Fix |
|-------|-----|
| `Missing OPENAI_API_KEY` | Set in `.env.story.local` |
| `Missing ELEVENLABS_*` | Set key + voice ID; run `--list-voices` |
| `Missing FAL_KEY` | Only needed for `--video-mode fal` |

Env file must be `.env.story.local` at repo root.

---

## ffmpeg not found

`./setup.sh` tries to locate ffmpeg/ffprobe and writes `FFMPEG_PATH` / `FFPROBE_PATH` into `.env.story.local`. On macOS with Homebrew it can also offer to run `brew install ffmpeg`.

Manual install:

```bash
brew install ffmpeg   # macOS
```

If binaries are installed but not on cron's `PATH`, keep the paths in `.env.story.local`:

```text
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg
FFPROBE_PATH=/opt/homebrew/bin/ffprobe
```

---

## ElevenLabs voice issues

| Issue | Fix |
|-------|-----|
| 401/403 | Invalid API key or plan |
| 422 | Bad voice ID or text too long |
| Inconsistent voice | Keep same `ELEVENLABS_VOICE_ID` across episodes |

Regenerate voice: `--voice` then `render_episode.py`

---

## Notifications / SMTP

**No email:** Set `PIPELINE_NOTIFY_EMAIL` + `SMTP_*` vars (`SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, etc.). Legacy `EMAIL_SENDER` / `EMAIL_PASSWORD` / `EMAIL_RECEIVER` still work — see [API_KEYS.md](API_KEYS.md#4-email-notifications-optional).

**Pending files:** Normal without SMTP — check `{series}/notifications/`

**Disable:** `--no-notify` on pipeline runs

---

## Re-render without regenerating

No OpenAI/ElevenLabs calls:

```bash
python3 tools/run_episode_pipeline.py \
  --episode episode_04 \
  --skip-voice --skip-images --skip-cover --skip-videos
```

Or: `python3 tools/render_episode.py --episode episode_04`

Change cover intro: `--intro-duration 3.0`

---

## Other issues

| Issue | Fix |
|-------|-----|
| Missing `scenes.json` | Copy from `templates/episode/scenes.template.json` |
| Missing voiceover warning | Run `--voice` first |
| Images not updating | Add `--force-images` or `--force` |
| Captions out of sync | Re-render after fixing `scenes.json`; regenerate voice if text changed |
| Missing cover intro | Run `--cover --openai-cover` |
| PyYAML error | `pip install pyyaml` or `pip install -r requirements.txt` |

Verify output:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of csv=p=0 EXPORT.mp4
```

Expected: `1080,1920,30/1,h264`
