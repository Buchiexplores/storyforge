# Daily Batch Prompt

This file has moved to the generic, repo-local version:

**[docs/AI_BATCH_PROMPT.md](docs/AI_BATCH_PROMPT.md)**

Use that prompt with your AI assistant for batch episode writing and pipeline runs. Fill in `{SERIES_DIR}`, `{SERIES_TITLE}`, and other placeholders for your series.

Quick start:

```bash
# Set your active series in .env.story.local
PIPELINE_SERIES_DIR=examples/phone_from_tomorrow

# Run one episode after content is written
python3 tools/run_episode_pipeline.py --episode episode_07
```

See also:

- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
- [docs/STORY_AUTHORING.md](docs/STORY_AUTHORING.md)
