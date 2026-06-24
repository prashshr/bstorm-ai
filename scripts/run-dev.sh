#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-3000}"
LOG_FILE="${LOG_FILE:-/tmp/ai-ensemble-dev.log}"

cd "$ROOT_DIR"

echo "Starting AI Ensemble dev server"
echo "Root: $ROOT_DIR"
echo "URL:  http://$HOST:$PORT/"
echo "Log:  $LOG_FILE"

exec python3 -m http.server "$PORT" --bind "$HOST" >>"$LOG_FILE" 2>&1
