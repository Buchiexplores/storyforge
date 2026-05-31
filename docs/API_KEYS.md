# How to Get Your API Keys

Storyforge needs two keys to produce a finished episode, plus two optional ones.
Add each value to `.env.story.local` (copied from `.env.story.example` by `./setup.sh`).
**Never commit `.env.story.local` or paste a real key into chat or a screenshot.**

| Key | Required? | What it powers | Cost model |
|-----|-----------|----------------|------------|
| `OPENAI_API_KEY` | **Required** | Scene images + cover backgrounds | Pay-as-you-go per image |
| `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` | **Required** | Narrator voiceover | Monthly character quota |
| `FAL_KEY` | Optional | AI motion clips (instead of free local motion) | Pay-as-you-go per clip |
| `SMTP_*` | Optional | Email notifications when a render finishes | Free (your own mail provider) |

---

## 1. OpenAI (scene images + cover) — required

1. Create an account at <https://platform.openai.com/signup>.
2. Add a payment method under **Billing** (image generation is pay-as-you-go; there is no free tier for the image API).
3. Go to **API keys** → <https://platform.openai.com/api-keys> → **Create new secret key**.
4. Copy the key (starts with `sk-...`) — you only see it once.
5. Paste it into `.env.story.local`:

   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

**Tip:** Set a monthly spend limit under **Billing → Limits** so a runaway batch can't surprise you.
Keep `OPENAI_IMAGE_STRICT=1` (the default) so the pipeline stops on a billing/quota error instead of silently shipping blank frames.

---

## 2. ElevenLabs (voiceover) — required

1. Create an account at <https://elevenlabs.io/>.
2. Open your profile menu → **API Keys** (<https://elevenlabs.io/app/settings/api-keys>) → **Create API Key**.
3. Copy the key into `.env.story.local`:

   ```bash
   ELEVENLABS_API_KEY=your-key-here
   ```

4. Pick a **voice ID**. Either:
   - Browse the **Voice Library** in the ElevenLabs app, add a voice to *My Voices*, and copy its Voice ID, **or**
   - List the voices available to your account from the repo:

     ```bash
     python3 tools/generate_episode_assets.py --list-voices
     ```

5. Paste the voice ID:

   ```bash
   ELEVENLABS_VOICE_ID=your-voice-id-here
   ```

The free tier includes a monthly character allowance — enough to test a few episodes. Upgrade if you batch many episodes per month.

---

## 3. fal.ai (optional — AI motion clips)

By default the pipeline animates still images locally (Ken Burns-style motion) for **zero extra cost**.
Only set this up if you want true AI-generated motion clips.

1. Sign up at <https://fal.ai/>.
2. Create a key at <https://fal.ai/dashboard/keys>.
3. Add it and switch the video mode:

   ```bash
   FAL_KEY=your-fal-key-here
   PIPELINE_VIDEO_MODE=fal
   ```

   (or leave `PIPELINE_VIDEO_MODE=local` and pass `--video-mode fal` per run.)

You'll also need the optional dependency: uncomment `fal-client` in `requirements.txt` and reinstall.

---

## 4. SMTP (optional — email notifications)

If you want an email when a render finishes or fails, fill in your mail provider's SMTP details.
Without these, the pipeline just writes a notification file into your series `notifications/` folder.

```bash
PIPELINE_NOTIFY_EMAIL=you@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=you@example.com
SMTP_USE_TLS=true
```

**Gmail:** use an [App Password](https://support.google.com/accounts/answer/185833), not your login password.

---

## Security checklist

- [ ] `.env.story.local` is listed in `.gitignore` (it is, by default).
- [ ] You never pasted a real key into a commit, screenshot, or chat.
- [ ] Spend limits are set on OpenAI (and fal.ai if used).
- [ ] If a key ever leaks, **rotate it immediately** in the provider dashboard.

Run `git status` before every push — if you ever see `.env.story.local` staged, unstage it and check your `.gitignore`.
