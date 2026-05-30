#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.story.local"
from pipeline_config import get_series_dir

SERIES_DIR = get_series_dir()


def episode_output_slug(episode_path: Path) -> str:
    scenes_path = episode_path / "scenes.json"
    if scenes_path.exists():
        try:
            return json.loads(scenes_path.read_text(encoding="utf-8")).get(
                "output_slug",
                episode_path.name,
            )
        except json.JSONDecodeError:
            return episode_path.name
    return episode_path.name


def resolve_episode_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    if path.name == value:
        return SERIES_DIR / value
    return (ROOT / path).resolve()


def first_existing(paths):
    for path in paths:
        if path and Path(path).exists():
            return str(path)
    return None


def find_binary(name: str, env_name: str, candidates):
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


def ffprobe_duration(ffprobe: str, path: Path) -> float:
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


def make_music_bed(ffmpeg: str, duration: float, output_path: Path):
    out_fade_start = max(duration - 2.0, 0.0)
    lavfi_sources = [
        f"sine=frequency=92:sample_rate=44100:duration={duration:.3f}",
        f"sine=frequency=138:sample_rate=44100:duration={duration:.3f}",
        f"sine=frequency=207:sample_rate=44100:duration={duration:.3f}",
        f"sine=frequency=276:sample_rate=44100:duration={duration:.3f}",
        f"sine=frequency=414:sample_rate=44100:duration={duration:.3f}",
        f"anoisesrc=color=pink:sample_rate=44100:duration={duration:.3f}",
    ]
    cmd = [ffmpeg, "-y"]
    for source in lavfi_sources:
        cmd += ["-f", "lavfi", "-i", source]

    filter_complex = (
        "[0:a]volume=0.80,tremolo=f=0.10:d=0.30[a0];"
        "[1:a]volume=0.66,tremolo=f=0.11:d=0.35[a1];"
        "[2:a]volume=0.46,tremolo=f=0.14:d=0.42[a2];"
        "[3:a]volume=0.30,tremolo=f=0.17:d=0.48[a3];"
        "[4:a]volume=0.16,tremolo=f=0.21:d=0.55[a4];"
        "[5:a]volume=0.035,highpass=f=120,lowpass=f=2600[n];"
        "[a0][a1][a2][a3][a4][n]"
        "amix=inputs=6:duration=longest:normalize=0,"
        "volume=1.8,"
        "acompressor=threshold=0.24:ratio=3.5:attack=60:release=500,"
        "alimiter=limit=0.82,"
        f"afade=t=in:st=0:d=1.2,afade=t=out:st={out_fade_start:.3f}:d=2.0[music]"
    )
    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[music]",
        "-ac",
        "2",
        "-ar",
        "44100",
        str(output_path),
    ]
    run(cmd)


def mix_music(ffmpeg: str, input_video: Path, music_bed: Path, output_video: Path):
    filter_complex = (
        "[0:a]volume=1.0[main];"
        "[1:a]volume=0.72[music];"
        "[music][main]"
        "sidechaincompress=threshold=0.08:ratio=5:attack=55:release=500:makeup=1[ducked];"
        "[main][ducked]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95[a]"
    )
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(input_video),
            "-i",
            str(music_bed),
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_video),
        ]
    )


def main():
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(
        description="Add an audible suspense music bed to a rendered fiction episode."
    )
    parser.add_argument(
        "--episode",
        default="episode_01",
        help="Episode folder name under the current series, or an absolute episode directory.",
    )
    args = parser.parse_args()

    ffmpeg = find_binary(
        "ffmpeg",
        "FFMPEG_PATH",
        [
            "/opt/homebrew/bin/ffmpeg",
            "/opt/homebrew/Cellar/ffmpeg/8.0.1_4/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ],
    )
    ffprobe = find_binary(
        "ffprobe",
        "FFPROBE_PATH",
        [
            "/opt/homebrew/bin/ffprobe",
            "/opt/homebrew/Cellar/ffmpeg/8.0.1_4/bin/ffprobe",
            "/usr/local/bin/ffprobe",
        ],
    )

    episode = resolve_episode_path(args.episode)
    slug = episode_output_slug(episode)
    exports_dir = episode / "assets" / "exports"
    input_video = exports_dir / f"{slug}_vertical.mp4"
    music_bed = exports_dir / f"{slug}_thriller_music_bed.wav"
    output_video = exports_dir / f"{slug}_vertical_thriller_music.mp4"

    if not input_video.exists():
        raise SystemExit(f"Missing rendered episode video: {input_video}")

    duration = ffprobe_duration(ffprobe, input_video)
    make_music_bed(ffmpeg, duration, music_bed)
    mix_music(ffmpeg, input_video, music_bed, output_video)

    print(f"Wrote {music_bed}")
    print(f"Wrote {output_video}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
