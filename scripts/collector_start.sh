#!/usr/bin/env bash
# scripts/collector_start.sh
# Starts a collector as a background process (local / non-Pi use).
# On Raspberry Pi use systemd instead: bash deploy/install_services.sh
#
# Usage:
#   bash scripts/collector_start.sh --mode tram
#   bash scripts/collector_start.sh --mode ubahn

set -e

# ── Parse --mode argument ─────────────────────────────────────────────────────
MODE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="$2"; shift 2 ;;
        *)      echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$MODE" ]]; then
    echo "Usage: bash scripts/collector_start.sh --mode <tram|ubahn>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$SCRIPT_DIR/logs/collector-${MODE}.pid"
LOG_FILE="$SCRIPT_DIR/logs/collector-${MODE}.log"

# ── Guard: already running? ───────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[$MODE] Collector läuft bereits (PID $PID)."
        echo "Stoppen mit: bash scripts/collector_stop.sh --mode $MODE"
        exit 1
    else
        echo "[$MODE] Alte PID-Datei gefunden aber Prozess tot — wird neu gestartet."
        rm "$PID_FILE"
    fi
fi

mkdir -p "$SCRIPT_DIR/logs"

# ── Activate conda env if available ──────────────────────────────────────────
if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate tram-analysis 2>/dev/null || true
fi

cd "$SCRIPT_DIR"

nohup python -m src.collector.collect_departures --mode "$MODE" \
    >> "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "[$MODE] Collector gestartet (PID $(cat "$PID_FILE"))."
echo "Logs:   tail -f $LOG_FILE"
echo "Status: bash scripts/collector_status.sh"
echo "Stopp:  bash scripts/collector_stop.sh --mode $MODE"
