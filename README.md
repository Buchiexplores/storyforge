# Storyforge

**Turn written short-fiction episodes into vertical videos for TikTok, Instagram Reels, and YouTube Shorts — from your laptop.**

Storyforge is a local production pipeline. You write an episode (a short script + a few scene prompts), and it produces a finished, ready-to-post vertical video:

- 🎙️ ElevenLabs narrator voiceover
- 🖼️ OpenAI scene images
- 🎬 A branded cover/poster intro (AI background + local typography)
- 🎞️ Motion clips from stills — **no video-API credits required** (optional fal.ai motion if you want it)
- 📱 Final synced **1080×1920** vertical MP4, plus a preview grid and image contact sheet

> No timeline editor, no manual rendering. Author text → run one command → get an MP4.

---

## ▶️ Watch example episodes

The sample series **"The Phone That Receives Tomorrow"** (an Afro-futurist mystery thriller) was produced entirely with this pipeline.

**▶ [Watch all 10 episodes in the browser (embedded player)](docs/preview/index.html)** — playable YouTube embeds, no leaving the page.

On GitHub.com, README cover art links out to YouTube (GitHub strips iframe embeds). Click any poster below, or open the [episode viewer](docs/preview/index.html).

<!-- README-PLAYER-START -->

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/Bh6mAgm_QtI"><img src="docs/preview/posters/episode_01.jpg" width="200" alt="Episode 1 · Do Not Open The Door"></a><br>
      <b><a href="https://youtube.com/shorts/Bh6mAgm_QtI">Ep 1 · Do Not Open The Door</a></b>
    </td>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/Y2-6ruKLOF8"><img src="docs/preview/posters/episode_02.jpg" width="200" alt="Episode 2 · The Bus With No Driver"></a><br>
      <b><a href="https://youtube.com/shorts/Y2-6ruKLOF8">Ep 2 · The Bus With No Driver</a></b>
    </td>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/P7XBdPvjcJ8"><img src="docs/preview/posters/episode_03.jpg" width="200" alt="Episode 3 · Save Her Twice"></a><br>
      <b><a href="https://youtube.com/shorts/P7XBdPvjcJ8">Ep 3 · Save Her Twice</a></b>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/DLaWm1o32fY"><img src="docs/preview/posters/episode_04.jpg" width="200" alt="Episode 4 · The Price Of A Minute"></a><br>
      <b><a href="https://youtube.com/shorts/DLaWm1o32fY">Ep 4 · The Price Of A Minute</a></b>
    </td>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/-NcfeG9QFpE"><img src="docs/preview/posters/episode_05.jpg" width="200" alt="Episode 5 · Mara's Name"></a><br>
      <b><a href="https://youtube.com/shorts/-NcfeG9QFpE">Ep 5 · Mara's Name</a></b>
    </td>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/AcZlC_kdeNs"><img src="docs/preview/posters/episode_06.jpg" width="200" alt="Episode 6 · The Street That Disappears"></a><br>
      <b><a href="https://youtube.com/shorts/AcZlC_kdeNs">Ep 6 · The Street That Disappears</a></b>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/L8ZU78CpKuc"><img src="docs/preview/posters/episode_07.jpg" width="200" alt="Episode 7 · The First Owner"></a><br>
      <b><a href="https://youtube.com/shorts/L8ZU78CpKuc">Ep 7 · The First Owner</a></b>
    </td>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/YWWyK7UIfWQ"><img src="docs/preview/posters/episode_08.jpg" width="200" alt="Episode 8 · Battery At One Percent"></a><br>
      <b><a href="https://youtube.com/shorts/YWWyK7UIfWQ">Ep 8 · Battery At One Percent</a></b>
    </td>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/qTONDPdGxa8"><img src="docs/preview/posters/episode_09.jpg" width="200" alt="Episode 9 · Tomorrow Calls Back"></a><br>
      <b><a href="https://youtube.com/shorts/qTONDPdGxa8">Ep 9 · Tomorrow Calls Back</a></b>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <a href="https://youtube.com/shorts/shIX0gKaJDs"><img src="docs/preview/posters/episode_10.jpg" width="200" alt="Episode 10 · Delete My Number"></a><br>
      <b><a href="https://youtube.com/shorts/shIX0gKaJDs">Ep 10 · Delete My Number</a></b>
    </td>
    <td colspan="2"></td>
  </tr>
</table>
<!-- README-PLAYER-END -->

Your own renders land in each episode's `assets/exports/` folder (gitignored — never pushed).

---

## ⚡ Quick start (5 minutes)

```bash
git clone https://github.com/Buchiexplores/storyforge.git
cd storyforge

./setup.sh            # creates .venv, installs deps, copies .env.story.example → .env.story.local
```

Then add your API keys to `.env.story.local`. **New to API keys? Follow [docs/API_KEYS.md](docs/API_KEYS.md)** — it walks you through getting each one.

```bash
# REQUIRED keys (see docs/API_KEYS.md for step-by-step):
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...      # see docs/API_KEYS.md — run: python3 tools/generate_episode_assets.py --list-voices
```

Now choose a path:

### Path A — Render the included example

```bash
python3 tools/run_episode_pipeline.py --series examples/phone_from_tomorrow --episode episode_01
# → examples/phone_from_tomorrow/episode_01/assets/exports/episode_01_vertical.mp4
```

### Path B — Start your own series (interactive wizard)

```bash
python3 tools/init_series.py
```

The 6-step wizard asks for:

1. **Series title** — short name only (becomes the folder slug)
2. **Visual style** — pick from 12 built-in templates
3. **Episode count** — how many `episode_XX` folders to scaffold
4. **Logline** — one-sentence premise
5. **Story description for AI** — characters, world rules, season arc (saved to `story_context.md`)
6. **Folder location** — defaults to `series/<slug>/`

It scaffolds `series_config.yaml`, `series_bible.md`, `story_context.md`, `season_outline.md`, `ai_authoring_brief.md`, and pre-filled episode templates, then prints `file://` clickable links to every file. It offers to set `PIPELINE_SERIES_DIR` and optionally auto-author with OpenAI.

```bash
# Optional: auto-author all scaffolded episodes with OpenAI (needs OPENAI_API_KEY in .env.story.local)
python3 tools/author_series.py --series series/<your_slug>

# Or hand-author episode_01 (scenes.json + voiceover_text.txt) — links are printed by the wizard
# Then render:
python3 tools/run_episode_pipeline.py --series series/<your_slug> --episode episode_01
```

The same `OPENAI_API_KEY` powers scene/cover image generation and optional text authoring via `author_series.py` (chat tokens are billed separately from images).

Prefer flags over prompts?

```bash
python3 tools/init_series.py \
  --name "The Last Signal" \
  --style sci_fi \
  --episodes 5 \
  --logline "A radio operator intercepts messages from a future that hasn't happened yet." \
  --story-context "Mara is a night-shift dispatcher in Lagos. The phone only rings at 2:13 AM..." \
  --auto-author \
  --set-active
```

---

## 🎬 Generate a story, episode by episode

Storyforge is built for serialized content. Add and render one episode at a time:

```bash
# Scaffold the next episode folder (auto-increments: episode_02, episode_03, ...)
python3 tools/new_episode.py --series series/<your_slug>

# Author its scenes.json + voiceover_text.txt, then render:
python3 tools/run_episode_pipeline.py --series series/<your_slug> --episode episode_02
```

Each render also produces a cover, a preview grid, and an image contact sheet so you can review before posting.

**Auto-author episodes with OpenAI** (after scaffolding):

```bash
python3 tools/author_series.py --series series/<your_slug>           # all placeholder episodes
python3 tools/author_series.py --series series/<your_slug> --from 3  # resume from episode 3
python3 tools/author_series.py --series series/<your_slug> --force   # regenerate authored episodes
```

Writes `script.md`, `voiceover_text.txt`, `voice_direction.md`, `visual_prompts.md`, `scenes.json`, `upload_package.md`, and updates `authoring_state.json` for continuity across episodes.

### 🤖 Or automate it — a new episode every morning

Pre-author several episodes, then let cron render the next pending one daily and email you when it's done:

```bash
# Renders the lowest-numbered episode that has content but no video yet
python3 tools/run_next_episode.py
```

```cron
# crontab -e — every morning at 7:00
0 7 * * * cd /absolute/path/to/storyforge && .venv/bin/python tools/run_next_episode.py >> /tmp/storyforge.log 2>&1
```

Full setup (SMTP/email + cron tips): **[docs/GETTING_STARTED.md → Automate it](docs/GETTING_STARTED.md#7-automate-it-daily-cron--email)**.

---

## ✍️ Authoring an episode

Every episode folder needs two files to render: `scenes.json` and `voiceover_text.txt`. The `init_series.py` wizard pre-fills starter templates for every scaffolded episode — replace the placeholders before rendering, or let OpenAI do it for you.

**Three paths:**

| Path | Tool | Best for |
|------|------|----------|
| Auto-author | `author_series.py` | Fast first draft of all episodes; sequential continuity |
| Manual | Edit scaffold files | Full creative control |
| External AI | [AI_BATCH_PROMPT.md](docs/AI_BATCH_PROMPT.md) | Claude/ChatGPT batch workflows with custom prompts |

| File | Required to render | What it is |
|------|-------------------|------------|
| `scenes.json` | ✅ | Scene list (caption + visual prompt per beat) and cover settings |
| `voiceover_text.txt` | ✅ | The exact narration ElevenLabs will speak |
| `script.md`, `voice_direction.md`, `visual_prompts.md`, `upload_package.md` | optional | Authoring notes + publishing copy (auto-written by `author_series.py`) |

Full guide with examples: **[docs/STORY_AUTHORING.md](docs/STORY_AUTHORING.md)**.

---

## 🧰 What you need

| Requirement | Purpose | How to get it |
|-------------|---------|---------------|
| Python 3.10+ | Run the pipeline | [python.org](https://www.python.org/downloads/) |
| ffmpeg + ffprobe | Video rendering | `./setup.sh` auto-detects paths; offers `brew install ffmpeg` on macOS |
| OpenAI API key | Scene images & covers | [docs/API_KEYS.md](docs/API_KEYS.md) |
| ElevenLabs key + voice ID | Narrator voiceover | [docs/API_KEYS.md](docs/API_KEYS.md) |
| fal.ai key *(optional)* | AI motion clips | [docs/API_KEYS.md](docs/API_KEYS.md) |

---

## 📁 Repository layout

```text
storyforge/
  .env.story.example          # Config template (copied to .env.story.local by setup.sh)
  config/style_templates/     # Reusable visual + platform style presets
  docs/                       # Onboarding & reference docs (start with GETTING_STARTED.md)
  docs/preview/               # Embedded YouTube episode viewer (index.html)
  series/                     # Your working series (init_series.py scaffolds here)
  examples/phone_from_tomorrow/  # Published demo series for the repo (Episodes 1–10)
  templates/                  # Scaffolding templates for new series/episodes
  tools/                      # Pipeline CLI (init_series, author_series, new_episode, run, run_next_episode, render, generate)
```

---

## 📚 Documentation

- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** — install, configure, first render, batch workflow
- **[docs/API_KEYS.md](docs/API_KEYS.md)** — how to obtain every API key, step by step
- **[docs/STORY_AUTHORING.md](docs/STORY_AUTHORING.md)** — write scripts, `scenes.json`, style templates
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** — all environment variables and series config
- **[docs/PLATFORM_GUIDE.md](docs/PLATFORM_GUIDE.md)** — TikTok, Reels, and Shorts publishing
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — common failures and fixes
- **[docs/AI_BATCH_PROMPT.md](docs/AI_BATCH_PROMPT.md)** — AI-assisted episode writing
- **[docs/WEEKLY_PIPELINE.md](docs/WEEKLY_PIPELINE.md)** — a weekly production cadence

---

## 🧪 Pipeline flags (cheat sheet)

```bash
python3 tools/run_episode_pipeline.py --series series/my_series --episode episode_01 [flags]
```

| Flag | Effect |
|------|--------|
| `--force` | Regenerate images, cover, and motion clips |
| `--skip-voice` / `--skip-images` / `--skip-cover` / `--skip-videos` / `--skip-render` | Skip a stage |
| `--video-mode fal` | Use fal.ai motion (needs `FAL_KEY`) |
| `--no-notify` | Disable run notifications |

Render-only (no API calls): `--skip-voice --skip-images --skip-cover --skip-videos`

---

## 🤝 Contributing

Contributions are welcome for **pipeline tools**, **documentation**, and **style templates**. Keep your personal stories in local `series/` — do not submit them in PRs.

### Ways to help

| Area | What to contribute | Where |
|------|-------------------|-------|
| **Bugs & ideas** | Repro steps, feature requests, render failures | [GitHub Issues](https://github.com/Buchiexplores/storyforge/issues) |
| **Pipeline tools** | Render fixes, new CLI flags, automation | `tools/` |
| **Scaffolding & authoring** | `init_series.py`, `author_series.py`, `new_episode.py`, templates | `tools/`, `templates/` |
| **Docs** | Onboarding, troubleshooting, platform tips | `docs/` |
| **Style templates** | New visual/platform presets | `config/style_templates/` |
| **AI providers & models** | New/back-end integrations for text, image, voice, motion | `tools/generate_episode_assets.py`, `tools/author_series.py` |

You do **not** need API keys to improve docs, templates, or Python tooling. Keys are only required to test a full render locally.

### Development setup

```bash
git clone https://github.com/Buchiexplores/storyforge.git
cd storyforge
git checkout -b your-branch-name

./setup.sh
# Add keys to .env.story.local for render testing — never commit this file
```

Smoke-test a change without spending API credits (uses the bundled example series):

```bash
python3 tools/run_episode_pipeline.py \
  --series examples/phone_from_tomorrow --episode episode_01 \
  --skip-voice --skip-images --skip-cover --skip-videos
```

Test scaffolding without touching your working series or invoking OpenAI:

```bash
python3 tools/init_series.py \
  --name "Test Series" --style sci_fi --episodes 1 \
  --output-dir /tmp \
  --no-auto-author
```

### Contributing to pipeline tools

| Tool | Purpose |
|------|---------|
| `init_series.py` | Interactive or flag-driven series scaffold |
| `author_series.py` | OpenAI batch authoring for scaffolded episodes |
| `new_episode.py` | Add the next episode folder to an existing series |
| `run_episode_pipeline.py` | Full episode pipeline (voice → images → cover → motion → render) |
| `run_next_episode.py` | Render the next pending episode (automation/cron) |
| `generate_episode_assets.py` | Standalone asset generation stages |
| `render_episode.py` | FFmpeg render from existing assets |
| `send_pipeline_update.py` | Email/notification helper |

Before opening a PR:

- [ ] Smoke test with skip flags (see above) or run the specific tool you changed
- [ ] Keep changes focused on one tool or concern
- [ ] Update docs if CLI flags or behavior changed
- [ ] Do not commit `series/`, `.env.story.local`, or generated `assets/` media


### Contributing AI provider integrations

Storyforge today ships with opinionated defaults (OpenAI images, ElevenLabs voice, local ffmpeg motion). **We welcome PRs that add alternative providers** — especially open-source and local backends — without breaking existing workflows.

| Pipeline stage | Current providers | Contribution ideas |
|----------------|-------------------|-------------------|
| **Text authoring** (`author_series.py`) | OpenAI chat (`OPENAI_TEXT_MODEL`) | Anthropic, Google Gemini, Ollama/LM Studio, OpenRouter, local GGUF |
| **Scene images** (`generate_episode_assets.py`) | `openai`, `fal`, `local` via `--image-provider` | ComfyUI, Stable Diffusion / SDXL, Replicate, Together, local diffusers |
| **Cover backgrounds** | `openai`, `fal`, `local` via `--cover-provider` | Same image backends as scene images |
| **Voice** (`generate_episode_assets.py`) | ElevenLabs only | Piper, Coqui TTS, Bark, OpenAI TTS, Azure Speech, local XTTS |
| **Video motion** | `local` (ffmpeg Ken Burns, **default, zero API cost**) or `fal` via `--video-mode fal` / `--local-videos` | Runway, Pika, Luma, AnimateDiff, Deforum, more ffmpeg presets |

**How to add a provider:**

1. Follow the existing switch pattern — see `--image-provider`, `--cover-provider`, and `--video-mode` in `tools/generate_episode_assets.py` and `tools/run_episode_pipeline.py`.
2. Keep **OpenAI + ElevenLabs + local motion** as defaults so current users are unaffected.
3. Gate optional dependencies — comment new packages in `requirements.txt` (like `fal-client` today).
4. Document new env vars and flags in [docs/CONFIGURATION.md](docs/CONFIGURATION.md).
5. Add a `--skip-*` path or mock so contributors can smoke-test without every API key.

**Motion note:** Local ffmpeg Ken Burns is the zero-cost default (`PIPELINE_VIDEO_MODE=local`). fal.ai motion is optional. PRs for additional motion backends (cloud or local) are especially welcome — the pipeline already falls back to local motion when fal fails.

Open a [GitHub Issue](https://github.com/Buchiexplores/storyforge/issues) first if you are planning a large provider refactor; small, focused provider PRs can go straight to draft PR.

### Pull request guidelines

1. **Tooling PRs only** — pipeline code, docs, templates, and style presets. Do not submit personal series content.
2. **Never commit secrets** — `.env.story.local`, API keys, or voice IDs.
3. **Do not commit generated media** — MP4s, scene PNGs, voiceover WAVs, and covers under `assets/` are gitignored on purpose.
4. **Keep PRs focused** — one fix or feature per PR when possible.
5. **Say what you tested** — e.g. "smoke-tested with skip flags" or "docs-only change".
6. **`examples/` is maintainer-maintained** — the demo series and README viewer are updated by project maintainers, not community PRs.

### Questions before you start?

Open a [GitHub Issue](https://github.com/Buchiexplores/storyforge/issues) with the **question** label, or describe your idea in a draft PR. No contribution is too small — typo fixes and clearer error messages count.

---

## License

MIT — see [LICENSE](LICENSE). The example story and characters are original works included for demonstration.
