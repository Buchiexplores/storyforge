# Production Steps

Step-by-step production is documented in:

- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** — install, configure, run pipeline, verify
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** — env vars and CLI flags
- **[docs/STORY_AUTHORING.md](docs/STORY_AUTHORING.md)** — episode content package

## Quick reference

```bash
# 1. Configure keys
cp .env.story.example .env.story.local

# 2. List voices (if needed)
python3 tools/generate_episode_assets.py --list-voices

# 3. Full pipeline
python3 tools/run_episode_pipeline.py --episode episode_01

# 4. Review export
# examples/phone_from_tomorrow/episode_01/assets/exports/episode_01_vertical.mp4

# 5. Publish using upload_package.md
# See docs/PLATFORM_GUIDE.md
```

For weekly production cadence, see `weekly_pipeline.md`.
