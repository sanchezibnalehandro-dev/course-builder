#!/usr/bin/env bash
# TTS synthesis wrapper — guarantees pipefail and loads .env.
# Usage: run.sh <transcript.txt> <out_dir> [extra flags passed to synthesize-tts.py]

set -euo pipefail

TRANSCRIPT="${1:?Usage: run.sh <transcript.txt> <out_dir> [flags]}"
OUT_DIR="${2:?Usage: run.sh <transcript.txt> <out_dir> [flags]}"
shift 2

# Resolve project root (two dirs up from this script: skills/tts-synthesis/scripts/)
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

# Load env (for OPENAI_API_KEY) if .env exists
if [ -f "$ROOT/.env" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.env"
fi

SCRIPT="$ROOT/scripts/synthesize-tts.py"
[ -f "$SCRIPT" ] || { echo "ERROR: $SCRIPT not found" >&2; exit 2; }

# Select a real Python interpreter. On Windows, python3.exe may be a disabled
# Microsoft Store alias while `python` is the installed interpreter.
PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys' >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done
[ -n "$PYTHON_BIN" ] || { echo "ERROR: Python 3.10+ missing" >&2; exit 3; }

# Keep Python subprocess I/O UTF-8 on Windows consoles whose legacy code page
# cannot encode status symbols or Russian text.
export PYTHONUTF8="${PYTHONUTF8:-1}"

# Use PIPESTATUS to propagate the Python exit code through tee.
LOG="${TTS_LOG:-/tmp/tts-$(date +%s).log}"
"$PYTHON_BIN" "$SCRIPT" "$TRANSCRIPT" "$OUT_DIR" "$@" 2>&1 | tee "$LOG"
exit "${PIPESTATUS[0]}"
