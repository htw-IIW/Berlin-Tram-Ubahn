# Berlin Tram & U-Bahn Analysis

Semesterprojekt: Vergleich der Berliner Verkehrsmittel Tram und U-Bahn

Kombiniertes Projekt für **Data Science** (Jupyter-Analyse + Video) und **NoSQL-Datenbanken** (Elasticsearch + Kibana).

## Potentielle Forschungsfragen

1. Vergleich des Nutzungspotentials zwischen Tram und U-Bahn im Hinblick auf den Ausbau des ÖPNV
2. Wie pünktlich ist die Tram und wie ist der Einfluss nicht optimierter Ampelschaltungen?
3. Wo häufen sich Störungen und wann?
4. Lassen sich Verspätungen aus Tageszeit, Linie und Wochentag vorhersagen?

## Datenquellen

| Quelle | Typ | Inhalt |
|---|---|---|
| `v6.bvg.transport.rest` | REST API (live) | Abfahrten, Verspätungen, Ausfälle |
| VBB GTFS (Mobilithek) | Statisch | Fahrplan, Haltestellen, Linien |


## Stack

```
Python 3.11+
├── requests              — API-Abrufe
├── pandas                — Datenverarbeitung
├── elasticsearch         — Python-Client für ES
├── scipy / statsmodels   — Hypothesentests, Zeitreihen
├── scikit-learn          — Vorhersagemodell
└── plotly / folium       — Visualisierungen

Elasticsearch 8.17.2 + Kibana 8.17.2 (via Docker, keine manuelle Installation nötig)
```

---

## Wo werden die Daten gespeichert?

**Nicht im Repo.** Alle gesammelten Daten landen in Elasticsearch, das in einem
Docker Volume läuft, außerhalb des Repos, verwaltet von Docker:

```
collect_departures.py
        │  schreibt in
        ▼
Elasticsearch-Container
        │  persistiert in
        ▼
Docker Volume "esdata"
(z.B. /var/lib/docker/volumes/berlin-tram-analysis_esdata/)
```

Das Repo selbst enthält nur Code. `data/` und `logs/` sind im `.gitignore`.

**Speicherbedarf für 1,2 Monate Langzeitmessung:**
~200 Tram-Haltestellen + ~170 U-Bahn-Haltestellen × 10 Abfahrten × alle 60s = ~500.000 Dokumente/Tag.
Nach Elasticsearch-Kompression ca. **50,70 MB/Tag, ca. 3 GB für 2 Monate** (beide Netze zusammen).

---

## Voraussetzungen installieren

Zwei externe Programme müssen einmalig installiert werden:

**1. Anaconda** (falls noch nicht vorhanden)
→ [anaconda.com/download](https://www.anaconda.com/download) — Python 3.11+

**2. Docker Desktop** — wird für Elasticsearch und Kibana benötigt.
ES und Kibana selbst müssen *nicht* manuell installiert werden, sie laufen als Container.
→ [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
Kostenlos, verfügbar für Windows, Mac und Linux.

---

## Setup (einmalig)

### Schritt 1 — Repo klonen

```bash
git clone https://github.com/<dein-username>/Berlin-Tram-UBahn.git
cd NoSQL
```

### Schritt 2 — Conda-Umgebung einrichten

```bash
conda create -n tram-analysis python=3.11
conda activate tram-analysis
pip install -r requirements.txt
```

> Bei jeder neuen Terminal-Session: `conda activate tram-analysis`

### Schritt 3 — Elasticsearch & Kibana starten

```bash
docker-compose up -d
```

Beim ersten Start werden Images heruntergeladen (~1 GB, einmalig).
Danach erreichbar unter:
- **Elasticsearch:** http://localhost:9200
- **Kibana:** http://localhost:5601 — Login: `elastic` / `changeme`

Verbindung testen:
```bash
curl -u elastic:changeme http://localhost:9200
# → JSON mit ES-Versionsnummer = alles ok
```

### Schritt 4 — Elasticsearch-Indizes anlegen

Für jedes Netzwerk separat ausführen:

```bash
python -m src.elasticsearch.indices --mode tram
python -m src.elasticsearch.indices --mode ubahn
```

Legt jeweils vier Indizes mit ihren Mappings an. Beispielausgabe für Tram:
```
Erstelle Elasticsearch-Indizes für Straßenbahn...
  Erstellt:  tram-departures
  Erstellt:  tram-disruptions
  Erstellt:  tram-stops
  Erstellt:  tram-routes
Fertig.
```

### Schritt 5 — Kibana einrichten

```bash
python -m src.elasticsearch.kibana_setup
```

Legt automatisch an: Data Views für alle Indizes + ein leeres Basis-Dashboard.
Danach in Kibana: http://localhost:5601 → Dashboard → *Berliner Tram & U-Bahn, Übersicht*.

### Schritt 6 — Haltestellen laden (einmalig)

```bash
python -m src.collector.seed_stops --mode tram
python -m src.collector.seed_stops --mode ubahn
```

Dauert jeweils ca. 2,3 Minuten. Lädt ~200 Berliner Tram-Haltestellen und ~170 U-Bahn-Haltestellen in die jeweiligen `*-stops`-Indizes. Nur einmal nötig.

---

## Collector: Daten sammeln

### Starten (Hintergrundprozess)

```bash
bash scripts/collector_start.sh --mode tram
bash scripts/collector_start.sh --mode ubahn
```

Beide Collector laufen unabhängig im Hintergrund — **das Terminal kann geschlossen werden**.
Jeder sammelt alle 60 Sekunden Abfahrten und Verspätungen aller Haltestellen des jeweiligen Netzes
und schreibt sie direkt in Elasticsearch. Für eine Langzeitmessung einfach laufen lassen.

### Status & Logs prüfen

```bash
# Übersicht für beide Netze: läuft er? Wie viele Dokumente? Letzte Log-Zeilen?
bash scripts/collector_status.sh

# Live-Log verfolgen (Ctrl+C beendet nur die Ansicht, Collector läuft weiter)
tail -f logs/collector-tram.log
tail -f logs/collector-ubahn.log
```

Beispiel-Ausgabe von `collector_status.sh`:
```
══════════════════════════════════════════════
 Collector Status
══════════════════════════════════════════════

── tram ──────────────────────────────────────
  ✅ Collector läuft (PID 38291)

  Elasticsearch-Dokumente:
    tram-departures              143.820
    tram-disruptions             512
    tram-stops                   201

  Letzte Log-Zeilen:
    14:03:01 [INFO] [Straßenbahn] Runde 47: 2.840 Abfahrten, 12 Störungen indexiert (0 Fehler, 18.3s)
    14:04:01 [INFO] [Straßenbahn] Runde 48: 2.815 Abfahrten, 9 Störungen indexiert (0 Fehler, 17.9s)

── ubahn ─────────────────────────────────────
  ✅ Collector läuft (PID 38305)

  Elasticsearch-Dokumente:
    ubahn-departures             121.440
    ubahn-disruptions            287
    ubahn-stops                  172

  Letzte Log-Zeilen:
    14:03:05 [INFO] [U-Bahn] Runde 47: 2.430 Abfahrten, 6 Störungen indexiert (0 Fehler, 15.1s)
    14:04:05 [INFO] [U-Bahn] Runde 48: 2.398 Abfahrten, 4 Störungen indexiert (0 Fehler, 14.8s)
══════════════════════════════════════════════
```

### Stoppen

```bash
bash scripts/collector_stop.sh --mode tram
bash scripts/collector_stop.sh --mode ubahn
```

### Einmalig testen (ohne Hintergrundprozess)

```bash
python -m src.collector.collect_departures --mode tram --once
python -m src.collector.collect_departures --mode ubahn --once
```

---

## Elasticsearch & Kibana verwalten

```bash
# Container stoppen — Daten im Volume bleiben erhalten
docker-compose stop

# Container wieder starten
docker-compose start

# Alles löschen inkl. aller gesammelten Daten (Vorsicht!)
docker-compose down -v
```

In Kibana Daten direkt ansehen:
1. http://localhost:5601 → **Discover**
2. Data View `Tram Abfahrten` oder `U-Bahn Abfahrten` auswählen
3. Zeitraum oben rechts auf "Last 1 hour" setzen
4. Felder `line_name`, `delay_s`, `stop_name` in der linken Spalte anklicken

---

## Elasticsearch-Indizes

Pro Netzwerk gibt es vier Indizes (Präfix `tram-*` bzw. `ubahn-*`):

| Index | Inhalt | Wichtigste Felder |
|---|---|---|
| `*-departures` | Eine Zeile pro Abfahrt | `line_name`, `stop_name`, `delay_s`, `planned_when`, `hour_of_day`, `day_of_week`, `cancelled` |
| `*-disruptions` | Störungsmeldungen | `line_name`, `summary`, `remark_type`, `valid_from`, `valid_until` |
| `*-stops` | Haltestellen-Stammdaten | `stop_id`, `name`, `location` (geo_point), `lines` |
| `*-routes` | Linienverlauf (geordnete Haltestellen) | `line_name`, `stops` (nested: `stop_id`, `name`, `stop_sequence`, `location`) |

---

## Projektstruktur

```
berlin-tram-ubahn/
├── config/
│   └── settings.py                        # API-URLs, ES-Verbindung, Netzwerk-Konfiguration (Tram & U-Bahn)
├── data/
│   ├── raw/                               # Rohdaten-Exporte (nicht in Git)
│   └── processed/                         # Bereinigte Daten (nicht in Git)
├── deploy/
│   ├── install_services.sh                # Systemd-Dienste auf Raspberry Pi einrichten
│   └── transit-collector@.service         # Systemd-Unit-Template für Pi-Betrieb
├── docs/                                  # Dokumentation, Drehbuch
├── logs/                                  # Collector-Logs (nicht in Git)
│   └── .gitkeep
├── notebooks/
│   ├── 01_eda.ipynb                       # Explorative Datenanalyse
│   ├── 02_hypothesen.ipynb                # Hypothesentests
│   └── 03_modell.ipynb                    # Vorhersagemodell
├── scripts/
│   ├── collector_start.sh                 # Collector als Hintergrundprozess starten (--mode tram|ubahn)
│   ├── collector_stop.sh                  # Collector stoppen (--mode tram|ubahn)
│   └── collector_status.sh               # Status + Dokument-Zähler + Logs (beide Netze)
├── src/
│   ├── collector/
│   │   ├── seed_stops.py                  # Haltestellen einmalig über BVG-API laden
│   │   ├── seed_stops_gtfs.py             # Haltestellen alternativ über VBB GTFS laden
│   │   ├── seed_routes.py                 # Linienverläufe einmalig laden
│   │   ├── reseed_stops_from_departures.py # Fehlende Haltestellen aus gesammelten Abfahrten nacherfassen
│   │   └── collect_departures.py         # Abfahrten + Delays (Dauerprozess, --mode tram|ubahn)
│   ├── elasticsearch/
│   │   ├── indices.py                     # Index-Definitionen & Mappings (--mode tram|ubahn)
│   │   └── kibana_setup.py               # Data Views & Dashboard anlegen
│   └── utils/
│       └── helpers.py                     # Parsing, Datenanreicherung
├── DATASET.md                             # Dataset-Beschreibung und Schema-Dokumentation
├── PI_setup.md                            # Anleitung für Raspberry Pi Dauerbetrieb
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Jupyter starten

```bash
conda activate tram-analysis
jupyter notebook notebooks/
```

Mit `01_eda.ipynb` beginnen: setzt voraus, dass der Collector
bereits einige Stunden Daten gesammelt hat.
