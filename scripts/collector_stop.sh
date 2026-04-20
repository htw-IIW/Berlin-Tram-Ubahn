#!/usr/bin/env bash
# scripts/collector_stop.sh

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$SCRIPT_DIR/logs/collector.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Keine PID-Datei gefunden — Collector läuft wahrscheinlich nicht."
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm "$PID_FILE"
    echo "Collector gestoppt (PID $PID)."
else
    echo "Prozess $PID existiert nicht mehr."
    rm "$PID_FILE"
fi
