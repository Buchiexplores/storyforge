#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


from pipeline_config import (
    ROOT,
    get_series_dir,
    load_local_env,
    resolve_episode_path,
)

GENERATOR = ROOT / "tools" / "generate_episode_assets.py"
RENDERER = ROOT / "tools" / "render_episode.py"
NOTIFIER = ROOT / "tools" / "send_pipeline_update.py"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def series_cli_arg(series_dir: Path) -> list[str]:
    try:
        relative = series_dir.relative_to(ROOT)
        return ["--series", str(relative)]
    except ValueError:
        return ["--series", str(series_dir)]


def episode_slug(episode_dir: Path) -> str:
    return episode_dir.name


def run(cmd, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    print(" ".join(str(part) for part in cmd))
    subprocess.run(cmd, check=True, env=env)


def find_binary(name: str, env_name: str, candidates):
    env_path = os.getenv(env_name)
    if env_path and Path(env_path).exists():
        return env_path
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return name


def ffprobe_value(ffprobe: str, path: Path, args):
    result = subprocess.run(
        [ffprobe, "-v", "error", *args, str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def create_preview_grid(ffmpeg: str, video: Path, out_path: Path):
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vf",
            "fps=1/10,scale=270:480,tile=3x3",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(out_path),
        ]
    )


def create_contact_sheet(images_dir: Path, out_path: Path):
    images = sorted(images_dir.glob("*.png"))
    if not images:
        return
    thumb_w, thumb_h = 204, 306
    cols = 5
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 34)), "#101014")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    for index, path in enumerate(images):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = (index % cols) * thumb_w + (thumb_w - image.width) // 2
        y = (index // cols) * (thumb_h + 34)
        sheet.paste(image, (x, y))
        draw.text(((index % cols) * thumb_w + 6, y + thumb_h + 6), path.stem[:24], fill="white", font=font)
    sheet.save(out_path, quality=92)


def send_update(subject: str, body: str, series_dir: Path):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as handle:
        handle.write(body)
        body_path = handle.name
    subprocess.run(
        [
            sys.executable,
            str(NOTIFIER),
            "--subject",
            subject,
            "--body-file",
            body_path,
            "--series-dir",
            str(series_dir),
        ],
        check=False,
    )


def verify_episode(episode_dir: Path, ffprobe: str):
    slug = episode_slug(episode_dir)
    video = episode_dir / "assets" / "exports" / f"{slug}_vertical.mp4"
    duration = ffprobe_value(
        ffprobe,
        video,
        ["-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1"],
    )
    video_stream = ffprobe_value(
        ffprobe,
        video,
        [
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,codec_name",
            "-of",
            "csv=p=0",
        ],
    )
    audio_stream = ffprobe_value(
        ffprobe,
        video,
        [
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,channels,sample_rate",
            "-of",
            "csv=p=0",
        ],
    )
    concat = episode_dir / "assets" / "work" / "concat.txt"
    first_segment = concat.read_text(encoding="utf-8").splitlines()[0] if concat.exists() else ""
    image_count = len(list((episode_dir / "assets" / "images").glob("*.png")))
    return {
        "video": video,
        "duration": duration,
        "video_stream": video_stream,
        "audio_stream": audio_stream,
        "first_segment": first_segment,
        "image_count": image_count,
    }


def main():
    load_local_env()
    parser = argparse.ArgumentParser(description="Run one storytelling episode end to end.")
    parser.add_argument(
        "--series",
        default=None,
        help="Series directory relative to repo root or absolute path. Defaults to PIPELINE_SERIES_DIR.",
    )
    parser.add_argument("--episode", required=True, help="Episode folder, e.g. episode_07.")
    parser.add_argument("--force", action="store_true", help="Regenerate images, cover, and motion clips.")
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-cover", action="store_true")
    parser.add_argument("--skip-videos", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--video-mode", choices=("local", "fal"), default=os.getenv("PIPELINE_VIDEO_MODE", "local"))
    parser.add_argument(
        "--notify",
        action=argparse.BooleanOptionalAction,
        default=env_bool("PIPELINE_NOTIFY_ON_RUN", True),
        help="Send or queue a completion/failure notification.",
    )
    args = parser.parse_args()

    series_dir = get_series_dir(args.series)
    episode_dir = resolve_episode_path(args.episode, series_dir)
    series_arg = series_cli_arg(series_dir)
    if not (episode_dir / "scenes.json").exists():
        raise SystemExit(f"Missing episode content package: {episode_dir / 'scenes.json'}")

    strict_env = {
        "OPENAI_IMAGE_STRICT": "1",
        "OPENAI_IMAGE_TIMEOUT_SECONDS": os.getenv("OPENAI_IMAGE_TIMEOUT_SECONDS", "180"),
    }
    ffmpeg = find_binary(
        "ffmpeg",
        "FFMPEG_PATH",
        ["/opt/homebrew/bin/ffmpeg", "/opt/homebrew/Cellar/ffmpeg/8.0.1_4/bin/ffmpeg", "/usr/local/bin/ffmpeg"],
    )
    ffprobe = find_binary(
        "ffprobe",
        "FFPROBE_PATH",
        ["/opt/homebrew/bin/ffprobe", "/opt/homebrew/Cellar/ffmpeg/8.0.1_4/bin/ffprobe", "/usr/local/bin/ffprobe"],
    )
    slug = episode_slug(episode_dir)

    try:
        if not args.skip_voice:
            run([sys.executable, str(GENERATOR), *series_arg, "--episode", args.episode, "--voice"], strict_env)
        if not args.skip_images:
            cmd = [sys.executable, str(GENERATOR), *series_arg, "--episode", args.episode, "--images", "--openai-images"]
            if args.force:
                cmd.append("--force-images")
            run(cmd, strict_env)
        if not args.skip_cover:
            cmd = [sys.executable, str(GENERATOR), *series_arg, "--episode", args.episode, "--cover", "--openai-cover"]
            if args.force:
                cmd.append("--force-cover")
            run(cmd, strict_env)
        if not args.skip_videos:
            cmd = [sys.executable, str(GENERATOR), *series_arg, "--episode", args.episode, "--videos"]
            if args.video_mode == "local":
                cmd.append("--local-videos")
            if args.force:
                cmd.append("--force-videos")
            run(cmd)
        if not args.skip_render:
            run([sys.executable, str(RENDERER), *series_arg, "--episode", args.episode])

        exports = episode_dir / "assets" / "exports"
        video = exports / f"{slug}_vertical.mp4"
        create_preview_grid(ffmpeg, video, exports / f"{slug}_preview_grid.jpg")
        create_contact_sheet(episode_dir / "assets" / "images", exports / f"{slug}_image_contact_sheet.jpg")
        verification = verify_episode(episode_dir, ffprobe)
        body = (
            f"`{args.episode}` completed successfully.\n\n"
            f"- Final video: `{verification['video']}`\n"
            f"- Duration: `{verification['duration']}` seconds\n"
            f"- Video stream: `{verification['video_stream']}`\n"
            f"- Audio stream: `{verification['audio_stream']}`\n"
            f"- Scene images: `{verification['image_count']}`\n"
            f"- First segment: `{verification['first_segment']}`\n"
            f"- Cover: `{exports / f'{slug}_cover.png'}`\n"
            f"- Preview grid: `{exports / f'{slug}_preview_grid.jpg'}`\n"
            f"- Contact sheet: `{exports / f'{slug}_image_contact_sheet.jpg'}`\n"
        )
        print(body)
        if args.notify:
            send_update(f"Storytelling episode ready: {args.episode}", body, series_dir)
    except Exception as exc:
        if args.notify:
            send_update(
                f"Storyforge pipeline failed: {args.episode}",
                f"`{args.episode}` failed.\n\n```text\n{exc}\n```\n",
                series_dir,
            )
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
