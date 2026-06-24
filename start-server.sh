#!/bin/bash
DIR="/arbeit/ai-welt/projects/ai-ensemble"
LOG="/tmp/server3000.log"
cd "$DIR" || exit 1
while true; do
    python3 -m http.server 3000 --bind 127.0.0.1 >> "$LOG" 2>&1
    sleep 2
done