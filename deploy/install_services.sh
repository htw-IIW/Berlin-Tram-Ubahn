#!/usr/bin/env bash
# deploy/install_services.sh
# Installs the tram-collector systemd service on Raspberry Pi.
# Run once after cloning the repo:  bash deploy/install_services.sh
#
# What it does:
#   1. Detects the repo directory and the conda-env Python
#   2. Fills placeholders in deploy/tram-collector.service
#   3. Installs + enables + starts the systemd unit
#
# After this, the collector:
#   - starts automatically on every Pi boot
#   - restarts itself after a crash (30s delay)
#   - writes logs to logs/collector.log (same as the bash scripts)

set -euo pipefail

SERVICE_NAME="tram-collector"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$REPO_DIR/deploy/tram-collector.service"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# ── Detect current user ───────────────────────────────────────────────────────
CURRENT_USER="$(whoami)"

# ── Detect Python (prefer conda env, fall back to system python3) ─────────────
CONDA_PYTHON="$HOME/miniforge3/envs/tram-analysis/bin/python"
if [ -x "$CONDA_PYTHON" ]; then
    PYTHON="$CONDA_PYTHON"
elif command -v conda &>/dev/null; then
    PYTHON="$(conda run -n tram-analysis which python 2>/dev/null)" || PYTHON="python3"
else
    PYTHON="$(command -v python3)"
fi

echo "── Installing $SERVICE_NAME ───────────────────────────────────────────"
echo "  Repo:   $REPO_DIR"
echo "  User:   $CURRENT_USER"
echo "  Python: $PYTHON"
echo ""

# ── Make sure logs dir exists ─────────────────────────────────────────────────
mkdir -p "$REPO_DIR/logs"

# ── Fill template placeholders and write unit file ────────────────────────────
sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__USER__|$CURRENT_USER|g" \
    -e "s|__PYTHON__|$PYTHON|g" \
    "$TEMPLATE" \
    | sudo tee "$UNIT_FILE" > /dev/null

echo "  Unit file written to $UNIT_FILE"

# ── Enable and start ──────────────────────────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "Done. Collector is running as a systemd service."
echo ""
echo "Useful commands:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo systemctl restart $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo "  tail -f $REPO_DIR/logs/collector.log"
