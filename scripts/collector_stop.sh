#!/usr/bin/env bash
# scripts/collector_stop.sh
# Stops a background collector process started via collector_start.sh.
#
# Usage:
#   bash scripts/collector_stop.sh --mode tram
#   bash scripts/collector_stop.sh --mode ubahn

MODE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="$2"; shift 2 ;;
        *)      echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$MODE" ]]; then
    echo "Usage: bash scripts/collector_stop.sh --mode <tram|ubahn>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$SCRIPT_DIR/logs/collector-${MODE}.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "[$MODE] Keine PID-Datei gefunden — Collector läuft wahrscheinlich nicht."
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm "$PID_FILE"
    echo "[$MODE] Collector gestoppt (PID $PID)."
else
    echo "[$MODE] Prozess $PID existiert nicht mehr."
    rm "$PID_FILE"
fi
