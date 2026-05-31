# How to Get Your API Keys

Storyforge needs two keys to produce a finished episode, plus two optional ones.
Add each value to `.env.story.local` (copied from `.env.story.example` by `./setup.sh`).
**Never commit `.env.story.local` or paste a real key into chat or a screenshot.**

| Key | Required? | What it powers | Cost model |
|-----|-----------|----------------|------------|
| `OPENAI_API_KEY` | **Required** | Scene images + cover backgrounds | Pay-as-you-go per image |
| `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` | **Required** | Narrator voiceover | Monthly character quota |
| `FAL_KEY` | Optional | AI motion clips (instead of free local motion) | Pay-as-you-go per clip |
| `PIPELINE_NOTIFY_EMAIL` + `SMTP_*` | Optional | Email when a render finishes | Free (your own mail provider) |

---

## 1. OpenAI (scene images + cover) — required

1. Create an account at [platform.openai.com/signup](https://platform.openai.com/signup).
2. Open **Settings → Billing** and add a payment method. Image generation is pay-as-you-go; there is no free image API tier.
3. Go to **API keys** → [platform.openai.com/api-keys](https://platform.openai.com/api-keys) → **Create new secret key**.
4. Name the key (e.g. `storyforge-local`) and copy it immediately — OpenAI only shows the full key once.
5. Paste into `.env.story.local`:

   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

6. *(Recommended)* Set a monthly spend limit under **Billing → Limits** so a runaway batch cannot surprise you.

Keep `OPENAI_IMAGE_STRICT=1` (the default) so the pipeline stops on billing/quota errors instead of shipping blank frames.

**Verify:** after saving the key, a dry run that skips image generation should start without an OpenAI error:

```bash
python3 tools/run_episode_pipeline.py \
  --series examples/phone_from_tomorrow \
  --episode episode_01 \
  --skip-voice --skip-images --skip-cover --skip-videos
```

---

## 2. ElevenLabs (voiceover) — required

You need **two values**: an API key and a **voice ID**.

### A. Get your API key

1. Create an account at [elevenlabs.io](https://elevenlabs.io/).
2. Open **Profile → API Keys** (or go to [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)).
3. Click **Create API Key**, copy it, and add to `.env.story.local`:

   ```bash
   ELEVENLABS_API_KEY=your-key-here
   ```

### B. Get your voice ID

Pick **one** of these methods:

**Method 1 — list voices from the repo (easiest after the API key is set)**

```bash
source .venv/bin/activate   # if you use the project venv
python3 tools/generate_episode_assets.py --list-voices
```

Example output:

```text
Adam: pNInz6obpgDQGcFmaJgB
Rachel: 21m00Tcm4TlvDq8ikWAM
```

Copy the ID after the colon into `.env.story.local`:

```bash
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

**Method 2 — copy from the ElevenLabs web app**

1. In the ElevenLabs app, open **Voices** → **My Voices** (or browse **Voice Library** and add a voice you like).
2. Click the voice you want for narration.
3. Open the voice's **Settings** or **More actions** menu — the **Voice ID** is a long alphanumeric string (often shown in the URL or a copy button).
4. Paste it as `ELEVENLABS_VOICE_ID` in `.env.story.local`.

**Tips**

- Use the **same voice ID across every episode** in a series so narration stays consistent.
- The free tier includes a monthly character allowance — enough to test a few episodes. Upgrade if you batch many episodes per month.
- If voice generation fails with 401/403, recheck the API key. For 422 errors, verify the voice ID and that your text is not empty.

---

## 3. fal.ai (optional — AI motion clips)

By default the pipeline animates still images locally (Ken Burns-style motion) for **zero extra cost**.
Only set this up if you want true AI-generated motion clips.

1. Sign up at [fal.ai](https://fal.ai/).
2. Create a key at [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys).
3. Add it and switch the video mode:

   ```bash
   FAL_KEY=your-fal-key-here
   PIPELINE_VIDEO_MODE=fal
   ```

   (or leave `PIPELINE_VIDEO_MODE=local` and pass `--video-mode fal` per run.)

You'll also need the optional dependency: uncomment `fal-client` in `requirements.txt` and reinstall.

---

## 4. Email notifications (optional)

The pipeline uses **`PIPELINE_NOTIFY_EMAIL`** (who receives mail) plus **`SMTP_*`** (how to send it).

| Variable | Purpose |
|----------|---------|
| `PIPELINE_NOTIFY_EMAIL` | Recipient address (comma-separated for multiple) |
| `SMTP_HOST` | Mail server hostname |
| `SMTP_PORT` | Usually `587` |
| `SMTP_USERNAME` | SMTP login (often your email address) |
| `SMTP_PASSWORD` | SMTP password or app password |
| `SMTP_FROM_EMAIL` | From address shown in the inbox |
| `SMTP_USE_TLS` | `true` for STARTTLS (default) |

Without SMTP configured, notifications are still written to `{series}/notifications/` — you just will not get email.

**Gmail example**

```bash
PIPELINE_NOTIFY_ON_RUN=true
PIPELINE_NOTIFY_EMAIL=you@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM_EMAIL=you@gmail.com
SMTP_USE_TLS=true
```

Use a [Google App Password](https://support.google.com/accounts/answer/185833), not your normal Gmail login password.

**Legacy names (still work, but prefer `SMTP_*`)**

| Old variable | Maps to |
|--------------|---------|
| `EMAIL_RECEIVER` | `PIPELINE_NOTIFY_EMAIL` |
| `EMAIL_SENDER` | `SMTP_USERNAME` / `SMTP_FROM_EMAIL` |
| `EMAIL_PASSWORD` | `SMTP_PASSWORD` |

If you have an older `.env.story.local` with `EMAIL_SENDER` / `EMAIL_PASSWORD` / `EMAIL_RECEIVER`, migrate to the `SMTP_*` + `PIPELINE_NOTIFY_EMAIL` names above when convenient — both sets are read by `tools/send_pipeline_update.py`.

---

## 5. Active series path (`PIPELINE_SERIES_DIR`)

This is not an API key, but you need it for daily runs.

| Folder | Purpose |
|--------|---------|
| `series/` | **Your working series** — scaffold with `init_series.py` |
| `examples/` | **Published demos** shipped in the repo (e.g. phone_from_tomorrow) |

After creating a series:

```bash
python3 tools/init_series.py --name "The Last Signal" --style sci_fi --episodes 5
# Accept setting PIPELINE_SERIES_DIR when prompted, or add manually:
```

```bash
PIPELINE_SERIES_DIR=series/the_last_signal
```

To render the included demo without changing your active series:

```bash
python3 tools/run_episode_pipeline.py --series examples/phone_from_tomorrow --episode episode_01
```

---

## Security checklist

- [ ] `.env.story.local` is listed in `.gitignore` (it is, by default).
- [ ] You never pasted a real key into a commit, screenshot, or chat.
- [ ] Spend limits are set on OpenAI (and fal.ai if used).
- [ ] If a key ever leaks, **rotate it immediately** in the provider dashboard.

Run `git status` before every push — if you ever see `.env.story.local` staged, unstage it and check your `.gitignore`.
