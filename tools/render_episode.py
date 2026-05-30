#!/usr/bin/env python3
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


from pipeline_config import (
    ROOT,
    ENV_PATH,
    episode_output_slug,
    get_series_dir,
    load_local_env,
    resolve_episode_path,
)

SERIES_DIR = get_series_dir()
EPISODE = SERIES_DIR / "episode_01"
SCENES_PATH = EPISODE / "scenes.json"
ASSETS = EPISODE / "assets"
IMAGES_DIR = ASSETS / "images"
VIDEOS_DIR = ASSETS / "video"
VOICE_PATH = ASSETS / "voiceover" / "voiceover_episode_01.mp3"
WORK_DIR = ASSETS / "work"
EXPORTS_DIR = ASSETS / "exports"
OUTPUT = EXPORTS_DIR / "episode_01_vertical.mp4"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm")
INTRO_DURATION_SECONDS = 2.5


def configure_series(value=None):
    global SERIES_DIR
    SERIES_DIR = get_series_dir(value)


def configure_episode(value):
    global EPISODE, SCENES_PATH, ASSETS, IMAGES_DIR, VIDEOS_DIR, VOICE_PATH, WORK_DIR, EXPORTS_DIR, OUTPUT
    EPISODE = resolve_episode_path(value, SERIES_DIR)
    SCENES_PATH = EPISODE / "scenes.json"
    ASSETS = EPISODE / "assets"
    IMAGES_DIR = ASSETS / "images"
    VIDEOS_DIR = ASSETS / "video"
    slug = episode_output_slug(EPISODE)
    VOICE_PATH = ASSETS / "voiceover" / f"voiceover_{slug}.mp3"
    WORK_DIR = ASSETS / "work"
    EXPORTS_DIR = ASSETS / "exports"
    OUTPUT = EXPORTS_DIR / f"{slug}_vertical.mp4"


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


def ffprobe_duration(ffprobe, path: Path):
    if not path.exists():
        return None
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def ffprobe_has_audio(ffprobe, path: Path):
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def load_font(size):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def cover_image(image: Image.Image, width: int, height: int):
    image = image.convert("RGB")
    ratio = max(width / image.width, height / image.height)
    new_size = (math.ceil(image.width * ratio), math.ceil(image.height * ratio))
    image = image.resize(new_size, Image.Resampling.LANCZOS)
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    return image.crop((left, top, left + width, top + height))


def make_placeholder(prompt, width, height):
    image = Image.new("RGB", (width, height), "#101014")
    draw = ImageDraw.Draw(image)
    title_font = load_font(52)
    body_font = load_font(32)
    draw.rectangle((0, 0, width, height), fill="#101014")
    draw.text((70, 160), "Missing generated image", font=title_font, fill="#f2f2f2")
    wrapped = textwrap.wrap(prompt, width=38)
    y = 260
    for line in wrapped[:16]:
        draw.text((70, y), line, font=body_font, fill="#b5b5b5")
        y += 46
    return image


def apply_grade(image: Image.Image):
    image = ImageEnhance.Contrast(image).enhance(1.08)
    image = ImageEnhance.Color(image).enhance(0.9)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    draw.rectangle((0, 0, width, int(height * 0.22)), fill=(0, 0, 0, 70))
    draw.rectangle((0, int(height * 0.72), width, height), fill=(0, 0, 0, 105))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def draw_rounded_rectangle(draw, box, radius, fill):
    try:
        draw.rounded_rectangle(box, radius=radius, fill=fill)
    except AttributeError:
        draw.rectangle(box, fill=fill)


def make_caption_layer(size, scene):
    width, height = size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    is_end_card = scene["id"] == "10_end_card" or scene["id"].startswith("10")
    font = load_font(76 if is_end_card else 60)
    wrapped = textwrap.wrap(scene["caption"], width=23 if is_end_card else 28)
    line_height = 88 if is_end_card else 74
    text_height = len(wrapped) * line_height
    if is_end_card:
        y = int((height - text_height) / 2)
        box = (70, y - 42, width - 70, y + text_height + 42)
    else:
        y = height - 420
        box = (58, y - 38, width - 58, y + text_height + 42)
    draw_rounded_rectangle(draw, box, 32, (0, 0, 0, 155))
    for line in wrapped:
        text_box = draw.textbbox((0, 0), line, font=font)
        text_width = text_box[2] - text_box[0]
        draw.text(
            ((width - text_width) / 2, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=3,
            stroke_fill=(0, 0, 0, 220),
        )
        y += line_height
    return overlay


def add_caption(image: Image.Image, scene):
    overlay = make_caption_layer(image.size, scene)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def find_scene_asset(directory: Path, asset_id: str, extensions):
    for suffix in extensions:
        candidate = directory / f"{asset_id}{suffix}"
        if candidate.exists():
            return candidate
    return None


def prepare_background(scene, width, height):
    source_id = scene.get("image_id", scene["id"])
    image_path = find_scene_asset(IMAGES_DIR, source_id, IMAGE_EXTENSIONS)
    if image_path:
        image = Image.open(image_path)
        image = cover_image(image, width, height)
    else:
        image = make_placeholder(scene.get("prompt", scene["caption"]), width, height)
    image = add_caption(apply_grade(image), scene)
    out = WORK_DIR / f"{scene['id']}_bg.png"
    image.save(out)
    return out


def prepare_caption_overlay(scene, width, height):
    overlay = make_caption_layer((width, height), scene)
    out = WORK_DIR / f"{scene['id']}_caption.png"
    overlay.save(out)
    return out


def find_cover_asset(slug: str):
    for suffix in IMAGE_EXTENSIONS:
        candidate = EXPORTS_DIR / f"{slug}_cover{suffix}"
        if candidate.exists():
            return candidate
    return None


def render_cover_intro_segment(ffmpeg, cover_path: Path, duration, width, height, fps):
    image = cover_image(Image.open(cover_path), width, height)
    out_image = WORK_DIR / "episode_cover_intro.png"
    image.save(out_image)
    frames = max(1, int(round(duration * fps)))
    segment = WORK_DIR / "episode_cover_intro.mp4"
    vf = (
        "zoompan="
        "z='min(zoom+0.00035,1.035)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={frames}:"
        f"s={width}x{height}:"
        f"fps={fps},"
        "setsar=1,format=yuv420p"
    )
    run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            str(out_image),
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            ambient_noise_source(),
            "-vf",
            vf,
            "-af",
            audio_fade_filter(duration, volume="0.08"),
            "-frames:v",
            str(frames),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
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
            str(segment),
        ]
    )
    return segment


def scene_video_path(scene):
    source_id = scene.get("image_id", scene["id"])
    return find_scene_asset(VIDEOS_DIR, source_id, VIDEO_EXTENSIONS)


def audio_fade_filter(duration, volume="0.20"):
    fade_out = max(0, duration - 0.35)
    return (
        f"aformat=channel_layouts=stereo,volume={volume},"
        "afade=t=in:st=0:d=0.15,"
        f"afade=t=out:st={fade_out:.3f}:d=0.35,"
        f"apad,atrim=0:{duration:.3f}"
    )


def ambient_noise_source():
    return "anoisesrc=color=brown:amplitude=0.018:sample_rate=44100"


def render_video_segment(ffmpeg, ffprobe, scene, duration, width, height, fps):
    video = scene_video_path(scene)
    overlay = prepare_caption_overlay(scene, width, height)
    segment = WORK_DIR / f"{scene['id']}.mp4"
    video_filter = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},setsar=1,format=rgba[base];"
        "[base][1:v]overlay=0:0,format=yuv420p[v]"
    )
    if ffprobe_has_audio(ffprobe, video):
        filter_complex = f"{video_filter};[0:a]{audio_fade_filter(duration)}[a]"
        cmd = [
            ffmpeg,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(video),
            "-i",
            str(overlay),
            "-t",
            f"{duration:.3f}",
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
        ]
    else:
        filter_complex = f"{video_filter};[2:a]{audio_fade_filter(duration, volume='0.14')}[a]"
        cmd = [
            ffmpeg,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(video),
            "-i",
            str(overlay),
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            ambient_noise_source(),
            "-t",
            f"{duration:.3f}",
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
        ]
    cmd += [
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
        str(segment),
    ]
    run(cmd)
    return segment


def render_still_segment(ffmpeg, scene, duration, width, height, fps):
    bg = prepare_background(scene, width, height)
    frames = max(1, int(round(duration * fps)))
    segment = WORK_DIR / f"{scene['id']}.mp4"
    vf = (
        "zoompan="
        "z='min(zoom+0.00045,1.055)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={frames}:"
        f"s={width}x{height}:"
        f"fps={fps},"
        "setsar=1,format=yuv420p"
    )
    run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            str(bg),
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            ambient_noise_source(),
            "-vf",
            vf,
            "-af",
            audio_fade_filter(duration, volume="0.12"),
            "-frames:v",
            str(frames),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
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
            str(segment),
        ]
    )
    return segment


def main():
    parser = argparse.ArgumentParser(description="Render a fiction-storytelling episode.")
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
    parser.add_argument(
        "--intro-duration",
        type=float,
        default=float(os.getenv("EPISODE_COVER_INTRO_SECONDS", INTRO_DURATION_SECONDS)),
        help="Seconds to show the episode cover before narration starts.",
    )
    args = parser.parse_args()
    load_local_env()
    configure_series(args.series)
    configure_episode(args.episode)

    ffmpeg = find_binary(
        "ffmpeg",
        "FFMPEG_PATH",
        [
            "/opt/homebrew/Cellar/ffmpeg/8.0.1_4/bin/ffmpeg",
            "/Applications/CapCut.app/Contents/Resources/ffmpeg",
        ],
    )
    ffprobe = find_binary(
        "ffprobe",
        "FFPROBE_PATH",
        ["/opt/homebrew/Cellar/ffmpeg/8.0.1_4/bin/ffprobe"],
    )

    data = json.loads(SCENES_PATH.read_text(encoding="utf-8"))
    width = int(data["resolution"]["width"])
    height = int(data["resolution"]["height"])
    fps = int(data["resolution"]["fps"])
    source_scenes = data["scenes"]
    source_by_id = {scene["id"]: scene for scene in source_scenes}
    scenes = data.get("caption_segments", source_scenes)
    for scene in scenes:
        source_scene = source_by_id.get(scene.get("image_id", scene["id"]), {})
        scene.setdefault("prompt", source_scene.get("prompt", scene.get("caption", "")))

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    planned_total = sum(float(scene["duration"]) for scene in scenes)
    audio_duration = ffprobe_duration(ffprobe, VOICE_PATH)
    if audio_duration:
        narration_total = sum(
            float(scene["duration"]) for scene in scenes if not scene.get("post_roll")
        )
        post_roll_total = sum(
            float(scene["duration"]) for scene in scenes if scene.get("post_roll")
        )
        narration_scale = audio_duration / narration_total if narration_total else 1.0
        durations = [
            float(scene["duration"]) if scene.get("post_roll") else float(scene["duration"]) * narration_scale
            for scene in scenes
        ]
        target_total = audio_duration + post_roll_total
    else:
        target_total = planned_total
        durations = [float(scene["duration"]) for scene in scenes]
        print(f"Warning: missing voiceover at {VOICE_PATH}. Rendering silent preview.")

    slug = data.get("output_slug", EPISODE.name)
    intro_duration = max(0.0, float(args.intro_duration))
    cover_path = find_cover_asset(slug)
    if intro_duration and not cover_path:
        print(f"Warning: missing cover intro image for {slug}; rendering without cover intro.")
        intro_duration = 0.0

    segment_paths = []
    if intro_duration and cover_path:
        segment_paths.append(render_cover_intro_segment(ffmpeg, cover_path, intro_duration, width, height, fps))

    for scene, duration in zip(scenes, durations):
        if scene_video_path(scene):
            segment = render_video_segment(ffmpeg, ffprobe, scene, duration, width, height, fps)
        else:
            segment = render_still_segment(ffmpeg, scene, duration, width, height, fps)
        segment_paths.append(segment)

    concat_file = WORK_DIR / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{path.as_posix()}'" for path in segment_paths) + "\n",
        encoding="utf-8",
    )
    assembled_video = WORK_DIR / f"{slug}_assembled.mp4"
    run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(assembled_video),
        ]
    )

    cmd = [ffmpeg, "-y", "-i", str(assembled_video)]
    if VOICE_PATH.exists():
        voice_delay_ms = int(round(intro_duration * 1000))
        cmd += [
            "-i",
            str(VOICE_PATH),
            "-filter_complex",
            "[0:a]volume=0.18[amb];"
            f"[1:a]volume=1.0,adelay={voice_delay_ms}|{voice_delay_ms},apad[voice];"
            "[amb][voice]amix=inputs=2:duration=first:normalize=0[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-t",
            f"{target_total + intro_duration:.3f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(OUTPUT),
        ]
    else:
        cmd += ["-c:v", "copy", "-an", str(OUTPUT)]
    run(cmd)

    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
