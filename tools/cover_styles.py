#!/usr/bin/env python3
"""Cover poster typography and style resolution for Storyforge."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from pipeline_config import ROOT, get_series_dir, load_series_config, merged_series_settings

COVER_WIDTH = 1080
COVER_HEIGHT = 1920
SAFE_MARGIN = 56


def content_width(margin: int = SAFE_MARGIN) -> int:
    return COVER_WIDTH - 2 * margin


_COVER_STYLES_PATH = ROOT / "config" / "cover_styles.yaml"
_CACHE: dict[str, Any] | None = None


def load_cover_styles() -> dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        if not _COVER_STYLES_PATH.exists():
            raise SystemExit(f"Missing cover styles config: {_COVER_STYLES_PATH}")
        _CACHE = yaml.safe_load(_COVER_STYLES_PATH.read_text(encoding="utf-8")) or {}
    return _CACHE


def default_style_for_template(template_name: str) -> str:
    defaults = load_cover_styles().get("default_for_template", {})
    return defaults.get(template_name, "thriller_neon_rain")


def get_style(style_id: str) -> dict[str, Any]:
    styles = load_cover_styles().get("styles", {})
    if style_id not in styles:
        known = ", ".join(sorted(styles))
        raise SystemExit(f"Unknown cover style {style_id!r}. Known: {known}")
    style = dict(styles[style_id])
    style["id"] = style_id
    return style


def list_styles(style_template: str | None = None) -> list[dict[str, Any]]:
    data = load_cover_styles()
    defaults = data.get("default_for_template", {})
    recommended = set(defaults.values())
    out: list[dict[str, Any]] = []
    for style_id, style in sorted(data.get("styles", {}).items()):
        templates = style.get("style_templates") or []
        if style_template and style_template not in templates:
            continue
        out.append({
            "id": style_id,
            "name": style.get("name", style_id),
            "description": style.get("description", ""),
            "recommended": style_id in recommended,
        })
    return out


def resolve_cover_style_id(scenes_data: dict[str, Any], series_dir: Path | None = None) -> str:
    cover = scenes_data.get("cover", {})
    if cover.get("design_style"):
        return str(cover["design_style"])
    settings = merged_series_settings(series_dir)
    series_cover = settings.get("cover", {}) if isinstance(settings.get("cover"), dict) else {}
    if series_cover.get("default_design_style"):
        return str(series_cover["default_design_style"])
    template_name = load_series_config(series_dir).get("style_template", "")
    if template_name:
        return default_style_for_template(str(template_name))
    return "thriller_neon_rain"


def hex_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        return (255, 255, 255, alpha)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)



def cover_config(scenes_data: dict[str, Any], series_dir: Path | None = None, style_id: str | None = None) -> dict[str, Any]:
    cover = scenes_data.get("cover", {})
    episode_title = cover.get("episode_title", scenes_data.get("episode_title", ""))
    title_lines = cover.get("title_lines")
    if not title_lines:
        if episode_title.upper() == "DO NOT OPEN THE DOOR":
            title_lines = ["DO NOT OPEN", "THE DOOR"]
        else:
            title_lines = wrap_text_lines(
                episode_title.upper(),
                content_width() - 112,
                "impact",
                max_lines=2,
                start_size=104,
                min_size=48,
            )
    series = series_dir or get_series_dir()
    settings = merged_series_settings(series)
    series_title = cover.get(
        "series_title",
        settings.get("series", {}).get("title", "Your Series Title"),
    )
    resolved_style = style_id or resolve_cover_style_id(scenes_data, series)
    style = get_style(resolved_style)
    return {
        "series_title": str(series_title).upper(),
        "episode_number": str(cover.get("episode_number", "1")),
        "part_number": str(cover.get("part_number", "1")),
        "hook_lines": cover.get("hook_lines", ["DON'T", "MAKE THIS", "MISTAKE"]),
        "hook_highlight": str(cover.get("hook_highlight", "MISTAKE")).upper(),
        "title_lines": [line.upper() for line in title_lines],
        "style_id": resolved_style,
        "style": style,
        "colors": style.get("colors", {}),
        "effects": style.get("effects", {}),
    }


def load_font(size, candidates=None):
    candidates = candidates or [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def font_candidates(kind):
    fonts = {
        "impact": [
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
        ],
        "condensed": [
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/System/Library/Fonts/Avenir Next Condensed.ttc",
            "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
            "/System/Library/Fonts/Supplemental/Impact.ttf",
        ],
        "hand": [
            "/System/Library/Fonts/MarkerFelt.ttc",
            "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
            "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
        ],
        "block": [
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ],
    }
    return fonts.get(kind, fonts["block"])


def text_width(draw, text, font, stroke_width=0):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return box[2] - box[0]


def fit_font(text, max_width, start_size, min_size, kind, stroke_width=0, absolute_min=18):
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    floor = min(min_size, absolute_min)
    for size in range(start_size, floor - 1, -2):
        font = load_font(size, font_candidates(kind))
        if text_width(probe, text, font, stroke_width=stroke_width) <= max_width:
            return font
    return load_font(floor, font_candidates(kind))


def fit_font_box(text, max_width, max_height, start_size, min_size, kind, stroke_width=0, absolute_min=18):
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    floor = min(min_size, absolute_min)
    for size in range(start_size, floor - 1, -2):
        font = load_font(size, font_candidates(kind))
        box = probe.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return font
    return load_font(floor, font_candidates(kind))


def text_height(draw, text, font, stroke_width=0):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return box[3] - box[1]


def wrap_text_lines(
    text,
    max_width,
    kind,
    max_lines=2,
    start_size=60,
    min_size=20,
    stroke_width=0,
):
    words = text.split()
    if not words:
        return [""]

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines: list[str] = []
    idx = 0

    while idx < len(words) and len(lines) < max_lines:
        current: list[str] = []
        while idx < len(words):
            trial = " ".join(current + [words[idx]])
            font = fit_font(trial, max_width, start_size, min_size, kind, stroke_width=stroke_width)
            if text_width(probe, trial, font, stroke_width=stroke_width) <= max_width or not current:
                current.append(words[idx])
                idx += 1
            else:
                break
        if current:
            lines.append(" ".join(current))

    if idx < len(words) and lines:
        lines[-1] = " ".join(lines[-1].split() + words[idx:])

    return lines if lines else [text]


def normalize_hook_lines(hook_lines, kind, max_width=400, max_lines=5):
    result: list[str] = []
    for line in hook_lines:
        if not line:
            continue
        wrapped = wrap_text_lines(
            str(line).upper(),
            max_width,
            kind,
            max_lines=max_lines,
            start_size=60,
            min_size=18,
            stroke_width=2,
        )
        for wrapped_line in wrapped:
            if len(result) >= max_lines:
                break
            result.append(wrapped_line)
        if len(result) >= max_lines:
            break
    return result if result else ["DON'T", "MAKE THIS", "MISTAKE"]


def centered_text(draw, text, y, font, fill, stroke_width=0, stroke_fill=(0, 0, 0, 255)):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_w = box[2] - box[0]
    x = int((COVER_WIDTH - text_w) / 2)
    max_x = COVER_WIDTH - SAFE_MARGIN - text_w
    x = max(SAFE_MARGIN, min(x, max_x))
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
    return y + box[3] - box[1]



def add_poster_grade(image, style: dict[str, Any]):
    grade = style.get("grade", "rain_neon")
    effects = style.get("effects", {})
    contrast = {
        "rain_neon": 1.22,
        "cold_fog": 1.08,
        "warm_glow": 1.12,
        "high_contrast": 1.35,
        "soft_wash": 0.95,
        "sepia_dust": 1.05,
        "pastel": 0.92,
        "terminal_scan": 1.18,
        "noir_shadow": 1.28,
    }.get(grade, 1.15)
    color_boost = {
        "sepia_dust": 0.88,
        "pastel": 1.12,
        "soft_wash": 1.02,
    }.get(grade, 1.05)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(color_boost)
    if grade == "sepia_dust":
        image = ImageEnhance.Color(image).enhance(0.75)
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    top_alpha = {"soft_wash": 140, "pastel": 120, "minimal_top": 150}.get(grade, 185)
    draw.rectangle((0, 0, width, 610), fill=(0, 0, 0, top_alpha))
    draw.rectangle((0, height - 560, width, height), fill=(0, 0, 0, 170))
    draw.rectangle((0, 0, 90, height), fill=(0, 0, 0, 120))
    draw.rectangle((width - 90, 0, width, height), fill=(0, 0, 0, 120))
    draw.rectangle((0, 0, width, 26), fill=(0, 0, 0, 255))
    draw.rectangle((0, height - 26, width, height), fill=(0, 0, 0, 255))
    if grade == "terminal_scan":
        scan = ImageDraw.Draw(overlay)
        for row in range(0, height, 4):
            scan.rectangle((0, row, width, row + 1), fill=(0, 255, 120, 18))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    if effects.get("rain") or grade == "rain_neon":
        rain = Image.new("RGBA", image.size, (0, 0, 0, 0))
        rain_draw = ImageDraw.Draw(rain)
        rng = random.Random(13)
        for _ in range(170):
            x = rng.randint(-80, width + 60)
            y = rng.randint(0, height)
            length = rng.randint(22, 78)
            alpha = rng.randint(35, 100)
            rain_draw.line((x, y, x + 10, y + length), fill=(170, 230, 225, alpha), width=1)
        rain = rain.filter(ImageFilter.GaussianBlur(0.35))
        image = Image.alpha_composite(image, rain)
    return image


def draw_glitch_word(base, text, y, colors: dict[str, str], enabled: bool = True):
    max_w = content_width() - 24
    accent = hex_rgba(colors.get("accent", "#00F55E"))
    if not enabled:
        font = fit_font(text, max_w, 205, 120, "impact", stroke_width=2)
        draw = ImageDraw.Draw(base)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=2)
        text_w = box[2] - box[0]
        x = int((COVER_WIDTH - text_w) / 2)
        max_x = COVER_WIDTH - SAFE_MARGIN - text_w
        x = max(SAFE_MARGIN, min(x, max_x))
        draw.text((x, y), text, font=font, fill=accent, stroke_width=2, stroke_fill=(0, 0, 0, 255))
        return y + box[3] - box[1] + 8
    font = fit_font(text, max_w, 205, 120, "impact", stroke_width=2)
    probe = ImageDraw.Draw(Image.new("RGBA", (COVER_WIDTH, 260), (0, 0, 0, 0)))
    box = probe.textbbox((0, 0), text, font=font, stroke_width=2)
    text_w = box[2] - box[0]
    text_h = box[3] - box[1]
    x = int((COVER_WIDTH - text_w) / 2)
    max_x = COVER_WIDTH - SAFE_MARGIN - text_w
    x = max(SAFE_MARGIN, min(x, max_x))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_fill = (accent[0], accent[1], accent[2], 115)
    for offset in (-8, -4, 4, 8):
        glow_draw.text((x + offset, y), text, font=font, fill=glow_fill, stroke_width=4, stroke_fill=(accent[0], accent[1], accent[2], 70))
    glow = glow.filter(ImageFilter.GaussianBlur(9))
    base.alpha_composite(glow)
    draw.text((x, y), text, font=font, fill=accent, stroke_width=2, stroke_fill=(0, 40, 20, 255))
    rng = random.Random(42)
    for _ in range(10):
        sy = y + rng.randint(0, max(1, text_h))
        draw.rectangle((x - rng.randint(10, 45), sy, x + text_w + rng.randint(10, 45), sy + rng.randint(1, 4)), fill=(accent[0], accent[1], accent[2], rng.randint(45, 95)))
    for _ in range(8):
        sy = y + rng.randint(10, max(11, text_h - 4))
        crop = layer.crop((x, sy, x + text_w, sy + rng.randint(3, 9)))
        layer.alpha_composite(crop, (x + rng.randint(-28, 28), sy))
    base.alpha_composite(layer)
    return y + text_h + 8


def draw_handwritten_hook(base, cfg):
    style = cfg["style"]
    hook_style = style.get("hook_style", "handwritten_arrow")
    if hook_style == "none":
        return
    colors = cfg["colors"]
    draw = ImageDraw.Draw(base)
    hook_max_width = 420
    hook_lines = normalize_hook_lines(cfg["hook_lines"], "hand", max_width=hook_max_width)
    highlight = cfg["hook_highlight"]
    x, y = 92, 760
    white = hex_rgba(colors.get("title", "#FFFFFF"))
    accent = hex_rgba(colors.get("hook_highlight", colors.get("accent", "#23FF70")))
    for line in hook_lines:
        start_size = 66 if line == highlight else 58
        font = fit_font(line, hook_max_width, start_size, 28, "hand", stroke_width=2)
        fill = accent if line == highlight else white
        draw.text((x, y), line, font=font, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0, 210))
        y += text_height(draw, line, font, stroke_width=2) + 10
    if hook_style == "handwritten_arrow":
        draw.line((120, y - 8, 320, y - 42), fill=accent, width=6)
        draw.line((308, y + 35, 365, y + 112), fill=white, width=6)
        draw.line((365, y + 112, 335, y + 103), fill=white, width=6)
        draw.line((365, y + 112, 355, y + 82), fill=white, width=6)


def draw_block_hook(base, cfg):
    style = cfg["style"]
    if style.get("hook_style") == "none":
        return
    colors = cfg["colors"]
    draw = ImageDraw.Draw(base)
    hook_max_width = 420
    hook_lines = normalize_hook_lines(cfg["hook_lines"], "block", max_width=hook_max_width)
    highlight = cfg["hook_highlight"]
    x, y = 72, 780
    white = hex_rgba(colors.get("title", "#FFFFFF"))
    accent = hex_rgba(colors.get("hook_highlight", colors.get("accent", "#23FF70")))
    for line in hook_lines:
        start_size = 60 if line == highlight else 52
        font = fit_font(line, hook_max_width, start_size, 28, "block", stroke_width=2)
        fill = accent if line == highlight else white
        draw.text((x, y), line, font=font, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0, 220))
        y += text_height(draw, line, font, stroke_width=2) + 8



def draw_episode_badge(base, episode_number, style):
    colors = style.get("colors", {})
    badge_style = style.get("badge_style", "red_episode")
    draw = ImageDraw.Draw(base)
    x1, y1, x2, y2 = 398, 1468, 682, 1535
    fill = hex_rgba(colors.get("badge_fill", "#D21212"), 230)
    if badge_style == "outline_minimal":
        font = fit_font("EPISODE " + str(episode_number), 240, 48, 30, "condensed", stroke_width=2)
        centered_text(draw, "EPISODE " + str(episode_number), y1 + 10, font, hex_rgba(colors.get("title", "#FFFFFF")), stroke_width=2, stroke_fill=(0, 0, 0, 255))
        return
    rng = random.Random(7)
    for _ in range(90):
        x = rng.randint(x1 - 35, x2 + 35)
        y = rng.randint(y1 - 12, y2 + 12)
        r = rng.randint(1, 3)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(fill[0], fill[1], fill[2], rng.randint(35, 115)))
    draw.rectangle((x1, y1, x2, y2), fill=fill)
    font = fit_font("EPISODE " + str(episode_number), 240, 48, 30, "condensed", stroke_width=1)
    centered_text(draw, "EPISODE " + str(episode_number), y1 + 10, font, (255, 255, 255, 255), stroke_width=1)


def draw_distressed_text(base, text, y, max_width, start_size, kind, fill, stroke_width=2, max_height=None, scratch=True):
    if max_height:
        font = fit_font_box(text, max_width, max_height, start_size, 48, kind, stroke_width=stroke_width)
    else:
        font = fit_font(text, max_width, start_size, 48, kind, stroke_width=stroke_width)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_w = box[2] - box[0]
    x = int((COVER_WIDTH - text_w) / 2)
    max_x = COVER_WIDTH - SAFE_MARGIN - text_w
    x = max(SAFE_MARGIN, min(x, max_x))
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=(0, 0, 0, 255))
    if scratch:
        alpha = layer.getchannel("A")
        scratch_draw = ImageDraw.Draw(alpha)
        rng = random.Random(sum(ord(ch) for ch in text))
        for _ in range(150):
            sx = rng.randint(max(0, x), min(COVER_WIDTH - 1, x + text_w))
            sy = rng.randint(y, min(COVER_HEIGHT - 1, y + box[3] - box[1] + 20))
            scratch_draw.line((sx, sy, sx + rng.randint(8, 28), sy + rng.randint(-3, 3)), fill=0, width=rng.randint(1, 3))
        layer.putalpha(alpha)
    base.alpha_composite(layer)
    return y + box[3] - box[1] + 8


def _estimate_title_block_height(title_lines, max_width, layout, scratch):
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    total = 0
    for i, line in enumerate(title_lines):
        kind = "hand" if i == 1 and layout == "brush_accent" else "impact"
        start_size = 104 if i == 0 else (102 if layout == "brush_accent" else 100)
        sublines = wrap_text_lines(line, max_width, kind, max_lines=2, start_size=start_size, min_size=48, stroke_width=2)
        for sub in sublines:
            max_h = 118 if i == 0 else 120
            font = fit_font_box(sub, max_width, max_h, start_size, 48, kind, stroke_width=2)
            total += text_height(probe, sub, font, stroke_width=2) + 8
    return total


def draw_bottom_title(base, cfg):
    style = cfg["style"]
    colors = cfg["colors"]
    effects = cfg.get("effects", style.get("effects", {}))
    title_lines = cfg["title_lines"]
    title_fill = hex_rgba(colors.get("title", "#FFFFFF"))
    accent_fill = hex_rgba(colors.get("accent", "#00F55E"))
    layout = style.get("title_layout", "brush_accent")
    scratch = bool(effects.get("scratch", True))
    max_width = content_width() - 56
    part_y = 1842
    block_height = _estimate_title_block_height(title_lines, max_width, layout, scratch)
    y = max(1540, part_y - block_height - 24)

    if title_lines:
        sublines = wrap_text_lines(title_lines[0], max_width, "impact", max_lines=2, start_size=104, min_size=48, stroke_width=2)
        for sub in sublines:
            y = draw_distressed_text(base, sub, y, max_width, 104, "impact", title_fill, max_height=118, scratch=scratch)

    if len(title_lines) > 1:
        if layout == "brush_accent":
            accent_sublines = wrap_text_lines(title_lines[1], max_width, "hand", max_lines=2, start_size=102, min_size=48, stroke_width=2)
            for sub in accent_sublines:
                brush_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
                brush_y = y + 6
                draw_distressed_text(brush_layer, sub, brush_y, max_width, 102, "hand", accent_fill, max_height=120, scratch=scratch)
                brush_layer = brush_layer.rotate(-2.2, resample=Image.Resampling.BICUBIC, center=(540, brush_y + 70))
                base.alpha_composite(brush_layer)
                probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
                font = fit_font_box(sub, max_width, 120, 102, 48, "hand", stroke_width=2)
                y += text_height(probe, sub, font, stroke_width=2) + 8
        else:
            impact_sublines = wrap_text_lines(title_lines[1], max_width, "impact", max_lines=2, start_size=100, min_size=48, stroke_width=2)
            for sub in impact_sublines:
                y = draw_distressed_text(base, sub, y + 6, max_width, 100, "impact", title_fill, max_height=120, scratch=scratch)

    draw = ImageDraw.Draw(base)
    part_number = cfg.get("part_number", "1")
    part_text = "PART " + str(part_number)
    font = fit_font(part_text, 235, 44, 30, "block", stroke_width=1)
    box = draw.textbbox((0, 0), part_text, font=font, stroke_width=1)
    part_w = box[2] - box[0] + 88
    x1 = int((COVER_WIDTH - part_w) / 2)
    y1 = part_y
    outline = hex_rgba(colors.get("part_outline", colors.get("accent", "#00E652")))
    part_text_color = hex_rgba(colors.get("part_text", colors.get("accent", "#24FF69")))
    draw.rectangle((x1, y1, x1 + part_w, y1 + 52), outline=outline, width=3)
    centered_text(draw, part_text, y1 + 5, font, part_text_color, stroke_width=1)


def draw_series_header(base, cfg):
    style = cfg["style"]
    colors = cfg["colors"]
    layout = style.get("series_layout", "stacked_glitch")
    series_words = cfg["series_title"].split()
    title_white = hex_rgba(colors.get("title", "#FFFFFF"))
    draw = ImageDraw.Draw(base)
    header_max_w = content_width() - 24
    glitch_on = layout == "stacked_glitch" and style.get("effects", {}).get("glitch", True)

    if layout == "minimal_top":
        font = fit_font(cfg["series_title"], header_max_w, 56, 40, "condensed", stroke_width=1)
        centered_text(draw, cfg["series_title"], 48, font, title_white, stroke_width=1)
        return

    if layout == "single_impact":
        lines = wrap_text_lines(cfg["series_title"], header_max_w, "impact", max_lines=2, start_size=120, min_size=72, stroke_width=3)
        y = 72
        for line in lines:
            font = fit_font(line, header_max_w, 120, 72, "impact", stroke_width=3)
            y = centered_text(draw, line, y, font, title_white, stroke_width=3) + 8
        return

    if len(series_words) <= 4:
        if len(series_words) <= 1:
            draw_glitch_word(base, series_words[0] if series_words else cfg["series_title"], 58, colors, enabled=glitch_on)
            return
        prefix = " ".join(series_words[:-1])
        last_word = series_words[-1]
        prefix_lines = wrap_text_lines(prefix, header_max_w, "condensed", max_lines=2, start_size=92, min_size=54, stroke_width=2)
        y = 58
        for line in prefix_lines:
            font = fit_font(line, header_max_w, 92, 54, "condensed", stroke_width=2)
            y = centered_text(draw, line, y, font, title_white, stroke_width=2) + 10
        draw_glitch_word(base, last_word, y + 8, colors, enabled=glitch_on)
        return

    top_line = " ".join(series_words[:3]) or cfg["series_title"]
    receive_line = " ".join(series_words[3:-1])
    last_word = series_words[-1] if series_words else "TOMORROW"
    top_font = fit_font(top_line, header_max_w, 92, 54, "condensed", stroke_width=2)
    centered_text(draw, top_line, 58, top_font, title_white, stroke_width=2)
    if receive_line:
        receive_font = fit_font(receive_line, header_max_w, 150, 96, "impact", stroke_width=3)
        centered_text(draw, receive_line, 166, receive_font, title_white, stroke_width=3)
    draw_glitch_word(base, last_word, 356, colors, enabled=glitch_on)


def compose_cover(base_path, out_path, scenes_data, style_id=None, series_dir=None):
    width, height = COVER_WIDTH, COVER_HEIGHT
    image = Image.open(base_path).convert("RGB")
    ratio = max(width / image.width, height / image.height)
    image = image.resize((int(image.width * ratio), int(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    resolved = style_id or resolve_cover_style_id(scenes_data, series_dir)
    image = add_poster_grade(image.crop((left, top, left + width, top + height)), get_style(resolved))
    cfg = cover_config(scenes_data, series_dir, resolved)
    draw_series_header(image, cfg)
    hook_style = cfg["style"].get("hook_style", "handwritten_arrow")
    if hook_style == "handwritten_arrow":
        draw_handwritten_hook(image, cfg)
    elif hook_style == "block_left":
        draw_block_hook(image, cfg)
    draw_episode_badge(image, cfg["episode_number"], cfg["style"])
    draw_bottom_title(image, cfg)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out_path, quality=95)
    print("Wrote " + str(out_path))


_GRADE_MOOD = {
    "rain_neon": "dark rainy cinematic atmosphere, neon accent glow, wet reflections",
    "cold_fog": "cold desaturated fog, icy blue practical light, muted tension",
    "warm_glow": "warm golden practical light, soft atmospheric glow",
    "high_contrast": "high contrast dramatic lighting, bold shadows",
    "soft_wash": "soft diffused light, gentle pastel wash",
    "sepia_dust": "sepia dust, sun-bleached frontier tones",
    "pastel": "bright pastel-friendly lighting, cheerful saturation",
    "terminal_scan": "futuristic HUD glow, tech laboratory atmosphere",
    "noir_shadow": "film noir shadows, venetian blind light, smoky contrast",
}


def cover_background_prompt(scenes_data=None, style_id=None, series_dir=None):
    scenes_data = scenes_data or {}
    cover = scenes_data.get("cover", {})
    resolved = style_id or resolve_cover_style_id(scenes_data, series_dir)
    style = get_style(resolved)
    grade = style.get("grade", "rain_neon")
    mood = _GRADE_MOOD.get(grade, "cinematic poster atmosphere")
    episode_background = cover.get(
        "background_prompt",
        "dark atmospheric entrance with warm light in the middle distance, a mysterious figure or key story object, strong foreground prop with glow and floor reflections.",
    )
    return (
        "Vertical 9:16 cinematic poster scene plate matching the recurring cover style reference. "
        "Generate only the background image; absolutely no typography, no badges, no arrows, no graphic layout. "
        "Composition must preserve the reference layout: clean negative space across the upper third for a huge stacked title; "
        "main story threat in the middle distance; a key story object large in the foreground with glow and reflections. "
        "Visual mood (" + resolved + "): " + mood + ". "
        "Episode-specific scene plate: " + episode_background + " "
        "Heavy contrast, atmospheric depth, no gore unless the scene requires it. Full-bleed single continuous photographic scene, "
        "no border, no matte frame, no inset panel, no logos, no readable brand names, no text anywhere."
    )
