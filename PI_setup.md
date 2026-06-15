# Raspberry Pi Deployment

Runs 24/7, collecting data automatically in the background. Accessible from anywhere via SSH and Tailscale.

## Requirements

- Raspberry Pi 5, 8 GB RAM
- 32 GB microSD with Raspberry Pi OS Lite 64-bit
- Home network with internet access
- Tailscale account (free, tailscale.com)

## One-time setup (follow this order)

```bash
# 1. Basic Pi configuration
sudo apt update && sudo apt upgrade -y
sudo dphys-swapfile swapoff
# → edit /etc/dphys-swapfile: set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup && sudo dphys-swapfile swapon
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p

# 2. Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi
# → log out and back in

# 3. Miniforge (ARM-compatible Conda)
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh -b
~/miniforge3/bin/conda init bash && source ~/.bashrc
conda create -n tram-analysis python=3.11 -y

# 4. Repo and dependencies
cd ~
git clone https://github.com/<username>/berlin-tram-analysis.git
cd berlin-tram-analysis
conda activate tram-analysis
pip install -r requirements.txt

# 5. Elasticsearch + Kibana
docker-compose up -d
# Wait until healthy (~60 s), then:
python -m src.elasticsearch.indices --mode tram
python -m src.elasticsearch.indices --mode ubahn
python -m src.elasticsearch.kibana_setup
python -m src.collector.seed_stops --mode tram
python -m src.collector.seed_stops --mode ubahn

# 6. systemd services (auto-start + crash recovery)
bash deploy/install_services.sh
# → auto-detects repo path, user, and Conda Python
# → installs tram-collector.service and starts it immediately

# 7. Tailscale (remote access from anywhere)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# → open the printed link in a browser and log in
```

## Daily operations

```bash
# Status of all collectors + document counts
bash berlin-tram-analysis/scripts/collector_status.sh

# systemd service status
sudo systemctl status transit-collector@tram
sudo systemctl status transit-collector@ubahn

# Live logs
tail -f berlin-tram-analysis/logs/collector-tram.log
tail -f berlin-tram-analysis/logs/collector-ubahn.log

# Restart a single collector
sudo systemctl restart transit-collector@tram
sudo systemctl restart transit-collector@ubahn

# Docker container status
docker-compose -f berlin-tram-analysis/docker-compose.yml ps

# Query Elasticsearch directly
curl -u elastic:changeme http://localhost:9200/tram-departures-v2/_count
```

## Remote access via Tailscale

```bash
# SSH from Mac or anywhere
ssh pi@tram-pi

# Kibana in the browser (from anywhere on the Tailscale network)
http://tram-pi:5601

# Query Elasticsearch from a notebook on your Mac
# → set in config/settings.py: ES_HOST = "http://tram-pi:9200"
```

## Restart behaviour

The systemd services `transit-collector@tram` and `transit-collector@ubahn` start automatically:
- on Pi boot
- after a crash (30 s delay)
- after a power outage

Docker containers also restart automatically via `restart: unless-stopped` in `docker-compose.yml`.

## Storage

| Component | Size |
|---|---|
| Elasticsearch data (2 months) | ~2–3 GB |
| Docker images | ~1.5 GB |
| OS + software | ~4 GB |
| **Total** | **~8–9 GB** (32 GB card is sufficient) |
