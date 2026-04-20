#!/usr/bin/env bash
# scripts/collector_status.sh
# Zeigt ob der Collector läuft, wie viele Dokumente in ES sind,
# und die letzten Log-Zeilen.

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$SCRIPT_DIR/logs/collector.pid"
LOG_FILE="$SCRIPT_DIR/logs/collector.log"
ES_URL="http://localhost:9200"
ES_AUTH="elastic:changeme"

echo "══════════════════════════════════════"
echo " Collector Status"
echo "══════════════════════════════════════"

# Prozess-Status
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ Collector läuft (PID $PID)"
    else
        echo "❌ Collector gestoppt (PID $PID existiert nicht mehr)"
    fi
else
    echo "❌ Collector nicht gestartet"
fi

echo ""
echo "── Elasticsearch-Dokumente ────────────"

# Anzahl Dokumente pro Index
for INDEX in tram-departures tram-disruptions tram-stops; do
    COUNT=$(curl -s -u "$ES_AUTH" "$ES_URL/$INDEX/_count" \
        2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('count','?'))" 2>/dev/null || echo "?")
    printf "  %-22s %s Dokumente\n" "$INDEX" "$COUNT"
done

echo ""
echo "── Letzte Log-Zeilen ──────────────────"
if [ -f "$LOG_FILE" ]; then
    tail -n 8 "$LOG_FILE"
else
    echo "  (noch keine Logs)"
fi

echo "══════════════════════════════════════"
echo "Live-Log: tail -f $LOG_FILE"
