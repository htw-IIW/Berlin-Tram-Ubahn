#!/usr/bin/env python3
"""Exportiert je Tram-Haltestelle den ÖPNV-Beeinflussungsstatus der nächsten LSA.

Beantwortet die Frage, an welchen Haltestellen eine Lichtsignalanlage mit
ÖPNV-Beeinflussung steht und an welchen nicht — und hält dabei fest, wo die
Antwort auf einer Primärquelle beruht und wo auf einer Annahme.

── Was erzeugt wird ─────────────────────────────────────────────────────────

    data/export/haltestellen_lsa_tram.csv   eine Zeile je Haltestelle
    data/export/lsa_standorte.csv           eine Zeile je Anlage (alle 2.307)

Beide Dateien sind in `data/export/CODEBOOK_LSA.md` beschrieben.

── Zuordnung ────────────────────────────────────────────────────────────────

Jeder Haltestelle wird die nächstgelegene Anlage innerhalb von 150 m
zugeordnet. Definitionen und Quellenlage stehen in `src/analysis/lsa.py`,
inklusive der beiden Korrekturen gegen die Drucksache 19/19804.

    python scripts/export_lsa_haltestellen.py
    python scripts/export_lsa_haltestellen.py --radius 250   # Robustheitsprobe
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
from elasticsearch import Elasticsearch

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from config.settings import ES_HOST, ES_USER, ES_PASSWORD          # noqa: E402
from src.analysis.quality import ist_betriebliche_haltestelle       # noqa: E402
from src.analysis.lsa import (                                      # noqa: E402
    RADIUS_METERS,
    haltestellen_koordinaten,
    lade_lsa,
    lsa_je_haltestelle,
)

INDEX_DEPARTURES = "tram-departures-v2"
SEGMENT_PARQUET = WURZEL / "data" / "processed" / "segmente_tram_gesamt.parquet"
ZIEL = WURZEL / "data" / "export"

SPALTEN = [
    "stop_name", "stop_id", "lat", "lon", "linien",
    # Frage 1: liegt eine Anlage an der Haltestelle? Gemessen.
    "lsa_vorhanden", "lsa_distanz_m", "lsa_im_radius",
    # Frage 2: ist die Beeinflussung dort in Betrieb? Nur für M4/M5 beantwortet.
    "beeinflussung_belegt", "auf_drucksachen_linie",
    # Rohwert des Index, für den Abgleich mit Notebook 03
    "lsa_status",
    "lsa_id", "lsa_bezeichnung", "lsa_bemerkung",
    "avg_delay_s", "erzeugte_verspaetung_s", "n_segmentbeobachtungen",
    "n_abfahrten", "n_mit_delay", "ist_betriebshalt",
]


def zufluss_aus_parquet(pfad: Path) -> pd.DataFrame:
    """
    Erzeugte Verspätung im Zulauf je Haltestelle, aus dem Segment-Parquet.

    Das Parquet führt je Haltestellenpaar Summe und Anzahl mit; der Mittelwert
    je Zielhaltestelle ist deshalb exakt rekonstruierbar, ohne die 7,1 Mio.
    Einzelbeobachtungen erneut zu laden. Gemittelt wird über alle Zufahrten —
    also: wie viel Verspätung entsteht auf dem Weg *zu* dieser Haltestelle, im
    Zulauf auf die dortige Kreuzung.
    """
    seg = pd.read_parquet(pfad)
    agg = seg.groupby("stop_to").agg(
        summe=("summe_delta", "sum"), n=("n", "sum")).reset_index()
    agg["erzeugte_verspaetung_s"] = agg["summe"] / agg["n"]
    return agg.rename(columns={"stop_to": "stop_name",
                               "n": "n_segmentbeobachtungen"})[
        ["stop_name", "erzeugte_verspaetung_s", "n_segmentbeobachtungen"]]


def schreibe_codebook(pfad: Path, stops: pd.DataFrame, lsa: pd.DataFrame,
                      radius: float) -> None:
    verteilung = stops["lsa_status"].value_counts()
    # Zwei Zählebenen, die sich nicht decken: eine Anlage an einer Kreuzung kann
    # zwei Haltestellen im Radius haben, und nicht jede Anlage hat überhaupt
    # eine. Die Verwechslung ist die naheliegendste Fehlerquelle dieser Tabelle,
    # deshalb stehen beide Spalten nebeneinander.
    anlagen_je_status = (stops.dropna(subset=["lsa_id"])
                         .groupby("lsa_status")["lsa_id"].nunique())
    im_index = lsa["oepnv_status"].value_counts()
    zeilen = "\n".join(
        f"| `{status}` | {int(im_index.get(status, 0))} | "
        f"{int(anlagen_je_status.get(status, 0))} | {n} |"
        for status, n in verteilung.items())

    mittel = (stops[~stops["ist_betriebshalt"]]
              .groupby("lsa_status")
              .agg(halte=("stop_name", "size"),
                   verspaetung=("avg_delay_s", "mean"),
                   erzeugt=("erzeugte_verspaetung_s", "mean")))
    mittel_zeilen = "\n".join(
        f"| `{s}` | {r.halte} | {r.verspaetung:+.1f} | {r.erzeugt:+.2f} |"
        for s, r in mittel.iterrows())

    # Die Begründungen der inaktiven Anlagen sind für die Interpretation
    # wichtiger als die Zahlen darüber — deshalb vollständig in das Codebook.
    inaktiv = stops[stops["lsa_status"] == "inaktiv"].sort_values(
        "erzeugte_verspaetung_s", ascending=False)
    inaktiv_zeilen = "\n".join(
        f"| {r.lsa_bezeichnung} | {r.stop_name} | {r.lsa_bemerkung} | "
        f"{'' if pd.isna(r.erzeugte_verspaetung_s) else format(r.erzeugte_verspaetung_s, '+.1f')} |"
        for r in inaktiv.itertuples())

    inaktiv_gesamt = int((lsa["oepnv_status"] == "inaktiv").sum())
    inaktiv_anlagen = inaktiv["lsa_id"].nunique()
    _gleis = inaktiv["lsa_bemerkung"].fillna("").str.contains(
        "Gleisschäden", case=False)
    gleis_anlagen = inaktiv.loc[_gleis, "lsa_id"].nunique()
    gleis_halte = int(_gleis.sum())

    # Derselbe Vergleich einmal über alle Linien und einmal nur auf denen, die
    # die Drucksache geprüft hat.
    echt = stops[~stops["ist_betriebshalt"]]
    m45 = echt[echt["auf_drucksachen_linie"]]

    def _mittel(teil, status):
        wert = teil.loc[teil["lsa_status"] == status, "erzeugte_verspaetung_s"]
        n = int(wert.notna().sum())
        return f"{wert.mean():+.1f} s ({n} Halte)" if n else "—"

    m45_zeilen = "\n".join(
        f"| `{status}` | {_mittel(echt, status)} | {_mittel(m45, status)} |"
        for status in ("aktiv", "inaktiv", "kein_lsa"))

    # Welche inaktive Anlage hat keine Haltestelle im Radius?
    ohne_halt = lsa[(lsa["oepnv_status"] == "inaktiv")
                    & ~lsa["lsa_id"].isin(set(stops["lsa_id"].dropna()))]
    ohne_halt_zeilen = "\n".join(
        f"* **{r.bezeichnung}** — {r.oepnv_bemerkung}"
        for r in ohne_halt.itertuples()) or "* (keine)"

    pfad.write_text(f"""# Codebook — LSA-Status je Haltestelle

Erzeugt von `scripts/export_lsa_haltestellen.py` am {time.strftime('%d.%m.%Y')}.
Zuordnungsradius: **{radius:.0f} m**.

## Dateien

| Datei | Inhalt |
|---|---|
| `haltestellen_lsa_tram.csv` | eine Zeile je Tram-Haltestelle, {len(stops)} Zeilen |
| `lsa_standorte.csv` | eine Zeile je Lichtsignalanlage, {len(lsa):,} Zeilen |

Beide lassen sich über `lsa_id` verbinden. `haltestellen_lsa_tram.csv` verbindet
sich über `stop_name` mit `messpunkte_tram_sample.csv`; dort stehen die Spalten
`lsa_status` und `lsa_distanz_m` bereits an jeder Zeile.

## Zuerst: Anlagen sind nicht Haltestellen

Die beiden Ebenen decken sich nicht, und sie zu verwechseln ist die
naheliegendste Fehlerquelle dieser Tabelle:

* Eine Anlage an einer Kreuzung kann **zwei Haltestellen** im Radius haben — bei
  den inaktiven trifft das auf zwei von ihnen zu und erzeugt dort je zwei Zeilen.
* Eine Anlage kann **gar keine** Haltestelle im Radius haben und taucht dann in
  `haltestellen_lsa_tram.csv` überhaupt nicht auf.

Deshalb steht in jeder Tabelle unten, welche Ebene gemeint ist. Für Gruppen-
vergleiche ist **`lsa_id` die Clustervariable**, nicht `stop_name`: Zwei
Haltestellen an derselben Anlage sind keine zwei unabhängigen Beobachtungen.

## Zwei Spalten statt einer Skala

`lsa_status` aus dem Index sieht aus wie eine Rangfolge von `aktiv` bis
`kein_lsa`, mischt aber zwei Fragen mit sehr verschiedener Belegqualität. Der
Export trennt sie deshalb — in denselben drei Kategorien, die auch die Karte in
Notebook 03 färbt:

| Spalte | Frage | Werte | Karte |
|---|---|---|---|
| `lsa_vorhanden` | Liegt eine Anlage an der Haltestelle? **Gemessen.** | `True` / `False` | grün / grau |
| `beeinflussung_belegt` | Ist die Beeinflussung dort in Betrieb? **Nur für M4/M5 beantwortet.** | `inaktiv_belegt`, `nicht_vorhanden_belegt`, `unklar`, `nicht_belegt` | rot |

**Es gibt bewusst keine Spalte `hat_oepnv_beeinflussung`.** Für keine einzige
Anlage ist positiv belegt, dass die Beeinflussung dort arbeitet — der
WFS-Datensatz führt das Feld nicht. `nicht_belegt` heißt genau das: über diese
Anlage sagt keine Quelle etwas. Es heißt nicht "funktioniert".

### Der Rohwert `lsa_status`

Bleibt für den Abgleich mit Notebook 03 in der Datei:

| Wert | Bedeutung | Quelle |
|---|---|---|
| `aktiv` | Anlage im Radius, **nicht** in der Ausnahmeliste | keine — siehe unten |
| `inaktiv` | Beeinflussung vorhanden, aber nicht in Betrieb | Drucksache 19/19804 |
| `nicht_vorhanden` | keine Beeinflussung eingebaut | Drucksache 19/19804 |
| `unklar` | Zuordnung der Quelle nicht eindeutig (Alexanderstraße) | — |
| `kein_lsa` | keine Anlage innerhalb von {radius:.0f} m | — |
| `kein_tram` | nächste Anlage ist als "ohne Tramstrecke" geführt | — |

Verteilung auf beiden Ebenen:

| Status | Anlagen im Index | davon einer Halte zugeordnet | Haltestellen |
|---|---|---|---|
{zeilen}

Die erste Spalte zählt alle Anlagen Berlins, die zweite nur die mit einer
Tram-Haltestelle im {radius:.0f}-m-Radius, die dritte die Haltestellen. Von den
{int(im_index.get('aktiv', 0))} als `aktiv` geführten Anlagen liegen also
{int(anlagen_je_status.get('aktiv', 0))} an einer Haltestelle; sie versorgen
{int(verteilung.get('aktiv', 0))} Halte.

Zwei Eigenheiten der Tabelle:

* **`nicht_vorhanden` kommt nicht vor.** Die einzige Anlage dieser Kategorie ist
  durch Korrektur 1 auf `unklar` gegangen (siehe unten). Der Wert bleibt hier
  beschrieben, weil er im Rohindex existiert.
* **`kein_tram` bei einer Tram-Haltestelle ist ein Widerspruch** und trifft
  {int(verteilung.get('kein_tram', 0))} Halte. Der Status wurde beim Seed über die Nähe zu einer
  Haltestelle des `tram-stops`-Index vergeben, die Koordinaten hier stammen aus
  dem Abfahrtsindex — knapp außerhalb des Radius bei der einen Rechnung, knapp
  innerhalb bei der anderen. Wie `kein_lsa` zu behandeln.

## Der entscheidende Vorbehalt — woher `aktiv` kommt

Der WFS-Datensatz der Senatsverwaltung enthält Koordinaten und Bezeichnungen
aller Berliner Anlagen, aber **keine Angabe darüber, ob die ÖPNV-Beeinflussung
in Betrieb ist**. Der Status entsteht in zwei Schritten im Collector:

1. `src/collector/seed_lsa.py` — alle {len(lsa):,} Anlagen starten auf `unbekannt`.
   Nur wer mit der Bezeichnung auf eine **hartcodierte Liste aus der Drucksache**
   passt, bekommt `inaktiv` oder `nicht_vorhanden`. Das sind 11 Einträge.
2. `src/collector/enrich_lsa_tram.py` — jede verbliebene `unbekannt`-Anlage
   **innerhalb von {radius:.0f} m einer Tram-Haltestelle** wird auf `aktiv` gesetzt,
   der Rest auf `kein_tram`.

`aktiv` heißt damit wörtlich: *liegt in der Nähe einer Haltestelle und stand
nicht auf der Liste.* Über die Beeinflussung sagt es **nichts**. Die {int(im_index.get('aktiv', 0))}
`aktiv`-Anlagen sind schlicht die Anlagen am Tramnetz.

Belegt ist ausschließlich die negative Seite: Die Drucksache 19/19804 (Antwort
des Senats vom 07.08.2024) deckt **allein die Linien M4 und M5** ab und nennt
dort sieben Anlagen — eine ohne Beeinflussung, sechs mit vorhandener, aber nicht
in Betrieb befindlicher.

Wer daraus einen Effekt schätzt, schätzt den Effekt einer Klassifikation, deren
positive Kategorie ungeprüft ist. Die Gruppen sind zudem sehr ungleich besetzt
({int(verteilung.get('aktiv', 0))} gegen {int(verteilung.get('inaktiv', 0)) + int(verteilung.get('nicht_vorhanden', 0))} Halte) — ein Gruppenvergleich hängt an einer Handvoll
Haltestellen und sollte auf Haltestellenebene gerechnet werden, nicht auf
Einzelabfahrten. Auf Abfahrtsebene erzeugen 100.000 Beobachtungen aus 400
Haltestellen einen p-Wert, der die Zahl der Haltestellen und nicht die der
Abfahrten widerspiegelt (Notebook 03, Abschnitt 4e: Designeffekt Median 2,1).

### Die Vergleichsgruppe: M4 und M5, nicht das ganze Netz

Weil die Drucksache nur diese beiden Linien geprüft hat, steckt in einem
Vergleich der belegt-inaktiven Halte gegen **alle** Halte auch die Frage, welche
Linien überhaupt untersucht wurden. Die Spalte `auf_drucksachen_linie` grenzt auf
die geprüfte Ebene ein — und der Abstand schrumpft dabei:

| Gruppe | alle Linien | nur M4/M5 |
|---|---|---|
{m45_zeilen}

### Begriff

Der Senat schreibt durchgehend **„ÖPNV-Beeinflussung"** und nicht „Vorrang" — ein
absoluter Vorrang sei im Stadtverkehr wegen der Zielkonflikte meist nicht
möglich. Diese Auswertung übernimmt den Begriff; „Vorrang" kommt in den
Spaltennamen nicht vor.

## Zwei Korrekturen gegen die Primärquelle

Vorgenommen in der Auswertung, nicht im Index, damit die Abweichung sichtbar und
die Korrektur umkehrbar bleibt (`src/analysis/lsa.py`):

1. **Alexanderstraße.** Der Index führt sieben Anlagen als `nicht_vorhanden`; die
   Drucksache nennt genau eine. Der Seed hat offenbar auf den Straßennamen
   gemustert — ausgerechnet die Anlage, die dem Namen wörtlich entspricht,
   steht im Index als `aktiv`. Die sieben stehen jetzt auf `unklar`.
2. **Zwei fehlende Anlagen nachgetragen** — Antonplatz und Berliner
   Allee/Buschallee, beide laut Drucksache inaktiv, im Index nicht vorhanden.
   Erkennbar an `lsa_id` mit Präfix `drs-19804-`.

## Spalten — `haltestellen_lsa_tram.csv`

| Spalte | Bedeutung |
|---|---|
| `stop_name`, `stop_id` | Haltestelle |
| `lat`, `lon` | Koordinaten aus dem Abfahrtsindex |
| `linien` | alle Linien, die hier halten, mit `;` getrennt |
| `lsa_vorhanden` | **Frage 1:** Anlage im {radius:.0f}-m-Radius. Gemessen |
| `beeinflussung_belegt` | **Frage 2:** `inaktiv_belegt`, `nicht_vorhanden_belegt`, `unklar`, `nicht_belegt` |
| `auf_drucksachen_linie` | Halt liegt an M4 oder M5 — nur dort hat die Quelle nachgesehen |
| `lsa_status` | Rohwert des Index, siehe oben |
| `lsa_distanz_m` | Entfernung zur nächsten Anlage im Radius |
| `lsa_im_radius` | Zahl der Anlagen im Radius. Zugeordnet wird die **nächste**, nicht die schlechteste |
| `lsa_id`, `lsa_bezeichnung` | die zugeordnete Anlage |
| `lsa_bemerkung` | Begründung aus der Drucksache, warum keine Beeinflussung wirkt — nur bei `inaktiv` / `nicht_vorhanden` gefüllt |
| `avg_delay_s` | mittlere Verspätung an dieser Haltestelle, gesamter Erhebungszeitraum |
| `erzeugte_verspaetung_s` | mittleres `delta_delay` **im Zulauf** auf diese Haltestelle, 60 Werktage |
| `n_segmentbeobachtungen` | Beobachtungen hinter `erzeugte_verspaetung_s` |
| `n_abfahrten`, `n_mit_delay` | Umfang der Verspätungsdaten |
| `ist_betriebshalt` | Betriebshof, `[Ausstieg]`, `[Endstelle]` — **vor der Auswertung ausschließen** |

`erzeugte_verspaetung_s` ist die Größe, die für einen LSA-Vergleich taugt, nicht
`avg_delay_s`: Die Verspätung an einer Haltestelle ist überwiegend geerbt und
misst vor allem die Position in der Linie. Die Differenz zum vorherigen Halt ist
um diesen Upstream-Effekt bereinigt.

Mittelwerte je Status, ohne Betriebshalte:

| Status | Halte | Ø Verspätung (s) | Ø erzeugte Verspätung (s) |
|---|---|---|---|
{mittel_zeilen}

## Die {inaktiv_gesamt} inaktiven Anlagen im Klartext — und warum das die Auswertung entscheidet

Die Drucksache 19/19804 nennt **{inaktiv_gesamt} Anlagen** mit vorhandener, aber nicht in
Betrieb befindlicher Beeinflussung. {inaktiv_anlagen} davon haben eine Haltestelle im
{radius:.0f}-m-Radius; sie erzeugen die folgenden **{len(inaktiv)} Zeilen** der
Haltestellentabelle:

| Anlage | Haltestelle | Begründung laut Drucksache | Ø erzeugte Verspätung (s) |
|---|---|---|---|
{inaktiv_zeilen}

Ohne Haltestelle im Radius, deshalb nicht in der Tabelle:

{ohne_halt_zeilen}

**{gleis_anlagen} der {inaktiv_gesamt} Anlagen sind wegen einer Langsamfahrstelle nach
Gleisschäden außer Betrieb** — sie stehen an {gleis_halte} der {len(inaktiv)} Haltestellen und
liefern die beiden höchsten Werte der Tabelle. Damit ist die naheliegende Lesart
nicht die einzige:

* *Kausal:* Die Beeinflussung fehlt, die Bahn steht länger an der Ampel.
* *Konfundiert:* Der Gleisschaden verlangsamt die Bahn **und** ist der Grund,
  warum die Anlage abgeschaltet wurde. Die Ampel ist dann Symptom, nicht Ursache.

Die Drucksache belegt den zweiten Mechanismus selbst. In Antwort 7 schreibt der
Senat, bei *„Langsamfahrstellen durch die BVG aufgrund von Gleisschäden"*
übersteige der Projektierungsaufwand die Dauer der Einschränkung, deshalb werde
vorübergehend auf Festzeitprogramme umgestellt. Die Behörde sagt also selbst,
dass das Gleis zuerst kommt und die Ampel danach.

Aus diesen Daten lässt sich zwischen beiden Lesarten nicht entscheiden. Die Spalte
`lsa_bemerkung` ist deshalb keine Fußnote, sondern die Kontrollvariable — und die
Größenordnung, um die es geht, ist klein: Wer den Gleisschadensfall herausrechnet,
behält {inaktiv_anlagen - gleis_anlagen} Anlagen an {len(inaktiv) - gleis_halte} Haltestellen. Das
ist zu wenig für eine belastbare Schätzung, aber ehrlicher als der Gesamtwert.

**Auf dieser Gruppengröße hängt jeder Test an einzelnen Anlagen.** Die beiden
höchsten Werte der Tabelle — Karl-Lade-Str. und Oderbruchstr. — gehören zu
**derselben** Anlage an der Landsberger Allee. Als zwei unabhängige Beobachtungen
gezählt, verdoppeln sie den Befund, den sie belegen sollen.

Ein Nebenbefund aus Notebook 03 stützt die Konfundierungslesart: Der Unterschied
ist über die Tageszeit **flach** (Hauptverkehrszeit, Nebenzeit und Nacht alle
r ≈ 0,47). Eine Beeinflussungsanlage kann nachts kaum wirken, wenn kaum Verkehr
da ist — ein Gleisschaden wirkt rund um die Uhr.

## Spalten — `lsa_standorte.csv`

| Spalte | Bedeutung |
|---|---|
| `lsa_id` | aus den Koordinaten abgeleitete ID; `drs-19804-*` bei den Nachträgen |
| `bezeichnung` | Ortsangabe. **`standort` ist im Index durchgängig leer** |
| `lat`, `lon` | Koordinaten |
| `oepnv_status` | siehe oben, mit Korrekturen |
| `oepnv_bemerkung` | Begründung aus der Drucksache |
| `tram_linien` | Tramlinien im 150-m-Umkreis, beim Seed abgeleitet |
""", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--radius", type=float, default=RADIUS_METERS,
                   help=f"Zuordnungsradius in Metern (Vorgabe {RADIUS_METERS:.0f})")
    args = p.parse_args()

    ZIEL.mkdir(parents=True, exist_ok=True)
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=180)
    if not es.ping():
        raise SystemExit(f"Keine Verbindung zu {ES_HOST}")

    print("1/4  LSA laden …")
    roh = lade_lsa(es, korrigieren=False)
    lsa = lade_lsa(es, korrigieren=True)
    print(f"  {len(roh):,} Anlagen im Index, {len(lsa):,} nach Korrektur")
    print("  Status vor / nach Korrektur:")
    vergleich = pd.concat(
        [roh["oepnv_status"].value_counts().rename("roh"),
         lsa["oepnv_status"].value_counts().rename("korrigiert")],
        axis=1).fillna(0).astype(int)
    print(vergleich.to_string().replace("\n", "\n    ").rjust(4))

    print("\n2/4  Haltestellen laden …")
    stops = haltestellen_koordinaten(es, INDEX_DEPARTURES)
    print(f"  {len(stops)} Haltestellen mit Koordinaten und Verspätungsdaten")

    print(f"\n3/4  Nächste Anlage im {args.radius:.0f}-m-Radius suchen …")
    stops = lsa_je_haltestelle(stops, lsa, args.radius)
    stops["ist_betriebshalt"] = stops["stop_name"].apply(
        ist_betriebliche_haltestelle)

    if SEGMENT_PARQUET.exists():
        stops = stops.merge(zufluss_aus_parquet(SEGMENT_PARQUET),
                            on="stop_name", how="left")
    else:
        stops["erzeugte_verspaetung_s"] = pd.NA
        stops["n_segmentbeobachtungen"] = pd.NA
        print(f"  {SEGMENT_PARQUET.name} fehlt — erzeugte Verspätung bleibt leer")

    print(stops["lsa_status"].value_counts().to_string()
          .replace("\n", "\n  ").rjust(2))

    print("\n4/4  Schreiben …")
    stops = stops[SPALTEN].sort_values(
        ["lsa_status", "erzeugte_verspaetung_s"], ascending=[True, False])
    ziel_stops = ZIEL / "haltestellen_lsa_tram.csv"
    stops.to_csv(ziel_stops, index=False, float_format="%.6g")

    lsa_aus = lsa.copy()
    lsa_aus["tram_linien"] = lsa_aus["tram_linien"].apply(
        lambda v: ";".join(map(str, v)) if isinstance(v, list) else v)
    ziel_lsa = ZIEL / "lsa_standorte.csv"
    lsa_aus.to_csv(ziel_lsa, index=False)

    schreibe_codebook(ZIEL / "CODEBOOK_LSA.md", stops, lsa, args.radius)

    print(f"  {ziel_stops}  ({len(stops)} Zeilen)")
    print(f"  {ziel_lsa}  ({len(lsa_aus):,} Zeilen)")
    print(f"  {ZIEL / 'CODEBOOK_LSA.md'}")

    echt = stops[~stops["ist_betriebshalt"]]
    print("\nKontrolle — ohne Betriebshalte")
    print("\n  Frage 1, gemessen: liegt eine Anlage an der Haltestelle?")
    print("   ", int(echt["lsa_vorhanden"].sum()), "von", len(echt), "Halten")
    print("\n  Frage 2, Quellenlage: ist die Beeinflussung in Betrieb?")
    print(echt["beeinflussung_belegt"].value_counts().to_string()
          .replace("\n", "\n    ").rjust(4))
    print("\n  Erzeugte Verspätung je Rohstatus, alle Linien / nur M4+M5:")
    for teil, name in ((echt, "alle "), (echt[echt["auf_drucksachen_linie"]], "M4/M5")):
        werte = teil.groupby("lsa_status")["erzeugte_verspaetung_s"].agg(
            ["size", "mean"]).round(2)
        print(f"    [{name}] " + "  ".join(
            f"{s} {r['mean']:+.2f} (n={int(r['size'])})"
            for s, r in werte.iterrows()))


if __name__ == "__main__":
    main()
