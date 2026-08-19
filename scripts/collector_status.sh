#!/usr/bin/env bash
# scripts/collector_status.sh
# Shows process status, ES document counts, and recent log lines
# for all transit network collectors.

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Zugangsdaten aus .env im Repo-Root (Vorlage: .env.example), nicht im Code.
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a; . "$SCRIPT_DIR/.env"; set +a
fi

ES_URL="${ES_HOST:-http://localhost:9200}"
if [ -z "${ES_PASSWORD:-}" ]; then
    echo "❌ ES_PASSWORD ist nicht gesetzt — .env.example nach .env kopieren." >&2
    exit 1
fi
ES_AUTH="${ES_USER:-elastic}:${ES_PASSWORD}"

echo "══════════════════════════════════════════════"
echo " Collector Status"
echo "══════════════════════════════════════════════"

for MODE in tram ubahn; do
    LOG_FILE="$SCRIPT_DIR/logs/collector-${MODE}.log"

    echo ""
    echo "── $MODE ──────────────────────────────────────"

    if systemctl is-active --quiet "transit-collector@${MODE}"; then
        MAIN_PID=$(systemctl show "transit-collector@${MODE}" --property=MainPID --value)
        echo "  ✅ Collector läuft (PID $MAIN_PID)"
    else
        echo "  ❌ Collector nicht aktiv"
        systemctl status "transit-collector@${MODE}" --no-pager -n 3 2>&1 | sed 's/^/    /'
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
