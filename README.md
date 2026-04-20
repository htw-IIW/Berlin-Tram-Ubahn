# Berlin Tram Analysis

Semesterprojekt: Ist die Berliner Tram ein gutes Verkehrsmittel?

Kombiniertes Projekt für **Data Science** (Jupyter-Analyse + Video) und **NoSQL-Datenbanken** (Elasticsearch + Kibana).

## Forschungsfragen

1. Wer nutzt die Berliner Tram — und warum? (MiD 2023)
2. Wie pünktlich ist die Tram im Vergleich zu Bussen auf ähnlichen Strecken?
3. Wo häufen sich Störungen — und wann?
4. Lassen sich Verspätungen aus Tageszeit, Linie und Wochentag vorhersagen?

## Datenquellen

| Quelle | Typ | Inhalt |
|---|---|---|
| `v6.bvg.transport.rest` | REST API (live) | Abfahrten, Verspätungen, Ausfälle |
| VBB GTFS (Mobilithek) | Statisch | Fahrplan, Haltestellen, Linien |
| OpenData Berlin Störungen | REST API | Störungsmeldungen mit Ursache |
| MiD 2023 (BASt) | CSV/SPSS | Mobilitätsverhalten, Modalwahl |

## Stack

```
Python 3.11+
├── requests              — API-Abrufe
├── pandas                — Datenverarbeitung
├── elasticsearch         — Python-Client für ES
├── scipy / statsmodels   — Hypothesentests, Zeitreihen
├── scikit-learn          — Vorhersagemodell
└── plotly / folium       — Visualisierungen

Elasticsearch 8.x + Kibana 8.x (via Docker — keine manuelle Installation nötig)
```

---

## Wo werden die Daten gespeichert?

**Nicht im Repo.** Alle gesammelten Daten landen in Elasticsearch, das in einem
Docker Volume läuft — außerhalb des Repos, verwaltet von Docker:

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

**Speicherbedarf für 1–2 Monate Langzeitmessung:**
~300 Haltestellen × 10 Abfahrten × alle 60s = ~430.000 Dokumente/Tag.
Nach Elasticsearch-Kompression ca. **40–50 MB/Tag → ~2–3 GB für 2 Monate**.

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
git clone https://github.com/<dein-username>/NoSQL.git
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

```bash
python -m src.elasticsearch.indices
```

Legt die drei Indizes mit ihren Mappings an. Ausgabe:
```
Erstellt: tram-departures
Erstellt: tram-disruptions
Erstellt: tram-stops
Fertig.
```

### Schritt 5 — Kibana einrichten

```bash
python -m src.elasticsearch.kibana_setup
```

Legt automatisch an: Data Views für alle Indizes + ein leeres Basis-Dashboard.
Danach in Kibana: http://localhost:5601 → Dashboard → *Berliner Tram — Übersicht*.

### Schritt 6 — Tram-Haltestellen laden (einmalig)

```bash
python -m src.collector.seed_stops
```

Dauert ca. 2–3 Minuten. Lädt ~300 Berliner Tram-Haltestellen in den
`tram-stops`-Index. Nur einmal nötig.

---

## Collector: Daten sammeln

### Starten (Hintergrundprozess)

```bash
bash scripts/collector_start.sh
```

Der Collector läuft jetzt im Hintergrund — **das Terminal kann geschlossen werden**.
Er sammelt alle 60 Sekunden Abfahrten + Verspätungen aller Tram-Haltestellen
und schreibt sie direkt in Elasticsearch. Für eine Langzeitmessung einfach laufen lassen.

### Status & Logs prüfen

```bash
# Übersicht: läuft er? Wie viele Dokumente? Letzte Log-Zeilen?
bash scripts/collector_status.sh

# Live-Log verfolgen (Ctrl+C beendet nur die Ansicht, Collector läuft weiter)
tail -f logs/collector.log
```

Beispiel-Ausgabe von `collector_status.sh`:
```
══════════════════════════════════════
 Collector Status
══════════════════════════════════════
✅ Collector läuft (PID 38291)

── Elasticsearch-Dokumente ────────────
  tram-departures        143.820 Dokumente
  tram-disruptions       512 Dokumente
  tram-stops             312 Dokumente

── Letzte Log-Zeilen ──────────────────
14:03:01 [INFO] Runde 47: 2.840 Abfahrten, 12 Störungen indexiert (0 Fehler, 18.3s)
14:04:01 [INFO] Runde 48: 2.815 Abfahrten, 9 Störungen indexiert (0 Fehler, 17.9s)
══════════════════════════════════════
```

### Stoppen

```bash
bash scripts/collector_stop.sh
```

### Einmalig testen (ohne Hintergrundprozess)

```bash
python -m src.collector.collect_departures --once
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
2. Data View `Tram Abfahrten` auswählen
3. Zeitraum oben rechts auf "Last 1 hour" setzen
4. Felder `line_name`, `delay_s`, `stop_name` in der linken Spalte anklicken

---

## Elasticsearch-Indizes

| Index | Inhalt | Wichtigste Felder |
|---|---|---|
| `tram-departures` | Eine Zeile pro Abfahrt | `line_name`, `stop_name`, `delay_s`, `planned_when`, `hour_of_day`, `day_of_week`, `cancelled` |
| `tram-disruptions` | Störungsmeldungen | `line_name`, `summary`, `remark_type`, `valid_from`, `valid_until` |
| `tram-stops` | Haltestellen-Stammdaten | `name`, `location` (geo_point), `lines` |

---

## Projektstruktur

```
berlin-tram-analysis/
├── config/
│   └── settings.py                  # API-URLs, ES-Verbindung, Linien-Liste
├── data/
│   ├── raw/                         # Rohdaten-Exporte (nicht in Git)
│   └── processed/                   # Bereinigte Daten (nicht in Git)
├── docs/                            # Dokumentation, Drehbuch
├── logs/                            # Collector-Logs (nicht in Git)
│   └── .gitkeep
├── notebooks/
│   ├── 01_eda.ipynb                 # Explorative Datenanalyse
│   ├── 02_hypothesen.ipynb          # Hypothesentests
│   └── 03_modell.ipynb              # Vorhersagemodell
├── scripts/
│   ├── collector_start.sh           # Collector als Hintergrundprozess starten
│   ├── collector_stop.sh            # Collector stoppen
│   └── collector_status.sh         # Status + Dokument-Zähler + Logs
├── src/
│   ├── collector/
│   │   ├── seed_stops.py            # Haltestellen einmalig laden
│   │   └── collect_departures.py   # Abfahrten + Delays (Dauerprozess)
│   ├── elasticsearch/
│   │   ├── indices.py               # Index-Definitionen & Mappings
│   │   └── kibana_setup.py         # Data Views & Dashboard anlegen
│   └── utils/
│       └── helpers.py               # Parsing, Datenanreicherung
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

Mit `01_eda.ipynb` beginnen — setzt voraus dass der Collector
bereits einige Stunden Daten gesammelt hat.