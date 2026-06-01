#!/usr/bin/env python3
import argparse
import base64
import json
import os
import random
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from pipeline_config import (
    ROOT,
    ENV_PATH,
    episode_output_slug,
    get_series_dir,
    load_local_env,
    merged_series_settings,
    resolve_episode_path,
)

from cover_styles import (
    compose_cover,
    cover_background_prompt,
    font_candidates,
    fit_font,
    load_font,
    resolve_cover_style_id,
)


try:
    SERIES_DIR = get_series_dir()
except SystemExit:
    SERIES_DIR = ROOT / "series" / "_unconfigured"
EPISODE = SERIES_DIR / "episode_01"
SCENES_PATH = EPISODE / "scenes.json"
VOICE_TEXT_PATH = EPISODE / "voiceover_text.txt"
VOICE_OUT = EPISODE / "assets" / "voiceover" / "voiceover_episode_01.mp3"
IMAGES_DIR = EPISODE / "assets" / "images"
VIDEOS_DIR = EPISODE / "assets" / "video"
EXPORTS_DIR = EPISODE / "assets" / "exports"


def configure_series(value=None):
    global SERIES_DIR
    SERIES_DIR = get_series_dir(value)


def configure_episode(value):
    global EPISODE, SCENES_PATH, VOICE_TEXT_PATH, VOICE_OUT, IMAGES_DIR, VIDEOS_DIR, EXPORTS_DIR
    EPISODE = resolve_episode_path(value, SERIES_DIR)
    SCENES_PATH = EPISODE / "scenes.json"
    VOICE_TEXT_PATH = EPISODE / "voiceover_text.txt"
    slug = episode_output_slug(EPISODE)
    VOICE_OUT = EPISODE / "assets" / "voiceover" / f"voiceover_{slug}.mp3"
    IMAGES_DIR = EPISODE / "assets" / "images"
    VIDEOS_DIR = EPISODE / "assets" / "video"
    EXPORTS_DIR = EPISODE / "assets" / "exports"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing {name}. Add it to {ENV_PATH}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def first_existing(paths):
    for path in paths:
        if path and Path(path).exists():
            return str(path)
    return None


def find_binary(name, env_name, candidates):
    env_path = os.getenv(env_name)
    found = first_existing([env_path, *candidates])
    if found:
        return found
    system = shutil.which(name)
    if system:
        return system
    raise SystemExit(f"Could not find {name}. Set {env_name} in {ENV_PATH}.")


def run(cmd):
    print(" ".join(str(part) for part in cmd))
    subprocess.run(cmd, check=True)


def notify_openai_generation_failure(asset_kind: str, asset_id: str, exc: Exception):
    notifications_dir = SERIES_DIR / "notifications"
    notifications_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    body_path = notifications_dir / f"{stamp}_openai_generation_blocked.md"
    episode_name = EPISODE.name
    body = textwrap.dedent(
        f"""\
        OpenAI/ChatGPT image generation is blocked for `{episode_name}`.

        Failed asset:
        - Type: {asset_kind}
        - ID: {asset_id}

        Error:
        ```text
        {exc}
        ```

        The pipeline did not create local storyboard art or non-ChatGPT fallback images.
        Add usable OpenAI image-generation credit or lift the billing/quota limit for the active `OPENAI_API_KEY`, then rerun the episode generation.
        """
    )
    body_path.write_text(body, encoding="utf-8")
    notify_script = ROOT / "tools" / "send_pipeline_update.py"
    subject = f"{episode_name} blocked: OpenAI image generation"
    try:
        subprocess.run(
            [
                sys.executable,
                str(notify_script),
                "--subject",
                subject,
                "--body-file",
                str(body_path),
                "--series-dir",
                str(SERIES_DIR),
            ],
            check=False,
        )
    except Exception as notify_exc:
        print(f"Could not send or queue notification: {notify_exc}")


def list_voices():
    api_key = require_env("ELEVENLABS_API_KEY")
    resp = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key},
        timeout=60,
    )
    if not resp.ok:
        raise SystemExit(f"ElevenLabs voice list failed: {resp.status_code} {resp.text}")
    data = resp.json()
    for voice in data.get("voices", []):
        print(f"{voice.get('name')}: {voice.get('voice_id')}")


def generate_voice():
    api_key = require_env("ELEVENLABS_API_KEY")
    voice_id = require_env("ELEVENLABS_VOICE_ID")
    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    output_format = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
    text = VOICE_TEXT_PATH.read_text(encoding="utf-8").strip()
    VOICE_OUT.parent.mkdir(parents=True, exist_ok=True)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    resp = requests.post(
        url,
        params={"output_format": output_format},
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.75,
                "style": 0.25,
                "use_speaker_boost": True,
            },
        },
        timeout=180,
    )
    if not resp.ok:
        raise SystemExit(f"ElevenLabs TTS failed: {resp.status_code} {resp.text}")

    VOICE_OUT.write_bytes(resp.content)
    print(f"Wrote {VOICE_OUT}")


def find_first_url(value):
    if isinstance(value, str) and value.startswith("http"):
        return value
    if isinstance(value, list):
        for item in value:
            found = find_first_url(item)
            if found:
                return found
    if isinstance(value, dict):
        for key in ("url", "image_url", "video_url"):
            found = find_first_url(value.get(key))
            if found:
                return found
        for item in value.values():
            found = find_first_url(item)
            if found:
                return found
    return None


def download_url(url: str, path: Path):
    resp = requests.get(url, timeout=180)
    if not resp.ok:
        raise SystemExit(f"Download failed: {resp.status_code} {url}")
    path.write_bytes(resp.content)


def openai_image_b64(result):
    data = getattr(result, "data", None)
    if data is None and isinstance(result, dict):
        data = result.get("data")
    if not data:
        return None
    first = data[0]
    if isinstance(first, dict):
        return first.get("b64_json")
    return getattr(first, "b64_json", None)


def character_continuity_prompt(scenes_data):
    notes = scenes_data.get("continuity_notes")
    characters = scenes_data.get("characters", [])
    parts = []
    if notes:
        parts.append(str(notes).strip())
    for character in characters:
        name = character.get("name")
        description = character.get("description")
        if name and description:
            parts.append(f"{name}: {description}")
    if parts:
        return " ".join(parts)
    return (
        "Maintain consistent character appearance, wardrobe, props, and setting details "
        "across all scenes in this episode. Add continuity_notes or characters to scenes.json "
        "for stronger series consistency."
    )


def image_prompt_rules(scenes_data):
    if scenes_data.get("image_prompt_rules"):
        return str(scenes_data["image_prompt_rules"]).strip()
    settings = merged_series_settings(SERIES_DIR)
    return str(settings.get("image_prompt_rules", "")).strip()


def openai_scene_prompt(style, scene, continuity, scenes_data):
    rules = image_prompt_rules(scenes_data)
    prompt = (
        "Use case: illustration-story\n"
        "Asset type: vertical 9:16 short-form fiction frame for TikTok, Instagram Reels, and YouTube Shorts\n"
        f"Series style: {style}.\n"
        f"Character and prop continuity: {continuity}\n"
        f"Exact narration beat to visualize: {scene.get('caption', '')}\n"
        f"Scene direction: {scene['prompt']}\n"
        "Composition requirements: one clear cinematic moment that directly matches this exact "
        "narration beat; vertical portrait composition; emotionally readable subject; strong "
        "foreground/midground/background depth.\n"
        "Continuity requirements: keep characters, props, and setting consistent with the series bible. "
        "Do not add unrelated characters or props.\n"
        "Text requirements: no subtitles, no captions, no title cards, no watermarks, no logos, "
        "no readable brand names unless the scene direction explicitly asks for on-screen text."
    )
    if rules:
        prompt += f"\nSeries-specific rules:\n{rules}"
    return prompt




def generate_openai_image(scene, style, continuity, out_path: Path, scenes_data=None):
    require_env("OPENAI_API_KEY")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "Missing openai package. Run: python3 -m pip install --user openai"
        ) from exc

    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
    size = os.getenv("OPENAI_IMAGE_SIZE", "1024x1536")
    quality = os.getenv("OPENAI_IMAGE_QUALITY", "high")
    timeout = float(os.getenv("OPENAI_IMAGE_TIMEOUT_SECONDS", "180"))
    client = OpenAI(timeout=timeout)
    prompt = openai_scene_prompt(style, scene, continuity, scenes_data or {})

    result = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        output_format="png",
        n=1,
    )
    image_b64 = openai_image_b64(result)
    if not image_b64:
        raise RuntimeError(f"No base64 image found in OpenAI result for {scene['id']}: {result}")
    out_path.write_bytes(base64.b64decode(image_b64))
    print(f"Wrote OpenAI image {out_path} ({model}, {size}, {quality})")


def add_thriller_texture(image: Image.Image, seed: int):
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rng = random.Random(seed)

    for _ in range(170):
        x = rng.randint(-80, width + 70)
        y = rng.randint(0, height)
        length = rng.randint(26, 96)
        alpha = rng.randint(24, 88)
        draw.line((x, y, x + 12, y + length), fill=(145, 226, 220, alpha), width=1)

    for _ in range(900):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        alpha = rng.randint(6, 18)
        draw.point((x, y), fill=(255, 255, 255, alpha))

    draw.rectangle((0, 0, width, int(height * 0.18)), fill=(0, 0, 0, 90))
    draw.rectangle((0, int(height * 0.77), width, height), fill=(0, 0, 0, 125))
    draw.rectangle((0, 0, 84, height), fill=(0, 0, 0, 118))
    draw.rectangle((width - 84, 0, width, height), fill=(0, 0, 0, 118))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def make_storyboard_base():
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height), "#071012")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / height
        r = int(4 + 24 * t)
        g = int(13 + 12 * (1 - abs(t - 0.58)))
        b = int(16 + 9 * (1 - t))
        draw.line((0, y, width, y), fill=(r, g, b))
    return image


def draw_glow_ellipse(image, box, color=(0, 255, 96), alpha=150, blur=38):
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(box, fill=(*color, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(blur))
    image.alpha_composite(glow)


def draw_glow_rect(image, box, color=(0, 255, 96), alpha=125, blur=24):
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(box, radius=26, fill=(*color, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(blur))
    image.alpha_composite(glow)


def draw_fitted_text(draw, text, box, max_size, min_size, fill, kind="block", stroke_width=0, align="center"):
    x1, y1, x2, y2 = box
    max_width = x2 - x1
    max_height = y2 - y1
    words = text.split()
    for size in range(max_size, min_size - 1, -2):
        font = load_font(size, font_candidates(kind))
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            text_box = draw.textbbox((0, 0), candidate, font=font, stroke_width=stroke_width)
            if text_box[2] - text_box[0] <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        line_height = int(size * 1.18)
        total_height = line_height * len(lines)
        widest = max((draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)[2] for line in lines), default=0)
        if total_height <= max_height and widest <= max_width:
            y = y1 + (max_height - total_height) / 2
            for line in lines:
                text_box = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
                line_width = text_box[2] - text_box[0]
                if align == "left":
                    x = x1
                else:
                    x = x1 + (max_width - line_width) / 2
                draw.text((x, y), line, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=(0, 0, 0, 220))
                y += line_height
            return
    font = load_font(min_size, font_candidates(kind))
    draw.text((x1, y1), text[:72], font=font, fill=fill, stroke_width=stroke_width, stroke_fill=(0, 0, 0, 220))


def draw_phone(image, center, size, tilt=0, screen_fill=(7, 18, 16), glow=True):
    width, height = size
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = center
    x1 = int(cx - width / 2)
    y1 = int(cy - height / 2)
    x2 = int(cx + width / 2)
    y2 = int(cy + height / 2)
    if glow:
        draw_glow_rect(image, (x1 + 25, y1 + 45, x2 - 25, y2 - 45), alpha=105, blur=34)
    draw.rounded_rectangle((x1, y1, x2, y2), radius=48, fill=(9, 11, 11, 255), outline=(56, 61, 58, 255), width=8)
    screen = (x1 + 44, y1 + 70, x2 - 44, y2 - 88)
    draw.rounded_rectangle(screen, radius=30, fill=(*screen_fill, 255), outline=(0, 170, 75, 150), width=4)
    draw.ellipse((cx - 18, y2 - 62, cx + 18, y2 - 26), fill=(18, 23, 23, 255), outline=(55, 70, 65, 255), width=2)
    rng = random.Random(width + height)
    for _ in range(9):
        sx = rng.randint(screen[0] + 20, screen[2] - 20)
        sy = rng.randint(screen[1] + 20, screen[3] - 20)
        ex = sx + rng.randint(-95, 95)
        ey = sy + rng.randint(-95, 95)
        draw.line((sx, sy, ex, ey), fill=(175, 255, 218, rng.randint(80, 145)), width=2)
    if tilt:
        layer = layer.rotate(tilt, resample=Image.Resampling.BICUBIC, center=center)
    image.alpha_composite(layer)
    return screen


def draw_message_screen(image, header, message, time_text=None, door_hint=False):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    if door_hint:
        draw_door_shape(draw, (690, 250, 1020, 1320), shadow=True)
    screen = draw_phone(image, (540, 950), (660, 1060), tilt=-4, screen_fill=(3, 22, 16))
    draw = ImageDraw.Draw(image)
    header_font = load_font(44, font_candidates("block"))
    small_font = load_font(31, font_candidates("block"))
    draw.text((screen[0] + 42, screen[1] + 36), header, font=header_font, fill=(225, 255, 235, 255))
    draw.line((screen[0] + 28, screen[1] + 104, screen[2] - 28, screen[1] + 104), fill=(0, 210, 89, 130), width=3)
    if time_text:
        big = fit_font(time_text, screen[2] - screen[0] - 90, 142, 92, "impact")
        text_box = draw.textbbox((0, 0), time_text, font=big)
        draw.text(((1080 - (text_box[2] - text_box[0])) / 2, screen[1] + 245), time_text, font=big, fill=(238, 255, 244, 255), stroke_width=2, stroke_fill=(0, 70, 30, 255))
    bubble = (screen[0] + 52, screen[1] + 190, screen[2] - 52, screen[1] + 520)
    draw.rounded_rectangle(bubble, radius=34, fill=(0, 130, 64, 235), outline=(69, 255, 129, 190), width=4)
    draw_fitted_text(draw, message, (bubble[0] + 34, bubble[1] + 28, bubble[2] - 34, bubble[3] - 26), 52, 31, (245, 255, 249, 255), "block", stroke_width=1)
    draw.text((screen[0] + 58, bubble[3] + 28), "Unknown delivery thread", font=small_font, fill=(124, 210, 156, 190))
    return image.convert("RGB")


def draw_door_shape(draw, box, shadow=False):
    x1, y1, x2, y2 = box
    draw.rectangle((x1, y1, x2, y2), fill=(81, 43, 21, 255), outline=(177, 102, 44, 255), width=8)
    draw.rectangle((x1 + 42, y1 + 72, x2 - 42, y1 + 450), outline=(128, 72, 36, 255), width=7)
    draw.rectangle((x1 + 42, y1 + 505, x2 - 42, y2 - 70), outline=(128, 72, 36, 255), width=7)
    draw.ellipse((x2 - 82, y1 + 690, x2 - 40, y1 + 732), fill=(221, 151, 56, 255))
    if shadow:
        draw.ellipse((x1 + 70, y1 + 185, x2 - 70, y1 + 655), fill=(0, 0, 0, 95))
        draw.rectangle((x1 + 145, y1 + 460, x2 - 145, y2 - 125), fill=(0, 0, 0, 85))


def draw_tobi(draw, x, y, scale=1.0, phone=False, fear=False):
    skin = (83, 46, 29, 255)
    shirt = (31, 53, 49, 255)
    outline = (2, 7, 8, 255)
    head_r = int(70 * scale)
    draw.ellipse((x - head_r, y - head_r * 2, x + head_r, y), fill=skin, outline=outline, width=max(2, int(4 * scale)))
    draw.arc((x - 35 * scale, y - 58 * scale, x - 5 * scale, y - 38 * scale), 0, 180, fill=(230, 230, 210, 255), width=max(2, int(3 * scale)))
    draw.arc((x + 5 * scale, y - 58 * scale, x + 35 * scale, y - 38 * scale), 0, 180, fill=(230, 230, 210, 255), width=max(2, int(3 * scale)))
    mouth_y = y - int(24 * scale)
    if fear:
        draw.arc((x - 28 * scale, mouth_y - 8, x + 28 * scale, mouth_y + 28), 185, 355, fill=(235, 230, 220, 255), width=max(2, int(3 * scale)))
    else:
        draw.arc((x - 30 * scale, mouth_y - 14, x + 30 * scale, mouth_y + 20), 15, 165, fill=(235, 230, 220, 255), width=max(2, int(4 * scale)))
    torso = [
        (x - 115 * scale, y + 22 * scale),
        (x + 115 * scale, y + 22 * scale),
        (x + 160 * scale, y + 420 * scale),
        (x - 160 * scale, y + 420 * scale),
    ]
    draw.polygon(torso, fill=shirt, outline=outline)
    if phone:
        draw.rounded_rectangle((x + 66 * scale, y + 120 * scale, x + 165 * scale, y + 292 * scale), radius=int(13 * scale), fill=(5, 18, 14, 255), outline=(0, 245, 94, 210), width=max(2, int(3 * scale)))
        draw.rectangle((x + 79 * scale, y + 145 * scale, x + 152 * scale, y + 260 * scale), fill=(0, 105, 52, 255))


def draw_package(draw, box, breathing=False):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=(156, 103, 58, 255), outline=(231, 177, 106, 255), width=5)
    draw.line((x1 + 18, y1 + 66, x2 - 18, y1 + 66), fill=(98, 57, 29, 200), width=5)
    draw.line(((x1 + x2) / 2, y1 + 6, (x1 + x2) / 2, y2 - 6), fill=(105, 61, 31, 210), width=5)
    draw.rectangle((x1 + 60, y1 + 96, x2 - 60, y1 + 190), fill=(185, 148, 98, 235))
    if breathing:
        for i in range(4):
            pad = 18 + i * 20
            draw.arc((x1 - pad, y1 - pad, x2 + pad, y2 + pad), 205, 335, fill=(40, 255, 112, 90 - i * 14), width=4)


def draw_bed_phone_scene(image):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 1120, 1080, 1920), fill=(25, 23, 24, 255))
    draw.rounded_rectangle((180, 610, 900, 1220), radius=70, fill=(42, 40, 42, 255))
    draw.rounded_rectangle((250, 710, 820, 1075), radius=65, fill=(177, 177, 166, 255))
    draw_glow_ellipse(image, (348, 762, 774, 1114), alpha=148, blur=50)
    draw.rounded_rectangle((388, 910, 715, 1058), radius=32, fill=(8, 12, 12, 255), outline=(0, 240, 92, 180), width=6)
    draw.rectangle((430, 948, 672, 1024), fill=(0, 184, 78, 230))
    for dx in (-55, -25, 25, 55):
        draw.arc((330 + dx, 850, 760 + dx, 1110), 305, 55, fill=(0, 255, 100, 105), width=5)
    return image.convert("RGB")


def draw_tobi_bed_scene(image, fear=False, bag=False):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 1130, 1080, 1920), fill=(24, 22, 24, 255))
    draw.rectangle((130, 720, 950, 1390), fill=(51, 42, 37, 255))
    draw.rounded_rectangle((180, 665, 500, 850), radius=45, fill=(178, 172, 155, 255))
    if bag:
        draw.rounded_rectangle((205, 1085, 875, 1425), radius=42, fill=(46, 44, 38, 255), outline=(111, 93, 61, 255), width=7)
        draw.rectangle((250, 1135, 420, 1325), fill=(131, 93, 56, 255))
        draw.rectangle((605, 1125, 820, 1335), fill=(158, 120, 74, 255))
        draw_glow_rect(image, (430, 1100, 620, 1355), alpha=150, blur=38)
        draw_phone(image, (525, 1226), (182, 318), tilt=5, glow=False)
    else:
        draw_tobi(draw, 540, 805, scale=1.35, phone=True, fear=fear)
        draw_glow_ellipse(image, (505, 855, 820, 1305), alpha=95, blur=54)
    return image.convert("RGB")


def draw_lagos_scene(image, sounds=False):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 1040, 1080, 1920), fill=(28, 31, 31, 255))
    for y in range(1040, 1920, 70):
        draw.line((0, y, 1080, y + 110), fill=(48, 54, 52, 120), width=5)
    draw.rectangle((50, 530, 360, 1055), fill=(40, 38, 32, 255))
    draw.rectangle((710, 450, 1020, 1055), fill=(34, 39, 38, 255))
    for x in (105, 190, 770, 875):
        draw.rectangle((x, 610, x + 55, 745), fill=(239, 170, 69, 170))
    for i, x in enumerate((150, 470, 760)):
        y = 1110 + i * 70
        draw.rounded_rectangle((x, y, x + 270, y + 155), radius=30, fill=(223, 156, 43, 255), outline=(28, 20, 12, 255), width=4)
        draw.rectangle((x + 34, y + 24, x + 236, y + 74), fill=(35, 50, 50, 255))
        draw.ellipse((x + 38, y + 123, x + 92, y + 177), fill=(8, 8, 8, 255))
        draw.ellipse((x + 190, y + 123, x + 244, y + 177), fill=(8, 8, 8, 255))
    if sounds:
        draw.rounded_rectangle((74, 1280, 270, 1435), radius=18, fill=(46, 50, 43, 255), outline=(108, 119, 94, 255), width=4)
        draw.ellipse((112, 1317, 188, 1393), outline=(185, 198, 151, 255), width=6)
        for i in range(4):
            draw.ellipse((170 + i * 22, 1110 - i * 40, 360 + i * 70, 1248 - i * 25), fill=(174, 174, 156, 35))
    for x in (130, 510, 840):
        draw.ellipse((x - 105, 1490, x + 165, 1558), fill=(97, 143, 123, 100))
        draw.line((x - 80, 1518, x + 120, 1500), fill=(252, 193, 86, 120), width=5)
    return image.convert("RGB")


def draw_door_scene(image, mara=False, knock=False, time_phone=False, buzz_phone=False):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 1030, 1080, 1920), fill=(24, 25, 24, 255))
    draw_door_shape(draw, (370, 360, 810, 1450), shadow=knock)
    draw.rectangle((0, 380, 260, 1420), fill=(46, 31, 22, 255))
    if mara:
        draw.rectangle((42, 470, 286, 1365), fill=(117, 73, 31, 255))
        draw_tobi(draw, 195, 880, scale=0.9, phone=False, fear=False)
        draw_tobi(draw, 650, 960, scale=1.05, phone=True, fear=True)
    elif knock:
        draw.ellipse((483, 520, 705, 910), fill=(0, 0, 0, 110))
        draw.rectangle((550, 780, 638, 1280), fill=(0, 0, 0, 92))
        draw.line((726, 835, 872, 882), fill=(0, 0, 0, 145), width=18)
        for y in (780, 860, 940):
            draw_glow_ellipse(image, (760, y, 870, y + 110), color=(255, 192, 80), alpha=32, blur=12)
    else:
        draw_tobi(draw, 215, 995, scale=1.1, phone=True, fear=True)
        draw.ellipse((168, 1490, 278, 1548), fill=(12, 10, 9, 255))
        draw.ellipse((304, 1496, 392, 1536), outline=(115, 94, 70, 255), width=8)
    if time_phone:
        return draw_message_screen(image, "7:40 AM", "The exact minute from the warning.", time_text="7:40", door_hint=True)
    if buzz_phone:
        draw_glow_ellipse(image, (385, 840, 720, 1260), alpha=118, blur=46)
        draw_phone(image, (540, 1050), (360, 650), tilt=-8, screen_fill=(0, 90, 42), glow=False)
        for pad in (24, 62, 100):
            draw.arc((358 - pad, 750 - pad, 722 + pad, 1350 + pad), 120, 240, fill=(0, 255, 96, 125 - pad), width=5)
            draw.arc((358 - pad, 750 - pad, 722 + pad, 1350 + pad), 300, 60, fill=(0, 255, 96, 125 - pad), width=5)
    return image.convert("RGB")


def draw_flashback_scene(image):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 1010, 1080, 1920), fill=(30, 33, 34, 255))
    draw.rounded_rectangle((595, 1010, 980, 1205), radius=32, fill=(38, 37, 35, 255), outline=(147, 102, 45, 255), width=5)
    draw.ellipse((635, 1165, 740, 1270), fill=(8, 8, 8, 255))
    draw.ellipse((850, 1165, 955, 1270), fill=(8, 8, 8, 255))
    draw.line((640, 1045, 535, 920), fill=(125, 92, 50, 255), width=12)
    draw_tobi(draw, 390, 830, scale=1.18, phone=False, fear=True)
    draw.line((455, 980, 540, 1070), fill=(83, 46, 29, 255), width=22)
    draw.ellipse((180, 1430, 515, 1500), fill=(86, 134, 116, 80))
    return image.convert("RGB")


def draw_peephole_scene(image):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1080, 1920), fill=(3, 5, 6, 255))
    peephole = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(peephole)
    pd.ellipse((105, 240, 975, 1540), fill=(31, 28, 24, 255), outline=(193, 134, 58, 255), width=12)
    pd.rectangle((280, 1070, 800, 1540), fill=(39, 31, 22, 255))
    draw_tobi(pd, 540, 780, scale=1.15, phone=False, fear=False)
    pd.rounded_rectangle((365, 870, 735, 1130), radius=24, fill=(151, 103, 56, 255), outline=(231, 177, 106, 255), width=5)
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).ellipse((105, 240, 975, 1540), fill=255)
    image.alpha_composite(peephole)
    dark = Image.new("RGBA", image.size, (0, 0, 0, 235))
    dark.putalpha(Image.eval(mask, lambda p: 0 if p else 235))
    image.alpha_composite(dark)
    return image.convert("RGB")


def draw_package_scene(image, peek=False, breathing=False):
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 930, 1080, 1920), fill=(28, 28, 26, 255))
    draw_door_shape(draw, (285, 250, 795, 1230), shadow=False)
    draw_glow_ellipse(image, (315, 1125, 785, 1615), alpha=92, blur=62)
    draw_package(draw, (330, 1200, 750, 1505), breathing=breathing)
    if peek:
        draw.rectangle((250, 250, 335, 1230), fill=(9, 10, 9, 255))
        draw_tobi(draw, 240, 800, scale=0.68, phone=False, fear=True)
    return image.convert("RGB")


def create_storyboard_image(scene, out_path: Path, reason: str = "local storyboard"):
    scene_id = scene["id"]
    image = make_storyboard_base()
    if "phone_buzz" in scene_id or scene_id == "01_phone_under_pillow":
        image = draw_bed_phone_scene(image)
    elif "own_number" in scene_id:
        image = draw_message_screen(image, "My Number", "The message came from his own number.")
    elif "warning_text" in scene_id:
        image = draw_message_screen(image, "My Number", "Do not open your door tomorrow at 7:40 AM.")
    elif "tobi_laughed" in scene_id:
        image = draw_tobi_bed_scene(image, fear=False)
    elif "fear_line" in scene_id or scene_id == "03_tobi_reacts":
        image = draw_tobi_bed_scene(image, fear=True)
    elif "stolen_phone" in scene_id:
        image = draw_flashback_scene(image)
    elif "unclaimed_bag" in scene_id:
        image = draw_tobi_bed_scene(image, bag=True)
    elif "lagos_awake" in scene_id or scene_id == "04_morning_lagos":
        image = draw_lagos_scene(image)
    elif "lagos_sounds" in scene_id:
        image = draw_lagos_scene(image, sounds=True)
    elif "door_wait" in scene_id or scene_id == "05_tobi_at_door":
        image = draw_door_scene(image)
    elif "mara_line" in scene_id:
        image = draw_door_scene(image, mara=True)
    elif "three_taps" in scene_id or scene_id == "06_three_taps":
        image = draw_door_scene(image, knock=True)
    elif "time_check" in scene_id:
        image = draw_door_scene(image, time_phone=True)
    elif "phone_buzzed" in scene_id:
        image = draw_door_scene(image, buzz_phone=True)
    elif "second_warning" in scene_id or scene_id == "07_second_warning":
        image = draw_message_screen(image, "My Number", "If you open it, she will know where you live.", door_hint=True)
    elif "delivery_voice" in scene_id or scene_id == "08_woman_with_package":
        image = draw_peephole_scene(image)
    elif "full_name" in scene_id:
        image = draw_package_scene(image, peek=True)
    elif "not_ordered" in scene_id or "follow_cta" in scene_id or "end_card" in scene_id or scene_id == "09_package_breathing":
        image = draw_package_scene(image, breathing=True)
    else:
        image = draw_message_screen(image, "Story Beat", scene.get("caption", "Suspense beat."))

    seed = sum(ord(ch) for ch in scene_id)
    image = add_thriller_texture(image, seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, quality=95)
    print(f"Wrote {reason} {out_path}")


def visual_asset_specs(scenes_data, include_caption_segments=True):
    specs = []
    seen = set()

    for scene in scenes_data.get("scenes", []):
        specs.append(scene)
        seen.add(scene["id"])

    if include_caption_segments:
        for segment in scenes_data.get("caption_segments", []):
            asset_id = segment.get("image_id", segment["id"])
            if asset_id != segment["id"] or asset_id in seen:
                continue
            prompt = segment.get("prompt")
            if not prompt:
                continue
            specs.append(
                {
                    "id": asset_id,
                    "caption": segment.get("caption", ""),
                    "prompt": prompt,
                    "motion": segment.get("motion", ""),
                    "generate_video": segment.get("generate_video", True),
                }
            )
            seen.add(asset_id)
    return specs


def generate_images(force: bool = False, requested_ids=None, provider: str = "openai"):
    fal_client = None
    strict_openai = env_bool("OPENAI_IMAGE_STRICT", True)
    if provider == "openai":
        require_env("OPENAI_API_KEY")
    elif provider == "fal":
        require_env("FAL_KEY")
        try:
            import fal_client
        except ImportError as exc:
            raise SystemExit(
                "Missing fal-client. Run: python3 -m pip install --user fal-client"
            ) from exc
    elif provider != "local":
        raise SystemExit(f"Unknown image provider: {provider}")

    scenes_data = json.loads(SCENES_PATH.read_text(encoding="utf-8"))
    style = scenes_data["style"]
    continuity = character_continuity_prompt(scenes_data)
    requested_ids = set(requested_ids or [])
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    for scene in visual_asset_specs(scenes_data):
        if requested_ids and scene["id"] not in requested_ids:
            continue
        out_path = IMAGES_DIR / f"{scene['id']}.png"
        if out_path.exists() and not force:
            print(f"Skipping existing {out_path.name}")
            continue
        if provider == "local":
            create_storyboard_image(scene, out_path)
            continue
        if provider == "openai":
            print(f"Generating {scene['id']} with OpenAI...")
            try:
                generate_openai_image(scene, style, continuity, out_path, scenes_data)
            except Exception as exc:
                notify_openai_generation_failure("scene image", scene["id"], exc)
                if strict_openai:
                    raise
                print(f"OpenAI image generation failed for {scene['id']}; creating local storyboard: {exc}")
                create_storyboard_image(scene, out_path)
            continue
        prompt = (
            f"{style}. {scene['prompt']} "
            "This must directly match the narration beat. Vertical cinematic frame, "
            "clear subject, emotionally readable, no subtitles, no title text, no logos."
        )
        print(f"Generating {scene['id']}...")
        try:
            result = fal_client.subscribe(
                "fal-ai/nano-banana-pro",
                arguments={
                    "prompt": prompt,
                    "image_size": "portrait_16_9",
                    "num_images": 1,
                },
            )
            url = find_first_url(result)
            if not url:
                raise RuntimeError(f"No image URL found in fal result for {scene['id']}: {result}")
            download_url(url, out_path)
            print(f"Wrote {out_path}")
        except Exception as exc:
            print(f"fal image generation failed for {scene['id']}; creating local storyboard: {exc}")
            create_storyboard_image(scene, out_path)


def find_asset(directory: Path, asset_id: str, extensions):
    for extension in extensions:
        path = directory / f"{asset_id}{extension}"
        if path.exists():
            return path
    return None


def video_scene_specs(scenes_data):
    segment_specs = []
    for segment in scenes_data.get("caption_segments", []):
        asset_id = segment.get("image_id", segment["id"])
        if asset_id != segment["id"]:
            continue
        if segment.get("generate_video", True) is False:
            continue
        if not segment.get("prompt"):
            continue
        segment_specs.append(
            {
                "id": asset_id,
                "duration": str(segment.get("video_duration", segment.get("duration", 4))),
                "motion": segment.get(
                    "motion",
                    "Subtle cinematic movement that directly matches the narration beat.",
                ),
            }
        )
    if segment_specs:
        return segment_specs

    configured = scenes_data.get("video_scenes")
    if configured:
        return configured
    return [
        {
            "id": "01_phone_under_pillow",
            "duration": "4",
            "motion": "The cracked phone trembles under the pillow as green light pulses through the fabric. Slow push-in, faint rain, muffled night room tone, tense phone vibration.",
        },
        {
            "id": "02_message_from_self",
            "duration": "5",
            "motion": "The camera creeps closer to the cracked screen as the ominous text glows. Rain streaks across the window behind it, subtle hand movement, low electronic hum and phone buzz.",
        },
        {
            "id": "06_three_taps",
            "duration": "4",
            "motion": "The apartment door stays closed while a shadow shifts outside. Three soft knocks land with suspenseful hallway ambience, tiny camera shake, no jump scare.",
        },
        {
            "id": "08_woman_with_package",
            "duration": "5",
            "motion": "Through the peephole, the mysterious woman adjusts the package and leans slightly toward the door. Rainy corridor ambience, distant generator hum, quiet fabric movement.",
        },
        {
            "id": "09_package_breathing",
            "duration": "5",
            "motion": "The brown package on the floor subtly rises and falls as if breathing. Low angle, amber hallway light flicker, paper rustle, soft ominous room tone.",
        },
    ]


def create_motion_fallback(scene_id: str, image_path: Path, out_path: Path, duration: str):
    ffmpeg = find_binary(
        "ffmpeg",
        "FFMPEG_PATH",
        [
            "/opt/homebrew/Cellar/ffmpeg/8.0.1_4/bin/ffmpeg",
            "/Applications/CapCut.app/Contents/Resources/ffmpeg",
        ],
    )
    seconds = float(duration)
    frames = max(1, int(round(seconds * 30)))
    if scene_id in {"01_phone_under_pillow", "02_message_from_self"}:
        audio_source = "anoisesrc=color=pink:amplitude=0.018:sample_rate=44100"
        audio_filter = "afade=t=in:st=0:d=0.2,afade=t=out:st={:.2f}:d=0.35".format(max(0, seconds - 0.35))
    elif scene_id == "06_three_taps":
        audio_source = "anoisesrc=color=brown:amplitude=0.014:sample_rate=44100"
        audio_filter = "afade=t=in:st=0:d=0.2,afade=t=out:st={:.2f}:d=0.35".format(max(0, seconds - 0.35))
    else:
        audio_source = "anoisesrc=color=brown:amplitude=0.016:sample_rate=44100"
        audio_filter = "afade=t=in:st=0:d=0.2,afade=t=out:st={:.2f}:d=0.35".format(max(0, seconds - 0.35))
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan=z='min(zoom+0.00065,1.075)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s=1080x1920:fps=30,"
        "eq=contrast=1.08:saturation=0.92,"
        "setsar=1,format=yuv420p"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-f",
            "lavfi",
            "-t",
            f"{seconds:.3f}",
            "-i",
            audio_source,
            "-vf",
            vf,
            "-frames:v",
            str(frames),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-af",
            audio_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(out_path),
        ]
    )
    print(f"Wrote fallback motion clip {out_path}")


def log_fal_update(label):
    last_printed = 0.0

    def on_update(update):
        nonlocal last_printed
        status_name = type(update).__name__
        now = time.monotonic()
        if status_name == "InProgress" and now - last_printed < 20:
            return
        last_printed = now
        print(f"{label}: {status_name}")
        for log in getattr(update, "logs", []) or []:
            message = log.get("message") if isinstance(log, dict) else str(log)
            if message:
                print(f"{label}: {message}")

    return on_update


def generate_videos(force: bool = False, requested_ids=None, local_only: bool = False):
    fal_client = None
    if not local_only:
        require_env("FAL_KEY")
        try:
            import fal_client
        except ImportError as exc:
            raise SystemExit(
                "Missing fal-client. Run: python3 -m pip install --user fal-client"
            ) from exc

    scenes_data = json.loads(SCENES_PATH.read_text(encoding="utf-8"))
    source_scenes = {scene["id"]: scene for scene in visual_asset_specs(scenes_data)}
    style = scenes_data["style"]
    model_id = os.getenv("FAL_VIDEO_MODEL", "bytedance/seedance-2.0/image-to-video")
    resolution = os.getenv("FAL_VIDEO_RESOLUTION", "720p")
    client_timeout = int(os.getenv("FAL_VIDEO_TIMEOUT_SECONDS", "480"))
    generate_audio = env_bool("FAL_VIDEO_GENERATE_AUDIO", False)
    requested_ids = set(requested_ids or [])
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    for spec in video_scene_specs(scenes_data):
        scene_id = spec["id"]
        if requested_ids and scene_id not in requested_ids:
            continue
        scene = source_scenes.get(scene_id)
        if not scene:
            print(f"Skipping unknown video scene {scene_id}")
            continue
        out_path = VIDEOS_DIR / f"{scene_id}.mp4"
        if out_path.exists() and not force:
            print(f"Skipping existing {out_path.name}")
            continue
        image_path = find_asset(IMAGES_DIR, scene_id, (".png", ".jpg", ".jpeg", ".webp"))
        if not image_path:
            print(f"Skipping {scene_id}; no source image found in {IMAGES_DIR}")
            continue
        if local_only:
            create_motion_fallback(scene_id, image_path, out_path, str(spec.get("duration", "5")))
            continue

        try:
            image_url = fal_client.upload_file(image_path)
        except Exception as exc:
            print(f"Upload failed for {scene_id}; using data URI fallback: {exc}")
            image_url = fal_client.encode_file(image_path)
        prompt = (
            f"{style}. Visual beat: {scene['prompt']} Motion direction: {spec['motion']} "
            "The moving clip must directly match the narration for this exact beat. "
            "Vertical cinematic short-form shot, realistic motion, suspenseful pacing, "
            "keep characters and props consistent, no new characters unless described, "
            "no subtitles, no title cards, no logos, no readable brand names."
        )
        duration = str(spec.get("duration", "5"))
        print(f"Generating moving clip {scene_id}...")
        try:
            result = fal_client.subscribe(
                model_id,
                arguments={
                    "prompt": prompt,
                    "image_url": image_url,
                    "resolution": resolution,
                    "duration": duration,
                    "aspect_ratio": "9:16",
                    "generate_audio": generate_audio,
                },
                client_timeout=client_timeout,
                with_logs=True,
                on_queue_update=log_fal_update(scene_id),
            )
            url = find_first_url(result)
            if not url:
                raise RuntimeError(f"No video URL found in fal result for {scene_id}: {result}")
            download_url(url, out_path)
            print(f"Wrote {out_path}")
        except Exception as exc:
            print(f"fal video generation failed for {scene_id}; creating local fallback: {exc}")
            create_motion_fallback(scene_id, image_path, out_path, duration)



def generate_openai_cover_base(out_path: Path, scenes_data, cover_style: str | None = None):
    require_env("OPENAI_API_KEY")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "Missing openai package. Run: python3 -m pip install --user openai"
        ) from exc

    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
    size = os.getenv("OPENAI_IMAGE_SIZE", "1024x1536")
    quality = os.getenv("OPENAI_IMAGE_QUALITY", "high")
    timeout = float(os.getenv("OPENAI_IMAGE_TIMEOUT_SECONDS", "180"))
    client = OpenAI(timeout=timeout)
    result = client.images.generate(
        model=model,
        prompt=cover_background_prompt(scenes_data, style_id=cover_style, series_dir=SERIES_DIR),
        size=size,
        quality=quality,
        output_format="png",
        n=1,
    )
    image_b64 = openai_image_b64(result)
    if not image_b64:
        raise RuntimeError(f"No base64 cover image found in OpenAI result: {result}")
    out_path.write_bytes(base64.b64decode(image_b64))
    print(f"Wrote OpenAI cover base {out_path} ({model}, {size}, {quality})")



def generate_cover(force_cover: bool = False, provider: str = "openai", cover_style: str | None = None):
    scenes_data = json.loads(SCENES_PATH.read_text(encoding="utf-8"))
    fal_available = bool(os.getenv("FAL_KEY"))
    strict_openai = env_bool("OPENAI_IMAGE_STRICT", True)
    try:
        import fal_client
    except ImportError as exc:
        fal_client = None
    if provider == "openai":
        require_env("OPENAI_API_KEY")
    elif provider not in {"fal", "local"}:
        raise SystemExit(f"Unknown cover provider: {provider}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = scenes_data.get("output_slug", EPISODE.name)
    base_path = EXPORTS_DIR / f"{slug}_cover_base.png"
    out_path = EXPORTS_DIR / f"{slug}_cover.png"
    if force_cover and base_path.exists():
        base_path.unlink()
    if not base_path.exists():
        if provider == "openai":
            try:
                generate_openai_cover_base(base_path, scenes_data, cover_style=cover_style)
            except Exception as exc:
                notify_openai_generation_failure("cover base", slug, exc)
                if strict_openai:
                    raise
                print("OpenAI cover generation failed; using existing episode art.")
        elif provider == "fal" and fal_available and fal_client:
            try:
                result = fal_client.subscribe(
                    "fal-ai/nano-banana-pro",
                    arguments={
                        "prompt": cover_background_prompt(scenes_data, style_id=cover_style, series_dir=SERIES_DIR),
                        "image_size": "portrait_16_9",
                        "num_images": 1,
                    },
                    client_timeout=300,
                )
                url = find_first_url(result)
                if not url:
                    raise RuntimeError(f"No cover image URL found in fal result: {result}")
                download_url(url, base_path)
                print(f"Wrote {base_path}")
            except Exception as exc:
                print(f"fal cover generation failed; using existing episode art: {exc}")
        if not base_path.exists():
            fallback = (
                find_asset(IMAGES_DIR, "09a_tobi_grabs_iya_sade", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "17a_real_iya_shadow_crosses", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "18a_supposed_to_die_tomorrow", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "19a_follow_cta", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "02b_warning_text", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "08a_delivery_voice", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "01a_phone_buzz", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "02_message_from_self", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "08_woman_with_package", (".png", ".jpg", ".jpeg", ".webp"))
                or find_asset(IMAGES_DIR, "01_phone_under_pillow", (".png", ".jpg", ".jpeg", ".webp"))
                or next(iter(sorted(IMAGES_DIR.glob("*.png"))), None)
            )
            if not fallback:
                raise SystemExit(f"No local image found for cover fallback in {IMAGES_DIR}")
            Image.open(fallback).convert("RGB").save(base_path)
            print(f"Wrote {base_path} from {fallback.name}")
    resolved_style = cover_style or resolve_cover_style_id(scenes_data, SERIES_DIR)
    compose_cover(base_path, out_path, scenes_data, style_id=resolved_style, series_dir=SERIES_DIR)


def main():
    parser = argparse.ArgumentParser(description="Generate storyforge episode assets.")
    parser.add_argument(
        "--series",
        default=None,
        help="Series directory relative to repo root or absolute path. Defaults to PIPELINE_SERIES_DIR.",
    )
    parser.add_argument(
        "--episode",
        default="episode_01",
        help="Episode folder name under the current series, or an absolute episode directory.",
    )
    parser.add_argument("--list-voices", action="store_true", help="List ElevenLabs voices and IDs.")
    parser.add_argument("--voice", action="store_true", help="Generate ElevenLabs voiceover.")
    parser.add_argument("--images", action="store_true", help="Generate scene images.")
    parser.add_argument("--force-images", action="store_true", help="Regenerate images even if files exist.")
    parser.add_argument(
        "--image-provider",
        choices=("fal", "openai", "local"),
        default="openai",
        help="Image provider to use. Defaults to OpenAI/ChatGPT for series consistency.",
    )
    parser.add_argument("--openai-images", action="store_true", help="Generate images with OpenAI GPT Image.")
    parser.add_argument("--local-images", action="store_true", help="Create local storyboard images instead of calling a remote image model.")
    parser.add_argument("--image-ids", help="Comma-separated image/segment IDs to generate.")
    parser.add_argument("--videos", action="store_true", help="Generate moving scene clips with fal.ai.")
    parser.add_argument("--force-videos", action="store_true", help="Regenerate videos even if files exist.")
    parser.add_argument("--local-videos", action="store_true", help="Create local motion clips instead of calling fal.ai.")
    parser.add_argument("--video-ids", help="Comma-separated source scene IDs to generate.")
    parser.add_argument("--cover", action="store_true", help="Generate the episode cover image.")
    parser.add_argument("--force-cover", action="store_true", help="Regenerate the cover background before composing.")
    parser.add_argument(
        "--cover-provider",
        choices=("fal", "openai", "local"),
        default="openai",
        help="Cover background provider. Defaults to OpenAI/ChatGPT; typography is always composed locally.",
    )
    parser.add_argument("--openai-cover", action="store_true", help="Generate the cover background with OpenAI GPT Image.")
    parser.add_argument("--cover-style", metavar="STYLE_ID", help="Cover design style id (see --list-cover-styles).")
    parser.add_argument("--list-cover-styles", action="store_true", help="List available cover design styles and exit.")
    args = parser.parse_args()

    load_local_env()
    if args.list_cover_styles:
        from cover_styles import list_styles
        from pipeline_config import load_series_config
        template = None
        try:
            series_dir = get_series_dir(args.series)
            template = load_series_config(series_dir).get("style_template")
        except BaseException:
            if args.series:
                raise
        for item in list_styles(template):
            rec = " (template default)" if item["recommended"] else ""
            print(f"{item['id']}: {item['name']}{rec}")
            if item["description"]:
                print(f"  {item['description']}")
        return 0
    configure_series(args.series)
    configure_episode(args.episode)
    if args.list_voices:
        list_voices()
    if args.voice:
        generate_voice()
    if args.images:
        requested_ids = None
        if args.image_ids:
            requested_ids = [item.strip() for item in args.image_ids.split(",") if item.strip()]
        image_provider = args.image_provider
        if args.openai_images:
            image_provider = "openai"
        if args.local_images:
            image_provider = "local"
        generate_images(force=args.force_images, requested_ids=requested_ids, provider=image_provider)
    if args.videos:
        requested_ids = None
        if args.video_ids:
            requested_ids = [item.strip() for item in args.video_ids.split(",") if item.strip()]
        generate_videos(force=args.force_videos, requested_ids=requested_ids, local_only=args.local_videos)
    if args.cover:
        cover_provider = args.cover_provider
        if args.openai_cover:
            cover_provider = "openai"
        generate_cover(force_cover=args.force_cover, provider=cover_provider, cover_style=args.cover_style)
    if not (args.list_voices or args.voice or args.images or args.videos or args.cover or args.list_cover_styles):
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
