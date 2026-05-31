# AI Batch Episode Prompt

Use this prompt with an AI assistant (Claude, ChatGPT, etc.) to write and produce multiple episodes in a batch. Copy the entire **Prompt** section below into your AI tool, then fill in the bracketed placeholders.

Related docs:

- [STORY_AUTHORING.md](STORY_AUTHORING.md) — episode structure and `scenes.json`
- [GETTING_STARTED.md](GETTING_STARTED.md) — running the pipeline
- [CONFIGURATION.md](CONFIGURATION.md) — environment and CLI flags
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — billing and failure handling

---

## Prompt

```text
You are helping produce episodes for a serialized storyforge pipeline.

## Series context

- Series directory: {SERIES_DIR}          # e.g. examples/phone_from_tomorrow or series/my_series
- Series title: {SERIES_TITLE}
- Style template: {STYLE_TEMPLATE}      # thriller_mystery | horror | noir | action | sci_fi | cyberpunk | fantasy | anime | romance_drama | comedy | western | period_drama
- Narrator tone: {NARRATOR_NOTES}       # from series_config.yaml or series bible

Read before writing:
- {SERIES_DIR}/series_bible.md
- {SERIES_DIR}/season_outline.md
- Existing episodes for continuity (script.md, scenes.json, voiceover_text.txt)

## Batch rules

1. Generate up to {MAX_EPISODES_PER_BATCH} subsequent episodes per run, starting after the highest numbered episode folder that already has a completed vertical export.
2. Stop at episode {FINAL_EPISODE_NUMBER} if set. When the final episode is complete, notify that the season arc is done and suggest planning the next season or a new series.
3. Scaffold each new episode folder with `python3 tools/new_episode.py --series {SERIES_DIR}` before authoring its content.
4. Use OpenAI image generation strictly for all scene images and cover backgrounds. Assume OPENAI_IMAGE_STRICT=1.
5. If OpenAI image generation fails (especially billing/quota errors), STOP the batch and report the error. Do NOT fall back to fal.ai or local storyboard art.
6. Keep the same narrator voice and character continuity from earlier episodes. Reference continuity_notes and characters in scenes.json.
7. Each episode must include these files:
   - script.md
   - voiceover_text.txt (150–220 words; no markdown)
   - voice_direction.md
   - visual_prompts.md
   - scenes.json (timed scenes, image prompts, cover config, caption_segments if needed)
   - upload_package.md (captions, titles, disclosures, hashtags)
8. Captions, narration, and visuals must stay synced. After rendering, verify with ffprobe.
9. Final video must start with the episode cover for 2.5 seconds before narration (EPISODE_COVER_INTRO_SECONDS).
10. Clean final export path: {SERIES_DIR}/{EPISODE}/assets/exports/{output_slug}_vertical.mp4

## Per-episode pipeline commands

Run from the storyforge repo root. Replace {EPISODE} with episode folder name (e.g. episode_07).

# Full pipeline (preferred):
OPENAI_IMAGE_STRICT=1 python3 tools/run_episode_pipeline.py \
  --series {SERIES_DIR} \
  --episode {EPISODE}

# Or step-by-step:
OPENAI_IMAGE_STRICT=1 python3 tools/generate_episode_assets.py --series {SERIES_DIR} --episode {EPISODE} --voice
OPENAI_IMAGE_STRICT=1 python3 tools/generate_episode_assets.py --series {SERIES_DIR} --episode {EPISODE} --images --openai-images
OPENAI_IMAGE_STRICT=1 python3 tools/generate_episode_assets.py --series {SERIES_DIR} --episode {EPISODE} --cover --openai-cover
python3 tools/generate_episode_assets.py --series {SERIES_DIR} --episode {EPISODE} --videos --local-videos
python3 tools/render_episode.py --series {SERIES_DIR} --episode {EPISODE}

Use --force / --force-images / --force-cover / --force-videos only when regenerating existing assets.

## Before finalizing each batch

Verify for every episode in the batch:
- [ ] Expected scene image count present in assets/images/
- [ ] Motion clips present in assets/video/ (or local fallback generated)
- [ ] Final video stream is 1080x1920, 30fps, H.264 + AAC
- [ ] Duration ≈ narration length + post-roll + 2.5s cover intro
- [ ] Preview grid and contact sheet exist in assets/exports/
- [ ] upload_package.md filled with fiction disclosure on all platforms
- [ ] No logos, public figures, or real personal data in prompts or images

ffprobe checks:
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {EXPORT_PATH}
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of csv=p=0 {EXPORT_PATH}

## Notification after batch

Write a concise Markdown summary listing each episode:
- Episode title
- Final video path
- Cover path
- Preview grid path
- Verified duration

Send with:
python3 tools/send_pipeline_update.py \
  --subject "Storytelling batch ready: Episodes {START}-{END}" \
  --body-file PATH_TO_UPDATE.md \
  --series-dir {SERIES_DIR}

Recipient is configured via PIPELINE_NOTIFY_EMAIL in .env.story.local.
Without SMTP, pending files are written to {SERIES_DIR}/notifications/.

## Output format for this session

For each episode, deliver:
1. All content files (show full contents or write to disk)
2. Confirmation of pipeline commands run
3. ffprobe verification results
4. Any blockers (OpenAI quota, missing keys, ffmpeg errors)

Start by listing which episode numbers you will produce and their one-line hooks.
```

---

## Placeholder reference

| Placeholder | Example |
|-------------|---------|
| `{SERIES_DIR}` | `examples/phone_from_tomorrow` |
| `{SERIES_TITLE}` | `The Phone That Receives Tomorrow` |
| `{STYLE_TEMPLATE}` | `thriller_mystery` |
| `{NARRATOR_NOTES}` | Modern, tense, intimate. Pause before cliffhangers. |
| `{MAX_EPISODES_PER_BATCH}` | `3` |
| `{FINAL_EPISODE_NUMBER}` | `10` (or leave blank for open-ended) |
| `{EPISODE}` | `episode_07` |
| `{EXPORT_PATH}` | `examples/phone_from_tomorrow/episode_07/assets/exports/episode_07_vertical.mp4` |

---

## Example filled prompt (minimal)

```text
Series directory: examples/phone_from_tomorrow
Series title: The Phone That Receives Tomorrow
Style template: thriller_mystery
Max episodes per batch: 2
Final episode number: 10

Produce episodes 8 and 9. Follow all batch rules in docs/AI_BATCH_PROMPT.md.
Run the pipeline after writing content files. Verify with ffprobe. Send batch notification when done.
```

---

## Tips

- Write `scenes.json` before running the pipeline — the pipeline does not generate story content
- Reuse `continuity_notes` and `characters` from earlier episodes for visual consistency
- See [COVER_STYLE.md](COVER_STYLE.md) for per-episode cover fields in `scenes.json`
- For weekly planning prompts, see [WEEKLY_PIPELINE.md](WEEKLY_PIPELINE.md)
