#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
ENV_FILE=".env.story.local"

locate_binary() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return 0
  fi

  local candidate
  for candidate in \
    "/opt/homebrew/bin/${name}" \
    "/usr/local/bin/${name}"; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done

  if [[ -d /opt/homebrew/Cellar/ffmpeg ]]; then
    for candidate in /opt/homebrew/Cellar/ffmpeg/*/bin/"${name}"; do
      if [[ -x "$candidate" ]]; then
        echo "$candidate"
        return 0
      fi
    done
  fi

  return 1
}

pair_ffprobe() {
  local ffmpeg_path="$1"
  local derived="${ffmpeg_path%/ffmpeg}/ffprobe"
  if [[ -x "$derived" ]]; then
    echo "$derived"
    return 0
  fi
  locate_binary ffprobe
}

prompt_yes() {
  local message="$1"
  local default_yes="${2:-1}"
  if [[ ! -t 0 ]]; then
    return 1
  fi
  local reply
  if [[ "$default_yes" == "1" ]]; then
    read -r -p "$message [Y/n]: " reply
    reply="${reply:-Y}"
  else
    read -r -p "$message [y/N]: " reply
    reply="${reply:-N}"
  fi
  [[ "$reply" =~ ^[Yy]$ ]]
}

install_ffmpeg() {
  local os
  os="$(uname -s)"

  if [[ "$os" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    if prompt_yes "ffmpeg not found. Install with Homebrew now?"; then
      brew install ffmpeg
      return 0
    fi
    return 1
  fi

  if [[ "$os" == "Linux" ]]; then
    echo "ffmpeg not found."
    if command -v apt-get >/dev/null 2>&1; then
      echo "  Install with: sudo apt-get update && sudo apt-get install -y ffmpeg"
    elif command -v dnf >/dev/null 2>&1; then
      echo "  Install with: sudo dnf install -y ffmpeg"
    elif command -v pacman >/dev/null 2>&1; then
      echo "  Install with: sudo pacman -S ffmpeg"
    else
      echo "  Install ffmpeg from https://ffmpeg.org/download.html"
    fi
    return 1
  fi

  echo "ffmpeg not found. Install from https://ffmpeg.org/download.html"
  return 1
}

update_env_var() {
  local key="$1"
  local value="$2"
  local file="$3"
  local tmp

  if [[ ! -f "$file" ]]; then
    return 0
  fi

  tmp="$(mktemp)"
  python3 - "$key" "$value" "$file" "$tmp" <<'PY'
import sys
from pathlib import Path

key, value, src, dst = sys.argv[1:5]
lines = Path(src).read_text(encoding="utf-8").splitlines()
out = []
replaced = False
prefixes = (f"{key}=", f"# {key}=")

for line in lines:
    if line.startswith(prefixes):
        out.append(f"{key}={value}")
        replaced = True
    else:
        out.append(line)

if not replaced:
    insert_at = len(out)
    for index, line in enumerate(out):
        if line.strip() == "# --- Video render ---":
            insert_at = index + 1
            while insert_at < len(out) and out[insert_at].strip() == "":
                insert_at += 1
            break
    out.insert(insert_at, f"{key}={value}")

Path(dst).write_text("\n".join(out) + "\n", encoding="utf-8")
PY
  mv "$tmp" "$file"
}

configure_ffmpeg() {
  local ffmpeg_path ffprobe_path

  if ! ffmpeg_path="$(locate_binary ffmpeg)"; then
    install_ffmpeg || true
    ffmpeg_path="$(locate_binary ffmpeg || true)"
  fi

  if [[ -z "${ffmpeg_path:-}" ]]; then
    echo ""
    echo "Warning: ffmpeg is still not available. Video rendering will fail until you install it."
    echo "  macOS:  brew install ffmpeg"
    echo "  Docs:   docs/TROUBLESHOOTING.md#ffmpeg-not-found"
    return 0
  fi

  if ! ffprobe_path="$(pair_ffprobe "$ffmpeg_path")"; then
    echo ""
    echo "Warning: ffprobe not found next to ffmpeg. Set FFPROBE_PATH manually in ${ENV_FILE}."
    return 0
  fi

  update_env_var "FFMPEG_PATH" "$ffmpeg_path" "$ENV_FILE"
  update_env_var "FFPROBE_PATH" "$ffprobe_path" "$ENV_FILE"

  echo ""
  echo "ffmpeg configured:"
  echo "  FFMPEG_PATH=$ffmpeg_path"
  echo "  FFPROBE_PATH=$ffprobe_path"
  "$ffmpeg_path" -version | head -n 1 || true
}

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f "$ENV_FILE" ]; then
  cp .env.story.example "$ENV_FILE"
  echo "Created ${ENV_FILE} — add your API keys before running the pipeline."
fi

configure_ffmpeg

echo ""
echo "Setup complete. Next steps:"
echo "  source .venv/bin/activate"
echo "  # Edit ${ENV_FILE} — see docs/API_KEYS.md for keys and voice ID"
echo "  # Try the included demo (examples/ is published reference content):"
echo "  python tools/run_episode_pipeline.py --series examples/phone_from_tomorrow --episode episode_01"
echo "  # Start your own series under series/:"
echo "  python tools/init_series.py"
