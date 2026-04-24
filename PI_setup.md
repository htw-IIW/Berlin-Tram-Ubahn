# Raspberry Pi Deployment

Der Pi läuft 24/7 und sammelt Daten automatisch im Hintergrund.
Von überall per SSH + Tailscale erreichbar.

## Voraussetzungen

- Raspberry Pi 5, 8GB RAM
- MicroSD 32GB mit Raspberry Pi OS Lite 64-bit
- Heimnetz mit Internetanschluss
- Tailscale-Account (kostenlos, tailscale.com)

## Einmaliges Setup (Reihenfolge einhalten)

```bash
# 1. Pi grundlegend einrichten
sudo apt update && sudo apt upgrade -y
sudo dphys-swapfile swapoff
# → /etc/dphys-swapfile: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup && sudo dphys-swapfile swapon
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p

# 2. Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi
# → neu einloggen

# 3. Miniforge (ARM-Conda)
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh -b
~/miniforge3/bin/conda init bash && source ~/.bashrc
conda create -n tram-analysis python=3.11 -y

# 4. Repo + Dependencies
cd ~
git clone https://github.com/<username>/berlin-tram-analysis.git
cd berlin-tram-analysis
conda activate tram-analysis
pip install -r requirements.txt

# 5. Elasticsearch + Kibana
docker-compose up -d
# Warten bis healthy (~60s), dann:
python -m src.elasticsearch.indices --mode tram
python -m src.elasticsearch.indices --mode ubahn
python -m src.elasticsearch.kibana_setup
python -m src.collector.seed_stops --mode tram
python -m src.collector.seed_stops --mode ubahn

# 6. Systemd-Dienst (Autostart + Crash-Recovery)
bash deploy/install_services.sh
# → erkennt automatisch Repo-Pfad, User und Conda-Python
# → installiert tram-collector.service und startet ihn sofort

# 7. Tailscale (Remote-Zugriff von überall)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# → Link im Browser öffnen, einloggen
```

## Täglicher Betrieb — Befehle

```bash
# Status aller Collector + Dokument-Zähler
bash berlin-tram-analysis/scripts/collector_status.sh

# Systemd-Dienst-Status
sudo systemctl status transit-collector@tram
sudo systemctl status transit-collector@ubahn

# Live-Logs
tail -f berlin-tram-analysis/logs/collector-tram.log
tail -f berlin-tram-analysis/logs/collector-ubahn.log

# Einzelnen Collector neu starten
sudo systemctl restart transit-collector@tram
sudo systemctl restart transit-collector@ubahn

# Docker-Container Status
docker-compose -f berlin-tram-analysis/docker-compose.yml ps

# Elasticsearch direkt abfragen
curl -u elastic:changeme http://localhost:9200/tram-departures/_count
```

## Remote-Zugriff via Tailscale

```bash
# SSH von Mac/unterwegs
ssh pi@tram-pi

# Kibana im Browser (von überall im Tailscale-Netz)
http://tram-pi:5601

# Daten aus Python-Notebook auf dem Mac abfragen
# → in config/settings.py: ES_HOST = "http://tram-pi:9200"
```

## Neustart-Verhalten

Die systemd-Dienste `transit-collector@tram` und `transit-collector@ubahn` starten automatisch:
- beim Pi-Booten
- nach einem Absturz (nach 30s)
- nach Stromausfall

Docker-Container starten ebenfalls automatisch dank `restart: unless-stopped`
(in docker-compose.yml bereits so konfiguriert).

## Speicherverbrauch

| Was | Größe |
|---|---|
| Elasticsearch-Daten (2 Monate) | ~2–3 GB |
| Docker Images | ~1.5 GB |
| OS + Software | ~4 GB |
| **Gesamt** | **~8–9 GB** (32GB Karte reicht locker) |