#!/usr/bin/env bash
# scripts/collector_status.sh
# Shows process status, ES document counts, and recent log lines
# for all transit network collectors.

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ES_URL="http://localhost:9200"
ES_AUTH="elastic:changeme"

echo "══════════════════════════════════════════════"
echo " Collector Status"
echo "══════════════════════════════════════════════"

for MODE in tram ubahn; do
    PID_FILE="$SCRIPT_DIR/logs/collector-${MODE}.pid"
    LOG_FILE="$SCRIPT_DIR/logs/collector-${MODE}.log"

    echo ""
    echo "── $MODE ──────────────────────────────────────"

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "  ✅ Collector läuft (PID $PID)"
        else
            echo "  ❌ Collector gestoppt (PID $PID existiert nicht mehr)"
        fi
    else
        echo "  ❌ Collector nicht gestartet"
    fi

    echo ""
    echo "  Elasticsearch-Dokumente:"
    for INDEX in "${MODE}-departures" "${MODE}-disruptions" "${MODE}-stops"; do
        COUNT=$(curl -s -u "$ES_AUTH" "$ES_URL/$INDEX/_count" \
            2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('count','?'))" 2>/dev/null || echo "?")
        printf "    %-28s %s\n" "$INDEX" "$COUNT"
    done

    echo ""
    echo "  Letzte Log-Zeilen:"
    if [ -f "$LOG_FILE" ]; then
        tail -n 4 "$LOG_FILE" | sed 's/^/    /'
    else
        echo "    (noch keine Logs)"
    fi
done

echo ""
echo "══════════════════════════════════════════════"
echo "Live-Logs:"
echo "  tail -f $SCRIPT_DIR/logs/collector-tram.log"
echo "  tail -f $SCRIPT_DIR/logs/collector-ubahn.log"
