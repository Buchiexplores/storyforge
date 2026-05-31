#!/usr/bin/env python3
"""Shared configuration for the storyforge pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.story.local"
DEFAULT_SERIES_REL = ""


def load_local_env() -> None:
    if ENV_PATH.exists():
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_series_dir(series: str | None = None) -> Path:
    """Resolve the active series directory."""
    configured = (series or os.getenv("PIPELINE_SERIES_DIR", DEFAULT_SERIES_REL)).strip()
    if not configured:
        raise SystemExit(
            "No active series configured. Set PIPELINE_SERIES_DIR in .env.story.local "
            "(for example series/the_last_signal after running init_series.py), "
            "or pass --series on the command line. "
            "The examples/ folder is for published demo stories — put your own work under series/."
        )
    path = Path(configured).expanduser()
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def resolve_episode_path(episode: str | None, series_dir: Path | None = None) -> Path:
    """Resolve an episode folder under the active series."""
    series = series_dir or get_series_dir()
    if not episode:
        return series / "episode_01"
    path = Path(episode).expanduser()
    if path.is_absolute():
        return path
    if "/" in episode or episode.startswith("examples/") or episode.startswith("series/"):
        return (ROOT / path).resolve()
    return series / episode


def load_series_config(series_dir: Path | None = None) -> dict[str, Any]:
    """Load optional series-level YAML config."""
    series = series_dir or get_series_dir()
    config_path = series / "series_config.yaml"
    if not config_path.exists():
        return {}
    if yaml is None:
        raise SystemExit(
            "PyYAML is required to read series_config.yaml. Run: python3 -m pip install pyyaml"
        )
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid series config (expected mapping): {config_path}")
    return data


def load_style_template(template_name: str) -> dict[str, Any]:
    """Load a reusable style template from config/style_templates/."""
    path = ROOT / "config" / "style_templates" / f"{template_name}.yaml"
    if not path.exists():
        return {}
    if yaml is None:
        raise SystemExit(
            "PyYAML is required to read style templates. Run: python3 -m pip install pyyaml"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def merged_series_settings(series_dir: Path | None = None) -> dict[str, Any]:
    """Merge series config with an optional style template."""
    series = series_dir or get_series_dir()
    config = load_series_config(series)
    template_name = config.get("style_template")
    template = load_style_template(template_name) if template_name else {}
    merged: dict[str, Any] = {}
    for source in (template, config):
        for key, value in source.items():
            if key == "style_template":
                continue
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
    return merged


def episode_output_slug(episode_path: Path) -> str:
    scenes_path = episode_path / "scenes.json"
    if scenes_path.exists():
        try:
            data = json.loads(scenes_path.read_text(encoding="utf-8"))
            return data.get("output_slug", episode_path.name)
        except json.JSONDecodeError:
            return episode_path.name
    return episode_path.name


def default_notify_recipients() -> list[str]:
    configured = (
        os.getenv("PIPELINE_NOTIFY_EMAIL")
        or os.getenv("PIPELINE_NOTIFY_EMAILS")
        or os.getenv("EMAIL_RECEIVER")
    )
    if not configured:
        return []
    return [item.strip() for item in configured.split(",") if item.strip()]
