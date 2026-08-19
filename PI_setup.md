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
source ~/berlin-tram-analysis/.env
curl -u "$ES_USER:$ES_PASSWORD" http://localhost:9200/tram-departures-v2/_count
```

## Credentials

Passwords live in `.env` in the repo root on the Pi and are **not** in git. `git pull`
does not create or overwrite this file — after a fresh clone it has to be created once:

```bash
cd ~/berlin-tram-analysis
cp .env.example .env && chmod 600 .env
nano .env          # → ES_PASSWORD, KIBANA_SYSTEM_PASSWORD
```

`config/settings.py` reads it via an absolute path derived from the repo root, so the
systemd collectors pick it up without any extra unit configuration. **If `.env` is
missing, the collectors fail on the next restart** with an explicit error.

### Rotating the password

`ELASTIC_PASSWORD` in `docker-compose.yml` only takes effect when initialising an empty
data volume. On a running cluster the password must be reset through Elasticsearch
itself:

Two accounts are affected: `elastic` (the superuser, used by collectors, notebooks and
the Kibana browser login) and `kibana_system` (Kibana's internal service account, used
only by `docker-compose.yml`). Write the new values into `.env` **first**, then set them
on the cluster — that way nothing has to be copied by hand:

```bash
cd ~/berlin-tram-analysis
OLD=changeme                                    # currently valid password
NEW_ES=$(openssl rand -base64 24 | tr -d '/+=')
NEW_KB=$(openssl rand -base64 24 | tr -d '/+=')

# 1. .env with the new values
cat > .env <<EOF
ES_HOST=http://localhost:9200
ES_USER=elastic
ES_PASSWORD=$NEW_ES
KIBANA_SYSTEM_PASSWORD=$NEW_KB
EOF
chmod 600 .env

# 2. Apply them to the cluster
curl -s -u "elastic:$OLD" -X POST localhost:9200/_security/user/elastic/_password \
  -H 'Content-Type: application/json' -d "{\"password\":\"$NEW_ES\"}"
curl -s -u "elastic:$NEW_ES" -X POST localhost:9200/_security/user/kibana_system/_password \
  -H 'Content-Type: application/json' -d "{\"password\":\"$NEW_KB\"}"

# 3. Restart everything that authenticates
docker restart tram-kibana
sudo systemctl restart transit-collector@tram transit-collector@ubahn

# 4. Verify: collectors running, document count rising
bash scripts/collector_status.sh
```

`elasticsearch-reset-password -u elastic -a` inside the container does the same thing but
generates the value itself, which then has to be transcribed into `.env` by hand.

Afterwards put the same `ES_PASSWORD` into the `.env` on the Mac — notebooks and scripts
use the same account.

Do not forget the `.env` on the Mac — notebooks and scripts use the same credentials.

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
