# Platform Publishing Guide

How to publish to **TikTok**, **Instagram Reels**, and **YouTube Shorts**.

- [GETTING_STARTED.md](GETTING_STARTED.md) — produce the export
- [STORY_AUTHORING.md](STORY_AUTHORING.md) — `upload_package.md`

---

## Video specifications

| Spec | Value |
|------|-------|
| Resolution | **1080 × 1920** (9:16) |
| Frame rate | **30 fps** |
| Codecs | H.264 + AAC |
| Container | MP4 |
| Duration | ~60–90s + ~2.5s cover intro |

Export: `{series}/{episode}/assets/exports/{output_slug}_vertical.mp4`

Review assets: `{slug}_cover.png`, `{slug}_preview_grid.jpg`, `{slug}_image_contact_sheet.jpg`

---

## Fiction disclosure

Always label content as fictional in caption or description. Never imply real events.

**Minimum:** "This is a fictional story."

**AI-assisted:** "Original fictional story with human creative direction and AI-assisted visuals."

Avoid: fake news framing, real disaster footage as fact, missing fiction labels, copyrighted music/logos/public figures.

Style templates include platform disclosures in `config/style_templates/*.yaml`.

---

## `upload_package.md`

Each episode should have ready-to-paste captions. Template: `templates/episode/upload_package.template.md`

Sections: TikTok caption, YouTube title/description, Instagram caption, pinned comment, platform checklist.

Example: `examples/phone_from_tomorrow/episode_01/upload_package.md`

---

## Posting order

Default from `series_config.yaml`:

1. **TikTok** — fastest feedback on hooks
2. **YouTube Shorts** — search and subscriptions
3. **Instagram Reels** — optional third; tweak caption

Same MP4 on all platforms; only metadata changes. Space uploads by a few hours if monitoring TikTok first.

---

## Platform tips

### TikTok

- Hook in first line; disclosure on line 2–3
- 3–6 hashtags (`#fictionstory` + genre tags)
- Pipeline audio includes voice + ambient; avoid copyrighted trending sounds on top

### YouTube Shorts

- Specific title with hook; episode number in description
- 3–5 hashtags in description
- Add to series playlist as you publish

### Instagram Reels

- Conversational caption + disclosure
- Up to ~10 hashtags including `#reelsfiction`
- Share to Stories with "Part 2?" for cliffhangers

---

## Hashtags

Use 3–6 relevant tags. Mix broad (`#fictionstory`, `#storytime`) and genre (`#mysterystory`, `#scifistory`, `#romancedrama`). Keep a consistent core set per series.

Template defaults:

| Style | Examples |
|-------|----------|
| `thriller_mystery` | `#fictionstory` `#mysterystory` `#storytime` |
| `romance_drama` | `#fictionstory` `#romancedrama` `#dramatiktok` |
| `sci_fi` | `#fictionstory` `#scifistory` `#futuristic` |

---

## Pinned comments

Tease the next episode on every platform:

```text
Episode 2: The package was breathing. Should Tobi open the door or wait?
```

---

## Pre-publish checklist

- [ ] Fiction disclosure in caption/description
- [ ] AI disclosure if platform asks
- [ ] Not presented as a real event
- [ ] Royalty-free audio only
- [ ] 1080×1920 MP4 from `assets/exports/`
- [ ] Full watch-through — hook, captions, cliffhanger
- [ ] Pinned comment ready

Weekly compilations: see [WEEKLY_PIPELINE.md](WEEKLY_PIPELINE.md).
