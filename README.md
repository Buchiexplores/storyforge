# Fiction Storytelling Pipeline

Turn written short-fiction episodes into vertical videos for **TikTok**, **Instagram Reels**, and **YouTube Shorts**.

This repo is a local production pipeline that converts an episode content package into:

- ElevenLabs narrator voiceover
- OpenAI scene images
- OpenAI cover background + local typography compositing
- Local motion clips from still images (no video API credits required)
- Final synced 1080×1920 vertical MP4 with cover intro
- Preview grid, image contact sheet, and optional email notifications

## Quick start

```bash
git clone <your-repo-url>
cd fiction_storytelling

./setup.sh  # creates .venv, installs deps, copies .env.story.example
# Edit .env.story.local with your API keys

# Option A: use the included example series
python3 tools/run_episode_pipeline.py --episode episode_01

# Option B: scaffold your own series
python3 tools/init_series.py --name "My Story Series" --style thriller_mystery
# Set PIPELINE_SERIES_DIR=series/my_story_series in .env.story.local
# Edit series/my_story_series/episode_01/scenes.json and voiceover_text.txt
python3 tools/run_episode_pipeline.py --series series/my_story_series --episode episode_01
```

## What you need

| Requirement | Purpose |
|-------------|---------|
| Python 3.10+ | Run pipeline scripts |
| ffmpeg + ffprobe | Video rendering |
| OpenAI API key | Scene images and cover backgrounds |
| ElevenLabs API key + voice ID | Narrator voiceover |

Optional: fal.ai key if you want AI-generated motion clips instead of local Ken Burns-style motion.

## Repository layout

```text
fiction_storytelling/
  .env.story.example          # Config template (copy to .env.story.local)
  config/style_templates/     # Reusable visual + platform style presets
  docs/                       # Full onboarding and reference docs
  examples/phone_from_tomorrow/  # Complete example series (Episodes 1-9 scripts)
  series/                     # Your own series go here (empty by default)
  templates/                  # Scaffolding templates for new series/episodes
  tools/                      # Pipeline scripts
```

## Documentation

Start here for full onboarding:

- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** — install, configure, first render, batch workflow
- **[docs/STORY_AUTHORING.md](docs/STORY_AUTHORING.md)** — write scripts, scenes.json, style templates
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** — all environment variables and series config
- **[docs/PLATFORM_GUIDE.md](docs/PLATFORM_GUIDE.md)** — TikTok, Instagram Reels, YouTube Shorts publishing
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — common failures and fixes
- **[docs/AI_BATCH_PROMPT.md](docs/AI_BATCH_PROMPT.md)** — prompt for AI-assisted episode writing batches

## Run one episode

```bash
python3 tools/run_episode_pipeline.py \
  --series examples/phone_from_tomorrow \
  --episode episode_01 \
  --force
```

Output:

```text
examples/phone_from_tomorrow/episode_01/assets/exports/episode_01_vertical.mp4
```

## Create a new series

```bash
python3 tools/init_series.py \
  --name "The Last Signal" \
  --style sci_fi \
  --output-dir series
```

Built-in style templates: `thriller_mystery`, `romance_drama`, `sci_fi`

## License

MIT — see [LICENSE](LICENSE).
