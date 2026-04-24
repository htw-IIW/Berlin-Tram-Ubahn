#!/usr/bin/env bash
# deploy/install_services.sh
# Installs one systemd service instance per transit network on Raspberry Pi.
# Run once after cloning:  bash deploy/install_services.sh
#
# Creates:
#   /etc/systemd/system/transit-collector@tram.service
#   /etc/systemd/system/transit-collector@ubahn.service
#
# Both services start automatically on boot and restart after crashes (30s).
# Logs: logs/collector-tram.log  and  logs/collector-ubahn.log

set -euo pipefail

TEMPLATE_NAME="transit-collector@"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$REPO_DIR/deploy/${TEMPLATE_NAME}.service"

# ── Detect user ───────────────────────────────────────────────────────────────
CURRENT_USER="$(whoami)"

# ── Detect Python (conda env preferred, system python3 as fallback) ───────────
CONDA_PYTHON="$HOME/miniforge3/envs/tram-analysis/bin/python"
if [ -x "$CONDA_PYTHON" ]; then
    PYTHON="$CONDA_PYTHON"
elif command -v conda &>/dev/null; then
    PYTHON="$(conda run -n tram-analysis which python 2>/dev/null)" || PYTHON="$(command -v python3)"
else
    PYTHON="$(command -v python3)"
fi

echo "── Installing transit-collector services ──────────────────────────────"
echo "  Repo:   $REPO_DIR"
echo "  User:   $CURRENT_USER"
echo "  Python: $PYTHON"
echo ""

mkdir -p "$REPO_DIR/logs"

# ── Install the template unit file ───────────────────────────────────────────
UNIT_DEST="/etc/systemd/system/${TEMPLATE_NAME}.service"
sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__USER__|$CURRENT_USER|g" \
    -e "s|__PYTHON__|$PYTHON|g" \
    "$TEMPLATE" \
    | sudo tee "$UNIT_DEST" > /dev/null
echo "  Template installed: $UNIT_DEST"

sudo systemctl daemon-reload

# ── Enable and start one instance per network ─────────────────────────────────
for MODE in tram ubahn; do
    INSTANCE="transit-collector@${MODE}"
    sudo systemctl enable "$INSTANCE"
    sudo systemctl restart "$INSTANCE"
    echo "  ✅  $INSTANCE enabled and started"
done

echo ""
echo "Done. Both collectors are running."
echo ""
echo "Status:"
echo "  sudo systemctl status transit-collector@tram"
echo "  sudo systemctl status transit-collector@ubahn"
echo ""
echo "Logs:"
echo "  tail -f $REPO_DIR/logs/collector-tram.log"
echo "  tail -f $REPO_DIR/logs/collector-ubahn.log"
echo ""
echo "Restart a single collector:"
echo "  sudo systemctl restart transit-collector@tram"
