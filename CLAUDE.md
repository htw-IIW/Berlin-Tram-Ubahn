# Hinweise für Claude-Sitzungen in diesem Repository

## Zuerst: WORKLOG.md lesen

An diesem Projekt arbeiten mehrere Claude-Sitzungen parallel im selben
Arbeitsverzeichnis — derzeit eine für die Datenanalyse und eine für den Videoschnitt.

**Vor der ersten Änderung an einer Datei `WORKLOG.md` im Repo-Root lesen** und das dort
beschriebene Protokoll befolgen: belegte Bereiche prüfen, eigenen Bereich eintragen,
nach getaner Arbeit im Logbuch vermerken.

`WORKLOG.md` ist bewusst nicht in Git — sie ist ein lokales Koordinationsmittel. Falls
sie fehlt, ist das kein Fehler; dann arbeitet gerade nur eine Sitzung.

## Arbeitsstand

Die Arbeit läuft auf dem Branch **`analyse-umbau`**, nicht auf `main`.

Die Notebooks `04_delay_propagation.ipynb`, `05_kosten.ipynb` und der Ordner `video/`
stehen auf Wunsch der Nutzerin in der `.gitignore`. Sie sind trotzdem Teil der Analyse
und dürfen bearbeitet werden — nur nicht mit `git add -f` erzwungen werden.

## Datenzugriff

Elasticsearch läuft auf einem Raspberry Pi unter `http://tram-pi:9200`, Kibana unter
`http://tram-pi:5601` (Version 8.17.2). Zugangsdaten stehen in `config/settings.py`.

Die Erhebung **läuft weiter**. Kennzahlen verschieben sich bei jedem Durchlauf leicht;
in Fließtext und Dokumentation deshalb runden statt exakte Nachkommastellen zu
zitieren.

`data/processed/segmente_tram_gesamt.parquet` ist ein teuer berechneter Zwischenstand
(60 Werktage, 7,1 Mio. Segmentbeobachtungen, rund 7 Minuten Rechenzeit). Nicht löschen.

## Gemeinsame Analysegrundlagen

Die Notebooks teilen sich Definitionen über `src/analysis/`:

- `quality.py` — Analysefenster, Ausschlussregeln, Schwellenwerte
- `takt.py` — effektiver Takt je Linie, Kosten von Verfrühungen
- `segmente.py` — erzeugte Verspätung je Abschnitt

Neue Auswertungen sollen diese Definitionen verwenden statt eigene Schwellen zu setzen.
Die bekannten Eigenheiten der Rohdaten sind in `DATASET.md` unter *Known Data
Characteristics* dokumentiert — insbesondere die Minutenquantisierung von `delay_s`,
der Collector-Ausfall Ende Juni und die Zählweise der Störungsmeldungen.
