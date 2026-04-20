#!/usr/bin/env bash
# scripts/collector_start.sh
# Startet den Collector als Hintergrundprozess.
# Das Terminal kann danach geschlossen werden — der Prozess läuft weiter.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$SCRIPT_DIR/logs/collector.pid"
LOG_FILE="$SCRIPT_DIR/logs/collector.log"

# Prüfen ob bereits läuft
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Collector läuft bereits (PID $PID)."
        echo "Stoppen mit: bash scripts/collector_stop.sh"
        exit 1
    else
        echo "Alte PID-Datei gefunden aber Prozess tot — wird neu gestartet."
        rm "$PID_FILE"
    fi
fi

mkdir -p "$SCRIPT_DIR/logs"

# Conda-Umgebung aktivieren falls vorhanden
if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate tram-analysis 2>/dev/null || true
fi

cd "$SCRIPT_DIR"

# Hintergrundprozess starten
nohup python -m src.collector.collect_departures \
    >> "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "Collector gestartet (PID $(cat $PID_FILE))."
echo "Logs:   tail -f $LOG_FILE"
echo "Status: bash scripts/collector_status.sh"
echo "Stopp:  bash scripts/collector_stop.sh"
