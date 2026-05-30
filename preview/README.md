# Preview example

`preview/example/` is a **finished sample series** shipped with the repo so anyone can watch the end result of the Storyforge pipeline before setting up API keys or rendering their own episodes.

## What's included

| File | Purpose |
|------|---------|
| `episode_*.mp4` | Six sample vertical episodes |
| `episodes.json` | Episode titles and player metadata |
| `index.html`, `player.css`, `player.js` | Interactive player (Previous / Next, keyboard nav, auto-advance) |

## Where to watch

- **README** — embedded players with next/previous links on the repo home page
- **GitHub Pages** — [https://Buchiexplores.github.io/storyforge/preview/example/](https://Buchiexplores.github.io/storyforge/preview/example/)

## Your own renders

When you run the pipeline, output goes to your episode folder, for example:

```text
examples/phone_from_tomorrow/episode_01/assets/exports/episode_01_vertical.mp4
```

Those files stay local (`**/assets/exports/` is gitignored). The committed sample in `preview/example/` is separate and does not change when you render.
